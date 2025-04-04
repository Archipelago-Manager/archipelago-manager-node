import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, delete
from sqlmodel.pool import StaticPool
from app.main import app
from app.db import session_handler
from app.models.servers import Server
from app.utils.server_utils import server_manager


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    # Make all code in tests use test engine
    session_handler.set_engine(engine)
    with Session(engine) as session:
        yield session
        statement = delete(Server)
        session.execute(statement)
        session.commit()


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    client = TestClient(app)
    yield client
    server_manager.servers = {}  # Reset server_manager


@pytest.fixture(name="client_teardown")
def client_teardown_fixture(session: Session):
    def get_session_override():
        return session

    with TestClient(app) as client:
        yield client
    server_manager.servers = {}  # Reset server_manager
