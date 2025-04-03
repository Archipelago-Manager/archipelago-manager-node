from sqlmodel import Session
from app.models.servers import Server, ServerCreateInternal
from app.utils.server_utils import port_handler


def create_random_server(session: Session) -> Server:
    port = port_handler.get_new_port()
    db_server = Server.model_validate(ServerCreateInternal(
        address="localhost",
        port=port
        ))
    session.add(db_server)
    session.commit()
    session.refresh(db_server)
    return db_server
