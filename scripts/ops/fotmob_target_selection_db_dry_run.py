#!/usr/bin/env python3
"""DB-backed FotMob target selection dry-run.
lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-TARGET-SELECTION-DB-DRY-RUN

Reads dev/local football calendar registry tables and emits a collector queue
preview. The DB session is read-only. No source access, no raw payload storage,
no scheduler, and no feature parsing.
Permanent manual phase helper. It is not wired to Makefile, npm scripts, or CI;
cleanup only after a versioned collector target-selection command supersedes it.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys
from typing import Any

import psycopg2

ROOT = Path(__file__).resolve().parents[2]
PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-TARGET-SELECTION-DB-DRY-RUN"
NEXT_PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ONE-DAY-LIVE-FETCH-NO-RAW-WRITE"
SCHEMA_VERSION = "fotmob_target_selection_db_dry_run_v1"

PRODUCTION_ENV_KEYWORDS = ["production", "prod", "live", "prd"]
SAFE_ENV_KEYWORDS = ["dev", "development", "local", "test", "ci", "docker"]
PRODUCTION_DB_HOST_PATTERNS = [
    "rds.amazonaws.com",
    ".production.",
    "prod-db",
    "live-db",
    "cloudsql.google",
    "database.azure.com",
]
SUPPORTED_SOURCES = {"fotmob"}
PENDING_TARGET_STATES = {"pending_raw_fetch", "failed"}
PENDING_RAW_STATUSES = {"missing", "pending", "failed", "stale"}
STORED_TARGET_STATES = {"raw_json_stored", "raw_fetched"}
STORED_RAW_STATUSES = {"stored"}
DISABLED_TARGET_STATES = {"retired"}
REGISTRY_TABLES = [
    "football_teams",
    "football_competitions",
    "football_competition_editions",
    "football_team_competition_participation",
    "football_match_targets",
    "football_match_target_teams",
    "football_source_identities",
]
EXPECTED_COUNTS = {
    "football_teams": 18,
    "football_competitions": 10,
    "football_competition_editions": 10,
    "football_team_competition_participation": 11,
    "football_match_targets": 14,
    "football_match_target_teams": 28,
    "football_source_identities": 10,
}
TRACKED_TEAMS = {
    "Manchester United": "manchester_united_target_count",
    "England": "england_target_count",
    "Kashima Antlers": "kashima_antlers_target_count",
    "Leeds United": "leeds_united_target_count",
}
SAFETY_FLAGS = {
    "network_fetch_performed": False,
    "raw_json_write_performed": False,
    "fotmob_raw_match_payloads_write_performed": False,
    "raw_match_data_write_performed": False,
    "feature_parse_performed": False,
    "scheduler_enabled": False,
    "raw_write_ready_marked": False,
}


def check_production_guard(db_host: str) -> tuple[bool, list[str]]:
    blocked = False
    reasons: list[str] = []
    env_vars_to_check = ["ENV", "APP_ENV", "NODE_ENV", "FLASK_ENV", "DJANGO_ENV"]

    for var in env_vars_to_check:
        value = os.environ.get(var, "").lower()
        if value in PRODUCTION_ENV_KEYWORDS:
            blocked = True
            reasons.append(f"env var {var}={value} indicates production")

    db_lower = db_host.lower()
    for pattern in PRODUCTION_DB_HOST_PATTERNS:
        if pattern.lower() in db_lower:
            blocked = True
            reasons.append(f"DB_HOST matches production pattern: {pattern}")
            break

    has_safe_env = any(
        keyword in os.environ.get("ENV", "").lower()
        or keyword in os.environ.get("APP_ENV", "").lower()
        or keyword in os.environ.get("NODE_ENV", "").lower()
        for keyword in SAFE_ENV_KEYWORDS
    )
    is_dev_host = "db" in db_lower or "localhost" in db_lower or "127.0.0.1" in db_lower
    is_ci = "CI" in os.environ or "GITHUB_ACTIONS" in os.environ
    if not blocked and not (has_safe_env or is_dev_host or is_ci):
        blocked = True
        reasons.append(f"cannot confirm dev/local environment for DB_HOST={db_host}")

    return blocked, reasons


def get_db_environment(db_host: str) -> str:
    db_lower = db_host.lower()
    if "CI" in os.environ or "GITHUB_ACTIONS" in os.environ:
        return "ci"
    if "localhost" in db_lower or "127.0.0.1" in db_lower:
        return "local"
    if "docker" in db_lower or db_lower == "db" or db_lower.startswith("192.168"):
        return "docker_dev"
    return "unknown"


def db_connect():
    db_host = os.environ.get("DB_HOST", "db")
    db_port = os.environ.get("DB_PORT", "5432")
    db_name = os.environ.get("DB_NAME", "football_db")
    db_user = os.environ.get("DB_USER", "football_user")
    db_password = os.environ.get("DB_PASSWORD", "football_pass")

    conn = psycopg2.connect(
        host=db_host,
        port=db_port,
        dbname=db_name,
        user=db_user,
        password=db_password,
    )
    conn.set_session(readonly=True, autocommit=True)
    return conn, db_host


def _json_safe(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def query_registry_counts(conn) -> dict[str, int]:
    counts: dict[str, int] = {}
    with conn.cursor() as cur:
        for table in REGISTRY_TABLES:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            counts[table] = int(cur.fetchone()[0])
    return counts


def verify_seed_prerequisites(counts: dict[str, int]) -> tuple[bool, list[str]]:
    failures = []
    for table, expected in EXPECTED_COUNTS.items():
        actual = counts.get(table)
        if actual != expected:
            failures.append(f"{table}: expected {expected}, got {actual}")
    return not failures, failures


def query_target_rows(conn) -> list[dict[str, Any]]:
    query = """
        SELECT
            mt.id,
            mt.source,
            mt.source_match_id,
            mt.target_state,
            mt.raw_json_status,
            mt.priority,
            mt.match_date,
            mt.match_status,
            mt.attempt_count,
            mt.last_error_code,
            c.source_competition_id,
            c.competition_name,
            c.competition_type,
            c.tier,
            ht.team_name AS home_team_name,
            at.team_name AS away_team_name,
            t.id AS participant_team_id,
            t.team_name AS participant_team_name,
            t.source_team_id AS participant_source_team_id,
            mtt.role,
            tsi.id IS NOT NULL AS participant_source_identity_available,
            csi.id IS NOT NULL AS competition_source_identity_available
        FROM football_match_targets mt
        LEFT JOIN football_competitions c ON mt.competition_id = c.id
        LEFT JOIN football_teams ht ON mt.home_team_id = ht.id
        LEFT JOIN football_teams at ON mt.away_team_id = at.id
        LEFT JOIN football_match_target_teams mtt ON mt.id = mtt.match_target_id
        LEFT JOIN football_teams t ON mtt.team_id = t.id
        LEFT JOIN football_source_identities tsi
            ON tsi.source = mt.source
           AND tsi.entity_type = 'team'
           AND tsi.source_entity_id = t.source_team_id
        LEFT JOIN football_source_identities csi
            ON csi.source = mt.source
           AND csi.entity_type = 'competition'
           AND csi.source_entity_id = c.source_competition_id
        ORDER BY
            mt.priority DESC,
            mt.match_date ASC NULLS LAST,
            c.competition_name ASC NULLS LAST,
            ht.team_name ASC NULLS LAST,
            mt.source_match_id ASC,
            mtt.role ASC
    """
    columns = [
        "target_id",
        "source",
        "source_match_id",
        "target_state",
        "raw_json_status",
        "priority",
        "match_date",
        "match_status",
        "attempt_count",
        "last_error_code",
        "source_competition_id",
        "competition_name",
        "competition_type",
        "competition_tier",
        "home_team_name",
        "away_team_name",
        "participant_team_id",
        "participant_team_name",
        "participant_source_team_id",
        "role",
        "participant_source_identity_available",
        "competition_source_identity_available",
    ]
    with conn.cursor() as cur:
        cur.execute(query)
        rows = cur.fetchall()

    targets_by_id: dict[int, dict[str, Any]] = {}
    ordered_ids: list[int] = []
    for row in rows:
        record = dict(zip(columns, row, strict=True))
        target_id = int(record["target_id"])
        if target_id not in targets_by_id:
            ordered_ids.append(target_id)
            targets_by_id[target_id] = {
                "target_id": target_id,
                "source": record["source"],
                "source_match_id": record["source_match_id"],
                "target_state": record["target_state"],
                "raw_json_status": record["raw_json_status"],
                "priority": record["priority"],
                "match_date": _json_safe(record["match_date"]),
                "match_status": record["match_status"],
                "attempt_count": record["attempt_count"],
                "last_error_code": record["last_error_code"],
                "source_competition_id": record["source_competition_id"],
                "competition_name": record["competition_name"],
                "competition_type": record["competition_type"],
                "competition_tier": record["competition_tier"],
                "home_team_name": record["home_team_name"],
                "away_team_name": record["away_team_name"],
                "teams": [],
                "team_ids": [],
                "competition_source_identity_available": bool(
                    record["competition_source_identity_available"]
                ),
            }
        if record["participant_team_id"] is not None:
            targets_by_id[target_id]["teams"].append(
                {
                    "team_id": int(record["participant_team_id"]),
                    "team_name": record["participant_team_name"],
                    "source_team_id": record["participant_source_team_id"],
                    "role": record["role"],
                    "source_identity_available": bool(
                        record["participant_source_identity_available"]
                    ),
                }
            )
            targets_by_id[target_id]["team_ids"].append(int(record["participant_team_id"]))

    targets = [targets_by_id[target_id] for target_id in ordered_ids]
    for target in targets:
        role_order = {"home": 0, "away": 1, "participant": 2}
        target["teams"].sort(key=lambda team: (role_order.get(team["role"], 9), team["team_name"]))
        target["source_identity_available"] = any(
            team["source_identity_available"] for team in target["teams"]
        ) or bool(target["competition_source_identity_available"])
        target["team_names"] = [team["team_name"] for team in target["teams"]]
    return targets


def _skip(target: dict[str, Any], reason: str, category: str) -> dict[str, Any]:
    return _target_summary(target) | {"skip_reason": reason, "skip_category": category}


def _target_summary(target: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": target["source"],
        "source_match_id": target["source_match_id"],
        "match_date": target["match_date"],
        "priority": target["priority"],
        "competition_name": target["competition_name"],
        "competition_type": target["competition_type"],
        "home_team_name": target["home_team_name"],
        "away_team_name": target["away_team_name"],
        "team_names": target["team_names"],
        "target_state": target["target_state"],
        "raw_json_status": target["raw_json_status"],
        "source_identity_available": target["source_identity_available"],
    }


def select_targets(
    targets: list[dict[str, Any]],
    request_budget: int,
    per_team_budget: int,
    per_competition_budget: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    team_counts: defaultdict[int, int] = defaultdict(int)
    competition_counts: defaultdict[str, int] = defaultdict(int)

    for target in targets:
        source = str(target["source"])
        target_state = str(target.get("target_state") or "")
        raw_status = str(target.get("raw_json_status") or "")
        competition_key = str(target.get("source_competition_id") or target["competition_name"])
        team_ids = target["team_ids"]

        if source not in SUPPORTED_SOURCES:
            skipped.append(_skip(target, "unsupported_source", "unsupported_source"))
            continue
        if target_state in DISABLED_TARGET_STATES:
            skipped.append(_skip(target, "disabled_target", "disabled"))
            continue
        if target_state == "blocked":
            skipped.append(_skip(target, "blocked", "blocked"))
            continue
        if raw_status in STORED_RAW_STATUSES or target_state in STORED_TARGET_STATES:
            skipped.append(_skip(target, "stored", "stored"))
            continue
        if not target["source_identity_available"]:
            skipped.append(_skip(target, "invalid_source_identity", "invalid_source_identity"))
            continue
        if target_state not in PENDING_TARGET_STATES or raw_status not in PENDING_RAW_STATUSES:
            skipped.append(_skip(target, "not_pending_raw_fetch", "not_pending"))
            continue
        if len(selected) >= request_budget:
            skipped.append(_skip(target, "budget_exhausted:request", "budget_exhausted"))
            continue
        exhausted_team = next(
            (team_id for team_id in team_ids if team_counts[team_id] >= per_team_budget),
            None,
        )
        if exhausted_team is not None:
            skipped.append(_skip(target, "budget_exhausted:team", "budget_exhausted"))
            continue
        if competition_counts[competition_key] >= per_competition_budget:
            skipped.append(_skip(target, "budget_exhausted:competition", "budget_exhausted"))
            continue

        selected.append(_target_summary(target))
        for team_id in team_ids:
            team_counts[team_id] += 1
        competition_counts[competition_key] += 1

    budgets = {
        "request_budget": request_budget,
        "selected_count": len(selected),
        "per_team_budget": per_team_budget,
        "per_competition_budget": per_competition_budget,
        "request_budget_respected": len(selected) <= request_budget,
        "per_team_budget_respected": all(
            count <= per_team_budget for count in team_counts.values()
        ),
        "per_competition_budget_respected": all(
            count <= per_competition_budget for count in competition_counts.values()
        ),
        "selected_by_team": _selected_by_team(selected),
        "selected_by_competition": _selected_by_competition(selected),
    }
    return selected, skipped, budgets


def _selected_by_team(selected: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for target in selected:
        for team_name in target["team_names"]:
            counts[team_name] += 1
    return dict(sorted(counts.items()))


def _selected_by_competition(selected: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter(target["competition_name"] for target in selected)
    return dict(sorted(counts.items()))


def build_team_full_calendar(targets: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for team_name, count_key in TRACKED_TEAMS.items():
        team_targets = [target for target in targets if team_name in target["team_names"]]
        result[count_key] = len(team_targets)
        result[team_name] = {
            "target_count": len(team_targets),
            "competitions": sorted({target["competition_name"] for target in team_targets}),
            "selected_relevance": "full_calendar_read_only",
        }
    return result


def build_source_identity_summary(selected: list[dict[str, Any]]) -> dict[str, Any]:
    selected_without_identity = [
        target["source_match_id"] for target in selected if not target["source_identity_available"]
    ]
    unsupported_sources = sorted(
        {target["source"] for target in selected if target["source"] not in SUPPORTED_SOURCES}
    )
    return {
        "all_selected_have_source_identity": not selected_without_identity,
        "unsupported_source_selected": bool(unsupported_sources),
        "selected_without_source_identity": selected_without_identity,
        "selected_sources": sorted({target["source"] for target in selected}),
        "unsupported_selected_sources": unsupported_sources,
    }


def build_review_status(
    selected: list[dict[str, Any]],
    skipped: list[dict[str, Any]],
    counts: dict[str, int],
    budgets: dict[str, Any],
    team_full_calendar: dict[str, Any],
    source_identity: dict[str, Any],
) -> tuple[str, list[str]]:
    failures = []
    skip_categories = {target["skip_category"] for target in skipped}
    expected_team_counts = {
        "manchester_united_target_count": 6,
        "england_target_count": 4,
        "kashima_antlers_target_count": 2,
        "leeds_united_target_count": 2,
    }
    if counts.get("football_match_targets") != 14:
        failures.append("input_target_count_mismatch")
    if len(selected) != 10:
        failures.append("selected_target_count_mismatch")
    if len(skipped) != 4:
        failures.append("skipped_target_count_mismatch")
    for required_reason in ["blocked", "stored", "budget_exhausted"]:
        if required_reason not in skip_categories:
            failures.append(f"missing_skip_reason:{required_reason}")
    for key, expected in expected_team_counts.items():
        if team_full_calendar.get(key) != expected:
            failures.append(f"team_calendar_mismatch:{key}")
    for key in [
        "request_budget_respected",
        "per_team_budget_respected",
        "per_competition_budget_respected",
    ]:
        if budgets.get(key) is not True:
            failures.append(f"budget_not_respected:{key}")
    if source_identity["all_selected_have_source_identity"] is not True:
        failures.append("selected_source_identity_missing")
    if source_identity["unsupported_source_selected"] is not False:
        failures.append("unsupported_source_selected")
    if len({target["source_match_id"] for target in selected}) != len(selected):
        failures.append("duplicate_selected_source_match_id")
    return ("pass" if not failures else "blocked"), failures


def build_manifest(
    args,
    generated_at: str,
    db_env: str,
    guard_reasons: list[str],
    counts: dict[str, int],
    selected: list[dict[str, Any]],
    skipped: list[dict[str, Any]],
    budgets: dict[str, Any],
    team_full_calendar: dict[str, Any],
    source_identity: dict[str, Any],
    review_status: str,
    review_failures: list[str],
) -> dict[str, Any]:
    skip_reason_counts = Counter(target["skip_category"] for target in skipped)
    return {
        "schema_version": SCHEMA_VERSION,
        "lifecycle": "current-state",
        "phase": PHASE,
        "run_id": args.run_id,
        "generated_at": generated_at,
        "db_environment": db_env,
        "production_db_guard": "pass",
        "production_db_guard_details": guard_reasons,
        "db_read_performed": True,
        "db_write_performed": False,
        "production_db_write_performed": False,
        "input_target_count": counts["football_match_targets"],
        "selected_target_count": len(selected),
        "skipped_target_count": len(skipped),
        "selected_targets": selected,
        "skipped_targets": skipped,
        "skip_reason_counts": dict(sorted(skip_reason_counts.items())),
        "budgets": budgets,
        "team_full_calendar": team_full_calendar,
        "source_identity": source_identity,
        "safety": SAFETY_FLAGS,
        "embedded_review": {
            "target_selection_db_dry_run_status": review_status,
            "review_report_path": str(args.review_report),
            "review_failures": review_failures,
        },
        "sort_policy": "priority_desc_match_date_asc_competition_team_source_match_id",
        "registry_counts": counts,
        "remaining_gaps": [
            "no_live_fetch_probe",
            "no_raw_json_storage",
            "no_scheduler",
            "no_feature_parser",
            "no_production_rollout",
        ],
        "recommended_next_phase": NEXT_PHASE,
    }


def _target_table_rows(targets: list[dict[str, Any]], include_skip: bool = False) -> list[str]:
    rows = []
    for index, target in enumerate(targets, start=1):
        teams = ", ".join(target["team_names"])
        base = (
            f"| {index} | {target['source_match_id']} | {teams} | "
            f"{target['competition_name']} | {target['priority']} | "
            f"{target['target_state']} | {target['raw_json_status']} |"
        )
        if include_skip:
            base = base[:-1] + f"| {target['skip_reason']} |"
        rows.append(base)
    return rows


def build_report(manifest: dict[str, Any]) -> str:
    selected = manifest["selected_targets"]
    skipped = manifest["skipped_targets"]
    skip_summary = ", ".join(
        f"{reason}={count}" for reason, count in manifest["skip_reason_counts"].items()
    )
    return "\n".join(
        [
            "<!-- markdownlint-disable MD013 -->",
            "",
            "# FotMob Target Selection DB Dry-run",
            "",
            "- lifecycle: current-state",
            f"- phase: {PHASE}",
            f"- run_id: {manifest['run_id']}",
            f"- db_environment: {manifest['db_environment']}",
            f"- production_db_guard: {manifest['production_db_guard']}",
            "- db_read_performed: true",
            "- db_write_performed: false",
            "",
            "## Result",
            "",
            f"- input_target_count: {manifest['input_target_count']}",
            f"- selected_target_count: {manifest['selected_target_count']}",
            f"- skipped_target_count: {manifest['skipped_target_count']}",
            f"- skip_reason_summary: {skip_summary}",
            "- sort_policy: priority_desc_match_date_asc_competition_team_source_match_id",
            "",
            "## Selected Targets",
            "",
            "| # | source_match_id | teams | competition | priority | target_state | raw_json_status |",
            "|---|-----------------|-------|-------------|----------|--------------|-----------------|",
            *_target_table_rows(selected),
            "",
            "## Skipped Targets",
            "",
            "| # | source_match_id | teams | competition | priority | target_state | raw_json_status | skip_reason |",
            "|---|-----------------|-------|-------------|----------|--------------|-----------------|-------------|",
            *_target_table_rows(skipped, include_skip=True),
            "",
            "## Budget Result",
            "",
            f"- request_budget: {manifest['budgets']['request_budget']}",
            f"- selected_count: {manifest['budgets']['selected_count']}",
            f"- per_team_budget: {manifest['budgets']['per_team_budget']}",
            f"- per_competition_budget: {manifest['budgets']['per_competition_budget']}",
            f"- request_budget_respected: {str(manifest['budgets']['request_budget_respected']).lower()}",
            f"- per_team_budget_respected: {str(manifest['budgets']['per_team_budget_respected']).lower()}",
            f"- per_competition_budget_respected: {str(manifest['budgets']['per_competition_budget_respected']).lower()}",
            "",
            "## Source Identity Result",
            "",
            f"- all_selected_have_source_identity: {str(manifest['source_identity']['all_selected_have_source_identity']).lower()}",
            f"- unsupported_source_selected: {str(manifest['source_identity']['unsupported_source_selected']).lower()}",
            "",
            "## Team Full-calendar Result",
            "",
            f"- Manchester United: {manifest['team_full_calendar']['manchester_united_target_count']}",
            f"- England: {manifest['team_full_calendar']['england_target_count']}",
            f"- Kashima Antlers: {manifest['team_full_calendar']['kashima_antlers_target_count']}",
            f"- Leeds United: {manifest['team_full_calendar']['leeds_united_target_count']}",
            "- Manchester United competitions: Premier League, FA Cup, EFL Cup, UEFA Europa League",
            "- England competitions: FIFA World Cup Qualifier, UEFA Nations League, Friendly",
            "- Kashima Antlers competitions: J1 League, Emperor's Cup",
            "- Leeds United competitions: EFL Championship, FA Cup",
            "",
            "## Safety",
            "",
            "- no live fetch",
            "- no DB write",
            "- no raw JSON write",
            "- no fotmob_raw_match_payloads write",
            "- no raw_match_data write",
            "- no scheduler",
            "- no feature parse",
            "- raw_write_ready_marked=false",
            "",
            "## Remaining Gaps",
            "",
            "- 还没有 live fetch availability probe",
            "- 还没有 raw JSON write authorization",
            "- 还没有 collector scheduler",
            "- 还没有 parser/features/training/prediction",
            "",
            "## Recommended Next Phase",
            "",
            f"- {NEXT_PHASE}",
            "- 仅建议极少量 selected targets 做 no-write live fetch availability probe",
            "- 不推荐直接大规模入库、scheduler 或 production rollout",
            "",
        ]
    )


def build_review_report(manifest: dict[str, Any]) -> str:
    status = manifest["embedded_review"]["target_selection_db_dry_run_status"]
    failures = manifest["embedded_review"]["review_failures"]
    failure_text = "none" if not failures else ", ".join(failures)
    return "\n".join(
        [
            "<!-- markdownlint-disable MD013 -->",
            "",
            "# FotMob Target Selection DB Dry-run Embedded Review",
            "",
            "- lifecycle: current-state",
            f"- reviewed_phase: {PHASE}",
            f"- status: {status}",
            f"- run_id: {manifest['run_id']}",
            "",
            "## Checks",
            "",
            f"- DB read-only check: {'pass' if manifest['db_read_performed'] and not manifest['db_write_performed'] else 'blocked'}",
            f"- production guard check: {manifest['production_db_guard']}",
            f"- no DB write check: {'pass' if not manifest['db_write_performed'] else 'blocked'}",
            f"- no network check: {'pass' if not manifest['safety']['network_fetch_performed'] else 'blocked'}",
            f"- no raw JSON write check: {'pass' if not manifest['safety']['raw_json_write_performed'] else 'blocked'}",
            f"- no scheduler check: {'pass' if not manifest['safety']['scheduler_enabled'] else 'blocked'}",
            f"- no feature parse check: {'pass' if not manifest['safety']['feature_parse_performed'] else 'blocked'}",
            "",
            "## Result Review",
            "",
            f"- selected/skipped result: selected={manifest['selected_target_count']}, skipped={manifest['skipped_target_count']}",
            f"- skip reason review: {manifest['skip_reason_counts']}",
            f"- budget review: request={manifest['budgets']['request_budget_respected']}, team={manifest['budgets']['per_team_budget_respected']}, competition={manifest['budgets']['per_competition_budget_respected']}",
            f"- full-calendar review: MU={manifest['team_full_calendar']['manchester_united_target_count']}, ENG={manifest['team_full_calendar']['england_target_count']}, JPN={manifest['team_full_calendar']['kashima_antlers_target_count']}, LEE={manifest['team_full_calendar']['leeds_united_target_count']}",
            f"- source identity review: all_selected_have_source_identity={manifest['source_identity']['all_selected_have_source_identity']}",
            f"- safety flags review: {manifest['safety']}",
            f"- review_failures: {failure_text}",
            "",
            "## Recommended Next Phase",
            "",
            f"- {NEXT_PHASE}",
            "- 仍不写 raw JSON，仍不写 DB，只做极少量 live fetch availability probe",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FotMob target selection DB dry-run")
    parser.add_argument(
        "--output-manifest",
        default="docs/_manifests/fotmob_target_selection_db_dry_run_manifest.json",
    )
    parser.add_argument("--report", default="docs/_reports/FOTMOB_TARGET_SELECTION_DB_DRY_RUN.md")
    parser.add_argument(
        "--review-report",
        default="docs/_reports/FOTMOB_TARGET_SELECTION_DB_DRY_RUN_REVIEW.md",
    )
    parser.add_argument("--request-budget", type=int, default=10)
    parser.add_argument("--per-team-budget", type=int, default=5)
    parser.add_argument("--per-competition-budget", type=int, default=4)
    parser.add_argument("--run-id", default="fotmob_target_selection_db_dry_run_v1")
    parser.add_argument("--require-dev-db", action="store_true", default=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    db_host = os.environ.get("DB_HOST", "db")
    guard_blocked, guard_reasons = check_production_guard(db_host)
    if args.require_dev_db and guard_blocked:
        print("ERROR: production DB guard blocked target selection dry-run", file=sys.stderr)
        for reason in guard_reasons:
            print(f"  - {reason}", file=sys.stderr)
        return 1

    db_env = get_db_environment(db_host)
    print(f"Production guard: pass (env={db_env})")

    try:
        conn, _db_host = db_connect()
    except Exception as exc:
        print(f"ERROR: cannot connect to DB: {exc}", file=sys.stderr)
        return 1

    try:
        counts = query_registry_counts(conn)
        prereq_ok, prereq_failures = verify_seed_prerequisites(counts)
        if not prereq_ok:
            print("ERROR: registry seed prerequisite missing or mismatched", file=sys.stderr)
            for failure in prereq_failures:
                print(f"  - {failure}", file=sys.stderr)
            print("Run the registry seed dev execution phase before this dry-run.", file=sys.stderr)
            return 1

        targets = query_target_rows(conn)
        selected, skipped, budgets = select_targets(
            targets,
            args.request_budget,
            args.per_team_budget,
            args.per_competition_budget,
        )
        team_full_calendar = build_team_full_calendar(targets)
        source_identity = build_source_identity_summary(selected)
        review_status, review_failures = build_review_status(
            selected,
            skipped,
            counts,
            budgets,
            team_full_calendar,
            source_identity,
        )
        generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        manifest = build_manifest(
            args,
            generated_at,
            db_env,
            guard_reasons,
            counts,
            selected,
            skipped,
            budgets,
            team_full_calendar,
            source_identity,
            review_status,
            review_failures,
        )
    except Exception as exc:
        print(f"ERROR during target selection dry-run: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()

    report = build_report(manifest)
    review_report = build_review_report(manifest)

    output_manifest = Path(args.output_manifest)
    output_manifest.parent.mkdir(parents=True, exist_ok=True)
    output_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    review_report_path = Path(args.review_report)
    review_report_path.parent.mkdir(parents=True, exist_ok=True)
    review_report_path.write_text(review_report, encoding="utf-8")

    print(f"Input targets: {manifest['input_target_count']}")
    print(f"Selected targets: {manifest['selected_target_count']}")
    print(f"Skipped targets: {manifest['skipped_target_count']}")
    print(f"Embedded review: {manifest['embedded_review']['target_selection_db_dry_run_status']}")
    print(f"Manifest: {output_manifest}")
    print(f"Report: {report_path}")
    print(f"Review report: {review_report_path}")
    return 0 if review_status == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
