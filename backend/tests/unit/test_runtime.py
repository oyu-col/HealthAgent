import asyncio
import logging

import httpx
import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from openai import APIConnectionError, APIError, APIStatusError, APITimeoutError
from typing_extensions import TypedDict

from app.agent.context import RunContext
from app.agent.errors import AgentError
from app.agent.runtime import HealthAgentRuntime, extract_answer
from app.agents.lead_agent import build_lead_agent
from app.agents.prompts import HEALTH_SYSTEM_PROMPT
from app.config import Settings
from tests.fakes import SpyChatModel


async def test_real_graph_and_trusted_context(settings):
    model = SpyChatModel()
    graph = build_lead_agent(model)
    context = RunContext.create(settings, "test-trace")
    runtime = HealthAgentRuntime(graph, settings)
    assert await runtime.ainvoke("我想了解健康记录", context) == "收到：我想了解健康记录"
    assert len(model._seen) == 1
    assert isinstance(model._seen[0][0], SystemMessage)
    assert model._seen[0][0].content == HEALTH_SYSTEM_PROMPT
    assert isinstance(model._seen[0][-1], HumanMessage)
    assert model._contexts == [context]
    assert graph.checkpointer is None


@pytest.mark.parametrize(
    "content, expected",
    [
        ("  正常回答  ", "正常回答"),
        (
            [
                {"type": "text", "text": "第一段"},
                {"type": "reasoning", "reasoning": "HIDDEN"},
                {"type": "text", "text": "第二段"},
            ],
            "第一段第二段",
        ),
        (["文本", {"type": "image_url", "image_url": "HIDDEN"}], "文本"),
    ],
)
def test_visible_answer_only(content, expected):
    assert extract_answer({"messages": [AIMessage(content=content)]}) == expected


@pytest.mark.parametrize(
    "state",
    [
        None,
        {},
        {"messages": []},
        {"messages": [HumanMessage(content="private")]},
        {"messages": [AIMessage(content=" ")]},
        {"messages": [AIMessage(content=[{"type": "reasoning", "reasoning": "private"}])]},
        {"messages": [AIMessage(content="old"), HumanMessage(content="latest")]},
        {"messages": [AIMessage(content="partial", response_metadata={"finish_reason": "length"})]},
        {
            "messages": [
                AIMessage(content="x", tool_calls=[{"name": "write", "args": {}, "id": "t"}])
            ]
        },
    ],
)
def test_reject_nonfinal_or_hidden_only_result(state):
    with pytest.raises(AgentError, match="完整回答"):
        extract_answer(state)


def provider_error(kind):
    request = httpx.Request("POST", "https://example.invalid/v1/chat/completions")
    if kind == "timeout":
        return APITimeoutError(request=request)
    if kind == "connection":
        return APIConnectionError(message="LEAK-secret", request=request)
    if kind == "protocol":
        return APIError("LEAK-secret", request=request, body=None)
    if isinstance(kind, int):
        return APIStatusError(
            "LEAK-secret", response=httpx.Response(kind, request=request), body={"health": "LEAK"}
        )
    return RuntimeError("LEAK-secret")


@pytest.mark.parametrize(
    "kind, code, status",
    [
        ("timeout", "timeout", 504),
        ("connection", "provider_unavailable", 503),
        (429, "provider_unavailable", 503),
        (503, "provider_unavailable", 503),
        (401, "provider_error", 502),
        (400, "provider_error", 502),
        ("protocol", "provider_error", 502),
        ("unexpected", "internal_error", 500),
    ],
)
async def test_error_mapping_is_sanitized(settings, caplog, kind, code, status):
    model = SpyChatModel(failure=provider_error(kind))
    runtime = HealthAgentRuntime(build_lead_agent(model), settings)
    with caplog.at_level(logging.INFO, logger="health_agent.runtime"):
        with pytest.raises(AgentError) as info:
            await runtime.ainvoke("PRIVATE-HEALTH-TEXT", RunContext.create(settings, "trace"))
    assert info.value.code == code
    assert info.value.status_code == status
    assert "LEAK" not in str(info.value)
    assert "LEAK" not in caplog.text
    assert "PRIVATE-HEALTH-TEXT" not in caplog.text
    assert "trace_id=trace" in caplog.text
    assert len(model._seen) == 1  # No app-level retries or fake fallback.


async def test_total_timeout_cancels_model():
    settings = Settings(
        model_mode="fake",
        request_timeout_seconds=0.1,
        model_timeout_seconds=0.05,
        _env_file=None,
    )
    model = SpyChatModel(delay=5)
    runtime = HealthAgentRuntime(build_lead_agent(model), settings)
    with pytest.raises(AgentError) as info:
        await runtime.ainvoke("wait", RunContext.create(settings, "trace"))
    assert info.value.code == "timeout"
    assert model._cancelled


async def test_external_cancellation_is_not_an_error_answer(settings):
    model = SpyChatModel(delay=5)
    runtime = HealthAgentRuntime(build_lead_agent(model), settings)
    task = asyncio.create_task(runtime.ainvoke("wait", RunContext.create(settings, "trace")))
    for _ in range(100):
        if model._contexts:
            break
        await asyncio.sleep(0.01)
    assert model._contexts
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert model._cancelled


async def test_real_graph_step_budget(settings):
    class Counter(TypedDict):
        count: int

    graph = StateGraph(Counter)
    graph.add_node("increment", lambda state: {"count": state.get("count", 0) + 1})
    graph.add_edge(START, "increment")
    graph.add_conditional_edges(
        "increment", lambda state: "increment" if state["count"] < 99 else END
    )
    runtime = HealthAgentRuntime(graph.compile(), settings)
    with pytest.raises(AgentError) as info:
        await runtime.ainvoke("loop", RunContext.create(settings, "trace"))
    assert info.value.code == "step_limit"


async def test_runtime_rejects_input_before_model(settings):
    model = SpyChatModel()
    runtime = HealthAgentRuntime(build_lead_agent(model), settings)
    for message in (" ", "a" * (settings.max_input_chars + 1)):
        with pytest.raises(AgentError) as info:
            await runtime.ainvoke(message, RunContext.create(settings, "trace"))
        assert info.value.status_code == 422
    assert model._seen == []


async def test_unrelated_langsmith_env_cannot_upload_health_text(settings, monkeypatch):
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setenv("LANGSMITH_API_KEY", "not-a-real-key")
    model = SpyChatModel()
    runtime = HealthAgentRuntime(build_lead_agent(model), settings)
    await runtime.ainvoke("private-health", RunContext.create(settings, "trace"))
    assert model._tracing_flags == [False]
