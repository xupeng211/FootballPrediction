#!/usr/bin/env python3
"""Controlled FotMob live availability probe without raw writes.
lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ONE-DAY-LIVE-FETCH-NO-RAW-WRITE

Reads dev/local registry targets, performs at most three serial FotMob GET
probes, and records only response metadata. It never persists response bodies,
raw JSON, DB rows, scheduler state, or feature output.
Permanent manual phase helper. Not wired to Makefile, npm scripts, or CI;
cleanup after a versioned collector probe gate supersedes it.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import ssl
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import ProxyHandler, Request, build_opener

import psycopg2

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ONE-DAY-LIVE-FETCH-NO-RAW-WRITE"
SCHEMA_VERSION = "fotmob_one_day_live_fetch_no_raw_write_v1"
ALLOW_FLAG = "ALLOW_FOTMOB_LIVE_FETCH_NO_RAW_WRITE"
NEXT_SAFE_REVIEW = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-LIVE-FETCH-ROUTE-REVIEW-NO-WRITE"
NEXT_RAW_WRITE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-RAW-JSON-DEV-WRITE"
MAX_TARGETS_LIMIT = 3
MAX_ATTEMPTS_PER_TARGET = 1
CONCURRENCY = 1
MAX_RESPONSE_BYTES = 1_000_000
JSON_KEY_LIMIT = 30
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
SAFETY_FALSE = {
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
    "retry_storm_performed": False,
}


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


def query_probe_targets(conn, limit: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sql = """
        SELECT
            mt.id,
            mt.source,
            mt.source_match_id,
            mt.source_url,
            mt.priority,
            mt.match_date,
            mt.target_state,
            mt.raw_json_status,
            c.competition_name,
            ht.team_name AS home_team_name,
            at.team_name AS away_team_name,
            (
                EXISTS (
                    SELECT 1
                    FROM football_match_target_teams mtt
                    JOIN football_teams t ON t.id = mtt.team_id
                    JOIN football_source_identities si
                      ON si.source = mt.source
                     AND si.entity_type = 'team'
                     AND si.source_entity_id = t.source_team_id
                    WHERE mtt.match_target_id = mt.id
                )
                OR EXISTS (
                    SELECT 1
                    FROM football_source_identities si
                    WHERE si.source = mt.source
                      AND si.entity_type = 'competition'
                      AND si.source_entity_id = c.source_competition_id
                )
            ) AS source_identity_available
        FROM football_match_targets mt
        LEFT JOIN football_competitions c ON c.id = mt.competition_id
        LEFT JOIN football_teams ht ON ht.id = mt.home_team_id
        LEFT JOIN football_teams at ON at.id = mt.away_team_id
        WHERE mt.source = 'fotmob'
          AND mt.target_state IN ('pending_raw_fetch', 'failed')
          AND COALESCE(mt.raw_json_status, 'missing') IN ('missing', 'pending', 'failed', 'stale')
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
        "source_url",
        "priority",
        "match_date",
        "target_state",
        "raw_json_status",
        "competition_name",
        "home_team_name",
        "away_team_name",
        "source_identity_available",
    ]
    selected: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    with conn.cursor() as cur:
        cur.execute(sql)
        for row in cur.fetchall():
            target = dict(zip(columns, row, strict=True))
            target["match_date"] = (
                target["match_date"].isoformat() if target.get("match_date") else None
            )
            if not target["source_identity_available"]:
                skipped.append({**target, "skip_reason": "missing_source_identity"})
                continue
            if len(selected) < limit:
                selected.append(target)
    return selected, skipped


def build_target_url(target: dict[str, Any]) -> tuple[str, str]:
    if target.get("source_url"):
        return str(target["source_url"]), "source_url"
    match_id = quote(str(target["source_match_id"]), safe="")
    return f"https://www.fotmob.com/matches/{match_id}", "match_page_from_source_match_id"


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _body_category(content_type: str, payload: bytes, json_parse_ok: bool) -> str | None:
    lower_type = content_type.lower()
    lower_body = payload[:4096].lower()
    challenge_tokens = [b"captcha", b"cloudflare", b"cf-chl", b"bot challenge"]
    if any(token in lower_body for token in challenge_tokens):
        return "captcha_or_bot_challenge"
    if "html" in lower_type or lower_body.lstrip().startswith(b"<!doctype html"):
        return "unexpected_html"
    if "json" not in lower_type and not lower_body.lstrip().startswith((b"{", b"[")):
        return "content_type_not_json_like"
    if not json_parse_ok:
        return "schema_shift"
    return None


