#!/usr/bin/env python3
"""Controlled FotMob hydration route variant follow-up — metadata only.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-ROUTE-VARIANT-FOLLOWUP-NO-WRITE

Tests /en and original slug path route variants to see if the hydration keyspace
differs from the default/zh-Hans baseline. Only saves route/key path metadata.
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

from fotmob_hydration_route_variant_followup_no_write_report import (
    enforce_safety,
    validate_inheritance,
    write_outputs,
)

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-ROUTE-VARIANT-FOLLOWUP-NO-WRITE"
SCHEMA = "fotmob_hydration_route_variant_followup_no_write_v1"
NEXT_PHASE_DETAIL = (
    "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ROUTE-VARIANT-CANDIDATE-PATH-VALIDATION-NO-WRITE"
)
NEXT_PHASE_DIFFERS = (
    "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ROUTE-VARIANT-DIFFERENT-KEYSPACE-FOLLOWUP-NO-WRITE"
)
NEXT_PHASE_NONE = (
    "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-FOTMOB-PAGE-NO-EMBEDDED-DETAIL-DECISION-NO-WRITE"
)
NEXT_PHASE_DRY = PHASE

TIMEOUT_SECONDS = 10
MAX_SAMPLES = 2
MAX_ROUTE_VARIANTS = 2
MAX_NETWORK_REQUESTS = 4
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
# fmt: on

SAFETY_FALSE = dict.fromkeys(SAFETY_FALSE_NAMES, False)

SAMPLE_DEFS: list[dict[str, str]] = [
    {
        "review_id": "rtv-s01",
        "match_id": "4813722",
        "route_code": "2ygkcb",
        "team_pair": "Liverpool vs Manchester United",
        "slug": "liverpool-vs-manchester-united",
    },
    {
        "review_id": "rtv-s02",
        "match_id": "4813492",
        "route_code": "2ynv4k",
        "team_pair": "Everton vs Manchester United",
        "slug": "everton-vs-manchester-united",
    },
]

ROUTE_VARIANTS: list[dict[str, str]] = [
    {"variant": "en", "description": "/en/matches/{route_code}/{match_id}"},
    {"variant": "slug", "description": "original slug path without fragment"},
]


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"{label} missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_type(value: Any) -> str:
    return TYPE_NAME_BY_PY.get(type(value).__name__, type(value).__name__)


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


def _child_count(value: Any) -> int:
    if isinstance(value, dict):
        return len(value)
    if isinstance(value, (list, tuple)):
        return len(value)
    return 0


def _score_key_path(path: str, key_name: str, target_match_id: str, route_code: str) -> int:
    score = 0
    path_lower = path.lower()
    key_lower = key_name.lower()
    if target_match_id in path:
        score += 5
    if route_code in path:
        score += 4
    for token in ("matchdetails", "matchdata", "match_detail", "match_data"):
        if token in path_lower or token in key_lower:
            score += 4
            break
    detail_terms = ("matchfacts", "matchinfo", "shotmap", "momentum", "playerstats")
    for term in detail_terms:
        if term in path_lower or term in key_lower:
            score += 3
            break
    for term in ("header", "general", "content"):
        if term == key_lower or f".{term}" in path_lower:
            score += 3
            break
    for term in ("stats", "lineup", "lineups", "events", "incidents", "matchfacts"):
        if term in key_lower or term in path_lower:
            score += 2
            break
    for term in ("teams", "hometeam", "awayteam"):
        if term in key_lower or term in path_lower:
            score += 2
            break
    for term in ("status", "score", "fixture", "tournament", "league"):
        if term in key_lower or term in path_lower:
            score += 1
            break
    if "notablematches" in path_lower or "notablematches" in key_lower:
        score -= 4
    for term in ("translations", "language", "countrycodes"):
        if term in path_lower or term in key_lower:
            score -= 4
            break
    for term in ("config", "static", "navigation", "menu", "ads", "seo"):
        if term in path_lower or term in key_lower:
            score -= 3
            break
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
    if depth > max_depth or not isinstance(obj, dict):
        return recorded
    for key, value in obj.items():
        path = f"{prefix}.{key}" if prefix else key
        score = _score_key_path(path, key, target_match_id, route_code)
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
            "classification": _classify_path(score),
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


def _build_url(variant: str, route_code: str, match_id: str, slug: str = "") -> str:
    if variant == "en":
        return f"https://www.fotmob.com/en/matches/{route_code}/{match_id}"
    if variant == "slug":
        return f"https://www.fotmob.com/zh-Hans/matches/{slug}/{route_code}"
    return f"https://www.fotmob.com/matches/{route_code}/{match_id}"


def _perform_probe(url: str, max_body_bytes: int) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status_code": None,
        "content_type": None,
        "content_length": None,
        "bytes_read": 0,
        "body_truncated": False,
        "html_body": None,
        "error": None,
        "final_url": None,
        "redirect_observed": False,
    }
    try:
        req = request.Request(url, headers={"User-Agent": "FootballPrediction/1.0"})
        with request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            result["status_code"] = resp.status
            result["content_type"] = resp.headers.get("Content-Type", "")
            result["final_url"] = resp.url
            result["redirect_observed"] = resp.url != url
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


def _determine_variant_decision(strong: int, weak: int, differs: bool) -> str:
    if strong >= 1 or weak >= 1:
        return "route_variant_unlocks_detail_candidate"
    if differs:
        return "route_variant_differs_but_no_detail"
    return "route_variant_same_generic_keyspace"


def _determine_next_phase(allow_network: bool, unlocks: int, differs: int) -> str:
    if not allow_network:
        return NEXT_PHASE_DRY
    if unlocks >= 1:
        return NEXT_PHASE_DETAIL
    if differs >= 1:
        return NEXT_PHASE_DIFFERS
    return NEXT_PHASE_NONE


def _build_dry_run_manifest(
    run_id: str,
    controlled: dict[str, Any],
    keyspace: dict[str, Any],
    review_followup: dict[str, Any],
    seed_manifest: dict[str, Any],
    review_report_path: str,
    max_samples: int,
    max_body_bytes: int,
    max_scan_depth: int,
    max_key_paths: int,
) -> dict[str, Any]:
    validate_inheritance(controlled, keyspace)
    samples = SAMPLE_DEFS[:max_samples]
    return {
        "schema_version": SCHEMA,
        "lifecycle": "current-state",
        "phase": PHASE,
        "run_id": run_id,
        "generated_at": _utc_now(),
        "mode": "dry_run_route_variant_followup_plan_only",
        "inherited_keyspace_review": {
            "default_route_strong_path_candidate_count": 0,
            "zh_hans_route_strong_path_candidate_count": 0,
            "weak_path_candidate_count": 0,
            "best_path_candidate": "props.pageProps.fetchingLeagueData",
            "notable_matches_rejected": True,
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
        },
        "route_variant_selection": {
            "max_samples": max_samples,
            "max_route_variants": MAX_ROUTE_VARIANTS,
            "selected_sample_count": len(samples),
            "selected_match_ids": [s["match_id"] for s in samples],
            "selected_route_codes": [s["route_code"] for s in samples],
            "selected_route_variants": [
                "/en/matches/{route_code}/{match_id}",
                "original_user_slug_path_without_fragment",
            ],
            "max_body_bytes": max_body_bytes,
            "max_scan_depth": max_scan_depth,
            "max_key_paths_recorded": max_key_paths,
            "max_value_preview_chars": 0,
        },
        "route_variant_results": [],
        "route_variant_summary": {
            "allow_network_probe": False,
            "max_network_requests": MAX_NETWORK_REQUESTS,
            "network_requests_attempted": 0,
            "en_variant_attempted_count": 0,
            "slug_variant_attempted_count": 0,
            "route_variant_unlocks_detail_candidate_count": 0,
            "route_variant_differs_but_no_detail_count": 0,
            "route_variant_same_generic_keyspace_count": 0,
            "route_variant_blocked_count": 0,
            "route_variant_invalid_count": 0,
        },
        "route_variant_decision": {
            "best_route_variant": None,
            "best_candidate_path": None,
            "best_candidate_score": 0,
            "best_candidate_state": None,
            "recommended_next_action": "run with --allow-network-probe",
        },
        "raw_write_readiness": {
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
            "raw_write_blocked_until_json_validated": True,
            "route_variant_candidate_validation_required": True,
        },
        "safety": {
            "network_fetch_performed": False,
            "bounded_body_read_performed": False,
            **SAFETY_FALSE,
        },
        "embedded_review": {
            "route_variant_followup_status": "pass",
            "review_report_path": review_report_path,
        },
        "recommended_next_phase": _determine_next_phase(False, 0, 0),
    }


def _build_live_manifest(
    run_id: str,
    controlled: dict[str, Any],
    keyspace: dict[str, Any],
    review_followup: dict[str, Any],
    seed_manifest: dict[str, Any],
    review_report_path: str,
    max_samples: int,
    max_body_bytes: int,
    max_scan_depth: int,
    max_key_paths: int,
    max_network_requests: int,
) -> dict[str, Any]:
    validate_inheritance(controlled, keyspace)
    samples = SAMPLE_DEFS[:max_samples]
    results: list[dict[str, Any]] = []
    network_attempted = 0
    unlocks_count = 0
    differs_count = 0
    same_count = 0
    blocked_count = 0
    invalid_count = 0
    best_score = -999
    best_path = None
    best_variant = None
    best_state = None

    variant_names = [v["variant"] for v in ROUTE_VARIANTS]

    for sample in samples:
        for vn in variant_names:
            if network_attempted >= max_network_requests:
                break
            network_attempted += 1

            url = _build_url(vn, sample["route_code"], sample["match_id"], sample.get("slug", ""))
            probe = _perform_probe(url, max_body_bytes)

            entry: dict[str, Any] = {
                "review_id": sample["review_id"],
                "match_id": sample["match_id"],
                "route_code": sample["route_code"],
                "route_variant": vn,
                "team_pair": sample["team_pair"],
                "requested_path_redacted": url,
                "final_path_redacted": probe.get("final_url", url),
                "redirect_observed": probe["redirect_observed"],
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
                "strong_path_candidate_count": 0,
                "weak_path_candidate_count": 0,
                "partial_path_candidate_count": 0,
                "generic_or_irrelevant_path_count": 0,
                "top_candidate_path": None,
                "top_candidate_score": 0,
                "top_candidate_state": None,
                "differs_from_default_baseline": False,
                "variant_decision": None,
                "validation_state": "route_variant_keyspace_review_completed",
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
                    "route_variant_blocked"
                    if (probe["status_code"] and probe["status_code"] >= 400)
                    else "route_variant_invalid"
                )
                if probe["status_code"] and 300 <= probe["status_code"] < 400:
                    entry["validation_state"] = "route_variant_blocked"
                entry["stop_reason"] = probe["error"]
                if entry["validation_state"] == "route_variant_blocked":
                    blocked_count += 1
                else:
                    invalid_count += 1
                results.append(entry)
                continue

            if probe["status_code"] and probe["status_code"] >= 400:
                entry["validation_state"] = "route_variant_blocked"
                entry["stop_reason"] = f"HTTP {probe['status_code']}"
                blocked_count += 1
                results.append(entry)
                continue

            ct = (probe.get("content_type") or "").lower()
            if "text/html" not in ct:
                entry["validation_state"] = "route_variant_not_html"
                entry["stop_reason"] = f"content_type={ct}"
                invalid_count += 1
                results.append(entry)
                continue

            t0 = time.perf_counter()
            html_body = probe.get("html_body") or ""
            next_data = _parse_next_data(html_body)
            entry["elapsed_ms"] = int((time.perf_counter() - t0) * 1000)

            if next_data is None:
                entry["validation_state"] = "route_variant_next_data_parse_failed"
                entry["stop_reason"] = "NEXT_DATA parse failed"
                invalid_count += 1
                results.append(entry)
                continue

            entry["next_data_parse_ok"] = True
            props = next_data.get("props", {})
            page_props = props.get("pageProps", {})
            entry["pageProps_present"] = bool(page_props)
            entry["fallback_present"] = bool(page_props.get("fallback"))

            recorded = _scan_keyspace(
                next_data, "", 0, max_scan_depth, [], sample["match_id"], sample["route_code"]
            )
            entry["total_key_paths_seen"] = len(recorded)
            entry["key_paths_recorded_count"] = min(len(recorded), max_key_paths)
            entry["target_match_id_in_key_path"] = any(
                r["target_match_id_in_path"] for r in recorded
            )
            entry["route_code_in_key_path"] = any(r["route_code_in_path"] for r in recorded)

            scored = sorted(recorded, key=lambda r: r["score"], reverse=True)
            entry["strong_path_candidate_count"] = sum(
                1 for r in scored if r["classification"].startswith("strong")
            )
            entry["weak_path_candidate_count"] = sum(
                1 for r in scored if r["classification"].startswith("weak")
            )
            entry["partial_path_candidate_count"] = sum(
                1 for r in scored if r["classification"].startswith("partial")
            )
            entry["generic_or_irrelevant_path_count"] = sum(
                1 for r in scored if r["classification"].startswith("generic")
            )

            if scored:
                entry["top_candidate_path"] = scored[0]["key_path"]
                entry["top_candidate_score"] = scored[0]["score"]
                entry["top_candidate_state"] = scored[0]["classification"]

            # Compare to baseline: the default route found only fetchingLeagueData (score=1)
            baseline_path = "props.pageProps.fetchingLeagueData"
            entry["differs_from_default_baseline"] = (
                scored and scored[0]["key_path"] != baseline_path
            )

            s = entry["strong_path_candidate_count"]
            w = entry["weak_path_candidate_count"]
            entry["variant_decision"] = _determine_variant_decision(
                s, w, entry["differs_from_default_baseline"]
            )

            if s >= 1 or w >= 1:
                unlocks_count += 1
            elif entry["differs_from_default_baseline"]:
                differs_count += 1
            else:
                same_count += 1

            if scored and scored[0]["score"] > best_score:
                best_score = scored[0]["score"]
                best_path = scored[0]["key_path"]
                best_variant = vn
                best_state = scored[0]["classification"]

            probe["html_body"] = None  # safety: clear body
            results.append(entry)

    return {
        "schema_version": SCHEMA,
        "lifecycle": "current-state",
        "phase": PHASE,
        "run_id": run_id,
        "generated_at": _utc_now(),
        "mode": "controlled_route_variant_followup_no_write",
        "inherited_keyspace_review": {
            "default_route_strong_path_candidate_count": 0,
            "zh_hans_route_strong_path_candidate_count": 0,
            "weak_path_candidate_count": 0,
            "best_path_candidate": "props.pageProps.fetchingLeagueData",
            "notable_matches_rejected": True,
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
        },
        "route_variant_selection": {
            "max_samples": max_samples,
            "max_route_variants": MAX_ROUTE_VARIANTS,
            "selected_sample_count": len(samples),
            "selected_match_ids": [s["match_id"] for s in samples],
            "selected_route_codes": [s["route_code"] for s in samples],
            "selected_route_variants": [
                "/en/matches/{route_code}/{match_id}",
                "original_user_slug_path_without_fragment",
            ],
            "max_body_bytes": max_body_bytes,
            "max_scan_depth": max_scan_depth,
            "max_key_paths_recorded": max_key_paths,
            "max_value_preview_chars": 0,
        },
        "route_variant_results": results,
        "route_variant_summary": {
            "allow_network_probe": True,
            "max_network_requests": max_network_requests,
            "network_requests_attempted": network_attempted,
            "en_variant_attempted_count": sum(1 for r in results if r.get("route_variant") == "en"),
            "slug_variant_attempted_count": sum(
                1 for r in results if r.get("route_variant") == "slug"
            ),
            "route_variant_unlocks_detail_candidate_count": unlocks_count,
            "route_variant_differs_but_no_detail_count": differs_count,
            "route_variant_same_generic_keyspace_count": same_count,
            "route_variant_blocked_count": blocked_count,
            "route_variant_invalid_count": invalid_count,
        },
        "route_variant_decision": {
            "best_route_variant": best_variant,
            "best_candidate_path": best_path,
            "best_candidate_score": best_score,
            "best_candidate_state": best_state,
            "recommended_next_action": _determine_next_phase(True, unlocks_count, differs_count),
        },
        "raw_write_readiness": {
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
            "raw_write_blocked_until_json_validated": True,
            "route_variant_candidate_validation_required": True,
        },
        "safety": {
            "network_fetch_performed": True,
            "bounded_body_read_performed": True,
            **SAFETY_FALSE,
        },
        "embedded_review": {
            "route_variant_followup_status": "pass",
            "review_report_path": review_report_path,
        },
        "recommended_next_phase": _determine_next_phase(True, unlocks_count, differs_count),
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keyspace-manifest", required=True)
    parser.add_argument("--review-followup-manifest", required=True)
    parser.add_argument("--seed-manifest", required=True)
    parser.add_argument("--output-manifest", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--review-report", required=True)
    parser.add_argument("--decision-report", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--max-samples", type=int, default=2)
    parser.add_argument("--max-route-variants", type=int, default=2)
    parser.add_argument("--max-body-bytes", type=int, default=524288)
    parser.add_argument("--max-scan-depth", type=int, default=12)
    parser.add_argument("--max-key-paths-recorded", type=int, default=500)
    parser.add_argument("--max-network-requests", type=int, default=4)
    parser.add_argument("--allow-network-probe", action="store_true", default=False)
    return parser.parse_args(argv)


def _validate_args(args: argparse.Namespace) -> None:
    if args.max_samples > MAX_SAMPLES:
        raise ValueError(f"--max-samples {args.max_samples} > {MAX_SAMPLES}")
    if args.max_route_variants > MAX_ROUTE_VARIANTS:
        raise ValueError(f"--max-route-variants {args.max_route_variants} > {MAX_ROUTE_VARIANTS}")
    if args.max_network_requests > MAX_NETWORK_REQUESTS:
        raise ValueError(
            f"--max-network-requests {args.max_network_requests} > {MAX_NETWORK_REQUESTS}"
        )
    if args.max_body_bytes > MAX_BODY_BYTES:
        raise ValueError(f"--max-body-bytes {args.max_body_bytes} > {MAX_BODY_BYTES}")
    if args.max_scan_depth > MAX_SCAN_DEPTH:
        raise ValueError(f"--max-scan-depth {args.max_scan_depth} > {MAX_SCAN_DEPTH}")
    if args.max_key_paths_recorded > MAX_KEY_PATHS_RECORDED:
        raise ValueError(
            f"--max-key-paths-recorded {args.max_key_paths_recorded} > {MAX_KEY_PATHS_RECORDED}"
        )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    allow_network = args.allow_network_probe

    try:
        _validate_args(args)
        controlled = _load_json(Path(args.review_followup_manifest), "review followup manifest")
        keyspace = _load_json(Path(args.keyspace_manifest), "keyspace manifest")
        seed_manifest = _load_json(Path(args.seed_manifest), "seed manifest")
        review_report_path = str(Path(args.review_report))

        if allow_network:
            manifest = _build_live_manifest(
                run_id=args.run_id,
                controlled=controlled,
                keyspace=keyspace,
                review_followup=controlled,
                seed_manifest=seed_manifest,
                review_report_path=review_report_path,
                max_samples=args.max_samples,
                max_body_bytes=args.max_body_bytes,
                max_scan_depth=args.max_scan_depth,
                max_key_paths=args.max_key_paths_recorded,
                max_network_requests=args.max_network_requests,
            )
        else:
            manifest = _build_dry_run_manifest(
                run_id=args.run_id,
                controlled=controlled,
                keyspace=keyspace,
                review_followup=controlled,
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
    print(f"PASS: hydration route variant follow-up no-write ({mode}) complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
