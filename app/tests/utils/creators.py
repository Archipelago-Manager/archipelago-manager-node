from pathlib import Path
from sqlmodel import Session
from app.models.servers import Server, ServerCreateInternal
from app.utils.server_utils import port_handler, server_manager
from app.utils.asyncserver import AsyncServer


def create_random_server(session: Session) -> Server:
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


def create_random_initted_server(session: Session) -> Server:
    db_server = create_random_server(session)
    folder_str = f"arch_games_dev/{db_server.id}/"
    Path(folder_str).mkdir(parents=True, exist_ok=True)
    with open('test_files/test.archipelago', 'rb') as archipelago_file:
        with open(Path(folder_str) / "game.archipelago", "wb") as f:
            arch_content = archipelago_file.read()
            f.write(arch_content)
        db_server.archipelago_file_name = "test.archipelago"
    db_server.initialized = True
    session.add(db_server)
    session.commit()
    session.refresh(db_server)
    return db_server
