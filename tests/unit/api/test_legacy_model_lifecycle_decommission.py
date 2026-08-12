"""PR-4 regression tests for the legacy model-lifecycle boundary.

These tests exercise the mounted FastAPI surface and the canonical inference
package without starting the application lifespan.  They do not train, load a
production artifact, access the database, or make network requests.

lifecycle: permanent
"""

import inspect
import json
import os
from pathlib import Path

os.environ["LOG_LEVEL"] = "INFO"

import src.main as main_module
import src.ml.inference as inference_package
from src.ml.inference import Predictor, prediction_runtime
from src.ml.inference.model_dispatcher import Predictor as DispatcherPredictor
import src.ml.inference.predict_cli as prediction_cli

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_ARTIFACT = REPOSITORY_ROOT / "model_zoo/production/v26.7_aligned_production.pkl"
ARTIFACT_MANIFEST = REPOSITORY_ROOT / "config/model_artifacts.json"


def _route_paths() -> set[str]:
    return {route.path for route in main_module.app.routes if hasattr(route, "path")}


def test_canonical_prediction_and_readonly_model_routes_are_mounted():
    """Prediction and the converged read-only model surface are mounted."""
    paths = _route_paths()

    assert "/predict" in paths
    assert "/predict/batch" in paths
    assert "/api/v1/models/info" in paths
    assert "/api/v1/models/list" in paths
    assert not any(path.startswith("/api/v1/admin") for path in paths)

    model_routes = {
        route.path: route.methods
        for route in main_module.app.routes
        if hasattr(route, "path") and route.path.startswith("/api/v1/models")
    }
    assert model_routes["/api/v1/models/info"] == {"GET"}
    assert model_routes["/api/v1/models/list"] == {"GET"}
    assert "/api/v1/models/reload" not in model_routes

    # The old admin/retraining registration symbol remains absent.
    assert "admin_router" not in vars(main_module)


def test_predictor_factory_remains_canonical(monkeypatch):
    """HTTP and CLI resolve through the shared canonical runtime owner."""
    assert Predictor is DispatcherPredictor
    factory_source = inspect.getsource(prediction_runtime.get_predictor)
    sentinel = object()
    monkeypatch.setattr(prediction_runtime, "get_predictor", lambda: sentinel)
    assert main_module.get_predictor() is sentinel
    assert prediction_cli.get_predictor() is sentinel
    assert "create_v26_7_aligned" in factory_source
    assert "model_loader" not in factory_source.lower()


def test_package_surface_no_longer_exposes_legacy_api_compatibility_facade():
    """Package-level loading must not expose the old arbitrary-path facade."""
    assert inference_package.Predictor is DispatcherPredictor
    for legacy_name in (
        "ModelLoader",
        "MatchPredictor",
        "get_model_loader",
        "predict_match",
    ):
        assert not hasattr(inference_package, legacy_name)


def test_current_pending_artifact_state_and_fail_closed_file_state_are_unchanged():
    """PR-4 does not activate or create the current production artifact."""
    manifest = json.loads(ARTIFACT_MANIFEST.read_text(encoding="utf-8"))
    api_rows = [
        row
        for row in manifest["artifacts"]
        if row.get("required_for") == "api" and row.get("name") == "v26_7_aligned"
    ]

    assert len(api_rows) == 1
    assert api_rows[0]["model_type"] == "v26_7_aligned"
    assert api_rows[0]["status"] == "pending"
    assert api_rows[0]["checksum_sha256"] is None
    assert not CANONICAL_ARTIFACT.exists()


def test_decommissioned_legacy_modules_are_not_present():
    """Dead admin/retraining and orphaned core loader code is removed."""
    for relative_path in (
        "src/api/v1/endpoints/admin.py",
        "src/services/mlops/retraining_service.py",
        "src/core/inference_engine.py",
    ):
        assert not (REPOSITORY_ROOT / relative_path).exists()
