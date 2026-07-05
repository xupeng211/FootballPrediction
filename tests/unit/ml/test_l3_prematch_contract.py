#!/usr/bin/env python3
# ruff: noqa: PLR2004
"""Unit tests for L3 prematch-safe feature contract filter.

lifecycle: permanent
scope: GOLD-AUDIT-2F enforcement validation

Tests that the contract loader and filter functions correctly:
- retain PREMATCH_SAFE golden keys
- deny POSTMATCH_LEAKAGE rating keys
- deny_all for tactical_features
- deny unknown keys
- deny default Elo as training signal
- deny odds fallback placeholders
- deny priority over allow
- None / empty inputs are safe
"""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from typing import ClassVar

import pytest

# ---------------------------------------------------------------------------
# Load the contract module via importlib to bypass broken __init__.py chain
# ---------------------------------------------------------------------------
_PROJECT = Path(__file__).resolve().parents[3]
_SPEC = importlib.util.spec_from_file_location(
    "l3_prematch_contract",
    _PROJECT / "src" / "ml" / "features" / "l3_prematch_contract.py",
)
_mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_mod)

load_l3_prematch_contract = _mod.load_l3_prematch_contract
filter_l3_feature_group = _mod.filter_l3_feature_group
filter_l3_feature_payload = _mod.filter_l3_feature_payload

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def contract() -> dict:
    """Load the real contract from disk once per test run."""
    return load_l3_prematch_contract()


# ============================================================================
# 1. golden PREMATCH_SAFE keys retained
# ============================================================================


class TestGoldenSafeKeysRetained:
    """PREMATCH_SAFE golden keys must pass the allowlist."""

    def test_age_squad_keys(self, contract):
        features = {
            "home_age_avg": 26.5,
            "away_age_avg": 20.6,
            "age_gap": 5.9,
            "home_starters_count": 11,
            "away_starters_count": 11,
            "home_u23_count": 3,
            "away_u23_count": 9,
            "home_veteran_count": 4,
            "away_veteran_count": 0,
        }
        result = filter_l3_feature_group("golden_features", features, contract=contract)
        for key in features:
            assert key in result, f"PREMATCH_SAFE key should be retained: {key}"
        assert len(result) == len(features)

    def test_market_value_keys(self, contract):
        features = {
            "home_market_value_total": 22189037000000,
            "away_market_value_total": 141443829000000,
            "home_market_value_avg": 2017185181818,
            "away_market_value_avg": 12858529909091,
            "home_market_value_raw": 22189037,
            "away_market_value_raw": 141443829,
            "market_value_gap": -119254792000000,
            "market_value_ratio": 0.157,
        }
        result = filter_l3_feature_group("golden_features", features, contract=contract)
        for key in features:
            assert key in result, f"market value key should be retained: {key}"

    def test_injury_suspension_keys(self, contract):
        features = {
            "home_injury_count": 1,
            "away_injury_count": 3,
            "injury_count_gap": -2,
            "home_injury_doubtful_count": 0,
            "away_injury_doubtful_count": 0,
            "home_injury_injury_count": 0,
            "away_injury_injury_count": 1,
            "home_injury_suspension_count": 1,
            "away_injury_suspension_count": 2,
        }
        result = filter_l3_feature_group("golden_features", features, contract=contract)
        for key in features:
            assert key in result, f"injury key should be retained: {key}"


# ============================================================================
# 2. golden rating fields denied
# ============================================================================


class TestGoldenRatingDenied:
    """POSTMATCH_LEAKAGE rating fields must be denied by exact and pattern rules."""

    RATING_KEYS: ClassVar[list[str]] = [
        "home_rating_avg",
        "away_rating_avg",
        "home_rating_std",
        "away_rating_std",
        "home_rating_max",
        "away_rating_max",
        "home_rating_min",
        "away_rating_min",
        "home_rating_available_count",
        "away_rating_available_count",
        "home_rating_average_count",
        "away_rating_average_count",
        "home_rating_excellent_count",
        "away_rating_excellent_count",
        "home_rating_good_count",
        "away_rating_good_count",
        "home_rating_poor_count",
        "away_rating_poor_count",
        "rating_gap",
    ]

    def test_all_rating_keys_exact_denied(self, contract):
        for key in self.RATING_KEYS:
            result = filter_l3_feature_group("golden_features", {key: 7.0}, contract=contract)
            assert key not in result, f"rating key must be denied: {key}"
            assert len(result) == 0, f"expected empty for {key}, got {result}"

    def test_mixed_safe_and_unsafe(self, contract):
        features = {
            "home_age_avg": 26.5,
            "home_rating_avg": 6.97,
            "away_rating_avg": 7.12,
            "rating_gap": -0.15,
            "home_market_value_total": 22189037000000,
        }
        result = filter_l3_feature_group("golden_features", features, contract=contract)
        assert "home_age_avg" in result
        assert "home_market_value_total" in result
        assert "home_rating_avg" not in result
        assert "away_rating_avg" not in result
        assert "rating_gap" not in result

    def test_rating_pattern_deny_catches_variants(self, contract):
        """Pattern .*rating.* must catch any future rating-like keys."""
        result = filter_l3_feature_group(
            "golden_features", {"new_player_rating": 8.0}, contract=contract
        )
        assert len(result) == 0, "pattern .*rating.* should catch new_player_rating"

        result = filter_l3_feature_group(
            "golden_features", {"rating_score": 5.5}, contract=contract
        )
        assert len(result) == 0, "pattern .*rating.* should catch rating_score"


