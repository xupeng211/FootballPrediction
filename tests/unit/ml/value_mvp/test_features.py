"""Sequential feature generation tests: chronology, Elo, rolling windows."""

from __future__ import annotations

import math

import numpy as np
import pytest

from src.ml.value_mvp.features import (
    INITIAL_ELO,
    K_FACTOR,
    POINTS_DRAW,
    POINTS_WIN,
    build_feature_frame,
)
from src.ml.value_mvp.sources import Match, build_dataset, load_csv_rows, load_observations
from tests.unit.ml.value_mvp._helpers import synthetic_protocol, write_synthetic_inputs


def _matches_from_inputs(tmp_path) -> list[Match]:
    paths = write_synthetic_inputs(tmp_path)
    return build_dataset(
        load_observations(paths["observations_dir"]),
        load_csv_rows(paths["csv_dir"]),
        synthetic_protocol(),
    )


def _match(mid, kickoff, home, away, label_str, home_goals=1, away_goals=1):
    return Match(
        mid=mid,
        kickoff_at=kickoff,
        home=home,
        away=away,
        season="2022/23",
        label={"H": 0, "D": 1, "A": 2}[label_str],
        label_str=label_str,
        home_goals=home_goals,
        away_goals=away_goals,
    )


def test_feature_frame_initial_state_has_nan_windows_and_seen_zero():
    match = _match("m1", "2022-08-06T14:00:00+01:00", "Alpha FC", "Beta FC", "H")
    rows = build_feature_frame([match])
    row = rows[0]
    assert row["home_elo_pre"] == INITIAL_ELO
    assert row["away_elo_pre"] == INITIAL_ELO
    assert row["elo_diff"] == pytest.approx(0.0)
    assert math.isnan(row["home_last5_ppg"])
    assert math.isnan(row["home_last5_goals_for"])
    assert math.isnan(row["home_last5_home_ppg"])
    assert row["home_matches_seen"] == 0.0


def test_same_kickoff_batch_prevents_result_peeking():
    first = _match("m1", "2022-08-06T14:00:00+01:00", "Alpha FC", "Beta FC", "H")
    second = _match("m2", "2022-08-06T14:00:00+01:00", "Gamma FC", "Delta FC", "A")
    rows = build_feature_frame([first, second])
    # second match must not see the first match's result: elo still initial,
    # matches_seen still 0.
    assert rows[1]["away_elo_pre"] == INITIAL_ELO
    assert rows[1]["away_matches_seen"] == 0.0
    assert math.isnan(rows[1]["away_last5_ppg"])


def test_elo_updates_after_feature_emission():
    home_win = _match("m1", "2022-08-06T14:00:00+01:00", "Alpha FC", "Beta FC", "H")
    later = _match("m2", "2022-08-13T14:00:00+01:00", "Alpha FC", "Gamma FC", "A")
    rows = build_feature_frame([home_win, later])
    # After a home win by the initial-strength favorite-less team, its elo rises.
    assert rows[1]["home_elo_pre"] > INITIAL_ELO
    assert rows[1]["home_matches_seen"] == 1.0
    assert rows[1]["home_last5_ppg"] == POINTS_WIN


def test_elo_update_magnitude_follows_k_factor_and_expected_score():
    strong = _match("m1", "2022-08-06T14:00:00+01:00", "Alpha FC", "Beta FC", "H")
    later = _match("m2", "2022-08-13T14:00:00+01:00", "Alpha FC", "Gamma FC", "H")
    rows = build_feature_frame([strong, later])
    # Alpha gained K_FACTOR * (1 - expected_score_against_equal_opponent).
    expected = 1.0 / (1.0 + 10.0 ** ((INITIAL_ELO - INITIAL_ELO) / 400.0))
    assert rows[1]["home_elo_pre"] == pytest.approx(INITIAL_ELO + K_FACTOR * (1.0 - expected))
    # Beta lost the same amount.
    later_beta = _match("m3", "2022-08-20T14:00:00+01:00", "Beta FC", "Delta FC", "A")
    rows3 = build_feature_frame([strong, later_beta])
    assert rows3[1]["home_elo_pre"] == pytest.approx(INITIAL_ELO + K_FACTOR * (0.0 - expected))


def test_rolling_window_trimmed_to_five():
    matches = [
        _match(f"m{i}", f"2022-08-0{i + 1}T14:00:00+01:00", "Alpha FC", f"Opp {i}", "H")
        for i in range(6)
    ]
    rows = build_feature_frame(matches)
    # after 6 matches, the window for match 6 uses exactly the last 5.
    assert rows[5]["home_matches_seen"] == 5.0
    assert rows[5]["home_last5_ppg"] == POINTS_WIN


def test_home_away_split_ppg_uses_only_relevant_side():
    first_home = _match("m1", "2022-08-06T14:00:00+01:00", "Alpha FC", "Beta FC", "H")
    first_away = _match("m2", "2022-08-13T14:00:00+01:00", "Gamma FC", "Alpha FC", "D")
    later_home = _match("m3", "2022-08-20T14:00:00+01:00", "Alpha FC", "Delta FC", "H")
    rows = build_feature_frame([first_home, first_away, later_home])
    # row 3's features are frozen BEFORE m3 kicks off: Alpha has played m1 (win)
    # and m2 (away draw) only.
    # home_last5_home_ppg: only the m1 home win -> 3.0
    assert rows[2]["home_last5_home_ppg"] == pytest.approx(POINTS_WIN)
    # home_last5_ppg: the two completed games (3, 1) -> 2.0
    assert rows[2]["home_last5_ppg"] == pytest.approx((3 + POINTS_DRAW) / 2)
    # away_last5_away_ppg: Delta (m3's away side) has not played yet -> NaN
    assert math.isnan(rows[2]["away_last5_away_ppg"])


def test_goal_features_track_goals_for_and_against():
    first = _match(
        "m1", "2022-08-06T14:00:00+01:00", "Alpha FC", "Beta FC", "H", home_goals=2, away_goals=1
    )
    second = _match(
        "m2", "2022-08-13T14:00:00+01:00", "Alpha FC", "Gamma FC", "A", home_goals=0, away_goals=3
    )
    rows = build_feature_frame([first, second])
    # row 2 is frozen before m2; only Alpha's m1 history exists, Gamma is new.
    assert rows[1]["home_last5_goals_for"] == pytest.approx(2.0)
    assert rows[1]["home_last5_goals_against"] == pytest.approx(1.0)
    assert math.isnan(rows[1]["away_last5_goals_for"])
    assert math.isnan(rows[1]["away_last5_goals_against"])


def test_feature_frame_chronological_order_matches_input(tmp_path):
    matches = _matches_from_inputs(tmp_path)
    rows = build_feature_frame(matches)
    kickoffs = [m.kickoff_at for m in matches]
    assert kickoffs == sorted(kickoffs)
    assert len(rows) == len(matches)
    for row in rows:
        assert set(row) == {
            "home_elo_pre",
            "away_elo_pre",
            "elo_diff",
            "home_last5_ppg",
            "away_last5_ppg",
            "home_last5_goals_for",
            "away_last5_goals_for",
            "home_last5_goals_against",
            "away_last5_goals_against",
            "home_last5_home_ppg",
            "away_last5_away_ppg",
            "home_matches_seen",
            "away_matches_seen",
        }
        for value in row.values():
            assert np.isfinite(value) or math.isnan(value)
