from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from app.db import create_db_and_tables
from app.api.routers import servers
from app.models.servers import Server
from app import models
from app.servermanager import server_managers 


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    Path("arch_games_dev/").mkdir(parents=True, exist_ok=True)
    yield
    for server_id, asyncserver in server_managers.servers.items():
        print(f"Terminating archipelago server with id {server_id}:")
        await asyncserver.stop()

app = FastAPI(lifespan=lifespan)

app.include_router(servers.router)
