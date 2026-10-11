import secrets
from typing import Annotated

from fastapi import Depends, Request

from app.agent.errors import AgentError


async def current_user(request: Request) -> str:
    settings = request.app.state.settings
    if settings.auth_mode == "local":
        return settings.local_user_id
    authorization = request.headers.get("Authorization", "")
    token = authorization.removeprefix("Bearer ") if authorization.startswith("Bearer ") else ""
    for user_id, expected in settings.api_tokens.items():
        value = expected.get_secret_value() if hasattr(expected, "get_secret_value") else expected
        if secrets.compare_digest(token, value):
            return user_id
    raise AgentError("unauthorized", "需要有效的访问凭据。", 401)


UserDependency = Annotated[str, Depends(current_user)]
