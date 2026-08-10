"""MLC-1 API regression tests: missing production model artifact → HTTP 503.

Contract under test:
- When canonical predictor initialization fails with the
  model-artifact-unavailable condition, /predict and /predict/batch must
  return HTTP 503 with a stable, user-safe message.
- Unrelated error semantics stay unchanged:
  ValueError (bad user input) → 400, other Exception → 500.

Side-effect safety:
- The real Predictor is never instantiated: src.main.get_predictor is
  monkeypatched at the canonical boundary, so no model is loaded or trained
  and no artifact is written.
- The rate limiter is disabled to keep this file isolated from the shared
  slowapi per-IP counter used by the other /predict contract tests.
"""

import os

os.environ["LOG_LEVEL"] = "INFO"

from fastapi.testclient import TestClient
import pytest
from starlette import status

import src.main as main_module
from src.ml.inference.model_dispatcher import ModelArtifactUnavailableError


class _RaisingPredictor:
    """Predictor stand-in that raises a pre-configured error on every call."""

    def __init__(self, error: Exception):
        self.error = error

    def predict(self, _data: dict) -> dict:
        raise self.error

    def predict_batch(self, _data: list[dict]) -> list[dict]:
        raise self.error


def _get_predictor_raising(error: Exception):
    def _get():
        raise error

    return _get


@pytest.fixture
def client() -> TestClient:
    """TestClient bound to src.main.app without lifespan (no DB init)."""
    main_module.app.state.limiter.enabled = False
    return TestClient(main_module.app)


# ---------------------------------------------------------------------------
# TEST B — 模型产物缺失 → 503
# ---------------------------------------------------------------------------


def test_predict_missing_model_artifact_returns_503(client, monkeypatch):
    """/predict 在模型产物缺失时返回 503 与稳定用户安全信息。"""
    monkeypatch.setattr(
        main_module,
        "get_predictor",
        _get_predictor_raising(
            ModelArtifactUnavailableError("模型产物不可用: model_type=v26_7_aligned")
        ),
    )

    response = client.post("/predict", json={"home_team": "A", "away_team": "B"})

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    body = response.json()
    assert body.get("error") is True
    assert body.get("status_code") == status.HTTP_503_SERVICE_UNAVAILABLE
    # 稳定、用户安全的信息
    assert "prediction model unavailable" in body.get("message", "")
    # 不暴露本地文件系统路径
    assert "model_zoo" not in body.get("message", "")
    assert "/home/" not in body.get("message", "")
    assert "/tmp/" not in body.get("message", "")


def test_predict_batch_missing_model_artifact_returns_503(client, monkeypatch):
    """/predict/batch 在模型产物缺失时同样返回 503。"""
    monkeypatch.setattr(
        main_module,
        "get_predictor",
        _get_predictor_raising(ModelArtifactUnavailableError("模型产物不可用")),
    )

    response = client.post("/predict/batch", json=[{"home_team": "A", "away_team": "B"}])

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    body = response.json()
    assert body.get("error") is True
    assert "prediction model unavailable" in body.get("message", "")


# ---------------------------------------------------------------------------
# 错误语义不回归：只有模型不可用条件映射到 503
# ---------------------------------------------------------------------------


def test_unrelated_valueerror_still_returns_400(client, monkeypatch):
    """坏用户输入（ValueError）必须仍然映射到 400，而不是 503。"""
    monkeypatch.setattr(
        main_module,
        "get_predictor",
        _get_predictor_raising(ValueError("bad match data")),
    )

    response = client.post("/predict", json={"x": 1})

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json().get("error") is True


def test_unrelated_exception_still_returns_500(client, monkeypatch):
    """未预期的内部错误必须仍然映射到 500，而不是 503。"""
    monkeypatch.setattr(
        main_module,
        "get_predictor",
        _get_predictor_raising(RuntimeError("boom")),
    )

    response = client.post("/predict", json={"x": 1})

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json().get("error") is True
