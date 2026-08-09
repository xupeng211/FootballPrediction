"""Shared fixtures for VALUE_MVP-1 tests (hermetic synthetic inputs)."""

from __future__ import annotations

import hashlib

import pytest

from src.ml.value_mvp import pipeline
from tests.unit.ml.value_mvp._helpers import write_synthetic_inputs


@pytest.fixture
def staged_inputs(tmp_path, monkeypatch):
    """Synthetic inputs with pipeline constants patched to match them."""
    paths = write_synthetic_inputs(tmp_path)
    input_dir = tmp_path
    input_dir.mkdir(exist_ok=True)

    new_input_hashes = {}
    for path in paths["csv_dir"].glob("*.csv"):
        new_input_hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    new_counts = {}
    new_observation_hashes = {}
    for path in paths["observations_dir"].glob("*.jsonl"):
        new_counts[path.name] = sum(1 for _ in path.open("r", encoding="utf-8"))
        new_observation_hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    receipt_path = paths["observations_dir"] / "receipt.json"
    monkeypatch.setattr(pipeline, "INPUT_HASHES", new_input_hashes)
    monkeypatch.setattr(pipeline, "OBSERVATION_COUNTS", new_counts)
    monkeypatch.setattr(pipeline, "OBSERVATION_HASHES", new_observation_hashes)
    monkeypatch.setattr(
        pipeline, "RECEIPT_HASH", hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    )
    monkeypatch.setattr(
        pipeline,
        "DATA_GATES",
        {"total_eligible_min": 4, "fold1_oos_min": 1, "fold2_oos_min": 1, "pooled_oos_min": 2},
    )
    return input_dir
