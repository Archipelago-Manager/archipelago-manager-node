import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from sqlmodel import select
from app.db import create_db_and_tables, session_handler
from app.api.routers import servers
from app.models.servers import Server, ServerStateEnum
from app.utils.asyncserver import AsyncServer
from app.utils.server_utils import server_manager
from app import models


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# TODO: Refactor into utils file?
async def reinit_server_objects():
    session = next(session_handler.get_session())
    servers = session.exec(select(Server)).all()

    restart_coros = []
    for server in servers:
        as_obj = AsyncServer(server.id, server.port)
        server_manager.servers[server.id] = as_obj
        if server.state in [ServerStateEnum.running, ServerStateEnum.starting]:
            restart_coros.append(as_obj.start_wait(is_restart=True))

    if len(restart_coros) > 0:
        print("Restarting servers")
        await asyncio.gather(*restart_coros)
    print(server_manager.servers)

    session.close()


async def stop_running_servers():
    stop_coros = []
    for server_id, asyncserver in server_manager.servers.items():
        if asyncserver.running:
            stop_coros.append(asyncserver.stop())
    if len(stop_coros) > 0:
        await asyncio.gather(*stop_coros)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    Path("arch_games_dev/").mkdir(parents=True, exist_ok=True)
    await reinit_server_objects()
    yield
    await stop_running_servers()


app = FastAPI(lifespan=lifespan)

app.include_router(servers.router)
