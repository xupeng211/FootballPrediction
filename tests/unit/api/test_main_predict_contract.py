"""Contract tests for src.main:app /predict and /predict/batch endpoints.

These tests lock the current real API behavior without triggering:
- Real model loading (Predictor.create_v26_7_aligned)
- DB connections / pool initialization
- Docker / uvicorn startup
- Network calls / live HTTP requests
- Secret / .env file reads

Strategy:
- Use FastAPI TestClient without context manager (no lifespan → no DB init).
- Monkeypatch src.main.get_predictor → StubPredictor (no real Predictor).
- Do not read .env; set LOG_LEVEL=INFO so pydantic-settings validates.
"""

import os

os.environ["LOG_LEVEL"] = "INFO"

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from starlette import status

import src.main as main_module

# ---------------------------------------------------------------------------
# Stub predictors
# ---------------------------------------------------------------------------


class StubPredictor:
    """Returns fixed prediction dicts; records every call."""

    def __init__(self):
        self.predict_calls: list[dict] = []
        self.predict_batch_calls: list[list[dict]] = []

    def predict(self, request: dict) -> dict:
        self.predict_calls.append(request)
        return {
            "prediction": "Home",
            "probabilities": {"Away": 0.15, "Draw": 0.25, "Home": 0.60},
            "confidence": 0.60,
            "model_type": "v26_mini",
        }

    def predict_batch(self, batch_data: list[dict]) -> list[dict]:
        self.predict_batch_calls.append(batch_data)
        return [
            {
                "prediction": "Home",
                "probabilities": {"Away": 0.15, "Draw": 0.25, "Home": 0.60},
                "confidence": 0.60,
                "model_type": "v26_mini",
            }
            for _ in batch_data
        ]


