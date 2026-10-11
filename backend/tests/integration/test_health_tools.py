import asyncio
import json

import httpx
import pytest
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import ValidationError

from app.domain.schemas import DietInput, ExerciseInput, MetricInput, QueryInput
from app.main import create_app
from tests.fakes import ToolChatModel


class RepeatingToolModel(ToolChatModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self._seen.append(messages)
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": self.tool_name,
                                "args": self.arguments,
                                "id": f"call-{len(self._seen)}",
                            }
                        ],
                    )
                )
            ]
        )


async def test_repeat_observations_stop_without_unbounded_tool_calls(settings):
    model = RepeatingToolModel(tool_name="query_health_metrics", arguments={})
    app = create_app(settings=settings.model_copy(update={"max_steps": 50}), model=model)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/chat", json={"message": "合成循环测试"})
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "no_progress"
    assert len(model._seen) == 3


async def test_agent_tool_database_observation_answer(settings):
    model = ToolChatModel(
        tool_name="add_health_metric",
        arguments={
            "record": {
                "metric_type": "weight",
                "value": 70,
                "unit": "kg",
                "measured_at": "2026-10-03T08:00:00+08:00",
            }
        },
    )
    app = create_app(settings=settings, model=model)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/chat", json={"message": "记录合成体重 70kg"})
        assert response.status_code == 200
        result = json.loads(response.json()["answer"])
        assert result["success"] is True
        rows = await app.state.health.query("metric", "local-user", QueryInput())
        assert rows.data["records"][0]["value"] == 70
        assert rows.data["records"][0]["measured_at"] == "2026-10-03T00:00:00Z"
        assert len(model._seen) == 2
        assert "user_id" not in str(model._schemas)


async def test_idempotent_writes_and_owner_filter(settings):
    app = create_app(settings=settings)
    async with app.router.lifespan_context(app):
        data = MetricInput(metric_type="weight", value=70, unit="kg")
        first = await app.state.health.add("metric", "alice", data, "same-operation")
        second = await app.state.health.add("metric", "alice", data, "same-operation")
        assert first.data["id"] == second.data["id"]
        assert (await app.state.health.query("metric", "bob", QueryInput())).data["records"] == []
        assert (
            len((await app.state.health.query("metric", "alice", QueryInput())).data["records"])
            == 1
        )


@pytest.mark.parametrize(
    "values",
    [
        {"metric_type": "weight", "value": -1, "unit": "kg"},
        {"metric_type": "weight", "value": 70, "unit": "lb"},
        {"metric_type": "weight", "value": float("nan"), "unit": "kg"},
        {"metric_type": "steps", "value": 1.2, "unit": "count"},
        {"metric_type": "weight", "value": 70, "unit": "kg", "measured_at": "2026-01-01"},
    ],
)
def test_invalid_metric_rejected(values):
    with pytest.raises(ValidationError):
        MetricInput(**values)


async def test_invalid_tool_arguments_are_safe_structured_observation(settings):
    app = create_app(
        settings=settings,
        model=ToolChatModel(
            tool_name="add_health_metric",
            arguments={"record": {"metric_type": "weight", "value": -5, "unit": "SECRET"}},
        ),
    )
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/chat", json={"message": "测试无效参数"})
    result = json.loads(response.json()["answer"])
    assert result["error_code"] == "validation_error"
    assert result["retryable"] is False
    assert "SECRET" not in response.text


async def test_credentials_determine_identity(settings):
    settings = settings.model_copy(
        update={"auth_mode": "token", "api_tokens": {"alice": "a" * 32, "bob": "b" * 32}}
    )
    app = create_app(
        settings=settings, model=ToolChatModel(tool_name="query_health_metrics", arguments={})
    )
    async with app.router.lifespan_context(app):
        await app.state.health.add(
            "metric", "alice", MetricInput(metric_type="weight", value=70, unit="kg"), "a"
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (await client.post("/api/chat", json={"message": "查询"})).status_code == 401
            response = await client.post(
                "/api/chat",
                json={"message": "查询"},
                headers={"Authorization": "Bearer " + "b" * 32, "X-User-ID": "alice"},
            )
            assert json.loads(response.json()["answer"])["data"]["records"] == []


async def test_diet_exercise_trend_and_concurrent_deduplication(settings):
    app = create_app(settings=settings)
    async with app.router.lifespan_context(app):
        health = app.state.health
        food = await health.add(
            "diet",
            "alice",
            DietInput(food_name="合成燕麦", amount="50g", meal_type="breakfast"),
            "diet",
        )
        assert food.data["nutrition_info"] is None
        exercise = await health.add(
            "exercise",
            "alice",
            ExerciseInput(exercise_type="合成步行", duration=30, distance=2),
            "exercise",
        )
        assert exercise.data["duration"] == 30
        first = MetricInput(
            metric_type="weight", value=70, unit="kg", measured_at="2026-10-01T08:00:00+08:00"
        )
        second = MetricInput(
            metric_type="weight", value=69, unit="kg", measured_at="2026-10-02T08:00:00+08:00"
        )
        await asyncio.gather(*[health.add("metric", "alice", first, "first") for _ in range(4)])
        conflict = await health.add("metric", "alice", second, "first")
        assert conflict.error_code == "idempotency_conflict"
        await health.add("metric", "alice", second, "second")
        trend = await health.trend("alice", "weight", QueryInput())
        assert trend.data["count"] == 2 and trend.data["change"] == -1
        assert (await health.trend("bob", "weight", QueryInput())).error_code == "insufficient_data"
