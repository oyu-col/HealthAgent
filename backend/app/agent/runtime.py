import asyncio
import logging
from collections.abc import Mapping
from contextlib import aclosing, asynccontextmanager
from dataclasses import replace
from time import perf_counter

from langchain.agents.middleware.tool_call_limit import ToolCallLimitExceededError
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.errors import GraphRecursionError
from langgraph.graph.state import CompiledStateGraph
from langsmith import tracing_context
from openai import APIConnectionError, APIError, APIStatusError, APITimeoutError

from app.agent.context import RunContext
from app.agent.errors import AgentError, invalid_output
from app.config import Settings
from app.observability.recorder import TraceRecorder

logger = logging.getLogger("health_agent.runtime")


def extract_answer(state: object) -> str:
    """Read only the terminal AI message and its visible text blocks (v1 output)."""
    if not isinstance(state, Mapping):
        raise invalid_output()
    messages = state.get("messages")
    if not isinstance(messages, list) or not messages:
        raise invalid_output()
    message = messages[-1]
    if not isinstance(message, AIMessage) or message.tool_calls or message.invalid_tool_calls:
        raise invalid_output()
    if message.response_metadata.get("finish_reason") in {"length", "content_filter"}:
        raise invalid_output()
    content = message.content
    if isinstance(content, str):
        answer = content
    else:
        answer = "".join(
            block if isinstance(block, str) else block["text"]
            for block in content
            if isinstance(block, str)
            or (
                isinstance(block, dict)
                and block.get("type") == "text"
                and isinstance(block.get("text"), str)
            )
        )
    if not answer.strip():
        raise invalid_output()
    return answer.strip()


