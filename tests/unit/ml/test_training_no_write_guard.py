#!/usr/bin/env python3
# ruff: noqa: ARG001, ARG002, ARG005
"""Tests for no-write training artifact guards.

lifecycle: permanent
scope: GOLD-AUDIT-2AE training guard validation
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class ArtifactBranchEnteredError(Exception):
    """Raised by tests when an artifact branch would start writing."""


def _stub_module(name: str, **attrs):
    # Never decorate an already imported real package: pytest's conftest and
    # sibling ML tests may have loaded it before this fixture starts.
    module = ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _install_training_dependency_stubs() -> None:
    class _Frame:
        """Minimal pandas DataFrame/Series stand-in for import-time annotations."""

    class _Estimator:
        def fit(self, *args, **kwargs):
            raise AssertionError("fit must not run in no-write guard tests")

    _stub_module("numpy", inf=float("inf"), nan=float("nan"), isfinite=lambda value: True)
    _stub_module(
        "pandas",
        DataFrame=_Frame,
        Series=_Frame,
        get_dummies=lambda *args, **kwargs: _Frame(),
    )
    _stub_module("xgboost", XGBClassifier=_Estimator)

    sklearn = _stub_module("sklearn")
    sklearn.__path__ = []
    _stub_module(
        "sklearn.metrics",
        accuracy_score=lambda *args, **kwargs: 0,
        classification_report=lambda *args, **kwargs: {},
        confusion_matrix=lambda *args, **kwargs: [],
        f1_score=lambda *args, **kwargs: 0,
        log_loss=lambda *args, **kwargs: 0,
    )
    _stub_module("sklearn.model_selection", train_test_split=lambda *args, **kwargs: ())
    _stub_module("sklearn.preprocessing", StandardScaler=_Estimator)
    _stub_module("sklearn.calibration", CalibratedClassifierCV=_Estimator)
    _stub_module(
        "joblib",
        dump=lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("joblib.dump must not run before write confirmation")
        ),
    )

    psycopg2 = _stub_module(
        "psycopg2",
        connect=lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("DB connections must not run in guard tests")
        ),
    )
    psycopg2.__path__ = []
    _stub_module("psycopg2.extras", RealDictCursor=object)

    database = _stub_module("src.database")
    database.__path__ = [str(PROJECT_ROOT / "src" / "database")]
    repositories = _stub_module("src.database.repositories")
    repositories.__path__ = [str(PROJECT_ROOT / "src" / "database" / "repositories")]
    _stub_module(
        "src.database.repositories.prediction_repo",
        get_db_connection=lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("DB connections must not run in guard tests")
        ),
        parse_jsonb=lambda value: value,
        safe_float=lambda value, default=0.0: default if value is None else value,
    )


def _load_module(module_name: str, relative_path: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, PROJECT_ROOT / relative_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def training_modules():
    """Load guard targets with test-only stubs and restore imports afterwards.

    These source files import heavyweight ML and database packages at module load
    time.  The guard tests intentionally avoid those dependencies, but the stubs
    must never survive this test: other ML tests require the actual packages.
    """
    original_modules = sys.modules.copy()
    try:
        _install_training_dependency_stubs()
        src_package = _stub_module("src")
        src_package.__path__ = [str(PROJECT_ROOT / "src")]
        constants_package = _stub_module("src.constants")
        constants_package.__path__ = [str(PROJECT_ROOT / "src" / "constants")]

        training_write_guard = _load_module(
            "_training_no_write_guard_contract",
            "src/ml/training_write_guard.py",
        )
        ml_package = _stub_module("src.ml")
        ml_package.__path__ = [str(PROJECT_ROOT / "src" / "ml")]
        sys.modules["src.ml.training_write_guard"] = training_write_guard
        train_model = _load_module(
            "_training_no_write_guard_train_model",
            "scripts/ops/train_model.py",
        )
        train_baseline_v1 = _load_module(
            "_training_no_write_guard_baseline",
            "scripts/model_training/train_baseline_v1.py",
        )
        yield SimpleNamespace(
            guard=training_write_guard,
            train_model=train_model,
            baseline=train_baseline_v1,
            joblib=sys.modules["joblib"],
        )
    finally:
        # Do not leave either stubbed dependencies or dynamically loaded source
        # modules in the shared interpreter used by the rest of tests/unit/ml.
        for module_name in set(sys.modules) - set(original_modules):
            del sys.modules[module_name]
        sys.modules.update(original_modules)


def test_training_write_confirmation_requires_both_flags(training_modules) -> None:
    guard = training_modules.guard
    assert guard.training_write_confirmed({}) is False
    assert guard.training_write_confirmed({"ALLOW_TRAINING_WRITE": "yes"}) is False
    assert (
        guard.training_write_confirmed(
            {
                "ALLOW_TRAINING_WRITE": "yes",
                "FINAL_TRAINING_WRITE_CONFIRMATION": "yes",
            }
        )
        is True
    )


def test_require_training_write_confirmation_fails_closed(training_modules) -> None:
    guard = training_modules.guard
    with pytest.raises(guard.TrainingWriteGuardError):
        guard.require_training_write_confirmation({})


def test_train_model_save_model_blocked_before_artifact_write(
    monkeypatch, training_modules
) -> None:
    train_model = training_modules.train_model
    monkeypatch.delenv("ALLOW_TRAINING_WRITE", raising=False)
    monkeypatch.delenv("FINAL_TRAINING_WRITE_CONFIRMATION", raising=False)

    with pytest.raises(RuntimeError):
        train_model.save_model(
            model=object(),
            scaler=object(),
            metrics={
                "accuracy": 0,
                "f1_score": 0,
                "log_loss": 0,
                "training_samples": 0,
                "training_time_seconds": 0,
                "feature_importance": {},
            },
            output_name="blocked",
        )


def test_train_model_save_model_requires_double_confirmation_before_branch(
    monkeypatch, training_modules
) -> None:
    train_model = training_modules.train_model
    monkeypatch.setenv("ALLOW_TRAINING_WRITE", "yes")
    monkeypatch.setenv("FINAL_TRAINING_WRITE_CONFIRMATION", "yes")
    joblib_stub = training_modules.joblib
    monkeypatch.setattr(
        joblib_stub,
        "dump",
        lambda *args, **kwargs: (_ for _ in ()).throw(ArtifactBranchEnteredError()),
    )

    with pytest.raises(ArtifactBranchEnteredError):
        train_model.save_model(
            model=object(),
            scaler=object(),
            metrics={
                "accuracy": 0,
                "f1_score": 0,
                "log_loss": 0,
                "training_samples": 0,
                "training_time_seconds": 0,
                "feature_importance": {},
            },
            output_name="branch_probe",
        )


def test_baseline_persist_outputs_blocked_before_mkdir(
    monkeypatch, tmp_path, training_modules
) -> None:
    train_baseline_v1 = training_modules.baseline
    monkeypatch.delenv("ALLOW_TRAINING_WRITE", raising=False)
    monkeypatch.delenv("FINAL_TRAINING_WRITE_CONFIRMATION", raising=False)
    output_dir = tmp_path / "blocked_artifacts"
    result = train_baseline_v1.BaselineTrainingResult(
        target="result_1x2",
        model_path=None,
        calibrated_model_path=None,
        metadata_path=None,
        samples=0,
        features=0,
        accuracy=None,
        log_loss=None,
        raw_accuracy=None,
        raw_log_loss=None,
        calibration_method="none",
        calibration_cv=0,
        class_distribution={},
        generated_at="2026-07-06T00:00:00+00:00",
    )

    with pytest.raises(RuntimeError):
        train_baseline_v1.persist_outputs(
            raw_model=object(),
            calibrated_model=object(),
            feature_columns=[],
            result=result,
            output_dir=output_dir,
        )

    assert not output_dir.exists()


def test_baseline_persist_outputs_requires_double_confirmation_before_branch(
    monkeypatch, tmp_path, training_modules
) -> None:
    train_baseline_v1 = training_modules.baseline
    monkeypatch.setenv("ALLOW_TRAINING_WRITE", "yes")
    monkeypatch.setenv("FINAL_TRAINING_WRITE_CONFIRMATION", "yes")
    output_dir = tmp_path / "branch_probe"
    result = train_baseline_v1.BaselineTrainingResult(
        target="result_1x2",
        model_path=None,
        calibrated_model_path=None,
        metadata_path=None,
        samples=0,
        features=0,
        accuracy=None,
        log_loss=None,
        raw_accuracy=None,
        raw_log_loss=None,
        calibration_method="none",
        calibration_cv=0,
        class_distribution={},
        generated_at="2026-07-06T00:00:00+00:00",
    )

    def fail_mkdir(self, *args, **kwargs):
        raise ArtifactBranchEnteredError

    monkeypatch.setattr(Path, "mkdir", fail_mkdir)

    with pytest.raises(ArtifactBranchEnteredError):
        train_baseline_v1.persist_outputs(
            raw_model=object(),
            calibrated_model=object(),
            feature_columns=[],
            result=result,
            output_dir=output_dir,
        )

    assert not output_dir.exists()


def test_report_only_mode_does_not_call_training_or_save(monkeypatch, training_modules) -> None:
    train_model = training_modules.train_model
    expected = {
        "TASK": "filtered_feature_matrix_report_only",
        "mode": "report-only",
        "model_fit": False,
        "artifact_write": False,
    }

    def fail(*args, **kwargs):
        raise AssertionError("training/save path must not run in report-only mode")

    monkeypatch.setattr(train_model, "build_report_from_connection", lambda conn: expected)
    monkeypatch.setattr(train_model, "train_model", fail)
    monkeypatch.setattr(train_model, "save_model", fail)

    assert train_model.run_report_only_mode(object()) == expected


def test_setup_logging_console_only_does_not_create_log_dir(monkeypatch, training_modules) -> None:
    train_model = training_modules.train_model

    def fail_mkdir(self, *args, **kwargs):
        raise AssertionError("console-only logging must not create directories")

    monkeypatch.setattr(Path, "mkdir", fail_mkdir)

    logger = train_model.setup_logging(write_file=False)

    assert not any(isinstance(handler, logging.FileHandler) for handler in logger.handlers)
