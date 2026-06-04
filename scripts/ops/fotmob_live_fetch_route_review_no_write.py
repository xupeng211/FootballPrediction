#!/usr/bin/env python3
"""Review FotMob live fetch route and source identities without raw writes.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-LIVE-FETCH-ROUTE-REVIEW-NO-WRITE

Reads previous phase manifests, inspects dev/local registry source identities,
analyses route construction correctness, and optionally probes at most three
route candidates.  It never persists response bodies, raw JSON, DB rows,
scheduler state, or feature output.

Permanent manual phase helper. Not wired to Makefile, npm scripts, or CI;
cleanup after a versioned collector route validation gate supersedes it.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
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

from fotmob_live_fetch_route_review_no_write_report import (
    blocked_manifest,
    parse_args,
    write_artifacts,
)
import psycopg2

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-LIVE-FETCH-ROUTE-REVIEW-NO-WRITE"
SCHEMA_VERSION = "fotmob_live_fetch_route_review_no_write_v1"
ALLOW_FLAG = "ALLOW_FOTMOB_ROUTE_REVIEW_NO_WRITE"
NEXT_SAFE_REVIEW = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-DESIGN-NO-WRITE"
NEXT_RAW_WRITE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-RAW-JSON-DEV-WRITE"
MAX_ROUTE_CANDIDATES = 3
MAX_LIVE_PROBE_REQUESTS = 3
MAX_ATTEMPTS_PER_ROUTE = 1
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
FIXTURE_LIKE_PREFIXES = ("fixture-", "synthetic-", "placeholder-", "dummy-")
FOTMOB_MATCH_ID_REAL_PATTERN = r"^\d{5,8}$"
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


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


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
# source identity analysis
# ---------------------------------------------------------------------------


def _is_fixture_like(value: str) -> bool:
    """Heuristic: a source_match_id or source_entity_id looks synthetic."""
    if not value:
        return True
    return any(value.lower().startswith(p) for p in FIXTURE_LIKE_PREFIXES)


def _is_numeric_id(value: str) -> bool:
    return bool(value and value.isdigit() and 5 <= len(value) <= 8)


def analyse_source_identities(conn) -> dict[str, Any]:
    """Read registry source identities and assess realism."""
    sql = """
        SELECT
            si.id,
            si.source,
            si.entity_type,
            si.source_entity_id,
            CASE WHEN si.entity_type = 'team' THEN t.team_name ELSE NULL END AS team_name,
            CASE WHEN si.entity_type = 'competition' THEN c.competition_name ELSE NULL END
                AS competition_name
        FROM football_source_identities si
        LEFT JOIN football_teams t
            ON si.entity_type = 'team'
           AND si.source = 'fotmob'
           AND t.source_team_id = si.source_entity_id
        LEFT JOIN football_competitions c
            ON si.entity_type = 'competition'
           AND si.source = 'fotmob'
           AND c.source_competition_id = si.source_entity_id
        WHERE si.source = 'fotmob'
        ORDER BY si.entity_type, si.id
    """
    identities: list[dict[str, Any]] = []
    with conn.cursor() as cur:
        cur.execute(sql)
        identities.extend(
            {
                "id": row[0],
                "source": row[1],
                "entity_type": row[2],
                "source_entity_id": row[3],
                "entity_name": row[4] or row[5] or "unknown",
            }
            for row in cur.fetchall()
        )

    total = len(identities)
    fixture_like = sum(1 for i in identities if _is_fixture_like(i["source_entity_id"]))
    numeric = sum(1 for i in identities if _is_numeric_id(i["source_entity_id"]))
    by_type: dict[str, list[str]] = {}
    for i in identities:
        by_type.setdefault(i["entity_type"], []).append(i["source_entity_id"])

    quality = (
        "fixture_like" if fixture_like == total else ("candidate" if numeric > 0 else "unknown")
    )
    return {
        "total_identities": total,
        "fixture_like_count": fixture_like,
        "numeric_count": numeric,
        "quality": quality,
        "by_entity_type": {k: sorted(v) for k, v in by_type.items()},
        "identities": identities,
    }


def analyse_match_targets(conn) -> dict[str, Any]:
    """Read match targets and assess source_match_id realism."""
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
            at.team_name AS away_team_name
        FROM football_match_targets mt
        LEFT JOIN football_competitions c ON c.id = mt.competition_id
        LEFT JOIN football_teams ht ON ht.id = mt.home_team_id
        LEFT JOIN football_teams at ON at.id = mt.away_team_id
        WHERE mt.source = 'fotmob'
        ORDER BY mt.priority DESC, mt.match_date ASC NULLS LAST
    """
    targets: list[dict[str, Any]] = []
    with conn.cursor() as cur:
        cur.execute(sql)
        for row in cur.fetchall():
            sid = str(row[2] or "")
            targets.append(
                {
                    "target_id": row[0],
                    "source": row[1],
                    "source_match_id": sid,
                    "source_url": row[3],
                    "priority": row[4],
                    "match_date": row[5].isoformat() if row[5] else None,
                    "target_state": row[6],
                    "raw_json_status": row[7],
                    "competition_name": row[8],
                    "home_team_name": row[9],
                    "away_team_name": row[10],
                    "source_match_id_fixture_like": _is_fixture_like(sid),
                    "source_match_id_numeric": _is_numeric_id(sid),
                }
            )

    total = len(targets)
    fixture_like = sum(1 for t in targets if t["source_match_id_fixture_like"])
    numeric = sum(1 for t in targets if t["source_match_id_numeric"])
    has_source_url = sum(1 for t in targets if t["source_url"])
    return {
        "total_match_targets": total,
        "fixture_like_source_match_ids": fixture_like,
        "numeric_source_match_ids": numeric,
        "has_source_url_count": has_source_url,
        "match_id_realism": "all_fixture_like"
        if fixture_like == total
        else ("mixed" if numeric > 0 else "unknown"),
        "targets": targets,
    }


