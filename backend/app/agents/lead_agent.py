from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.graph.state import CompiledStateGraph

from app.agent.context import RunContext
from app.agent.reliability import (
    BoundedReadRetryMiddleware,
    HealthSafetyMiddleware,
    SharedModelBudgetMiddleware,
)
from app.agent.tool_middleware import ToolBoundaryMiddleware
from app.agents.prompts import HEALTH_SYSTEM_PROMPT
from app.config import Settings


def build_lead_agent(
    model: BaseChatModel,
    *,
    tools=None,
    checkpointer=None,
    middleware=None,
    max_tool_calls=12,
    settings: Settings | None = None,
) -> CompiledStateGraph:
    """Use public framework tools, middleware, and checkpoint interfaces."""
    available_tools = list(tools or [])
    if available_tools and settings and settings.subagents_enabled:
        from app.agents.subagents import SpecialistPool

        available_tools.append(SpecialistPool(model, available_tools, settings).tool())
    reliability = [HealthSafetyMiddleware(), SharedModelBudgetMiddleware()] if settings else []
    return create_agent(
        model=model,
        tools=available_tools,
        middleware=reliability
        + (
            [
                ToolBoundaryMiddleware(),
                *([BoundedReadRetryMiddleware(settings)] if settings else []),
                ToolCallLimitMiddleware(run_limit=max_tool_calls, exit_behavior="error"),
            ]
            if available_tools
            else []
        )
        + (middleware or []),
        checkpointer=checkpointer,
        system_prompt=HEALTH_SYSTEM_PROMPT,
        context_schema=RunContext,
        name="health_lead_agent",
    )
