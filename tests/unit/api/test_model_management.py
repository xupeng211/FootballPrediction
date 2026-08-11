"""PR-5 canonical read-only model-management behavior tests.

lifecycle: permanent

These tests exercise the mounted FastAPI surface with the tracked pending
manifest and isolated temporary manifest/registry fixtures.  They do not load
a model, train, access the database, make network requests, or mutate the
repository-tracked configuration.
"""

import json
import os
from pathlib import Path
from unittest.mock import patch

os.environ["LOG_LEVEL"] = "INFO"

from fastapi.testclient import TestClient
import pytest
from starlette import status

import src.api.health as health_module
import src.api.model_management as model_management_module
import src.main as main_module
from src.ml.inference.artifact_manifest import ReadinessManager, get_process_readiness_manager
from src.ml.inference.feature_contract_registry import FeatureContractRegistry
import src.services.inference_service as inference_service_module

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = REPOSITORY_ROOT / "config/model_artifacts.json"
REGISTRY_PATH = REPOSITORY_ROOT / "config/model_feature_contracts.json"
EXPECTED_FEATURE_COUNT = 20
EXPECTED_MODEL_COUNT = 2


@pytest.fixture
def client() -> TestClient:
    """Use the app without its DB-initializing lifespan."""
    main_module.app.state.limiter.enabled = False
    main_module.app.openapi_schema = None
    return TestClient(main_module.app)


def _api_entry(
    *,
    status: str = "pending",
    checksum: str | None = None,
    model_type: str = "v26_7_aligned",
) -> dict[str, object]:
    return {
        "name": "v26_7_aligned",
        "path": "model_zoo/production/v26.7_aligned_production.pkl",
        "required_for": "api",
        "status": status,
        "checksum_sha256": checksum,
        "model_type": model_type,
        "schema_version": None,
        "source": "external_artifact_storage",
    }


def _cli_entry() -> dict[str, object]:
    return {
        "name": "cli_only_model",
        "path": "models/cli_only_model.joblib",
        "required_for": "cli",
        "status": "pending",
        "checksum_sha256": None,
        "model_type": "cli_only",
        "schema_version": None,
        "source": "external_artifact_storage",
    }


