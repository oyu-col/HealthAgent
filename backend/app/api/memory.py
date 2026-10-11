from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from app.auth import UserDependency
from app.memory.extraction import ALLOWED_VALUES, PreferenceKey

router = APIRouter(prefix="/api/memory", tags=["memory"])


class PreferenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str = Field(min_length=1, max_length=32)


@router.get("")
async def get_memory(request: Request, user_id: UserDependency):
    return {
        "preferences": await request.app.state.memory.list(user_id),
        "allowed_values": {key: sorted(values) for key, values in ALLOWED_VALUES.items()},
    }


@router.put("/{key}")
async def update_memory(
    key: PreferenceKey, body: PreferenceRequest, request: Request, user_id: UserDependency
):
    return {"changes": await request.app.state.memory.update(user_id, key, body.value)}


@router.delete("/{key}")
async def delete_memory(key: PreferenceKey, request: Request, user_id: UserDependency):
    return {"changes": await request.app.state.memory.update(user_id, key, None)}
