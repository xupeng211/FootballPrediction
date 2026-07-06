#!/usr/bin/env python3
"""Report-only filtered feature matrix audit helpers.

lifecycle: permanent
scope: no-write training readiness reporting
"""

from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
import importlib.util
import json
import math
from pathlib import Path
import re
from typing import Any

FEATURE_GROUPS = [
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
]

EXCLUDED_DATA_VERSIONS = {"PHASE4.23", "PHASE4.43_SYNTHETIC"}
METADATA_KEYS = {"_source", "_version"}
HIGH_MISSING_THRESHOLD = 0.5
MIN_LABEL_CLASS_COUNT = 3
LOW_VARIANCE_UNIQUE_THRESHOLD = 2
MIN_TRAINING_ROWS_FOR_DRY_RUN = 100
MIN_MODEL_SIGNAL_FEATURES = 10
LOW_VARIANCE_EXAMPLE_LIMIT = 12
ELO_SUFFIXES = (".home_elo", ".away_elo")
ODDS_PREFIXES = ("odds_features.", "odds_movement_features.")
POSTMATCH_KEY_RE = re.compile(
    r"(xg|shot|possession|momentum|corner|card|foul|pass|big_chance|"
    r"woodwork|offside|duel|discipline|strength|stats|touch|accurate|goal|penalt)",
    re.IGNORECASE,
)
ODDS_KEY_RE = re.compile(
    r"(odds|implied_prob|steam|bookmaker|favorite_prob|prob_entropy|"
    r"margin|has_odds_data|_error|_data_quality)",
    re.IGNORECASE,
)


def _load_contract_module():
    contract_path = Path(__file__).resolve().parent / "l3_prematch_contract.py"
    spec = importlib.util.spec_from_file_location("l3_prematch_contract", contract_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_CONTRACT_MODULE = _load_contract_module()


def _json_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


def _is_missing(value: Any) -> bool:
    return value is None or value == ""


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        if value is None or value == "":
            return None
        number = float(value)
        if math.isfinite(number):
            return number
    except (TypeError, ValueError):
        return None
    return None


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _encode_result(home_score: Any, away_score: Any) -> str | None:
    if home_score is None or away_score is None:
        return None
    home = int(home_score)
    away = int(away_score)
    if home > away:
        return "HOME"
    if home == away:
        return "DRAW"
    return "AWAY"


def _is_eligible_row(row: dict[str, Any]) -> bool:
    data_version = str(row.get("data_version") or "")
    return bool(row.get("external_id")) and data_version not in EXCLUDED_DATA_VERSIONS


def _flatten_filtered_payload(
    row: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, int], dict[str, int]]:
    payload = {
        group: row.get(group) if isinstance(row.get(group), dict) else {}
        for group in FEATURE_GROUPS
    }
    raw_counts = {group: len(payload[group]) for group in FEATURE_GROUPS}
    filtered = _CONTRACT_MODULE.filter_l3_feature_payload(
        payload,
        include_conditional=False,
        allow_diagnostic_postmatch=False,
    )

    flat: dict[str, Any] = {}
    filtered_counts: dict[str, int] = {}
    for group in FEATURE_GROUPS:
        safe = filtered.get(group) if isinstance(filtered.get(group), dict) else {}
        filtered_counts[group] = len(safe)
        for key, value in safe.items():
            flat[f"{group}.{key}"] = value
    return flat, raw_counts, filtered_counts


