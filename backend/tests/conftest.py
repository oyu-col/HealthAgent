import os

import httpx
import pytest
import requests

from app.config import Settings


def pytest_addoption(parser):
    parser.addoption("--run-live", action="store_true", help="Allow explicit real-provider smoke")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-live"):
        for item in items:
            if "live" in item.keywords:
                item.add_marker(pytest.mark.skip(reason="Real provider requires --run-live"))


@pytest.fixture(autouse=True)
def isolate_environment_and_network(monkeypatch, request):
    if request.node.get_closest_marker("live"):
        return
    for name in list(os.environ):
        if name.startswith(("HEALTH_AGENT_", "OPENAI_", "LANGSMITH_", "LANGCHAIN_")):
            monkeypatch.delenv(name)
    monkeypatch.setenv("LANGSMITH_TRACING", "false")

    def no_network(*args, **kwargs):
        raise AssertionError("Offline tests must not use a network transport")

    async def no_async_network(*args, **kwargs):
        raise AssertionError("Offline tests must not use a network transport")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", no_network)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", no_async_network)
    monkeypatch.setattr(requests.sessions.Session, "request", no_network)


@pytest.fixture
def settings(tmp_path):
    return Settings(model_mode="fake", data_dir=tmp_path, _env_file=None)
