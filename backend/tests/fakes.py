import asyncio
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.runtime import get_runtime
from langsmith.run_helpers import get_tracing_context
from pydantic import PrivateAttr


class SpyChatModel(BaseChatModel):
    delay: float = 0
    failure: Any = None
    _seen: list[list[BaseMessage]] = PrivateAttr(default_factory=list)
    _contexts: list[Any] = PrivateAttr(default_factory=list)
    _cancelled: bool = PrivateAttr(default=False)
    _tracing_flags: list[Any] = PrivateAttr(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        return self

    @property
    def _llm_type(self) -> str:
        return "test-spy"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        self._seen.append(messages)
        if self.failure:
            raise self.failure
        human = next(m for m in reversed(messages) if isinstance(m, HumanMessage))
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=f"收到：{human.content}"))]
        )

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        self._contexts.append(get_runtime().context)
        self._tracing_flags.append(get_tracing_context()["enabled"])
        try:
            if self.delay:
                await asyncio.sleep(self.delay)
            return self._generate(messages, stop, run_manager, **kwargs)
        except asyncio.CancelledError:
            self._cancelled = True
            raise


class ToolChatModel(SpyChatModel):
    tool_name: str
    arguments: dict
    _schemas: list = PrivateAttr(default_factory=list)

    def bind_tools(self, tools, **kwargs):
        self._schemas = [tool.tool_call_schema.model_json_schema() for tool in tools]
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self._seen.append(messages)
        if isinstance(messages[-1], ToolMessage):
            message = AIMessage(content=messages[-1].content)
        else:
            message = AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": self.tool_name,
                        "args": self.arguments,
                        "id": "test-call",
                        "type": "tool_call",
                    }
                ],
            )
        return ChatResult(generations=[ChatGeneration(message=message)])