def build_filtered_feature_matrix_report(
    rows: list[dict[str, Any]],
    *,
    coverage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a no-write, no-fit filtered matrix report from in-memory rows."""
    eligible_rows = [row for row in rows if _is_eligible_row(row)]
    excluded_rows = len(rows) - len(eligible_rows)

    labels: Counter[str] = Counter()
    matrix: list[dict[str, Any]] = []
    raw_group_totals: defaultdict[str, int] = defaultdict(int)
    filtered_group_totals: defaultdict[str, int] = defaultdict(int)

    for row in eligible_rows:
        result = _encode_result(row.get("home_score"), row.get("away_score"))
        if result is not None:
            labels[result] += 1

        flat, raw_counts, filtered_counts = _flatten_filtered_payload(row)
        matrix.append(flat)
        for group, count in raw_counts.items():
            raw_group_totals[group] += count
        for group, count in filtered_counts.items():
            filtered_group_totals[group] += count

    columns = sorted({key for item in matrix for key in item})
    metadata_columns = sorted(col for col in columns if col.rsplit(".", 1)[-1] in METADATA_KEYS)
    model_columns = sorted(col for col in columns if col not in metadata_columns)
    feature_stats = _build_feature_stats(matrix, columns)
    model_stats = [stat for stat in feature_stats if stat["feature"] in model_columns]

    high_missing = [stat for stat in model_stats if stat["missing_rate"] > HIGH_MISSING_THRESHOLD]
    constant = [stat for stat in model_stats if stat["constant"]]
    all_zero = [stat for stat in model_stats if stat["all_zero"]]
    numeric = [stat for stat in model_stats if stat["numeric_convertible"]]
    non_numeric = [stat for stat in model_stats if stat["non_numeric"]]
    leakage = _build_leakage_summary(model_columns, columns)
    signal = _build_signal_summary(model_columns)

    readiness_status = _readiness_status(
        rows_after_label_availability_filter=sum(labels.values()),
        label_counts=labels,
        model_signal_feature_columns=len(model_columns),
        leakage=leakage,
        signal=signal,
        high_missing_feature_count=len(high_missing),
        constant_feature_count=len(constant),
    )

    return {
        "TASK": "filtered_feature_matrix_report_only",
        "mode": "report-only",
        "db_write": False,
        "artifact_write": False,
        "model_fit": False,
        "dataset_write": False,
        "L3 coverage": _json_safe(coverage or {}),
        "Label audit": {
            "eligible_l3_rows": len(eligible_rows),
            "rows_with_scores": sum(labels.values()),
            "home_win_count": labels.get("HOME", 0),
            "draw_count": labels.get("DRAW", 0),
            "away_win_count": labels.get("AWAY", 0),
            "class_balance": _class_balance(labels),
            "label_blocker": sum(labels.values()) == 0 or len(labels) < MIN_LABEL_CLASS_COUNT,
        },
        "Filtered matrix": {
            "raw_eligible_rows": len(eligible_rows),
            "excluded_legacy_or_synthetic_rows": excluded_rows,
            "filtered_matrix_rows": len(matrix),
            "filtered_matrix_columns_total": len(columns),
            "model_signal_feature_columns": len(model_columns),
            "metadata_columns": len(metadata_columns),
            "excluded_metadata_names": metadata_columns,
            "sample_feature_names": model_columns[:16],
        },
        "Feature quality": {
            "constant_feature_count": len(constant),
            "all_zero_feature_count": len(all_zero),
            "high_missing_feature_count": len(high_missing),
            "numeric_feature_count": len(numeric),
            "non_numeric_feature_count": len(non_numeric),
            "top_missing_features": [
                {
                    "feature": stat["feature"],
                    "missing_rate": round(stat["missing_rate"], 4),
                    "non_null_count": stat["non_null_count"],
                }
                for stat in sorted(
                    model_stats,
                    key=lambda item: (-item["missing_rate"], item["feature"]),
                )[:10]
            ],
            "constant_feature_examples": [stat["feature"] for stat in constant[:12]],
            "low_variance_feature_examples": [
                stat["feature"]
                for stat in model_stats
                if stat["numeric_convertible"]
                and stat["numeric_unique_count"] <= LOW_VARIANCE_UNIQUE_THRESHOLD
            ][:LOW_VARIANCE_EXAMPLE_LIMIT],
        },
        "Leakage check": leakage,
        "Signal availability": signal,
        "Readiness": {
            "TRAINING_READINESS_STATUS": readiness_status,
            "SAFE_FOR_TRAINING_DRY_RUN": False,
            "SAFE_FOR_REAL_TRAINING": False,
            "SAFE_FOR_REAL_PREDICTION": False,
            "SAFE_FOR_BACKTEST": False,
        },
        "raw_group_totals": dict(raw_group_totals),
        "filtered_group_totals": dict(filtered_group_totals),
    }


def _build_feature_stats(matrix: list[dict[str, Any]], columns: list[str]) -> list[dict[str, Any]]:
    stats = []
    row_count = len(matrix)
    for column in columns:
        values = [row.get(column) for row in matrix]
        non_missing = [value for value in values if not _is_missing(value)]
        numbers = [_as_number(value) for value in non_missing]
        numeric_convertible = bool(non_missing) and len(numbers) == len(non_missing)
        unique_values = {_json_key(value) for value in non_missing}
        numeric_unique = {value for value in numbers if value is not None}
        all_zero = (
            numeric_convertible
            and len(non_missing) == row_count
            and all(value == 0 for value in numbers)
        )
        stats.append(
            {
                "feature": column,
                "non_null_count": len(non_missing),
                "missing_rate": 1 - (len(non_missing) / row_count if row_count else 0),
                "unique_value_count": len(unique_values),
                "numeric_convertible": numeric_convertible,
                "non_numeric": not numeric_convertible,
                "constant": len(unique_values) <= 1,
                "all_zero": all_zero,
                "numeric_unique_count": len(numeric_unique),
            }
        )
    return stats


def _build_leakage_summary(model_columns: list[str], columns: list[str]) -> dict[str, int]:
    return {
        "postmatch_leakage_remaining_count": sum(
            1 for column in model_columns if POSTMATCH_KEY_RE.search(column)
        ),
        "rating_remaining_count": sum(1 for column in model_columns if "rating" in column.lower()),
        "default_elo_remaining_count": sum(
            1
            for column in model_columns
            if column.startswith("elo_features.")
            or "_is_default" in column
            or column.endswith(ELO_SUFFIXES)
        ),
        "odds_fallback_remaining_count": sum(
            1
            for column in model_columns
            if column.startswith(ODDS_PREFIXES) or ODDS_KEY_RE.search(column)
        ),
        "unknown_or_audit_only_remaining_count": sum(
            1 for column in columns if "_extractedAt" in column or "audit" in column.lower()
        ),
    }


def _build_signal_summary(model_columns: list[str]) -> dict[str, bool]:
    return {
        "odds_signal_available": any(column.startswith(ODDS_PREFIXES) for column in model_columns),
        "elo_signal_available": any(column.startswith("elo_features.") for column in model_columns),
        "market_value_signal_available": any("market_value" in column for column in model_columns),
        "injury_availability_signal_available": any("injury" in column for column in model_columns),
        "age_signal_available": any(
            "age" in column or "u23" in column or "veteran" in column for column in model_columns
        ),
    }


def _class_balance(labels: Counter[str]) -> dict[str, float]:
    total = sum(labels.values())
    if total == 0:
        return {"HOME": 0.0, "DRAW": 0.0, "AWAY": 0.0}
    return {name: round(labels.get(name, 0) / total, 4) for name in ("HOME", "DRAW", "AWAY")}


def _readiness_status(
    *,
    rows_after_label_availability_filter: int,
    label_counts: Counter[str],
    model_signal_feature_columns: int,
    leakage: dict[str, int],
    signal: dict[str, bool],
    high_missing_feature_count: int,
    constant_feature_count: int,
) -> str:
    not_ready = (
        any(value != 0 for value in leakage.values())
        or rows_after_label_availability_filter < MIN_TRAINING_ROWS_FOR_DRY_RUN
        or len(label_counts) < MIN_LABEL_CLASS_COUNT
        or model_signal_feature_columns < MIN_MODEL_SIGNAL_FEATURES
        or not signal["odds_signal_available"]
        or not signal["elo_signal_available"]
        or high_missing_feature_count > model_signal_feature_columns // 2
        or constant_feature_count > model_signal_feature_columns // 2
    )
    return "NOT_READY" if not_ready else "READY_FOR_DRY_RUN_ONLY"


def build_report_from_connection(conn: Any) -> dict[str, Any]:
    """Build a report from a DB connection using SELECT-only queries."""
    coverage = _fetch_one(conn, _COVERAGE_SQL)
    rows = _fetch_all(conn, _ELIGIBLE_ROWS_SQL)
    return build_filtered_feature_matrix_report(rows, coverage=coverage)


def _fetch_one(conn: Any, query: str) -> dict[str, Any]:
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        row = cursor.fetchone()
        if row is None:
            return {}
        columns = [item[0] for item in cursor.description]
        return dict(zip(columns, row, strict=False))
    finally:
        cursor.close()


def _fetch_all(conn: Any, query: str) -> list[dict[str, Any]]:
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]
    finally:
        cursor.close()


_COVERAGE_SQL = """
WITH eligible AS (
  SELECT DISTINCT r.match_id
  FROM raw_match_data r
  JOIN matches m ON m.match_id = r.match_id
  WHERE m.external_id IS NOT NULL
    AND COALESCE(r.data_version, '') NOT IN ('PHASE4.23', 'PHASE4.43_SYNTHETIC')
),
pending AS (
  SELECT
    COUNT(*)::int AS pending_raw_rows,
    COUNT(DISTINCT r.match_id)::int AS pending_distinct_matches
  FROM raw_match_data r
  JOIN matches m ON m.match_id = r.match_id
  LEFT JOIN l3_features l3 ON l3.match_id = r.match_id
  WHERE l3.match_id IS NULL
    AND m.external_id IS NOT NULL
    AND COALESCE(r.data_version, '') NOT IN ('PHASE4.23', 'PHASE4.43_SYNTHETIC')
),
coverage AS (
  SELECT
    COUNT(DISTINCT e.match_id)::int AS eligible_raw_distinct_matches,
    COUNT(DISTINCT l3.match_id)::int AS covered_l3_distinct_matches
  FROM eligible e
  LEFT JOIN l3_features l3 ON l3.match_id = e.match_id
),
legacy AS (
  SELECT COUNT(DISTINCT l3.match_id)::int AS legacy_or_synthetic_l3_count
  FROM l3_features l3
  JOIN raw_match_data r ON r.match_id = l3.match_id
  WHERE COALESCE(r.data_version, '') IN ('PHASE4.23', 'PHASE4.43_SYNTHETIC')
)
SELECT
  (SELECT COUNT(*)::int FROM raw_match_data) AS raw_count,
  (SELECT COUNT(*)::int FROM matches) AS matches_count,
  (SELECT COUNT(*)::int FROM l3_features) AS l3_count,
  coverage.eligible_raw_distinct_matches,
  coverage.covered_l3_distinct_matches,
  pending.pending_raw_rows,
  pending.pending_distinct_matches,
  legacy.legacy_or_synthetic_l3_count
FROM coverage, pending, legacy
"""

_ELIGIBLE_ROWS_SQL = """
WITH ranked_raw AS (
  SELECT
    r.match_id,
    r.data_version,
    ROW_NUMBER() OVER (
      PARTITION BY r.match_id
      ORDER BY
        CASE r.data_version
          WHEN 'fotmob_live_v1' THEN 1
          WHEN 'fotmob_pageprops_v2' THEN 2
          WHEN 'fotmob_html_hyd_v1' THEN 3
          ELSE 99
        END,
        r.data_version
    ) AS rn
  FROM raw_match_data r
  JOIN matches m ON m.match_id = r.match_id
  WHERE m.external_id IS NOT NULL
    AND COALESCE(r.data_version, '') NOT IN ('PHASE4.23', 'PHASE4.43_SYNTHETIC')
),
eligible AS (
  SELECT rr.match_id, rr.data_version
  FROM ranked_raw rr
  WHERE rr.rn = 1
)
SELECT
  l3.match_id,
  m.external_id,
  m.home_team,
  m.away_team,
  m.match_date,
  m.home_score,
  m.away_score,
  m.league_name,
  m.season,
  e.data_version,
  COALESCE(l3.golden_features, '{}'::jsonb) AS golden_features,
  COALESCE(l3.tactical_features, '{}'::jsonb) AS tactical_features,
  COALESCE(l3.odds_movement_features, '{}'::jsonb) AS odds_movement_features,
  COALESCE(l3.odds_features, '{}'::jsonb) AS odds_features,
  COALESCE(l3.elo_features, '{}'::jsonb) AS elo_features,
  COALESCE(l3.rolling_features, '{}'::jsonb) AS rolling_features,
  COALESCE(l3.efficiency_features, '{}'::jsonb) AS efficiency_features,
  COALESCE(l3.draw_features, '{}'::jsonb) AS draw_features,
  COALESCE(l3.market_sentiment, '{}'::jsonb) AS market_sentiment,
  COALESCE(l3.stitch_summary, '{}'::jsonb) AS stitch_summary
FROM eligible e
JOIN l3_features l3 ON l3.match_id = e.match_id
JOIN matches m ON m.match_id = e.match_id
ORDER BY m.match_date, l3.match_id
"""
