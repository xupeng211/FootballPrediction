"""WAVE-A-NEXT-03 canonical feature availability hermetic tests.

lifecycle: permanent
component: Canonical prediction

所有 provider、数据库连接、scaler、model 和 HTTP/CLI 依赖均使用 fake 或
mock；本文件不启动 PostgreSQL、不访问网络、不加载生产 artifact，也不训练。
"""

from __future__ import annotations

from copy import deepcopy
import io
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient
import numpy as np
import pandas as pd
import pytest
from starlette import status

from src.core.exceptions import (
    InvalidPredictionInputError,
    PredictionError,
    RequiredFeatureDataUnavailableError,
)
import src.database.schema_manager as schema_manager_module
import src.main as main_module
from src.ml.feature_adapter import AdaptationResult, V26_6_PreMatchAdapter
from src.ml.inference import predict_cli
from src.ml.inference.canonical_model_loader import ModelArtifactUnavailableError
from src.ml.inference.model_dispatcher import Predictor

CANONICAL_FEATURES = [
    "rolling_xg_home",
    "rolling_xg_away",
    "rolling_shots_on_target_home",
    "rolling_shots_on_target_away",
    "rolling_possession_home",
    "rolling_possession_away",
    "rolling_team_rating_home",
    "rolling_team_rating_away",
    "home_table_position",
    "away_table_position",
    "table_position_diff",
    "home_points",
    "away_points",
    "points_diff",
    "home_recent_form_points",
    "raw_elo_gap",
    "adjusted_elo_gap",
    "home_fatigue_index",
    "away_fatigue_index",
    "fatigue_diff",
]
CANONICAL_FEATURE_COUNT = 20
EXPECTED_FATIGUE = 0.5
EXPECTED_ROLLING_PROVIDER_CALLS = 2
EXPECTED_LEGACY_PROVIDER_CALLS = 7
EXPECTED_SCHEMA_PROVIDER_CALLS = 4

CANONICAL_PAYLOAD = {
    "header": {
        "status": {"startTimeStr": "2026-08-14T19:00:00Z"},
        "teams": {
            "home": {"name": "Home FC"},
            "away": {"name": "Away FC"},
        },
    },
    # 赛中统计存在也不能进入 canonical 赛前向量。
    "content": {
        "stats": {
            "home": {"xg": 9.9, "possession": {"percentage": 99}},
            "away": {"xg": 9.8, "possession": {"percentage": 1}},
        }
    },
}

ROLLING_STATS = {
    "rolling_xg": 1.4,
    "rolling_shots_on_target": 4.2,
    "rolling_possession": 54.0,
    "matches_count": 5,
}


def _standings(position: int = 4, points: int = 22) -> dict[str, Any]:
    return {
        "position": position,
        "points": points,
        "played": 5,
        "won": 3,
        "drawn": 1,
        "lost": 1,
        "goals_for": 8,
        "goals_against": 4,
        "goal_diff": 4,
        "recent_form_points": 7,
    }