def build_route_candidates(
    _identity_analysis: dict[str, Any],
    target_analysis: dict[str, Any],
) -> list[dict[str, Any]]:
    """Derive route candidates from existing repo evidence.

    When all source_match_ids are fixture-like and no real IDs exist,
    return an empty list — no reliable candidates to probe.
    """
    candidates: list[dict[str, Any]] = []

    # candidate-source: known FotMob match-detail page pattern
    # from historical ADG data: https://www.fotmob.com/matches/{hash}/{match_id}
    # We CANNOT use this without a real hash+match_id pair.

    # candidate-source: FotMob API pattern
    # https://www.fotmob.com/api/matchDetails?matchId={id}
    # Historical ADG44 found this returns 404; pattern is known but
    # requires a real numeric match_id.

    # candidate-source: team fixtures page
    # Requires real FotMob team ID, which we lack.

    # candidate-source: league fixtures page
    # Requires real FotMob league ID, which we lack.

    # candidate-source: date-based fixtures
    # https://www.fotmob.com/fixtures?date={YYYY-MM-DD}
    # This might work without any specific ID, but returns HTML, not JSON.

    # If any target has a non-fixture source_match_id, treat it as a candidate.
    for target in target_analysis["targets"]:
        sid = target["source_match_id"]
        if not _is_fixture_like(sid) and sid:
            url = f"https://www.fotmob.com/matches/{quote(sid, safe='')}"
            candidates.append(
                {
                    "candidate_label": "match_page_from_source_match_id",
                    "candidate_source": "db_source_match_id",
                    "candidate_confidence": "low",
                    "source_match_id": sid,
                    "url_pattern_hash": hashlib.sha256(url.encode()).hexdigest()[:12],
                    "url_redacted": f"https://www.fotmob.com/matches/<{len(sid)}_chars>",
                }
            )
            if len(candidates) >= MAX_ROUTE_CANDIDATES:
                break

    # If we still have no candidates, check for source_url values
    if not candidates:
        for target in target_analysis["targets"]:
            if target["source_url"]:
                candidates.append(
                    {
                        "candidate_label": "source_url_from_db",
                        "candidate_source": "db_source_url",
                        "candidate_confidence": "low",
                        "source_match_id": target["source_match_id"],
                        "url_pattern_hash": hashlib.sha256(
                            str(target["source_url"]).encode()
                        ).hexdigest()[:12],
                        "url_redacted": str(target["source_url"])[:80],
                    }
                )
                if len(candidates) >= MAX_ROUTE_CANDIDATES:
                    break

    return candidates


