"""Hermetic synthetic fixtures for VALUE_MVP-1 tests (no DB, no network)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from src.ml.value_mvp.protocol import FEATURE_NAMES

if TYPE_CHECKING:
    from pathlib import Path

SOURCES = ("raw_odds_2223", "raw_odds_2324", "real_odds_raw")
PHASE_CLOSING = "closing"
PHASE_FIRST = "first_collection_after_market_open"
SELECTIONS = ("home", "draw", "away")


def synthetic_protocol() -> dict:
    """A minimal but structurally valid protocol for synthetic runs."""
    return {
        "schema_version": "value-mvp-1-evaluation-protocol/v1",
        "task": "VALUE_MVP_1_BASELINE_VS_CLOSING_MARKET",
        "task_type": "BUSINESS_RESEARCH_IMPLEMENTATION",
        "claim_boundary": "test only",
        "population_policy": {
            "expected_population": {"total": 0, "per_season": {}},
            "primary": "test",
            "bookmaker_exclusion": ["Max", "Avg"],
            "bookmaker_exclusion_reason": "test",
        },
        "season_assignment_rule": "kickoff_at month >= 8 -> YYYY/YYYY+1 else (YYYY-1)/YYYY",
        "season_split_policy": {
            "fold1": {"train": ["2022/23"], "test": ["2023/24"]},
            "fold2": {"train": ["2022/23", "2023/24"], "test": ["2024/25"]},
            "no_random_split": True,
        },
        "feature_contract": {
            "features": list(FEATURE_NAMES),
            "feature_count": len(FEATURE_NAMES),
            "generation": "test",
            "points_win": 3,
            "points_draw": 1,
            "missing_policy": "test",
        },
        "elo_contract": {
            "initial_elo": 1500,
            "k_factor": 20,
            "expected_formula": "E = 1 / (1 + 10^((R_opponent - R_self) / 400))",
            "result_mapping": {"home_win": 1, "draw": 0.5, "home_loss": 0},
            "no_market_adjustment": True,
        },
        "rolling_window": 5,
        "model_family": "multinomial_logistic_regression",
        "model_hyperparameters": {
            "solver": "lbfgs",
            "C": 1.0,
            "max_iter": 2000,
            "class_weight": None,
            "n_jobs": 1,
        },
        "no_hyperparameter_search": True,
        "imputer_policy": {"method": "median", "fit_on": "training_fold_rows_only"},
        "scaler_policy": {"method": "standard", "fit_on": "training_fold_rows_only"},
        "market_no_vig_method": "test",
        "market_consensus_method": "test",
        "minimum_bookmaker_count": 2,
        "eligibility_fail": "MARKET_BENCHMARK_INELIGIBLE",
        "primary_metric": "multiclass_log_loss",
        "secondary_metrics": ["multiclass_brier_score", "accuracy", "calibration_summary"],
        "log_loss_eps": 1e-15,
        "log_loss_formula": "test",
        "brier_formula": "test",
        "calibration_bins": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        "statistical_inference_method": "season-stratified paired bootstrap",
        "bootstrap": {"replicates": 100, "seed": 20260810, "ci_percentiles": [2.5, 97.5]},
        "claim_classification": {
            "MODEL_BETTER_THAN_CLOSING": "CI upper < 0",
            "MARKET_BETTER_THAN_MODEL": "CI lower > 0",
            "INCONCLUSIVE": "CI includes 0",
        },
        "primary_claim_basis": "pooled OOS",
        "forbidden_features": [
            "odds",
            "market",
            "closing",
            "close",
            "first_collection",
            "result",
            "FTR",
            "FTHG",
            "FTAG",
            "score",
            "shots",
            "corners",
            "cards",
            "postmatch",
        ],
        "forbidden_claims": [
            "profitability",
            "ROI",
            "yield",
            "kelly",
            "staking",
            "CLV",
            "tradable edge",
            "decision-time execution",
            "bets",
            "wins",
            "losses",
            "stakes",
        ],
        "determinism": {"runs": "RUN_A/RUN_B", "requirement": "byte-stable", "tolerance": "none"},
    }


def synthetic_matches() -> list[dict]:
    """Eight canonical matches: six in 2022/23, one each in 2023/24, 2024/25.

    The 2022/23 block has repeated teams across weeks so every rolling feature
    column has at least one non-NaN value in the training fold (the imputer
    rejects all-NaN columns). Each match carries two closing bookmakers (b1, b2)
    and one first-collection bookmaker (f1) with valid triples.
    """
    return [
        {
            "mid": "47_2022_101",
            "kickoff_at": "2022-08-06T14:00:00+01:00",
            "home": "Alpha FC",
            "away": "Beta FC",
            "ftr": "H",
            "fthg": 2,
            "ftag": 1,
            "closing": {"b1": (1.8, 3.6, 4.5), "b2": (1.75, 3.7, 4.8)},
            "first": {"f1": (1.7, 3.5, 4.9)},
        },
        {
            "mid": "47_2022_102",
            "kickoff_at": "2022-08-06T16:30:00+01:00",
            "home": "Gamma FC",
            "away": "Delta FC",
            "ftr": "A",
            "fthg": 0,
            "ftag": 3,
            "closing": {"b1": (3.1, 3.2, 2.2), "b2": (3.2, 3.3, 2.1)},
            "first": {"f1": (3.0, 3.4, 2.2)},
        },
        {
            "mid": "47_2022_103",
            "kickoff_at": "2022-08-13T14:00:00+01:00",
            "home": "Alpha FC",
            "away": "Gamma FC",
            "ftr": "D",
            "fthg": 1,
            "ftag": 1,
            "closing": {"b1": (2.0, 3.5, 3.4), "b2": (2.05, 3.6, 3.3)},
            "first": {"f1": (2.1, 3.4, 3.3)},
        },
        {
            "mid": "47_2022_104",
            "kickoff_at": "2022-08-13T16:30:00+01:00",
            "home": "Beta FC",
            "away": "Delta FC",
            "ftr": "H",
            "fthg": 2,
            "ftag": 0,
            "closing": {"b1": (2.4, 3.2, 2.9), "b2": (2.45, 3.3, 2.8)},
            "first": {"f1": (2.5, 3.1, 2.8)},
        },
        {
            "mid": "47_2022_105",
            "kickoff_at": "2022-08-20T14:00:00+01:00",
            "home": "Alpha FC",
            "away": "Delta FC",
            "ftr": "H",
            "fthg": 3,
            "ftag": 0,
            "closing": {"b1": (1.7, 3.9, 4.6), "b2": (1.65, 4.0, 4.8)},
            "first": {"f1": (1.6, 4.0, 5.0)},
        },
        {
            "mid": "47_2022_106",
            "kickoff_at": "2022-08-27T14:00:00+01:00",
            "home": "Beta FC",
            "away": "Gamma FC",
            "ftr": "A",
            "fthg": 0,
            "ftag": 2,
            "closing": {"b1": (3.0, 3.3, 2.3), "b2": (3.1, 3.4, 2.2)},
            "first": {"f1": (2.9, 3.5, 2.3)},
        },
        {
            "mid": "47_2023_201",
            "kickoff_at": "2023-08-05T14:00:00+01:00",
            "home": "Alpha FC",
            "away": "Delta FC",
            "ftr": "D",
            "fthg": 1,
            "ftag": 1,
            "closing": {"b1": (2.0, 3.4, 3.6), "b2": (2.05, 3.3, 3.7)},
            "first": {"f1": (2.1, 3.3, 3.5)},
        },
        {
            "mid": "47_2024_301",
            "kickoff_at": "2024-08-10T14:00:00+01:00",
            "home": "Beta FC",
            "away": "Gamma FC",
            "ftr": "H",
            "fthg": 3,
            "ftag": 0,
            "closing": {"b1": (1.6, 4.0, 5.2), "b2": (1.55, 4.1, 5.4)},
            "first": {"f1": (1.6, 4.0, 5.0)},
        },
    ]


def _source_for_season(season: str) -> str:
    return {
        "2022/23": "raw_odds_2223",
        "2023/24": "raw_odds_2324",
        "2024/25": "real_odds_raw",
    }[season]


def write_synthetic_inputs(tmp_path: Path) -> dict:
    """Write observations jsonl + csv rows for the synthetic matches."""
    observations_dir = tmp_path / "observations"
    csv_dir = tmp_path / "csv"
    observations_dir.mkdir(parents=True, exist_ok=True)
    csv_dir.mkdir(parents=True, exist_ok=True)

    csv_rows: dict[str, list[dict]] = {source: [] for source in SOURCES}

    for match_spec in synthetic_matches():
        start_year = int(match_spec["mid"].split("_")[1])
        season = f"{start_year}/{str(start_year + 1)[-2:]}"
        source = _source_for_season(season)
        # one CSV row per locator; row N = CSV line N (header = line 1)
        for _, odds_by_phase in (
            (PHASE_CLOSING, match_spec["closing"]),
            (PHASE_FIRST, match_spec["first"]),
        ):
            for bookmaker, triple in odds_by_phase.items():
                row_number = len(csv_rows[source]) + 2
                csv_rows[source].append(
                    {
                        "FTR": match_spec["ftr"],
                        "FTHG": str(match_spec["fthg"]),
                        "FTAG": str(match_spec["ftag"]),
                    }
                )
                for selection, odds in zip(SELECTIONS, triple, strict=True):
                    observations_dir_specific = observations_dir / f"{source}.jsonl"
                    with observations_dir_specific.open("a", encoding="utf-8") as handle:
                        handle.write(
                            json.dumps(
                                {
                                    "kickoff_at": match_spec["kickoff_at"],
                                    "home_team": match_spec["home"],
                                    "away_team": match_spec["away"],
                                    "match_link": {"matched_id": match_spec["mid"]},
                                    "provider_collection_phase": "closing"
                                    if odds_by_phase is match_spec["closing"]
                                    else PHASE_FIRST,
                                    "bookmaker_source_id": bookmaker,
                                    "selection": selection,
                                    "decimal_odds": odds,
                                    "raw_record_locator": f"csv:row={row_number}:{source}:{selection}",
                                }
                            )
                            + "\n"
                        )

    for source in SOURCES:
        with (csv_dir / f"{source}.csv").open("w", encoding="utf-8") as handle:
            handle.write("FTR,FTHG,FTAG\n")
            for row in csv_rows[source]:
                handle.write(f"{row['FTR']},{row['FTHG']},{row['FTAG']}\n")

    # verify_inputs requires a receipt; content is only hashed, not parsed.
    (observations_dir / "receipt.json").write_text(
        json.dumps({"schema": "m3-historical-odds-rebuild-receipt/v3", "dummy": True}) + "\n",
        encoding="utf-8",
    )

    return {"observations_dir": observations_dir, "csv_dir": csv_dir}
