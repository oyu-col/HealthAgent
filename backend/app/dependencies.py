from typing import Annotated

from fastapi import Depends, Request

from app.agent.errors import AgentError
from app.agent.runtime import HealthAgentRuntime
from app.config import Settings


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_runtime(request: Request) -> HealthAgentRuntime:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime is None:
        raise AgentError("not_ready", "服务尚未完成初始化。", 503)
    return runtime


SettingsDependency = Annotated[Settings, Depends(get_settings)]
RuntimeDependency = Annotated[HealthAgentRuntime, Depends(get_runtime)]
