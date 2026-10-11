import pytest
from pydantic import ValidationError

from app.config import PROJECT_ROOT, Settings, load_settings


def test_mode_must_be_explicit():
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.parametrize(
    "fields",
    [
        {"model_mode": "unknown"},
        {"max_steps": 0},
        {"max_steps": 101},
        {"max_input_chars": 0},
        {"max_input_chars": 32_001},
        {"request_timeout_seconds": 0},
        {"request_timeout_seconds": float("nan")},
        {"model_timeout_seconds": float("inf")},
        {"model_timeout_seconds": 61},
        {"model_max_retries": 3},
        {"tool_max_retries": 4},
        {"tool_timeout_seconds": 0},
        {"tool_retry_initial_delay": -1},
        {"max_delegations": 0},
        {"max_delegations": 7},
        {"subagent_max_concurrency": 5},
        {"subagent_timeout_seconds": 0},
        {"subagent_max_steps": 1},
        {"local_user_id": "  "},
        {"timezone": "Not/AZone"},
        {"model_base_url": "ftp://example.com"},
        {"model_base_url": "https://u:secret@example.com/v1"},
        {"model_base_url": "https://example.com/v1?key=secret"},
    ],
)
def test_invalid_settings(fields):
    with pytest.raises(ValidationError):
        Settings(**({"model_mode": "fake"} | fields), _env_file=None)


def test_provider_has_no_implicit_credentials(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "unrelated-secret")
    with pytest.raises(ValidationError):
        Settings(model_mode="provider", _env_file=None)


@pytest.mark.parametrize("secret", [None, "", "   "])
def test_provider_requires_key(secret):
    with pytest.raises(ValidationError):
        Settings(
            model_mode="provider",
            model_name="test",
            model_base_url="https://example.com/v1",
            model_api_key=secret,
            _env_file=None,
        )


def test_provider_config_and_secret_repr():
    value = Settings(
        model_mode="provider",
        model_name="test-model",
        model_base_url="https://example.com/v1",
        model_api_key="secret-not-for-logs",
        _env_file=None,
    )
    assert value.model_mode == "provider"
    assert value.timezone == "Asia/Shanghai"
    assert "secret-not-for-logs" not in repr(value)
    assert "example.com" not in repr(value)


def test_env_path_is_project_root_and_explicit_files_work(tmp_path, monkeypatch):
    assert Settings.model_config["env_file"] == PROJECT_ROOT / ".env"
    env = tmp_path / ".env"
    env.write_text(
        "HEALTH_AGENT_MODEL_MODE=fake\nHEALTH_AGENT_LOCAL_USER_ID=演示\n", encoding="utf8"
    )
    monkeypatch.chdir(tmp_path)
    assert Settings(_env_file=env).local_user_id == "演示"


def test_startup_error_does_not_disclose_invalid_value(monkeypatch):
    def invalid():
        raise ValueError("secret-and-health-data")

    monkeypatch.setattr("app.config.Settings", invalid)
    with pytest.raises(RuntimeError) as info:
        load_settings()
    assert "secret-and-health-data" not in str(info.value)
    assert info.value.__suppress_context__
