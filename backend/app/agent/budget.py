"""One in-memory budget shared by all graphs in a single admitted run."""

from dataclasses import dataclass

from app.agent.errors import AgentError


@dataclass(slots=True)
class ExecutionBudget:
    max_tool_calls: int = 12
    max_model_calls: int = 12
    max_delegations: int = 3
    tool_calls: int = 0
    model_calls: int = 0
    delegations: int = 0
    retries: int = 0

    # Reservation has no await, so parallel async tools cannot oversubscribe.
    # The application remains deliberately single-worker / single event loop.
    def consume_tool(self):
        if self.tool_calls >= self.max_tool_calls:
            raise AgentError("tool_limit", "执行达到共享工具尝试上限。", 503)
        self.tool_calls += 1

    def consume_model(self):
        if self.model_calls >= self.max_model_calls:
            raise AgentError("step_limit", "执行达到共享模型调用上限。", 503)
        self.model_calls += 1

    def consume_delegation(self):
        if self.delegations >= self.max_delegations:
            raise AgentError("delegation_limit", "执行达到子任务委派上限。", 503)
        self.delegations += 1
