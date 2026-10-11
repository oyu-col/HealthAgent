"""UI access to the same validated, owner-scoped health services as Agent tools."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request

from app.agent.errors import AgentError
from app.api.schemas import ErrorResponse
from app.auth import UserDependency
from app.domain.schemas import (
    DietInput,
    DomainModel,
    ExerciseInput,
    MetricInput,
    QueryInput,
    ToolResult,
)

RecordKind = Literal["metric", "diet", "exercise"]


class MetricWrite(DomainModel):
    record: MetricInput
    request_id: UUID


class DietWrite(DomainModel):
    record: DietInput
    request_id: UUID


class ExerciseWrite(DomainModel):
    record: ExerciseInput
    request_id: UUID


WRITE_SCHEMAS = {"metric": MetricWrite, "diet": DietWrite, "exercise": ExerciseWrite}
router = APIRouter(prefix="/api/records", tags=["health records"])


@router.get("/{kind}", response_model=ToolResult)
async def list_records(
    kind: RecordKind,
    request: Request,
    user_id: UserDependency,
    query: Annotated[QueryInput, Query()],
) -> ToolResult:
    if kind != "metric" and query.metric_type is not None:
        raise AgentError("invalid_request", "metric_type 仅适用于指标查询。", 422)
    return await request.app.state.health.query(kind, user_id, query)


@router.post(
    "/{kind}",
    response_model=ToolResult,
    responses={code: {"model": ErrorResponse} for code in (401, 409, 422)},
)
async def add_record(
    kind: RecordKind,
    body: MetricWrite | DietWrite | ExerciseWrite,
    request: Request,
    user_id: UserDependency,
) -> ToolResult:
    if not isinstance(body, WRITE_SCHEMAS[kind]):
        raise AgentError("invalid_request", "记录内容与记录类型不符。", 422)
    # A separate namespace prevents UI request IDs from colliding with graph tool receipts.
    result = await request.app.state.health.add(
        kind, user_id, body.record, f"http-record:{body.request_id}"
    )
    if not result.success:
        raise AgentError(result.error_code, result.error_message, 409)
    return result