# ---------------------------------------------------------------------------
# live probe helpers (only used when reliable candidates exist)
# ---------------------------------------------------------------------------


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


def probe_route_candidate(
    candidate: dict[str, Any],
    timeout_seconds: int,
    sleep_seconds: int,
) -> dict[str, Any]:
    url = candidate.get("url")
    if not url:
        return {
            "candidate_label": candidate["candidate_label"],
            "probe_attempted": False,
            "skip_reason": "no_url",
            "status_code": None,
            "content_type": None,
            "response_size_bytes": 0,
            "json_parse_ok": False,
            "top_level_keys_sample": [],
            "error_category": "blocked_no_url",
            "stop_policy_triggered": False,
        }
    started = _utc_now()
    result: dict[str, Any] = {
        "candidate_label": candidate["candidate_label"],
        "probe_attempted": True,
        "request_url_redacted": "https://www.fotmob.com/.../<redacted>",
        "request_started_at": started,
        "request_ended_at": None,
        "status_code": None,
        "content_type": None,
        "response_size_bytes": 0,
        "json_parse_ok": False,
        "top_level_keys_sample": [],
        "error_category": None,
        "stop_policy_triggered": False,
    }
    opener = build_opener(ProxyHandler({}))
    req = Request(url, method="GET")
    req.add_header(
        "User-Agent",
        "Mozilla/5.0 (compatible; FotMobRouteReview/1.0; +https://github.com/xupeng211/FootballPrediction)",
    )
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
        result["error_category"] = result["error_category"] or "response_too_large"
    elif payload:
        parse_ok, keys = _json_probe(payload)
        result["json_parse_ok"] = parse_ok
        result["top_level_keys_sample"] = keys
        if result["error_category"] is None:
            result["error_category"] = _body_category(
                str(result["content_type"] or ""), payload, parse_ok
            )

    status = result["status_code"]
    if status == 403:
        result["error_category"] = result["error_category"] or "http_403"
    elif status == 429:
        result["error_category"] = result["error_category"] or "http_429"
    if result["error_category"]:
        result["stop_policy_triggered"] = True

    if sleep_seconds > 0:
        time.sleep(sleep_seconds)
    return result


# ---------------------------------------------------------------------------
# manifest
# ---------------------------------------------------------------------------


def load_previous_manifest(path: str) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def determine_route_review_status(
    _identity_analysis: dict[str, Any],
    _target_analysis: dict[str, Any],
    candidates: list[dict[str, Any]],
    probe_results: list[dict[str, Any]],
    blocked: bool,
) -> tuple[str, str | None]:
    if blocked:
        return "blocked", "missing_explicit_allow_flag_or_production_guard"
    if not candidates:
        return "blocked", "blocked_no_reliable_route_candidate"
    if not probe_results:
        return "partial", "candidates_found_but_no_probe_executed"
    json_ok = sum(1 for r in probe_results if r.get("json_parse_ok"))
    errors = [r.get("error_category") for r in probe_results if r.get("error_category")]
    if any(e in ("http_403", "captcha_or_bot_challenge") for e in errors):
        return "blocked", "blocked_forbidden"
    if any(e in ("http_429",) for e in errors):
        return "partial", "rate_limited"
    if json_ok > 0:
        return "partial", "json_received_but_not_yet_stable"
    if any(e in ("unexpected_html", "content_type_not_json_like") for e in errors):
        return "partial", "route_invalid_html_not_json"
    return "partial", "route_probe_inconclusive"


