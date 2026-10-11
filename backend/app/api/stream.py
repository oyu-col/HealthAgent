import asyncio
from contextlib import aclosing

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.agent.errors import AgentError
from app.api.chat import chat_response
from app.api.schemas import ChatRequest
from app.api.sse import encode_event
from app.auth import UserDependency

router = APIRouter()


@router.post("/api/chat/stream")
async def stream_chat(body: ChatRequest, request: Request, user_id: UserDependency):
    settings = request.app.state.settings
    if len(body.message) > settings.max_input_chars:
        raise AgentError("invalid_request", "输入超过长度限制。", 422)
    threads = request.app.state.threads
    if body.thread_id:
        await threads.owned(user_id, str(body.thread_id))

    async def events():
        seq = 0
        identifiers = {
            "version": 1,
            "trace_id": request.state.trace_id,
            "run_id": None,
            "thread_id": str(body.thread_id) if body.thread_id else None,
        }

        def frame(event, data):
            nonlocal seq
            seq += 1
            return encode_event(event, {**identifiers, **data, "seq": seq})

        try:
            async with threads.prepare(
                user_id=user_id,
                trace_id=request.state.trace_id,
                message=body.message,
                thread_id=str(body.thread_id) if body.thread_id else None,
                request_id=str(body.request_id) if body.request_id else None,
            ) as prepared:
                context = prepared.context
                identifiers.update(
                    run_id=context.run_id,
                    thread_id=context.thread_id,
                    request_id=context.operation_id,
                )
                completed = False
                try:
                    yield frame("run.started", {"model_mode": settings.model_mode})
                    answer = prepared.cached_answer
                    if answer is None:
                        async with aclosing(
                            request.app.state.runtime.astream(prepared.message, context)
                        ) as stream:
                            async for part in stream:
                                if part["event"] == "answer":
                                    answer = part["data"]["answer"]
                                else:
                                    yield frame(part["event"], part["data"])
                    else:
                        await request.app.state.runtime.record_cached(context)
                    await threads.complete(prepared, answer)
                    completed = True
                    yield frame(
                        "run.completed", chat_response(answer, prepared, settings).model_dump()
                    )
                except BaseException:
                    if not completed:
                        await asyncio.shield(threads.fail(prepared))
                    raise
        except AgentError as error:
            yield frame("run.failed", {"error_code": error.code, "error_message": error.message})
        except Exception:
            yield frame(
                "run.failed",
                {
                    "error_code": "internal_error",
                    "error_message": "流式执行失败，请使用 request_id 恢复。",
                },
            )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"},
    )
