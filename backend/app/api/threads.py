from uuid import UUID

from fastapi import APIRouter, Request

from app.api.chat import execute_chat
from app.api.schemas import (
    ChatResponse,
    ResumeRequest,
    ThreadListResponse,
    ThreadMetadata,
    ThreadResponse,
)
from app.auth import UserDependency

router = APIRouter(prefix="/api/threads", tags=["threads"])


@router.post("", response_model=ThreadMetadata)
async def create_thread(request: Request, user_id: UserDependency):
    return await request.app.state.threads.create(user_id)


@router.get("", response_model=ThreadListResponse)
async def list_threads(request: Request, user_id: UserDependency):
    return {"threads": await request.app.state.threads.list(user_id)}


@router.get("/{thread_id}", response_model=ThreadResponse)
async def get_thread(thread_id: UUID, request: Request, user_id: UserDependency):
    return await request.app.state.threads.state(user_id, str(thread_id))


@router.post("/{thread_id}/resume", response_model=ChatResponse)
async def resume_thread(
    thread_id: UUID, body: ResumeRequest, request: Request, user_id: UserDependency
):
    return await execute_chat(
        request, user_id, thread_id=str(thread_id), request_id=str(body.request_id), resume=True
    )
