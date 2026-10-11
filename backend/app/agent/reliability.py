"""Small domain policies around LangChain's native retry and middleware APIs."""

import asyncio
import re

import httpx
from langchain.agents.middleware import AgentMiddleware, ToolRetryMiddleware
from langchain.agents.middleware.types import ModelResponse
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from openai import APIConnectionError, APIStatusError
from sqlalchemy.exc import OperationalError

from app.domain.schemas import ToolResult

READ_TOOLS = frozenset(
    {
        "query_health_metrics",
        "query_diet_records",
        "query_exercise_records",
        "query_health_documents",
        "calculate_health_trend",
        "search_health_knowledge",
    }
)
WRITE_TOOLS = frozenset({"add_health_metric", "add_diet_record", "add_exercise_record"})
TRANSIENT_CODES = frozenset({"storage_unavailable", "retrieval_unavailable", "tool_timeout"})


class RetryableToolResult(Exception):
    def __init__(self, result: ToolResult):
        super().__init__("Transient read failure")
        self.result = result


def transient_failure(error: Exception) -> bool:
    if isinstance(
        error,
        (
            TimeoutError,
            ConnectionError,
            APIConnectionError,
            httpx.TimeoutException,
            httpx.NetworkError,
            RetryableToolResult,
        ),
    ):
        return True
    if isinstance(error, APIStatusError):
        return error.status_code == 429 or 500 <= error.status_code < 600
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code == 429 or 500 <= error.response.status_code < 600
    if isinstance(error, OperationalError):
        return getattr(error.orig, "sqlite_errorcode", None) in {5, 6} or str(
            error.orig
        ).lower() in {"database is locked", "database table is locked", "database is busy"}
    return False


class BoundedReadRetryMiddleware(ToolRetryMiddleware):
    """Use framework backoff/jitter; reserve shared budget for every physical attempt."""

    def __init__(self, settings):
        super().__init__(
            max_retries=settings.tool_max_retries,
            tools=sorted(READ_TOOLS),
            retry_on=transient_failure,
            on_failure="error",
            initial_delay=settings.tool_retry_initial_delay,
            backoff_factor=2,
            max_delay=2,
            jitter=True,
        )
        self.settings = settings

    async def awrap_tool_call(self, request, handler):
        attempt = 0
        context = request.runtime.context
        name = request.tool_call["name"]

        async def bounded_attempt(current_request):
            nonlocal attempt
            context.budget.consume_tool()
            attempt += 1
            if attempt > 1:
                context.budget.retries += 1
                context.emit("tool.retry", name=name, attempt=attempt)
            timeout = (
                self.settings.subagent_timeout_seconds + 0.1
                if name == "delegate_health_task"
                else self.settings.tool_timeout_seconds
            )
            async with asyncio.timeout(min(timeout, self.settings.request_timeout_seconds)):
                message = await handler(current_request)
            if name in READ_TOOLS and isinstance(message, ToolMessage):
                try:
                    result = ToolResult.model_validate_json(message.content)
                except ValueError:
                    return message
                if not result.success and result.retryable and result.error_code in TRANSIENT_CODES:
                    raise RetryableToolResult(result)
            return message

        return await super().awrap_tool_call(request, bounded_attempt)


class SharedModelBudgetMiddleware(AgentMiddleware):
    async def awrap_model_call(self, request, handler):
        request.runtime.context.budget.consume_model()
        return await handler(request)


class HealthSafetyMiddleware(AgentMiddleware):
    """A narrow explicit-emergency rule, not a clinical triage or diagnosis model."""

    async def awrap_model_call(self, request, handler):
        context = request.runtime.context
        current = next(
            (
                message
                for message in reversed(request.messages)
                if isinstance(message, HumanMessage)
            ),
            None,
        )
        text = current.content if current and isinstance(current.content, str) else ""
        urgent = any(
            re.search(
                r"(?:我现在|我正在|突然出现|目前有|持续出现).{0,20}(?:胸痛|呼吸困难|意识不清|大量出血)",
                clause,
            )
            and not re.search(
                r"(?:没有|并非|不再|否认|无).{0,8}(?:胸痛|呼吸困难|意识不清|大量出血)", clause
            )
            for clause in re.split(r"[。！？\n]", text)
        )
        if context.delegation_depth == 0 and urgent:
            context.emit("guardrail.blocked", error_code="urgent_health_request")
            return ModelResponse(
                result=[
                    AIMessage(
                        content=(
                            "你描述的情况可能需要紧急处理。请立即联系当地急救服务或由身边的人协助就医，"
                            "不要等待聊天回复。HealthAgent 不能进行诊断或代替急救人员。"
                        )
                    )
                ]
            )
        return await handler(request)
