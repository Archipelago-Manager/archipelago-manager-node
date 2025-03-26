import asyncio
from typing import Callable
from pathlib import Path
from pydantic import BaseModel, ConfigDict


class CallbackManager(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    callbacks: dict[str, Callable[[str], None]] = {}


class AsyncServer():
    def __init__(self, server_id, port):
        self.server_id = server_id
        self.port = port
        self.subprocess = None
        self.output_lines = []
        self.read_task = None
        self.running = False

        self.callback_manager = CallbackManager()

    async def consume_lines(self):
        stdout = self.subprocess.stdout
        async for line in stdout:
            sanitized_line = line.decode("utf-8").strip()
            for _, func in self.callback_manager.callbacks.items():
                func(sanitized_line)
        else:
            # When outout stops, the server has stopped
            self.running = False

    def add_stdin_callback(self, name: str, func: callable):
        self.callback_manager.callbacks[name] = func

    async def wait_for_shutdown(self):
        # TODO: Make this throw exception?
        for _ in range(10):  # 0.5 * 10 = 5s
            await asyncio.sleep(0.5)
            if not self.running:
                return True
        return False

    async def start(self):
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
        self.add_stdin_callback("print", print)
        self.add_stdin_callback(lambda x: self.output_lines.append(x))
        self.running = True

    async def stop(self):
        self.subprocess.stdin.write(str.encode("/exit\n"))
        await self.subprocess.stdin.drain()
        isShutDown = await self.wait_for_shutdown()
        if isShutDown:
            print("Server shut down")
        else:
            print("Server hung shutting down")


class ServerManager(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    servers: dict[int, AsyncServer]


class PortCounter(BaseModel):
    next_port: int = 40000


server_managers = ServerManager(servers={})

# TODO: Make this more refined, use a file, and some nice way of
# finding unused ports
port_counter = PortCounter()
