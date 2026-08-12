"""PR-A3 prediction authority convergence behavior tests.

lifecycle: permanent

These tests prove the shared HTTP/CLI owner, canonical model identity, thin
CLI behavior, fail-closed errors, package routing, legacy separation, and
import purity without loading a production artifact, querying the database,
fetching the network, or training a model.
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

os.environ["LOG_LEVEL"] = "INFO"

from src.constants.model_config import TITAN_COMBAT_FEATURES_LEGACY
import src.main as main_module
from src.ml.feature_adapter import V26_6_PreMatchAdapter
import src.ml.inference as inference_package
from src.ml.inference import predict_cli, prediction_runtime
from src.ml.inference.canonical_model_loader import ModelArtifactUnavailableError
from src.ml.inference.model_dispatcher import Predictor

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
LEGACY_FEATURE_COUNT = 11
CANONICAL_FEATURE_COUNT = 20
PACKAGE_JSON = REPOSITORY_ROOT / "package.json"
MANIFEST = REPOSITORY_ROOT / "config" / "model_artifacts.json"
REGISTRY = REPOSITORY_ROOT / "config" / "model_feature_contracts.json"

CANONICAL_PAYLOAD = {
    "header": {
        "status": {"startTimeStr": "2026-08-14T19:00:00Z"},
        "teams": {
            "home": {"name": "Home FC"},
            "away": {"name": "Away FC"},
        },
    }
}


@pytest.fixture(autouse=True)
def reset_shared_runtime():
    """Keep process-local predictor state isolated across behavior tests."""
    prediction_runtime.reset_predictor()
    yield
    prediction_runtime.reset_predictor()


class _FakePredictor:
    model_type = "v26_7_aligned"

    def __init__(self):
        self.single_calls: list[dict] = []
        self.batch_calls: list[list[dict]] = []

    def ensure_canonical_model_current(self) -> None:
        return None

    def predict(self, payload: dict) -> dict:
        self.single_calls.append(payload)
        return {
            "prediction": "Home",
            "probabilities": {"Away": 0.1, "Draw": 0.2, "Home": 0.7},
            "confidence": 0.7,
            "model_type": self.model_type,
        }

    def predict_batch(self, payload: list[dict]) -> list[dict]:
        self.batch_calls.append(payload)
        return [self.predict(item) for item in payload]


def test_http_and_cli_delegate_to_the_same_runtime_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    """Both public adapters resolve through the one shared owner at runtime."""
    fake = _FakePredictor()
    monkeypatch.setattr(prediction_runtime, "get_predictor", lambda: fake)

    assert main_module.get_predictor() is fake
    assert predict_cli.get_predictor() is fake


def test_shared_owner_requests_only_canonical_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    """The shared owner constructs v26_7_aligned and never selects Titan/mini."""
    fake = _FakePredictor()
    calls: list[str] = []

    def create_canonical(_cls) -> _FakePredictor:
        calls.append("v26_7_aligned")
        return fake

    monkeypatch.setattr(Predictor, "create_v26_7_aligned", classmethod(create_canonical))
    monkeypatch.setattr(
        Predictor,
        "create_v26_mini",
        classmethod(lambda _cls: (_ for _ in ()).throw(AssertionError("mini fallback"))),
    )

    assert prediction_runtime.get_predictor() is fake
    assert calls == ["v26_7_aligned"]


def test_cli_success_with_injected_canonical_runtime() -> None:
    """A representative canonical payload is passed through without translation."""
    fake = _FakePredictor()

    result = predict_cli.predict_payload(
        CANONICAL_PAYLOAD,
        predictor_provider=lambda: fake,
    )

    assert result["model_type"] == "v26_7_aligned"
    assert result["prediction"] == "Home"
    assert result["probabilities"] == {"Away": 0.1, "Draw": 0.2, "Home": 0.7}
    assert fake.single_calls == [CANONICAL_PAYLOAD]


def test_cli_missing_artifact_fails_closed_without_titan_fallback(tmp_path: Path) -> None:
    """Canonical unavailability is a stable non-zero CLI error, not a fallback."""
    before = set(tmp_path.iterdir())
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps(CANONICAL_PAYLOAD), encoding="utf-8")

    def unavailable():
        raise ModelArtifactUnavailableError("internal path must not be exposed")

    stdout = io.StringIO()
    stderr = io.StringIO()
    code = predict_cli.main(
        ["--input", str(input_path)],
        stdout=stdout,
        stderr=stderr,
        predictor_provider=unavailable,
    )

    assert code == predict_cli.EXIT_MODEL_UNAVAILABLE
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == "prediction model unavailable\n"
    assert "Titan" not in stderr.getvalue()
    assert set(tmp_path.iterdir()) == before | {input_path}


def test_cli_malformed_json_is_nonzero_and_has_no_traceback(tmp_path: Path) -> None:
    """Malformed input fails before the runtime seam is called."""
    input_path = tmp_path / "malformed.json"
    input_path.write_text("{not-json", encoding="utf-8")
    provider_called = False

    def provider():
        nonlocal provider_called
        provider_called = True
        raise AssertionError("runtime must not be called")

    stderr = io.StringIO()
    code = predict_cli.main(
        ["--input", str(input_path)],
        stdout=io.StringIO(),
        stderr=stderr,
        predictor_provider=provider,
    )

    assert code == predict_cli.EXIT_INPUT_ERROR
    assert stderr.getvalue() == "input error: malformed JSON\n"
    assert "Traceback" not in stderr.getvalue()
    assert provider_called is False


def test_cli_import_does_not_load_legacy_titan_or_db_modules(tmp_path: Path) -> None:
    """Fresh canonical imports do not pull in legacy Titan or DB repositories."""
    probe = """
