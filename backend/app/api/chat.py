import asyncio

from fastapi import APIRouter, Request

from app.agent.errors import AgentError
from app.api.schemas import ChatRequest, ChatResponse, ErrorResponse, HealthResponse
from app.auth import UserDependency
from app.dependencies import RuntimeDependency, SettingsDependency

router = APIRouter()


@router.get("/healthz", response_model=HealthResponse)
async def healthz(settings: SettingsDependency, runtime: RuntimeDependency) -> HealthResponse:
    """Application liveness only; never probes the paid provider."""
    return HealthResponse(model_mode=settings.model_mode)


def chat_response(answer, prepared, settings):
    context = prepared.context
    return ChatResponse(
        answer=answer,
        trace_id=context.trace_id,
        run_id=context.run_id,
        thread_id=context.thread_id,
        request_id=context.operation_id,
        model_mode=settings.model_mode,
        memory_updates=context.memory_updates,
    )


async def execute_chat(
    request, user_id, *, message=None, thread_id=None, request_id=None, resume=False
):
    settings = request.app.state.settings
    if message is not None and len(message) > settings.max_input_chars:
        raise AgentError("invalid_request", "输入超过长度限制。", 422)
    threads = request.app.state.threads
    async with threads.prepare(
        user_id=user_id,
        trace_id=request.state.trace_id,
        message=message,
        thread_id=thread_id,
        request_id=request_id,
        resume=resume,
    ) as prepared:
        request.state.thread_id = prepared.context.thread_id
        request.state.request_id = prepared.context.operation_id
        try:
            answer = prepared.cached_answer
            if answer is None:
                answer = await request.app.state.runtime.ainvoke(prepared.message, prepared.context)
            else:
                await request.app.state.runtime.record_cached(prepared.context)
            await threads.complete(prepared, answer)
            return chat_response(answer, prepared, settings)
        except BaseException:
            await asyncio.shield(threads.fail(prepared))
            raise


@router.post(
    "/api/chat",
    response_model=ChatResponse,
    responses={code: {"model": ErrorResponse} for code in (401, 404, 409, 422, 500, 502, 503, 504)},
)
async def chat(
    body: ChatRequest,
    request: Request,
    user_id: UserDependency,
) -> ChatResponse:
    return await execute_chat(
        request,
        user_id,
        message=body.message,
        thread_id=str(body.thread_id) if body.thread_id else None,
        request_id=str(body.request_id) if body.request_id else None,
    )
