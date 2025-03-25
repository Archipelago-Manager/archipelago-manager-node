from fastapi import APIRouter
from pydantic import BaseModel
from app.models.servers import ServerStateEnum


class ServerStartedRecieved(BaseModel):
    ok: bool


class ServerStarted(BaseModel):
    state: ServerStateEnum


server_callback_router = APIRouter()


@server_callback_router.post(
    "{$callback_url}/hubs/{$request.body.hub_id}/games/{$request.bod.game_id}/started",
    response_model=ServerStartedRecieved
)
def server_started_notification(body: ServerStarted):
    pass
