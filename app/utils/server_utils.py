from pydantic import BaseModel, ConfigDict
from sqlmodel import select
from app.models.servers import Server
from app.db import session_handler
from app.utils.asyncserver import AsyncServer
from app.core.config import settings


class ServerManager(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    servers: dict[int, AsyncServer]


class PortHandler():
    def get_new_port(self) -> int:
        session = next(session_handler.get_session())
        # Using where on port forces index to be sorted
        statement = select(Server).where(
                Server.port > settings.ARCHIPELAGO_PORT_START-1
                )
        servers = session.exec(statement)

        # Finds lowest unused port above ARCHIPELAGO_PORT_START
        last_port = settings.ARCHIPELAGO_PORT_START - 1
        for server in servers:
            if server.port - 1 != last_port:
                session.close()
                return last_port + 1
            last_port = server.port
        if last_port + 1 > settings.ARCHIPELAGO_PORT_END:
            return -1
        else:
            return last_port + 1


server_manager = ServerManager(servers={})

port_handler = PortHandler()
