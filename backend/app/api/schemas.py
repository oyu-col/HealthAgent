from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.config import HARD_INPUT_LIMIT, ModelMode


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: Annotated[
        str,
        StringConstraints(
            strict=True, strip_whitespace=True, min_length=1, max_length=HARD_INPUT_LIMIT
        ),
    ]

    thread_id: UUID | None = None
    request_id: UUID | None = None


class ResumeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: UUID


class ChatResponse(BaseModel):
    answer: str
    trace_id: str
    run_id: str
    thread_id: str
    request_id: str
    model_mode: ModelMode
    termination_reason: Literal["completed"] = "completed"
    memory_updates: list[dict] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    phase: Literal[12] = 12
    model_mode: ModelMode


class ThreadMetadata(BaseModel):
    thread_id: str
    created_at: str
    active_request_id: str | None
    title: str
    status: Literal["idle", "running", "failed", "interrupted"]
    can_resume: bool
    pending: bool


class ThreadListResponse(BaseModel):
    threads: list[ThreadMetadata]


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str | list


class ThreadResponse(ThreadMetadata):
    messages: list[ConversationMessage]


class ErrorDetail(BaseModel):
    code: str
    message: str
    trace_id: str
    thread_id: str | None = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
