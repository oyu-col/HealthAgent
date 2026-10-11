import json
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from app.agent.context import RunContext
from app.observability.recorder import TraceRecorder
from app.persistence.database import database_session
from app.persistence.trace_repository import TraceRepository


@pytest.mark.parametrize("missing_kind", ["model", "tool"])
@pytest.mark.parametrize("outcome", ["completed", "cancelled", "timeout"])
async def test_terminal_capture_is_incomplete_when_started_callback_has_no_end(
    settings, missing_kind, outcome
):
    recorder = TraceRecorder(
        RunContext.create(settings, str(uuid4())), task_kind="chat", model_mode="fake"
    )
    run_id = uuid4()
    if missing_kind == "model":
        await recorder.on_chat_model_start({}, [["SYNTHETIC_INPUT"]], run_id=run_id)
    else:
        await recorder.on_tool_start(
            {"name": "query_health_metrics"}, "SYNTHETIC_ARGUMENTS", run_id=run_id
        )
    before = list(recorder.events)
    summary = recorder.summary(outcome)
    assert summary["dropped_events"] == 0
    assert summary["capture_complete"] is False
    assert recorder.events == before  # Reporting cannot invent a missing callback.


async def test_capture_matches_each_parallel_tool_attempt_including_failed_attempt(settings):
    recorder = TraceRecorder(
        RunContext.create(settings, str(uuid4())), task_kind="chat", model_mode="fake"
    )
    first, second = uuid4(), uuid4()
    for run_id in (first, second):
        await recorder.on_tool_start({"name": "query_health_metrics"}, "{}", run_id=run_id)
    await recorder.on_tool_end({}, run_id=second)
    assert recorder.summary("completed")["capture_complete"] is False
    await recorder.on_tool_error(TimeoutError("SYNTHETIC_TIMEOUT"), run_id=first)
    assert recorder.summary("completed")["capture_complete"] is True
    await recorder.on_tool_error(TimeoutError("SYNTHETIC_TIMEOUT"), run_id=first)
    assert sum(event["event"] == "tool.finished" for event in recorder.events) == 2


def test_no_callback_execution_can_be_complete_only_when_terminal(settings):
    # Guardrail and cached replies can legitimately call neither model nor tool.
    recorder = TraceRecorder(
        RunContext.create(settings, str(uuid4())), task_kind="cached", model_mode="fake"
    )
    assert recorder.summary()["capture_complete"] is False
    assert recorder.summary("completed")["capture_complete"] is True


async def test_callback_dedup_and_late_usage_do_not_duplicate_steps(settings):
    recorder = TraceRecorder(
        RunContext.create(settings, str(uuid4())), task_kind="chat", model_mode="fake"
    )
    run_id = uuid4()
    await recorder.on_chat_model_start({}, [["PRIVATE_PROMPT"]], run_id=run_id)
    await recorder.on_chat_model_start({}, [["PRIVATE_PROMPT"]], run_id=run_id)
    without_usage = LLMResult(
        generations=[[ChatGeneration(message=AIMessage(content="PRIVATE_ANSWER"))]]
    )
    await recorder.on_llm_end(without_usage, run_id=run_id)
    with_usage = LLMResult(
        generations=[
            [
                ChatGeneration(
                    message=AIMessage(
                        content="OTHER_PRIVATE_ANSWER",
                        usage_metadata={"input_tokens": 3, "output_tokens": 2, "total_tokens": 5},
                    )
                )
            ]
        ]
    )
    await recorder.on_llm_end(with_usage, run_id=run_id)
    await recorder.on_llm_end(with_usage, run_id=run_id)
    late_zero_usage = LLMResult(
        generations=[
            [
                ChatGeneration(
                    message=AIMessage(
                        content="PRIVATE",
                        usage_metadata={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                    )
                )
            ]
        ]
    )
    await recorder.on_llm_end(late_zero_usage, run_id=run_id)
    summary = recorder.summary("completed")
    assert summary["model_calls"] == 1
    assert summary["token_usage"]["total_tokens"] == 5
    assert len(recorder.events) == 2
    assert "PRIVATE" not in json.dumps(recorder.events)


def test_custom_events_are_allowlisted_and_bounded(settings):
    recorder = TraceRecorder(
        RunContext.create(settings, str(uuid4())), task_kind="chat", model_mode="fake", max_events=2
    )
    recorder.emit(
        "tool.retry",
        {
            "name": "query_health_metrics",
            "attempt": 2,
            "error_code": "storage_unavailable",
            "args": "PRIVATE",
            "prompt": "PRIVATE",
        },
    )
    recorder.emit(
        "delegation.started", {"role": "diet_agent", "task": "PRIVATE", "secret": "PRIVATE"}
    )
    recorder.emit("model.retry", {"attempt": 1, "error_code": "PRIVATE"})
    recorder.emit("PRIVATE_EVENT", {"text": "PRIVATE"})
    summary = recorder.summary("completed")
    assert summary["event_count"] == 2
    assert summary["dropped_events"] == 1
    assert summary["capture_complete"] is False
    assert summary["retry_count"] == 2
    assert summary["subagent_calls"] == 1
    assert "PRIVATE" not in json.dumps(recorder.events)


async def test_retention_prunes_old_finished_traces_and_restart_marks_running(settings):
    async with database_session(settings.data_dir) as sessions:
        repository = TraceRepository(sessions, max_total=2, max_per_user=2)
        await repository.initialize()
        ids = []
        for _ in range(3):
            recorder = TraceRecorder(
                RunContext.create(settings, str(uuid4())), task_kind="chat", model_mode="fake"
            )
            await repository.start("local-user", recorder.summary())
            await repository.finish("local-user", recorder.summary("completed"), [])
            ids.append(recorder.context.trace_id)
        rows = await repository.list("local-user")
        assert len(rows) == 2
        assert ids[0] not in [row["trace_id"] for row in rows]
        running = TraceRecorder(
            RunContext.create(settings, str(uuid4())), task_kind="chat", model_mode="fake"
        )
        await repository.start("local-user", running.summary())
        second_running = TraceRecorder(
            RunContext.create(settings, str(uuid4())), task_kind="chat", model_mode="fake"
        )
        await repository.start("local-user", second_running.summary())
        rows = await repository.list("local-user")
        assert len(rows) == 2 and all(row["status"] == "running" for row in rows)
        await repository.initialize()
        restored = await repository.get("local-user", running.context.trace_id)
        assert restored["status"] == "interrupted"
        assert restored["termination_reason"] == "process_interrupted"
        assert restored["latency_ms"] is None
        assert restored["capture_complete"] is False
