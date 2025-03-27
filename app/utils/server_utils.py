from pydantic import BaseModel, ConfigDict
from sqlmodel import select
from app.models.servers import Server
from app.db import get_session
from app.utils.asyncserver import AsyncServer


# TODO: Add these to some settings file or something
MIN_PORT = 38281
MAX_PORT = 50000


class ServerManager(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    servers: dict[int, AsyncServer]


class PortHandler():
    def get_new_port(self) -> int:
        session = next(get_session())
        # Using where on port forces index to be sorted
        statement = select(Server).where(Server.port > MIN_PORT-1)
        servers = session.exec(statement)

        # Finds lowest unused port above MIN_PORT
        last_port = MIN_PORT - 1
        for server in servers:
            if server.port - 1 != last_port:
                session.close()
                return last_port + 1
            last_port = server.port
        if last_port + 1 > MAX_PORT:
            return -1
        else:
            return last_port + 1


server_manager = ServerManager(servers={})

port_handler = PortHandler()
