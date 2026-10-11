from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.auth import UserDependency
from app.config import ModelMode


class SessionResponse(BaseModel):
    user_id: str
    model_mode: ModelMode
    timezone: str
    memory_enabled: bool


router = APIRouter(tags=["session"])


@router.get("/api/session", response_model=SessionResponse)
async def current_session(request: Request, user_id: UserDependency) -> SessionResponse:
    settings = request.app.state.settings
    return SessionResponse(
        user_id=user_id,
        model_mode=settings.model_mode,
        timezone=settings.timezone,
        memory_enabled=settings.memory_enabled,
    )
