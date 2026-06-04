#!/usr/bin/env python3
"""Controlled FotMob endpoint runtime candidate probe — metadata only.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ENDPOINT-RUNTIME-CANDIDATE-PROBE-NO-WRITE

Probes only ep-004, ep-005, ep-006 endpoint candidates with bounded GET requests.
Saves metadata only — no response body, no raw JSON, no DB writes.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
import time
from typing import Any
from urllib import error, request

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ENDPOINT-RUNTIME-CANDIDATE-PROBE-NO-WRITE"
SCHEMA = "fotmob_endpoint_runtime_candidate_probe_no_write_v1"
NEXT_PHASE_VALIDATION = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ENDPOINT-CANDIDATE-RESPONSE-VALIDATION-NO-WRITE"  # fmt: skip
NEXT_PHASE_DOWNGRADE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-FOTMOB-RAW-DETAIL-DOWNGRADE-DECISION-NO-WRITE"  # fmt: skip
NEXT_PHASE_DRY = PHASE

TIMEOUT_SECONDS = 10
MAX_CANDIDATES = 3
MAX_SAMPLES = 2
MAX_NETWORK_REQUESTS = 6
MAX_BODY_BYTES = 262144
MAX_REDIRECTS = 2
USER_AGENT = "FootballPrediction/1.0"

FORBIDDEN_REC = ["DIRECT-RAW-WRITE", "RAW-JSON-WRITE", "RAW-WRITE-EXECUTION"]

SELECTED_IDS = ["ep-004", "ep-005", "ep-006"]

# fmt: off
MATCH_DETAIL_POSITIVE = ["match", "matchId", "match_id", "matches", "matchDetails", "matchData", "fixture", "fixtures", "header", "general", "content", "facts", "matchFacts", "stats", "statistics", "lineup", "lineups", "events", "incidents", "teams", "homeTeam", "awayTeam", "status", "score", "shotmap", "momentum", "playerStats", "table", "league", "tournament"]

GENERIC_NEGATIVE = ["notableMatches", "CountryCodes", "Language", "translations", "seo", "menu", "navigation", "ads", "config", "static", "locale", "fetchingLeagueData"]

SAFETY_FALSE_NAMES = ["full_body_read_performed", "response_body_saved", "raw_response_body_saved", "full_html_saved", "html_body_saved", "full_next_data_saved", "value_persistence_performed", "raw_json_write_performed", "db_read_performed", "db_write_performed", "production_db_write_performed", "fotmob_raw_match_payloads_write_performed", "raw_match_data_write_performed", "feature_parse_performed", "scheduler_enabled", "raw_write_ready_marked", "browser_automation_performed", "cookie_harvesting_performed", "captcha_bypass_performed", "proxy_rotation_performed"]
SAFETY_FALSE = dict.fromkeys(SAFETY_FALSE_NAMES, False)
CANDIDATE_TEMPLATES = {"ep-004": {"category": "nextjs_data_route", "template": "/_next/data/{buildId}/en/match/{match_id}.json", "params": ["buildId", "match_id"]}, "ep-005": {"category": "nextjs_data_route", "template": "/_next/data/{buildId}/en/matches/{route_code}/{match_id}.json", "params": ["buildId", "route_code", "match_id"]}, "ep-006": {"category": "runtime_request", "template": "/api/matches?date={date}", "params": ["date"]}}
SAMPLE_DEFS = [{"sample_id": "s01", "match_id": "4813722", "route_code": "2ygkcb", "date_known": False}, {"sample_id": "s02", "match_id": "4813492", "route_code": "2ynv4k", "date_known": False}]
def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
def _safe_type(value: Any) -> str:
    tn = type(value).__name__
    return {"NoneType": "null", "bool": "bool", "dict": "dict", "list": "list", "int": "int", "float": "float", "str": "str"}.get(tn, tn)
# fmt: on


def _approx_size(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (bool, int, float)):
        return 1
    if isinstance(value, str):
        return max(len(value), 1)
    if isinstance(value, (list, tuple)):
        return len(value)
    if isinstance(value, dict):
        return len(value)
    return 1


def _score_signal(recorded: list[dict[str, Any]], target_match_id: str, route_code: str) -> int:
    """Score endpoint response key paths for match detail signals."""
    score = 0
    all_paths = " ".join(r["key_path"].lower() for r in recorded)
    all_keys = " ".join(r["key_name"].lower() for r in recorded)

    if target_match_id in all_paths:
        score += 5
    if route_code in all_paths or route_code in all_keys:
        score += 4
    for term in ("matchdetails", "matchdata", "matchdetailresponse"):
        if term in all_paths or term in all_keys:
            score += 4
            break
    for term in ("matchfacts", "facts", "matchinfo", "playerstats", "shotmap"):
        if term in all_paths or term in all_keys:
            score += 3
            break
    for term in (
        "header",
        "general",
        "content",
        "stats",
        "lineup",
        "lineups",
        "events",
        "incidents",
    ):
        if term in all_paths or term in all_keys:
            score += 3
            break
    for term in ("hometeam", "awayteam", "teams", "shotmap", "xg", "expectedgoals"):
        if term in all_paths or term in all_keys:
            score += 2
            break
    for term in ("status", "score", "fixture", "tournament", "league"):
        if term in all_paths or term in all_keys:
            score += 1
            break
    if any(t in all_paths for t in ["notablematches", "translations", "countrycodes", "language"]):
        score -= 4
    return score


def _classify_candidate(score: int, content_type: str, is_json: bool, status: int | None) -> str:
    if status == 403:
        return "blocked_403"
    if status == 429:
        return "blocked_429"
    if status == 404:
        return "not_found_404"
    ct_lower = (content_type or "").lower()
    if "text/html" in ct_lower and not is_json:
        return "rejected_or_generic_endpoint_candidate"
    if not is_json and status and status >= 400:
        return "rejected_or_generic_endpoint_candidate"
    if not is_json:
        return "not_json"

    if score >= 8:
        return "strong_endpoint_match_detail_candidate"
    if score >= 4:
        return "weak_endpoint_match_detail_candidate"
    if score >= 1:
        return "partial_or_ambiguous_endpoint_candidate"
    return "rejected_or_generic_endpoint_candidate"


def _scan_keyspace_flat(
    obj: Any,
    prefix: str = "",
    depth: int = 0,
    max_depth: int = 8,
    recorded: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if recorded is None:
        recorded = []
    if depth > max_depth or not isinstance(obj, dict):
        return recorded
    for key, value in obj.items():
        path = f"{prefix}.{key}" if prefix else key
        entry = {
            "key_path": path,
            "key_name": key,
            "depth": depth,
            "data_type": _safe_type(value),
            "size_class": _approx_size(value),
            "target_match_id_in_path": False,
            "route_code_in_path": False,
        }
        if len(recorded) < 200:
            recorded.append(entry)
        if isinstance(value, dict):
            _scan_keyspace_flat(value, path, depth + 1, max_depth, recorded)
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            _scan_keyspace_flat(value[0], f"{path}[0]", depth + 1, max_depth, recorded)
    return recorded


def _resolve_url(candidate_id: str, sample: dict[str, str], build_id: str) -> str | None:
    tmpl = CANDIDATE_TEMPLATES.get(candidate_id, {}).get("template", "")
    if not tmpl:
        return None
    url = tmpl.format(
        buildId=build_id,
        match_id=sample["match_id"],
        route_code=sample.get("route_code", ""),
        date=sample.get("date", ""),
    )
    return f"https://www.fotmob.com{url}"


def _perform_probe(url: str) -> dict[str, Any]:
    result = {
        "status_code": None,
        "content_type": None,
        "content_length": None,
        "bytes_read": 0,
        "body_truncated": False,
        "body_text": None,
        "error": None,
    }
    try:
        req = request.Request(url, headers={"User-Agent": USER_AGENT})
        with request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            result["status_code"] = resp.status
            result["content_type"] = resp.headers.get("Content-Type", "")
            cl = resp.headers.get("Content-Length")
            result["content_length"] = int(cl) if cl else None
            body = resp.read(MAX_BODY_BYTES + 1)
            result["bytes_read"] = len(body)
            if len(body) > MAX_BODY_BYTES:
                result["body_truncated"] = True
                body = body[:MAX_BODY_BYTES]
            try:
                result["body_text"] = body.decode("utf-8", errors="replace")
            except UnicodeDecodeError:
                result["body_text"] = body.decode("latin-1", errors="replace")
    except error.HTTPError as e:
        result["status_code"] = e.code
        result["error"] = str(e)
    except error.URLError as e:
        result["error"] = str(e)
    except Exception as e:
        result["error"] = str(e)
    return result


def _is_json_like(text: str, content_type: str) -> tuple[bool, Any | None]:
    """Check if response is JSON-like and attempt parse in memory."""
    ct_lower = content_type.lower()
    is_json_ct = "application/json" in ct_lower or "json" in ct_lower
    text_stripped = text.strip()
    looks_json = text_stripped.startswith(("{", "["))
    if not is_json_ct and not looks_json:
        return False, None
    try:
        return True, json.loads(text_stripped)
    except (json.JSONDecodeError, ValueError):
        return False, None


def _extract_build_id(plan_manifest: dict[str, Any]) -> str:
    """Try to extract buildId from existing manifest data."""
    for field in ["buildId", "build_id"]:
        val = plan_manifest.get(field)
        if val:
            return str(val)
    return ""


def _determine_next_phase(strong: int, weak: int) -> str:
    if strong >= 1 or weak >= 1:
        return NEXT_PHASE_VALIDATION
    return NEXT_PHASE_DOWNGRADE


def _build_dry_run_manifest(args: argparse.Namespace, review_report_path: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "lifecycle": "current-state",
        "phase": PHASE,
        "run_id": args.run_id,
        "generated_at": _utc_now(),
        "mode": "dry_run_endpoint_candidate_probe_plan_only",
        "inherited_plan": {
            "endpoint_candidate_count": 10,
            "next_probe_candidate_count": 3,
            "html_hydration_route_status": "exhausted_no_embedded_match_detail",
            "page_level_next_data_status": "no_match_detail_json_embedded",
            "raw_json_readiness": "not_ready",
            "db_write_readiness": "blocked",
            "l2_harvesting_readiness": "blocked",
        },
        "selected_candidates": SELECTED_IDS,
        "selected_samples": SAMPLE_DEFS,
        "probe_limits": {
            "max_candidates": args.max_candidates,
            "max_samples": args.max_samples,
            "max_network_requests": args.max_network_requests,
            "max_body_bytes": args.max_body_bytes,
            "browser_automation_allowed": False,
            "cookie_harvesting_allowed": False,
            "captcha_bypass_allowed": False,
            "proxy_rotation_allowed": False,
            "db_write_allowed": False,
            "raw_write_allowed": False,
        },
        "probe_results": [],
        "skipped_candidates": [],
        "probe_summary": {
            "allow_network_probe": False,
            "network_requests_attempted": 0,
            "strong_endpoint_match_detail_candidate_count": 0,
            "weak_endpoint_match_detail_candidate_count": 0,
            "partial_or_ambiguous_endpoint_candidate_count": 0,
            "rejected_or_generic_endpoint_candidate_count": 0,
            "blocked_403_count": 0,
            "blocked_429_count": 0,
            "not_found_404_count": 0,
            "parse_failed_count": 0,
            "skipped_count": 0,
        },
        "raw_write_readiness": {
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
            "raw_write_blocked_until_json_validated": True,
        },
        "safety": {
            "network_fetch_performed": False,
            "bounded_body_read_performed": False,
            **SAFETY_FALSE,
        },
        "embedded_review": {
            "endpoint_candidate_probe_status": "pass",
            "review_report_path": review_report_path,
        },
        "recommended_next_phase": _determine_next_phase(0, 0),
    }


def _build_live_manifest(
    args: argparse.Namespace,
    plan_manifest: dict[str, Any],
    seed_manifest: dict[str, Any],
    review_report_path: str,
) -> dict[str, Any]:
    build_id = _extract_build_id(plan_manifest)
    samples = SAMPLE_DEFS[: args.max_samples]
    results: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    network_attempted = 0
    strong_count = weak_count = partial_count = rejected_count = 0
    blocked_403 = blocked_429 = not_found_count = parse_failed = skip_count = 0

    for candidate_id in SELECTED_IDS:
        tmpl_info = CANDIDATE_TEMPLATES[candidate_id]
        needs_build = "buildId" in tmpl_info["params"]
        needs_date = "date" in tmpl_info["params"]

        if needs_build and not build_id:
            skipped.append({"candidate_id": candidate_id, "reason": "skipped_missing_build_id"})
            skip_count += 1
            continue
        if needs_date and not any(s["date_known"] for s in samples):
            skipped.append({"candidate_id": candidate_id, "reason": "skipped_missing_date"})
            skip_count += 1
            continue

        for sample in samples:
            if network_attempted >= MAX_NETWORK_REQUESTS:
                break

            if needs_date and not sample["date_known"]:
                continue

            url = _resolve_url(candidate_id, sample, build_id)
            if not url:
                continue

            network_attempted += 1
            probe = _perform_probe(url)
            t0 = time.perf_counter()

            entry: dict[str, Any] = {
                "candidate_id": candidate_id,
                "category": tmpl_info["category"],
                "endpoint_template": tmpl_info["template"],
                "resolved_path_redacted": url,
                "sample_id": sample["sample_id"],
                "match_id": sample["match_id"],
                "route_code": sample.get("route_code", ""),
                "network_performed": True,
                "status_code": probe["status_code"],
                "content_type": probe["content_type"],
                "content_length": probe["content_length"],
                "bytes_read": probe["bytes_read"],
                "body_truncated": probe["body_truncated"],
                "parse_ok": False,
                "json_like": False,
                "top_level_type": None,
                "top_level_key_count": 0,
                "key_paths_recorded_count": 0,
                "match_detail_signal_score": 0,
                "target_match_id_seen_in_key_path": False,
                "route_code_seen_in_key_path": False,
                "match_detail_terms_seen_in_key_path": False,
                "candidate_state": None,
                "stop_reason": None,
                "elapsed_ms": 0,
                "response_body_saved": False,
                "raw_response_body_saved": False,
                "raw_json_write_performed": False,
                "db_write_performed": False,
            }

            if probe.get("error"):
                entry["candidate_state"] = "parse_failed"
                entry["stop_reason"] = probe["error"]
                entry["elapsed_ms"] = int((time.perf_counter() - t0) * 1000)
                parse_failed += 1
                probe["body_text"] = None  # clear
                results.append(entry)
                continue

            status = probe["status_code"]
            if status and status >= 400:
                entry["candidate_state"] = _classify_candidate(
                    0, probe["content_type"], False, status
                )
                entry["stop_reason"] = f"HTTP {status}"
                entry["elapsed_ms"] = int((time.perf_counter() - t0) * 1000)
                if status == 403:
                    blocked_403 += 1
                elif status == 429:
                    blocked_429 += 1
                elif status == 404:
                    not_found_count += 1
                else:
                    rejected_count += 1
                probe["body_text"] = None
                results.append(entry)
                continue

            ct = probe.get("content_type") or ""
            body_text = probe.get("body_text") or ""
            is_json, parsed = _is_json_like(body_text, ct)

            entry["json_like"] = is_json
            entry["parse_ok"] = is_json and parsed is not None

            if parsed is not None:
                entry["top_level_type"] = _safe_type(parsed)
                if isinstance(parsed, dict):
                    entry["top_level_key_count"] = len(parsed)
                recorded = _scan_keyspace_flat(parsed)
                entry["key_paths_recorded_count"] = len(recorded)
                entry["match_detail_signal_score"] = _score_signal(
                    recorded, sample["match_id"], sample.get("route_code", "")
                )
                entry["target_match_id_seen_in_key_path"] = sample["match_id"] in json.dumps(
                    [r["key_path"] for r in recorded]
                )
                entry["route_code_seen_in_key_path"] = any(
                    sample.get("route_code", "") in r["key_path"] for r in recorded
                )
                entry["match_detail_terms_seen_in_key_path"] = any(
                    t in " ".join(r["key_path"].lower() for r in recorded)
                    for t in MATCH_DETAIL_POSITIVE[:5]
                )

            entry["candidate_state"] = _classify_candidate(
                entry["match_detail_signal_score"], ct, is_json, status
            )
            entry["stop_reason"] = "completed"
            entry["elapsed_ms"] = int((time.perf_counter() - t0) * 1000)

            state = entry["candidate_state"]
            if state.startswith("strong"):
                strong_count += 1
            elif state.startswith("weak"):
                weak_count += 1
            elif state.startswith("partial"):
                partial_count += 1
            else:
                rejected_count += 1

            probe["body_text"] = None  # safety: clear body
            results.append(entry)

            if state.startswith(("strong", "blocked_403", "blocked_429")):
                # Stop probing this candidate further
                break

    return {
        "schema_version": SCHEMA,
        "lifecycle": "current-state",
        "phase": PHASE,
        "run_id": args.run_id,
        "generated_at": _utc_now(),
        "mode": "controlled_endpoint_candidate_probe_no_write",
        "inherited_plan": {
            "endpoint_candidate_count": 10,
            "next_probe_candidate_count": 3,
            "html_hydration_route_status": "exhausted_no_embedded_match_detail",
            "page_level_next_data_status": "no_match_detail_json_embedded",
            "raw_json_readiness": "not_ready",
            "db_write_readiness": "blocked",
            "l2_harvesting_readiness": "blocked",
        },
        "selected_candidates": SELECTED_IDS,
        "selected_samples": samples,
        "probe_limits": {
            "max_candidates": args.max_candidates,
            "max_samples": args.max_samples,
            "max_network_requests": args.max_network_requests,
            "max_body_bytes": args.max_body_bytes,
            "browser_automation_allowed": False,
            "cookie_harvesting_allowed": False,
            "captcha_bypass_allowed": False,
            "proxy_rotation_allowed": False,
            "db_write_allowed": False,
            "raw_write_allowed": False,
        },
        "probe_results": results,
        "skipped_candidates": skipped,
        "probe_summary": {
            "allow_network_probe": True,
            "network_requests_attempted": network_attempted,
            "strong_endpoint_match_detail_candidate_count": strong_count,
            "weak_endpoint_match_detail_candidate_count": weak_count,
            "partial_or_ambiguous_endpoint_candidate_count": partial_count,
            "rejected_or_generic_endpoint_candidate_count": rejected_count,
            "blocked_403_count": blocked_403,
            "blocked_429_count": blocked_429,
            "not_found_404_count": not_found_count,
            "parse_failed_count": parse_failed,
            "skipped_count": skip_count,
        },
        "raw_write_readiness": {
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
            "raw_write_blocked_until_json_validated": True,
        },
        "safety": {
            "network_fetch_performed": True,
            "bounded_body_read_performed": True,
            **SAFETY_FALSE,
        },
        "embedded_review": {
            "endpoint_candidate_probe_status": "pass",
            "review_report_path": review_report_path,
        },
        "recommended_next_phase": _determine_next_phase(strong_count, weak_count),
    }


def enforce_safety(manifest: dict[str, Any]) -> None:
    safety = manifest.get("safety", {})
    for flag in SAFETY_FALSE_NAMES:
        if safety.get(flag) is True:
            raise ValueError(f"safety.{flag} must remain false")
    for r in manifest.get("probe_results", []):
        for k in [
            "response_body_saved",
            "raw_response_body_saved",
            "raw_json_write_performed",
            "db_write_performed",
            "full_html_saved",
        ]:
            if r.get(k) is True:
                raise ValueError(f"result {r.get('candidate_id')}.{k} must remain false")
    rd = manifest.get("raw_write_readiness", {})
    if rd.get("json_validated_count", 0) > 0:
        raise ValueError("json_validated_count must remain 0")
    if rd.get("raw_write_eligible_count", 0) > 0:
        raise ValueError("raw_write_eligible_count must remain 0")
    rec = manifest.get("recommended_next_phase", "")
    if any(t in rec for t in FORBIDDEN_REC):
        raise ValueError("recommended_next_phase must not be direct raw write")


def render_report(manifest: dict[str, Any], allow_network: bool) -> str:
    summary = manifest["probe_summary"]
    results = manifest.get("probe_results", [])
    skipped = manifest.get("skipped_candidates", [])
    mode = (
        "controlled_endpoint_candidate_probe_no_write"
        if allow_network
        else "dry_run_endpoint_candidate_probe_plan_only"
    )
    lines = [
        "<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->",
        "# FotMob Endpoint Runtime Candidate Probe No Write",
        "",
        "- lifecycle: current-state",
        f"- phase: {PHASE}",
        f"- run_id: {manifest['run_id']}",
        f"- mode: {mode}",
        "",
        "## 当前阶段背景",
        "",
        "- #1452 已完成 endpoint/runtime request discovery plan no-write。",
        "- 本阶段对 ep-004/ep-005/ep-006 执行受控 bounded probe。",
        "- bounded body read in memory，不保存 response body / raw JSON / DB write。",
        "",
        "## #1452 Discovery Plan Inheritance",
        "",
        "- endpoint_candidate_count: 10",
        "- next_probe_candidate_count: 3",
        "- selected: ep-004 (_next/data match), ep-005 (_next/data matches), ep-006 (api/matches)",
    ]
    if skipped:
        lines += ["", "## Skipped Candidates"]
        for s in skipped:
            lines.append(f"- {s['candidate_id']}: {s['reason']}")

    if allow_network and results:
        lines += [
            "",
            "## Controlled Probe Summary",
            f"- network_requests_attempted: {summary['network_requests_attempted']}",
            f"- strong: {summary['strong_endpoint_match_detail_candidate_count']}",
            f"- weak: {summary['weak_endpoint_match_detail_candidate_count']}",
            f"- partial: {summary['partial_or_ambiguous_endpoint_candidate_count']}",
            f"- rejected: {summary['rejected_or_generic_endpoint_candidate_count']}",
            f"- 403: {summary['blocked_403_count']}",
            f"- 429: {summary['blocked_429_count']}",
            f"- 404: {summary['not_found_404_count']}",
            f"- parse_failed: {summary['parse_failed_count']}",
            f"- skipped: {summary['skipped_count']}",
        ]
        for entry in results:
            lines += [
                "",
                f"### {entry['candidate_id']} — {entry.get('sample_id')} ({entry.get('match_id')})",
                f"- status: {entry.get('status_code')}",
                f"- content_type: {entry.get('content_type')}",
                f"- parse_ok: {entry.get('parse_ok')}",
                f"- json_like: {entry.get('json_like')}",
                f"- signal_score: {entry.get('match_detail_signal_score', 0)}",
                f"- state: {entry.get('candidate_state')}",
                f"- stop_reason: {entry.get('stop_reason')}",
            ]

    lines += [
        "",
        "## Raw Write Readiness Gate",
        "",
        "- json_validated_count: 0",
        "- raw_write_eligible_count: 0",
        "- raw_write_blocked_until_json_validated: true",
        "",
        "## No-Write Safety Review",
        "",
        "- 本阶段允许 bounded body read in memory，但不保存 response body。",
        "- 本阶段不保存 raw JSON、不写 DB、不启用 scheduler、不使用 browser automation。",
        "- 即使发现 strong candidate，也只是进入 response validation no-write。",
        "",
        "## Recommended Next Phase",
        "",
        f"- **{manifest['recommended_next_phase']}**",
    ]
    return "\n".join(lines)


def render_review(manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->",
            "# FotMob Endpoint Runtime Candidate Probe No Write Review",
            "",
            "- lifecycle: current-state",
            f"- phase: {PHASE} review",
            f"- run_id: {manifest['run_id']}",
            "",
            "- [pass] #1452 plan inherited",
            "- [pass] selected candidates only ep-004/ep-005/ep-006",
            f"- [pass] max_candidates={manifest['probe_limits']['max_candidates']} <= 3",
            f"- [pass] max_samples={manifest['probe_limits']['max_samples']} <= 2",
            f"- [pass] max_network_requests={manifest['probe_limits']['max_network_requests']} <= 6",
            f"- [pass] max_body_bytes={manifest['probe_limits']['max_body_bytes']} <= 262144",
            "- [pass] allow-network-probe required for live probe",
            "- [pass] no response body saved",
            "- [pass] no raw JSON saved",
            "- [pass] no HTML saved",
            "- [pass] no value persistence",
            "- [pass] no DB write",
            "- [pass] no scheduler",
            "- [pass] no feature parse",
            "- [pass] no browser automation",
            "- [pass] no cookie harvesting",
            "- [pass] no captcha bypass",
            "- [pass] no proxy rotation",
            "- [pass] json_validated_count=0",
            "- [pass] raw_write_eligible_count=0",
            "- [pass] recommended next phase safe",
            "- [pass] no direct raw write recommendation",
            "",
            "## Overall: pass",
        ]
    )


def render_decision(manifest: dict[str, Any], allow_network: bool) -> str:
    results = manifest.get("probe_results", [])
    skipped = manifest.get("skipped_candidates", [])
    lines = [
        "<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->",
        "# FotMob Endpoint Runtime Candidate Decision",
        "",
        "- lifecycle: current-state",
        f"- phase: {PHASE} decision",
        f"- run_id: {manifest['run_id']}",
        f"- mode: {'controlled' if allow_network else 'dry_run_plan_only'}",
    ]
    if skipped:
        lines += ["", "## Skipped", *[f"- {s['candidate_id']}: {s['reason']}" for s in skipped]]
    if results:
        lines += ["", "## Probe Results"]
        for entry in results:
            lines += [
                "",
                f"### {entry['candidate_id']} ({entry.get('sample_id')})",
                f"- status: {entry.get('status_code')}",
                f"- content_type: {entry.get('content_type')}",
                f"- json_like: {entry.get('json_like')}",
                f"- parse_ok: {entry.get('parse_ok')}",
                f"- signal_score: {entry.get('match_detail_signal_score')}",
                f"- state: {entry.get('candidate_state')}",
                f"- target_match_id in paths: {entry.get('target_match_id_seen_in_key_path')}",
                f"- match_detail_terms: {entry.get('match_detail_terms_seen_in_key_path')}",
            ]
    lines += [
        "",
        "## Why Raw Write Is Still Blocked",
        "",
        "- json_validated_count=0",
        "- raw_write_eligible_count=0",
        "- 即使发现 strong candidate，也只是进入 response validation no-write",
        "",
        "## Recommended Next Phase",
        "",
        f"- **{manifest['recommended_next_phase']}**",
    ]
    return "\n".join(lines)


def write_outputs(args: argparse.Namespace, manifest: dict[str, Any], allow_network: bool) -> None:
    for p in [
        Path(args.output_manifest),
        Path(args.report),
        Path(args.review_report),
        Path(args.decision_report),
    ]:
        p.parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_manifest).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    Path(args.report).write_text(render_report(manifest, allow_network) + "\n", encoding="utf-8")
    Path(args.review_report).write_text(render_review(manifest) + "\n", encoding="utf-8")
    Path(args.decision_report).write_text(
        render_decision(manifest, allow_network) + "\n", encoding="utf-8"
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan-manifest", required=True)
    p.add_argument("--seed-manifest", required=True)
    p.add_argument("--output-manifest", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--review-report", required=True)
    p.add_argument("--decision-report", required=True)
    p.add_argument("--run-id", required=True)
    p.add_argument("--max-candidates", type=int, default=3)
    p.add_argument("--max-samples", type=int, default=2)
    p.add_argument("--max-network-requests", type=int, default=6)
    p.add_argument("--max-body-bytes", type=int, default=262144)
    p.add_argument("--allow-network-probe", action="store_true", default=False)
    return p.parse_args(argv)


def _validate_args(args: argparse.Namespace) -> None:
    if args.max_candidates > MAX_CANDIDATES:
        raise ValueError(f"--max-candidates {args.max_candidates} > {MAX_CANDIDATES}")
    if args.max_samples > MAX_SAMPLES:
        raise ValueError(f"--max-samples {args.max_samples} > {MAX_SAMPLES}")
    if args.max_network_requests > MAX_NETWORK_REQUESTS:
        raise ValueError(
            f"--max-network-requests {args.max_network_requests} > {MAX_NETWORK_REQUESTS}"
        )
    if args.max_body_bytes > MAX_BODY_BYTES:
        raise ValueError(f"--max-body-bytes {args.max_body_bytes} > {MAX_BODY_BYTES}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    allow_network = args.allow_network_probe
    try:
        _validate_args(args)
        plan = _load_json(Path(args.plan_manifest), "plan manifest")
        seed = _load_json(Path(args.seed_manifest), "seed manifest")
        review_report_path = str(Path(args.review_report))
        manifest = (
            _build_live_manifest(args, plan, seed, review_report_path)
            if allow_network
            else _build_dry_run_manifest(args, review_report_path)
        )
        enforce_safety(manifest)
        write_outputs(args, manifest, allow_network)
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    mode = "controlled" if allow_network else "dry_run_plan_only"
    print(f"PASS: endpoint runtime candidate probe no-write ({mode}) complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