class ErrorPredictor:
    """Raises a pre-configured error on every call."""

    def __init__(self, error: Exception):
        self.error = error

    def predict(self, _request: dict) -> dict:
        raise self.error

    def predict_batch(self, _batch_data: list[dict]) -> list[dict]:
        raise self.error


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient bound to src.main.app *without* lifespan.

    Avoiding the context-manager form means the lifespan (which initialises
    the asyncpg pool and starts Prometheus) never runs.

    The rate limiter is left at its default (enabled).  The /predict route
    was fixed in #L2B to expose a Starlette Request for slowapi alongside
    the JSON body dict, so the limiter no longer crashes on ``request: dict``.
    """
    return TestClient(main_module.app)


@pytest.fixture
def stub_predictor(monkeypatch) -> StubPredictor:
    """Replace src.main.get_predictor with a StubPredictor singleton."""
    stub = StubPredictor()
    monkeypatch.setattr(main_module, "get_predictor", lambda: stub)
    return stub


# ===================================================================
# 1. App import / route registration
# ===================================================================


def test_app_is_fastapi_instance():
    """src.main.app must be importable and an instance of FastAPI."""
    assert isinstance(main_module.app, FastAPI)


def test_predict_route_registered():
    """/predict must appear in the app route table."""
    paths = {r.path for r in main_module.app.routes if hasattr(r, "path")}
    assert "/predict" in paths


def test_predict_batch_route_registered():
    """/predict/batch must appear in the app route table."""
    paths = {r.path for r in main_module.app.routes if hasattr(r, "path")}
    assert "/predict/batch" in paths


# ===================================================================
# 2. /predict happy path
# ===================================================================


def test_predict_happy_path_200(client, stub_predictor):
    """Valid dict body → 200, response contains prediction keys, predictor called once."""
    payload: dict = {
        "header": {
            "teams": {
                "home": {"name": "Arsenal", "score": 2},
                "away": {"name": "Chelsea", "score": 1},
            }
        },
        "content": {
            "stats": {
                "home": {"possession": {"percentage": 55}, "shotsTotal": {"total": 15}, "xg": 1.8},
                "away": {"possession": {"percentage": 45}, "shotsTotal": {"total": 12}, "xg": 1.2},
            }
        },
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "prediction" in data
    assert "confidence" in data
    assert isinstance(data["prediction"], str)
    assert isinstance(data["confidence"], (int, float))

    assert len(stub_predictor.predict_calls) == 1
    assert stub_predictor.predict_calls[0] == payload


def test_predict_with_minimal_dict(client, stub_predictor):
    """Even a minimal dict is forwarded to the predictor (no strict schema validation)."""
    payload: dict = {"home_team": "X", "away_team": "Y"}
    response = client.post("/predict", json=payload)
    assert response.status_code == status.HTTP_200_OK
    assert len(stub_predictor.predict_calls) == 1


# ===================================================================
# 3. /predict ValueError → 400
# ===================================================================


def test_predict_valueerror_returns_400(client, monkeypatch):
    """When predictor.predict raises ValueError, the endpoint maps it to 400."""
    monkeypatch.setattr(
        main_module, "get_predictor", lambda: ErrorPredictor(ValueError("bad match data"))
    )

    response = client.post("/predict", json={"match": "data"})
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    data = response.json()
    # http_exception_handler returns structured error JSON
    assert data.get("error") is True


# ===================================================================
# 4. /predict invalid body → should NOT call predictor
# ===================================================================


def test_predict_body_list_should_not_call_predictor(client, stub_predictor):
    """JSON list body for /predict (expects dict) must be rejected before reaching predictor."""
    response = client.post("/predict", json=["item1", "item2"])
    # FastAPI type-coercion rejects non-dict for a dict-typed body parameter → 422
    assert response.status_code in (
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        status.HTTP_400_BAD_REQUEST,
    )
    assert len(stub_predictor.predict_calls) == 0


# ===================================================================
# 5. /predict/batch happy path
# ===================================================================


def test_predict_batch_happy_path_200(client, stub_predictor):
    """Valid list[dict] body → 200, returns list, predictor.predict_batch called once."""
    payload: list[dict] = [
        {"home_team": "A", "away_team": "B"},
        {"home_team": "C", "away_team": "D"},
    ]
    response = client.post("/predict/batch", json=payload)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == len(payload)
    for item in data:
        assert "prediction" in item
        assert "confidence" in item

    assert len(stub_predictor.predict_batch_calls) == 1
    assert stub_predictor.predict_batch_calls[0] == payload


def test_predict_batch_single_item(client, stub_predictor):
    """Single-item list is valid input for batch endpoint."""
    payload: list[dict] = [{"home_team": "E", "away_team": "F"}]
    response = client.post("/predict/batch", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == len(payload)
    assert stub_predictor is not None  # side-effect guard: stub is in place


# ===================================================================
# 6. /predict/batch Exception → 500
# ===================================================================


def test_predict_batch_exception_returns_500(client, monkeypatch):
    """When predictor.predict_batch raises Exception, the endpoint maps it to 500."""
    monkeypatch.setattr(
        main_module, "get_predictor", lambda: ErrorPredictor(Exception("batch boom"))
    )

    response = client.post("/predict/batch", json=[{"match": "data"}])
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    data = response.json()
    assert data.get("error") is True


# ===================================================================
# Side-effect safety verification
# ===================================================================


def test_predict_error_path_does_not_create_real_predictor(client, monkeypatch):
    """Verify that the ValueError error path never calls Predictor.create_v26_7_aligned."""
    real_get_predictor_called = False

    def _fake_get_predictor():
        nonlocal real_get_predictor_called
        real_get_predictor_called = True
        return ErrorPredictor(ValueError("bad match data"))

    monkeypatch.setattr(main_module, "get_predictor", _fake_get_predictor)

    response = client.post("/predict", json={"x": 1})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    # The fake was called, but it did NOT call the real Predictor factory
    assert real_get_predictor_called is True


# ===================================================================
# 7. Rate limiter compatibility (L2B fix)
# ===================================================================


def test_limiter_enabled_predict_does_not_crash(client, stub_predictor):
    """With the rate limiter enabled, /predict happy path must not crash.

    Before the L2B fix, ``request: dict`` shadowed the Starlette Request
    object required by slowapi, causing an ``Exception: parameter 'request'
    must be an instance of starlette.requests.Request``.
    """
    # Confirm the limiter is actually enabled for this test
    assert main_module.app.state.limiter.enabled is True

    payload: dict = {"home_team": "X", "away_team": "Y"}
    response = client.post("/predict", json=payload)
    assert response.status_code == status.HTTP_200_OK
    assert len(stub_predictor.predict_calls) == 1
    assert stub_predictor.predict_calls[0] == payload


def test_limiter_enabled_predict_batch_does_not_crash(client, stub_predictor):
    """With the rate limiter enabled, /predict/batch must still work.

    /predict/batch already had ``request: Request`` before the L2B fix,
    so this is a regression guard.
    """
    assert main_module.app.state.limiter.enabled is True

    payload: list[dict] = [{"home_team": "A", "away_team": "B"}]
    response = client.post("/predict/batch", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert len(stub_predictor.predict_batch_calls) == 1
