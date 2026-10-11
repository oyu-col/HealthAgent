from collections.abc import Callable
from dataclasses import dataclass, field
from uuid import uuid4

from app.agent.budget import ExecutionBudget
from app.config import Settings


@dataclass(frozen=True, slots=True)
class RunContext:
    user_id: str
    timezone: str
    trace_id: str
    run_id: str
    operation_id: str = ""
    thread_id: str | None = None
    memory_updates: list[dict] = field(default_factory=list)
    tool_observations: dict[str, int] = field(default_factory=dict)
    budget: ExecutionBudget = field(default_factory=ExecutionBudget)
    agent_name: str = "health_lead_agent"
    delegation_depth: int = 0
    delegation_id: str | None = None
    event_sink: Callable[[str, dict], None] | None = field(default=None, repr=False, compare=False)

    def emit(self, event: str, **metadata):
        """Append safe metadata to an optional run-owned trace sink, without doing IO."""
        if self.event_sink:
            self.event_sink(event, {"agent_name": self.agent_name, **metadata})

    @classmethod
    def create(
        cls, settings: Settings, trace_id: str, user_id: str | None = None, **kwargs
    ) -> "RunContext":
        run_id = str(uuid4())
        return cls(
            user_id=user_id or settings.local_user_id,
            timezone=settings.timezone,
            trace_id=trace_id,
            run_id=run_id,
            operation_id=kwargs.pop("operation_id", run_id),
            budget=kwargs.pop(
                "budget",
                ExecutionBudget(
                    max_tool_calls=settings.max_tool_calls,
                    max_model_calls=settings.max_steps,
                    max_delegations=settings.max_delegations,
                ),
            ),
            **kwargs,
        )
