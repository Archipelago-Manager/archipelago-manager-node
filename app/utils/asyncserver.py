import asyncio
from typing import Callable
from pathlib import Path
from pydantic import BaseModel, ConfigDict
from app.models.servers import (
        Server,
        ServerStateEnum,
        ServerWrongStateException,
        ServerNotInitializedException
        )
from app.db import get_session


class ProcessNotRunningException(Exception):
    pass


class CallbackManager(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    callbacks: dict[str, Callable[[str], None]] = {}
    async_callbacks: dict[str, Callable[[str], None]] = {}
    callbacks_err: dict[str, Callable[[str], None]] = {}
    async_callbacks_err: dict[str, Callable[[str], None]] = {}


class AsyncServer():
    def __init__(self, server_id, port):
        self.server_id = server_id
        self.port = port
        self.subprocess = None
        self.output_lines = []
        self.read_task = None
        self.err_task = None

        self.running = False

        self.callback_manager = CallbackManager()

    def get_is_initilized(self) -> bool:
        session = next(get_session())
        db_server = session.get(Server, self.server_id)
        session.close()
        return db_server.initialized

    def get_state(self) -> ServerStateEnum:
        session = next(get_session())
        db_server = session.get(Server, self.server_id)
        session.close()
        return db_server.state

    def set_state(self, state: ServerStateEnum) -> None:
        session = next(get_session())
        db_server = session.get(Server, self.server_id)
        db_server.state = state
        session.add(db_server)
        session.commit()
        session.close()

    def add_stdin_callback(self, name: str, func: callable):
        self.callback_manager.callbacks[name] = func

    def add_stderr_callback(self, name: str, func: callable):
        self.callback_manager.callbacks_err[name] = func

    def add_async_stdin_callback(self, name: str, func: callable):
        self.callback_manager.async_callbacks[name] = func

    def remove_stdin_callback(self, name: str):
        try:
            self.callback_manager.callbacks.pop(name)
            return True
        except KeyError:
            return False

    def remove_async_stdin_callback(self, name: str):
        try:
            self.callback_manager.async_callbacks.pop(name)
            return True
        except KeyError:
            return False

    def remove_stderr_callback(self, name: str):
        try:
            self.callback_manager.callbacks_err.pop(name)
            return True
        except KeyError:
            return False

    def has_started_cb(self, x: str):
        """
        Checks string x, sets self.running to true if x starts
        with 'server listening on '
        """
        if x.startswith("server listening"):
            self.running = True

    async def consume_lines(self):
        stdout = self.subprocess.stdout
        async for line in stdout:
            sanitized_line = line.decode("utf-8").strip()

            # Sync callbacks
            for _, func in self.callback_manager.callbacks.items():
                func(sanitized_line)

            # Async callbacks
            if len(self.callback_manager.async_callbacks) > 0:
                coros = [func(sanitized_line) for _, func in
                         self.callback_manager.async_callbacks.items()]
                asyncio.gather(*coros)

        else:
            # When outout stops, the server has stopped
            self.running = False
            self.subprocess = None

    async def consume_errors(self):
        stderr = self.subprocess.stderr
        async for line in stderr:
            sanitized_line = line.decode("utf-8").strip()

            # Sync callbacks
            for _, func in self.callback_manager.callbacks_err.items():
                func(sanitized_line)

            # Async callbacks
            if len(self.callback_manager.async_callbacks_err) > 0:
                coros = [func(sanitized_line) for _, func in
                         self.callback_manager.async_callbacks_err.items()]
                asyncio.gather(*coros)

    async def wait_for_startup(self):
        for _ in range(10):  # 0.5 * 10 = 5s
            await asyncio.sleep(0.5)
            if self.running:
                self.remove_stdin_callback("start_cb")
                return True
        self.remove_stdin_callback("start_cb")
        return False

    async def wait_for_shutdown(self):
        for _ in range(10):  # 0.5 * 10 = 5s
            await asyncio.sleep(0.5)
            if not self.running:
                return True
        return False

    async def start(self, is_restart=False):
        db_state = self.get_state()
        if not is_restart:
            if not self.get_is_initilized():
                raise ServerNotInitializedException(
                        "Server not initialized"
                        )
            if db_state not in [
                    ServerStateEnum.created,
                    ServerStateEnum.stopped,
                    ServerStateEnum.failed
                    ]:
                raise ServerWrongStateException(
                        f"Not in a startable state, current state: {db_state}"
                        )
        self.set_state(ServerStateEnum.starting)
        folder_str = f"arch_games_dev/{self.server_id}/"
        arch_file_path = Path(folder_str) / "game.archipelago"
        self.subprocess = await asyncio.subprocess.create_subprocess_exec(
                "ArchipelagoServer",
                "--port", str(self.port),
                arch_file_path.absolute(),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                )
        self.read_task = asyncio.create_task(self.consume_lines())
        self.err_task = asyncio.create_task(self.consume_errors())

        self.add_stdin_callback("print", print)
        self.add_stdin_callback("output",
                                lambda x: self.output_lines.append(x))
        self.add_stdin_callback("start_cb", self.has_started_cb)

    async def start_wait(self, is_restart=False):
        try:
            await self.start(is_restart)
            is_started = await self.wait_for_startup()
            self.set_state(ServerStateEnum.running)
        except Exception as e:
            is_started = False
            self.set_state(ServerStateEnum.failed)
            print(e)
        return is_started

    async def stop(self):
        db_state = self.get_state()
        if db_state is not ServerStateEnum.running:
            raise ServerWrongStateException((
                "Not in a stoppable state (not running), "
                f"current state: {db_state}"
                ))
        self.subprocess.stdin.write(str.encode("/exit\n"))
        await self.subprocess.stdin.drain()
        is_shut_down = await self.wait_for_shutdown()
        if is_shut_down:
            print(f"Server with id {self.server_id} shut down")
        else:
            print(f"Server with id {self.server_id} hung shutting down")
        return is_shut_down

    async def send_cmd(self, cmd: str):
        if not self.subprocess:
            raise ProcessNotRunningException("The process is not running, "
                                             "cannot send cmd")
        self.subprocess.stdin.write(str.encode(cmd+"\n"))
        await self.subprocess.stdin.drain()
