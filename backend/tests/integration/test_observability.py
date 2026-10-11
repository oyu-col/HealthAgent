import asyncio
import json
from uuid import uuid4

import httpx
import pytest
from langchain.tools import tool
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.runtime import get_runtime

from app.agent.context import RunContext
from app.agent.errors import AgentError
from app.agent.runtime import HealthAgentRuntime
from app.agents.lead_agent import build_lead_agent
from app.api.sse import SSEDecoder
from app.domain.schemas import ToolResult
from app.main import create_app
from app.persistence.database import database_session
from app.persistence.trace_repository import TraceRepository
from tests.fakes import SpyChatModel, ToolChatModel
from tests.integration.test_streaming import StreamingModel
from tests.integration.test_subagents import DelegatingModel


class UsageModel(SpyChatModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self._seen.append(messages)
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(
                        content="SYNTHETIC_PRIVATE_ANSWER",
                        usage_metadata={"input_tokens": 11, "output_tokens": 7, "total_tokens": 18},
                    )
                )
            ]
        )


async def test_trace_persists_real_model_usage_without_health_text(settings):
    model = UsageModel()
    app = create_app(settings=settings, model=model)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/chat", json={"message": "SYNTHETIC_PRIVATE_INPUT"})
            assert response.status_code == 200
            identity = response.json()
            trace = (await client.get("/api/traces/" + identity["trace_id"])).json()
            assert trace["status"] == "completed"
            assert trace["termination_reason"] == "completed"
            assert trace["model_calls"] == 1
            assert trace["tool_calls"] == 0
            assert trace["token_usage"] == {
                "input_tokens": 11,
                "output_tokens": 7,
                "total_tokens": 18,
                "complete": True,
            }
            assert trace["latency_ms"] >= 0
            assert any(event["event"] == "model.finished" for event in trace["events"])
            assert "SYNTHETIC_PRIVATE" not in json.dumps(trace)
    restored = create_app(settings=settings, model=SpyChatModel())
    async with restored.router.lifespan_context(restored):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=restored), base_url="http://test"
        ) as client:
            traces = (
                await client.get("/api/traces", params={"thread_id": identity["thread_id"]})
            ).json()
            assert traces["traces"][0]["trace_id"] == identity["trace_id"]
            assert "events" not in traces["traces"][0]


async def test_trace_owner_isolation_and_unknown_tokens(settings):
    configured = settings.model_copy(
        update={"auth_mode": "token", "api_tokens": {"alice": "token-a", "bob": "token-b"}}
    )
    app = create_app(settings=configured, model=SpyChatModel())
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/chat",
                headers={"Authorization": "Bearer token-a"},
                json={"message": "synthetic"},
            )
            assert response.status_code == 200
            trace_id = response.json()["trace_id"]
            trace = (
                await client.get(
                    f"/api/traces/{trace_id}", headers={"Authorization": "Bearer token-a"}
                )
            ).json()
            assert trace["token_usage"]["total_tokens"] is None
            assert trace["token_usage"]["complete"] is False
            assert (
                await client.get(
                    f"/api/traces/{trace_id}", headers={"Authorization": "Bearer token-b"}
                )
            ).status_code == 404
            assert (
                await client.get("/api/traces", headers={"Authorization": "Bearer token-b"})
            ).json()["traces"] == []
            assert (await client.get("/api/traces")).status_code == 401


async def test_tool_trace_omits_arguments_and_results(settings):
    model = ToolChatModel(
        tool_name="add_diet_record",
        arguments={
            "record": {
                "food_name": "PRIVATE_FOOD",
                "amount": "PRIVATE_AMOUNT",
                "meal_type": "lunch",
                "timestamp": "2026-10-03T04:00:00Z",
            }
        },
    )
    app = create_app(settings=settings, model=model)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/chat", json={"message": "PRIVATE_HEALTH"})
            assert response.status_code == 200
            trace = (await client.get("/api/traces/" + response.json()["trace_id"])).json()
            assert trace["tool_calls"] >= 1
            assert any(event["event"] == "tool.started" for event in trace["events"])
            assert "PRIVATE_" not in json.dumps(trace)