def build_manifest(
    args: argparse.Namespace,
    *,
    db_env: str,
    guard_reasons: list[str],
    explicit: bool,
    db_read: bool,
    previous_manifest: dict[str, Any],
    identity_analysis: dict[str, Any],
    target_analysis: dict[str, Any],
    candidates: list[dict[str, Any]],
    probe_results: list[dict[str, Any]],
    stop_reason: str | None,
    blocked: bool,
) -> dict[str, Any]:
    prev_fetch = previous_manifest.get("fetch_results", [{}])[0] if previous_manifest else {}
    route_status, status_reason = determine_route_review_status(
        identity_analysis, target_analysis, candidates, probe_results, blocked
    )
    reliable = len(candidates) > 0

    # Determine likely failure reason
    if target_analysis.get("match_id_realism") == "all_fixture_like":
        likely_failure = (
            "all_source_match_ids_are_fixture_like_synthetics; "
            "route_concatenation_with_fixture_prefix_yields_non_existent_fotmob_url; "
            "fotmob_expects_numeric_match_ids_or_hash_id_pairs"
        )
    elif not candidates:
        likely_failure = (
            "no_reliable_route_candidates_found; "
            "source_identities_and_match_ids_do_not_map_to_real_fotmob_entities"
        )
    else:
        likely_failure = (
            f"previous_stop_reason={stop_reason or 'unknown'}; "
            "route_candidates_exist_but_not_yet_validated"
        )

    json_ok_count = sum(1 for r in probe_results if r.get("json_parse_ok"))
    attempted_probes = sum(1 for r in probe_results if r.get("probe_attempted"))

    recommended = (
        NEXT_RAW_WRITE if json_ok_count > 0 and route_status == "pass" else (NEXT_SAFE_REVIEW)
    )

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
        "reviewed_previous_phase": {
            "one_day_live_fetch_no_raw_write_status": previous_manifest.get(
                "embedded_review", {}
            ).get("one_day_live_fetch_no_raw_write_status", "unknown"),
            "previous_stop_reason": prev_fetch.get("error_category", "unknown"),
            "previous_status_code": prev_fetch.get("status_code"),
            "previous_content_type": prev_fetch.get("content_type", "unknown"),
            "previous_json_parse_ok_count": previous_manifest.get("json_parse_ok_count", 0),
        },
        "route_review": {
            "route_review_status": route_status,
            "likely_failure_reason": likely_failure,
            "source_identity_quality": identity_analysis.get("quality", "unknown"),
            "source_match_id_realism": target_analysis.get("match_id_realism", "unknown"),
            "endpoint_route_realism": (
                "invalid_when_fixture_like" if not reliable else "unverified"
            ),
            "match_id_discovery_required": not reliable,
            "reliable_route_candidate_found": reliable,
            "detailed_reason": status_reason,
        },
        "route_candidates": [
            {
                "candidate_label": c["candidate_label"],
                "candidate_source": c["candidate_source"],
                "candidate_confidence": c.get("candidate_confidence", "low"),
                "probe_attempted": False,
                "status_code": None,
                "content_type": None,
                "response_size_bytes": 0,
                "json_parse_ok": False,
                "top_level_keys_sample": [],
                "error_category": None,
                "stop_policy_triggered": False,
            }
            for c in candidates
        ],
        "probe_results": probe_results,
        "request_budget": {
            "max_route_candidates": MAX_ROUTE_CANDIDATES,
            "max_live_probe_requests": MAX_LIVE_PROBE_REQUESTS,
            "used": attempted_probes,
            "remaining": max(0, MAX_LIVE_PROBE_REQUESTS - attempted_probes),
        },
        "rate_limit": {
            "concurrency": CONCURRENCY,
            "sleep_seconds": args.sleep_seconds,
            "max_attempts_per_route": MAX_ATTEMPTS_PER_ROUTE,
        },
        "safety": {
            "network_fetch_performed": attempted_probes > 0,
            **SAFETY_FALSE,
        },
        "embedded_review": {
            "live_fetch_route_review_no_write_status": route_status,
            "review_report_path": str(args.review_report),
        },
        "recommended_next_phase": recommended,
        "source_identity_analysis": {
            "total": identity_analysis.get("total_identities", 0),
            "fixture_like_count": identity_analysis.get("fixture_like_count", 0),
            "numeric_count": identity_analysis.get("numeric_count", 0),
            "quality": identity_analysis.get("quality", "unknown"),
        },
        "match_target_analysis": {
            "total": target_analysis.get("total_match_targets", 0),
            "fixture_like_source_match_ids": target_analysis.get(
                "fixture_like_source_match_ids", 0
            ),
            "numeric_source_match_ids": target_analysis.get("numeric_source_match_ids", 0),
            "has_source_url_count": target_analysis.get("has_source_url_count", 0),
        },
    }


