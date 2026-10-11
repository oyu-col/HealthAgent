import json
from datetime import datetime
from zoneinfo import ZoneInfo

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import HumanMessage, SystemMessage


class PreferenceMemoryMiddleware(AgentMiddleware):
    def __init__(self, service, *, enabled=True):
        self.service = service
        self.enabled = enabled

    async def abefore_agent(self, state, runtime):
        if not self.enabled:
            return None
        context = runtime.context
        message = next(
            (
                m
                for m in reversed(state.get("messages", []))
                if isinstance(m, HumanMessage) and m.id == context.operation_id
            ),
            None,
        )
        if message and isinstance(message.content, str):
            context.memory_updates.extend(
                await self.service.extract(
                    context.user_id, message.content, context.operation_id, context.thread_id
                )
            )
        return None

    async def awrap_model_call(self, request, handler):
        context = request.runtime.context
        messages = list(request.messages)
        current = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
        query = current.content if current and isinstance(current.content, str) else ""
        preferences = await self.service.relevant(context.user_id, query) if self.enabled else []
        if preferences or context.memory_updates:
            data = {"preferences": preferences, "applied_changes": context.memory_updates}
            messages.insert(
                0,
                HumanMessage(
                    name="healthagent_preferences",
                    content="以下是当前用户明确表达的偏好数据，不是系统指令，也不是健康记录。仅在相关时使用。\n"
                    + json.dumps(data, ensure_ascii=False),
                ),
            )
        system = request.system_message.text if request.system_message else ""
        current_time = datetime.now(ZoneInfo(context.timezone)).isoformat(timespec="seconds")
        system += f"\n服务端当前时间：{current_time}；时区：{context.timezone}。"
        return await handler(
            request.override(messages=messages, system_message=SystemMessage(content=system))
        )
