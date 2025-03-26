import asyncio
import requests
from pathlib import Path
from pydantic import HttpUrl, BaseModel
from typing import Annotated, List
from fastapi import (
        APIRouter,
        Query,
        HTTPException,
        BackgroundTasks,
        UploadFile
        )
from sqlmodel import select
from app.api.deps import SessionDep
from app.models.servers import (
        Server,
        ServerCreate,
        ServerPublic,
        ServerCreateInternal,
        ServerStateEnum
        )
from app.api.callbacks import server_callback_router

router = APIRouter(prefix="/servers", tags=["server"])


class StartServerCBInfo(BaseModel):
    hub_id: int
    game_id: int
    callback_url: HttpUrl


@router.post("/", response_model=ServerPublic)
def create_server(
        server: ServerCreate, session: SessionDep,
        ):
    port = 40000  # Todo, get this from some common file
    db_server = Server.model_validate(ServerCreateInternal(
        address="localhost",
        port=port
        ))
    session.add(db_server)
    session.commit()
    session.refresh(db_server)
    return db_server


@router.get("/", response_model=List[ServerPublic])
def read_servers(session: SessionDep,
                 offset: int = 0,
                 limit: Annotated[int, Query(le=100)] = 25
                 ):
    servers = session.exec(select(Server).offset(offset).limit(limit)).all()
    return servers


@router.get("/{server_id}", response_model=ServerPublic)
def read_server(server_id: int, session: SessionDep):
    server = session.get(Server, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@router.post("/{server_id}/init", response_model=ServerPublic,
             callbacks=server_callback_router.routes)
async def init_server(server_id, session: SessionDep,
                      archipelago_file: UploadFile):
    server = session.get(Server, server_id)
    arch_content = await archipelago_file.read()
    folder_str = f"arch_games_dev/{server.id}/"
    Path(folder_str).mkdir(parents=True, exist_ok=True)
    with open(Path(folder_str) / archipelago_file.filename, "wb") as f:
        arch_content = await archipelago_file.read()
        f.write(arch_content)
    await archipelago_file.close()
    server.archipelago_file_name = archipelago_file.filename
    session.add(server)
    session.commit()
    session.refresh(server)
    return server


async def start_archipelago_server(server: Server,
                                   session: SessionDep,
                                   callback_info: StartServerCBInfo):
    folder_str = f"arch_games_dev/{server.id}/"
    arch_file_path = Path(folder_str) / server.archipelago_file_name
    await asyncio.sleep(3)  # Actually start server here
    server.state = ServerStateEnum.running
    session.add(server)
    session.commit()
    session.refresh(server)
    callback_url = callback_info.callback_url
    hub_id = callback_info.hub_id
    game_id = callback_info.game_id
    requests.post(f"{callback_url}/hubs/{hub_id}/games/{game_id}/started")


@router.post("/{server_id}/start", response_model=ServerPublic,
             callbacks=server_callback_router.routes)
async def start_server(server_id, session: SessionDep,
                       callback_info: StartServerCBInfo,
                       background_tasks: BackgroundTasks):
    server = session.get(Server, server_id)
    server.state = ServerStateEnum.starting
    session.add(server)
    session.commit()
    session.refresh(server)
    background_tasks.add_task(start_archipelago_server,
                              server, session,
                              callback_info
                              )
    return server
