"""Compatibility contract tests for the feature-adapter module boundary.

lifecycle: permanent
scope: pure refactor compatibility coverage; no provider, database, network, or model load
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

import src.ml.feature_adapter as facade
from src.ml.feature_adapter import (
    AdaptationResult,
    BaseFeatureAdapter,
    FeatureAdapterFactory,
    ModelType,
    V19RollingAdapter,
    V26_5_ProductionAdapter,
    V26_6_PreMatchAdapter,
    V26MiniAdapter,
    adapt_features,
)
from src.ml.feature_adapters.base import AdaptationResult as BaseAdaptationResult
from src.ml.feature_adapters.base import BaseFeatureAdapter as BaseAdapterType
from src.ml.feature_adapters.base import ModelType as BaseModelType
from src.ml.feature_adapters.prematch import V26_6_PreMatchAdapter as PrematchImplementation
from src.ml.feature_adapters.production import V26_5_ProductionAdapter as ProductionImplementation

EXPECTED_CANONICAL_FEATURES = [
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


def test_legacy_facade_reexports_preserve_public_identity() -> None:
    assert facade.ModelType is BaseModelType
    assert facade.AdaptationResult is BaseAdaptationResult
    assert facade.BaseFeatureAdapter is BaseAdapterType
    assert facade.V26_5_ProductionAdapter is ProductionImplementation
    assert facade.V26_6_PreMatchAdapter is PrematchImplementation

    for symbol in (
        ModelType,
        AdaptationResult,
        BaseFeatureAdapter,
        V26_5_ProductionAdapter,
        V26_6_PreMatchAdapter,
    ):
        assert symbol.__module__ == "src.ml.feature_adapter"


def test_factory_mapping_and_helper_contract_are_unchanged() -> None:
    expected = {
        ModelType.V19_ROLLING: V19RollingAdapter,
        ModelType.V26_MINI: V26MiniAdapter,
        ModelType.V26_5_PRODUCTION: V26_5_ProductionAdapter,
        ModelType.V26_6_PRE_MATCH: V26_6_PreMatchAdapter,
    }

    for model_type, adapter_type in expected.items():
        assert type(FeatureAdapterFactory.get_adapter(model_type)) is adapter_type

    with pytest.raises(ValueError, match="不支持的模型类型"):
        FeatureAdapterFactory.get_adapter(ModelType.V26_BASELINE)

    result = adapt_features({}, ModelType.V26_MINI)
    assert result.success is True
    assert result.feature_names == V26MiniAdapter.MINI_FEATURES


def test_canonical_feature_order_and_count_are_unchanged() -> None:
    features = V26_6_PreMatchAdapter().get_required_features()

    assert features == EXPECTED_CANONICAL_FEATURES
    assert len(features) == CANONICAL_FEATURE_COUNT


def test_legacy_demo_defaults_and_shapes_are_unchanged() -> None:
    mini = V26MiniAdapter().adapt({})
    assert mini.success is True
    assert mini.feature_names == V26MiniAdapter.MINI_FEATURES
    assert mini.features.to_dict("records") == [
        {
            "home_score": 0,
            "away_score": 0,
            "home_possession": 0.5,
            "away_possession": 0.5,
            "home_shots_total": 10,
            "away_shots_total": 10,
            "home_xg": 1.0,
            "away_xg": 1.0,
            "possession_diff": 0.0,
            "xg_diff": 0.0,
        }
    ]

    rolling = V19RollingAdapter().adapt({})
    assert rolling.success is True
    assert len(rolling.feature_names) == len(V19RollingAdapter.V19_FEATURES)
    assert list(rolling.features.columns) == rolling.feature_names


def test_feature_adapter_facade_import_is_filesystem_and_database_pure(tmp_path: Path) -> None:
    probe = """
import sys
from pathlib import Path

before = sorted(path.name for path in Path('.').iterdir())
import src.ml.feature_adapter
after = sorted(path.name for path in Path('.').iterdir())

assert before == after
assert 'src.database.schema_manager' not in sys.modules
"""
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[3])
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