async def test_failure_resume_and_cached_replay_have_separate_honest_traces(settings):
    model = SpyChatModel(failure=RuntimeError("PRIVATE_EXCEPTION"))
    app = create_app(settings=settings, model=model)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            request_id = str(uuid4())
            body = {"message": "PRIVATE_HEALTH", "request_id": request_id}
            failed = await client.post("/api/chat", json=body)
            assert failed.status_code == 500
            error = failed.json()["error"]
            failed_trace = (await client.get("/api/traces/" + error["trace_id"])).json()
            assert failed_trace["status"] == "failed"
            assert failed_trace["termination_reason"] == "internal_error"
            assert "PRIVATE_" not in json.dumps(failed_trace)
            model.failure = None
            resumed = await client.post(
                f"/api/threads/{error['thread_id']}/resume", json={"request_id": request_id}
            )
            assert resumed.status_code == 200
            resumed_trace = (await client.get("/api/traces/" + resumed.json()["trace_id"])).json()
            assert resumed_trace["task_kind"] == "resume"
            assert resumed_trace["request_id"] == request_id
            replay = await client.post("/api/chat", json=body)
            cached_trace = (await client.get("/api/traces/" + replay.json()["trace_id"])).json()
            assert cached_trace["task_kind"] == "cached"
            assert cached_trace["model_calls"] == cached_trace["tool_calls"] == 0
            assert cached_trace["status"] == "completed"


async def test_cancelled_execution_is_persisted_and_stream_trace_is_completed(settings):
    model = SpyChatModel(delay=2)
    app = create_app(settings=settings, model=model)
    async with app.router.lifespan_context(app):
        thread = await app.state.threads.create(settings.local_user_id)
        context = RunContext.create(settings, str(uuid4()), thread_id=thread["thread_id"])
        pending = asyncio.create_task(app.state.runtime.ainvoke("PRIVATE", context))
        for _ in range(100):
            if model._contexts:
                break
            await asyncio.sleep(0.01)
        assert model._contexts
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        trace = await app.state.traces.get(context.user_id, context.trace_id)
        assert trace["status"] == "cancelled"
        assert trace["termination_reason"] == "cancelled"
        model.delay = 0
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/chat/stream", json={"message": "synthetic stream"})
            assert "event: run.completed" in response.text
            trace = (await client.get("/api/traces/" + response.headers["X-Trace-ID"])).json()
            assert trace["status"] == "completed"
            assert trace["model_calls"] == 1


async def test_trace_storage_failure_prevents_untraceable_execution(settings, monkeypatch):
    model = SpyChatModel()
    app = create_app(settings=settings, model=model)
    async with app.router.lifespan_context(app):

        async def broken(*args, **kwargs):
            raise RuntimeError("PRIVATE_STORAGE_DETAIL")

        monkeypatch.setattr(app.state.traces, "start", broken)
        with pytest.raises(AgentError) as info:
            await app.state.runtime.ainvoke("PRIVATE", RunContext.create(settings, str(uuid4())))
        assert info.value.code == "trace_unavailable"
        assert "PRIVATE" not in str(info.value)
        assert model._seen == []


async def test_terminal_trace_write_failure_does_not_return_success(settings, monkeypatch):
    app = create_app(settings=settings, model=SpyChatModel())
    async with app.router.lifespan_context(app):
        original = app.state.traces.finish

        async def broken(*args, **kwargs):
            raise RuntimeError("PRIVATE_STORAGE_ERROR")

        monkeypatch.setattr(app.state.traces, "finish", broken)
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            request_id = str(uuid4())
            failed = await client.post(
                "/api/chat", json={"message": "PRIVATE", "request_id": request_id}
            )
            assert failed.status_code == 503
            error = failed.json()["error"]
            assert error["code"] == "trace_unavailable"
            trace = (await client.get("/api/traces/" + error["trace_id"])).json()
            assert trace["status"] == "running"
            assert trace["capture_complete"] is False
            monkeypatch.setattr(app.state.traces, "finish", original)
            recovered = await client.post(
                f"/api/threads/{error['thread_id']}/resume", json={"request_id": request_id}
            )
            assert recovered.status_code == 200
            assert (await client.get("/api/traces/" + recovered.json()["trace_id"])).json()[
                "task_kind"
            ] == "cached"


async def test_closing_a_stream_persists_cancellation_without_final_success(settings):
    app = create_app(settings=settings, model=StreamingModel(delay=0.03))
    async with app.router.lifespan_context(app):
        thread = await app.state.threads.create(settings.local_user_id)
        context = RunContext.create(settings, str(uuid4()), thread_id=thread["thread_id"])
        stream = app.state.runtime.astream("PRIVATE_STREAM_INPUT", context)
        event = await anext(stream)
        assert event["event"] == "message.delta"
        await stream.aclose()
        trace = await app.state.traces.get(context.user_id, context.trace_id)
        assert trace["status"] == "cancelled"
        assert trace["termination_reason"] == "cancelled"
        assert "PRIVATE_STREAM_INPUT" not in json.dumps(trace)


