import asyncio
import json

import httpx
from langchain_core.messages import AIMessageChunk
from langchain_core.outputs import ChatGenerationChunk
from pydantic import PrivateAttr

from app.api.sse import SSEDecoder
from app.main import create_app
from tests.fakes import SpyChatModel, ToolChatModel


class StreamingModel(SpyChatModel):
    _started: asyncio.Event = PrivateAttr(default_factory=asyncio.Event)

    async def _astream(self, messages, **kwargs):
        try:
            self._started.set()
            for text in ("合成", "中文", "回答"):
                await asyncio.sleep(self.delay)
                yield ChatGenerationChunk(message=AIMessageChunk(content=text))
        except asyncio.CancelledError:
            self._cancelled = True
            raise


def parse_events(content):
    decoder = SSEDecoder()
    events = []
    for byte in content:
        events.extend(decoder.feed(bytes([byte])))
    return events


async def test_native_stream_to_sse_and_incremental_utf8_client(settings):
    app = create_app(settings=settings, model=StreamingModel())
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/chat/stream", json={"message": "流式合成测试"})
            assert response.headers["content-type"].startswith("text/event-stream")
            events = parse_events(response.content)
            assert events[0]["event"] == "run.started"
            assert events[-1]["event"] == "run.completed"
            assert (
                "".join(e["data"].get("text", "") for e in events if e["event"] == "message.delta")
                == "合成中文回答"
            )
            assert events[-1]["data"]["answer"] == "合成中文回答"
            assert [e["data"]["seq"] for e in events] == list(range(1, len(events) + 1))
            thread = (await client.get("/api/threads/" + events[-1]["data"]["thread_id"])).json()
            assert thread["messages"][-1]["content"] == "合成中文回答"


async def test_stream_tool_events_do_not_expose_arguments(settings):
    app = create_app(
        settings=settings, model=ToolChatModel(tool_name="query_health_metrics", arguments={})
    )
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            events = parse_events(
                (await client.post("/api/chat/stream", json={"message": "合成"})).content
            )
    assert [e["event"] for e in events if e["event"].startswith("tool.")] == [
        "tool.started",
        "tool.finished",
    ]
    assert json.loads(events[-1]["data"]["answer"])["success"] is True
    assert all("arguments" not in e["data"] for e in events)


async def test_stream_errors_are_terminal_and_safe(settings):
    app = create_app(settings=settings, model=SpyChatModel(failure=RuntimeError("SECRET")))
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/chat/stream", json={"message": "合成"})
    events = parse_events(response.content)
    assert events[-1]["event"] == "run.failed"
    assert "SECRET" not in response.text
    assert not any(e["event"] == "run.completed" for e in events)


async def test_stream_cancellation_closes_model_and_releases_thread(settings):
    model = StreamingModel(delay=60)
    app = create_app(settings=settings, model=model)
    async with app.router.lifespan_context(app):
        threads = app.state.threads
        async with threads.prepare(
            user_id="local-user", trace_id="cancel-test", message="合成"
        ) as run:
            stream = app.state.runtime.astream(run.message, run.context)
            task = asyncio.create_task(anext(stream))
            try:
                # Synchronize on entering the model, not on SQLite/filesystem latency.
                await asyncio.wait_for(model._started.wait(), timeout=5)
            finally:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                await stream.aclose()
        assert not threads._active
        assert model._cancelled