# ============================================================================
# 3. tactical_features all denied
# ============================================================================


class TestTacticalAllDenied:
    """tactical_features must return empty dict in prematch mode."""

    TACTICAL_KEYS: ClassVar[list[str]] = [
        "home_xg",
        "away_xg",
        "home_shots",
        "away_shots",
        "home_shots_on_target",
        "away_shots_on_target",
        "home_possession",
        "away_possession",
        "home_corners",
        "away_corners",
        "home_passes",
        "away_passes",
        "momentum_overall_mean",
        "momentum_direction",
        "home_yellow_cards",
        "away_yellow_cards",
        "xg_diff",
        "xg_ratio",
        "total_xg",
    ]

    def test_all_tactical_denied(self, contract):
        features = dict.fromkeys(self.TACTICAL_KEYS, 1.0)
        result = filter_l3_feature_group("tactical_features", features, contract=contract)
        assert len(result) == 0, f"tactical must be empty, got {len(result)} keys"

    def test_tactical_denied_even_with_safe_looking_key(self, contract):
        """Even keys that look benign must be denied — tactical is deny_all."""
        result = filter_l3_feature_group(
            "tactical_features", {"has_momentum_data": True}, contract=contract
        )
        assert len(result) == 0

    def test_tactical_allowed_in_diagnostic_mode(self, contract):
        features = {"home_xg": 0.59, "home_shots": 11}
        result = filter_l3_feature_group(
            "tactical_features",
            features,
            allow_diagnostic_postmatch=True,
            contract=contract,
        )
        assert len(result) == len(features)


# ============================================================================
# 4. unknown key default deny
# ============================================================================


class TestUnknownKeyDenied:
    """Keys not in the allowlist must be denied."""

    def test_unknown_golden_key(self, contract):
        result = filter_l3_feature_group(
            "golden_features", {"some_new_future_key": 123}, contract=contract
        )
        assert len(result) == 0

    def test_unknown_group(self, contract):
        result = filter_l3_feature_group("future_feature_group", {"x": 1}, contract=contract)
        assert len(result) == 0

    def test_metadata_key_denied(self, contract):
        """_extractedAt is metadata, not a feature."""
        result = filter_l3_feature_group(
            "golden_features", {"_extractedAt": "2026-01-01T00:00:00Z"}, contract=contract
        )
        assert "_extractedAt" not in result


# ============================================================================
# 5. default Elo denied
# ============================================================================


class TestDefaultEloDenied:
    """Elo with _is_default=true must be denied as training signal."""

    def test_default_elo_denied(self, contract):
        features = {"_is_default": True, "home_elo": 1500, "away_elo": 1500, "elo_diff": 0}
        result = filter_l3_feature_group("elo_features", features, contract=contract)
        assert len(result) == 0, "default Elo must be denied"

    def test_default_elo_denied_even_if_keys_match(self, contract):
        """Even if the keys look like valid Elo, conditional_safe without
        include_conditional must deny."""
        result = filter_l3_feature_group(
            "elo_features",
            {"home_elo": 1500, "away_elo": 1500, "elo_diff": 0, "_is_default": True},
            include_conditional=False,
            contract=contract,
        )
        assert len(result) == 0


# ============================================================================
# 6. odds fallback denied
# ============================================================================


class TestOddsFallbackDenied:
    """Fallback odds with has_odds_data=false must be denied."""

    def test_missing_odds_denied(self, contract):
        features = {
            "has_odds_data": False,
            "_data_quality": "INCOMPLETE_ODDS",
            "_error": "No odds data available",
            "current_home_odds": 0,
            "current_draw_odds": 0,
            "current_away_odds": 0,
            "implied_prob_home": 0.333,
            "implied_prob_draw": 0.333,
            "implied_prob_away": 0.333,
        }
        result = filter_l3_feature_group("odds_movement_features", features, contract=contract)
        assert len(result) == 0, "odds fallback must be denied"

    def test_odds_features_empty_group_denied(self, contract):
        """odds_features (separate group) is conditional_safe, denied by default."""
        result = filter_l3_feature_group(
            "odds_features", {"initial_home_odds": 2.0}, contract=contract
        )
        assert len(result) == 0


# ============================================================================
# 7. deny priority over allow
# ============================================================================


