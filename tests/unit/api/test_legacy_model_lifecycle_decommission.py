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
from src.ml.inference import Predictor
from src.ml.inference.model_dispatcher import Predictor as DispatcherPredictor

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_ARTIFACT = REPOSITORY_ROOT / "model_zoo/production/v26.7_aligned_production.pkl"
ARTIFACT_MANIFEST = REPOSITORY_ROOT / "config/model_artifacts.json"


def _route_paths() -> set[str]:
    return {route.path for route in main_module.app.routes if hasattr(route, "path")}


def test_canonical_predict_routes_remain_mounted_without_legacy_model_routes():
    """Only the canonical prediction routes remain on the active app surface."""
    paths = _route_paths()

    assert "/predict" in paths
    assert "/predict/batch" in paths
    assert not any(path.startswith("/api/v1/models") for path in paths)
    assert not any(path.startswith("/api/v1/admin") for path in paths)

    # The old router registration symbols must not be present in the active
    # application module either; route absence is the primary assertion above.
    assert "model_management_router" not in vars(main_module)
    assert "admin_router" not in vars(main_module)


def test_predictor_factory_remains_canonical():
    """The active factory still constructs the PR-3 canonical predictor."""
    assert Predictor is DispatcherPredictor
    factory_source = inspect.getsource(main_module.get_predictor)
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
