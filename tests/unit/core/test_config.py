from pathlib import Path

import pytest

from src.core.config import Config, Settings

pytestmark = pytest.mark.unit


@pytest.fixture
def sandbox_home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    return tmp_path


def test_config_persists_values_between_instances(sandbox_home):
    cfg = Config()
    assert cfg.get("missing", "default") == "default"

    cfg.set("api", {"host": "example"})
    cfg.save()

    reloaded = Config()
    assert reloaded.get("api") == {"host": "example"}
    assert (sandbox_home / ".footballprediction" / "config.json").exists()


def test_settings_reads_environment_overrides(monkeypatch):
    monkeypatch.setenv("API_HOST", "api.example.com")
    monkeypatch.setenv("API_PORT", "9001")

    settings = Settings()

    assert settings.api_host == "api.example.com"
    assert settings.api_port == 9001
