from uuid import uuid4

from app.agent.errors import AgentError
from app.memory.extraction import ALLOWED_VALUES, extract_preferences


class MemoryService:
    def __init__(self, repository):
        self.repository = repository

    async def extract(self, user_id, text, request_id, thread_id):
        changes = extract_preferences(text)
        if not changes:
            return []
        return await self.repository.apply(user_id, changes, request_id, thread_id)

    async def update(self, user_id, key, value):
        if key not in ALLOWED_VALUES or (value is not None and value not in ALLOWED_VALUES[key]):
            raise AgentError("invalid_preference", "偏好名称或值不在允许范围内。", 422)
        return await self.repository.apply(
            user_id, [{"key": key, "value": value}], str(uuid4()), None
        )

    async def list(self, user_id):
        return await self.repository.list(user_id)

    async def relevant(self, user_id, query):
        keys = {"language", "response_style"}
        if any(
            term in query.lower()
            for term in ("饮食", "食物", "吃", "营养", "餐", "diet", "food", "meal")
        ):
            keys.add("diet_preference")
        if any(
            term in query.lower()
            for term in ("运动", "锻炼", "健身", "跑", "游泳", "exercise", "workout")
        ):
            keys.add("exercise_preference")
        return [
            row
            for row in await self.list(user_id)
            if row["key"] in keys and row["value"] in ALLOWED_VALUES[row["key"]]
        ]
