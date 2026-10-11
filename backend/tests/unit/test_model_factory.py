import httpx
import pytest
from langchain_openai import ChatOpenAI

from app.config import Settings
from app.models.demo import DemoChatModel
from app.models.factory import model_session


async def test_fake_never_initializes_provider(settings, monkeypatch):
    def unexpected(**kwargs):
        raise AssertionError("fake must not construct a provider")

    monkeypatch.setattr("app.models.factory.ChatOpenAI", unexpected)
    async with model_session(settings) as model:
        assert isinstance(model, DemoChatModel)


async def test_provider_explicit_configuration_and_cleanup(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "wrong-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://wrong.invalid/v1")
    settings = Settings(
        model_mode="provider",
        model_name="test-model",
        model_base_url="https://example.invalid/v1",
        model_api_key="test-secret",
        model_timeout_seconds=2,
        model_max_retries=0,
        _env_file=None,
    )
    async with model_session(settings) as model:
        assert isinstance(model, ChatOpenAI)
        assert model.model_name == "test-model"
        assert model.openai_api_key.get_secret_value() == "test-secret"
        assert model.openai_api_base == "https://example.invalid/v1"
        assert model.max_retries == 0
        assert model.request_timeout == 2
        assert "streaming" not in model.model_fields_set  # graph callbacks must select streaming
        sync_client, async_client = model.http_client, model.http_async_client
        assert isinstance(sync_client, httpx.Client)
        assert not async_client.is_closed
    assert sync_client.is_closed
    assert async_client.is_closed


async def test_clients_close_if_provider_construction_fails(monkeypatch):
    captured = {}

    def broken(**kwargs):
        captured.update(kwargs)
        raise RuntimeError("construction failed")

    monkeypatch.setattr("app.models.factory.ChatOpenAI", broken)
    settings = Settings(
        model_mode="provider",
        model_name="test",
        model_base_url="https://example.invalid/v1",
        model_api_key="test",
        _env_file=None,
    )
    with pytest.raises(RuntimeError, match="construction failed"):
        async with model_session(settings):
            pytest.fail("must not yield")
    assert captured["http_client"].is_closed
    assert captured["http_async_client"].is_closed