import sys
import src.ml.inference.predict_cli
import src.ml.inference.prediction_runtime
assert 'src.ml.inference.titan_loader' not in sys.modules
assert 'src.database.repositories.prediction_repo' not in sys.modules
assert 'get_titan_model' not in vars(sys.modules['src.ml.inference'])
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPOSITORY_ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_cli_and_runtime_imports_are_filesystem_pure(tmp_path: Path) -> None:
    """Fresh imports do not create logs, model files, or other cwd artifacts."""
    probe = """
from pathlib import Path
before = sorted(path.name for path in Path('.').iterdir())
import src.ml.inference.predict_cli
import src.ml.inference.prediction_runtime
after = sorted(path.name for path in Path('.').iterdir())
assert before == after
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPOSITORY_ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_package_prediction_commands_are_canonical_and_legacy_is_explicit() -> None:
    """Generic package commands route to the canonical CLI only."""
    scripts = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))["scripts"]

    assert "predict_cli" in scripts["predict"]
    assert "predict_pipeline.py" not in scripts["predict"]
    assert "titan" not in scripts["predict"].lower()
    assert "predict_cli" in scripts["predict:dry"]
    assert "predict_cli" in scripts["predict:json"]
    assert "predict_pipeline.py" in scripts["predict:titan-legacy"]


def test_legacy_and_canonical_feature_contracts_are_not_conflated() -> None:
    """The old 11-feature core and canonical 20-feature registry remain distinct."""
    runtime_source = (REPOSITORY_ROOT / "src/ml/inference/prediction_runtime.py").read_text(
        encoding="utf-8"
    )
    cli_source = (REPOSITORY_ROOT / "src/ml/inference/predict_cli.py").read_text(encoding="utf-8")

    assert len(TITAN_COMBAT_FEATURES_LEGACY) == LEGACY_FEATURE_COUNT
    assert len(V26_6_PreMatchAdapter().get_required_features()) == CANONICAL_FEATURE_COUNT
    for forbidden in ("prediction_repo", "get_titan_model", "TITAN_COMBAT_FEATURES"):
        assert forbidden not in runtime_source
        assert forbidden not in cli_source


def test_current_pending_manifest_and_registry_contract_remain_unchanged() -> None:
    """A3 does not activate the pending artifact or mutate the registry contract."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    api_row = next(
        row
        for row in manifest["artifacts"]
        if row["name"] == "v26_7_aligned" and row["required_for"] == "api"
    )
    contract = json.loads(REGISTRY.read_text(encoding="utf-8"))["contracts"][0]

    assert api_row["status"] == "pending"
    assert api_row["checksum_sha256"] is None
    assert contract["contract_id"] == "v26_7_aligned/v1"
    assert contract["feature_count"] == CANONICAL_FEATURE_COUNT
    assert len(contract["ordered_features"]) == CANONICAL_FEATURE_COUNT


def test_inference_package_does_not_expose_titan_as_canonical_package_surface() -> None:
    """Titan remains directly callable only through its explicit legacy module."""
    assert not hasattr(inference_package, "get_titan_model")
    assert not hasattr(inference_package, "TitanModelLoader")
