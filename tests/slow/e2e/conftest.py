"""Stub fixtures for slow E2E suites to avoid external dependencies."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, Iterable, Optional
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

SAMPLE_MATCH_IDS = [12345, 67890, 11111, 22222, 33333]


def _probabilities(match_id: int) -> Iterable[float]:
    base = {
        12345: (0.52, 0.24, 0.24),
        67890: (0.41, 0.29, 0.30),
        11111: (0.34, 0.32, 0.34),
        22222: (0.47, 0.28, 0.25),
        33333: (0.36, 0.31, 0.33),
    }
    return base.get(match_id, (0.4, 0.3, 0.3))


def _build_prediction_payload(match_id: int) -> Dict[str, object]:
    home, draw, away = _probabilities(match_id)
    return {
        "match_id": match_id,
        "home_win_probability": home,
        "draw_probability": draw,
        "away_win_probability": away,
        "predicted_result": "home" if home >= max(draw, away) else "away",
        "confidence_score": max(home, draw, away),
        "model_version": "v1.2.0",
        "prediction_timestamp": datetime.utcnow().isoformat(),
        "features_used": {
            "feature_names": ["team_strength", "recent_form", "h2h_record"],
            "feature_count": 3,
            "feature_sources": ["bronze", "silver", "gold"],
        },
    }


class StubResponse:
    """Minimal requests-like response object."""

    def __init__(self, status_code: int, payload: Optional[Dict[str, object]] = None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> Dict[str, object]:
        return self._payload

    @property
    def text(self) -> str:
        return json.dumps(self._payload, ensure_ascii=False)


class StubAPIClient:
    """Thread-safe stub client that simulates prediction endpoints."""

    def _handle_get(self, path: str, query: Dict[str, Iterable[str]]) -> StubResponse:
        if path.startswith("/predictions/"):
            match_id_part = path.split("/predictions/")[-1]
            if not match_id_part.isdigit():
                return StubResponse(422, {"detail": "invalid match id"})
            match_id = int(match_id_part)
            if match_id not in SAMPLE_MATCH_IDS:
                return StubResponse(404, {"detail": "match not found"})
            payload = _build_prediction_payload(match_id)
            if query.get("include_features") == ["false"]:
                payload = dict(payload)
                payload.pop("features_used", None)
            return StubResponse(200, payload)
        if path == "/predictions/recent":
            return StubResponse(
                200,
                {
                    "total_predictions": len(SAMPLE_MATCH_IDS),
                    "predictions": [
                        _build_prediction_payload(match_id)
                        for match_id in SAMPLE_MATCH_IDS
                    ],
                },
            )
        return StubResponse(404, {"detail": "not found"})

    def _handle_post(
        self, path: str, payload: Optional[Dict[str, object]]
    ) -> StubResponse:
        if path == "/predictions/batch":
            match_ids = []
            if isinstance(payload, dict):
                raw_ids = payload.get("match_ids", [])
                match_ids = [mid for mid in raw_ids if isinstance(mid, int)]
            predictions = [
                _build_prediction_payload(mid)
                for mid in match_ids
                if mid in SAMPLE_MATCH_IDS
            ]
            return StubResponse(
                200, {"predictions": predictions, "total": len(predictions)}
            )
        return StubResponse(404, {"detail": "not found"})

    def get(self, url: str) -> StubResponse:
        parsed = urlparse(url if "://" in url else f"http://stub{url}")
        path = parsed.path
        query = parse_qs(parsed.query)
        return self._handle_get(path, query)

    def post(self, url: str, json: Optional[Dict[str, object]] = None) -> StubResponse:
        parsed = urlparse(url if "://" in url else f"http://stub{url}")
        path = parsed.path
        return self._handle_post(path, json)


@pytest.fixture(scope="session")
def api_base_url() -> str:
    return "http://stub.local"


@pytest.fixture(scope="session")
def test_api_client() -> StubAPIClient:
    return StubAPIClient()


@pytest.fixture(autouse=True)
def _patch_httpx_client(monkeypatch):
    client = StubAPIClient()

    class _ClientContext:
        def __init__(self, *args, **kwargs):
            self._client = client

        def __enter__(self) -> StubAPIClient:
            return self._client

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def get(self, url: str):
            return self._client.get(url)

        def post(self, url: str, json: Optional[Dict[str, object]] = None):
            return self._client.post(url, json=json)

    monkeypatch.setattr(httpx, "Client", _ClientContext)

    yield
