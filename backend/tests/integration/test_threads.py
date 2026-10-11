import asyncio
import json
from uuid import uuid4

import httpx
from langchain_core.messages import HumanMessage, ToolMessage

from app.domain.schemas import QueryInput
from app.main import create_app
from tests.fakes import SpyChatModel, ToolChatModel


async def test_history_survives_restart_and_requests_are_idempotent(settings):
    app = create_app(settings=settings, model=SpyChatModel())
    request_id = str(uuid4())
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            first = (
                await client.post(
                    "/api/chat", json={"message": "合成偏好", "request_id": request_id}
                )
            ).json()
            repeated = (
                await client.post(
                    "/api/chat", json={"message": "合成偏好", "request_id": request_id}
                )
            ).json()
            assert (
                repeated["answer"] == first["answer"]
                and repeated["thread_id"] == first["thread_id"]
            )
            conflict = await client.post(
                "/api/chat", json={"message": "更改内容", "request_id": request_id}
            )
            assert conflict.status_code == 409
    model = SpyChatModel()
    reopened = create_app(settings=settings, model=model)
    async with reopened.router.lifespan_context(reopened):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=reopened), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/chat", json={"message": "继续", "thread_id": first["thread_id"]}
            )
            assert response.status_code == 200
            assert [m.content for m in model._seen[-1] if isinstance(m, HumanMessage)] == [
                "合成偏好",
                "继续",
            ]
            state = (await client.get("/api/threads/" + first["thread_id"])).json()
            assert len(state["messages"]) == 4 and state["pending"] is False


class FailAfterWrite(ToolChatModel):
    failed: bool = False

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if isinstance(messages[-1], ToolMessage) and not self.failed:
            self.failed = True
            raise RuntimeError("sensitive error")
        return super()._generate(messages, stop, run_manager, **kwargs)


async def test_resume_checkpoint_after_write_without_duplicate(settings):
    model = FailAfterWrite(
        tool_name="add_health_metric",
        arguments={"record": {"metric_type": "weight", "value": 70, "unit": "kg"}},
    )
    app = create_app(settings=settings, model=model)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            thread_id = (await client.post("/api/threads")).json()["thread_id"]
            request_id = str(uuid4())
            failed = await client.post(
                "/api/chat",
                json={"message": "合成记录", "thread_id": thread_id, "request_id": request_id},
            )
            assert failed.status_code == 500
            assert failed.json()["error"]["thread_id"] == thread_id
            assert model.failed is True
            before_resume = await app.state.health.query("metric", "local-user", QueryInput())
            assert len(before_resume.data["records"]) == 1
    # New application + saver, no original in-memory run state.
    recovered = create_app(
        settings=settings,
        model=ToolChatModel(tool_name="add_health_metric", arguments=model.arguments),
    )
    async with recovered.router.lifespan_context(recovered):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=recovered), base_url="http://test"
        ) as client:
            response = await client.post(
                f"/api/threads/{thread_id}/resume", json={"request_id": request_id}
            )
            assert response.status_code == 200
            assert json.loads(response.json()["answer"])["success"] is True
            records = await recovered.state.health.query("metric", "local-user", QueryInput())
            assert len(records.data["records"]) == 1


async def test_thread_owner_and_concurrent_runs(settings):
    settings = settings.model_copy(
        update={"auth_mode": "token", "api_tokens": {"alice": "a" * 32, "bob": "b" * 32}}
    )
    app = create_app(settings=settings, model=SpyChatModel(delay=0.1))
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": "Bearer " + "a" * 32},
        ) as client:
            thread_id = (await client.post("/api/threads")).json()["thread_id"]
            path = "/api/threads/" + thread_id
            assert (
                await client.get(path, headers={"Authorization": "Bearer " + "b" * 32})
            ).status_code == 404
            responses = await asyncio.gather(
                *[
                    client.post("/api/chat", json={"message": "合成", "thread_id": thread_id})
                    for _ in range(2)
                ]
            )
            assert sorted(r.status_code for r in responses) == [200, 409]
            assert (
                await client.post(
                    "/api/chat",
                    json={"message": "伪造", "thread_id": thread_id},
                    headers={"Authorization": "Bearer " + "b" * 32},
                )
            ).status_code == 404
