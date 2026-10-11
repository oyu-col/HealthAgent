import asyncio
import json
from dataclasses import replace

import httpx
import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.runtime import get_runtime
from pydantic import PrivateAttr

from app.agent.context import RunContext
from app.agent.errors import AgentError
from app.agents.subagents import SpecialistPool
from app.domain.schemas import MetricInput
from app.main import create_app
from tests.fakes import SpyChatModel


class DelegatingModel(SpyChatModel):
    role: str = "record"
    forbidden_tool: str | None = None
    _roles: list[str] = PrivateAttr(default_factory=list)
    _tool_sets: list[set[str]] = PrivateAttr(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        self._tool_sets.append({tool.name for tool in tools})
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self._seen.append(messages)
        context = get_runtime().context
        self._roles.append(context.agent_name)
        if isinstance(messages[-1], ToolMessage):
            answer = (
                messages[-1].content
                if context.delegation_depth == 0
                else "已根据工具观测完成合成分析，资料不足时不推断。"
            )
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=answer))])
        if context.delegation_depth == 0:
            name = "delegate_health_task"
            args = {"agent": self.role, "task": "查询当前用户的合成健康数据并概述"}
        else:
            name = (
                self.forbidden_tool
                or {
                    "record": "query_health_metrics",
                    "nutrition": "query_diet_records",
                    "research": "search_health_knowledge",
                }[self.role]
            )
            args = {"query": "合成健康资料"} if name == "search_health_knowledge" else {}
            if name == "add_health_metric":
                args = {"record": {"metric_type": "weight", "value": 99, "unit": "kg"}}
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(
                        content="",
                        tool_calls=[
                            {"name": name, "args": args, "id": context.agent_name + "-call"}
                        ],
                    )
                )
            ]
        )


@pytest.mark.parametrize("role", ["record", "nutrition", "research"])
async def test_lead_delegates_to_scoped_specialist_and_aggregates(settings, role):
    model = DelegatingModel(role=role)
    settings = settings.model_copy(update={"max_steps": 30})
    app = create_app(settings=settings, model=model)
    async with app.router.lifespan_context(app):
        await app.state.health.add(
            "metric", "another-user", MetricInput(metric_type="weight", value=99, unit="kg"), "seed"
        )
        await app.state.knowledge.ingest(
            "another-user", "secret.txt", "其他用户合成健康资料".encode()
        )
        own_document = await app.state.knowledge.ingest(
            "local-user", "own.txt", "当前用户合成健康资料，仅用于测试".encode()
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/chat", json={"message": "请进行多步综合分析，私有上下文标记"}
            )
            state = (await client.get("/api/threads/" + response.json()["thread_id"])).json()
            assert len(state["messages"]) == 2
            assert state["messages"][0]["content"] == "请进行多步综合分析，私有上下文标记"
    assert response.status_code == 200
    result = json.loads(response.json()["answer"])
    assert result["success"] is True
    report = result["data"]
    assert report["agent"] == role and report["status"] == "completed"
    assert report["observations"] and report["observations"][0]["success"] is True
    if role == "record":
        assert report["observations"][0]["data"]["records"] == []
    elif role == "research":
        assert {item["document_id"] for item in report["observations"][0]["data"]["citations"]} == {
            own_document["id"]
        }
    assert "another-user" not in response.text and '"value":99' not in response.text
    child_messages = [
        messages
        for messages, agent in zip(model._seen, model._roles, strict=True)
        if agent != "health_lead_agent"
    ]
    assert all("私有上下文标记" not in str(messages) for messages in child_messages)
    child_contexts = [context for context in model._contexts if context.delegation_depth]
    assert child_contexts and all(context.user_id == "local-user" for context in child_contexts)
    assert child_contexts[0].budget is model._contexts[0].budget
    assert all("delegate_health_task" not in names for names in model._tool_sets[1:-1])


async def test_specialists_cannot_write_or_delegate_recursively(settings):
    model = DelegatingModel(forbidden_tool="add_health_metric")
    app = create_app(settings=settings.model_copy(update={"max_steps": 30}), model=model)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/chat", json={"message": "合成越界委派测试"})
            assert response.status_code == 200
            report = json.loads(response.json()["answer"])["data"]
            assert report["observations"][0]["success"] is False
            assert (await client.get("/api/records/metric")).json()["data"]["records"] == []
        context = replace(RunContext.create(settings, "recursive"), delegation_depth=1)
        result = await SpecialistPool(model, [], settings).run("record", "递归", context)
        assert result.error_code == "delegation_forbidden"


async def test_delegation_uses_shared_tool_budget(settings):
    app = create_app(
        settings=settings.model_copy(update={"max_tool_calls": 1, "max_steps": 30}),
        model=DelegatingModel(),
    )
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/chat", json={"message": "合成共享预算测试"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "tool_limit"


class ConcurrencyModel(SpyChatModel):
    _active_count: int = PrivateAttr(default=0)
    _peak: int = PrivateAttr(default=0)

    async def _agenerate(self, messages, **kwargs):
        self._active_count += 1
        self._peak = max(self._peak, self._active_count)
        try:
            return await super()._agenerate(messages, **kwargs)
        finally:
            self._active_count -= 1


async def test_subagent_capacity_timeout_and_cancel_release(settings):
    settings = settings.model_copy(
        update={"subagent_max_concurrency": 2, "subagent_timeout_seconds": 2}
    )
    model = ConcurrencyModel(delay=0.04)
    pool = SpecialistPool(model, [], settings)
    context = RunContext.create(settings, "capacity")
    results = await asyncio.gather(
        *[pool.run(role, "合成", context) for role in ("record", "nutrition", "research")]
    )
    assert all(result.success for result in results)
    assert model._peak == 2
    timeout_settings = settings.model_copy(update={"subagent_timeout_seconds": 0.01})
    timeout_pool = SpecialistPool(SpyChatModel(delay=1), [], timeout_settings)
    result = await timeout_pool.run(
        "record", "合成", RunContext.create(timeout_settings, "timeout")
    )
    assert result.error_code == "subagent_timeout"
    running = asyncio.create_task(pool.run("record", "合成", RunContext.create(settings, "cancel")))
    await asyncio.sleep(0)
    running.cancel()
    with pytest.raises(asyncio.CancelledError):
        await running
    assert (await pool.run("record", "合成", RunContext.create(settings, "after-cancel"))).success


async def test_shared_model_and_delegation_budget_cannot_reset_in_child_graph(settings):
    model = SpyChatModel()
    pool = SpecialistPool(model, [], settings)
    context = RunContext.create(settings, "shared-model")
    context.budget.max_model_calls = 1
    assert (await pool.run("record", "合成", context)).success
    with pytest.raises(AgentError) as model_limit:
        await pool.run("research", "合成", context)
    assert model_limit.value.code == "step_limit" and len(model._seen) == 1
    context = RunContext.create(
        settings.model_copy(update={"max_delegations": 1}), "shared-delegation"
    )
    assert (await pool.run("record", "合成", context)).success
    with pytest.raises(AgentError) as delegation_limit:
        await pool.run("nutrition", "合成", context)
    assert delegation_limit.value.code == "delegation_limit" and len(model._seen) == 2
