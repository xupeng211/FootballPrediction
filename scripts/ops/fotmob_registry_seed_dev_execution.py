#!/usr/bin/env python3
"""FotMob football calendar registry seed dev execution.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DEV-EXECUTION-NO-LIVE-FETCH
Executes a metadata-only registry seed into a dev/local PostgreSQL database.
All operations are idempotent (ON CONFLICT DO NOTHING).
Includes a production DB guard that blocks execution against production hosts.

Usage:
    python scripts/ops/fotmob_registry_seed_dev_execution.py \
        --input-plan docs/_fixtures/fotmob_registry_seed_dry_run_plan.json \
        --output-manifest docs/_manifests/fotmob_registry_seed_dev_execution_manifest.json \
        --report docs/_reports/FOTMOB_REGISTRY_SEED_DEV_EXECUTION.md \
        --request-budget 10 --per-team-budget 5 --per-competition-budget 4 \
        --run-id fotmob_registry_seed_dev_execution_v1 \
        --require-dev-db

"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys

import psycopg2

ROOT = Path(__file__).resolve().parents[2]

# Phase2C batch2: Python runtime DB write guard
_guard_path = str(Path(__file__).resolve().parents[2] / "scripts" / "ops")
if _guard_path not in sys.path:
    sys.path.insert(0, _guard_path)

from helpers.python_db_write_guard import assert_db_write_allowed  # noqa: E402

# Production-like env keywords that trigger rejection
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
TABLE_ORDER = [
    "teams",
    "competitions",
    "competition_editions",
    "team_competition_participation",
    "match_targets",
    "match_target_teams",
    "source_identities",
]


# -- Production guard --
def check_production_guard(db_host: str) -> tuple[bool, list[str]]:
    """Returns (blocked, reasons). If blocked=True, execution must stop."""
    blocked = False
    reasons: list[str] = []

    env_vars_to_check = ["ENV", "APP_ENV", "NODE_ENV", "FLASK_ENV", "DJANGO_ENV"]
    for var in env_vars_to_check:
        value = os.environ.get(var, "").lower()
        if value in PRODUCTION_ENV_KEYWORDS:
            blocked = True
            reasons.append(f"env var {var}={value} indicates production")

    if not blocked:
        db_lower = db_host.lower()
        for pattern in PRODUCTION_DB_HOST_PATTERNS:
            if pattern.lower() in db_lower:
                blocked = True
                reasons.append(f"DB_HOST matches production pattern: {pattern}")
                break

    if not blocked:
        has_safe = any(
            kw in os.environ.get("ENV", "").lower()
            or kw in os.environ.get("APP_ENV", "").lower()
            or kw in os.environ.get("NODE_ENV", "").lower()
            for kw in SAFE_ENV_KEYWORDS
        )
        is_docker = "db" in db_host or "localhost" in db_host or "127.0.0.1" in db_host
        is_ci = "CI" in os.environ or "GITHUB_ACTIONS" in os.environ
        if not (has_safe or is_docker or is_ci):
            blocked = True
            reasons.append(f"cannot confirm dev/local environment for DB_HOST={db_host}")

    return blocked, reasons


def get_db_environment(db_host: str) -> str:
    """Classify DB environment."""
    if "CI" in os.environ or "GITHUB_ACTIONS" in os.environ:
        return "ci"
    if "localhost" in db_host or "127.0.0.1" in db_host:
        return "local"
    if "docker" in db_host or db_host == "db" or db_host.startswith("192.168"):
        return "docker_dev"
    return "unknown"


# -- DB helpers --
def db_connect():
    """Connect to PostgreSQL using environment variables. Returns connection."""
    db_host = os.environ.get("DB_HOST", "db")
    db_port = os.environ.get("DB_PORT", "5432")
    db_name = os.environ.get("DB_NAME", "football_db")
    db_user = os.environ.get("DB_USER", "football_user")
    db_password = os.environ.get("DB_PASSWORD", "football_pass")

    return psycopg2.connect(
        host=db_host,
        port=db_port,
        dbname=db_name,
        user=db_user,
        password=db_password,
    ), db_host


# -- Idempotent seed execution --
def execute_seed(conn, plan: dict) -> dict[str, int]:
    """Execute idempotent seed. Returns {table: inserted_count}."""

    inserted: dict[str, int] = {}
    cur = conn.cursor()

    # Teams
    teams = plan.get("teams", [])
    count = 0
    for t in teams:
        cur.execute(
            """INSERT INTO football_teams (source, source_team_id, team_name, team_type, country, gender, active, metadata)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (source, source_team_id) DO NOTHING""",
            (
                t.get("source", "fotmob"),
                t["source_team_id"],
                t["team_name"],
                t["team_type"],
                t.get("country"),
                t.get("gender", "men"),
                t.get("active", True),
                json.dumps({}),
            ),
        )
        count += cur.rowcount
    inserted["teams"] = count

    # Competitions
    competitions = plan.get("competitions", [])
    count = 0
    for c in competitions:
        cur.execute(
            """INSERT INTO football_competitions (source, source_competition_id, competition_name, competition_type, country, confederation, tier, active, metadata)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (source, source_competition_id) DO NOTHING""",
            (
                c.get("source", "fotmob"),
                c["source_competition_id"],
                c["competition_name"],
                c["competition_type"],
                c.get("country"),
                c.get("confederation"),
                c.get("tier"),
                c.get("active", True),
                json.dumps({}),
            ),
        )
        count += cur.rowcount
    inserted["competitions"] = count

    # Editions — need to resolve competition_id from fixture ref
    editions_data = plan.get("competition_editions", [])
    count = 0
    for e in editions_data:
        comp_fixture_id = e["competition_fixture_id"]
        cur.execute(
            "SELECT id FROM football_competitions WHERE source_competition_id = %s",
            (f"fixture-{comp_fixture_id}",),
        )
        row = cur.fetchone()
        if row is None:
            continue
        comp_id = row[0]
        cur.execute(
            """INSERT INTO football_competition_editions (competition_id, season, edition_name, start_date, end_date, calendar_type, active, metadata)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (competition_id, season) DO NOTHING""",
            (
                comp_id,
                e["season"],
                e.get("edition_name"),
                e.get("start_date"),
                e.get("end_date"),
                e.get("calendar_type"),
                e.get("active", True),
                json.dumps({}),
            ),
        )
        count += cur.rowcount
    inserted["competition_editions"] = count

    # Build ID maps after base tables are inserted
    # Maps use the actual source_*_id values from the fixture (not constructed prefixes)
    team_fixture_map = {t["fixture_id"]: t["source_team_id"] for t in plan.get("teams", [])}
    comp_fixture_map = {
        c["fixture_id"]: c["source_competition_id"] for c in plan.get("competitions", [])
    }

    cur.execute("SELECT id, source_team_id FROM football_teams")
    team_id_map = {row[1]: row[0] for row in cur.fetchall()}
    cur.execute("SELECT id, source_competition_id FROM football_competitions")
    comp_id_map = {row[1]: row[0] for row in cur.fetchall()}
    cur.execute("SELECT id, competition_id, season FROM football_competition_editions")
    edition_rows = cur.fetchall()
    edition_id_map = {(row[1], row[2]): row[0] for row in edition_rows}

    def _tid(fixture_id: str):
        src_id = team_fixture_map.get(fixture_id)
        return team_id_map.get(src_id) if src_id else None

    def _cid(fixture_id: str):
        src_id = comp_fixture_map.get(fixture_id)
        return comp_id_map.get(src_id) if src_id else None

    def _eid(comp_fixture_id: str, season: str):
        cid = _cid(comp_fixture_id)
        if cid is None:
            return None
        return edition_id_map.get((cid, season))

    # Participations
    participations = plan.get("team_competition_participation", [])
    count = 0
    for p in participations:
        team_id = _tid(p["team_fixture_id"])
        comp_id = _cid(p["competition_fixture_id"])
        ed_data = next(
            (e for e in editions_data if e["fixture_id"] == p["edition_fixture_id"]), None
        )
        edition_id = _eid(p["competition_fixture_id"], ed_data["season"]) if ed_data else None
        if team_id is None or comp_id is None or edition_id is None:
            continue
        cur.execute(
            """INSERT INTO football_team_competition_participation (team_id, competition_id, edition_id, participation_state, qualification_source, metadata)
               VALUES (%s,%s,%s,%s,%s,%s)
               ON CONFLICT (team_id, competition_id, edition_id) DO NOTHING""",
            (
                team_id,
                comp_id,
                edition_id,
                p.get("participation_state", "unknown"),
                p.get("qualification_source"),
                json.dumps({}),
            ),
        )
        count += cur.rowcount
    inserted["team_competition_participation"] = count

    # Match targets
    match_targets = plan.get("match_targets", [])
    count = 0
    for mt in match_targets:
        home_id = _tid(mt.get("home_team_fixture_id", ""))
        away_id = _tid(mt.get("away_team_fixture_id", ""))
        comp_id = _cid(mt.get("competition_fixture_id", ""))
        ed_data = next(
            (e for e in editions_data if e["fixture_id"] == mt.get("edition_fixture_id", "")), None
        )
        edition_id = (
            _eid(mt.get("competition_fixture_id", ""), ed_data["season"]) if ed_data else None
        )
        cur.execute(
            """INSERT INTO football_match_targets (source, source_match_id, competition_id, edition_id, match_date, home_team_id, away_team_id, match_status, target_state, priority, discovery_source, source_url, raw_json_status, attempt_count, last_error_code, last_error_message, metadata)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (source, source_match_id) DO NOTHING""",
            (
                mt.get("source", "fotmob"),
                mt["source_match_id"],
                comp_id,
                edition_id,
                mt.get("match_date"),
                home_id,
                away_id,
                mt.get("match_status"),
                mt.get("target_state", "discovered"),
                mt.get("priority", 100),
                mt.get("discovery_source"),
                mt.get("source_url"),
                mt.get("raw_json_status"),
                mt.get("attempt_count", 0),
                mt.get("last_error_code"),
                mt.get("last_error_message"),
                json.dumps({}),
            ),
        )
        count += cur.rowcount
    inserted["match_targets"] = count

    # Build match_target id map
    cur.execute("SELECT id, source_match_id FROM football_match_targets")
    mt_id_map = {row[1]: row[0] for row in cur.fetchall()}

    # Match target teams
    mtt_list = plan.get("match_target_teams", [])
    count = 0
    for mtt in mtt_list:
        mt_data = next(
            (mt for mt in match_targets if mt["fixture_id"] == mtt["match_target_fixture_id"]), None
        )
        if mt_data is None:
            continue
        mt_id = mt_id_map.get(mt_data["source_match_id"])
        team_id = _tid(mtt["team_fixture_id"])
        if mt_id is None or team_id is None:
            continue
        cur.execute(
            """INSERT INTO football_match_target_teams (match_target_id, team_id, role)
               VALUES (%s,%s,%s)
               ON CONFLICT (match_target_id, team_id, role) DO NOTHING""",
            (mt_id, team_id, mtt.get("role", "participant")),
        )
        count += cur.rowcount
    inserted["match_target_teams"] = count

    # Source identities
    source_identities = plan.get("source_identities", [])
    count = 0
    for si in source_identities:
        cur.execute(
            """INSERT INTO football_source_identities (source, entity_type, entity_id, source_entity_id, metadata)
               VALUES (%s,%s,NULL,%s,%s)
               ON CONFLICT (source, entity_type, source_entity_id) DO NOTHING""",
            (
                si.get("source", "fotmob"),
                si.get("entity_type"),
                si.get("source_entity_id"),
                json.dumps({}),
            ),
        )
        count += cur.rowcount
    inserted["source_identities"] = count

    conn.commit()
    cur.close()
    return inserted


# -- Queries --
def query_existing_counts(conn) -> dict[str, int]:
    """Return current row counts for all 7 registry tables."""
    cur = conn.cursor()
    counts = {}
    for table in TABLE_ORDER:
        cur.execute(f"SELECT COUNT(*) FROM football_{table}")
        counts[table] = cur.fetchone()[0]
    cur.close()
    return counts


def query_target_selection(
    conn, request_budget: int, per_team_budget: int, per_competition_budget: int
) -> tuple[list[dict], list[dict]]:
    """Select pending_raw_fetch targets from seeded DB. Returns (selected, skipped)."""
    cur = conn.cursor()
    cur.execute("""
        SELECT mt.source_match_id, mt.target_state, mt.raw_json_status,
               mt.priority, mt.match_date, mt.competition_id, mt.home_team_id, mt.away_team_id,
               c.competition_name, c.competition_type
        FROM football_match_targets mt
        LEFT JOIN football_competitions c ON mt.competition_id = c.id
        ORDER BY mt.priority ASC, mt.match_date ASC
    """)
    rows = cur.fetchall()
    cur.close()
    col_names = [
        "source_match_id",
        "target_state",
        "raw_json_status",
        "priority",
        "match_date",
        "competition_id",
        "home_team_id",
        "away_team_id",
        "competition_name",
        "competition_type",
    ]

    selected: list[dict] = []
    skipped: list[dict] = []
    team_counts: dict[int, int] = {}
    comp_counts: dict[int, int] = {}

    for row in rows:
        t = dict(zip(col_names, row))
        state, raw = t.get("target_state", ""), t.get("raw_json_status", "")

        if state == "blocked":
            skipped.append({**t, "skip_reason": "target_state=blocked"})
            continue
        if raw == "stored":
            skipped.append({**t, "skip_reason": "raw_json_status=stored"})
            continue
        if state != "pending_raw_fetch":
            skipped.append({**t, "skip_reason": f"target_state={state}"})
            continue
        if request_budget > 0 and len(selected) >= request_budget:
            skipped.append({**t, "skip_reason": "request_budget exhausted"})
            continue

        hid, aid = t.get("home_team_id"), t.get("away_team_id")
        if hid and team_counts.get(hid, 0) >= per_team_budget:
            skipped.append({**t, "skip_reason": f"per_team_budget exhausted for team {hid}"})
            continue
        if aid and team_counts.get(aid, 0) >= per_team_budget:
            skipped.append({**t, "skip_reason": f"per_team_budget exhausted for team {aid}"})
            continue

        cid = t.get("competition_id")
        if cid and comp_counts.get(cid, 0) >= per_competition_budget:
            skipped.append({**t, "skip_reason": "per_competition_budget exhausted"})
            continue

        selected.append(t)
        if hid:
            team_counts[hid] = team_counts.get(hid, 0) + 1
        if aid:
            team_counts[aid] = team_counts.get(aid, 0) + 1
        if cid:
            comp_counts[cid] = comp_counts.get(cid, 0) + 1

    return selected, skipped


def query_team_calendar(conn, team_name: str) -> list[dict]:
    """Find all match targets for a given team by name."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT mt.source_match_id, c.competition_name, c.competition_type,
               mt.target_state, mt.raw_json_status, mt.priority, mt.match_date
        FROM football_match_target_teams mtt
        JOIN football_match_targets mt ON mtt.match_target_id = mt.id
        JOIN football_teams t ON mtt.team_id = t.id
        LEFT JOIN football_competitions c ON mt.competition_id = c.id
        WHERE t.team_name = %s
        ORDER BY mt.priority ASC, mt.match_date ASC
    """,
        (team_name,),
    )
    rows = cur.fetchall()
    cur.close()
    return [
        dict(
            zip(
                [
                    "source_match_id",
                    "competition_name",
                    "competition_type",
                    "target_state",
                    "raw_json_status",
                    "priority",
                    "match_date",
                ],
                r,
            )
        )
        for r in rows
    ]


# -- Report and Manifest --
def build_report(
    run_id,
    generated_at,
    db_env,
    guard_blocked,
    guard_reasons,
    counts,
    idem_first,
    idem_second,
    selected,
    skipped,
    man_cal,
    eng_cal,
    jpn_cal,
    lee_cal,
    request_budget,
    per_team_budget,
    per_competition_budget,
) -> str:
    lines = [
        "<!-- markdownlint-disable MD013 -->",
        "",
        "# FotMob Registry Seed Dev Execution 报告",
        "- lifecycle: current-state",
        "- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DEV-EXECUTION-NO-LIVE-FETCH",
        f"- run_id: {run_id}",
        f"- generated_at: {generated_at}",
        "",
        "",
        "## 1. DB Environment",
        "",
        f"- db_environment: {db_env}",
        f"- production_db_guard: {'pass' if not guard_blocked else 'blocked'}",
    ]
    if guard_reasons:
        for r in guard_reasons:
            lines.append(f"- guard_detail: {r}")
    lines.extend(
        [
            "",
            "",
            "## 2. Seed Result",
            "",
            "| 表 | 第一次插入 | 第二次插入 | 最终行数 |",
            "|----|-----------|-----------|---------|",
        ]
    )
    for table in TABLE_ORDER:
        c1 = idem_first.get(table, 0)
        c2 = idem_second.get(table, 0)
        cf = counts.get(table, 0)
        lines.append(f"| football_{table} | {c1} | {c2} | {cf} |")
    idem_pass = all(idem_second.get(t, 0) == 0 for t in TABLE_ORDER)
    lines.extend(
        [
            "",
            f"- idempotency: {'pass' if idem_pass else 'fail'} (第二次执行全部 0 inserted)",
            "",
            "## 3. 安全声明",
            "",
            "- **本 PR 只在 dev/local DB 执行**",
            "- **本 PR 没有访问 FotMob**",
            "- **本 PR 没有写 raw JSON**",
            "- **本 PR 没有写 fotmob_raw_match_payloads**",
            "- **本 PR 没有写 raw_match_data**",
            "- **本 PR 没有启用 scheduler**",
            "- **本 PR 没有 feature parse**",
            "- production_db_write_performed=false",
            "- db_write_scope=registry_tables_only",
            "",
            "## 4. Target Selection Query",
            "",
            f"- 选中: {len(selected)}",
            f"- 跳过: {len(skipped)}",
            f"- request_budget={request_budget}, per_team_budget={per_team_budget}, per_competition_budget={per_competition_budget}",
        ]
    )
    if skipped:
        lines.extend(["", "跳过明细：", ""])
        for t in skipped:
            lines.append(f"- {t.get('source_match_id', '')}: {t.get('skip_reason', '')}")
    lines.extend(
        [
            "",
            "## 5. 球队全年赛程",
            "",
            f"- Man United: {len(man_cal)} 场",
            f"- England: {len(eng_cal)} 场",
            f"- Kashima Antlers: {len(jpn_cal)} 场",
            f"- Leeds United: {len(lee_cal)} 场",
            "",
            "## 6. Remaining Gaps",
            "",
            "- 只有少量 metadata seed，不覆盖所有联赛",
            "- 还没有 live fetch",
            "- 还没有 raw JSON 采集和存储",
            "- 还没有 scheduler",
            "- 还没有 parser/feature layer",
            "- 还没有 production rollout",
            "- 不能连接到 production DB",
            "",
            "## 7. Recommended Next Phase",
            "",
            "推荐下一阶段：",
            "",
            "### FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DEV-EXECUTION-REVIEW",
            "",
            "审查通过后，进入：",
            "",
            "### FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ONE-DAY-NO-FEATURE-PARSE-PREFLIGHT",
            "",
            "当前阶段仍不允许 live fetch。",
        ]
    )
    return "\n".join(lines)


def build_manifest(
    run_id,
    generated_at,
    db_env,
    guard_blocked,
    guard_reasons,
    counts,
    idem_first,
    idem_second,
    selected,
    skipped,
    man_cal,
    eng_cal,
    jpn_cal,
    lee_cal,
    request_budget,
    per_team_budget,
    per_competition_budget,
) -> dict:
    idem_pass = all(idem_second.get(t, 0) == 0 for t in TABLE_ORDER)
    return {
        "schema_version": "fotmob_registry_seed_dev_execution_v1",
        "lifecycle": "current-state",
        "phase": "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DEV-EXECUTION-NO-LIVE-FETCH",
        "run_id": run_id,
        "generated_at": generated_at,
        "db_environment": db_env,
        "production_db_guard": "pass" if not guard_blocked else "blocked",
        "production_db_guard_details": guard_reasons,
        "production_db_write_performed": False,
        "source_fixture_path": "docs/_fixtures/fotmob_registry_seed_dry_run_plan.json",
        "inserted_counts": {f"football_{t}": idem_first.get(t, 0) for t in TABLE_ORDER},
        "existing_counts": {
            f"football_{t}": counts.get(t, 0) - idem_first.get(t, 0) for t in TABLE_ORDER
        },
        "final_counts": {f"football_{t}": counts.get(t, 0) for t in TABLE_ORDER},
        "idempotency": {
            "first_run_total": sum(idem_first.values()),
            "second_run_total": sum(idem_second.values()),
            "pass": idem_pass,
        },
        "target_selection": {
            "input_target_count": sum(counts.get(t, 0) for t in ["match_targets"]),
            "selected_target_count": len(selected),
            "skipped_target_count": len(skipped),
            "skip_reasons": list(set(s.get("skip_reason", "") for s in skipped)),
            "request_budget": request_budget,
            "per_team_budget": per_team_budget,
            "per_competition_budget": per_competition_budget,
            "budget_respected": len(selected) <= request_budget,
        },
        "team_full_calendar": {
            "manchester_united_target_count": len(man_cal),
            "england_target_count": len(eng_cal),
            "kashima_antlers_target_count": len(jpn_cal),
            "leeds_united_target_count": len(lee_cal),
        },
        "safety": {
            "network_fetch_performed": False,
            "db_write_performed": True,
            "db_write_scope": "registry_tables_only",
            "raw_json_write_performed": False,
            "fotmob_raw_match_payloads_write_performed": False,
            "raw_match_data_write_performed": False,
            "feature_parse_performed": False,
            "scheduler_enabled": False,
            "raw_write_ready_marked": False,
        },
        "recommended_next_phase": "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DEV-EXECUTION-REVIEW",
    }


# -- Main --
def main() -> int:
    parser = argparse.ArgumentParser(description="FotMob registry seed dev execution")
    parser.add_argument("--input-plan", required=True)
    parser.add_argument("--output-manifest", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--request-budget", type=int, default=10)
    parser.add_argument("--per-team-budget", type=int, default=5)
    parser.add_argument("--per-competition-budget", type=int, default=4)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--require-dev-db", action="store_true", default=True)
    args = parser.parse_args()

    # Production guard
    db_host = os.environ.get("DB_HOST", "db")
    guard_blocked, guard_reasons = check_production_guard(db_host)
    if guard_blocked:
        print("ERROR: Production DB guard blocked execution:")
        for r in guard_reasons:
            print(f"  - {r}")
        print("Set --require-dev-db flag and ensure DB_HOST is dev/local.")
        return 1
    print(f"Production guard: pass (env={get_db_environment(db_host)})")

    db_env = get_db_environment(db_host)

    # Read plan
    plan_path = Path(args.input_plan)
    if not plan_path.exists():
        print(f"ERROR: plan fixture not found: {plan_path}", file=sys.stderr)
        return 1
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    # Connect
    try:
        conn, _ = db_connect()
        print(f"Connected to DB: {db_env}")
    except Exception as e:
        print(f"ERROR: Cannot connect to DB: {e}", file=sys.stderr)
        return 1

    try:
        # Phase2C batch2: unified runtime guard before DB write
        assert_db_write_allowed(
            script_name="fotmob_registry_seed_dev_execution.py",
            operation="INSERT",
            target="football_registry_tables",
            tables=[
                "football_teams",
                "football_competitions",
                "football_competition_editions",
                "football_team_competition_participation",
                "football_match_targets",
                "football_match_target_teams",
                "football_source_identities",
            ],
        )

        # First run
        idem_first = execute_seed(conn, plan)
        first_total = sum(idem_first.values())
        print(f"First run: {first_total} inserted across {len(TABLE_ORDER)} tables")

        # Second run (idempotency)
        idem_second = execute_seed(conn, plan)
        second_total = sum(idem_second.values())
        print(f"Second run: {second_total} inserted (should be 0 for idempotency)")

        # Final counts
        counts = query_existing_counts(conn)
        for t, c in counts.items():
            print(f"  football_{t}: {c} rows")

        # Target selection query
        selected, skipped = query_target_selection(
            conn, args.request_budget, args.per_team_budget, args.per_competition_budget
        )
        print(f"Target selection: {len(selected)} selected, {len(skipped)} skipped")

        # Team full-calendar
        man_cal = query_team_calendar(conn, "Manchester United")
        eng_cal = query_team_calendar(conn, "England")
        jpn_cal = query_team_calendar(conn, "Kashima Antlers")
        lee_cal = query_team_calendar(conn, "Leeds United")
        print(
            f"Full-calendar: MU={len(man_cal)}, ENG={len(eng_cal)}, JPN={len(jpn_cal)}, LEE={len(lee_cal)}"
        )

        # Generate artifacts
        generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        report = build_report(
            args.run_id,
            generated_at,
            db_env,
            guard_blocked,
            guard_reasons,
            counts,
            idem_first,
            idem_second,
            selected,
            skipped,
            man_cal,
            eng_cal,
            jpn_cal,
            lee_cal,
            args.request_budget,
            args.per_team_budget,
            args.per_competition_budget,
        )
        manifest = build_manifest(
            args.run_id,
            generated_at,
            db_env,
            guard_blocked,
            guard_reasons,
            counts,
            idem_first,
            idem_second,
            selected,
            skipped,
            man_cal,
            eng_cal,
            jpn_cal,
            lee_cal,
            args.request_budget,
            args.per_team_budget,
            args.per_competition_budget,
        )

        Path(args.output_manifest).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output_manifest).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(report, encoding="utf-8")
        print(f"Manifest: {args.output_manifest}")
        print(f"Report:   {args.report}")

        idem_pass = all(idem_second.get(t, 0) == 0 for t in TABLE_ORDER)
        print(f"\nIdempotency: {'PASS' if idem_pass else 'FAIL'}")

    except Exception as e:
        conn.rollback()
        print(f"ERROR during seed: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
