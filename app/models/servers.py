from enum import IntEnum
from typing import Optional
from sqlmodel import SQLModel, Field


class ServerStateEnum(IntEnum):
    initialized = 0
    starting = 1
    running = 2
    stopped = 3


#############################################################################
#                                  SERVER                                   #
#############################################################################
# An archipelago server hosted on a node                                    #
#############################################################################
class ServerBase(SQLModel):
    address: str | None = None
    port: int | None = None


class ServerCreate(SQLModel):
    pass


class ServerCreateInternal(ServerBase):
    pass


class ServerPublic(ServerBase):
    id: int
    state: ServerStateEnum


class Server(ServerBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    state: ServerStateEnum = ServerStateEnum.initialized
    address: str | None = None
    port: int | None = None
    process_id: int | None = None
