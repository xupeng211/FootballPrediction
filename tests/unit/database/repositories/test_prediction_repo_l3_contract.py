#!/usr/bin/env python3
# ruff: noqa: PLR2004
"""Unit tests for prediction path L3 prematch contract enforcement.

lifecycle: permanent
scope: GOLD-AUDIT-2H enforcement validation

Tests that prediction_repo._filter_prediction_l3 correctly:
- retains golden PREMATCH_SAFE keys (market value)
- denies golden POSTMATCH_LEAKAGE rating keys
- denies tactical_features entirely (deny_all)
- denies default Elo as prediction signal
- handles None / empty / non-dict inputs safely
- is idempotent (double-filter = same result)
- extract_features survives empty filtered groups
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any, ClassVar

import pytest

# ---------------------------------------------------------------------------
# Load the contract module via importlib (same pattern as training code)
# ---------------------------------------------------------------------------
_PROJECT = Path(__file__).resolve().parents[4]
_SPEC = importlib.util.spec_from_file_location(
    "l3_prematch_contract",
    _PROJECT / "src" / "ml" / "features" / "l3_prematch_contract.py",
)
_mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_mod)

load_l3_prematch_contract = _mod.load_l3_prematch_contract
filter_l3_feature_group = _mod.filter_l3_feature_group

# ---------------------------------------------------------------------------
# Load the prediction_repo module (same importlib pattern — the file itself
# also uses importlib internally, so we only test its helper functions here).
# ---------------------------------------------------------------------------
_REPO_PATH = _PROJECT / "src" / "database" / "repositories" / "prediction_repo.py"
_REPO_SPEC = importlib.util.spec_from_file_location(
    "prediction_repo",
    str(_REPO_PATH),
)
_prediction_repo = importlib.util.module_from_spec(_REPO_SPEC)
_REPO_SPEC.loader.exec_module(_prediction_repo)

_filter_prediction_l3 = _prediction_repo._filter_prediction_l3
extract_features = _prediction_repo.extract_features
safe_float = _prediction_repo.safe_float

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def contract() -> dict[str, Any]:
    """Load the real contract from disk once per test run."""
    return load_l3_prematch_contract()


# ============================================================================
# 1. golden rating fields removed
# ============================================================================


class TestGoldenRatingDenied:
    """Unsafe golden rating keys must be stripped."""

    def test_rating_keys_removed(self) -> None:
        golden = {
            "home_market_value_total": 150000000,
            "away_market_value_total": 80000000,
            "home_age_avg": 27.3,
            "home_rating_avg": 7.1,
            "away_rating_avg": 6.8,
            "rating_gap": 0.5,
            "home_rating_max": 8.5,
            "home_rating_excellent_count": 2,
        }
        result = _filter_prediction_l3(golden_features=golden)
        gf = result["golden_features"]

        # PREMATCH_SAFE retained
        assert "home_market_value_total" in gf
        assert "away_market_value_total" in gf
        assert "home_age_avg" in gf

        # POSTMATCH_LEAKAGE denied
        assert "home_rating_avg" not in gf
        assert "away_rating_avg" not in gf
        assert "rating_gap" not in gf
        assert "home_rating_max" not in gf
        assert "home_rating_excellent_count" not in gf

    def test_only_safe_keys_survive(self) -> None:
        """No rating key should sneak through the deny_patterns."""
        golden = {
            f"home_rating_{s}": float(i)
            for i, s in enumerate(
                [
                    "avg",
                    "std",
                    "max",
                    "min",
                    "available_count",
                    "average_count",
                    "excellent_count",
                    "good_count",
                    "poor_count",
                ],
            )
        }
        golden["away_rating_avg"] = 6.5
        golden["rating_gap"] = 0.2
        golden["home_market_value_total"] = 100000000  # safe key

        result = _filter_prediction_l3(golden_features=golden)
        gf = result["golden_features"]

        assert "home_market_value_total" in gf
        # Every rating key must be gone
        for key in golden:
            if "rating" in key.lower():
                assert key not in gf, f"rating key {key} should be denied"


# ============================================================================
# 2. tactical postmatch fields removed
# ============================================================================


class TestTacticalDenied:
    """tactical_features must be entirely empty in prematch mode."""

    def test_tactical_empty_after_filter(self) -> None:
        tactical = {
            "home_xg": 2.1,
            "away_xg": 0.8,
            "home_shots": 14,
            "away_shots": 5,
            "home_shots_on_target": 6,
            "away_shots_on_target": 2,
            "home_possession": 58.3,
            "away_possession": 41.7,
            "momentum_overall_mean": 22.5,
            "home_corners": 7,
            "away_corners": 3,
            "home_yellow_cards": 2,
            "away_yellow_cards": 1,
        }
        result = _filter_prediction_l3(tactical_features=tactical)
        tf = result["tactical_features"]

        assert tf == {}, f"tactical_features must be empty, got {tf}"

    def test_tactical_even_small_payload_denied(self) -> None:
        result = _filter_prediction_l3(tactical_features={"home_xg": 1.0})
        assert result["tactical_features"] == {}


# ============================================================================
# 3. default Elo denied
# ============================================================================


class TestDefaultEloDenied:
    """When _is_default=True, elo_features must be empty in prematch mode."""

    def test_default_elo_denied(self) -> None:
        elo = {
            "_is_default": True,
            "home_elo_pre": 1500,
            "away_elo_pre": 1500,
            "elo_diff": 0,
            "expected_home_win": 0.45,
            "expected_away_win": 0.30,
            "k_factor_home": 32,
            "k_factor_away": 32,
        }
        result = _filter_prediction_l3(elo_features=elo)
        ef = result["elo_features"]

        # In prematch mode (include_conditional=False), conditional_safe
        # with default_action="deny_when_default" returns {}.
        assert ef == {}, f"default Elo must be denied in prematch mode, got {ef}"

    def test_non_default_elo_not_tested_no_data(self) -> None:
        """Without real non-default Elo data, this is a placeholder.

        When real Elo data with _is_default=False exists, it should be retained
        per the contract's allow_only_when conditions.
        """
        # This test documents expected behavior — real data needed to verify.
        pytest.skip("Real non-default Elo data not yet available")


# ============================================================================
# 4. None / empty / non-dict inputs are safe
# ============================================================================


class TestNoneEmptySafe:
    """Contract filter must not crash on None, {}, non-dict inputs."""

    def test_all_none(self) -> None:
        result = _filter_prediction_l3(
            elo_features=None,
            golden_features=None,
            tactical_features=None,
        )
        assert result["elo_features"] == {}
        assert result["golden_features"] == {}
        assert result["tactical_features"] == {}

    def test_all_empty_dict(self) -> None:
        result = _filter_prediction_l3(
            elo_features={},
            golden_features={},
            tactical_features={},
        )
        assert result["elo_features"] == {}
        assert result["golden_features"] == {}
        assert result["tactical_features"] == {}

    def test_non_dict_string_passthrough(self) -> None:
        """Non-dict input should be handled without crash."""
        result = _filter_prediction_l3(
            elo_features="not_a_dict",  # type: ignore[arg-type]
        )
        assert isinstance(result["elo_features"], dict)
        assert result["elo_features"] == {}

    def test_unknown_group_returns_empty(self) -> None:
        """Calling filter_l3_feature_group with unknown group name returns {}."""
        result = filter_l3_feature_group("nonexistent_group", {"key": 1})
        assert result == {}


# ============================================================================
# 5. extract_features survives empty filtered groups
# ============================================================================


class TestExtractFeaturesFallback:
    """extract_features() must not crash when all groups are empty."""

    def test_all_empty_no_crash(self) -> None:
        f, h2h_est = extract_features(
            elo_data={},
            lineup_data={},
            h2h_data={},
        )
        # Should return a dict with expected keys (from DEFAULT_VALUES)
        assert isinstance(f, dict)
        assert len(f) > 0
        # H2H should be estimated when data is empty
        assert h2h_est is True

    def test_elo_empty_defaults_used(self) -> None:
        f, _ = extract_features(elo_data={}, lineup_data={}, h2h_data={})
        # Default Elo values should be used
        assert f.get("home_elo_pre") == 1500.0
        assert f.get("away_elo_pre") == 1500.0

    def test_golden_missing_market_value_no_crash(self) -> None:
        f, _ = extract_features(
            elo_data={},
            lineup_data={},  # no market value keys
            h2h_data={},
        )
        # Should default to neutral log values
        assert "log_home_squad_value" in f
        assert "log_away_squad_value" in f
        assert f["home_mv_share"] == 0.5

    def test_partial_golden_still_works(self) -> None:
        """Only market value keys present, no rating keys — should work fine."""
        f, _ = extract_features(
            elo_data={"home_elo_pre": 1600, "away_elo_pre": 1400, "elo_diff": 200},
            lineup_data={
                "home_market_value_total": 200000000,
                "away_market_value_total": 100000000,
            },
            h2h_data={},
        )
        assert f["home_elo_pre"] == 1600.0
        assert f["away_elo_pre"] == 1400.0
        # H2H estimated from Elo diff
        assert "h2h_home_win_ratio" in f


# ============================================================================
# 6. no unsafe raw passthrough
# ============================================================================


class TestNoUnsafePassthrough:
    """Filtered output must not contain known postmatch leakage keys."""

    UNSAFE_KEYS: ClassVar[list[str]] = [
        "home_xg",
        "away_xg",
        "home_shots",
        "away_shots",
        "home_shots_on_target",
        "away_shots_on_target",
        "home_rating_avg",
        "away_rating_avg",
        "rating_gap",
        "momentum_overall_mean",
        "home_possession",
        "away_possession",
        "home_corners",
        "away_corners",
    ]

    def test_no_unsafe_in_filtered_output(self) -> None:
        """After filtering, no unsafe key should appear in any group."""
        golden = dict.fromkeys(TestNoUnsafePassthrough.UNSAFE_KEYS, 1.0)
        golden["home_market_value_total"] = 100000000  # one safe key

        tactical = dict.fromkeys(TestNoUnsafePassthrough.UNSAFE_KEYS, 1.0)

        result = _filter_prediction_l3(
            golden_features=golden,
            tactical_features=tactical,
        )

        for group_name, group_data in result.items():
            if group_name == "_dropped":
                continue
            for unsafe in self.UNSAFE_KEYS:
                assert unsafe not in group_data, f"UNSAFE key '{unsafe}' found in {group_name}"


# ============================================================================
# 7. filter is idempotent
# ============================================================================


class TestFilterIdempotent:
    """Running the filter twice on the same input must produce the same output."""

    def test_double_filter_same_result(self) -> None:
        golden = {
            "home_market_value_total": 150000000,
            "away_market_value_total": 80000000,
            "home_age_avg": 27.3,
            "home_rating_avg": 7.1,  # should be denied
            "rating_gap": 0.5,  # should be denied
        }
        tactical = {
            "home_xg": 2.1,
            "away_xg": 0.8,
        }

        first = _filter_prediction_l3(
            golden_features=golden,
            tactical_features=tactical,
        )
        second = _filter_prediction_l3(
            golden_features=first["golden_features"],
            tactical_features=first["tactical_features"],
        )

        assert first["golden_features"] == second["golden_features"]
        assert first["tactical_features"] == second["tactical_features"]

    def test_triple_filter_same(self) -> None:
        golden = {
            "home_market_value_total": 150000000,
            "home_rating_avg": 7.1,
            "rating_gap": 0.5,
        }
        first = _filter_prediction_l3(golden_features=golden)
        second = _filter_prediction_l3(golden_features=first["golden_features"])
        third = _filter_prediction_l3(golden_features=second["golden_features"])

        assert first["golden_features"] == second["golden_features"]
        assert second["golden_features"] == third["golden_features"]


# ============================================================================
# 8. contract consistency: prediction filter matches direct filter
# ============================================================================


class TestPredictionFilterMatchesDirectFilter:
    """_filter_prediction_l3 must produce the same results as calling
    filter_l3_feature_group directly with the same contract defaults."""

    def test_golden_consistent_with_direct(self) -> None:
        golden = {
            "home_market_value_total": 150000000,
            "away_market_value_total": 80000000,
            "home_age_avg": 27.3,
            "home_rating_avg": 7.1,
            "rating_gap": 0.5,
            "unknown_key_xyz": 999,
        }
        contract = load_l3_prematch_contract()

        direct = filter_l3_feature_group(
            "golden_features",
            golden,
            contract=contract,
        )
        via_helper = _filter_prediction_l3(golden_features=golden)

        assert via_helper["golden_features"] == direct

    def test_tactical_consistent_with_direct(self) -> None:
        tactical = {"home_xg": 2.1, "away_shots": 14}
        contract = load_l3_prematch_contract()

        direct = filter_l3_feature_group(
            "tactical_features",
            tactical,
            contract=contract,
        )
        via_helper = _filter_prediction_l3(tactical_features=tactical)

        assert via_helper["tactical_features"] == direct
        assert via_helper["tactical_features"] == {}
