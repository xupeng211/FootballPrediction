"""Leakage guard tests: feature names and random-split scan."""

from __future__ import annotations

from src.ml.value_mvp.leakage import feature_name_violations, scan_business_path_for_random_split
from src.ml.value_mvp.protocol import FEATURE_NAMES


def test_feature_names_contract_have_no_forbidden_collisions():
    assert feature_name_violations(FEATURE_NAMES) == []


def test_feature_name_violations_detect_forbidden_keyword():
    assert feature_name_violations(("home_odds_x", "away_result_y")) == [
        "home_odds_x collides with forbidden keyword odds",
        "away_result_y collides with forbidden keyword result",
    ]


def test_scan_business_path_detects_random_split(tmp_path):
    (tmp_path / "clean.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    (tmp_path / "dirty.py").write_text(
        "from sklearn.model_selection import train_test_split\n", encoding="utf-8"
    )
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "optuna_search.py").write_text("optuna = Optuna()\n", encoding="utf-8")
    violations = scan_business_path_for_random_split([tmp_path])
    paths = [violation.split(":")[0] for violation in violations]
    assert "dirty.py" in paths
    assert "nested/optuna_search.py" in paths
    assert "clean.py" not in paths


def test_scan_business_path_missing_root_is_noop(tmp_path):
    assert scan_business_path_for_random_split([tmp_path / "does-not-exist"]) == []
