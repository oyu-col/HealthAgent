import asyncio
from uuid import uuid4

import httpx
import pytest

from app.agent.context import RunContext
from app.agent.errors import AgentError
from app.api.sse import SSEDecoder
from app.main import create_app
from app.observability.recorder import TraceRecorder
from app.persistence.database import database_session
from app.persistence.trace_repository import TraceRepository
from tests.fakes import SpyChatModel


@pytest.mark.parametrize("streaming", [False, True])
@pytest.mark.parametrize("failure_at", ["start", "finish"])
async def test_failed_trace_replay_preserves_completed_historical_receipt(
    settings, monkeypatch, streaming, failure_at
):
    model = SpyChatModel()
    app = create_app(settings=settings, model=model)
    first_id, second_id = str(uuid4()), str(uuid4())
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            first_body = {"message": "synthetic first request", "request_id": first_id}
            first = await client.post("/api/chat", json=first_body)
            assert first.status_code == 200
            thread_id, answer = first.json()["thread_id"], first.json()["answer"]
            original_run_id = first.json()["run_id"]
            second = await client.post(
                "/api/chat",
                json={
                    "message": "synthetic later request",
                    "request_id": second_id,
                    "thread_id": thread_id,
                },
            )
            assert second.status_code == 200
            model_calls = len(model._seen)
            original = getattr(app.state.traces, failure_at)

            async def unavailable(*args, **kwargs):
                raise RuntimeError("PRIVATE_STORAGE_FAILURE")

            monkeypatch.setattr(app.state.traces, failure_at, unavailable)
            endpoint = "/api/chat/stream" if streaming else "/api/chat"
            failed = await client.post(endpoint, json=first_body)
            if streaming:
                events = SSEDecoder().feed(failed.content)
                assert events[-1]["event"] == "run.failed"
                assert events[-1]["data"]["error_code"] == "trace_unavailable"
            else:
                assert failed.status_code == 503
                assert failed.json()["error"]["code"] == "trace_unavailable"

            receipt = await app.state.threads.repository.get_run("local-user", first_id)
            assert receipt.status == "completed"
            assert receipt.answer == answer
            assert receipt.run_id == original_run_id
            monkeypatch.setattr(app.state.traces, failure_at, original)
            replay = await client.post("/api/chat", json=first_body)
            assert replay.status_code == 200
            assert replay.json()["answer"] == answer
            assert len(model._seen) == model_calls
            receipt = await app.state.threads.repository.get_run("local-user", first_id)
            assert receipt.run_id == original_run_id
            current = (await client.get(f"/api/threads/{thread_id}")).json()
            assert current["active_request_id"] == second_id
            assert current["status"] == "idle"


@pytest.mark.parametrize("scope", ["total", "owner"])
async def test_concurrent_trace_admission_cannot_exceed_running_capacity(settings, scope):
    async with database_session(settings.data_dir) as sessions:
        repository = TraceRepository(
            sessions, max_total=1 if scope == "total" else 12, max_per_user=1
        )
        await repository.initialize()
        owners = [f"user-{index}" if scope == "total" else "local-user" for index in range(12)]
        recorders = [
            TraceRecorder(
                RunContext.create(settings, str(uuid4()), user_id=owner),
                task_kind="chat",
                model_mode="fake",
            )
            for owner in owners
        ]
        results = await asyncio.gather(
            *[
                repository.start(owner, recorder.summary())
                for owner, recorder in zip(owners, recorders, strict=True)
            ],
            return_exceptions=True,
        )
        accepted = [result for result in results if result is None]
        rejected = [result for result in results if result is not None]
        assert len(accepted) == 1
        assert sum([len(await repository.list(owner)) for owner in set(owners)]) == 1
        assert len(rejected) == 11
        assert all(
            isinstance(result, AgentError) and result.code == "trace_capacity"
            for result in rejected
        )


@pytest.mark.parametrize("scope", ["total", "owner"])
async def test_mixed_running_and_finished_traces_reclaim_only_terminal_capacity(settings, scope):
    async with database_session(settings.data_dir) as sessions:
        repository = TraceRepository(
            sessions,
            max_total=3 if scope == "total" else 6,
            max_per_user=6 if scope == "total" else 3,
        )
        await repository.initialize()

        async def seed(owner, finished=False):
            recorder = TraceRecorder(
                RunContext.create(settings, str(uuid4()), user_id=owner),
                task_kind="chat",
                model_mode="fake",
            )
            await repository.start(owner, recorder.summary())
            if finished:
                await repository.finish(owner, recorder.summary("completed"), [])
            return recorder.context.trace_id

        unrelated = await seed("other-user", finished=True) if scope == "owner" else None
        first_running = await seed("local-user")
        terminal = await seed("local-user", finished=True)
        second_running = await seed("local-user")
        incoming = await seed("local-user")
        rows = await repository.list("local-user")
        assert {row["trace_id"] for row in rows} == {first_running, second_running, incoming}
        assert all(row["status"] == "running" for row in rows)
        with pytest.raises(AgentError) as pruned:
            await repository.get("local-user", terminal)
        assert pruned.value.code == "trace_not_found"
        if unrelated:
            assert (await repository.get("other-user", unrelated))["status"] == "completed"
