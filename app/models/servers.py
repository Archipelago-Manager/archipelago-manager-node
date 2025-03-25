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
    pass


class ServerCreate(ServerBase):
    pass


class ServerPublic(ServerBase):
    state: ServerStateEnum


class Server(ServerBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    state: ServerStateEnum = ServerStateEnum.initialized
    address: str | None = None
    port: int | None = None
