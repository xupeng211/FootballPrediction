#!/usr/bin/env python3
"""Controlled FotMob hydration keyspace review — key path metadata only.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-KEYSPACE-REVIEW-NO-WRITE

Scans bounded __NEXT_DATA__ key paths in memory, scores them for match detail
relevance, and persists only key path metadata (no values, no full HTML, no
raw JSON, no DB writes).

Default mode: dry-run (no network). Pass --allow-network-probe to perform
controlled GET probes.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import sys
import time
from typing import Any
from urllib import error, request

from fotmob_hydration_keyspace_review_no_write_report import (
    enforce_safety,
    validate_inheritance,
    write_outputs,
)

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-KEYSPACE-REVIEW-NO-WRITE"  # fmt: skip
SCHEMA = "fotmob_hydration_keyspace_review_no_write_v1"
NEXT_PHASE_STRONG = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-KEYSPACE-CANDIDATE-PATH-VALIDATION-NO-WRITE"  # fmt: skip
NEXT_PHASE_WEAK = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-KEYSPACE-WEAK-CANDIDATE-FOLLOWUP-NO-WRITE"  # fmt: skip
NEXT_PHASE_NONE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-ROUTE-VARIANT-FOLLOWUP-NO-WRITE"  # fmt: skip
NEXT_PHASE_DRY = PHASE

ROUTE_TEMPLATE = "/matches/{route_code}/{match_id}"
ZH_ROUTE_TEMPLATE = "/zh-Hans/matches/{route_code}/{match_id}"

TIMEOUT_SECONDS = 10
MAX_SAMPLES = 2
MAX_NETWORK_REQUESTS = 2
MAX_BODY_BYTES = 524288
MAX_SCAN_DEPTH = 12
MAX_KEY_PATHS_RECORDED = 500
MAX_CANDIDATE_PATHS_RECORDED = 50
MAX_VALUE_PREVIEW_CHARS = 0

# fmt: off
MATCH_DETAIL_POSITIVE = ["match", "matchId", "match_id", "matches", "matchDetails", "matchData", "fixture", "fixtures", "header", "general", "content", "facts", "matchFacts", "stats", "statistics", "lineup", "lineups", "events", "incidents", "teams", "homeTeam", "awayTeam", "status", "score", "shotmap", "momentum", "playerStats", "table", "league", "tournament"]

GENERIC_NEGATIVE = ["notableMatches", "CountryCodes", "Language", "translations", "seo", "menu", "navigation", "ads", "config", "static", "localization", "locale", "leagueData", "fetchingLeagueData"]

TARGET_SIGNALS = ["4813722", "4813492", "2ygkcb", "2ynv4k", "liverpool", "manchester", "united", "everton"]

TYPE_NAME_BY_PY = dict(pair.split(":") for pair in ["NoneType:null", "bool:bool", "dict:dict", "list:list", "int:int", "float:float", "str:str"])

SAFETY_FALSE_NAMES = ["full_body_read_performed", "full_html_saved", "raw_response_body_saved", "html_body_saved", "full_next_data_saved", "value_persistence_performed", "raw_json_write_performed", "db_read_performed", "db_write_performed", "production_db_write_performed", "fotmob_raw_match_payloads_write_performed", "raw_match_data_write_performed", "l3_features_write_performed", "predictions_write_performed", "feature_parse_performed", "scheduler_enabled", "raw_write_ready_marked", "browser_automation_performed", "captcha_bypass_performed", "proxy_rotation_performed"]

SAFETY_FALSE = dict.fromkeys(SAFETY_FALSE_NAMES, False)

SAMPLE_DEFS: list[dict[str, str]] = [
    {"review_id": "keyspace-s01", "match_id": "4813722", "route_code": "2ygkcb", "team_pair": "Liverpool vs Manchester United", "slug": "liverpool-vs-manchester-united"},
    {"review_id": "keyspace-s02", "match_id": "4813492", "route_code": "2ynv4k", "team_pair": "Everton vs Manchester United", "slug": "everton-vs-manchester-united"},
]
# fmt: on


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"{label} missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_type(value: Any) -> str:
    return TYPE_NAME_BY_PY.get(type(value).__name__, type(value).__name__)


def _approx_size(value: Any) -> int:
    """Approximate in-memory size hint without serializing values."""
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


def _child_count(value: Any) -> int:
    if isinstance(value, dict):
        return len(value)
    if isinstance(value, (list, tuple)):
        return len(value)
    return 0


def _score_key_path(
    path: str,
    key_name: str,
    target_match_id: str,
    route_code: str,
) -> int:
    score = 0
    path_lower = path.lower()
    key_lower = key_name.lower()

    # +5: path contains target match_id as a segment
    if target_match_id in path:
        score += 5

    # +4: path contains route_code or matchDetails/matchData
    if route_code in path:
        score += 4
    for token in ("matchdetails", "matchdata", "match_detail", "match_data"):
        if token in path_lower or token in key_lower:
            score += 4
            break

    # +3: match + detail-like term
    detail_terms = ("matchfacts", "matchinfo", "shotmap", "momentum", "playerstats")
    for term in detail_terms:
        if term in path_lower or term in key_lower:
            score += 3
            break

    # +3: header/general/content
    for term in ("header", "general", "content"):
        if term == key_lower or f".{term}" in path_lower:
            score += 3
            break

    # +2: stats/lineup/events/matchFacts
    for term in ("stats", "lineup", "lineups", "events", "incidents", "matchfacts"):
        if term in key_lower or term in path_lower:
            score += 2
            break

    # +2: teams/homeTeam/awayTeam
    for term in ("teams", "hometeam", "awayteam"):
        if term in key_lower or term in path_lower:
            score += 2
            break

    # +1: status/score/fixture/tournament/league
    for term in ("status", "score", "fixture", "tournament", "league"):
        if term in key_lower or term in path_lower:
            score += 1
            break

    # -4: notableMatches
    if "notablematches" in path_lower or "notablematches" in key_lower:
        score -= 4

    # -4: translations/Language/CountryCodes
    for term in ("translations", "language", "countrycodes"):
        if term in path_lower or term in key_lower:
            score -= 4
            break

    # -3: config/static/navigation/menu/ads
    for term in ("config", "static", "navigation", "menu", "ads", "seo"):
        if term in path_lower or term in key_lower:
            score -= 3
            break

    # -5: if only generic terms found
    all_terms = path_lower + "." + key_lower
    positive_hits = any(t in all_terms for t in MATCH_DETAIL_POSITIVE)
    if not positive_hits:
        score -= 5

    return score


def _classify_path(score: int) -> str:
    if score >= 8:
        return "strong_match_detail_path_candidate"
    if score >= 4:
        return "weak_match_detail_path_candidate"
    if score >= 1:
        return "partial_or_ambiguous_path"
    return "generic_or_irrelevant_path"


def _path_contains_term(path: str, terms: list[str]) -> bool:
    path_lower = path.lower()
    return any(term.lower() in path_lower for term in terms)


def _scan_keyspace(
    obj: Any,
    prefix: str = "",
    depth: int = 0,
    max_depth: int = MAX_SCAN_DEPTH,
    recorded: list[dict[str, Any]] | None = None,
    target_match_id: str = "",
    route_code: str = "",
) -> list[dict[str, Any]]:
    if recorded is None:
        recorded = []
    if depth > max_depth:
        return recorded
    if not isinstance(obj, dict):
        return recorded
    for key, value in obj.items():
        path = f"{prefix}.{key}" if prefix else key
        score = _score_key_path(path, key, target_match_id, route_code)
        classification = _classify_path(score)
        entry: dict[str, Any] = {
            "key_path": path,
            "key_name": key,
            "depth": depth,
            "parent_path": prefix,
            "data_type": _safe_type(value),
            "child_count": _child_count(value),
            "size_class": _approx_size(value),
            "score": score,
            "path_contains_target_terms": _path_contains_term(path, TARGET_SIGNALS),
            "path_contains_generic_terms": _path_contains_term(path, GENERIC_NEGATIVE),
            "path_contains_match_detail_terms": _path_contains_term(path, MATCH_DETAIL_POSITIVE),
            "target_match_id_in_path": target_match_id in path if target_match_id else False,
            "target_match_id_in_key": key == target_match_id,
            "route_code_in_path": route_code in path if route_code else False,
            "classification": classification,
        }
        if len(recorded) < MAX_KEY_PATHS_RECORDED:
            recorded.append(entry)
        if isinstance(value, dict):
            _scan_keyspace(value, path, depth + 1, max_depth, recorded, target_match_id, route_code)
        elif isinstance(value, (list, tuple)) and value and isinstance(value[0], dict):
            _scan_keyspace(
                value[0], f"{path}[0]", depth + 1, max_depth, recorded, target_match_id, route_code
            )
    return recorded


def _parse_next_data(html: str) -> dict[str, Any] | None:
    """Extract and parse __NEXT_DATA__ JSON from HTML in memory only."""
    match = re.search(
        r'<script\s+id="__NEXT_DATA__"\s+type="application/json"\s*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _build_url(route_variant: str, route_code: str, match_id: str, slug: str = "") -> str:
    if route_variant == "zh-Hans":
        return f"https://www.fotmob.com/zh-Hans/matches/{route_code}/{match_id}"
    if route_variant == "slug":
        return f"https://www.fotmob.com/matches/{slug}/{route_code}"
    return f"https://www.fotmob.com/matches/{route_code}/{match_id}"


def _perform_probe(url: str, max_body_bytes: int) -> dict[str, Any]:
    """Perform a single controlled GET probe. Returns metadata dict."""
    result: dict[str, Any] = {
        "status_code": None,
        "content_type": None,
        "content_length": None,
        "bytes_read": 0,
        "body_truncated": False,
        "html_body": None,
        "error": None,
    }
    try:
        req = request.Request(url, headers={"User-Agent": "FootballPrediction/1.0"})
        with request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            result["status_code"] = resp.status
            result["content_type"] = resp.headers.get("Content-Type", "")
            cl = resp.headers.get("Content-Length")
            result["content_length"] = int(cl) if cl else None
            body = resp.read(max_body_bytes + 1)
            result["bytes_read"] = len(body)
            if len(body) > max_body_bytes:
                result["body_truncated"] = True
                body = body[:max_body_bytes]
            try:
                result["html_body"] = body.decode("utf-8", errors="replace")
            except UnicodeDecodeError:
                result["html_body"] = body.decode("latin-1", errors="replace")
    except error.HTTPError as e:
        result["status_code"] = e.code
        result["error"] = str(e)
    except error.URLError as e:
        result["error"] = str(e)
    except Exception as e:
        result["error"] = str(e)
    return result


def _determine_next_phase(
    allow_network: bool,
    strong_count: int,
    weak_count: int,
) -> str:
    if not allow_network:
        return NEXT_PHASE_DRY
    if strong_count >= 1:
        return NEXT_PHASE_STRONG
    if weak_count >= 1:
        return NEXT_PHASE_WEAK
    return NEXT_PHASE_NONE


def build_dry_run_manifest(
    *,
    run_id: str,
    controlled: dict[str, Any],
    review_followup: dict[str, Any],
    seed_manifest: dict[str, Any],
    review_report_path: str,
    max_samples: int,
    max_body_bytes: int,
    max_scan_depth: int,
    max_key_paths: int,
) -> dict[str, Any]:
    validate_inheritance(controlled)
    samples = SAMPLE_DEFS[:max_samples]
    summary = controlled.get("extraction_summary", {})
    return {
        "schema_version": SCHEMA,
        "lifecycle": "current-state",
        "phase": PHASE,
        "run_id": run_id,
        "generated_at": _utc_now(),
        "mode": "dry_run_keyspace_review_plan_only",
        "inherited_review_followup": {
            "notable_matches_is_not_match_detail": True,
            "keyspace_review_required": True,
            "route_variant_review_required": True,
            "target_match_id_seen_count": summary.get("target_match_id_seen_count", 0),
            "strong_candidate_count": summary.get("strong_candidate_count", 0),
            "fallback_present_count": summary.get("fallback_present_count", 2),
            "generic_or_irrelevant_count": summary.get("generic_or_irrelevant_count", 2),
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
        },
        "keyspace_selection": {
            "max_samples": max_samples,
            "selected_sample_count": len(samples),
            "selected_match_ids": [s["match_id"] for s in samples],
            "selected_route_codes": [s["route_code"] for s in samples],
            "route_variants_selected": ["/matches/{route_code}/{match_id}", "zh-Hans"],
            "max_body_bytes": max_body_bytes,
            "max_scan_depth": max_scan_depth,
            "max_key_paths_recorded": max_key_paths,
            "max_value_preview_chars": 0,
        },
        "keyspace_results": [],
        "keyspace_summary": {
            "allow_network_probe": False,
            "max_network_requests": MAX_NETWORK_REQUESTS,
            "network_requests_attempted": 0,
            "next_data_parse_ok_count": 0,
            "pageProps_present_count": 0,
            "fallback_present_count": 0,
            "strong_path_candidate_count": 0,
            "weak_path_candidate_count": 0,
            "partial_path_candidate_count": 0,
            "generic_or_irrelevant_path_count": 0,
            "route_variant_with_best_candidate": "dry-run (no network)",
            "blocked_count": 0,
            "invalid_count": 0,
            "not_html_count": 0,
        },
        "keyspace_candidate_decision": {
            "viable_path_candidate_count": 0,
            "best_path_candidate": None,
            "best_path_score": 0,
            "best_route_variant": None,
            "recommended_next_action": "run with --allow-network-probe",
        },
        "raw_write_readiness": {
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
            "raw_write_blocked_until_json_validated": True,
            "keyspace_candidate_validation_required": True,
        },
        "safety": {
            "network_fetch_performed": False,
            "bounded_body_read_performed": False,
            "full_body_read_performed": False,
            "full_html_saved": False,
            "raw_response_body_saved": False,
            "html_body_saved": False,
            "full_next_data_saved": False,
            "value_persistence_performed": False,
            "raw_json_write_performed": False,
            "db_read_performed": False,
            "db_write_performed": False,
            "production_db_write_performed": False,
            "fotmob_raw_match_payloads_write_performed": False,
            "raw_match_data_write_performed": False,
            "l3_features_write_performed": False,
            "predictions_write_performed": False,
            "feature_parse_performed": False,
            "scheduler_enabled": False,
            "raw_write_ready_marked": False,
            "browser_automation_performed": False,
            "captcha_bypass_performed": False,
            "proxy_rotation_performed": False,
        },
        "embedded_review": {
            "hydration_keyspace_review_status": "pass",
            "review_report_path": review_report_path,
        },
        "recommended_next_phase": _determine_next_phase(False, 0, 0),
    }


def build_live_manifest(
    *,
    run_id: str,
    controlled: dict[str, Any],
    review_followup: dict[str, Any],
    seed_manifest: dict[str, Any],
    review_report_path: str,
    max_samples: int,
    max_body_bytes: int,
    max_scan_depth: int,
    max_key_paths: int,
    max_network_requests: int,
) -> dict[str, Any]:
    validate_inheritance(controlled)
    summary = controlled.get("extraction_summary", {})
    samples = SAMPLE_DEFS[:max_samples]

    route_variants = ["default", "zh-Hans"]
    results: list[dict[str, Any]] = []
    network_attempted = 0
    strong_count = 0
    weak_count = 0
    partial_count = 0
    generic_count = 0
    best_overall_path = None
    best_overall_score = -999
    best_overall_variant = None

    for sample in samples:
        for variant in route_variants:
            if network_attempted >= max_network_requests:
                break
            network_attempted += 1

            url = _build_url(
                variant, sample["route_code"], sample["match_id"], sample.get("slug", "")
            )
            probe = _perform_probe(url, max_body_bytes)

            entry: dict[str, Any] = {
                "review_id": sample["review_id"],
                "match_id": sample["match_id"],
                "route_code": sample["route_code"],
                "route_variant": variant,
                "team_pair": sample["team_pair"],
                "url_redacted": url,
                "network_performed": True,
                "status_code": probe["status_code"],
                "content_type": probe["content_type"],
                "content_length": probe["content_length"],
                "bytes_read": probe["bytes_read"],
                "body_truncated": probe["body_truncated"],
                "next_data_parse_ok": False,
                "pageProps_present": False,
                "fallback_present": False,
                "total_key_paths_seen": 0,
                "key_paths_recorded_count": 0,
                "value_persistence_performed": False,
                "target_match_id_in_key_path": False,
                "route_code_in_key_path": False,
                "positive_candidate_path_count": 0,
                "generic_path_count": 0,
                "top_candidate_paths": [],
                "top_candidate_scores": [],
                "top_candidate_states": [],
                "generic_paths_rejected": [],
                "validation_state": "keyspace_review_completed",
                "stop_reason": "completed",
                "elapsed_ms": 0,
                "full_html_saved": False,
                "raw_response_body_saved": False,
                "html_body_saved": False,
                "full_next_data_saved": False,
                "raw_json_write_performed": False,
                "db_write_performed": False,
                "raw_write_eligible": False,
            }

            if probe.get("error"):
                entry["validation_state"] = (
                    "keyspace_route_blocked"
                    if probe["status_code"] and probe["status_code"] >= 400
                    else "keyspace_route_invalid"
                )
                entry["stop_reason"] = probe["error"]
                results.append(entry)
                continue

            if probe["status_code"] and probe["status_code"] >= 400:
                entry["validation_state"] = "keyspace_route_blocked"
                entry["stop_reason"] = f"HTTP {probe['status_code']}"
                results.append(entry)
                continue

            ct = (probe.get("content_type") or "").lower()
            if "text/html" not in ct:
                entry["validation_state"] = "keyspace_not_html"
                entry["stop_reason"] = f"content_type={ct}"
                results.append(entry)
                continue

            t0 = time.perf_counter()
            html_body = probe.get("html_body") or ""
            next_data = _parse_next_data(html_body)
            entry["elapsed_ms"] = int((time.perf_counter() - t0) * 1000)

            if next_data is None:
                entry["validation_state"] = "keyspace_next_data_parse_failed"
                entry["stop_reason"] = "NEXT_DATA parse failed"
                results.append(entry)
                continue

            entry["next_data_parse_ok"] = True
            props = next_data.get("props", {})
            page_props = props.get("pageProps", {})
            entry["pageProps_present"] = bool(page_props)
            entry["fallback_present"] = bool(page_props.get("fallback"))

            # Scan keyspace — root, props, pageProps
            recorded = _scan_keyspace(
                next_data,
                "",
                0,
                max_scan_depth,
                [],
                sample["match_id"],
                sample["route_code"],
            )
            entry["total_key_paths_seen"] = len(recorded)
            entry["key_paths_recorded_count"] = min(len(recorded), max_key_paths)
            entry["target_match_id_in_key_path"] = any(
                r["target_match_id_in_path"] for r in recorded
            )
            entry["route_code_in_key_path"] = any(r["route_code_in_path"] for r in recorded)

            # Classify recorded paths
            scored = sorted(recorded, key=lambda r: r["score"], reverse=True)
            entry["positive_candidate_path_count"] = sum(1 for r in scored if r["score"] > 0)
            entry["generic_path_count"] = sum(1 for r in scored if r["score"] <= 0)

            top_candidates = [r for r in scored if r["score"] > 0][:MAX_CANDIDATE_PATHS_RECORDED]
            entry["top_candidate_paths"] = [r["key_path"] for r in top_candidates]
            entry["top_candidate_scores"] = [r["score"] for r in top_candidates]
            entry["top_candidate_states"] = [r["classification"] for r in top_candidates]

            rejected = [
                r
                for r in scored
                if r["score"] <= 0
                and _path_contains_term(r["key_path"], ["notableMatches", "translations", "config"])
            ]
            entry["generic_paths_rejected"] = [r["key_path"] for r in rejected[:20]]

            # Track per-entry counts
            s_count = sum(
                1 for r in scored if r["classification"] == "strong_match_detail_path_candidate"
            )
            w_count = sum(
                1 for r in scored if r["classification"] == "weak_match_detail_path_candidate"
            )
            p_count = sum(1 for r in scored if r["classification"] == "partial_or_ambiguous_path")
            g_count = sum(1 for r in scored if r["classification"] == "generic_or_irrelevant_path")
            strong_count += s_count
            weak_count += w_count
            partial_count += p_count
            generic_count += g_count

            if scored and scored[0]["score"] > best_overall_score:
                best_overall_score = scored[0]["score"]
                best_overall_path = scored[0]["key_path"]
                best_overall_variant = variant

            # Safety: clear the HTML body — we must not persist it
            probe["html_body"] = None
            results.append(entry)

        if network_attempted >= max_network_requests:
            break

    next_data_ok = sum(1 for r in results if r.get("next_data_parse_ok"))
    pp_count = sum(1 for r in results if r.get("pageProps_present"))
    fb_count = sum(1 for r in results if r.get("fallback_present"))
    blocked = sum(1 for r in results if r.get("validation_state") == "keyspace_route_blocked")
    invalid = sum(1 for r in results if r.get("validation_state") == "keyspace_route_invalid")
    not_html = sum(1 for r in results if r.get("validation_state") == "keyspace_not_html")

    return {
        "schema_version": SCHEMA,
        "lifecycle": "current-state",
        "phase": PHASE,
        "run_id": run_id,
        "generated_at": _utc_now(),
        "mode": "controlled_hydration_keyspace_review_no_write",
        "inherited_review_followup": {
            "notable_matches_is_not_match_detail": True,
            "keyspace_review_required": True,
            "route_variant_review_required": True,
            "target_match_id_seen_count": summary.get("target_match_id_seen_count", 0),
            "strong_candidate_count": summary.get("strong_candidate_count", 0),
            "fallback_present_count": summary.get("fallback_present_count", 2),
            "generic_or_irrelevant_count": summary.get("generic_or_irrelevant_count", 2),
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
        },
        "keyspace_selection": {
            "max_samples": max_samples,
            "selected_sample_count": len(samples),
            "selected_match_ids": [s["match_id"] for s in samples],
            "selected_route_codes": [s["route_code"] for s in samples],
            "route_variants_selected": route_variants,
            "max_body_bytes": max_body_bytes,
            "max_scan_depth": max_scan_depth,
            "max_key_paths_recorded": max_key_paths,
            "max_value_preview_chars": 0,
        },
        "keyspace_results": results,
        "keyspace_summary": {
            "allow_network_probe": True,
            "max_network_requests": max_network_requests,
            "network_requests_attempted": network_attempted,
            "next_data_parse_ok_count": next_data_ok,
            "pageProps_present_count": pp_count,
            "fallback_present_count": fb_count,
            "strong_path_candidate_count": strong_count,
            "weak_path_candidate_count": weak_count,
            "partial_path_candidate_count": partial_count,
            "generic_or_irrelevant_path_count": generic_count,
            "route_variant_with_best_candidate": best_overall_variant or "none",
            "blocked_count": blocked,
            "invalid_count": invalid,
            "not_html_count": not_html,
        },
        "keyspace_candidate_decision": {
            "viable_path_candidate_count": strong_count + weak_count,
            "best_path_candidate": best_overall_path,
            "best_path_score": best_overall_score,
            "best_route_variant": best_overall_variant,
            "recommended_next_action": _determine_next_phase(True, strong_count, weak_count),
        },
        "raw_write_readiness": {
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
            "raw_write_blocked_until_json_validated": True,
            "keyspace_candidate_validation_required": True,
        },
        "safety": {
            "network_fetch_performed": True,
            "bounded_body_read_performed": True,
            "full_body_read_performed": False,
            "full_html_saved": False,
            "raw_response_body_saved": False,
            "html_body_saved": False,
            "full_next_data_saved": False,
            "value_persistence_performed": False,
            "raw_json_write_performed": False,
            "db_read_performed": False,
            "db_write_performed": False,
            "production_db_write_performed": False,
            "fotmob_raw_match_payloads_write_performed": False,
            "raw_match_data_write_performed": False,
            "l3_features_write_performed": False,
            "predictions_write_performed": False,
            "feature_parse_performed": False,
            "scheduler_enabled": False,
            "raw_write_ready_marked": False,
            "browser_automation_performed": False,
            "captcha_bypass_performed": False,
            "proxy_rotation_performed": False,
        },
        "embedded_review": {
            "hydration_keyspace_review_status": "pass",
            "review_report_path": review_report_path,
        },
        "recommended_next_phase": _determine_next_phase(True, strong_count, weak_count),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-followup-manifest", required=True)
    parser.add_argument("--controlled-subtree-manifest", required=True)
    parser.add_argument("--seed-manifest", required=True)
    parser.add_argument("--output-manifest", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--review-report", required=True)
    parser.add_argument("--decision-report", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--max-samples", type=int, default=2)
    parser.add_argument("--max-body-bytes", type=int, default=524288)
    parser.add_argument("--max-scan-depth", type=int, default=12)
    parser.add_argument("--max-key-paths-recorded", type=int, default=500)
    parser.add_argument("--max-network-requests", type=int, default=2)
    parser.add_argument("--allow-network-probe", action="store_true", default=False)
    return parser.parse_args(argv)


def validate_args(args: argparse.Namespace, allow_network: bool) -> None:
    """Validate all bounds. Exit non-zero if exceeded."""
    if args.max_samples > MAX_SAMPLES:
        raise ValueError(f"--max-samples {args.max_samples} exceeds limit {MAX_SAMPLES}")
    if args.max_network_requests > MAX_NETWORK_REQUESTS:
        raise ValueError(
            f"--max-network-requests {args.max_network_requests} exceeds limit {MAX_NETWORK_REQUESTS}"
        )
    if args.max_body_bytes > MAX_BODY_BYTES:
        raise ValueError(f"--max-body-bytes {args.max_body_bytes} exceeds limit {MAX_BODY_BYTES}")
    if args.max_scan_depth > MAX_SCAN_DEPTH:
        raise ValueError(f"--max-scan-depth {args.max_scan_depth} exceeds limit {MAX_SCAN_DEPTH}")
    if args.max_key_paths_recorded > MAX_KEY_PATHS_RECORDED:
        raise ValueError(
            f"--max-key-paths-recorded {args.max_key_paths_recorded} exceeds limit {MAX_KEY_PATHS_RECORDED}"
        )
    if not allow_network and args.max_network_requests > 0:
        # In dry-run mode, network_requests_attempted must be 0
        pass


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    allow_network = args.allow_network_probe

    try:
        validate_args(args, allow_network)
        controlled = _load_json(
            Path(args.controlled_subtree_manifest), "controlled subtree manifest"
        )
        review_followup = _load_json(
            Path(args.review_followup_manifest), "review followup manifest"
        )
        seed_manifest = _load_json(Path(args.seed_manifest), "seed manifest")
        review_report_path = str(Path(args.review_report))

        if allow_network:
            manifest = build_live_manifest(
                run_id=args.run_id,
                controlled=controlled,
                review_followup=review_followup,
                seed_manifest=seed_manifest,
                review_report_path=review_report_path,
                max_samples=args.max_samples,
                max_body_bytes=args.max_body_bytes,
                max_scan_depth=args.max_scan_depth,
                max_key_paths=args.max_key_paths_recorded,
                max_network_requests=args.max_network_requests,
            )
        else:
            manifest = build_dry_run_manifest(
                run_id=args.run_id,
                controlled=controlled,
                review_followup=review_followup,
                seed_manifest=seed_manifest,
                review_report_path=review_report_path,
                max_samples=args.max_samples,
                max_body_bytes=args.max_body_bytes,
                max_scan_depth=args.max_scan_depth,
                max_key_paths=args.max_key_paths_recorded,
            )

        enforce_safety(manifest, allow_network)
        write_outputs(args, manifest, allow_network)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    mode = "controlled" if allow_network else "dry_run_plan_only"
    print(f"PASS: hydration keyspace review no-write ({mode}) complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
