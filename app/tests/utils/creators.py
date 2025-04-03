from sqlmodel import Session
from app.models.servers import Server


def create_random_server(session: Session) -> Server:
    db_server = Server()
    session.add(db_server)
    session.commit()
    session.refresh(db_server)
    return db_server
