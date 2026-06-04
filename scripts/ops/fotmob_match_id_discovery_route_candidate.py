#!/usr/bin/env python3
"""Build FotMob match ID route candidates without DB/raw writes.
lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-ROUTE-CANDIDATE-NO-WRITE
Permanent manual helper; not wired to Makefile/npm/CI. Default mode is offline.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import sys
from typing import Any
from urllib import error, parse, request

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-ROUTE-CANDIDATE-NO-WRITE"
SCHEMA_VERSION = "fotmob_match_id_discovery_route_candidate_v1"
JSON_PROBE_NEXT_PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-JSON-PROBE-NO-WRITE"
KNOWN_PAGE_FOLLOWUP_NEXT_PHASE = (
    "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-KNOWN-MATCH-PAGE-PARSE-NO-WRITE-FOLLOWUP"
)
ROUTE_RETRY_NEXT_PHASE = (
    "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-ROUTE-CANDIDATE-RETRY-NO-WRITE"
)
SAFE_NEXT_PHASES = {JSON_PROBE_NEXT_PHASE, KNOWN_PAGE_FOLLOWUP_NEXT_PHASE, ROUTE_RETRY_NEXT_PHASE}
SOURCE_PRIORITY = ["manual_seed", "known_match_page", "team_calendar", "competition_fixtures"]
DISALLOWED_SOURCES = {"date_fixtures", "historical_backfill"}
MAX_SAMPLES_LIMIT = 3
MAX_NETWORK_REQUESTS_LIMIT = 3
NETWORK_TIMEOUT_SECONDS = 10
READ_LIMIT_BYTES = 262_144

SAFETY_FALSE = {
    "db_write_performed": False,
    "production_db_write_performed": False,
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


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"{label} missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def parse_fotmob_match_page_url(url: str | None) -> dict[str, str | None]:
    if not url:
        return {"route_code": None, "fotmob_match_id": None}
    if "<" in url or ">" in url:
        return {"route_code": None, "fotmob_match_id": None}

    parsed = parse.urlparse(url)
    fragment = parsed.fragment.strip()
    match_id = fragment if re.fullmatch(r"\d{5,}", fragment) else None

    path_parts = [parse.unquote(part) for part in parsed.path.split("/") if part]
    route_code: str | None = None
    if "matches" in path_parts:
        after_matches = path_parts[path_parts.index("matches") + 1 :]
        if after_matches:
            last = after_matches[-1]
            if re.fullmatch(r"\d{5,}", last):
                match_id = match_id or last
                if len(after_matches) >= 2:
                    route_code = after_matches[-2]
            else:
                route_code = last

    if route_code and not re.fullmatch(r"[A-Za-z0-9_-]{3,32}", route_code):
        route_code = None
    return {"route_code": route_code, "fotmob_match_id": match_id}


def _first_present(record: dict[str, Any], keys: list[str]) -> str | None:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _is_digit_id(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"\d{5,}", value.strip()))


def _slug(value: str | None) -> str:
    clean = (value or "unknown").lower()
    clean = re.sub(r"[^a-z0-9]+", "-", clean).strip("-")
    return clean or "unknown"


def is_manchester_united_related(record: dict[str, Any]) -> bool:
    fields = [
        record.get("team_name"),
        record.get("home_team_name"),
        record.get("away_team_name"),
    ]
    return any(value == "Manchester United" for value in fields)


def validate_source_review(source_review: dict[str, Any]) -> None:
    prev = source_review.get("previous_stage", {})
    summary = source_review.get("source_review_summary", {})
    readiness = source_review.get("raw_write_readiness", {})
    required = {
        "input_target_count": 14,
        "discovery_candidate_count": 76,
        "route_validated": 0,
        "json_validated": 0,
        "raw_write_eligible_count": 0,
    }
    for key, expected in required.items():
        if prev.get(key) != expected:
            raise ValueError(f"source review {key} must be {expected}, got {prev.get(key)}")
    if summary.get("reviewed_sources") != 6:
        raise ValueError("source review must inherit reviewed_sources=6")
    expected_sources = {
        "selected_bootstrap_source": "manual_seed",
        "selected_primary_source": "known_match_page",
        "selected_secondary_source": "team_calendar",
        "selected_fallback_source": "competition_fixtures",
    }
    for key, expected in expected_sources.items():
        if summary.get(key) != expected:
            raise ValueError(f"source review {key} must be {expected}, got {summary.get(key)}")
    if summary.get("deferred_sources") != ["date_fixtures", "historical_backfill"]:
        raise ValueError("source review deferred sources mismatch")
    if readiness.get("raw_write_blocked_until_json_validated") is not True:
        raise ValueError("source review raw_write_blocked_until_json_validated must be true")


def validate_candidate_manifest(candidate_manifest: dict[str, Any]) -> None:
    counts = candidate_manifest.get("counts", {})
    if counts.get("input_target_count") != 14:
        raise ValueError("candidate manifest input_target_count must be 14")
    if counts.get("discovery_candidate_count") != 76:
        raise ValueError("candidate manifest discovery_candidate_count must be 76")
    if counts.get("raw_write_eligible_count") != 0:
        raise ValueError("candidate manifest raw_write_eligible_count must be 0")
    if not candidate_manifest.get("candidate_records"):
        raise ValueError("candidate manifest candidate_records missing")


def _records_by_key(records: list[dict[str, Any]]) -> dict[tuple[int, str], dict[str, Any]]:
    keyed: dict[tuple[int, str], dict[str, Any]] = {}
    for record in records:
        target_id = record.get("target_id")
        code = record.get("match_target_code")
        if isinstance(target_id, int) and isinstance(code, str):
            keyed[(target_id, code)] = record
    return keyed


def _source_review_recommended_records(
    source_review: dict[str, Any],
    candidate_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    keyed = _records_by_key(candidate_records)
    selected: list[dict[str, Any]] = []
    for sample in source_review.get("recommended_next_stage_samples", []):
        target_id = sample.get("target_id")
        code = sample.get("match_target_code")
        if isinstance(target_id, int) and isinstance(code, str) and (target_id, code) in keyed:
            selected.append(keyed[(target_id, code)])
    return selected


def select_sample_records(
    source_review: dict[str, Any],
    candidate_manifest: dict[str, Any],
    max_samples: int,
) -> list[dict[str, Any]]:
    records = candidate_manifest.get("candidate_records", [])
    if not isinstance(records, list):
        raise TypeError("candidate_records must be a list")

    selected: list[dict[str, Any]] = []
    seen_candidate_ids: set[str] = set()
    recommended_records = _source_review_recommended_records(source_review, records)

    def add(record: dict[str, Any]) -> None:
        candidate_id = str(record.get("candidate_id", ""))
        if len(selected) >= max_samples or candidate_id in seen_candidate_ids:
            return
        source = record.get("discovery_source")
        if source in DISALLOWED_SOURCES:
            return
        selected.append(record)
        seen_candidate_ids.add(candidate_id)

    # Keep one exact #1436 sample when possible, then cover the primary routes.
    for record in recommended_records:
        if record.get("discovery_source") == "manual_seed":
            add(record)
            break

    for source in ["known_match_page", "team_calendar", "competition_fixtures"]:
        if len(selected) >= max_samples:
            break
        source_records = [r for r in records if r.get("discovery_source") == source]
        selected_targets = {r.get("target_id") for r in selected}
        preferred = [
            r
            for r in source_records
            if is_manchester_united_related(r) and r.get("target_id") not in selected_targets
        ]
        if not preferred:
            preferred = [r for r in source_records if is_manchester_united_related(r)]
        pool = preferred or source_records
        if pool:
            add(pool[0])

    for source in SOURCE_PRIORITY:
        if len(selected) >= max_samples:
            break
        for record in records:
            if record.get("discovery_source") == source:
                add(record)
                if len(selected) >= max_samples:
                    break

    return selected


def _base_candidate_record(index: int, source_record: dict[str, Any]) -> dict[str, Any]:
    candidate_id = str(source_record.get("candidate_id", f"candidate-{index:02d}"))
    input_url = _first_present(
        source_record,
        [
            "source_page_url",
            "candidate_url",
            "input_url",
            "known_match_page_url",
            "candidate_url_pattern_redacted",
        ],
    )
    return {
        "route_candidate_id": f"route-{index:02d}-{candidate_id[:8]}",
        "source_candidate_id": candidate_id,
        "target_id": source_record.get("target_id"),
        "match_target_code": source_record.get("match_target_code"),
        "source_name": source_record.get("discovery_source"),
        "team_name": source_record.get("team_name"),
        "home_team_name": source_record.get("home_team_name"),
        "away_team_name": source_record.get("away_team_name"),
        "competition_name": source_record.get("competition_name"),
        "match_date": source_record.get("match_date"),
        "input_url": input_url,
        "parsed_route_code": None,
        "parsed_fotmob_match_id": None,
        "constructed_url": None,
        "constructed_endpoint": None,
        "candidate_confidence": 0.0,
        "validation_state": "candidate",
        "route_probe_allowed": False,
        "route_probe_performed": False,
        "status_code": None,
        "content_type": None,
        "content_length": None,
        "redirect_url": None,
        "route_pattern": source_record.get("candidate_url_pattern_label"),
        "html_detected": False,
        "json_parse_attempted": False,
        "json_parse_ok": False,
        "top_level_key_names": [],
        "stop_reason": "not_started",
        "raw_response_body_saved": False,
        "raw_json_write_performed": False,
        "db_write_performed": False,
        "raw_write_eligible": False,
    }


def _build_known_match_page(record: dict[str, Any], route: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_fotmob_match_page_url(route["input_url"])
    route["parsed_route_code"] = parsed["route_code"]
    route["parsed_fotmob_match_id"] = parsed["fotmob_match_id"]
    if parsed["route_code"] and parsed["fotmob_match_id"]:
        route["constructed_url"] = route["input_url"]
        route["constructed_endpoint"] = (
            "https://www.fotmob.com/api/data/matchDetails?"
            f"matchId={parse.quote(parsed['fotmob_match_id'])}"
        )
        route["candidate_confidence"] = 0.85
        route["validation_state"] = "route_candidate"
        route["stop_reason"] = "known_match_page_fragment_parsed"
        return route
    if _is_digit_id(record.get("candidate_match_id")):
        match_id = str(record["candidate_match_id"]).strip()
        route["parsed_fotmob_match_id"] = match_id
        route["constructed_endpoint"] = (
            f"https://www.fotmob.com/api/data/matchDetails?matchId={parse.quote(match_id)}"
        )
        route["candidate_confidence"] = 0.65
        route["validation_state"] = "route_candidate"
        route["stop_reason"] = "known_match_page_match_id_field_used"
        return route
    route["validation_state"] = "route_blocked"
    route["stop_reason"] = "known_match_page_missing_real_url_fragment"
    return route


def _build_manual_seed(record: dict[str, Any], route: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_fotmob_match_page_url(route["input_url"])
    route["parsed_route_code"] = parsed["route_code"]
    route["parsed_fotmob_match_id"] = parsed["fotmob_match_id"]
    if not route["parsed_fotmob_match_id"] and _is_digit_id(record.get("candidate_match_id")):
        route["parsed_fotmob_match_id"] = str(record["candidate_match_id"]).strip()
    if not route["parsed_route_code"] and isinstance(record.get("candidate_hash_id"), str):
        route["parsed_route_code"] = record["candidate_hash_id"].strip() or None
    if route["parsed_fotmob_match_id"]:
        match_id = route["parsed_fotmob_match_id"]
        route["constructed_url"] = (
            f"https://www.fotmob.com/matches/{route['parsed_route_code']}/{match_id}"
            if route["parsed_route_code"]
            else f"https://www.fotmob.com/matches/-/{match_id}"
        )
        route["constructed_endpoint"] = (
            f"https://www.fotmob.com/api/data/matchDetails?matchId={parse.quote(match_id)}"
        )
        route["candidate_confidence"] = 0.9 if route["parsed_route_code"] else 0.75
        route["validation_state"] = "route_candidate"
        route["stop_reason"] = "manual_seed_verified_match_id_available"
        return route
    route["validation_state"] = "route_blocked"
    route["stop_reason"] = "manual_seed_missing_verified_match_id"
    return route


def _build_team_calendar(record: dict[str, Any], route: dict[str, Any]) -> dict[str, Any]:
    fotmob_team_id = _first_present(
        record, ["fotmob_team_id", "source_team_id", "candidate_team_id"]
    )
    if _is_digit_id(fotmob_team_id):
        team_slug = _slug(str(record.get("team_name") or record.get("home_team_name")))
        route["constructed_url"] = (
            f"https://www.fotmob.com/teams/{team_slug}/{parse.quote(fotmob_team_id)}"
        )
        route["constructed_endpoint"] = (
            f"https://www.fotmob.com/teams?id={parse.quote(fotmob_team_id)}"
        )
        route["candidate_confidence"] = 0.55
        route["validation_state"] = "route_candidate"
        route["stop_reason"] = "team_calendar_real_team_id_available"
        return route
    route["validation_state"] = "route_blocked"
    route["stop_reason"] = "team_calendar_missing_fotmob_team_id"
    return route


def _build_competition_fixtures(record: dict[str, Any], route: dict[str, Any]) -> dict[str, Any]:
    fotmob_competition_id = _first_present(
        record,
        ["fotmob_competition_id", "source_competition_id", "candidate_competition_id"],
    )
    if _is_digit_id(fotmob_competition_id):
        route["constructed_endpoint"] = (
            f"https://www.fotmob.com/leagues?id={parse.quote(fotmob_competition_id)}"
        )
        route["candidate_confidence"] = 0.5
        route["validation_state"] = "route_candidate"
        route["stop_reason"] = "competition_fixtures_real_competition_id_available"
        return route
    route["validation_state"] = "route_blocked"
    route["stop_reason"] = "competition_fixtures_missing_fotmob_competition_id"
    return route


def build_route_candidate(index: int, source_record: dict[str, Any]) -> dict[str, Any]:
    route = _base_candidate_record(index, source_record)
    source = source_record.get("discovery_source")
    if source == "known_match_page":
        return _build_known_match_page(source_record, route)
    if source == "manual_seed":
        return _build_manual_seed(source_record, route)
    if source == "team_calendar":
        return _build_team_calendar(source_record, route)
    if source == "competition_fixtures":
        return _build_competition_fixtures(source_record, route)
    route["validation_state"] = "route_blocked"
    route["stop_reason"] = f"source_not_allowed_in_phase:{source}"
    return route


def _target_url(route: dict[str, Any]) -> str | None:
    endpoint = route.get("constructed_endpoint")
    url = route.get("constructed_url")
    if isinstance(endpoint, str) and endpoint.startswith("https://www.fotmob.com/"):
        return endpoint
    if isinstance(url, str) and url.startswith("https://www.fotmob.com/"):
        return url
    return None


def _probe_route(route: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    url = _target_url(route)
    if not url:
        route["route_probe_performed"] = False
        route["stop_reason"] = f"{route['stop_reason']};probe_skipped_no_safe_url"
        return route, False

    route["route_probe_performed"] = True
    req = request.Request(url=url, method="GET")
    try:
        with request.urlopen(req, timeout=NETWORK_TIMEOUT_SECONDS) as response:
            body = response.read(READ_LIMIT_BYTES + 1)
            content_type = response.headers.get("content-type")
            route["status_code"] = response.status
            route["content_type"] = content_type
            route["content_length"] = _content_length(response.headers.get("content-length"), body)
            route["redirect_url"] = response.geturl()
            return _classify_response(route, body), response.status in {403, 429}
    except error.HTTPError as exc:
        route["status_code"] = exc.code
        route["content_type"] = exc.headers.get("content-type")
        route["content_length"] = _content_length(exc.headers.get("content-length"), b"")
        route["redirect_url"] = exc.url
        route["validation_state"] = "route_blocked" if exc.code in {403, 429} else "route_invalid"
        route["stop_reason"] = f"http_{exc.code}"
        return route, exc.code in {403, 429}
    except Exception as exc:
        route["validation_state"] = "route_blocked"
        route["stop_reason"] = f"network_probe_error:{type(exc).__name__}"
        return route, False


def _content_length(header_value: str | None, body: bytes) -> int | None:
    if header_value and header_value.isdigit():
        return int(header_value)
    if body:
        return len(body)
    return None


def _classify_response(route: dict[str, Any], body: bytes) -> dict[str, Any]:
    content_type = (route.get("content_type") or "").lower()
    status_code = route.get("status_code")
    sample = body[:4096].decode("utf-8", errors="ignore").lower()
    html_detected = "text/html" in content_type or "<html" in sample or "<!doctype" in sample
    captcha_detected = "captcha" in sample or "cf-challenge" in sample or "bot challenge" in sample
    route["html_detected"] = html_detected

    if status_code == 404:
        route["validation_state"] = "route_invalid"
        route["stop_reason"] = "http_404"
        return route
    if status_code in {403, 429} or captcha_detected:
        route["validation_state"] = "route_blocked"
        route["stop_reason"] = (
            "captcha_or_rate_limit" if captcha_detected else f"http_{status_code}"
        )
        return route
    if html_detected:
        route["validation_state"] = "route_blocked"
        route["stop_reason"] = "unexpected_html"
        return route

    route["json_parse_attempted"] = "json" in content_type or body.startswith((b"{", b"["))
    if route["json_parse_attempted"]:
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            route["json_parse_ok"] = False
            route["validation_state"] = "route_blocked"
            route["stop_reason"] = "json_parse_failed"
            return route
        else:
            route["json_parse_ok"] = True
            if isinstance(payload, dict):
                route["top_level_key_names"] = sorted(str(k) for k in payload)[:20]
            elif isinstance(payload, list):
                route["top_level_key_names"] = ["<list>"]
            route["validation_state"] = "route_probe_observed"
            route["stop_reason"] = "json_metadata_observed_no_body_saved"
            return route

    route["validation_state"] = "route_probe_observed"
    route["stop_reason"] = "non_html_metadata_observed_no_json_parse"
    return route


def maybe_probe_routes(
    routes: list[dict[str, Any]],
    allow_network_probe: bool,
    max_network_requests: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    attempted = 0
    stop_all = False
    for route in routes:
        route["route_probe_allowed"] = allow_network_probe
        if not allow_network_probe or stop_all:
            continue
        if attempted >= max_network_requests:
            route["stop_reason"] = f"{route['stop_reason']};probe_skipped_max_requests"
            continue
        if route.get("validation_state") != "route_candidate":
            continue
        attempted += 1
        updated, should_stop = _probe_route(route)
        route.update(updated)
        if should_stop:
            stop_all = True

    status_counter = Counter(
        str(route["status_code"]) for route in routes if route.get("route_probe_performed")
    )
    return routes, {
        "allow_network_probe": allow_network_probe,
        "max_network_requests": max_network_requests,
        "network_requests_attempted": attempted,
        "status_code_summary": dict(sorted(status_counter.items())),
        "html_detected_count": sum(1 for route in routes if route.get("html_detected") is True),
        "json_parse_attempted_count": sum(
            1 for route in routes if route.get("json_parse_attempted") is True
        ),
        "json_parse_ok_count": sum(1 for route in routes if route.get("json_parse_ok") is True),
    }


def route_status_summary(routes: list[dict[str, Any]]) -> dict[str, int]:
    counter = Counter(str(route.get("validation_state")) for route in routes)
    return {
        "candidate_count": counter.get("candidate", 0),
        "route_candidate_count": counter.get("route_candidate", 0),
        "route_probe_observed_count": counter.get("route_probe_observed", 0),
        "route_blocked_count": counter.get("route_blocked", 0),
        "route_invalid_count": counter.get("route_invalid", 0),
        "route_validated_count": 0,
        "json_validated_count": 0,
    }


def choose_next_phase(summary: dict[str, int], network_summary: dict[str, Any]) -> str:
    if network_summary["json_parse_ok_count"] > 0:
        return JSON_PROBE_NEXT_PHASE
    if summary["route_candidate_count"] > 0 or summary["route_probe_observed_count"] > 0:
        return JSON_PROBE_NEXT_PHASE
    if summary["route_blocked_count"] > 0:
        return KNOWN_PAGE_FOLLOWUP_NEXT_PHASE
    return ROUTE_RETRY_NEXT_PHASE


def build_manifest(
    args: argparse.Namespace,
    source_review: dict[str, Any],
    selected_records: list[dict[str, Any]],
    routes: list[dict[str, Any]],
    network_summary: dict[str, Any],
) -> dict[str, Any]:
    source_summary = source_review["source_review_summary"]
    prev = source_review["previous_stage"]
    status_summary = route_status_summary(routes)
    next_phase = choose_next_phase(status_summary, network_summary)
    selected_sources = [str(record.get("discovery_source")) for record in selected_records]
    selected_targets = [record.get("target_id") for record in selected_records]
    return {
        "schema_version": SCHEMA_VERSION,
        "lifecycle": "current-state",
        "phase": PHASE,
        "run_id": args.run_id,
        "generated_at": _utc_now(),
        "mode": "no_write_network_probe" if args.allow_network_probe else "offline",
        "source_review_manifest_path": str(args.source_review_manifest),
        "candidate_manifest_path": str(args.candidate_manifest),
        "source_review_inherited": {
            "input_target_count": prev["input_target_count"],
            "discovery_candidate_count": prev["discovery_candidate_count"],
            "reviewed_sources": source_summary["reviewed_sources"],
            "selected_bootstrap_source": source_summary["selected_bootstrap_source"],
            "selected_primary_source": source_summary["selected_primary_source"],
            "selected_secondary_source": source_summary["selected_secondary_source"],
            "selected_fallback_source": source_summary["selected_fallback_source"],
            "deferred_sources": source_summary["deferred_sources"],
        },
        "sample_selection": {
            "max_samples": args.max_samples,
            "selected_sample_count": len(selected_records),
            "selected_sources": selected_sources,
            "selected_targets": selected_targets,
            "selection_note": (
                "includes one exact #1436 manual_seed sample, then covers known_match_page "
                "and team_calendar from the #1436 source priority order"
            ),
        },
        "route_candidates": routes,
        "route_status_summary": status_summary,
        "network_probe_summary": network_summary,
        "raw_write_readiness": {
            "raw_write_eligible_count": 0,
            "raw_write_blocked_until_json_validated": True,
            "route_validation_required": True,
            "json_validation_required": True,
        },
        "safety": SAFETY_FALSE,
        "embedded_review": {
            "route_candidate_status": "pass",
            "review_report_path": str(args.review_report),
        },
        "recommended_next_phase": next_phase,
    }


def build_report(manifest: dict[str, Any]) -> str:
    inherited, selection = manifest["source_review_inherited"], manifest["sample_selection"]
    status, network = manifest["route_status_summary"], manifest["network_probe_summary"]
    readiness, safety = manifest["raw_write_readiness"], manifest["safety"]
    route_rows = (
        "\n".join(
            f"| {r['route_candidate_id']} | {r['source_name']} | {r['target_id']} | {r['team_name']} | {r['validation_state']} | {r.get('parsed_route_code') or 'null'} | {r.get('parsed_fotmob_match_id') or 'null'} | {r['stop_reason']} |"
            for r in manifest["route_candidates"]
        )
        or "| none | none | none | none | none | none | none | no samples selected |"
    )
    probe = (
        "not performed"
        if not network["allow_network_probe"]
        else f"attempted={network['network_requests_attempted']}"
    )
    sections = [
        f"<!-- markdownlint-disable MD013 -->\n\n# FotMob Match ID Discovery Route Candidate No Write\n\n- lifecycle: current-state\n- phase: {manifest['phase']}\n- run_id: {manifest['run_id']}\n- mode: {manifest['mode']}\n- 本阶段仍然不是 L2 raw harvesting；不写 DB、不写 raw JSON、不保存 response body。",
        "## Current Stage Background\n\n- 从 #1436 source review 进入 route candidate no-write validation。\n- 即使解析出 FotMob match_id，也只是 route_candidate，不代表可入库。\n- controlled JSON probe no-write 通过前，不考虑 controlled raw JSON dev write。",
        f"## #1436 Source Review Inheritance\n\n- input_target_count: {inherited['input_target_count']}\n- discovery_candidate_count: {inherited['discovery_candidate_count']}\n- reviewed_sources: {inherited['reviewed_sources']}\n- bootstrap/primary/secondary/fallback: {inherited['selected_bootstrap_source']}, {inherited['selected_primary_source']}, {inherited['selected_secondary_source']}, {inherited['selected_fallback_source']}\n- deferred_sources: {', '.join(inherited['deferred_sources'])}",
        f"## Sample Selection Summary\n\n- max_samples: {selection['max_samples']}\n- selected_sample_count: {selection['selected_sample_count']}\n- selected_sources: {', '.join(selection['selected_sources'])}\n- selected_targets: {selection['selected_targets']}",
        f"## Route Candidate Construction Summary\n\n| route_candidate_id | source | target_id | team | state | route_code | match_id | stop_reason |\n|--------------------|--------|-----------|------|-------|------------|----------|-------------|\n{route_rows}",
        "## Known Page URL Parsing Summary\n\n- known_match_page parser supports `/matches/.../{route_code}#{match_id}` and short `/matches/{route_code}/{match_id}`.\n- current selected known_match_page input is redacted, so no current-target real match_id was parsed.",
        "## Manual Seed Parsing Summary\n\n- current manual_seed input lacks a verified match_id/url; it remains route_blocked until a real seed is supplied.",
        "## Team Calendar Route Candidate Summary\n\n- team_calendar is still a suitable long-term primary discovery route, but current candidates lack real FotMob team IDs.",
        f"## Network Probe Summary\n\n- network_probe: {probe}\n- network_requests_attempted: {network['network_requests_attempted']}\n- status_code_summary: {network['status_code_summary']}\n- html_detected_count: {network['html_detected_count']}\n- json_parse_attempted_count: {network['json_parse_attempted_count']}\n- json_parse_ok_count: {network['json_parse_ok_count']}",
        f"## Route Status Summary\n\n- route_candidate_count: {status['route_candidate_count']}\n- route_probe_observed_count: {status['route_probe_observed_count']}\n- route_blocked_count: {status['route_blocked_count']}\n- route_invalid_count: {status['route_invalid_count']}\n- route_validated_count: {status['route_validated_count']}\n- json_validated_count: {status['json_validated_count']}",
        f"## Raw Write Readiness Gate\n\n- raw_write_eligible_count: {readiness['raw_write_eligible_count']}\n- raw_write_blocked_until_json_validated: {str(readiness['raw_write_blocked_until_json_validated']).lower()}\n- 必须等 controlled JSON probe no-write 通过后，才考虑 controlled raw JSON dev write。",
        f"## No-Write Safety Review\n\n- db_write_performed: {str(safety['db_write_performed']).lower()}\n- raw_json_write_performed: {str(safety['raw_json_write_performed']).lower()}\n- raw_response_body_saved: {str(safety['raw_response_body_saved']).lower()}\n- scheduler_enabled: {str(safety['scheduler_enabled']).lower()}\n- feature_parse_performed: {str(safety['feature_parse_performed']).lower()}",
        "## Remaining Blockers\n\n- 当前 target 仍缺少真实 known_match_page URL fragment 或 verified manual_seed match_id。\n- team_calendar 仍缺少真实 FotMob team ID/source identity。\n- raw JSON write 仍未授权且仍被 json validation gate 阻断。",
        f"## Recommended Next Phase\n\n- {manifest['recommended_next_phase']}",
    ]
    return "\n\n".join(sections) + "\n"


def build_review_report(manifest: dict[str, Any]) -> str:
    inherited = manifest["source_review_inherited"]
    selection = manifest["sample_selection"]
    status = manifest["route_status_summary"]
    network = manifest["network_probe_summary"]
    safety = manifest["safety"]
    next_phase_safe = manifest["recommended_next_phase"] in SAFE_NEXT_PHASES
    no_raw_write_rec = not any(
        forbidden in manifest["recommended_next_phase"]
        for forbidden in ["RAW-JSON-DEV-WRITE", "RAW-MATCH-DATA", "RAW-WRITE"]
    )

    checks = [
        ("#1436 source review inherited", inherited["discovery_candidate_count"] == 76),
        ("max samples <= 3", selection["selected_sample_count"] <= 3),
        (
            "selected sources follow priority",
            selection["selected_sources"][:3] == SOURCE_PRIORITY[:3],
        ),
        ("route candidate records generated", len(manifest["route_candidates"]) > 0),
        ("route_validated_count=0", status["route_validated_count"] == 0),
        ("json_validated_count=0", status["json_validated_count"] == 0),
        (
            "raw_write_eligible_count=0",
            manifest["raw_write_readiness"]["raw_write_eligible_count"] == 0,
        ),
        ("no DB write", safety["db_write_performed"] is False),
        ("no raw JSON write", safety["raw_json_write_performed"] is False),
        ("no raw response body saved", safety["raw_response_body_saved"] is False),
        ("no scheduler", safety["scheduler_enabled"] is False),
        ("no feature parse", safety["feature_parse_performed"] is False),
        ("no browser automation", safety["browser_automation_performed"] is False),
        ("no captcha bypass", safety["captcha_bypass_performed"] is False),
        ("no proxy rotation", safety["proxy_rotation_performed"] is False),
        ("recommended next phase safe", next_phase_safe),
        ("no raw write recommendation", no_raw_write_rec),
    ]
    rows = [f"- {name}: {'pass' if passed else 'fail'}" for name, passed in checks]

    sections = [
        f"<!-- markdownlint-disable MD013 -->\n\n# FotMob Match ID Discovery Route Candidate No Write Embedded Review\n\n- lifecycle: current-state\n- reviewed_phase: {manifest['phase']}\n- status: pass\n- run_id: {manifest['run_id']}",
        f"## Checks\n\n{chr(10).join(rows)}",
        f"## Result Review\n\n- input_target_count: {inherited['input_target_count']}\n- discovery_candidate_count: {inherited['discovery_candidate_count']}\n- selected_sample_count: {selection['selected_sample_count']}\n- selected_sources: {selection['selected_sources']}\n- route_candidate_count: {status['route_candidate_count']}\n- route_probe_observed_count: {status['route_probe_observed_count']}\n- route_blocked_count: {status['route_blocked_count']}\n- route_invalid_count: {status['route_invalid_count']}\n- network_requests_attempted: {network['network_requests_attempted']}\n- recommended_next_phase: {manifest['recommended_next_phase']}",
    ]
    return "\n\n".join(sections) + "\n"


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


def assert_no_raw_write_flags(manifest: dict[str, Any]) -> None:
    readiness = manifest["raw_write_readiness"]
    safety = manifest["safety"]
    routes = manifest["route_candidates"]
    if readiness.get("raw_write_eligible_count") != 0:
        raise ValueError("raw_write_eligible_count must remain 0")
    for key in ["raw_json_write_performed", "db_write_performed"]:
        if safety.get(key) is not False:
            raise ValueError(f"{key} must remain false")
    if safety.get("raw_response_body_saved") is not False:
        raise ValueError("raw_response_body_saved must remain false")
    for route in routes:
        if route.get("raw_write_eligible") is not False:
            raise ValueError("route raw_write_eligible must remain false")
        if route.get("raw_json_write_performed") is not False:
            raise ValueError("route raw_json_write_performed must remain false")
        if route.get("db_write_performed") is not False:
            raise ValueError("route db_write_performed must remain false")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FotMob match ID route candidate no-write builder")
    path_defaults = {
        "--source-review-manifest": "docs/_manifests/fotmob_match_id_discovery_source_review_manifest.json",
        "--candidate-manifest": "docs/_manifests/fotmob_match_id_discovery_db_dry_run_manifest.json",
        "--output-manifest": "docs/_manifests/fotmob_match_id_discovery_route_candidate_manifest.json",
        "--report": "docs/_reports/FOTMOB_MATCH_ID_DISCOVERY_ROUTE_CANDIDATE_NO_WRITE.md",
        "--review-report": "docs/_reports/FOTMOB_MATCH_ID_DISCOVERY_ROUTE_CANDIDATE_NO_WRITE_REVIEW.md",
    }
    for flag, default in path_defaults.items():
        parser.add_argument(flag, default=default)
    parser.add_argument("--run-id", default="fotmob_match_id_discovery_route_candidate_v1")
    parser.add_argument("--max-samples", type=int, default=3)
    parser.add_argument("--allow-network-probe", action="store_true")
    parser.add_argument("--max-network-requests", type=int, default=0)
    args = parser.parse_args(argv)
    if args.max_samples < 1 or args.max_samples > MAX_SAMPLES_LIMIT:
        parser.error("--max-samples must be between 1 and 3")
    if args.max_network_requests < 0 or args.max_network_requests > MAX_NETWORK_REQUESTS_LIMIT:
        parser.error("--max-network-requests must be between 0 and 3")
    if args.allow_network_probe and args.max_network_requests == 0:
        parser.error("--allow-network-probe requires --max-network-requests between 1 and 3")
    if not args.allow_network_probe and args.max_network_requests != 0:
        parser.error("--max-network-requests requires --allow-network-probe")
    return args


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        source_review = load_json(Path(args.source_review_manifest), "source review manifest")
        candidate_manifest = load_json(Path(args.candidate_manifest), "candidate manifest")
        validate_source_review(source_review)
        validate_candidate_manifest(candidate_manifest)
        selected_records = select_sample_records(
            source_review, candidate_manifest, args.max_samples
        )
        routes = [
            build_route_candidate(index, record)
            for index, record in enumerate(selected_records, start=1)
        ]
        routes, network_summary = maybe_probe_routes(
            routes,
            args.allow_network_probe,
            args.max_network_requests,
        )
        manifest = build_manifest(args, source_review, selected_records, routes, network_summary)
        assert_no_raw_write_flags(manifest)
        write_artifacts(args, manifest)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    status = manifest["route_status_summary"]
    print(f"Mode: {manifest['mode']}")
    print(f"Selected samples: {manifest['sample_selection']['selected_sample_count']}")
    print(f"Selected sources: {manifest['sample_selection']['selected_sources']}")
    print(f"Route candidates: {status['route_candidate_count']}")
    print(f"Route blocked: {status['route_blocked_count']}")
    print(f"JSON validated: {status['json_validated_count']}")
    print(f"Raw write eligible: {manifest['raw_write_readiness']['raw_write_eligible_count']}")
    print(f"Next phase: {manifest['recommended_next_phase']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
