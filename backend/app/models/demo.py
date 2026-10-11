"""A stateless, visibly fake model for verifying local graph execution."""

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class DemoChatModel(BaseChatModel):
    def bind_tools(self, tools, **kwargs):
        return self

    @property
    def _llm_type(self) -> str:
        return "health-agent-fake"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        latest = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
        preview = str(latest.content)[:80] if latest else ""
        answer = (
            f"[FAKE 演示模式] 已通过 HealthAgent 的 LangGraph 图收到：{preview}\n"
            "这是本地运行链路验证，不是医学建议或真实模型回答。"
            "演示模型只回显输入，不会自动理解或执行健康工具。"
        )
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=answer))])

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        return self._generate(messages, stop, run_manager, **kwargs)