class TestDenyPriorityOverAllow:
    """Denylist must take priority over allowlist."""

    def test_rating_not_allowed_even_if_hypothetically_in_allowlist(self, contract):
        """Even if a rating key were added to the allowlist, the denylist
        (exact + pattern) must still block it.  This test verifies the
        deny-before-allow execution order."""
        # Simulate: modify the allowlist locally to include a denied key,
        # then verify the deny still wins.
        c = copy.deepcopy(contract)
        c["feature_groups"]["golden_features"]["prematch_safe_allowlist"].append("home_rating_avg")
        result = filter_l3_feature_group("golden_features", {"home_rating_avg": 6.97}, contract=c)
        assert "home_rating_avg" not in result, "deny_exact must override allowlist"


# ============================================================================
# 8. None / empty safe handling
# ============================================================================


class TestNoneEmptySafe:
    """None and empty inputs must be handled safely."""

    def test_none_input(self, contract):
        result = filter_l3_feature_group("golden_features", None, contract=contract)
        assert result == {}

    def test_empty_dict_input(self, contract):
        result = filter_l3_feature_group("golden_features", {}, contract=contract)
        assert result == {}

    def test_none_group_in_payload(self, contract):
        result = filter_l3_feature_group("golden_features", None, contract=contract)
        assert result == {}

    def test_string_input(self, contract):
        """Non-dict input must not crash."""
        result = filter_l3_feature_group("golden_features", "not_a_dict", contract=contract)
        assert result == {}


# ============================================================================
# 9. filter_l3_feature_payload integration
# ============================================================================


class TestFilterPayloadIntegration:
    """End-to-end payload filtering."""

    def test_mixed_payload(self, contract):
        payload = {
            "golden_features": {
                "home_age_avg": 26.5,
                "home_rating_avg": 6.97,
                "home_market_value_total": 22189037000000,
                "home_injury_count": 1,
            },
            "tactical_features": {
                "home_xg": 0.59,
                "away_xg": 2.02,
                "home_shots": 11,
            },
            "odds_movement_features": {
                "has_odds_data": False,
                "current_home_odds": 0,
            },
            "elo_features": {
                "_is_default": True,
                "home_elo": 1500,
            },
            "rolling_features": {},
            "unknown_group": {"x": 1},
        }
        filtered = filter_l3_feature_payload(payload, contract=contract)

        # golden: safe retained, rating denied
        assert "home_age_avg" in filtered["golden_features"]
        assert "home_market_value_total" in filtered["golden_features"]
        assert "home_injury_count" in filtered["golden_features"]
        assert "home_rating_avg" not in filtered["golden_features"]

        # tactical: all denied
        assert filtered["tactical_features"] == {}

        # odds: fallback denied
        assert filtered["odds_movement_features"] == {}

        # elo: default denied
        assert filtered["elo_features"] == {}

        # empty group passthrough
        assert filtered["rolling_features"] == {}

        # unknown group denied
        assert filtered["unknown_group"] == {}

        # _dropped summary
        assert "_dropped" in filtered
        assert filtered["_dropped"]["golden_features"] >= 1
        assert filtered["_dropped"]["tactical_features"] == 3

    def test_all_empty_payload(self, contract):
        filtered = filter_l3_feature_payload({}, contract=contract)
        assert filtered == {"_dropped": {}}


# ============================================================================
# 10. contract file integrity
# ============================================================================


class TestContractFileIntegrity:
    """The JSON contract file itself must be well-formed and consistent."""

    def test_can_load_from_disk(self):
        contract = load_l3_prematch_contract()
        assert contract["_meta"]["version"] == "v0"
        assert "feature_groups" in contract

    def test_all_known_groups_have_config(self, contract):
        known = {
            "golden_features",
            "tactical_features",
            "odds_movement_features",
            "odds_features",
            "elo_features",
            "rolling_features",
            "efficiency_features",
            "draw_features",
            "market_sentiment",
            "stitch_summary",
        }
        assert set(contract["feature_groups"].keys()) == known

    def test_golden_allowlist_is_non_empty(self, contract):
        allowlist = contract["feature_groups"]["golden_features"]["prematch_safe_allowlist"]
        assert len(allowlist) >= 30, (
            f"expected at least 30 prematch-safe keys, got {len(allowlist)}"
        )

    def test_golden_denylist_is_non_empty(self, contract):
        deny_exact = contract["feature_groups"]["golden_features"]["deny_exact"]
        assert len(deny_exact) >= 15, (
            f"expected at least 15 denied rating keys, got {len(deny_exact)}"
        )

    def test_tactical_deny_all(self, contract):
        assert contract["feature_groups"]["tactical_features"]["deny_all"] is True

    def test_no_overlap_between_allow_and_deny(self, contract):
        """The allowlist and explicit denylist must be disjoint."""
        cfg = contract["feature_groups"]["golden_features"]
        allow_set = set(cfg["prematch_safe_allowlist"])
        deny_set = set(cfg["deny_exact"])
        overlap = allow_set & deny_set
        assert not overlap, f"allowlist and denylist overlap: {overlap}"

    def test_no_rating_keys_in_allowlist(self, contract):
        allowlist = contract["feature_groups"]["golden_features"]["prematch_safe_allowlist"]
        for key in allowlist:
            assert "rating" not in key.lower(), f"rating key in allowlist: {key}"
            assert key != "rating_gap", "rating_gap must not be in allowlist"