class HealthAgentRuntime:
    def __init__(self, graph: CompiledStateGraph, settings: Settings, traces=None) -> None:
        self.graph = graph
        self.settings = settings
        self.traces = traces
        self._recorders = {}

    async def ainvoke(self, message: str | None, context: RunContext) -> str:
        if message is not None and (
            not message.strip() or len(message) > self.settings.max_input_chars
        ):
            raise AgentError("invalid_request", "输入为空或超过长度限制。", 422)
        async with self.execution(
            context, task_kind="resume" if message is None else "chat", message=message
        ) as traced_context:
            return await self._invoke_graph(message, traced_context)

    async def record_cached(self, context):
        """A receipt replay performs no model or tool work and must not invent it."""
        async with self.execution(context, task_kind="cached"):
            pass

    @asynccontextmanager
    async def execution(self, context, *, task_kind="chat", message=None):
        start = perf_counter()
        outcome = "completed"
        recorder = None
        if self.traces is not None:
            recorder = TraceRecorder(
                context,
                task_kind=task_kind,
                model_mode=self.settings.model_mode,
                input_characters=len(message) if message is not None else None,
            )
            try:
                await self.traces.start(context.user_id, recorder.summary())
            except Exception:
                raise AgentError(
                    "trace_unavailable", "执行记录暂时不可用，请稍后重试。", 503
                ) from None
            self._recorders[context.run_id] = recorder
            context = replace(context, event_sink=recorder.emit)
        try:
            with tracing_context(enabled=False):
                async with asyncio.timeout(self.settings.request_timeout_seconds):
                    yield context
        except asyncio.CancelledError:
            outcome = "cancelled"
            raise
        except GeneratorExit:
            outcome = "cancelled"
            raise
        except (TimeoutError, APITimeoutError):
            outcome = "timeout"
            raise AgentError("timeout", "模型请求超时，请稍后重试。", 504) from None
        except GraphRecursionError:
            outcome = "step_limit"
            raise AgentError("step_limit", "执行达到步骤上限，未完成本次请求。", 503) from None
        except ToolCallLimitExceededError:
            outcome = "tool_limit"
            raise AgentError("tool_limit", "执行达到工具调用上限。", 503) from None
        except APIConnectionError:
            outcome = "provider_unavailable"
            raise AgentError("provider_unavailable", "模型服务暂时不可用。", 503) from None
        except APIStatusError as error:
            transient = error.status_code == 429 or error.status_code >= 500
            outcome = "provider_unavailable" if transient else "provider_error"
            raise AgentError(
                outcome, "模型服务暂时不可用或拒绝了请求。", 503 if transient else 502
            ) from None
        except APIError:
            outcome = "provider_error"
            raise AgentError("provider_error", "模型服务返回了无法处理的响应。", 502) from None
        except AgentError as error:
            outcome = error.code
            raise
        except Exception:
            outcome = "internal_error"
            raise AgentError(
                "internal_error", "本次执行失败，请通过 trace_id 定位。", 500
            ) from None
        finally:
            if recorder is not None:
                self._recorders.pop(context.run_id, None)

                async def persist():
                    try:
                        await self.traces.finish(
                            context.user_id, recorder.summary(outcome), recorder.events
                        )
                        return True
                    except Exception:
                        logger.error(
                            "trace_persist_failed trace_id=%s run_id=%s",
                            context.trace_id,
                            context.run_id,
                        )
                        return False

                persistence = asyncio.create_task(persist())
                try:
                    persisted = await asyncio.shield(persistence)
                except asyncio.CancelledError:
                    await persistence
                    raise
                if not persisted and outcome == "completed":
                    raise AgentError(
                        "trace_unavailable",
                        "本次执行记录未保存，请检查会话状态并恢复。",
                        503,
                    ) from None
            # Never log prompts, answers, provider exceptions, identity or API keys.
            logger.info(
                "agent_run trace_id=%s run_id=%s outcome=%s latency_ms=%.2f",
                context.trace_id,
                context.run_id,
                outcome,
                (perf_counter() - start) * 1000,
            )

    def graph_config(self, context):
        config = {
            "recursion_limit": self.settings.max_steps,
            "run_id": context.run_id,
            "metadata": {"health_agent_name": context.agent_name},
        }
        if recorder := self._recorders.get(context.run_id):
            config["callbacks"] = [recorder]
        if context.thread_id:
            config["configurable"] = {"thread_id": context.thread_id}
        return config

    async def astream(self, message, context):
        if message is not None and (
            not message.strip() or len(message) > self.settings.max_input_chars
        ):
            raise AgentError("invalid_request", "输入为空或超过长度限制。", 422)
        final_state = None
        async with self.execution(
            context, task_kind="resume" if message is None else "chat", message=message
        ) as context:
            stream = self.graph.astream(
                self.graph_input(message, context),
                self.graph_config(context),
                context=context,
                stream_mode=["messages", "values", "custom"],
                version="v2",
            )
            async with aclosing(stream):
                async for part in stream:
                    if part["type"] == "values":
                        final_state = part["data"]
                    elif part["type"] == "messages":
                        chunk, metadata = part["data"]
                        if (
                            metadata.get("langgraph_node") == "model"
                            and metadata.get("health_agent_name") == context.agent_name
                            and isinstance(chunk, AIMessage)
                            and not chunk.tool_calls
                        ):
                            content = chunk.content
                            text = (
                                content
                                if isinstance(content, str)
                                else "".join(
                                    b["text"]
                                    for b in content
                                    if isinstance(b, dict)
                                    and b.get("type") == "text"
                                    and isinstance(b.get("text"), str)
                                )
                            )
                            if text:
                                yield {
                                    "event": "message.delta",
                                    "data": {"text": text, "message_id": chunk.id},
                                }
                    elif part["type"] == "custom" and part["data"].get("event") in {
                        "tool.started",
                        "tool.finished",
                    }:
                        yield part["data"]
            answer = extract_answer(final_state)
        # Commit trace before exposing the authoritative terminal answer.
        yield {"event": "answer", "data": {"answer": answer}}

    @staticmethod
    def graph_input(message, context):
        return (
            {"messages": [HumanMessage(content=message, id=context.operation_id or None)]}
            if message is not None
            else None
        )

    async def _invoke_graph(self, message: str | None, context: RunContext) -> str:
        async with asyncio.timeout(self.settings.request_timeout_seconds):
            # v1 dict output is explicitly selected and covered by a real-graph test.
            state = await self.graph.ainvoke(
                self.graph_input(message, context),
                config=self.graph_config(context),
                context=context,
                version="v1",
            )
            return extract_answer(state)
