import asyncio
from uuid import uuid4

import httpx
import pytest
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from app.main import create_app
from tests.fakes import SpyChatModel

RECORDS = {
    "metric": {"metric_type": "weight", "value": 70, "unit": "kg"},
    "diet": {"food_name": "合成燕麦", "amount": "50g", "meal_type": "breakfast"},
    "exercise": {"exercise_type": "合成步行", "duration": 30, "distance": 2},
}


@pytest.mark.parametrize("kind", RECORDS)
async def test_records_api_writes_idempotently_and_filters_owner(settings, kind):
    settings = settings.model_copy(
        update={"auth_mode": "token", "api_tokens": {"alice": "a" * 32, "bob": "b" * 32}}
    )
    app = create_app(settings=settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            path = f"/api/records/{kind}"
            assert (await client.get(path)).status_code == 401
            client.headers["Authorization"] = "Bearer " + "a" * 32
            body = {"record": RECORDS[kind], "request_id": str(uuid4())}
            first = await client.post(path, json=body)
            assert first.status_code == 200
            assert first.json()["success"] is True
            again = await client.post(path, json=body)
            assert again.json() == first.json()
            assert "user_id" not in first.json()["data"]
            records = (await client.get(path)).json()["data"]
            assert len(records["records"]) == 1 and records["truncated"] is False
            changed = {**RECORDS[kind]}
            changed[next(iter(changed))] = {
                "metric": "heart_rate",
                "diet": "合成米饭",
                "exercise": "合成跑步",
            }[kind]
            if kind == "metric":
                changed["unit"] = "bpm"
            conflict = await client.post(path, json={**body, "record": changed})
            assert conflict.status_code == 409
            assert conflict.json()["error"]["code"] == "idempotency_conflict"
            client.headers["Authorization"] = "Bearer " + "b" * 32
            client.headers["X-User-ID"] = "alice"
            assert (await client.get(path)).json()["data"]["records"] == []
            assert (await client.post(path, json=body)).status_code == 200
            assert (await client.get(path)).json()["data"]["records"][0]["id"] != first.json()[
                "data"
            ]["id"]


async def test_records_query_contract_and_strict_kind_validation(settings):
    app = create_app(settings=settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            for day in (1, 2, 3):
                await client.post(
                    "/api/records/metric",
                    json={
                        "record": {
                            **RECORDS["metric"],
                            "measured_at": f"2026-10-0{day}T08:00:00+08:00",
                        },
                        "request_id": str(uuid4()),
                    },
                )
            response = await client.get(
                "/api/records/metric",
                params={"start": "2026-10-02T00:00:00Z", "metric_type": "weight", "limit": 1},
            )
            assert response.status_code == 200
            assert response.json()["data"]["truncated"] is True
            assert response.json()["data"]["records"][0]["measured_at"] == "2026-10-03T00:00:00Z"
            for params in (
                {"start": "2026-10-01"},
                {"limit": 201},
                {"user_id": "SECRET"},
                {"start": "2026-10-03T00:00:00Z", "end": "2026-10-02T00:00:00Z"},
            ):
                invalid = await client.get("/api/records/metric", params=params)
                assert invalid.status_code == 422
                assert "SECRET" not in invalid.text
            for body in (
                {"record": RECORDS["diet"], "request_id": str(uuid4())},
                {"record": {**RECORDS["metric"], "user_id": "SECRET"}, "request_id": str(uuid4())},
                {"record": RECORDS["metric"], "request_id": "SECRET"},
                {"record": RECORDS["metric"], "request_id": str(uuid4()), "user_id": "SECRET"},
            ):
                invalid = await client.post("/api/records/metric", json=body)
                assert invalid.status_code == 422
                assert "SECRET" not in invalid.text
            assert (await client.post("/api/records/other", json={})).status_code == 422
            assert (
                await client.get("/api/records/diet", params={"metric_type": "weight"})
            ).status_code == 422


async def test_session_returns_only_authorized_capabilities(settings):
    settings = settings.model_copy(
        update={"auth_mode": "token", "api_tokens": {"alice": "a" * 32}, "memory_enabled": False}
    )
    app = create_app(settings=settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            assert (await client.get("/api/session")).status_code == 401
            response = await client.get(
                "/api/session", headers={"Authorization": "Bearer " + "a" * 32}
            )
            assert response.json() == {
                "user_id": "alice",
                "model_mode": "fake",
                "timezone": "Asia/Shanghai",
                "memory_enabled": False,
            }
            assert "a" * 32 not in response.text


async def test_ui_assets_are_optional_and_do_not_shadow_api(settings, tmp_path):
    dist = tmp_path / "ui"
    dist.mkdir()
    (dist / "assets").mkdir()
    (dist / "index.html").write_text("<html>HealthAgent test UI</html>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("window.test = true", encoding="utf-8")
    app = create_app(settings=settings, frontend_dist=dist)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            home = await client.get("/")
            assert home.status_code == 200 and "HealthAgent test UI" in home.text
            assert "text/html" in home.headers["content-type"]
            assert (await client.get("/assets/app.js")).text == "window.test = true"
            assert (await client.get("/healthz")).json()["phase"] == 12
            assert "swagger" in (await client.get("/docs")).text.lower()
            for path in (
                "/api/unknown",
                "/some-path",
                "/assets/missing.js",
                "/assets/%2e%2e/index.html",
            ):
                response = await client.get(path)
                assert response.status_code == 404
                assert "HealthAgent test UI" not in response.text
    absent = create_app(settings=settings, frontend_dist=tmp_path / "missing")
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=absent), base_url="http://test"
    ) as client:
        assert (await client.get("/")).status_code == 404


async def test_thread_metadata_title_and_recovery_when_checkpoint_is_finished(
    settings, monkeypatch
):
    model = SpyChatModel()
    app = create_app(settings=settings, model=model)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            empty = (await client.post("/api/threads")).json()
            assert empty["title"] == "新对话"
            assert empty["status"] == "idle" and empty["can_resume"] is False
            thread_id = empty["thread_id"]
            request_id = str(uuid4())
            original_complete = app.state.threads.complete

            async def fail_commit(*args, **kwargs):
                raise RuntimeError("synthetic failure after checkpoint")

            monkeypatch.setattr(app.state.threads, "complete", fail_commit)
            message = "合成标题\n\t测试\u202e " + "长" * 60
            failure = await client.post(
                "/api/chat",
                json={"message": message, "thread_id": thread_id, "request_id": request_id},
            )
            assert failure.status_code == 500
            state = (await client.get(f"/api/threads/{thread_id}")).json()
            assert state["pending"] is False
            assert state["status"] == "failed" and state["can_resume"] is True
            assert state["active_request_id"] == request_id
            assert state["title"].startswith("合成标题 测试 ")
            assert len(state["title"]) <= 48 and "\u202e" not in state["title"]
            summary = (await client.get("/api/threads")).json()["threads"][0]
            assert {key: state[key] for key in summary} == summary
            monkeypatch.setattr(app.state.threads, "complete", original_complete)
            recovered = await client.post(
                f"/api/threads/{thread_id}/resume", json={"request_id": request_id}
            )
            assert recovered.status_code == 200
            assert len(model._seen) == 1
            finished = (await client.get(f"/api/threads/{thread_id}")).json()
            assert finished["status"] == "idle" and finished["can_resume"] is False
            assert len(finished["messages"]) == 2
            await client.post("/api/chat", json={"message": "不同的问题", "thread_id": thread_id})
            assert (await client.get(f"/api/threads/{thread_id}")).json()["title"] == state["title"]


async def test_thread_metadata_distinguishes_running_and_interrupted_before_checkpoint(settings):
    app = create_app(settings=settings, model=SpyChatModel())
    async with app.router.lifespan_context(app):
        threads = app.state.threads
        request_id = str(uuid4())
        async with threads.prepare(
            user_id="local-user",
            trace_id=str(uuid4()),
            message="尚未进入图的合成请求",
            request_id=request_id,
        ) as prepared:
            thread_id = prepared.context.thread_id
            running = await threads.state("local-user", thread_id)
            assert running["status"] == "running" and running["can_resume"] is False
            assert running["pending"] is False and running["messages"] == []
        interrupted = await threads.state("local-user", thread_id)
        assert interrupted["status"] == "interrupted" and interrupted["can_resume"] is True
        assert interrupted["title"] == "尚未进入图的合成请求"
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resumed = await client.post(
                f"/api/threads/{thread_id}/resume", json={"request_id": request_id}
            )
            assert resumed.status_code == 200
            assert resumed.json()["answer"] == "收到：尚未进入图的合成请求"
        assert (await threads.state("local-user", thread_id))["status"] == "idle"


async def test_records_http_concurrent_retries_share_one_transaction_receipt(settings):
    app = create_app(settings=settings)
    request_id = str(uuid4())
    body = {"record": RECORDS["metric"], "request_id": request_id}
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            responses = await asyncio.gather(
                *[client.post("/api/records/metric", json=body) for _ in range(4)]
            )
            assert all(response.status_code == 200 for response in responses)
            assert len({response.json()["data"]["id"] for response in responses}) == 1
            rows = (await client.get("/api/records/metric")).json()["data"]["records"]
            assert len(rows) == 1
            wrong_kind = await client.post(
                "/api/records/diet", json={"record": RECORDS["diet"], "request_id": request_id}
            )
            assert wrong_kind.status_code == 409
            assert wrong_kind.json()["error"]["code"] == "idempotency_conflict"
            assert (await client.get("/api/records/diet")).json()["data"]["records"] == []


class EmptyAnswerModel(SpyChatModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self._seen.append(messages)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=""))])


async def test_invalid_terminal_checkpoint_is_not_advertised_as_resumable(settings):
    model = EmptyAnswerModel()
    app = create_app(settings=settings, model=model)
    request_id = str(uuid4())
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            thread_id = (await client.post("/api/threads")).json()["thread_id"]
            failed = await client.post(
                "/api/chat",
                json={"message": "合成空回答", "request_id": request_id, "thread_id": thread_id},
            )
            assert failed.status_code == 502
            state = (await client.get(f"/api/threads/{thread_id}")).json()
            assert state["status"] == "failed"
            assert state["can_resume"] is False and state["pending"] is False
            assert len(state["messages"]) == 1 and state["messages"][0]["role"] == "user"
            resumed = await client.post(
                f"/api/threads/{thread_id}/resume", json={"request_id": request_id}
            )
            assert resumed.status_code == 409
            assert resumed.json()["error"]["code"] == "resume_unavailable"
            assert len(model._seen) == 1
