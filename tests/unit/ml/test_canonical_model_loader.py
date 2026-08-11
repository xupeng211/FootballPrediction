"""PR-3 canonical verified model-loader behavior.

lifecycle: permanent

These tests use only temporary, test-only joblib artifacts.  No production
model path, training job, database write, or live data request is used.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
from typing import Any

os.environ["LOG_LEVEL"] = "INFO"

from fastapi.testclient import TestClient
import joblib
import pytest
from starlette import status

import src.api.health as health_module
from src.database.db_pool import DatabasePool
import src.main as main_module
from src.ml.feature_adapter import FeatureAdapterFactory, ModelType, V26_6_PreMatchAdapter
from src.ml.inference.artifact_manifest import (
    ArtifactManifest,
    ReadinessManager,
    get_process_readiness_manager,
)
from src.ml.inference.canonical_model_loader import (
    CANONICAL_API_ARTIFACT_NAME,
    CANONICAL_API_MODEL_TYPE,
    CanonicalModelLoader,
    ModelArtifactUnavailableError,
)
from src.ml.inference.feature_contract_registry import FeatureContractRegistry
import src.ml.inference.model_dispatcher as dispatcher_module

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_FEATURES = tuple(V26_6_PreMatchAdapter().get_required_features())
EXPECTED_FEATURE_COUNT = 20


class _SafeTestModel:
    """Small non-training model object used only inside tmp_path fixtures."""

    def __init__(self, marker: str):
        self.marker = marker
        self.n_features_in_ = len(RUNTIME_FEATURES)
        self.feature_names_in_ = RUNTIME_FEATURES

    def predict(self, _features: Any) -> list[int]:
        return [0]

    def predict_proba(self, _features: Any) -> list[list[float]]:
        return [[0.7, 0.2, 0.1]]


@pytest.fixture(autouse=True)
def isolated_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Keep all manifest paths and temporary artifacts inside tmp_path."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_manifest(
    tmp_path: Path,
    checksum: str | None,
    *,
    status_value: str = "active",
    model_type: str = CANONICAL_API_MODEL_TYPE,
    artifact_relative_path: str = "model_zoo/production/v26.7_aligned_production.pkl",
) -> Path:
    manifest_path = tmp_path / "model_artifacts.json"
    manifest_path.write_text(
        json.dumps(
            {
                "version": 2,
                "artifact_root": "models",
                "model_zoo_root": "model_zoo",
                "artifacts": [
                    {
                        "name": CANONICAL_API_ARTIFACT_NAME,
                        "path": artifact_relative_path,
                        "required_for": "api",
                        "status": status_value,
                        "checksum_sha256": checksum,
                        "model_type": model_type,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return manifest_path


def _write_registry(
    tmp_path: Path,
    *,
    features: tuple[str, ...] = RUNTIME_FEATURES,
    artifact_name: str = CANONICAL_API_ARTIFACT_NAME,
    model_type: str = CANONICAL_API_MODEL_TYPE,
) -> Path:
    registry_path = tmp_path / "model_feature_contracts.json"
    registry_path.write_text(
        json.dumps(
            {
                "schema_version": "model-feature-contract-registry/v1",
                "lifecycle": "permanent",
                "contracts": [
                    {
                        "contract_id": "v26_7_aligned/v1",
                        "artifact_name": artifact_name,
                        "model_type": model_type,
                        "feature_contract_version": "v26_6_pre_match/v1",
                        "feature_count": len(features),
                        "ordered_features": list(features),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return registry_path


def _artifact_path(
    tmp_path: Path,
    relative_path: str = "model_zoo/production/v26.7_aligned_production.pkl",
) -> Path:
    path = tmp_path / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _write_test_model(
    tmp_path: Path,
    marker: str = "A",
    relative_path: str = "model_zoo/production/v26.7_aligned_production.pkl",
) -> Path:
    path = _artifact_path(tmp_path, relative_path)
    joblib.dump(
        {
            "model": _SafeTestModel(marker),
            "scaler": None,
            "feature_columns": list(RUNTIME_FEATURES),
            "model_type": CANONICAL_API_MODEL_TYPE,
            "version": "test-only",
        },
        path,
    )
    return path


def _make_loader(
    tmp_path: Path,
    *,
    marker: str = "A",
    registry_features: tuple[str, ...] = RUNTIME_FEATURES,
    registry_artifact_name: str = CANONICAL_API_ARTIFACT_NAME,
    manifest_model_type: str = CANONICAL_API_MODEL_TYPE,
) -> tuple[CanonicalModelLoader, ReadinessManager, Path, Path]:
    artifact_path = _write_test_model(tmp_path, marker)
    manifest_path = _write_manifest(
        tmp_path, _sha256(artifact_path), model_type=manifest_model_type
    )
    registry_path = _write_registry(
        tmp_path,
        features=registry_features,
        artifact_name=registry_artifact_name,
    )
    manager = ReadinessManager(manifest_path, negative_cache_ttl=0)
    loader = CanonicalModelLoader(
        manifest=ArtifactManifest(manifest_path),
        registry=FeatureContractRegistry(registry_path),
        readiness_manager=manager,
    )
    return loader, manager, artifact_path, manifest_path


def _spy_mark(monkeypatch: pytest.MonkeyPatch, manager: ReadinessManager) -> list[tuple[Any, ...]]:
    calls: list[tuple[Any, ...]] = []
    original = manager.mark_model_loaded

    def _record(*args: Any, **kwargs: Any) -> bool:
        calls.append((*args, *kwargs.values()))
        return bool(original(*args, **kwargs))

    monkeypatch.setattr(manager, "mark_model_loaded", _record)
    return calls


def test_real_registry_order_matches_runtime_adapter() -> None:
    """The checked-in registry remains a declaration of the actual adapter."""
    contract = FeatureContractRegistry().get_for_model(
        CANONICAL_API_MODEL_TYPE, artifact_name=CANONICAL_API_ARTIFACT_NAME
    )
    assert contract.feature_count == len(RUNTIME_FEATURES) == EXPECTED_FEATURE_COUNT
    assert contract.ordered_features == RUNTIME_FEATURES


def test_pending_artifact_fails_before_deserialize(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = _write_manifest(tmp_path, None, status_value="pending")
    registry_path = _write_registry(tmp_path)
    manager = ReadinessManager(manifest_path, negative_cache_ttl=0)
    loader = CanonicalModelLoader(
        ArtifactManifest(manifest_path), FeatureContractRegistry(registry_path), manager
    )
    load_calls: list[bool] = []
    monkeypatch.setattr(joblib, "load", lambda *_args, **_kwargs: load_calls.append(True))

    with pytest.raises(ModelArtifactUnavailableError):
        loader.load()

    assert load_calls == []
    assert manager.snapshot()["service_ready"] is False
    assert manager.snapshot()["model_loaded"] is False
    assert not (tmp_path / "model_zoo").exists()


def test_active_missing_checksum_fails_before_deserialize(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = _write_manifest(tmp_path, None)
    registry_path = _write_registry(tmp_path)
    manager = ReadinessManager(manifest_path, negative_cache_ttl=0)
    loader = CanonicalModelLoader(
        ArtifactManifest(manifest_path), FeatureContractRegistry(registry_path), manager
    )
    load_calls: list[bool] = []
    monkeypatch.setattr(joblib, "load", lambda *_args, **_kwargs: load_calls.append(True))

    with pytest.raises(ModelArtifactUnavailableError):
        loader.load()

    assert load_calls == []
    assert manager.snapshot()["model_loaded"] is False


def test_checksum_mismatch_fails_before_deserialize(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact_path = _write_test_model(tmp_path)
    manifest_path = _write_manifest(tmp_path, "0" * 64)
    registry_path = _write_registry(tmp_path)
    manager = ReadinessManager(manifest_path, negative_cache_ttl=0)
    loader = CanonicalModelLoader(
        ArtifactManifest(manifest_path), FeatureContractRegistry(registry_path), manager
    )
    load_calls: list[bool] = []
    monkeypatch.setattr(joblib, "load", lambda *_args, **_kwargs: load_calls.append(True))

    with pytest.raises(ModelArtifactUnavailableError):
        loader.load()

    assert artifact_path.exists()
    assert load_calls == []
    assert manager.snapshot()["model_loaded"] is False


def test_missing_file_fails_before_deserialize(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path = _write_manifest(tmp_path, hashlib.sha256(b"missing").hexdigest())
    registry_path = _write_registry(tmp_path)
    manager = ReadinessManager(manifest_path, negative_cache_ttl=0)
    loader = CanonicalModelLoader(
        ArtifactManifest(manifest_path), FeatureContractRegistry(registry_path), manager
    )
    load_calls: list[bool] = []
    monkeypatch.setattr(joblib, "load", lambda *_args, **_kwargs: load_calls.append(True))

    with pytest.raises(ModelArtifactUnavailableError):
        loader.load()

    assert load_calls == []
    assert manager.snapshot()["model_loaded"] is False


def test_cross_registry_identity_mismatch_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    loader, manager, _artifact_path, _manifest_path = _make_loader(
        tmp_path, registry_artifact_name="stale_artifact"
    )
    load_calls: list[bool] = []
    monkeypatch.setattr(joblib, "load", lambda *_args, **_kwargs: load_calls.append(True))

    with pytest.raises(ModelArtifactUnavailableError):
        loader.load()

    assert load_calls == []
    assert manager.snapshot()["model_loaded"] is False


def test_runtime_feature_order_mismatch_fails_before_deserialize(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    loader, manager, _artifact_path, _manifest_path = _make_loader(
        tmp_path, registry_features=tuple(reversed(RUNTIME_FEATURES))
    )
    load_calls: list[bool] = []
    monkeypatch.setattr(joblib, "load", lambda *_args, **_kwargs: load_calls.append(True))

    with pytest.raises(ModelArtifactUnavailableError):
        loader.load()

    assert load_calls == []
    assert manager.snapshot()["model_loaded"] is False


def test_unexpected_runtime_adapter_binding_fails_before_deserialize(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    loader, manager, _artifact_path, _manifest_path = _make_loader(tmp_path)
    load_calls: list[bool] = []
    monkeypatch.setitem(FeatureAdapterFactory._adapters, ModelType.V26_6_PRE_MATCH, object())
    monkeypatch.setattr(joblib, "load", lambda *_args, **_kwargs: load_calls.append(True))

    with pytest.raises(ModelArtifactUnavailableError):
        loader.load()

    assert load_calls == []
    assert manager.snapshot()["model_loaded"] is False


def test_runtime_feature_count_mismatch_fails_before_deserialize(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    loader, manager, _artifact_path, _manifest_path = _make_loader(
        tmp_path, registry_features=RUNTIME_FEATURES[:-1]
    )
    load_calls: list[bool] = []
    monkeypatch.setattr(joblib, "load", lambda *_args, **_kwargs: load_calls.append(True))

    with pytest.raises(ModelArtifactUnavailableError):
        loader.load()

    assert load_calls == []
    assert manager.snapshot()["model_loaded"] is False


def test_deserialization_failure_does_not_mark_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact_path = _artifact_path(tmp_path)
    artifact_path.write_bytes(b"valid-checksum-but-not-a-joblib-stream")
    manifest_path = _write_manifest(tmp_path, _sha256(artifact_path))
    registry_path = _write_registry(tmp_path)
    manager = ReadinessManager(manifest_path, negative_cache_ttl=0)
    loader = CanonicalModelLoader(
        ArtifactManifest(manifest_path), FeatureContractRegistry(registry_path), manager
    )
    mark_calls = _spy_mark(monkeypatch, manager)

    with pytest.raises(ModelArtifactUnavailableError):
        loader.load()

    assert mark_calls == []
    assert manager.service_ready()[0] is False


def test_successful_temp_load_marks_shared_readiness_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    loader, manager, _artifact_path, _manifest_path = _make_loader(tmp_path)
    mark_calls = _spy_mark(monkeypatch, manager)
    original_load = joblib.load
    load_calls: list[bool] = []

    def _record_load(*args: Any, **kwargs: Any) -> Any:
        load_calls.append(True)
        return original_load(*args, **kwargs)

    monkeypatch.setattr(joblib, "load", _record_load)
    loaded = loader.load()
    cached = loader.load()

    assert loaded.model.marker == "A"
    assert loaded.feature_names == RUNTIME_FEATURES
    assert cached is loaded
    assert load_calls == [True]
    assert len(mark_calls) == 1
    assert mark_calls[0][0] == CANONICAL_API_ARTIFACT_NAME
    assert manager.service_ready() == (True, "")

    async def _db_ready() -> dict[str, Any]:
        return {"healthy": True, "message": "ok", "response_time_ms": 1.0}

    async def _db_quick_ready() -> bool:
        return True

    monkeypatch.setattr(health_module, "_check_database_async", _db_ready)
    monkeypatch.setattr(health_module, "_check_database_quick", _db_quick_ready)
    monkeypatch.setattr(health_module, "_readiness_manager", manager)
    health_client = TestClient(main_module.app)
    assert health_client.get("/health/readiness").status_code == status.HTTP_200_OK
    assert health_client.get("/health/quick").status_code == status.HTTP_200_OK


def test_verified_snapshot_isolated_from_source_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    loader, manager, artifact_path, _manifest_path = _make_loader(tmp_path, marker="A")
    mark_calls = _spy_mark(monkeypatch, manager)
    original_load = joblib.load
    observed_markers: list[str] = []

    def _replace_source_before_deserialize(snapshot: Any) -> Any:
        _write_test_model(tmp_path, marker="B")
        loaded_data = original_load(snapshot)
        observed_markers.append(loaded_data["model"].marker)
        return loaded_data

    monkeypatch.setattr(joblib, "load", _replace_source_before_deserialize)

    with pytest.raises(ModelArtifactUnavailableError):
        loader.load()

    assert observed_markers == ["A"]
    assert artifact_path.exists()
    assert mark_calls == []
    assert manager.service_ready()[0] is False


def test_changed_artifact_invalidates_ready_and_requires_new_verified_load(tmp_path: Path) -> None:
    loader, manager, artifact_path, manifest_path = _make_loader(tmp_path, marker="A")
    first = loader.load()
    assert manager.service_ready()[0] is True

    _write_test_model(tmp_path, marker="B")
    assert manager.service_ready()[0] is False
    with pytest.raises(ModelArtifactUnavailableError):
        loader.load()
    assert manager.snapshot()["model_loaded"] is False

    second_checksum = _sha256(artifact_path)
    _write_manifest(tmp_path, second_checksum)
    second = loader.load()

    assert first.model.marker == "A"
    assert second.model.marker == "B"
    assert second is not first
    assert manager.service_ready()[0] is True
    assert manifest_path.exists()


def test_manifest_identity_drift_invalidates_readiness_without_deserialize(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    loader, manager, artifact_path, manifest_path = _make_loader(tmp_path)
    loader.load()
    assert manager.service_ready()[0] is True
    original_load = joblib.load
    load_calls: list[bool] = []

    def _record_load(*args: Any, **kwargs: Any) -> Any:
        load_calls.append(True)
        return original_load(*args, **kwargs)

    monkeypatch.setattr(
        joblib,
        "load",
        _record_load,
    )

    _write_manifest(tmp_path, _sha256(artifact_path), model_type="different_model")
    with pytest.raises(ModelArtifactUnavailableError):
        loader.load()

    assert load_calls == []
    assert manager.service_ready()[0] is False
    assert manifest_path.exists()


def test_manifest_path_drift_invalidates_loaded_identity_before_reload(
    tmp_path: Path,
) -> None:
    loader, manager, _artifact_path, _manifest_path = _make_loader(tmp_path)
    first = loader.load()
    alternate_relative_path = "model_zoo/production/v26.7_aligned_alternate.pkl"
    alternate_path = _write_test_model(tmp_path, marker="B", relative_path=alternate_relative_path)
    _write_manifest(
        tmp_path,
        _sha256(alternate_path),
        artifact_relative_path=alternate_relative_path,
    )

    assert manager.refresh().service_ready is False
    second = loader.load()

    assert first.artifact_path != second.artifact_path
    assert second.artifact_path == alternate_relative_path
    assert second.model.marker == "B"
    assert manager.service_ready()[0] is True


def test_concurrent_loads_publish_one_object_and_one_deserialize(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    loader, manager, _artifact_path, _manifest_path = _make_loader(tmp_path)
    original_load = joblib.load
    load_count = 0

    def _count_load(*args: Any, **kwargs: Any) -> Any:
        nonlocal load_count
        load_count += 1
        return original_load(*args, **kwargs)

    monkeypatch.setattr(joblib, "load", _count_load)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _index: loader.load(), range(2)))

    assert results[0] is results[1]
    assert load_count == 1
    assert manager.service_ready()[0] is True


def test_loader_and_health_use_the_same_process_readiness_manager() -> None:
    assert health_module._readiness_manager is get_process_readiness_manager()


def test_canonical_predictor_ignores_duplicated_model_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Canonical Predictor cannot bypass the manifest with a caller path."""
    loader, _manager, _artifact_path, _manifest_path = _make_loader(tmp_path, marker="manifest")
    monkeypatch.setattr(dispatcher_module, "get_canonical_model_loader", lambda: loader)

    predictor = dispatcher_module.Predictor(
        model_path=str(tmp_path / "unrelated-caller-path.pkl"),
        model_type=CANONICAL_API_MODEL_TYPE,
    )

    assert predictor.model.marker == "manifest"
    assert predictor._canonical_loaded_model is not None
    assert predictor._canonical_loaded_model.artifact_path == (
        "model_zoo/production/v26.7_aligned_production.pkl"
    )