async def test_real_delegation_callback_and_domain_events_are_not_double_counted(settings):
    app = create_app(
        settings=settings.model_copy(update={"max_steps": 30}), model=DelegatingModel()
    )
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/chat", json={"message": "PRIVATE_ROOT_TASK"})
            assert response.status_code == 200
            trace = (await client.get("/api/traces/" + response.json()["trace_id"])).json()
            assert trace["subagent_calls"] == 1
            assert trace["model_calls"] == 4
            assert trace["tool_calls"] == 2
            started = [event for event in trace["events"] if event["event"] == "delegation.started"]
            finished = [
                event for event in trace["events"] if event["event"] == "delegation.finished"
            ]
            assert len(started) == len(finished) == 1
            assert started[0]["delegation_id"] == finished[0]["delegation_id"]
            assert started[0]["agent_name"] == "record"
            model_agents = {
                event["agent_name"]
                for event in trace["events"]
                if event["event"] == "model.started"
            }
            assert model_agents == {"health_lead_agent", "record_agent"}
            assert "PRIVATE_ROOT_TASK" not in json.dumps(trace)


async def test_real_tool_retries_are_distinct_from_model_calls_and_do_not_log_exceptions(settings):
    calls = 0

    @tool
    async def query_health_metrics() -> dict:
        """Read synthetic records with one transient failure."""
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError("PRIVATE_UPSTREAM_ERROR")
        return ToolResult.ok({"records": []}).model_dump()

    configured = settings.model_copy(
        update={"subagents_enabled": False, "tool_retry_initial_delay": 0}
    )
    async with database_session(settings.data_dir) as sessions:
        repository = TraceRepository(sessions)
        await repository.initialize()
        graph = build_lead_agent(
            ToolChatModel(tool_name="query_health_metrics", arguments={}),
            tools=[query_health_metrics],
            settings=configured,
        )
        runtime = HealthAgentRuntime(graph, configured, repository)
        context = RunContext.create(configured, str(uuid4()))
        answer = await runtime.ainvoke("PRIVATE_INPUT", context)
        assert json.loads(answer)["success"] is True
        trace = await repository.get(context.user_id, context.trace_id)
        assert trace["tool_retries"] == 1
        assert trace["model_retries"] == 0
        assert trace["tool_calls"] == calls == 2
        assert trace["model_calls"] == 2
        assert "PRIVATE_" not in json.dumps(trace)


async def test_tool_timeout_trace_does_not_claim_missing_callbacks_were_captured(settings):
    cancelled = asyncio.Event()

    @tool
    async def query_health_metrics() -> dict:
        """Wait until the synthetic timeout cancels this read."""
        try:
            await asyncio.sleep(1)
        finally:
            cancelled.set()
        return ToolResult.ok({"records": []}).model_dump()

    configured = settings.model_copy(
        update={
            "subagents_enabled": False,
            "tool_timeout_seconds": 0.05,
            "tool_max_retries": 0,
            "tool_retry_initial_delay": 0,
        }
    )
    async with database_session(settings.data_dir) as sessions:
        repository = TraceRepository(sessions)
        await repository.initialize()
        graph = build_lead_agent(
            ToolChatModel(tool_name="query_health_metrics", arguments={}),
            tools=[query_health_metrics],
            settings=configured,
        )
        runtime = HealthAgentRuntime(graph, configured, repository)
        context = RunContext.create(configured, str(uuid4()))
        answer = json.loads(await runtime.ainvoke("Synthetic read timeout", context))
        assert cancelled.is_set()
        assert answer["success"] is False and answer["error_code"] == "tool_timeout"
        trace = await repository.get(context.user_id, context.trace_id)
        started = {
            event["step_id"] for event in trace["events"] if event["event"] == "tool.started"
        }
        finished = {
            event["step_id"] for event in trace["events"] if event["event"] == "tool.finished"
        }
        assert started
        assert trace["status"] == "completed"  # Final answer can explain the failure.
        assert trace["dropped_events"] == 0
        assert trace["capture_complete"] is (started == finished)


class PrivateDraftModel(DelegatingModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if isinstance(messages[-1], ToolMessage):
            context = get_runtime().context
            answer = "PRIVATE_CHILD_DRAFT" if context.delegation_depth else "PUBLIC_LEAD_ANSWER"
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=answer))])
        return super()._generate(messages, stop, run_manager, **kwargs)


async def test_streaming_subagent_drafts_do_not_appear_as_lead_deltas(settings):
    app = create_app(
        settings=settings.model_copy(update={"max_steps": 30}), model=PrivateDraftModel()
    )
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/chat/stream", json={"message": "synthetic delegated stream"}
            )
            assert response.status_code == 200
            events = SSEDecoder().feed(response.content)
            assert events[-1]["event"] == "run.completed"
            assert events[-1]["data"]["answer"] == "PUBLIC_LEAD_ANSWER"
            assert "PRIVATE_CHILD_DRAFT" not in response.text
            assert (
                "".join(
                    event["data"]["text"] for event in events if event["event"] == "message.delta"
                )
                == "PUBLIC_LEAD_ANSWER"
            )
