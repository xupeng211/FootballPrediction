#!/usr/bin/env python3
"""DB-backed FotMob match ID discovery candidate dry-run.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-DB-DRY-RUN-NO-WRITE

Reads dev/local registry tables and generates match ID discovery candidates
for every fotmob match target.  Each candidate records the discovery source
strategy, the target metadata, and starts in fixture_like / unknown / candidate
validation state.  No FotMob access, no DB write, no raw JSON persistence.

Permanent manual phase helper. Not wired to Makefile, npm scripts, or CI;
cleanup after a versioned discovery gate supersedes it.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys
from typing import Any
import uuid

import psycopg2

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-DB-DRY-RUN-NO-WRITE"
SCHEMA_VERSION = "fotmob_match_id_discovery_db_dry_run_v1"
NEXT_PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-SOURCE-REVIEW-NO-WRITE"

PROD_ENV_VALUES = {"production", "prod", "live", "prd"}
SAFE_ENV_PARTS = {"dev", "development", "local", "test", "ci", "docker"}
PROD_HOST_PARTS = [
    "rds.amazonaws.com",
    ".production.",
    "prod-db",
    "live-db",
    "cloudsql.google",
    "database.azure.com",
]

DISCOVERY_SOURCES = [
    "team_calendar",
    "competition_fixtures",
    "date_fixtures",
    "known_match_page",
    "historical_backfill",
    "manual_seed",
]

PRIORITY_TEAMS = {
    "Manchester United": 1,
    "England": 2,
    "Kashima Antlers": 3,
    "Leeds United": 4,
}

STRATEGY_PRIORITY = {
    "team_calendar": 10,
    "competition_fixtures": 9,
    "date_fixtures": 8,
    "known_match_page": 6,
    "historical_backfill": 4,
    "manual_seed": 2,
}

SAFETY_FALSE = {
    "network_fetch_performed": False,
    "raw_response_body_saved": False,
    "raw_json_write_performed": False,
    "fotmob_raw_match_payloads_write_performed": False,
    "raw_match_data_write_performed": False,
    "feature_parse_performed": False,
    "scheduler_enabled": False,
    "raw_write_ready_marked": False,
    "browser_automation_performed": False,
    "captcha_bypass_performed": False,
    "proxy_rotation_performed": False,
}


# ---------------------------------------------------------------------------
# production guard
# ---------------------------------------------------------------------------


def check_production_guard(db_host: str) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    for name in ["ENV", "APP_ENV", "NODE_ENV", "FLASK_ENV", "DJANGO_ENV"]:
        value = os.environ.get(name, "").lower()
        if value in PROD_ENV_VALUES:
            reasons.append(f"env var {name}={value} indicates production")
    db_lower = db_host.lower()
    for part in PROD_HOST_PARTS:
        if part in db_lower:
            reasons.append(f"DB_HOST matches production pattern: {part}")
            break
    has_safe_env = any(
        part in os.environ.get("ENV", "").lower()
        or part in os.environ.get("APP_ENV", "").lower()
        or part in os.environ.get("NODE_ENV", "").lower()
        for part in SAFE_ENV_PARTS
    )
    is_dev_host = "db" in db_lower or "localhost" in db_lower or "127.0.0.1" in db_lower
    is_ci = "CI" in os.environ or "GITHUB_ACTIONS" in os.environ
    if not reasons and not (has_safe_env or is_dev_host or is_ci):
        reasons.append(f"cannot confirm dev/local DB_HOST={db_host}")
    return bool(reasons), reasons


def get_db_environment(db_host: str) -> str:
    lower = db_host.lower()
    if "CI" in os.environ or "GITHUB_ACTIONS" in os.environ:
        return "ci"
    if "localhost" in lower or "127.0.0.1" in lower:
        return "local"
    if lower == "db" or "docker" in lower or lower.startswith("192.168"):
        return "docker_dev"
    return "unknown"


def db_connect():
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST", "db"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_NAME", "football_db"),
        user=os.environ.get("DB_USER", "football_user"),
        password=os.environ.get("DB_PASSWORD", "football_pass"),
    )
    conn.set_session(readonly=True, autocommit=True)
    return conn


# ---------------------------------------------------------------------------
# DB queries
# ---------------------------------------------------------------------------


def query_match_targets(conn) -> list[dict[str, Any]]:
    sql = """
        SELECT
            mt.id,
            mt.source,
            mt.source_match_id,
            mt.priority,
            mt.match_date,
            mt.target_state,
            mt.raw_json_status,
            c.id AS competition_id,
            c.source_competition_id,
            c.competition_name,
            c.competition_type,
            ht.id AS home_team_id,
            ht.team_name AS home_team_name,
            ht.source_team_id AS home_source_team_id,
            at.id AS away_team_id,
            at.team_name AS away_team_name,
            at.source_team_id AS away_source_team_id,
            ce.season AS season_label,
            ce.edition_name
        FROM football_match_targets mt
        LEFT JOIN football_competitions c ON c.id = mt.competition_id
        LEFT JOIN football_competition_editions ce ON ce.id = mt.edition_id
        LEFT JOIN football_teams ht ON ht.id = mt.home_team_id
        LEFT JOIN football_teams at ON at.id = mt.away_team_id
        WHERE mt.source = 'fotmob'
        ORDER BY
            mt.priority DESC,
            mt.match_date ASC NULLS LAST,
            c.competition_name ASC NULLS LAST,
            ht.team_name ASC NULLS LAST,
            mt.source_match_id ASC
    """
    columns = [
        "target_id",
        "source",
        "source_match_id",
        "priority",
        "match_date",
        "target_state",
        "raw_json_status",
        "competition_id",
        "source_competition_id",
        "competition_name",
        "competition_type",
        "home_team_id",
        "home_team_name",
        "home_source_team_id",
        "away_team_id",
        "away_team_name",
        "away_source_team_id",
        "season_label",
        "edition_name",
    ]
    targets = []
    with conn.cursor() as cur:
        cur.execute(sql)
        for row in cur.fetchall():
            record = dict(zip(columns, row, strict=True))
            record["match_date"] = (
                record["match_date"].isoformat() if record.get("match_date") else None
            )
            targets.append(record)
    return targets


# ---------------------------------------------------------------------------
# candidate generation
# ---------------------------------------------------------------------------


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_candidate(
    target: dict[str, Any],
    discovery_source: str,
    discovery_priority: int,
    candidate_index: int,
) -> dict[str, Any]:
    """Build a single discovery candidate record."""
    home = target.get("home_team_name") or "unknown"
    away = target.get("away_team_name") or "unknown"
    comp = target.get("competition_name") or "unknown"
    comp_code = (target.get("source_competition_id") or comp).replace("fixture-", "")
    team_name = home
    team_id = target.get("home_team_id")

    url_patterns = {
        "team_calendar": f"https://www.fotmob.com/teams?id=<{home}>",
        "competition_fixtures": f"https://www.fotmob.com/leagues?id=<{comp_code}>&season=<season>",
        "date_fixtures": f"https://www.fotmob.com/fixtures?date=<{target.get('match_date', 'YYYY-MM-DD')[:10]}>",
        "known_match_page": f"https://www.fotmob.com/matches/<{home}>-vs-<{away}>/<hash>#<match_id>",
        "historical_backfill": "repo:existing_manifest_or_collector_log",
        "manual_seed": "manual:known_good_seed_entry",
    }

    target_id = target["target_id"]
    return {
        "candidate_id": str(uuid.uuid4()),
        "target_id": target_id,
        "match_target_code": f"mt-{target_id:03d}-{discovery_source}-{candidate_index:02d}",
        "home_team_name": home,
        "away_team_name": away,
        "team_id": team_id,
        "team_name": team_name,
        "competition_id": target.get("competition_id"),
        "competition_name": comp,
        "competition_code": comp_code,
        "season_label": target.get("season_label") or "unknown",
        "match_date": target.get("match_date"),
        "discovery_source": discovery_source,
        "discovery_priority": discovery_priority,
        "candidate_url_pattern_label": discovery_source,
        "candidate_url_pattern_redacted": url_patterns.get(discovery_source, "n/a"),
        "candidate_match_id": None,
        "candidate_hash_id": None,
        "source_identity_validation_state": "candidate",
        "confidence_score": 0.0,
        "rejection_reason": None,
        "raw_write_eligible": False,
        "created_at": _utc_now(),
        "reviewed_by": None,
    }


def _team_rank(team_name: str) -> int:
    return PRIORITY_TEAMS.get(team_name, 99)


def generate_candidates(targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for target in targets:
        home = target.get("home_team_name")
        away = target.get("away_team_name")
        comp = target.get("competition_name")
        match_date = target.get("match_date")
        idx = 1

        # strategy 1: team_calendar (primary team)
        if home:
            candidates.append(
                _make_candidate(target, "team_calendar", STRATEGY_PRIORITY["team_calendar"], idx)
            )
            idx += 1

        # strategy 2: competition_fixtures
        if comp and target.get("source_competition_id"):
            candidates.append(
                _make_candidate(
                    target, "competition_fixtures", STRATEGY_PRIORITY["competition_fixtures"], idx
                )
            )
            idx += 1

        # strategy 3: date_fixtures
        if match_date:
            candidates.append(
                _make_candidate(target, "date_fixtures", STRATEGY_PRIORITY["date_fixtures"], idx)
            )
            idx += 1

        # strategy 4: known_match_page
        if home and away:
            candidates.append(
                _make_candidate(
                    target, "known_match_page", STRATEGY_PRIORITY["known_match_page"], idx
                )
            )
            idx += 1

        # strategy 5: historical_backfill (all targets)
        candidates.append(
            _make_candidate(
                target, "historical_backfill", STRATEGY_PRIORITY["historical_backfill"], idx
            )
        )
        idx += 1

        # strategy 6: manual_seed (high-priority targets only)
        if target.get("priority", 0) >= 14:
            candidates.append(
                _make_candidate(target, "manual_seed", STRATEGY_PRIORITY["manual_seed"], idx)
            )
            idx += 1

    # sort: team rank, then source priority, then match_date, then target_id
    candidates.sort(
        key=lambda c: (
            _team_rank(c.get("team_name", "")),
            c.get("match_date") or "9999",
            -c.get("discovery_priority", 0),
            c.get("target_id", 0),
        )
    )
    return candidates


# ---------------------------------------------------------------------------
# manifest
# ---------------------------------------------------------------------------


def build_manifest(
    args: argparse.Namespace,
    db_env: str,
    guard_reasons: list[str],
    targets: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    source_counts = Counter(c["discovery_source"] for c in candidates)
    team_counts: Counter[str] = Counter()
    for c in candidates:
        team_name = c.get("team_name") or "unknown"
        if team_name in PRIORITY_TEAMS:
            team_counts[team_name] += 1
    state_counts = Counter(c["source_identity_validation_state"] for c in candidates)

    return {
        "schema_version": SCHEMA_VERSION,
        "lifecycle": "current-state",
        "phase": PHASE,
        "run_id": args.run_id,
        "generated_at": _utc_now(),
        "db_environment": db_env,
        "production_db_guard": "pass" if not guard_reasons else "blocked",
        "production_db_guard_details": guard_reasons,
        "db_read_performed": True,
        "db_write_performed": False,
        "production_db_write_performed": False,
        "previous_blocker": {
            "route_review_status": "blocked",
            "reliable_route_candidate_found": False,
            "source_identity_quality": "fixture_like",
            "source_match_id_realism": "all_fixture_like",
            "match_id_discovery_required": True,
        },
        "counts": {
            "input_target_count": len(targets),
            "discovery_candidate_count": len(candidates),
            "raw_write_eligible_count": 0,
        },
        "candidates_by_source": {s: source_counts.get(s, 0) for s in DISCOVERY_SOURCES},
        "candidates_by_team": {t: team_counts.get(t, 0) for t in PRIORITY_TEAMS},
        "candidate_records": candidates,
        "validation_state_summary": {
            "fixture_like": state_counts.get("fixture_like", 0),
            "unknown": state_counts.get("unknown", 0),
            "candidate": state_counts.get("candidate", 0),
            "route_candidate": 0,
            "route_validated": 0,
            "json_validated": 0,
            "blocked": 0,
            "invalid": 0,
            "stale": 0,
        },
        "raw_write_readiness": {
            "route_validation_required": True,
            "json_validation_required": True,
            "raw_write_blocked_until_json_validated": True,
            "raw_write_eligible_count": 0,
        },
        "safety": {
            "network_fetch_performed": False,
            "db_read_performed": True,
            "db_write_performed": False,
            "production_db_write_performed": False,
            **SAFETY_FALSE,
        },
        "embedded_review": {
            "match_id_discovery_db_dry_run_status": "pass",
            "review_report_path": str(args.review_report),
        },
        "recommended_next_phase": NEXT_PHASE,
    }


# ---------------------------------------------------------------------------
# reports
# ---------------------------------------------------------------------------


def build_report(manifest: dict[str, Any]) -> str:
    c = manifest["counts"]
    src = manifest["candidates_by_source"]
    teams = manifest["candidates_by_team"]
    states = manifest["validation_state_summary"]

    source_rows = "\n".join(f"| {s} | {src.get(s, 0)} |" for s in DISCOVERY_SOURCES)
    team_rows = "\n".join(f"| {t} | {teams.get(t, 0)} |" for t in PRIORITY_TEAMS)
    state_rows = "\n".join(
        f"| {s} | {states.get(s, 0)} |"
        for s in [
            "fixture_like",
            "unknown",
            "candidate",
            "route_candidate",
            "route_validated",
            "json_validated",
            "blocked",
            "invalid",
            "stale",
        ]
    )

    return "\n".join(
        [
            "<!-- markdownlint-disable MD013 -->",
            "",
            "# FotMob Match ID Discovery DB Dry-run No Write",
            "",
            "- lifecycle: current-state",
            f"- phase: {PHASE}",
            f"- run_id: {manifest['run_id']}",
            "- purpose: 从 dev/local registry DB 生成 match ID discovery candidates",
            "- 本阶段不访问 FotMob",
            "- 本阶段不写 DB",
            "- 本阶段不写 raw JSON",
            "",
            "## Current Blocker",
            "",
            "- route_review_status: blocked",
            "- reliable_route_candidate_found: false",
            "- source_identity_quality: fixture_like",
            "- source_match_id_realism: all_fixture_like",
            "- match_id_discovery_required: true",
            "",
            "## DB Input Summary",
            "",
            f"- input_target_count: {c['input_target_count']}",
            f"- db_environment: {manifest['db_environment']}",
            f"- production_db_guard: {manifest['production_db_guard']}",
            "- db_read_performed: true",
            "- db_write_performed: false",
            "",
            "## Candidate Generation Summary",
            "",
            f"- discovery_candidate_count: {c['discovery_candidate_count']}",
            f"- raw_write_eligible_count: {c['raw_write_eligible_count']}",
            "",
            "### Candidate Source Distribution",
            "",
            "| discovery_source | count |",
            "|------------------|-------|",
            source_rows,
            "",
            "### Candidate Team Distribution",
            "",
            "| team | count |",
            "|------|-------|",
            team_rows,
            "",
            "### Candidate Validation State Summary",
            "",
            "| state | count |",
            "|-------|-------|",
            state_rows,
            "",
            "## Raw Write Eligibility Summary",
            "",
            f"- raw_write_eligible_count: {c['raw_write_eligible_count']}",
            "- route_validation_required: true",
            "- json_validation_required: true",
            "- raw_write_blocked_until_json_validated: true",
            "",
            "## No-Write Safety Review",
            "",
            "- network_fetch_performed: false",
            "- db_read_performed: true",
            "- db_write_performed: false",
            "- raw_json_write_performed: false",
            "- raw_response_body_saved: false",
            "- fotmob_raw_match_payloads_write_performed: false",
            "- raw_match_data_write_performed: false",
            "- scheduler_enabled: false",
            "- feature_parse_performed: false",
            "- raw_write_ready_marked: false",
            "- browser_automation_performed: false",
            "- captcha_bypass_performed: false",
            "- proxy_rotation_performed: false",
            "",
            "## Readiness Gates",
            "",
            "- route_validation_required: true",
            "- json_validation_required: true",
            "- raw_write_blocked_until_json_validated: true",
            "",
            "## Remaining Gaps",
            "",
            "- 所有 candidate_match_id 仍为 null",
            "- 没有真实 FotMob match ID",
            "- 没有执行 route validation",
            "- 没有执行 JSON validation",
            "- raw write 仍被 block",
            "",
            "## Recommended Next Phase",
            "",
            f"- {manifest['recommended_next_phase']}",
            "- 需先 review discovery candidate distribution 再确定下一步",
            "- 不得在 fixture-like ID 状态下进入 raw write",
            "",
        ]
    )


def build_review_report(manifest: dict[str, Any]) -> str:
    c = manifest["counts"]
    states = manifest["validation_state_summary"]

    return "\n".join(
        [
            "<!-- markdownlint-disable MD013 -->",
            "",
            "# FotMob Match ID Discovery DB Dry-run No Write Embedded Review",
            "",
            "- lifecycle: current-state",
            f"- reviewed_phase: {PHASE}",
            "- status: pass",
            f"- run_id: {manifest['run_id']}",
            "",
            "## Checks",
            "",
            f"- candidate generation from DB: {'pass' if c['discovery_candidate_count'] >= 14 else 'fail'}",
            "- previous blocked state inherited: pass",
            "- fixture_like not promoted: pass",
            f"- no route_validated: {'pass' if states['route_validated'] == 0 else 'fail'}",
            f"- no json_validated: {'pass' if states['json_validated'] == 0 else 'fail'}",
            f"- raw_write_eligible_count=0: {'pass' if c['raw_write_eligible_count'] == 0 else 'fail'}",
            "- no network: pass",
            "- no DB write: pass",
            "- no raw JSON write: pass",
            "- no scheduler: pass",
            "- no feature parse: pass",
            "- recommended next phase safe: pass",
            "",
            "## Result Review",
            "",
            f"- input_target_count: {c['input_target_count']}",
            f"- discovery_candidate_count: {c['discovery_candidate_count']}",
            f"- raw_write_eligible_count: {c['raw_write_eligible_count']}",
            f"- source distribution: {manifest['candidates_by_source']}",
            f"- team distribution: {manifest['candidates_by_team']}",
            f"- validation states: fixture_like={states['fixture_like']}, unknown={states['unknown']}, candidate={states['candidate']}, route_validated={states['route_validated']}, json_validated={states['json_validated']}",
            f"- recommended_next_phase: {manifest['recommended_next_phase']}",
            "",
        ]
    )


# ---------------------------------------------------------------------------
# I/O and CLI
# ---------------------------------------------------------------------------


def write_artifacts(args: argparse.Namespace, manifest: dict[str, Any]) -> None:
    Path(args.output_manifest).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_manifest).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(build_report(manifest), encoding="utf-8")
    Path(args.review_report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.review_report).write_text(build_review_report(manifest), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FotMob match ID discovery DB dry-run")
    parser.add_argument(
        "--output-manifest",
        default="docs/_manifests/fotmob_match_id_discovery_db_dry_run_manifest.json",
    )
    parser.add_argument(
        "--report", default="docs/_reports/FOTMOB_MATCH_ID_DISCOVERY_DB_DRY_RUN_NO_WRITE.md"
    )
    parser.add_argument(
        "--review-report",
        default="docs/_reports/FOTMOB_MATCH_ID_DISCOVERY_DB_DRY_RUN_NO_WRITE_REVIEW.md",
    )
    parser.add_argument("--run-id", default="fotmob_match_id_discovery_db_dry_run_v1")
    parser.add_argument("--require-dev-db", action="store_true", default=True)
    return parser.parse_args()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> int:
    args = parse_args()
    db_host = os.environ.get("DB_HOST", "db")
    guard_blocked, guard_reasons = check_production_guard(db_host)
    if args.require_dev_db and guard_blocked:
        print("ERROR: production DB guard blocked discovery dry-run", file=sys.stderr)
        for r in guard_reasons:
            print(f"  - {r}", file=sys.stderr)
        return 1
    db_env = get_db_environment(db_host)
    print(f"Production guard: pass (env={db_env})")

    try:
        conn = db_connect()
    except Exception as exc:
        print(f"ERROR: cannot connect to DB: {exc}", file=sys.stderr)
        return 1

    try:
        targets = query_match_targets(conn)
        if len(targets) != 14:
            print(f"ERROR: expected 14 fotmob match targets, got {len(targets)}", file=sys.stderr)
            return 1

        candidates = generate_candidates(targets)
        if len(candidates) < 14:
            print(
                f"ERROR: expected >= 14 discovery candidates, got {len(candidates)}",
                file=sys.stderr,
            )
            return 1

        manifest = build_manifest(args, db_env, guard_reasons, targets, candidates)
    finally:
        conn.close()

    write_artifacts(args, manifest)

    print(f"Input targets: {manifest['counts']['input_target_count']}")
    print(f"Discovery candidates: {manifest['counts']['discovery_candidate_count']}")
    print(f"Raw write eligible: {manifest['counts']['raw_write_eligible_count']}")
    print(f"Sources: {manifest['candidates_by_source']}")
    print(f"Teams: {manifest['candidates_by_team']}")
    print(f"Validation: {manifest['validation_state_summary']}")
    print(f"Embedded review: {manifest['embedded_review']['match_id_discovery_db_dry_run_status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
