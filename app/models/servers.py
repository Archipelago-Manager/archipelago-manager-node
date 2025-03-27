from enum import Enum
from sqlmodel import SQLModel, Field


class ServerStateEnum(str, Enum):
    created = "created"
    starting = "starting"
    running = "running"
    stopped = "stopped"
    failed = "failed"


class ServerWrongStateException(Exception):
    pass


class ServerNotInitializedException(Exception):
    pass


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
    initialized: bool


class Server(ServerBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    state: ServerStateEnum = ServerStateEnum.created
    initialized: bool = False
    address: str | None = None
    port: int | None = Field(default=None, index=True)
    process_id: int | None = None
    archipelago_file_name: str | None = None
