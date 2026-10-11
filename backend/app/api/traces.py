from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.auth import UserDependency

router = APIRouter(prefix="/api/traces", tags=["traces"])


@router.get("")
async def list_traces(
    request: Request,
    user_id: UserDependency,
    thread_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=10000)] = 0,
):
    return {
        "traces": await request.app.state.traces.list(
            user_id, thread_id=str(thread_id) if thread_id else None, limit=limit, offset=offset
        ),
        "limit": limit,
        "offset": offset,
    }


@router.get("/{trace_id}")
async def trace_detail(trace_id: UUID, request: Request, user_id: UserDependency):
    return await request.app.state.traces.get(user_id, str(trace_id))
