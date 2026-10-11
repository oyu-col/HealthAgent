"""Contract-only scripted decisions. Expected answers/state are never read here."""

import json

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.runtime import get_runtime
from pydantic import Field, PrivateAttr


class ContractModel(BaseChatModel):
    execution_plan: dict = Field(exclude=True)
    _positions: dict = PrivateAttr(default_factory=dict)

    @property
    def _llm_type(self):
        return "benchmark-contract-not-language-evaluation"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        role = get_runtime().context.agent_name
        position = self._positions.get(role, 0)
        self._positions[role] = position + 1
        plan = self.execution_plan.get(role, [])
        if position < len(plan):
            action = plan[position]
            if "tool" in action:
                message = AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": action["tool"],
                            "args": action["args"],
                            "id": f"contract-{role}-{position}",
                            "type": "tool_call",
                        }
                    ],
                )
            else:
                message = AIMessage(content=action["respond"])
        else:
            # Render actual observations, not expected_state or fabricated success.
            results = [m.content for m in messages if isinstance(m, ToolMessage)]
            message = AIMessage(
                content="[CONTRACT ONLY] " + json.dumps(results, ensure_ascii=False)
            )
        return ChatResult(generations=[ChatGeneration(message=message)])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        return self._generate(messages, stop, run_manager, **kwargs)