def _write_manifest(tmp_path: Path, entries: list[dict[str, object]]) -> Path:
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / "model_artifacts.json"
    path.write_text(
        json.dumps(
            {
                "version": 2,
                "artifact_root": "models",
                "model_zoo_root": "model_zoo",
                "artifacts": entries,
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_registry(tmp_path: Path, document: dict) -> Path:
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / "model_feature_contracts.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def _install_temp_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    entries: list[dict[str, object]],
    *,
    registry_path: Path | None = None,
) -> Path:
    """Install only temporary canonical inputs for one request test."""
    manifest_path = _write_manifest(tmp_path, entries)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        model_management_module,
        "_readiness_manager",
        ReadinessManager(manifest_path, negative_cache_ttl=0),
    )
    if registry_path is not None:
        monkeypatch.setattr(
            model_management_module,
            "FeatureContractRegistry",
            lambda: FeatureContractRegistry(registry_path),
        )
    return manifest_path


def _registry_document() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def test_info_reports_real_tracked_pending_state(client, monkeypatch):
    """The current pending/null artifact is informational, not an HTTP 500."""
    monkeypatch.chdir(REPOSITORY_ROOT)
    monkeypatch.setattr(
        model_management_module,
        "_readiness_manager",
        ReadinessManager(MANIFEST_PATH, negative_cache_ttl=0),
    )

    response = client.get("/api/v1/models/info")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["artifact"]["name"] == "v26_7_aligned"
    assert body["artifact"]["model_type"] == "v26_7_aligned"
    assert body["artifact"]["required_for"] == "api"
    assert body["artifact"]["declared_status"] == "pending"
    assert body["artifact"]["checksum_present"] is False
    assert body["feature_contract"] == {
        "contract_id": "v26_7_aligned/v1",
        "feature_contract_version": "v26_6_pre_match/v1",
        "feature_count": EXPECTED_FEATURE_COUNT,
    }
    assert body["runtime"] == {
        "artifact_verified": False,
        "model_loaded": False,
        "service_ready": False,
        "reason": "model artifact pending",
        "verified_at": None,
    }


def test_list_contains_only_manifest_rows_and_exact_contracts(client, tmp_path, monkeypatch):
    """A rogue local pickle cannot become a management-list entry."""
    _install_temp_state(tmp_path, monkeypatch, [_api_entry(), _cli_entry()])
    rogue = tmp_path / "models" / "rogue_undeclared.pkl"
    rogue.parent.mkdir(parents=True, exist_ok=True)
    rogue.write_bytes(b"not a model")

    response = client.get("/api/v1/models/list")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["total_models"] == EXPECTED_MODEL_COUNT
    assert {item["name"] for item in body["models"]} == {
        "v26_7_aligned",
        "cli_only_model",
    }
    api_item = next(item for item in body["models"] if item["name"] == "v26_7_aligned")
    cli_item = next(item for item in body["models"] if item["name"] == "cli_only_model")
    assert api_item["feature_contract"]["feature_count"] == EXPECTED_FEATURE_COUNT
    assert cli_item["feature_contract"] is None
    assert "rogue_undeclared" not in response.text


def test_status_responses_do_not_expose_checksum_or_filesystem_path(client, tmp_path, monkeypatch):
    """Safe status includes presence only, never checksum values or paths."""
    checksum = "a" * 64
    _install_temp_state(
        tmp_path,
        monkeypatch,
        [_api_entry(status="active", checksum=checksum)],
    )

    response = client.get("/api/v1/models/info")

    assert response.status_code == status.HTTP_200_OK
    assert checksum not in response.text
    assert str(tmp_path) not in response.text
    assert "model_zoo/production" not in response.text
    assert "checksum_sha256" not in response.text
    assert "model_path" not in response.text
    assert response.json()["artifact"]["checksum_present"] is True


def test_canonical_info_requires_exact_manifest_contract_binding(client, tmp_path, monkeypatch):
    """A mismatched contract fails closed and never falls back."""
    document = _registry_document()
    document["contracts"][0]["artifact_name"] = "different_artifact"
    registry_path = _write_registry(tmp_path, document)
    _install_temp_state(
        tmp_path,
        monkeypatch,
        [_api_entry()],
        registry_path=registry_path,
    )

    response = client.get("/api/v1/models/info")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["message"] == "model management state unavailable"
    assert "different_artifact" not in response.text
    assert str(tmp_path) not in response.text


def test_malformed_manifest_is_sanitized_and_fails_closed(client, tmp_path, monkeypatch):
    """Malformed canonical JSON returns stable 503 text without internals."""
    manifest_path = _write_manifest(tmp_path, [_api_entry()])
    manifest_path.write_text("{malformed", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        model_management_module,
        "_readiness_manager",
        ReadinessManager(manifest_path, negative_cache_ttl=0),
    )

    response = client.get("/api/v1/models/info")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["message"] == "model management state unavailable"
    assert "malformed" not in response.text
    assert str(tmp_path) not in response.text
    assert "Traceback" not in response.text


def test_malformed_feature_registry_is_sanitized_and_fails_closed(client, tmp_path, monkeypatch):
    """Malformed contract configuration cannot produce a partial info response."""
    registry_path = _write_registry(tmp_path, {"bad": str(tmp_path / "secret")})
    _install_temp_state(
        tmp_path,
        monkeypatch,
        [_api_entry()],
        registry_path=registry_path,
    )

    response = client.get("/api/v1/models/info")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["message"] == "model management state unavailable"
    assert str(tmp_path) not in response.text
    assert "secret" not in response.text
    assert "Traceback" not in response.text


def test_model_management_uses_the_health_and_loader_readiness_owner():
    """All three API surfaces point to the one process-local manager."""
    assert model_management_module._readiness_manager is health_module._readiness_manager
    assert model_management_module._readiness_manager is get_process_readiness_manager()


def test_reload_is_absent_from_routes_and_openapi(client):
    """No remote reload/control-plane operation is mounted or documented."""
    schema = main_module.app.openapi()
    assert "/api/v1/models/info" in schema["paths"]
    assert "/api/v1/models/list" in schema["paths"]
    assert "/api/v1/models/reload" not in schema["paths"]

    response = client.post(
        "/api/v1/models/reload",
        json={"model_path": "/tmp/arbitrary.pkl", "backup_current": True},
    )
    assert response.status_code in (404, 405)


def test_model_info_never_constructs_legacy_inference_service(client, monkeypatch):
    """The old dependency-injection constructor is outside the request path."""
    monkeypatch.chdir(REPOSITORY_ROOT)
    monkeypatch.setattr(
        model_management_module,
        "_readiness_manager",
        ReadinessManager(MANIFEST_PATH, negative_cache_ttl=0),
    )

    with patch.object(
        inference_service_module,
        "InferenceService",
        side_effect=AssertionError("legacy DI constructor must not be called"),
    ):
        response = client.get("/api/v1/models/info")

    assert response.status_code == status.HTTP_200_OK


def test_model_management_does_not_mutate_tracked_configuration(client, monkeypatch):
    """Read-only endpoints leave both canonical configuration files unchanged."""
    monkeypatch.chdir(REPOSITORY_ROOT)
    manifest_before = MANIFEST_PATH.read_bytes()
    registry_before = REGISTRY_PATH.read_bytes()
    monkeypatch.setattr(
        model_management_module,
        "_readiness_manager",
        ReadinessManager(MANIFEST_PATH, negative_cache_ttl=0),
    )

    assert client.get("/api/v1/models/info").status_code == status.HTTP_200_OK
    assert client.get("/api/v1/models/list").status_code == status.HTTP_200_OK

    assert MANIFEST_PATH.read_bytes() == manifest_before
    assert REGISTRY_PATH.read_bytes() == registry_before


def test_predict_pending_artifact_remains_503(client, monkeypatch):
    """PR-5 observability does not change the canonical prediction contract."""
    monkeypatch.chdir(REPOSITORY_ROOT)
    monkeypatch.setattr(main_module, "_predictor", None)
    get_process_readiness_manager().invalidate()
    response = client.post("/predict", json={"home_team": "A", "away_team": "B"})

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.json()["message"] == "prediction model unavailable"