def test_current_pending_manifest_keeps_predict_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real tracked pending row still yields the public 503 contract."""
    monkeypatch.chdir(PROJECT_ROOT)
    monkeypatch.setattr(main_module, "_predictor", None)
    main_module.app.state.limiter.enabled = False
    load_calls: list[bool] = []
    monkeypatch.setattr(joblib, "load", lambda *_args, **_kwargs: load_calls.append(True))

    client = TestClient(main_module.app)
    response = client.post("/predict", json={"home_team": "A", "away_team": "B"})

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["message"] == "prediction model unavailable"
    assert load_calls == []


def test_startup_valid_temp_artifact_can_be_ready_without_prediction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Lifespan invokes the actual predictor/loader before the first request."""
    loader, manager, _artifact_path, _manifest_path = _make_loader(tmp_path)
    monkeypatch.setattr(dispatcher_module, "get_canonical_model_loader", lambda: loader)
    monkeypatch.setattr(health_module, "_readiness_manager", manager)
    monkeypatch.setattr(main_module, "_predictor", None)
    monkeypatch.setenv("ENABLE_METRICS", "false")

    class _FakePool:
        async def init_pool(self) -> None:
            return None

        async def close(self) -> None:
            return None

    async def _get_pool() -> _FakePool:
        return _FakePool()

    monkeypatch.setattr(DatabasePool, "get_instance", staticmethod(_get_pool))
    monkeypatch.chdir(tmp_path)

    async def _exercise() -> None:
        async with main_module.lifespan(main_module.app):
            assert manager.service_ready() == (True, "")
            assert main_module._predictor is not None

    asyncio.run(_exercise())


def test_startup_with_real_pending_manifest_stays_not_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Startup recognizes the tracked pending state without deserialization."""
    monkeypatch.chdir(PROJECT_ROOT)
    monkeypatch.setattr(main_module, "_predictor", None)
    monkeypatch.setenv("ENABLE_METRICS", "false")
    load_calls: list[bool] = []
    monkeypatch.setattr(joblib, "load", lambda *_args, **_kwargs: load_calls.append(True))

    class _FakePool:
        async def init_pool(self) -> None:
            return None

        async def close(self) -> None:
            return None

    async def _get_pool() -> _FakePool:
        return _FakePool()

    monkeypatch.setattr(DatabasePool, "get_instance", staticmethod(_get_pool))

    async def _exercise() -> None:
        async with main_module.lifespan(main_module.app):
            assert get_process_readiness_manager().service_ready()[0] is False
            assert main_module._predictor is None

    asyncio.run(_exercise())
    assert load_calls == []
    assert not (PROJECT_ROOT / "model_zoo" / "production" / "v26.7_aligned_production.pkl").exists()
