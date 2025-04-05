import asyncio
import pytest
import httpx
from pytest_httpx import HTTPXMock
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.models.servers import ServerStateEnum, Server
from app.utils.server_utils import server_manager
from app.tests.utils.creators import (
        create_random_server,
        create_random_initted_server
        )


def test_create_server(client: TestClient):
    response = client.post("/servers/")
    data = response.json()

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

    assert len(data) == 2
    assert response.status_code == 200
    assert data[0]["address"] == server1.address
    assert data[1]["address"] == server2.address
    assert data[0]["id"] == server1.id
    assert data[1]["id"] == server2.id


def test_delete_server(client: TestClient, session: Session):
    server = create_random_server(session)
    response = client.delete(f"/servers/{server.id}")

    assert response.status_code == 200
    # Using session.get uses cache or smth, so it says it exists when
    # it does not
    db_server = session.exec(
            select(Server).where(Server.id == server.id)
            ).first()
    assert db_server is None


def test_delete_server_not_found(client: TestClient, session: Session):
    server = create_random_server(session)
    response = client.delete(f"/servers/{server.id+1}")
    data = response.json()

    assert response.status_code == 404
    assert data['detail'] == 'Server not found'


def test_read_server(client: TestClient, session: Session):
    server = create_random_server(session)
    response = client.get(f"/servers/{server.id}")
    data = response.json()

    assert response.status_code == 200
    assert data["port"] is not None
    assert data["address"] is not None
    assert data["id"] is not None
    assert data["state"] == ServerStateEnum.created
    assert data["initialized"] is False


def test_read_server_not_found(client: TestClient, session: Session):
    server = create_random_server(session)
    response = client.get(f"/servers/{server.id+1}")
    data = response.json()

    assert response.status_code == 404
    assert data['detail'] == 'Server not found'


def test_init_server(client: TestClient, session: Session):
    server = create_random_server(session)
    with open('test_files/test.archipelago', 'rb') as f:
        file_j = {'archipelago_file': f}
        response = client.post(f"/servers/{server.id}/init/?overwrite=true",
                               files=file_j)
        data = response.json()

    assert response.status_code == 200
    assert data["port"] is not None
    assert data["address"] is not None
    assert data["id"] is not None
    assert data["state"] == ServerStateEnum.created
    assert data["initialized"] is True


def test_init_server_file_already_exists(client: TestClient, session: Session):
    server = create_random_initted_server(session)
    with open('test_files/test.archipelago', 'rb') as f:
        file_j = {'archipelago_file': f}
        response = client.post(f"/servers/{server.id}/init/",
                               files=file_j)
        data = response.json()

    assert response.status_code == 400
    assert data["detail"] == ("Archipelago file already exists, "
                              "rerun the command with overwrite=True "
                              "to overwrite")


@pytest.mark.asyncio()
async def test_start_server(client_teardown: TestClient, session: Session,
                            httpx_mock: HTTPXMock):
    server = create_random_initted_server(session)

    def mock_callback(request: httpx.Request):
        return httpx.Response(
                status_code=200, json={'state': ServerStateEnum.running}
                )
    httpx_mock.add_callback(mock_callback,
                            url="http://localhost/test/hubs/0/games/0/started"
                            )

    body = {
            "callback_url": "http://localhost/test",
            "hub_id": 0,
            "game_id": 0,
            }
    response = client_teardown.post(f"/servers/{server.id}/start", json=body)
    data = response.json()
    assert response.status_code == 200
    assert data["state"] == ServerStateEnum.starting
    assert data["initialized"] is True

    started = await server_manager.servers[server.id].wait_for_startup()
    assert started is True


@pytest.mark.asyncio()
async def test_start_server_already_started(client_teardown: TestClient,
                                            session: Session):
    server = create_random_initted_server(session)

    _ = await server_manager.servers[server.id].start_wait()

    body = {
            "callback_url": "http://localhost/test",
            "hub_id": 0,
            "game_id": 0,
            }
    response = client_teardown.post(f"/servers/{server.id}/start", json=body)
    data = response.json()
    assert response.status_code == 400
    assert data["detail"] == "Not in a startable state, current state: running"


def test_start_server_not_found(client_teardown: TestClient,
                                session: Session):
    server = create_random_initted_server(session)

    body = {
            "callback_url": "http://localhost/test",
            "hub_id": 0,
            "game_id": 0,
            }
    response = client_teardown.post(f"/servers/{server.id + 1}/start",
                                    json=body)
    data = response.json()
    assert response.status_code == 404
    assert data["detail"] == "Server not found"


@pytest.mark.asyncio()
async def test_start_server_not_initialized(client_teardown: TestClient,
                                            session: Session):
    server = create_random_server(session)

    body = {
            "callback_url": "http://localhost/test",
            "hub_id": 0,
            "game_id": 0,
            }
    response = client_teardown.post(f"/servers/{server.id}/start", json=body)
    data = response.json()
    assert response.status_code == 400
    assert data["detail"] == ("Server is not initialized, "
                              "call /server/{server_id}/init to "
                              "initialize.")


@pytest.mark.asyncio()
async def test_stop_server(client_teardown: TestClient, session: Session):
    server = create_random_initted_server(session)

    _ = await server_manager.servers[server.id].start_wait()
    await asyncio.sleep(1)

    response = client_teardown.post(f"/servers/{server.id}/stop")
    data = response.json()
    assert response.status_code == 200
    assert data["state"] == ServerStateEnum.stopped


def test_stop_server_wrong_id(client_teardown: TestClient,
                              session: Session):
    server = create_random_initted_server(session)

    response = client_teardown.post(f"/servers/{server.id+1}/stop")
    data = response.json()
    assert response.status_code == 404
    assert data["detail"] == "Server not found"


@pytest.mark.asyncio()
async def test_server_send_cmd(client_teardown: TestClient,
                               session: Session):
    server = create_random_initted_server(session)

    _ = await server_manager.servers[server.id].start_wait()
    await asyncio.sleep(1)

    json = {"cmd": "/help"}
    response = client_teardown.post(f"/servers/{server.id}/send_cmd",
                                    json=json)
    assert response.status_code == 200


def test_server_send_cmd_not_started(client_teardown: TestClient,
                                     session: Session):
    server = create_random_initted_server(session)

    json = {"cmd": "/help"}
    response = client_teardown.post(f"/servers/{server.id}/send_cmd",
                                    json=json)
    data = response.json()
    assert response.status_code == 404
    assert data["detail"] == ("The process is not running, "
                              "cannot send cmd")
