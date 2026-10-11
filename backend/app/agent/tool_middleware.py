import hashlib
import json
import logging
from time import perf_counter

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import ToolMessage
from langgraph.config import get_stream_writer
from langgraph.errors import GraphBubbleUp
from pydantic import ValidationError
from sqlalchemy.exc import OperationalError

from app.agent.errors import AgentError
from app.agent.reliability import WRITE_TOOLS, RetryableToolResult, transient_failure
from app.domain.schemas import ToolResult

logger = logging.getLogger("health_agent.tools")


class ToolBoundaryMiddleware(AgentMiddleware):
    """Normalize framework validation and domain failures without leaking tool inputs."""

    async def awrap_tool_call(self, request, handler):
        started = perf_counter()
        name = request.tool_call["name"]
        writer = get_stream_writer()
        event_data = {"name": name, "tool_call_id": request.tool_call["id"]}
        writer({"event": "tool.started", "data": event_data})
        result = None
        try:
            message = await handler(request)
            if isinstance(message, ToolMessage) and message.status == "error":
                result = ToolResult.fail(
                    "validation_error", "工具名称或参数不合法，请依据 schema 修正。"
                )
            else:
                result = ToolResult.model_validate_json(message.content)
        except (GraphBubbleUp, AgentError):
            raise
        except ValidationError:
            result = ToolResult.fail("validation_error", "工具参数不合法，请依据 schema 修正。")
        except RetryableToolResult as error:
            result = error.result
        except Exception as error:
            transient = transient_failure(error)
            if name in WRITE_TOOLS and (transient or isinstance(error, OperationalError)):
                result = ToolResult.fail(
                    "write_outcome_unknown", "写入结果尚未确认，请先查询已有记录再决定下一步。"
                )
            elif isinstance(error, OperationalError):
                result = ToolResult.fail("storage_unavailable", "存储暂时不可用。", transient)
            elif transient:
                result = ToolResult.fail("tool_timeout", "工具暂时不可用或超时。", True)
            else:
                result = ToolResult.fail("tool_error", "工具执行失败，请调整策略或稍后重试。")
        logger.info(
            "tool_run name=%s success=%s error_code=%s latency_ms=%.2f",
            name,
            result.success,
            result.error_code,
            (perf_counter() - started) * 1000,
        )
        writer(
            {
                "event": "tool.finished",
                "data": {**event_data, "success": result.success, "error_code": result.error_code},
            }
        )
        context = request.runtime.context
        signature = json.dumps(
            {
                "tool": name,
                "args": request.tool_call["args"],
                "result": result.model_dump(mode="json"),
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        fingerprint = hashlib.sha256(signature.encode()).hexdigest()
        context.tool_observations[fingerprint] = context.tool_observations.get(fingerprint, 0) + 1
        if context.tool_observations[fingerprint] >= 3:
            raise AgentError(
                "no_progress", "工具多次返回相同结果，已停止重复执行，请调整请求。", 503
            )
        return ToolMessage(
            content=result.model_dump_json(),
            name=name,
            tool_call_id=request.tool_call["id"],
            status="success" if result.success else "error",
        )
