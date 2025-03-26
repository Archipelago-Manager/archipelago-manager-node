from contextlib import asynccontextmanager
import os
from pathlib import Path
from fastapi import FastAPI
from app.db import create_db_and_tables
from app.api.routers import servers
from app.models.servers import Server
from app import models


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    Path("arch_games_dev/").mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(servers.router)
