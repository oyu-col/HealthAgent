import pytest

from app.agent.context import RunContext
from app.agent.runtime import HealthAgentRuntime
from app.agents.lead_agent import build_lead_agent
from app.config import load_settings
from app.models.factory import model_session


@pytest.mark.live
async def test_live_provider_smoke():
    try:
        settings = load_settings()
    except RuntimeError:
        pytest.skip("No valid HealthAgent provider configuration")
    if settings.model_mode != "provider":
        pytest.skip("HEALTH_AGENT_MODEL_MODE is not provider")
    async with model_session(settings) as model:
        runtime = HealthAgentRuntime(build_lead_agent(model), settings)
        answer = await runtime.ainvoke(
            "请用一句话介绍你能提供的帮助，不要给出具体医疗建议。",
            RunContext.create(settings, "live-smoke"),
        )
    assert answer.strip()
    assert "[FAKE 演示模式]" not in answer