def _json_probe(payload: bytes) -> tuple[bool, list[str]]:
    try:
        parsed = json.loads(payload.decode("utf-8"))
    except Exception:
        return False, []
    if isinstance(parsed, dict):
        return True, list(parsed.keys())[:JSON_KEY_LIMIT]
    if isinstance(parsed, list):
        return True, ["<list>"]
    return True, [type(parsed).__name__]


def probe_target(target: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    url, endpoint_label = build_target_url(target)
    started = _utc_now()
    result: dict[str, Any] = {
        "target_id": target["target_id"],
        "source_match_id": target["source_match_id"],
        "endpoint_label": endpoint_label,
        "request_url": url,
        "request_started_at": started,
        "request_ended_at": None,
        "status_code": None,
        "content_type": None,
        "response_size_bytes": 0,
        "json_parse_ok": False,
        "top_level_keys_sample": [],
        "error_category": None,
        "stop_policy_triggered": False,
        "retry_count": 0,
    }
    opener = build_opener(ProxyHandler({}))
    req = Request(url, method="GET")
    try:
        with opener.open(req, timeout=timeout_seconds) as response:
            payload = response.read(MAX_RESPONSE_BYTES + 1)
            result["status_code"] = response.getcode()
            result["content_type"] = response.headers.get("content-type", "")
    except HTTPError as exc:
        payload = exc.read(MAX_RESPONSE_BYTES + 1)
        result["status_code"] = exc.code
        result["content_type"] = exc.headers.get("content-type", "")
    except TimeoutError:
        payload = b""
        result["error_category"] = "network_timeout"
    except (URLError, OSError, ssl.SSLError) as exc:
        payload = b""
        result["error_category"] = "network_error"
        result["network_error_detail"] = type(exc).__name__

    result["request_ended_at"] = _utc_now()
    result["response_size_bytes"] = len(payload)
    if len(payload) > MAX_RESPONSE_BYTES:
        result["error_category"] = "response_too_large"
    if payload and len(payload) <= MAX_RESPONSE_BYTES:
        parse_ok, keys = _json_probe(payload)
        result["json_parse_ok"] = parse_ok
        result["top_level_keys_sample"] = keys
        if result["error_category"] is None:
            result["error_category"] = _body_category(
                str(result["content_type"] or ""), payload, parse_ok
            )
    status = result["status_code"]
    if status == 403:
        result["error_category"] = "http_403"
    elif status == 429:
        result["error_category"] = "http_429"
    if result["error_category"]:
        result["stop_policy_triggered"] = True
    return result


def status_from_results(fetch_results: list[dict[str, Any]], stopped: bool, blocked: bool) -> str:
    if blocked or not fetch_results:
        return "blocked"
    return "partial" if stopped else "pass"


def build_manifest(
    args: argparse.Namespace,
    *,
    db_env: str,
    guard_reasons: list[str],
    explicit: bool,
    db_read: bool,
    selected_targets: list[dict[str, Any]],
    skipped_targets: list[dict[str, Any]],
    fetch_results: list[dict[str, Any]],
    stop_reason: str | None,
    blocked: bool,
) -> dict[str, Any]:
    attempted = len(fetch_results)
    completed = sum(1 for item in fetch_results if item.get("status_code") is not None)
    status_counts = Counter(str(item.get("status_code")) for item in fetch_results)
    content_types = Counter(str(item.get("content_type") or "none") for item in fetch_results)
    errors = Counter(str(item.get("error_category") or "none") for item in fetch_results)
    stopped = bool(stop_reason)
    review_status = status_from_results(fetch_results, stopped, blocked)
    recommended = NEXT_RAW_WRITE if review_status == "pass" else NEXT_SAFE_REVIEW
    return {
        "schema_version": SCHEMA_VERSION,
        "lifecycle": "current-state",
        "phase": PHASE,
        "run_id": args.run_id,
        "generated_at": _utc_now(),
        "explicit_allow_flag_present": explicit,
        "db_environment": db_env,
        "production_db_guard": "pass" if not guard_reasons else "blocked",
        "production_db_guard_details": guard_reasons,
        "db_read_performed": db_read,
        "db_write_performed": False,
        "production_db_write_performed": False,
        "target_selection_source": "db_backed_selection",
        "max_live_fetch_targets": args.max_targets,
        "attempted_target_count": attempted,
        "completed_target_count": completed,
        "skipped_target_count": len(skipped_targets) + max(0, len(selected_targets) - attempted),
        "stopped_early": stopped,
        "stop_reason": stop_reason,
        "request_budget": {
            "global_request_budget": MAX_TARGETS_LIMIT,
            "used": attempted,
            "remaining": max(0, MAX_TARGETS_LIMIT - attempted),
        },
        "rate_limit": {
            "concurrency": CONCURRENCY,
            "sleep_seconds": args.sleep_seconds,
            "max_attempts_per_target": MAX_ATTEMPTS_PER_TARGET,
        },
        "selected_live_probe_targets": selected_targets,
        "skipped_targets": skipped_targets,
        "fetch_results": fetch_results,
        "status_code_summary": dict(status_counts),
        "content_type_summary": dict(content_types),
        "json_parse_ok_count": sum(1 for item in fetch_results if item["json_parse_ok"]),
        "error_categories": dict(errors),
        "safety": {"network_fetch_performed": attempted > 0, **SAFETY_FALSE},
        "embedded_review": {
            "one_day_live_fetch_no_raw_write_status": review_status,
            "review_report_path": str(args.review_report),
        },
        "recommended_next_phase": recommended,
    }


def build_report(manifest: dict[str, Any]) -> str:
    rows = [
        (
            f"| {item['source_match_id']} | {item.get('status_code')} | "
            f"{item.get('content_type') or 'none'} | {item['response_size_bytes']} | "
            f"{str(item['json_parse_ok']).lower()} | {item.get('error_category') or 'none'} | "
            f"{str(item['stop_policy_triggered']).lower()} |"
        )
        for item in manifest["fetch_results"]
    ]
    if not rows:
        rows = ["| none | none | none | 0 | false | none | false |"]
    return "\n".join(
        [
            "<!-- markdownlint-disable MD013 -->",
            "",
            "# FotMob One-day Live Fetch No Raw Write",
            "",
            "- lifecycle: current-state",
            f"- phase: {PHASE}",
            f"- run_id: {manifest['run_id']}",
            "- purpose: 极小规模真实 FotMob live fetch availability probe",
            f"- explicit_allow_flag_present: {str(manifest['explicit_allow_flag_present']).lower()}",
            "- DB target source: db_backed_selection",
            "- 本阶段真实访问 FotMob（若有 attempted_target_count > 0）",
            "- 本阶段没有保存 raw response body",
            "- 本阶段没有写 raw JSON",
            "- 本阶段没有写 DB",
            "- 本阶段没有 parser",
            "- 本阶段没有 scheduler",
            "- 本阶段不是大规模采集",
            "",
            "## Probe Result",
            "",
            f"- attempted_target_count: {manifest['attempted_target_count']}",
            f"- completed_target_count: {manifest['completed_target_count']}",
            f"- skipped_target_count: {manifest['skipped_target_count']}",
            f"- stopped_early: {str(manifest['stopped_early']).lower()}",
            f"- stop_reason: {manifest['stop_reason'] or 'none'}",
            f"- status_code_summary: {manifest['status_code_summary']}",
            f"- content_type_summary: {manifest['content_type_summary']}",
            f"- json_parse_ok_count: {manifest['json_parse_ok_count']}",
            f"- error_categories: {manifest['error_categories']}",
            "",
            "## Request Budget And Rate Limit",
            "",
            f"- global_request_budget: {manifest['request_budget']['global_request_budget']}",
            f"- used: {manifest['request_budget']['used']}",
            f"- remaining: {manifest['request_budget']['remaining']}",
            f"- concurrency: {manifest['rate_limit']['concurrency']}",
            f"- sleep_seconds: {manifest['rate_limit']['sleep_seconds']}",
            f"- max_attempts_per_target: {manifest['rate_limit']['max_attempts_per_target']}",
            "",
            "## Per-target Result",
            "",
            "| source_match_id | status_code | content_type | response_size_bytes | json_parse_ok | error_category | stop_policy_triggered |",
            "|-----------------|-------------|--------------|---------------------|---------------|----------------|-----------------------|",
            *rows,
            "",
            "## Safety Review",
            "",
            f"- network_fetch_performed: {str(manifest['safety']['network_fetch_performed']).lower()}",
            "- raw_response_body_saved: false",
            "- db_write_performed: false",
            "- raw_json_write_performed: false",
            "- fotmob_raw_match_payloads_write_performed: false",
            "- raw_match_data_write_performed: false",
            "- feature_parse_performed: false",
            "- scheduler_enabled: false",
            "- raw_write_ready_marked: false",
            "- browser_automation_performed: false",
            "- captcha_bypass_performed: false",
            "- proxy_rotation_performed: false",
            "- retry_storm_performed: false",
            "",
            "## Remaining Gaps",
            "",
            "- 尚未授权 raw JSON dev write",
            "- 尚未验证长期稳定 route",
            "- 尚未启用 scheduler",
            "- 尚未实现 parser/features/training/prediction",
            "",
            "## Recommended Next Phase",
            "",
            f"- {manifest['recommended_next_phase']}",
            "- 若本阶段触发 stop policy，应先做 no-write route review，不得直接 raw write",
            "- 若后续进入 raw write，仍只允许 dev/local、极少量、review 后再扩大",
            "",
        ]
    )


def build_review_report(manifest: dict[str, Any]) -> str:
    status = manifest["embedded_review"]["one_day_live_fetch_no_raw_write_status"]
    return "\n".join(
        [
            "<!-- markdownlint-disable MD013 -->",
            "",
            "# FotMob One-day Live Fetch No Raw Write Embedded Review",
            "",
            "- lifecycle: current-state",
            f"- reviewed_phase: {PHASE}",
            f"- status: {status}",
            "",
            "## Checks",
            "",
            f"- explicit allow flag review: {'pass' if manifest['explicit_allow_flag_present'] else 'blocked'}",
            f"- max target review: {'pass' if manifest['max_live_fetch_targets'] <= 3 else 'blocked'}",
            f"- rate limit review: concurrency={manifest['rate_limit']['concurrency']}, max_attempts={manifest['rate_limit']['max_attempts_per_target']}",
            f"- no raw body review: {'pass' if not manifest['safety']['raw_response_body_saved'] else 'blocked'}",
            f"- no DB write review: {'pass' if not manifest['db_write_performed'] else 'blocked'}",
            f"- no raw JSON write review: {'pass' if not manifest['safety']['raw_json_write_performed'] else 'blocked'}",
            f"- no feature parse review: {'pass' if not manifest['safety']['feature_parse_performed'] else 'blocked'}",
            f"- no scheduler review: {'pass' if not manifest['safety']['scheduler_enabled'] else 'blocked'}",
            f"- no browser automation review: {'pass' if not manifest['safety']['browser_automation_performed'] else 'blocked'}",
            f"- no proxy rotation review: {'pass' if not manifest['safety']['proxy_rotation_performed'] else 'blocked'}",
            f"- no captcha bypass review: {'pass' if not manifest['safety']['captcha_bypass_performed'] else 'blocked'}",
            f"- stop policy present: {'pass' if 'stopped_early' in manifest and 'stop_reason' in manifest else 'blocked'}",
            f"- next phase recommendation: {manifest['recommended_next_phase']}",
            "",
        ]
    )


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
    parser = argparse.ArgumentParser(description="FotMob one-day live fetch probe")
    parser.add_argument(
        "--output-manifest",
        default="docs/_manifests/fotmob_one_day_live_fetch_no_raw_write_manifest.json",
    )
    parser.add_argument(
        "--report", default="docs/_reports/FOTMOB_ONE_DAY_LIVE_FETCH_NO_RAW_WRITE.md"
    )
    parser.add_argument(
        "--review-report",
        default="docs/_reports/FOTMOB_ONE_DAY_LIVE_FETCH_NO_RAW_WRITE_REVIEW.md",
    )
    parser.add_argument("--max-targets", type=int, default=MAX_TARGETS_LIMIT)
    parser.add_argument("--timeout-seconds", type=int, default=15)
    parser.add_argument("--sleep-seconds", type=int, default=5)
    parser.add_argument("--run-id", default="fotmob_one_day_live_fetch_no_raw_write_v1")
    parser.add_argument("--require-dev-db", action="store_true", default=True)
    return parser.parse_args()


def blocked_manifest(args: argparse.Namespace, reason: str, explicit: bool) -> dict[str, Any]:
    return build_manifest(
        args,
        db_env="not_checked",
        guard_reasons=[],
        explicit=explicit,
        db_read=False,
        selected_targets=[],
        skipped_targets=[{"skip_reason": reason}],
        fetch_results=[],
        stop_reason=reason,
        blocked=True,
    )


def main() -> int:
    args = parse_args()
    explicit = os.environ.get(ALLOW_FLAG) == "1"
    if args.max_targets > MAX_TARGETS_LIMIT:
        manifest = blocked_manifest(args, "max_targets_exceeds_3", explicit)
        write_artifacts(args, manifest)
        print("ERROR: max targets cannot exceed 3", file=sys.stderr)
        return 1
    if args.timeout_seconds > 15 or args.sleep_seconds < 5:
        manifest = blocked_manifest(args, "unsafe_timeout_or_sleep", explicit)
        write_artifacts(args, manifest)
        print("ERROR: unsafe timeout/sleep parameters", file=sys.stderr)
        return 1
    if not explicit:
        manifest = blocked_manifest(args, "missing_explicit_allow_flag", explicit)
        write_artifacts(args, manifest)
        print(f"ERROR: missing {ALLOW_FLAG}=1", file=sys.stderr)
        return 1

    db_host = os.environ.get("DB_HOST", "db")
    guard_blocked, guard_reasons = check_production_guard(db_host)
    if args.require_dev_db and guard_blocked:
        manifest = blocked_manifest(args, "production_db_guard_blocked", explicit)
        manifest["production_db_guard"] = "blocked"
        manifest["production_db_guard_details"] = guard_reasons
        write_artifacts(args, manifest)
        print("ERROR: production DB guard blocked execution", file=sys.stderr)
        return 1
    db_env = get_db_environment(db_host)

    try:
        conn = db_connect()
        selected, skipped = query_probe_targets(conn, args.max_targets)
    except Exception as exc:
        manifest = blocked_manifest(args, "db_read_failed", explicit)
        manifest["db_environment"] = db_env
        manifest["production_db_guard"] = "pass"
        manifest["db_read_error"] = type(exc).__name__
        write_artifacts(args, manifest)
        print(f"ERROR: DB read failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if "conn" in locals():
            conn.close()

    if not selected:
        manifest = build_manifest(
            args,
            db_env=db_env,
            guard_reasons=[],
            explicit=explicit,
            db_read=True,
            selected_targets=[],
            skipped_targets=skipped or [{"skip_reason": "blocked_no_targets"}],
            fetch_results=[],
            stop_reason="blocked_no_targets",
            blocked=True,
        )
        write_artifacts(args, manifest)
        print("ERROR: no DB-backed selected targets available", file=sys.stderr)
        return 1

    results: list[dict[str, Any]] = []
    stop_reason: str | None = None
    for index, target in enumerate(selected):
        result = probe_target(target, args.timeout_seconds)
        results.append(result)
        if result["stop_policy_triggered"]:
            stop_reason = str(result["error_category"])
            break
        if index < len(selected) - 1:
            time.sleep(args.sleep_seconds)

    manifest = build_manifest(
        args,
        db_env=db_env,
        guard_reasons=[],
        explicit=explicit,
        db_read=True,
        selected_targets=selected,
        skipped_targets=skipped,
        fetch_results=results,
        stop_reason=stop_reason,
        blocked=False,
    )
    write_artifacts(args, manifest)
    print(f"Attempted targets: {manifest['attempted_target_count']}")
    print(f"Completed targets: {manifest['completed_target_count']}")
    print(f"Stopped early: {manifest['stopped_early']} ({manifest['stop_reason'] or 'none'})")
    print(
        f"Embedded review: {manifest['embedded_review']['one_day_live_fetch_no_raw_write_status']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