@pytest.fixture
def strict_provider_calls(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[dict[str, Any]]]:
    """安装成功的 strict provider，并记录每次 point-in-time 参数。"""
    calls: dict[str, list[dict[str, Any]]] = {
        "rolling": [],
        "standings": [],
        "elo": [],
        "fatigue": [],
    }

    def rolling(*, team_name: str, n_matches: int, before_match_date: str, strict: bool):
        calls["rolling"].append(
            {
                "team_name": team_name,
                "n_matches": n_matches,
                "before_match_date": before_match_date,
                "strict": strict,
            }
        )
        return dict(ROLLING_STATS)

    def standings(*, team_name: str, before_match_date: str, strict: bool, **_kwargs):
        calls["standings"].append(
            {
                "team_name": team_name,
                "before_match_date": before_match_date,
                "strict": strict,
            }
        )
        return _standings()

    def elo(*, team_names: list[str], before_match_date: str, strict: bool):
        calls["elo"].append(
            {
                "team_names": team_names,
                "before_match_date": before_match_date,
                "strict": strict,
            }
        )
        return dict.fromkeys(team_names, 1500.0)

    def fatigue(*, team_name: str, match_date: str, lookback_days: int, strict: bool):
        calls["fatigue"].append(
            {
                "team_name": team_name,
                "match_date": match_date,
                "lookback_days": lookback_days,
                "strict": strict,
            }
        )
        return 0.5

    monkeypatch.setattr(schema_manager_module.SchemaManager, "get_team_rolling_stats", rolling)
    monkeypatch.setattr(schema_manager_module.SchemaManager, "get_team_standings", standings)
    monkeypatch.setattr(schema_manager_module.SchemaManager, "get_elo_ratings", elo)
    monkeypatch.setattr(schema_manager_module.SchemaManager, "get_team_fatigue_index", fatigue)
    return calls


def test_strict_success_preserves_exact_20_order_and_accepts_1500_and_05(
    strict_provider_calls: dict[str, list[dict[str, Any]]],
) -> None:
    result = V26_6_PreMatchAdapter().adapt(CANONICAL_PAYLOAD, strict=True)

    assert result.success is True
    assert result.features is not None
    assert list(result.features.columns) == CANONICAL_FEATURES
    assert result.features.shape == (1, CANONICAL_FEATURE_COUNT)
    assert result.features.loc[0, "raw_elo_gap"] == 0.0
    assert result.features.loc[0, "home_fatigue_index"] == EXPECTED_FATIGUE
    assert len(strict_provider_calls["rolling"]) == EXPECTED_ROLLING_PROVIDER_CALLS


@pytest.mark.parametrize(
    ("team_key", "team_value"),
    [("home", None), ("home", "  "), ("away", None)],
)
def test_invalid_team_identity_fails_before_any_provider_query(
    strict_provider_calls: dict[str, list[dict[str, Any]]],
    team_key: str,
    team_value: str | None,
) -> None:
    payload = deepcopy(CANONICAL_PAYLOAD)
    if team_value is None:
        payload["header"]["teams"][team_key].pop("name")
    else:
        payload["header"]["teams"][team_key]["name"] = team_value

    with pytest.raises(InvalidPredictionInputError):
        V26_6_PreMatchAdapter().adapt(payload, strict=True)

    assert all(not provider_calls for provider_calls in strict_provider_calls.values())


@pytest.mark.parametrize("timestamp", [None, "not-a-timestamp"])
def test_missing_or_invalid_timestamp_fails_with_zero_provider_calls(
    strict_provider_calls: dict[str, list[dict[str, Any]]], timestamp: str | None
) -> None:
    payload = deepcopy(CANONICAL_PAYLOAD)
    if timestamp is None:
        payload["header"]["status"].pop("startTimeStr")
    else:
        payload["header"]["status"]["startTimeStr"] = timestamp

    with pytest.raises(InvalidPredictionInputError):
        V26_6_PreMatchAdapter().adapt(payload, strict=True)

    assert all(not provider_calls for provider_calls in strict_provider_calls.values())


def test_every_strict_provider_receives_the_same_target_cutoff(
    strict_provider_calls: dict[str, list[dict[str, Any]]],
) -> None:
    V26_6_PreMatchAdapter().adapt(CANONICAL_PAYLOAD, strict=True)
    cutoff = "2026-08-14T19:00:00+00:00"

    assert {call["before_match_date"] for call in strict_provider_calls["rolling"]} == {cutoff}
    assert {call["before_match_date"] for call in strict_provider_calls["standings"]} == {cutoff}
    assert {call["before_match_date"] for call in strict_provider_calls["elo"]} == {cutoff}
    assert {call["match_date"] for call in strict_provider_calls["fatigue"]} == {cutoff}
    assert all(call["strict"] for calls in strict_provider_calls.values() for call in calls)


