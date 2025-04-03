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
        ServerStateEnum,
        ServerWrongStateException,
        ServerNotInitializedException
        )
from app.api.callbacks import server_callback_router
from app.utils.asyncserver import AsyncServer, ProcessNotRunningException
from app.utils.server_utils import server_manager, port_handler

router = APIRouter(prefix="/servers", tags=["server"])


class StartServerCBInfo(BaseModel):
    hub_id: int
    game_id: int
    callback_url: HttpUrl


class SendCmdBody(BaseModel):
    cmd: str


@router.post("/", response_model=ServerPublic)
def create_server(session: SessionDep):
    port = port_handler.get_new_port()
    db_server = Server.model_validate(ServerCreateInternal(
        address="localhost",
        port=port
        ))
    session.add(db_server)
    session.commit()
    session.refresh(db_server)
    sm = AsyncServer(db_server.id, db_server.port)
    server_manager.servers[db_server.id] = sm
    return db_server


@router.delete("/{server_id}")
def delete_server(server_id: int, session: SessionDep):
    server = session.get(Server, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    session.delete(server)
    session.commit()
    return {"ok": True}


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
async def init_server(server_id: int, session: SessionDep,
                      archipelago_file: UploadFile,
                      overwrite: bool = False
                      ):
    server = session.get(Server, server_id)
    folder_str = f"arch_games_dev/{server.id}/"
    if (Path(folder_str) / "game.archipelago").is_file() and \
            not overwrite:
        raise HTTPException(status_code=400,
                            detail=("Archipelago file already exists, "
                                    "rerun the command with overwrite=True "
                                    "to overwrite")
                            )
    Path(folder_str).mkdir(parents=True, exist_ok=True)
    # TODO: Make into aiofiles?
    with open(Path(folder_str) / "game.archipelago", "wb") as f:
        arch_content = await archipelago_file.read()
        f.write(arch_content)
    await archipelago_file.close()
    server.archipelago_file_name = archipelago_file.filename
    server.initialized = True
    session.add(server)
    session.commit()
    session.refresh(server)
    return server


async def wait_start_archipelago_server(server: Server,
                                        session: SessionDep,
                                        callback_info: StartServerCBInfo):
    sm = server_manager.servers[server.id]
    is_started = await sm.wait_for_startup()
    if is_started:
        server.state = ServerStateEnum.running
    else:
        server.state = ServerStateEnum.failed
    session.add(server)
    session.commit()
    session.refresh(server)
    callback_url = callback_info.callback_url
    hub_id = callback_info.hub_id
    game_id = callback_info.game_id
    body = {"state": server.state}
    requests.post(
            f"{callback_url}/hubs/{hub_id}/games/{game_id}/started",
            json=body
            )


@router.post("/{server_id}/start", response_model=ServerPublic,
             callbacks=server_callback_router.routes)
async def start_server(server_id: int, session: SessionDep,
                       callback_info: StartServerCBInfo,
                       background_tasks: BackgroundTasks):
    sm = server_manager.servers[server_id]
    server = session.get(Server, server_id)
    try:
        await sm.start()
    except ServerWrongStateException as e:
        server.state = ServerStateEnum.failed
        session.add(server)
        session.commit()
        raise HTTPException(status_code=400, detail=str(e))
    except ServerNotInitializedException:
        server.state = ServerStateEnum.failed
        session.add(server)
        session.commit()
        raise HTTPException(status_code=400,
                            detail=("Server is not initialized, "
                                    "call /server/{server_id}/init to "
                                    "initialize."
                                    )
                            )
    server.state = ServerStateEnum.starting
    session.add(server)
    session.commit()
    session.refresh(server)
    background_tasks.add_task(wait_start_archipelago_server,
                              server, session,
                              callback_info
                              )
    return server


@router.post("/{server_id}/stop", response_model=ServerPublic)
async def stop_server(server_id, session: SessionDep):
    server = session.get(Server, server_id)
    sm = server_manager.servers[server.id]
    try:
        await sm.stop()
    except ServerWrongStateException as e:
        server.state = ServerStateEnum.failed
        session.add(server)
        session.commit()
        raise HTTPException(status_code=400, detail=str(e))
    server.state = ServerStateEnum.stopped
    session.add(server)
    session.commit()
    session.refresh(server)
    return server


@router.post("/{server_id}/send_cmd")
async def send_cmd_to_sever(server_id, session: SessionDep, cmd: SendCmdBody):
    server = session.get(Server, server_id)
    sm = server_manager.servers[server.id]
    try:
        await sm.send_cmd(cmd.cmd)
    except ProcessNotRunningException as e:
        raise HTTPException(status_code=400, detail=str(e))
