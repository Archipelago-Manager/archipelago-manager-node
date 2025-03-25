from typing import Annotated, List
from fastapi import APIRouter, Query, HTTPException
from sqlmodel import select
from app.api.deps import SessionDep
from app.models.servers import (
        Server,
        ServerCreate,
        ServerPublic,
        ServerCreateInternal
        )

router = APIRouter(prefix="/servers", tags=["server"])


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
def read_server(
        server_id: int,
        session: SessionDep,
        ):
    server = session.get(Server, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server
