"""Collect public LangChain callback metadata without retaining callback payloads."""

import json
import math
from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import ToolMessage

MAX_EVENTS = 400
TOOL_NAMES = frozenset(
    {
        "query_health_metrics",
        "add_health_metric",
        "query_diet_records",
        "add_diet_record",
        "query_exercise_records",
        "add_exercise_record",
        "query_health_documents",
        "search_health_knowledge",
        "calculate_health_trend",
        "delegate_task",
        "delegate_to_agent",
        "delegate_health_task",
    }
)
AGENT_NAMES = frozenset(
    {
        "health_lead_agent",
        "diet_agent",
        "exercise_agent",
        "report_agent",
        "diet",
        "exercise",
        "report",
        "lead",
        "nutrition_agent",
        "record_agent",
        "research_agent",
        "nutrition",
        "record",
        "research",
    }
)
ERROR_CODES = frozenset(
    {
        "timeout",
        "cancelled",
        "step_limit",
        "tool_limit",
        "model_limit",
        "delegation_limit",
        "delegation_depth",
        "delegation_timeout",
        "subagent_timeout",
        "subagent_error",
        "subagent_failed",
        "provider_unavailable",
        "provider_error",
        "internal_error",
        "invalid_model_output",
        "validation_error",
        "tool_error",
        "tool_timeout",
        "storage_unavailable",
        "no_progress",
        "not_found",
        "invalid_request",
        "request_conflict",
        "trace_unavailable",
        "trace_capacity",
        "completed",
        "process_interrupted",
        "unknown",
        "permission_denied",
        "retry_exhausted",
        "subagent_step_limit",
        "unknown_agent",
        "empty_result",
        "read_only",
        "budget_exceeded",
        "urgent_health_request",
        "retrieval_unavailable",
        "delegation_forbidden",
        "write_outcome_unknown",
        "range_too_large",
        "insufficient_data",
        "retrieval_failed",
        "idempotency_conflict",
    }
)
CUSTOM_EVENTS = frozenset(
    {"tool.retry", "model.retry", "delegation.started", "delegation.finished", "guardrail.blocked"}
)


def safe_error(value):
    return value if isinstance(value, str) and value in ERROR_CODES else "unknown"


def safe_name(value, allowed):
    return value if isinstance(value, str) and value in allowed else "unknown"


def token_counts(value):
    if not isinstance(value, dict):
        return None
    keys = ("input_tokens", "output_tokens", "total_tokens")
    if all(type(value.get(key)) is int and 0 <= value[key] <= 10**12 for key in keys):
        return {key: value[key] for key in keys}
    return None


