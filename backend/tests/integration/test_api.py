import asyncio
from uuid import UUID

import httpx
import pytest

from app.main import create_app
from tests.fakes import SpyChatModel
from tests.unit.test_runtime import provider_error


async def test_api_health_openapi_and_chat(settings):
    model = SpyChatModel()
    app = create_app(settings=settings, model=model)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            health = await client.get("/healthz")
            assert health.json() == {"status": "ok", "phase": 12, "model_mode": "fake"}
            assert model._seen == []
            schema = (await client.get("/openapi.json")).json()
            assert {"/healthz", "/api/chat", "/api/threads"} <= set(schema["paths"])
            assert schema["components"]["schemas"]["ChatRequest"]["additionalProperties"] is False
            assert "ErrorResponse" in str(schema["paths"]["/api/chat"]["post"]["responses"]["422"])
            response = await client.post(
                "/api/chat", json={"message": "你好"}, headers={"X-Trace-ID": "forged"}
            )
            assert response.status_code == 200
            body = response.json()
            assert body["answer"] == "收到：你好"
            assert body["model_mode"] == "fake"
            assert body["termination_reason"] == "completed"
            UUID(body["run_id"])
            UUID(body["trace_id"])
            assert body["trace_id"] == response.headers["X-Trace-ID"]
            assert response.headers["Cache-Control"] == "no-store"
    assert app.state.runtime is None


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"message": "   "},
        {"message": 123},
        {"message": "private", "user_id": "victim"},
        {"message": "private", "thread_id": "other"},
        {"message": "private", "config": {}},
        {"message": "a" * 8001},
        {"message": "a" * 32_001},
    ],
)
async def test_bad_request_does_not_reach_model_or_echo_input(settings, payload):
    model = SpyChatModel()
    app = create_app(settings=settings, model=model)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/chat", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert "private" not in response.text
    assert "victim" not in response.text
    assert model._seen == []


async def test_malformed_json_and_missing_route(settings):
    app = create_app(settings=settings, model=SpyChatModel())
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/chat", content='{"private":', headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 422
            assert "private" not in response.text
            missing = await client.get("/not-found")
            assert missing.status_code == 404
            assert missing.json()["error"]["trace_id"] == missing.headers["X-Trace-ID"]


async def test_parallel_and_sequential_requests_have_no_history(settings):
    model = SpyChatModel(delay=0.01)
    app = create_app(settings=settings, model=model)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            responses = await asyncio.gather(
                *[
                    client.post("/api/chat", json={"message": name})
                    for name in ("alpha", "beta", "gamma")
                ]
            )
            responses.append(await client.post("/api/chat", json={"message": "delta"}))
    assert [r.json()["answer"] for r in responses] == [
        f"收到：{x}" for x in ("alpha", "beta", "gamma", "delta")
    ]
    assert len({r.json()["run_id"] for r in responses}) == 4
    assert len({r.json()["trace_id"] for r in responses}) == 4
    assert all(len(messages) == 2 for messages in model._seen)
    assert all(context.user_id == "local-user" for context in model._contexts)


async def test_provider_failure_is_a_safe_http_error(settings, caplog):
    app = create_app(settings=settings, model=SpyChatModel(failure=provider_error(401)))
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/chat", json={"message": "private-health"})
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "provider_error"
    assert "FAKE" not in response.text
    assert "LEAK" not in response.text + caplog.text
    assert "private-health" not in response.text + caplog.text


async def test_real_demo_adapter_is_labelled_and_stateless(settings):
    app = create_app(settings=settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/api/chat", json={"message": "启动验证"})
    assert response.status_code == 200
    assert "[FAKE 演示模式]" in response.json()["answer"]
    assert "启动验证" in response.json()["answer"]
