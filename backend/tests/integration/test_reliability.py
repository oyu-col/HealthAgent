import asyncio
import json
from dataclasses import replace
from uuid import uuid4

import httpx
import pytest
from langchain.tools import tool

from app.agent.context import RunContext
from app.agent.errors import AgentError
from app.agent.runtime import HealthAgentRuntime
from app.agents.lead_agent import build_lead_agent
from app.api.sse import SSEDecoder
from app.domain.schemas import ToolResult
from app.main import create_app
from tests.fakes import SpyChatModel, ToolChatModel
from tests.unit.test_runtime import provider_error


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError("SECRET"),
        provider_error(429),
        provider_error(503),
        httpx.ReadError("SECRET connection reset"),
    ],
)
async def test_read_transient_retry_is_bounded_and_observable(settings, error):
    calls = 0

    @tool
    async def query_health_metrics() -> dict:
        """Read synthetic test records."""
        nonlocal calls
        calls += 1
        if calls <= 2:
            raise error
        return ToolResult.ok({"records": []}).model_dump()

    settings = settings.model_copy(
        update={"tool_retry_initial_delay": 0, "subagents_enabled": False}
    )
    model = ToolChatModel(tool_name="query_health_metrics", arguments={})
    graph = build_lead_agent(model, tools=[query_health_metrics], settings=settings)
    context = RunContext.create(settings, "read-retry")
    events = []
    context = replace(context, event_sink=lambda name, data: events.append((name, data)))
    answer = await HealthAgentRuntime(graph, settings).ainvoke("合成", context)
    assert json.loads(answer)["success"] is True
    assert calls == 3 and context.budget.tool_calls == 3 and context.budget.retries == 2
    assert len([event for event in events if event[0] == "tool.retry"]) == 2
    assert "SECRET" not in str(events)


async def test_write_timeout_is_not_replayed(settings):
    calls = 0

    @tool
    async def add_health_metric() -> dict:
        """Write synthetic data with an ambiguous commit."""
        nonlocal calls
        calls += 1
        raise TimeoutError("SECRET")

    model = ToolChatModel(tool_name="add_health_metric", arguments={})
    graph = build_lead_agent(model, tools=[add_health_metric], settings=settings)
    answer = await HealthAgentRuntime(graph, settings).ainvoke(
        "合成", RunContext.create(settings, "write")
    )
    result = json.loads(answer)
    assert calls == 1 and result["error_code"] == "write_outcome_unknown"
    assert result["retryable"] is False and "SECRET" not in answer


async def test_missing_tool_arguments_do_not_execute_or_retry(settings):
    calls = 0

    @tool
    async def query_health_metrics(required_limit: int) -> dict:
        """Read synthetic test records with a required input."""
        nonlocal calls
        calls += 1
        return ToolResult.ok([]).model_dump()

    context = RunContext.create(settings, "validation")
    graph = build_lead_agent(
        ToolChatModel(tool_name="query_health_metrics", arguments={}),
        tools=[query_health_metrics],
        settings=settings,
    )
    answer = await HealthAgentRuntime(graph, settings).ainvoke("合成", context)
    assert json.loads(answer)["error_code"] == "validation_error"
    assert calls == 0 and context.budget.retries == 0


async def test_shared_budget_caps_physical_retry_attempts(settings):
    calls = 0

    @tool
    async def query_health_metrics() -> dict:
        """Read synthetic data."""
        nonlocal calls
        calls += 1
        raise TimeoutError("SECRET")

    settings = settings.model_copy(update={"max_tool_calls": 2, "tool_retry_initial_delay": 0})
    graph = build_lead_agent(
        ToolChatModel(tool_name="query_health_metrics", arguments={}),
        tools=[query_health_metrics],
        settings=settings,
    )
    with pytest.raises(AgentError) as caught:
        await HealthAgentRuntime(graph, settings).ainvoke(
            "合成", RunContext.create(settings, "budget")
        )
    assert caught.value.code == "tool_limit" and calls == 2


async def test_explicit_urgent_request_short_circuits_model(settings):
    model = SpyChatModel()
    graph = build_lead_agent(model, settings=settings)
    result = await HealthAgentRuntime(graph, settings).ainvoke(
        "我现在胸痛并且呼吸困难", RunContext.create(settings, "safety")
    )
    assert "急救" in result and model._seen == []
    await HealthAgentRuntime(graph, settings).ainvoke(
        "我现在没有胸痛，我想了解健康记录", RunContext.create(settings, "negative")
    )
    assert len(model._seen) == 1


