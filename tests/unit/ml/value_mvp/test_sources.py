"""Source loading and dataset construction tests (synthetic, hermetic)."""

from __future__ import annotations

import pytest

from src.ml.value_mvp.protocol import season_of_kickoff
from src.ml.value_mvp.sources import (
    Match,
    build_dataset,
    csv_row_for,
    evaluation_population_hash,
    load_csv_rows,
    load_observations,
    season_counts,
)
from tests.unit.ml.value_mvp._helpers import synthetic_protocol, write_synthetic_inputs

RULE = "kickoff_at month >= 8 -> YYYY/YYYY+1 else (YYYY-1)/YYYY"


def _load(tmp_path):
    paths = write_synthetic_inputs(tmp_path)
    csv_rows = load_csv_rows(paths["csv_dir"])
    observations = load_observations(paths["observations_dir"])
    protocol = synthetic_protocol()
    matches = build_dataset(observations, csv_rows, protocol)
    return matches, csv_rows, protocol


def test_csv_row_for_header_offset_mapping(tmp_path):
    """Locator row N = CSV line N; header is line 1, so row 2 is index 0."""
    paths = write_synthetic_inputs(tmp_path)
    csv_rows = load_csv_rows(paths["csv_dir"])
    first_row = csv_row_for(csv_rows, "raw_odds_2223", 2)
    assert first_row["FTR"] in {"H", "A", "D"}
    with pytest.raises(ValueError, match="out of range"):
        csv_row_for(csv_rows, "raw_odds_2223", 999999)


def test_build_dataset_joins_observations_labels_and_odds(tmp_path):
    matches, _csv_rows, _protocol = _load(tmp_path)
    by_mid = {match.mid: match for match in matches}
    assert len(matches) == 8
    match = by_mid["47_2022_101"]
    assert match.home == "Alpha FC"
    assert match.away == "Beta FC"
    assert match.label == 0
    assert match.label_str == "H"
    assert match.home_goals == 2
    assert match.away_goals == 1
    assert match.season == "2022/23"
    closing = match.odds["closing"]
    assert closing["b1"]["home"] == pytest.approx(1.8)
    assert closing["b2"]["away"] == pytest.approx(4.8)
    assert match.sources[0][0] in {"raw_odds_2223", "raw_odds_2324", "real_odds_raw"}


def test_build_dataset_season_assignment(tmp_path):
    matches, _csv_rows, _protocol = _load(tmp_path)
    by_mid = {match.mid: match for match in matches}
    assert by_mid["47_2022_101"].season == "2022/23"
    assert by_mid["47_2023_201"].season == "2023/24"
    assert by_mid["47_2024_301"].season == "2024/25"
    for match in matches:
        assert season_of_kickoff(match.kickoff_at, RULE) == match.season


def test_build_dataset_rejects_conflicting_kickoff(tmp_path):
    paths = write_synthetic_inputs(tmp_path)
    csv_rows = load_csv_rows(paths["csv_dir"])
    observations = load_observations(paths["observations_dir"])
    observations[0]["kickoff_at"] = "2023-01-01T12:00:00+00:00"
    with pytest.raises(ValueError, match="conflicting kickoff"):
        build_dataset(observations, csv_rows, synthetic_protocol())


def test_build_dataset_rejects_conflicting_label(tmp_path):
    paths = write_synthetic_inputs(tmp_path)
    csv_rows = load_csv_rows(paths["csv_dir"])
    observations = load_observations(paths["observations_dir"])
    # rewrite the FTR of the CSV row behind the first observation
    first = observations[0]
    row = csv_row_for(csv_rows, first["_source"], 2)
    row["FTR"] = "A"
    with pytest.raises(ValueError, match="conflicting FTR"):
        build_dataset(observations, csv_rows, synthetic_protocol())


def test_build_dataset_rejects_missing_matched_id(tmp_path):
    paths = write_synthetic_inputs(tmp_path)
    csv_rows = load_csv_rows(paths["csv_dir"])
    observations = load_observations(paths["observations_dir"])
    observations[0]["match_link"] = {}
    with pytest.raises(ValueError, match="matched_id"):
        build_dataset(observations, csv_rows, synthetic_protocol())


def test_evaluation_population_hash_deterministic_and_sensitive(tmp_path):
    matches_a, _csv_rows, _protocol = _load(tmp_path)
    matches_b, _csv_rows, _protocol = _load(tmp_path)
    assert evaluation_population_hash(matches_a) == evaluation_population_hash(matches_b)
    matches_c = [
        Match(
            mid=m.mid,
            kickoff_at=m.kickoff_at,
            home=m.home,
            away=m.away,
            season=m.season,
            label=m.label,
            label_str=m.label_str,
            home_goals=m.home_goals,
            away_goals=m.away_goals,
            odds=m.odds,
            sources=m.sources,
        )
        for m in matches_a
    ]
    matches_c[0].home = "Renamed FC"
    assert evaluation_population_hash(matches_c) != evaluation_population_hash(matches_a)


def test_season_counts(tmp_path):
    matches, _csv_rows, _protocol = _load(tmp_path)
    assert season_counts(matches) == {"2022/23": 6, "2023/24": 1, "2024/25": 1}