class TraceRecorder(AsyncCallbackHandler):
    """One root execution; callbacks are inherited by child graphs and counted once."""

    run_inline = True
    raise_error = False

    def __init__(
        self, context, *, task_kind, model_mode, input_characters=None, max_events=MAX_EVENTS
    ):
        self.context = context
        self.task_kind = task_kind
        self.model_mode = model_mode
        self.input_characters = input_characters
        self.max_events = max_events
        self.started_at = datetime.now(UTC).isoformat()
        self.started = perf_counter()
        self.events = []
        self.dropped_events = 0
        self.model_runs = {}
        self.tool_runs = {}
        self.usage = {}
        self.ended_models = set()
        self.ended_tools = set()
        self.tool_retries = 0
        self.model_retries = 0
        self.subagent_calls = 0

    def append(self, event, **metadata):
        if len(self.events) >= self.max_events:
            self.dropped_events += 1
            return
        self.events.append(
            {
                "seq": len(self.events) + 1,
                "event": event,
                "elapsed_ms": round((perf_counter() - self.started) * 1000, 3),
                **metadata,
            }
        )

    def emit(self, event, metadata):
        if event not in CUSTOM_EVENTS:
            return
        clean = {}
        for key, value in metadata.items():
            if key in {"name", "tool", "tool_name"}:
                clean["name"] = safe_name(value, TOOL_NAMES)
            elif key in {"agent_name", "role", "agent", "target"}:
                clean["agent_name"] = safe_name(value, AGENT_NAMES)
            elif (
                key
                in {"attempt", "retry_count", "depth", "model_calls", "tool_calls", "delegations"}
                and type(value) is int
            ):
                clean[key] = max(0, min(value, 10000))
            elif (
                key in {"latency_ms", "duration_ms", "delay_seconds"}
                and type(value) in {int, float}
                and math.isfinite(value)
            ):
                clean[key] = max(0, min(float(value), 10**8))
            elif key in {"success", "retryable"} and type(value) is bool:
                clean[key] = value
            elif key in {"error_code", "termination_reason"}:
                clean[key] = safe_error(value) if value is not None else None
            elif key == "delegation_id" and isinstance(value, str):
                try:
                    clean[key] = str(UUID(value))
                except ValueError:
                    pass
            elif key == "status" and value in {"completed", "failed", "cancelled"}:
                clean[key] = value
        if event == "tool.retry":
            self.tool_retries += 1
        elif event == "model.retry":
            self.model_retries += 1
        elif event == "delegation.started":
            self.subagent_calls += 1
        self.append(event, **clean)

    def summary(self, outcome="running"):
        completed = outcome == "completed"
        terminal = outcome != "running"
        status = (
            "completed"
            if completed
            else "running"
            if not terminal
            else "cancelled"
            if outcome == "cancelled"
            else "failed"
        )
        complete_usage = bool(self.model_runs) and len(self.usage) == len(self.model_runs)
        # Cancellation can bypass a framework end callback. A terminal request
        # must not turn an unpaired started event into a fully captured execution.
        complete_callbacks = (
            self.model_runs.keys() == self.ended_models
            and self.tool_runs.keys() == self.ended_tools
        )
        totals = {
            key: sum(usage[key] for usage in self.usage.values()) if self.usage else None
            for key in ("input_tokens", "output_tokens", "total_tokens")
        }
        return {
            "trace_id": self.context.trace_id,
            "run_id": self.context.run_id,
            "thread_id": self.context.thread_id,
            "request_id": self.context.operation_id,
            "task_kind": self.task_kind,
            "input_characters": self.input_characters,
            "model_mode": self.model_mode,
            "status": status,
            "started_at": self.started_at,
            "finished_at": datetime.now(UTC).isoformat() if terminal else None,
            "termination_reason": safe_error(outcome) if terminal else None,
            "latency_ms": round((perf_counter() - self.started) * 1000, 3) if terminal else None,
            "model_calls": len(self.model_runs),
            "tool_calls": len(self.tool_runs),
            "subagent_calls": self.subagent_calls,
            "model_retries": self.model_retries,
            "tool_retries": self.tool_retries,
            "retry_count": self.model_retries + self.tool_retries,
            "retry_observation": "framework_and_domain_hooks",
            "total_steps": len(self.model_runs) + len(self.tool_runs),
            "token_usage": {**totals, "complete": complete_usage},
            "event_count": len(self.events),
            "dropped_events": self.dropped_events,
            "capture_complete": terminal and self.dropped_events == 0 and complete_callbacks,
        }

    async def on_chat_model_start(
        self, serialized, messages, *, run_id, parent_run_id=None, **kwargs
    ):
        key = str(run_id)
        if key in self.model_runs:
            return
        self.model_runs[key] = perf_counter()
        self.append(
            "model.started",
            step_id=key,
            parent_step_id=str(parent_run_id) if parent_run_id else None,
            agent_name=safe_name(
                (kwargs.get("metadata") or {}).get("health_agent_name"), AGENT_NAMES
            ),
        )

    async def on_llm_end(self, response, *, run_id, **kwargs):
        key = str(run_id)
        if key not in self.model_runs:
            return
        # Some adapters send an additional end callback with usage attached.
        for generations in response.generations:
            for generation in generations:
                usage = token_counts(
                    getattr(getattr(generation, "message", None), "usage_metadata", None)
                )
                previous = self.usage.get(key)
                if usage is not None and (
                    previous is None or usage["total_tokens"] > previous["total_tokens"]
                ):
                    self.usage[key] = usage
        if key not in self.ended_models:
            self.ended_models.add(key)
            self.append(
                "model.finished",
                step_id=key,
                success=True,
                latency_ms=round((perf_counter() - self.model_runs[key]) * 1000, 3),
            )

    async def on_llm_error(self, error, *, run_id, **kwargs):
        key = str(run_id)
        if key not in self.model_runs or key in self.ended_models:
            return
        self.ended_models.add(key)
        self.append(
            "model.finished",
            step_id=key,
            success=False,
            latency_ms=round((perf_counter() - self.model_runs[key]) * 1000, 3),
        )

    async def on_tool_start(self, serialized, input_str, *, run_id, parent_run_id=None, **kwargs):
        key = str(run_id)
        if key in self.tool_runs:
            return
        name = safe_name(serialized.get("name") if serialized else None, TOOL_NAMES)
        self.tool_runs[key] = (perf_counter(), name)
        self.append(
            "tool.started",
            step_id=key,
            parent_step_id=str(parent_run_id) if parent_run_id else None,
            name=name,
            agent_name=safe_name(
                (kwargs.get("metadata") or {}).get("health_agent_name"), AGENT_NAMES
            ),
        )

    async def on_tool_end(self, output, *, run_id, **kwargs):
        key = str(run_id)
        if key not in self.tool_runs or key in self.ended_tools:
            return
        self.ended_tools.add(key)
        started, name = self.tool_runs[key]
        success = getattr(output, "status", None) != "error"
        code = None
        # Only inspect the standard result envelope; never retain its data or raw text.
        if isinstance(output, ToolMessage) and isinstance(output.content, str):
            try:
                envelope = json.loads(output.content)
                if isinstance(envelope, dict) and type(envelope.get("success")) is bool:
                    success = envelope["success"]
                    code = safe_error(envelope.get("error_code")) if not success else None
            except (ValueError, TypeError):
                pass
        self.append(
            "tool.finished",
            step_id=key,
            name=name,
            success=success,
            error_code=code,
            latency_ms=round((perf_counter() - started) * 1000, 3),
        )

    async def on_tool_error(self, error, *, run_id, **kwargs):
        key = str(run_id)
        if key not in self.tool_runs or key in self.ended_tools:
            return
        self.ended_tools.add(key)
        started, name = self.tool_runs[key]
        self.append(
            "tool.finished",
            step_id=key,
            name=name,
            success=False,
            error_code=safe_error(getattr(error, "code", None)),
            latency_ms=round((perf_counter() - started) * 1000, 3),
        )

    async def on_retry(self, retry_state, *, run_id, **kwargs):
        key = str(run_id)
        if key in self.tool_runs:
            event = "tool.retry"
        elif key in self.model_runs:
            event = "model.retry"
        else:
            return
        self.emit(event, {"attempt": getattr(retry_state, "attempt_number", 0)})