@pytest.mark.parametrize("matches_count", [0, 4])
def test_no_or_insufficient_rolling_history_fails_closed(
    strict_provider_calls: dict[str, list[dict[str, Any]]],
    monkeypatch: pytest.MonkeyPatch,
    matches_count: int,
) -> None:
    def insufficient(**_kwargs: Any) -> dict[str, Any]:
        result = dict(ROLLING_STATS)
        result["matches_count"] = matches_count
        return result

    monkeypatch.setattr(schema_manager_module.SchemaManager, "get_team_rolling_stats", insufficient)

    with pytest.raises(RequiredFeatureDataUnavailableError):
        V26_6_PreMatchAdapter().adapt(CANONICAL_PAYLOAD, strict=True)

    assert strict_provider_calls["standings"] == []


def test_rolling_provider_exception_is_feature_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(**_kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("database host must not cross the boundary")

    monkeypatch.setattr(schema_manager_module.SchemaManager, "get_team_rolling_stats", unavailable)

    with pytest.raises(RequiredFeatureDataUnavailableError) as error:
        V26_6_PreMatchAdapter().adapt(CANONICAL_PAYLOAD, strict=True)

    assert "database host" not in str(error.value)


@pytest.mark.parametrize("provider_mode", ["no_data", "provider_error"])
def test_standings_no_data_or_provider_error_fails_closed(
    strict_provider_calls: dict[str, list[dict[str, Any]]],
    monkeypatch: pytest.MonkeyPatch,
    provider_mode: str,
) -> None:
    def standings(**_kwargs: Any) -> dict[str, Any]:
        if provider_mode == "provider_error":
            raise RuntimeError("standings database failure")
        return {**_standings(), "played": 0, "position": 10, "points": 30}

    monkeypatch.setattr(schema_manager_module.SchemaManager, "get_team_standings", standings)

    with pytest.raises(RequiredFeatureDataUnavailableError):
        V26_6_PreMatchAdapter().adapt(CANONICAL_PAYLOAD, strict=True)

    assert strict_provider_calls["rolling"]


@pytest.mark.parametrize("provider_mode", ["missing_team", "provider_error"])
def test_elo_missing_or_provider_error_fails_closed(
    strict_provider_calls: dict[str, list[dict[str, Any]]],
    monkeypatch: pytest.MonkeyPatch,
    provider_mode: str,
) -> None:
    def elo(*, team_names: list[str], **_kwargs: Any) -> dict[str, float]:
        if provider_mode == "provider_error":
            raise RuntimeError("ELO database failure")
        return {team_names[0]: 1500.0}

    monkeypatch.setattr(schema_manager_module.SchemaManager, "get_elo_ratings", elo)

    with pytest.raises(RequiredFeatureDataUnavailableError):
        V26_6_PreMatchAdapter().adapt(CANONICAL_PAYLOAD, strict=True)

    assert strict_provider_calls["standings"]


def test_fatigue_provider_error_fails_closed(
    strict_provider_calls: dict[str, list[dict[str, Any]]], monkeypatch: pytest.MonkeyPatch
) -> None:
    def fatigue(**_kwargs: Any) -> float:
        raise RuntimeError("fatigue database failure")

    monkeypatch.setattr(schema_manager_module.SchemaManager, "get_team_fatigue_index", fatigue)

    with pytest.raises(RequiredFeatureDataUnavailableError):
        V26_6_PreMatchAdapter().adapt(CANONICAL_PAYLOAD, strict=True)

    assert strict_provider_calls["elo"]


def test_missing_required_contract_key_never_zero_fills(
    strict_provider_calls: dict[str, list[dict[str, Any]]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        V26_6_PreMatchAdapter,
        "V26_6_FEATURES",
        [*CANONICAL_FEATURES, "missing_required_key"],
    )

    with pytest.raises(RequiredFeatureDataUnavailableError):
        V26_6_PreMatchAdapter().adapt(CANONICAL_PAYLOAD, strict=True)

    assert len(strict_provider_calls["rolling"]) == EXPECTED_ROLLING_PROVIDER_CALLS


class _SpyScaler:
    def __init__(self) -> None:
        self.calls = 0

    def transform(self, features: Any) -> Any:
        self.calls += 1
        return features


class _SpyModel:
    def __init__(self) -> None:
        self.predict_calls = 0
        self.predict_proba_calls = 0

    def predict(self, _features: Any) -> list[int]:
        self.predict_calls += 1
        return [2]

    def predict_proba(self, _features: Any) -> np.ndarray:
        self.predict_proba_calls += 1
        return np.asarray([[0.1, 0.2, 0.7]])


def _successful_adaptation() -> AdaptationResult:
    return AdaptationResult(
        True,
        pd.DataFrame([[0.0] * len(CANONICAL_FEATURES)], columns=CANONICAL_FEATURES),
        CANONICAL_FEATURES,
        [],
        [],
    )


def _predictor_with_adapter(adapter: Any, model_type: str = "v26_7_aligned") -> Predictor:
    predictor = Predictor.__new__(Predictor)
    predictor.model_type = model_type
    predictor.adapter = adapter
    predictor.model = _SpyModel()
    predictor.scaler = _SpyScaler()
    predictor.feature_names = CANONICAL_FEATURES
    predictor._canonical_loader = None
    predictor._canonical_loaded_model = None
    return predictor


def test_feature_exception_prevents_scaler_predict_and_predict_proba() -> None:
    class FailingAdapter:
        def adapt(self, _payload: dict[str, Any], *, strict: bool = False) -> Any:
            assert strict is True
            raise RequiredFeatureDataUnavailableError("required feature data unavailable")

    predictor = _predictor_with_adapter(FailingAdapter())

    with pytest.raises(RequiredFeatureDataUnavailableError):
        predictor.predict(CANONICAL_PAYLOAD)

    assert predictor.scaler.calls == 0
    assert predictor.model.predict_calls == 0
    assert predictor.model.predict_proba_calls == 0


def test_failed_adaptation_result_prevents_inference_calls() -> None:
    class FailedAdapter:
        def adapt(self, _payload: dict[str, Any], *, strict: bool = False) -> AdaptationResult:
            assert strict is True
            return AdaptationResult(
                False, None, CANONICAL_FEATURES, CANONICAL_FEATURES, ["missing"]
            )

    predictor = _predictor_with_adapter(FailedAdapter())

    with pytest.raises(PredictionError):
        predictor.predict(CANONICAL_PAYLOAD)

    assert predictor.scaler.calls == 0
    assert predictor.model.predict_calls == 0
    assert predictor.model.predict_proba_calls == 0


def test_legacy_non_strict_provider_call_and_fallback_values_are_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    def rolling(*, team_name: str, **_kwargs: Any) -> dict[str, Any]:
        calls.append({"provider": "rolling", "team_name": team_name})
        return {
            "rolling_xg": 1.2,
            "rolling_shots_on_target": 4.0,
            "rolling_possession": 50.0,
            "matches_count": 0,
        }

    def standings(*, team_name: str, **_kwargs: Any) -> dict[str, Any]:
        calls.append({"provider": "standings", "team_name": team_name})
        return {"position": 10, "points": 30, "played": 0, "recent_form_points": 6}

    def elo(*, team_names: list[str], **_kwargs: Any) -> dict[str, float]:
        calls.append({"provider": "elo", "team_names": team_names})
        return {}

    def fatigue(*, team_name: str, **_kwargs: Any) -> float:
        calls.append({"provider": "fatigue", "team_name": team_name})
        return 0.5

    monkeypatch.setattr(schema_manager_module.SchemaManager, "get_team_rolling_stats", rolling)
    monkeypatch.setattr(schema_manager_module.SchemaManager, "get_team_standings", standings)
    monkeypatch.setattr(schema_manager_module.SchemaManager, "get_elo_ratings", elo)
    monkeypatch.setattr(schema_manager_module.SchemaManager, "get_team_fatigue_index", fatigue)

    result = V26_6_PreMatchAdapter().adapt(CANONICAL_PAYLOAD)

    assert result.success is True
    assert result.features is not None
    assert result.features.loc[0, "raw_elo_gap"] == 0.0
    assert result.features.loc[0, "home_fatigue_index"] == EXPECTED_FATIGUE
    assert len(calls) == EXPECTED_LEGACY_PROVIDER_CALLS


def test_schema_manager_strict_no_data_raises_and_closes_resources(  # noqa: C901
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class EmptyCursor:
        def __init__(self) -> None:
            self.closed = False
            self.queries: list[tuple[str, Any]] = []

        def execute(self, query: str, params: Any) -> None:
            self.queries.append((query, params))

        def fetchall(self) -> list[Any]:
            return []

        def fetchone(self) -> None:
            return None

        def close(self) -> None:
            self.closed = True

    class Connection:
        def __init__(self) -> None:
            self.closed = False
            self.cursor_instance = EmptyCursor()

        def cursor(self) -> EmptyCursor:
            return self.cursor_instance

        def close(self) -> None:
            self.closed = True

    connections: list[Connection] = []

    def connect(**_kwargs: Any) -> Connection:
        connection = Connection()
        connections.append(connection)
        return connection

    password = SimpleNamespace(get_secret_value=lambda: "not-used")
    database = SimpleNamespace(
        host="unused", port=5432, name="unused", user="unused", password=password
    )
    monkeypatch.setattr(
        schema_manager_module, "get_settings", lambda: SimpleNamespace(database=database)
    )
    monkeypatch.setattr(schema_manager_module.psycopg2, "connect", connect)
    cutoff = "2026-08-14T19:00:00+00:00"

    calls = [
        lambda: schema_manager_module.SchemaManager.get_team_rolling_stats(
            "Home FC", n_matches=5, before_match_date=cutoff, strict=True
        ),
        lambda: schema_manager_module.SchemaManager.get_team_standings(
            "Home FC", before_match_date=cutoff, strict=True
        ),
        lambda: schema_manager_module.SchemaManager.get_elo_ratings(
            ["Home FC", "Away FC"], before_match_date=cutoff, strict=True
        ),
        lambda: schema_manager_module.SchemaManager.get_team_fatigue_index(
            "Home FC", match_date=cutoff, strict=True
        ),
    ]

    for call in calls:
        with pytest.raises(RequiredFeatureDataUnavailableError):
            call()

    assert len(connections) == EXPECTED_SCHEMA_PROVIDER_CALLS
    for connection in connections:
        assert connection.closed is True
        assert connection.cursor_instance.closed is True
        for query, _params in connection.cursor_instance.queries:
            assert "m.match_date < %s" in query


def test_canonical_batch_acquires_all_rows_before_any_inference() -> None:
    class BatchAdapter:
        def adapt(self, payload: dict[str, Any], *, strict: bool = False) -> AdaptationResult:
            assert strict is True
            if payload["header"]["teams"]["home"]["name"] == "Bad FC":
                return AdaptationResult(
                    False, None, CANONICAL_FEATURES, CANONICAL_FEATURES, ["missing"]
                )
            return _successful_adaptation()

    bad_payload = deepcopy(CANONICAL_PAYLOAD)
    bad_payload["header"]["teams"]["home"]["name"] = "Bad FC"
    predictor = _predictor_with_adapter(BatchAdapter())

    with pytest.raises(PredictionError):
        predictor.predict_batch([CANONICAL_PAYLOAD, bad_payload])

    assert predictor.scaler.calls == 0
    assert predictor.model.predict_calls == 0
    assert predictor.model.predict_proba_calls == 0


class _RaisingPredictor:
    def __init__(self, error: Exception):
        self.error = error

    def predict(self, _payload: dict[str, Any]) -> dict[str, Any]:
        raise self.error

    def predict_batch(self, _payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
        raise self.error


@pytest.fixture
def api_client() -> TestClient:
    main_module.app.state.limiter.enabled = False
    return TestClient(main_module.app)


@pytest.mark.parametrize(
    ("error", "status_code", "message"),
    [
        (InvalidPredictionInputError("internal details"), 400, "invalid prediction input"),
        (
            RequiredFeatureDataUnavailableError("database password must not leak"),
            503,
            "required prediction feature data unavailable",
        ),
        (
            ModelArtifactUnavailableError("/home/secret/model.pkl"),
            503,
            "prediction model unavailable",
        ),
        (PredictionError("internal prediction details"), 500, "prediction failed"),
        (RuntimeError("unexpected SQL detail"), 500, "prediction failed"),
    ],
)
def test_http_single_error_taxonomy_is_stable(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    status_code: int,
    message: str,
) -> None:
    monkeypatch.setattr(main_module, "get_predictor", lambda: _RaisingPredictor(error))

    response = api_client.post("/predict", json={"match": "payload"})

    assert response.status_code == status_code
    body = response.json()
    assert body["message"] == message
    assert "/home/secret" not in json.dumps(body)
    assert "database password" not in json.dumps(body)
    assert "unexpected SQL" not in json.dumps(body)


def test_http_batch_feature_unavailable_has_no_partial_response(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        main_module,
        "get_predictor",
        lambda: _RaisingPredictor(RequiredFeatureDataUnavailableError("hidden")),
    )

    response = api_client.post("/predict/batch", json=[CANONICAL_PAYLOAD, CANONICAL_PAYLOAD])

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["message"] == "required prediction feature data unavailable"


@pytest.mark.parametrize(
    ("error", "expected_code", "expected_message"),
    [
        (
            InvalidPredictionInputError("hidden"),
            predict_cli.EXIT_INPUT_ERROR,
            "input error: invalid prediction input",
        ),
        (
            RequiredFeatureDataUnavailableError("hidden"),
            predict_cli.EXIT_FEATURE_DATA_UNAVAILABLE,
            "required prediction feature data unavailable",
        ),
        (
            ModelArtifactUnavailableError("hidden"),
            predict_cli.EXIT_MODEL_UNAVAILABLE,
            "prediction model unavailable",
        ),
        (PredictionError("hidden"), predict_cli.EXIT_PREDICTION_ERROR, "prediction failed"),
        (RuntimeError("hidden"), predict_cli.EXIT_PREDICTION_ERROR, "prediction failed"),
    ],
)
def test_cli_error_taxonomy_is_stable(
    error: Exception, expected_code: int, expected_message: str
) -> None:
    stderr = io.StringIO()
    code = predict_cli.main(
        argv=[],
        stdin=io.StringIO(json.dumps(CANONICAL_PAYLOAD)),
        stdout=io.StringIO(),
        stderr=stderr,
        predictor_provider=lambda: _RaisingPredictor(error),
    )

    assert code == expected_code
    assert stderr.getvalue().strip() == expected_message
    assert "hidden" not in stderr.getvalue()


def test_exact_canonical_feature_contract_remains_20_and_ordered() -> None:
    registry = json.loads(
        (Path(__file__).resolve().parents[3] / "config" / "model_feature_contracts.json").read_text(
            encoding="utf-8"
        )
    )
    contract = registry["contracts"][0]

    assert contract["contract_id"] == "v26_7_aligned/v1"
    assert contract["feature_count"] == CANONICAL_FEATURE_COUNT
    assert contract["ordered_features"] == CANONICAL_FEATURES
    assert V26_6_PreMatchAdapter().get_required_features() == CANONICAL_FEATURES