# ---------------------------------------------------------------------------
# reports
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> int:
    args = parse_args()
    explicit = os.environ.get(ALLOW_FLAG) == "1"

    if args.max_route_candidates > MAX_ROUTE_CANDIDATES:
        manifest = blocked_manifest(args, "max_route_candidates_exceeds_3", explicit)
        write_artifacts(args, manifest)
        print("ERROR: max route candidates cannot exceed 3", file=sys.stderr)
        return 1
    if args.max_live_probe_requests > MAX_LIVE_PROBE_REQUESTS:
        manifest = blocked_manifest(args, "max_live_probe_requests_exceeds_3", explicit)
        write_artifacts(args, manifest)
        print("ERROR: max live probe requests cannot exceed 3", file=sys.stderr)
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

    # Load previous phase manifests
    previous_manifest = load_previous_manifest(args.input_live_probe_manifest)
    # target_selection_manifest: read but not strictly required for analysis
    _ = load_previous_manifest(args.input_target_selection_manifest)

    try:
        conn = db_connect()
        identity_analysis = analyse_source_identities(conn)
        target_analysis = analyse_match_targets(conn)
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

    # Build route candidates from current DB state
    candidates = build_route_candidates(identity_analysis, target_analysis)

    # Determine whether we have reliable candidates to probe
    reliable = len(candidates) > 0
    probe_results: list[dict[str, Any]] = []

    if not reliable:
        # No reliable route candidates — blocked, do NOT probe.
        # blocked=False because the safety guards (allow flag, prod) all passed.
        # determine_route_review_status will return blocked_no_reliable_route_candidate.
        manifest = build_manifest(
            args,
            db_env=db_env,
            guard_reasons=[],
            explicit=explicit,
            db_read=True,
            previous_manifest=previous_manifest,
            identity_analysis=identity_analysis,
            target_analysis=target_analysis,
            candidates=candidates,
            probe_results=probe_results,
            stop_reason="blocked_no_reliable_route_candidate",
            blocked=False,
        )
        write_artifacts(args, manifest)
        print("BLOCKED: no reliable route candidates found", file=sys.stderr)
        print("All source_match_ids are fixture-like synthetic values.", file=sys.stderr)
        print("Route review complete (no live probe). See report.", file=sys.stderr)
        print(
            f"Embedded review: {manifest['embedded_review']['live_fetch_route_review_no_write_status']}"
        )
        return 0

    # If we reach here, we have candidates to probe (future scenario)
    stop_reason: str | None = None
    for candidate in candidates[: args.max_live_probe_requests]:
        url = candidate.get("url") or candidate.get("url_pattern_hash", "")
        # Build actual URL from candidate (redacted in manifest)
        if not candidate.get("url"):
            # No actual URL to probe
            probe_results.append(
                {
                    "candidate_label": candidate["candidate_label"],
                    "probe_attempted": False,
                    "skip_reason": "no_url_available",
                    "status_code": None,
                    "content_type": None,
                    "response_size_bytes": 0,
                    "json_parse_ok": False,
                    "top_level_keys_sample": [],
                    "error_category": None,
                    "stop_policy_triggered": False,
                }
            )
            continue

        result = probe_route_candidate(candidate, args.timeout_seconds, args.sleep_seconds)
        probe_results.append(result)
        if result["stop_policy_triggered"]:
            stop_reason = str(result["error_category"])
            break

    manifest = build_manifest(
        args,
        db_env=db_env,
        guard_reasons=[],
        explicit=explicit,
        db_read=True,
        previous_manifest=previous_manifest,
        identity_analysis=identity_analysis,
        target_analysis=target_analysis,
        candidates=candidates,
        probe_results=probe_results,
        stop_reason=stop_reason,
        blocked=False,
    )
    write_artifacts(args, manifest)
    print(f"Route review status: {manifest['route_review']['route_review_status']}")
    print(f"Probes attempted: {manifest['request_budget']['used']}")
    print(f"JSON parse OK: {sum(1 for r in probe_results if r.get('json_parse_ok'))}")
    print(
        f"Embedded review: {manifest['embedded_review']['live_fetch_route_review_no_write_status']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