@pytest.mark.parametrize("error", [ValueError("SECRET"), provider_error(401)])
async def test_permanent_read_failures_are_not_retried(settings, error):
    calls = 0

    @tool
    async def query_health_metrics() -> dict:
        """Read test records."""
        nonlocal calls
        calls += 1
        raise error

    graph = build_lead_agent(
        ToolChatModel(tool_name="query_health_metrics", arguments={}),
        tools=[query_health_metrics],
        settings=settings,
    )
    answer = await HealthAgentRuntime(graph, settings).ainvoke(
        "合成", RunContext.create(settings, "permanent")
    )
    assert calls == 1
    assert json.loads(answer)["retryable"] is False and "SECRET" not in answer


async def test_tool_timeout_cancels_each_read_and_stops_after_configured_retries(settings):
    calls = 0
    cancelled = 0

    @tool
    async def query_health_metrics() -> dict:
        """Read deliberately slow synthetic records."""
        nonlocal calls, cancelled
        calls += 1
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            cancelled += 1
            raise
        return ToolResult.ok([]).model_dump()

    settings = settings.model_copy(
        update={"tool_timeout_seconds": 0.01, "tool_max_retries": 1, "tool_retry_initial_delay": 0}
    )
    graph = build_lead_agent(
        ToolChatModel(tool_name="query_health_metrics", arguments={}),
        tools=[query_health_metrics],
        settings=settings,
    )
    answer = await HealthAgentRuntime(graph, settings).ainvoke(
        "合成", RunContext.create(settings, "timeout")
    )
    assert calls == cancelled == 2
    assert json.loads(answer)["error_code"] == "tool_timeout"


async def test_real_retrieval_retries_injected_embedding_transient_failure(settings):
    settings = settings.model_copy(update={"tool_retry_initial_delay": 0})
    model = ToolChatModel(tool_name="search_health_knowledge", arguments={"query": "合成睡眠资料"})
    app = create_app(settings=settings, model=model)
    async with app.router.lifespan_context(app):
        document = await app.state.knowledge.ingest(
            "local-user", "synthetic.txt", "合成睡眠资料，仅用于测试".encode()
        )
        original_embedding = app.state.knowledge.embedding

        class TransientEmbedding:
            calls = 0

            async def aembed_query(self, query):
                self.calls += 1
                if self.calls == 1:
                    raise httpx.ConnectError(
                        "SECRET upstream", request=httpx.Request("POST", "https://example.invalid")
                    )
                return await original_embedding.aembed_query(query)

        embedding = TransientEmbedding()
        app.state.knowledge.embedding = embedding
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/chat", json={"message": "检索合成睡眠资料"})
            assert response.status_code == 200 and "SECRET" not in response.text
            result = json.loads(response.json()["answer"])
            assert result["success"] is True
            assert result["data"]["citations"][0]["document_id"] == document["id"]
        assert embedding.calls == 2 and model._contexts[-1].budget.retries == 1


async def test_urgent_guardrail_stream_checkpoint_and_replay_agree(settings):
    model = SpyChatModel()
    app = create_app(settings=settings, model=model)
    request_id = str(uuid4())
    message = "我现在胸痛并且呼吸困难"
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            streamed = await client.post(
                "/api/chat/stream", json={"message": message, "request_id": request_id}
            )
            events = SSEDecoder().feed(streamed.content)
            completed = events[-1]
            assert completed["event"] == "run.completed"
            answer = completed["data"]["answer"]
            assert "急救" in answer and "不能进行诊断" in answer
            thread_id = completed["data"]["thread_id"]
            replay = await client.post(
                "/api/chat",
                json={"message": message, "request_id": request_id, "thread_id": thread_id},
            )
            assert replay.json()["answer"] == answer
            state = (await client.get(f"/api/threads/{thread_id}")).json()
            assert state["messages"] == [
                {"role": "user", "content": message},
                {"role": "assistant", "content": answer},
            ]
            assert state["status"] == "idle" and state["can_resume"] is False
    assert model._seen == []
