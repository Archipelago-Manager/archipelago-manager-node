from fastapi.testclient import TestClient
from sqlmodel import Session
from app.tests.utils.creators import create_random_server
from app.models.servers import ServerStateEnum, Server


def test_create_server(client: TestClient):
    response = client.post("/servers/")
    data = response.json()

    print(data)
    assert response.status_code == 200
    assert data["port"] is not None
    assert data["address"] is not None
    assert data["id"] is not None
    assert data["state"] == ServerStateEnum.created
    assert data["initialized"] is False


def test_read_servers(client: TestClient, session: Session):
    server1 = create_random_server(session)
    server2 = create_random_server(session)
    response = client.get("/servers/")
    data = response.json()

    assert response.status_code == 200
    assert data[0]["address"] == server1.address
    assert data[1]["address"] == server2.address
    assert data[0]["id"] == server1.id
    assert data[1]["id"] == server2.id


def test_delete_servers(client: TestClient, session: Session):
    server = create_random_server(session)
    response = client.delete(f"/servers/{server.id}")
    data = response.json()

    assert response.status_code == 200
    assert data["ok"] is True
    db_server = session.get(Server, server.id)
    assert db_server is None


def test_read_server(client: TestClient, session: Session):
    server = create_random_server(session)
    response = client.get(f"/servers/{server.id}")
    data = response.json()
    print(data)

    assert response.status_code == 200
    assert data["port"] is not None
    assert data["address"] is not None
    assert data["id"] is not None
    assert data["state"] == ServerStateEnum.created
    assert data["initialized"] is False
