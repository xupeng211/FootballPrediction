#!/usr/bin/env python3
"""Controlled FotMob match detail subtree extraction metadata only.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-MATCH-DETAIL-SUBTREE-EXTRACTION-NO-WRITE

Performs bounded /matches/{route_code}/{match_id} probes only when explicitly
authorized, parses __NEXT_DATA__ in memory, and persists metadata only.
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

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-MATCH-DETAIL-SUBTREE-EXTRACTION-NO-WRITE"
SCHEMA = "fotmob_controlled_match_detail_subtree_extraction_no_write_v1"
ROUTE_TEMPLATE = "/matches/{route_code}/{match_id}"
FULL_ROUTE_TEMPLATE = f"https://www.fotmob.com{ROUTE_TEMPLATE}"
ROOT_PATH = "props.pageProps"
TIMEOUT_SECONDS = 10
MAX_SAMPLES = 2
MAX_NETWORK_REQUESTS = 2
MAX_BODY_BYTES = 524288
MAX_SUBTREE_SCAN_DEPTH = 8
MAX_KEY_PATHS_RECORDED = 200
MAX_CANDIDATE_PATHS_RECORDED = 20

DRY_RUN_NEXT = PHASE
STRONG_NEXT = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-DETAIL-SUBTREE-VALIDATION-NO-WRITE"
WEAK_NEXT = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-DETAIL-WEAK-SUBTREE-FOLLOWUP-NO-WRITE"
REVIEW_NEXT = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-DETAIL-SUBTREE-REVIEW-FOLLOWUP-NO-WRITE"

SAMPLE_FIELDS = ("extraction_id", "match_id", "route_code", "team_pair")
SAMPLES: list[dict[str, str]] = [
    dict(zip(SAMPLE_FIELDS, row, strict=True))
    for row in (
        ("subtree-s01", "4813722", "2ygkcb", "Liverpool vs Manchester United"),
        ("subtree-s02", "4813492", "2ynv4k", "Everton vs Manchester United"),
    )
]
PRIORITY_PATHS = "props.pageProps.fallback props.pageProps.fallback.*.data props.pageProps.fallback.*.matchDetails props.pageProps.fallback.*.content props.pageProps.fallback.*.header props.pageProps.fallback.*.general props.pageProps.*.match props.pageProps.*.matchData props.pageProps.*.matchDetails props.pageProps.*.content".split()
KEY_PRESENCE_KEYS = "matchId match_id id header general content matchFacts stats lineup events teams homeTeam awayTeam status fixture score tournament league".split()
NEGATIVE_CONFIG_KEYS = set(
    "countrycodes language translations translation static config locale locales messages ssr fetchingleaguedata".split()
)
SAFETY_FALSE_FLAG_NAMES = "full_body_read_performed full_html_saved raw_response_body_saved html_body_saved full_next_data_saved candidate_subtree_value_saved raw_json_write_performed db_read_performed db_write_performed production_db_write_performed fotmob_raw_match_payloads_write_performed raw_match_data_write_performed feature_parse_performed scheduler_enabled raw_write_ready_marked browser_automation_performed captcha_bypass_performed proxy_rotation_performed"
SAFETY_FALSE_FLAGS = dict.fromkeys(SAFETY_FALSE_FLAG_NAMES.split(), False)
REVIEW_FALSE_FLAGS = "full_body_read_performed full_html_saved raw_response_body_saved html_body_saved full_next_data_saved candidate_subtree_value_saved raw_json_write_performed db_write_performed scheduler_enabled feature_parse_performed browser_automation_performed captcha_bypass_performed proxy_rotation_performed".split()
RESULT_FALSE_FLAGS = "full_html_saved raw_response_body_saved html_body_saved full_next_data_saved candidate_subtree_value_saved raw_json_write_performed db_write_performed raw_write_eligible".split()
REQUIRED_ARGS = "subtree-plan-manifest hydration-validation-manifest seed-manifest output-manifest report review-report decision-report run-id".split()
TYPE_NAME_BY_PY = dict(
    pair.split(":")
    for pair in "NoneType:null bool:bool dict:dict list:list int:int float:float str:str".split()
)


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"{label} missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_type(value: Any) -> str:
    return TYPE_NAME_BY_PY.get(type(value).__name__, type(value).__name__)


def _split_team_names(team_pair: str) -> list[str]:
    return [part.strip() for part in team_pair.split(" vs ") if part.strip()]


def _is_target_value(value: Any, target_match_id: str) -> bool:
    if isinstance(value, (int, float)) and str(int(value)) == target_match_id:
        return True
    return isinstance(value, str) and value == target_match_id


def _contains_target_value(value: Any, target_match_id: str) -> bool:
    if _is_target_value(value, target_match_id):
        return True
    return isinstance(value, str) and target_match_id in value


def _priority_rank(path: str) -> int:
    if path == "props.pageProps.fallback" or path.startswith("props.pageProps.fallback."):
        return 0
    for idx, pattern in enumerate(PRIORITY_PATHS, start=1):
        if "*" not in pattern and path == pattern:
            return idx
        if "*" in pattern:
            prefix, suffix = pattern.split("*", 1)
            if path.startswith(prefix) and path.endswith(suffix):
                return idx
    return 99


def _classify_score(score: int) -> str:
    if score >= 10:
        return "match_detail_subtree_strong_candidate"
    if score >= 6:
        return "match_detail_subtree_weak_candidate"
    if score >= 3:
        return "partial_match_detail_subtree"
    return "generic_or_irrelevant_subtree"


def _estimate_size(value: Any, depth: int = 0) -> int:
    if depth > MAX_SUBTREE_SCAN_DEPTH:
        return 0
    if isinstance(value, dict):
        return sum(len(str(k)) + _estimate_size(v, depth + 1) for k, v in value.items())
    if isinstance(value, list):
        return sum(_estimate_size(v, depth + 1) for v in value)
    if value is None:
        return 0
    return len(str(value))


def _walk_nodes(value: Any, path: str, max_depth: int, depth: int = 0):
    yield path, value, depth
    if depth >= max_depth:
        return
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk_nodes(child, f"{path}.{key}", max_depth, depth + 1)
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            yield from _walk_nodes(child, f"{path}[{idx}]", max_depth, depth + 1)


def collect_key_path_metadata(
    value: Any,
    max_depth: int,
    max_paths: int = MAX_KEY_PATHS_RECORDED,
) -> list[dict[str, str]]:
    paths: list[dict[str, str]] = []
    for path, node, depth in _walk_nodes(value, ROOT_PATH, max_depth):
        paths.append({"path": path, "type": _safe_type(node), "depth": str(depth)})
        if len(paths) >= max_paths:
            break
    return paths


def _empty_presence() -> dict[str, bool]:
    return dict.fromkeys(KEY_PRESENCE_KEYS, False)


def analyze_subtree(value: Any, path: str, target_match_id: str, team_pair: str) -> dict[str, Any]:
    presence = _empty_presence()
    team_names = _split_team_names(team_pair)
    target_seen = False
    key_value_target_seen = False
    team_names_seen = False
    config_key_hits = 0
    total_key_count = 0

    stack: list[tuple[Any, int, str | None]] = [(value, 0, None)]
    while stack:
        node, depth, parent_key = stack.pop()
        if depth > MAX_SUBTREE_SCAN_DEPTH:
            continue
        if isinstance(node, dict):
            for key, child in node.items():
                total_key_count += 1
                key_text = str(key)
                key_lower = key_text.lower()
                normalized = key_lower.replace("_", "")
                if key_lower in NEGATIVE_CONFIG_KEYS:
                    config_key_hits += 1
                for presence_key in presence:
                    if key_text == presence_key or normalized == presence_key.lower().replace(
                        "_", ""
                    ):
                        presence[presence_key] = True
                if (
                    normalized in {"matchid", "id"}
                    or key_lower == "match_id"
                    or key_lower.endswith("id")
                ) and _is_target_value(child, target_match_id):
                    key_value_target_seen = True
                if _contains_target_value(child, target_match_id):
                    target_seen = True
                if any(team.lower() in key_lower for team in team_names):
                    team_names_seen = True
                stack.append((child, depth + 1, key_text))
        elif isinstance(node, list):
            for child in node:
                stack.append((child, depth + 1, parent_key))
        else:
            if _contains_target_value(node, target_match_id):
                target_seen = True
            if isinstance(node, str) and any(team.lower() in node.lower() for team in team_names):
                team_names_seen = True

    score = 0
    if target_seen:
        score += 5
    if key_value_target_seen:
        score += 4
    for key in ("header", "general", "content"):
        if presence[key]:
            score += 3
    for key in ("matchFacts", "stats", "lineup", "events"):
        if presence[key]:
            score += 2
    if presence["teams"] or presence["homeTeam"] or presence["awayTeam"]:
        score += 2
    for key in ("status", "fixture", "score"):
        if presence[key]:
            score += 1
    if presence["tournament"] or presence["league"]:
        score += 1

    lower_path = path.lower()
    config_path = any(key in lower_path for key in NEGATIVE_CONFIG_KEYS)
    config_only = total_key_count > 0 and config_key_hits == total_key_count
    if config_only:
        score -= 3
    if not target_seen and not team_names_seen:
        score -= 5
    if config_path or (config_key_hits > 0 and not any(presence.values())):
        score -= 5
    if config_path:
        score = min(score, -5)
    if (
        path == ROOT_PATH
        and isinstance(value, dict)
        and {"fallback", "translations"}.issubset({str(key) for key in value})
        and not target_seen
        and not team_names_seen
    ):
        score = min(score, -6)

    return {
        "path": path,
        "type": _safe_type(value),
        "score": score,
        "state": _classify_score(score),
        "key_presence": presence,
        "target_match_id_seen": target_seen,
        "team_names_seen": team_names_seen,
        "estimated_size": _estimate_size(value),
        "priority_rank": _priority_rank(path),
    }


def scan_page_props(
    page_props: dict[str, Any],
    target_match_id: str,
    team_pair: str,
    max_depth: int,
) -> dict[str, Any]:
    key_paths = collect_key_path_metadata(page_props, max_depth)
    candidates = []
    for path, node, _depth in _walk_nodes(page_props, ROOT_PATH, max_depth):
        if isinstance(node, (dict, list)):
            candidates.append(analyze_subtree(node, path, target_match_id, team_pair))
    ranked_candidates = [item for item in candidates if item["path"] != ROOT_PATH] or candidates
    ranked_candidates.sort(key=lambda item: (-item["score"], item["priority_rank"], item["path"]))
    recorded_candidates = ranked_candidates[:MAX_CANDIDATE_PATHS_RECORDED]
    best = recorded_candidates[0] if recorded_candidates else None
    return {
        "key_paths": key_paths,
        "candidate_paths": recorded_candidates,
        "best_candidate": best,
        "target_match_id_seen": any(item["target_match_id_seen"] for item in candidates),
        "team_names_seen": any(item["team_names_seen"] for item in candidates),
    }


def extract_next_data_page_props(
    text: str,
) -> tuple[bool, bool, bool, dict[str, Any] | None, str | None]:
    match = re.search(
        r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(?P<data>.*?)</script>',
        text,
        re.DOTALL,
    )
    if not match:
        return False, False, False, None, "next_data_marker_not_found"
    try:
        data = json.loads(match.group("data"))
    except json.JSONDecodeError:
        return True, True, False, None, "next_data_json_parse_failed"
    page_props = None
    if isinstance(data, dict):
        props = data.get("props")
        if isinstance(props, dict) and isinstance(props.get("pageProps"), dict):
            page_props = props["pageProps"]
    return True, True, True, page_props, None


def _base_result(sample: dict[str, str], max_body_bytes: int) -> dict[str, Any]:
    url = FULL_ROUTE_TEMPLATE.format(
        route_code=sample["route_code"],
        match_id=sample["match_id"],
    )
    return {
        "extraction_id": sample["extraction_id"],
        "match_id": sample["match_id"],
        "route_code": sample["route_code"],
        "team_pair": sample["team_pair"],
        "url_redacted": url,
        "network_performed": False,
        "status_code": None,
        "content_type": None,
        "content_length": None,
        "bytes_read": 0,
        "body_truncated": False,
        "next_data_parse_ok": False,
        "pageProps_present": False,
        "root_path_found": False,
        "fallback_present": False,
        "target_match_id_seen": False,
        "team_names_seen": False,
        "key_paths_recorded_count": 0,
        "candidate_paths_recorded_count": 0,
        "best_candidate_path": None,
        "best_candidate_score": 0,
        "best_candidate_state": "controlled_subtree_extraction_planned",
        "best_candidate_key_presence": _empty_presence(),
        "candidate_estimated_size": 0,
        "validation_state": "controlled_subtree_extraction_planned",
        "stop_reason": "dry_run_no_network",
        "elapsed_ms": 0,
        "max_body_bytes": max_body_bytes,
        "full_html_saved": False,
        "raw_response_body_saved": False,
        "html_body_saved": False,
        "full_next_data_saved": False,
        "candidate_subtree_value_saved": False,
        "raw_json_write_performed": False,
        "db_write_performed": False,
        "raw_write_eligible": False,
    }


def probe_and_extract(
    sample: dict[str, str], max_body_bytes: int, max_depth: int
) -> dict[str, Any]:
    result = _base_result(sample, max_body_bytes)
    result["network_performed"] = True
    result["stop_reason"] = None
    url = result["url_redacted"]
    started = time.monotonic()
    body = None
    text = None
    try:
        req = request.Request(url, method="GET")
        req.add_header("User-Agent", "FootballPrediction/1.0 (subtree-extraction; bounded-read)")
        req.add_header("Accept", "text/html,application/xhtml+xml")
        resp = request.urlopen(req, timeout=TIMEOUT_SECONDS)
        result["status_code"] = resp.status
        result["content_type"] = resp.headers.get("Content-Type", "")
        content_length = resp.headers.get("Content-Length")
        if content_length:
            try:
                result["content_length"] = int(content_length)
            except ValueError:
                result["content_length"] = None
        if resp.status in (403, 429):
            result["validation_state"] = "subtree_route_blocked"
            result["best_candidate_state"] = "subtree_route_blocked"
            result["stop_reason"] = f"blocked_{resp.status}"
            return result
        if resp.status == 404:
            result["validation_state"] = "subtree_route_invalid"
            result["best_candidate_state"] = "subtree_route_invalid"
            result["stop_reason"] = "invalid_404"
            return result
        if "html" not in (result["content_type"] or "").lower():
            result["validation_state"] = "subtree_not_html"
            result["best_candidate_state"] = "subtree_not_html"
            result["stop_reason"] = "not_html"
            return result
        body = resp.read(max_body_bytes)
        result["bytes_read"] = len(body)
        if result["content_length"] and result["content_length"] > result["bytes_read"]:
            result["body_truncated"] = True
        if result["bytes_read"] >= max_body_bytes and result["body_truncated"]:
            result["stop_reason"] = "bounded_body_read_reached_limit"
        text = body.decode("utf-8", errors="replace")
        marker, attempted, parse_ok, page_props, stop_reason = extract_next_data_page_props(text)
        result["next_data_parse_ok"] = marker and attempted and parse_ok
        result["pageProps_present"] = isinstance(page_props, dict)
        result["root_path_found"] = isinstance(page_props, dict)
        if stop_reason:
            result["validation_state"] = "subtree_next_data_parse_failed"
            result["best_candidate_state"] = "subtree_next_data_parse_failed"
            result["stop_reason"] = stop_reason
            return result
        if not isinstance(page_props, dict):
            result["validation_state"] = "subtree_next_data_parse_failed"
            result["best_candidate_state"] = "subtree_next_data_parse_failed"
            result["stop_reason"] = "pageProps_missing"
            return result
        result["fallback_present"] = isinstance(page_props.get("fallback"), dict)
        scan = scan_page_props(
            page_props,
            result["match_id"],
            result["team_pair"],
            max_depth,
        )
        result["key_paths_recorded_count"] = len(scan["key_paths"])
        result["candidate_paths_recorded_count"] = len(scan["candidate_paths"])
        result["target_match_id_seen"] = bool(scan["target_match_id_seen"])
        result["team_names_seen"] = bool(scan["team_names_seen"])
        best = scan["best_candidate"]
        if best:
            result["best_candidate_path"] = best["path"]
            result["best_candidate_score"] = best["score"]
            result["best_candidate_state"] = best["state"]
            result["best_candidate_key_presence"] = best["key_presence"]
            result["candidate_estimated_size"] = best["estimated_size"]
            result["validation_state"] = best["state"]
        else:
            result["best_candidate_state"] = "no_match_detail_subtree_found"
            result["validation_state"] = "no_match_detail_subtree_found"
        if result["stop_reason"] is None:
            result["stop_reason"] = "completed"
    except error.HTTPError as exc:
        result["status_code"] = exc.code
        if exc.code in (403, 429):
            result["validation_state"] = "subtree_route_blocked"
            result["best_candidate_state"] = "subtree_route_blocked"
            result["stop_reason"] = f"blocked_{exc.code}"
        elif exc.code == 404:
            result["validation_state"] = "subtree_route_invalid"
            result["best_candidate_state"] = "subtree_route_invalid"
            result["stop_reason"] = "invalid_404"
        else:
            result["validation_state"] = "subtree_route_invalid"
            result["best_candidate_state"] = "subtree_route_invalid"
            result["stop_reason"] = f"http_error_{exc.code}"
    except Exception as exc:
        result["validation_state"] = "subtree_route_invalid"
        result["best_candidate_state"] = "subtree_route_invalid"
        result["stop_reason"] = f"error_{type(exc).__name__}"
    finally:
        result["elapsed_ms"] = int((time.monotonic() - started) * 1000)
        del body
        del text
        try:
            resp.close()
        except Exception:
            pass
    return result


def _result_counts(results: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "fallback_present_count": sum(1 for r in results if r.get("fallback_present")),
        "target_match_id_seen_count": sum(1 for r in results if r.get("target_match_id_seen")),
        "strong_candidate_count": sum(
            1
            for r in results
            if r.get("best_candidate_state") == "match_detail_subtree_strong_candidate"
        ),
        "weak_candidate_count": sum(
            1
            for r in results
            if r.get("best_candidate_state") == "match_detail_subtree_weak_candidate"
        ),
        "partial_candidate_count": sum(
            1 for r in results if r.get("best_candidate_state") == "partial_match_detail_subtree"
        ),
        "generic_or_irrelevant_count": sum(
            1 for r in results if r.get("best_candidate_state") == "generic_or_irrelevant_subtree"
        ),
        "blocked_count": sum(
            1 for r in results if r.get("validation_state") == "subtree_route_blocked"
        ),
        "invalid_count": sum(
            1 for r in results if r.get("validation_state") == "subtree_route_invalid"
        ),
        "not_html_count": sum(
            1 for r in results if r.get("validation_state") == "subtree_not_html"
        ),
    }


def recommended_next_phase(allow_network_probe: bool, counts: dict[str, int]) -> str:
    if not allow_network_probe:
        return DRY_RUN_NEXT
    if counts["strong_candidate_count"] >= 1 and counts["target_match_id_seen_count"] >= 1:
        return STRONG_NEXT
    if counts["weak_candidate_count"] >= 1:
        return WEAK_NEXT
    return REVIEW_NEXT


def build_manifest(
    run_id: str,
    mode: str,
    max_samples: int,
    max_body_bytes: int,
    max_depth: int,
    max_network_requests: int,
    allow_network_probe: bool,
    results: list[dict[str, Any]],
    subtree_plan: dict[str, Any],
) -> dict[str, Any]:
    plan = subtree_plan.get("subtree_extraction_plan", {})
    counts = _result_counts(results)
    summary = {
        "allow_network_probe": allow_network_probe,
        "max_network_requests": max_network_requests,
        "network_requests_attempted": sum(1 for r in results if r.get("network_performed")),
        **counts,
    }
    rec = recommended_next_phase(allow_network_probe, counts)
    best = max(
        results,
        key=lambda r: int(r.get("best_candidate_score") or 0),
        default={},
    )
    safety = {
        "network_fetch_performed": summary["network_requests_attempted"] > 0,
        "bounded_body_read_performed": any(r.get("bytes_read", 0) > 0 for r in results),
        **SAFETY_FALSE_FLAGS,
    }
    return {
        "schema_version": SCHEMA,
        "lifecycle": "current-state",
        "phase": PHASE,
        "run_id": run_id,
        "generated_at": _utc_now(),
        "mode": mode,
        "inherited_subtree_plan": {
            "root_path": plan.get("root_path", ROOT_PATH),
            "priority_path_count": len(plan.get("priority_paths", PRIORITY_PATHS)),
            "scoring_rule_count": len(plan.get("scoring_rules", [])) or 17,
            "max_subtree_scan_depth": max_depth,
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
        },
        "extraction_selection": {
            "max_samples": max_samples,
            "selected_sample_count": len(results),
            "selected_match_ids": [r["match_id"] for r in results],
            "selected_route_codes": [r["route_code"] for r in results],
            "route_template": ROUTE_TEMPLATE,
            "max_body_bytes": max_body_bytes,
            "max_subtree_scan_depth": max_depth,
        },
        "extraction_results": results,
        "extraction_summary": summary,
        "match_detail_subtree_decision": {
            "viable_candidate_count": counts["strong_candidate_count"]
            + counts["weak_candidate_count"]
            + counts["partial_candidate_count"],
            "best_candidate_path": best.get("best_candidate_path"),
            "best_candidate_score": best.get("best_candidate_score", 0),
            "best_candidate_state": best.get(
                "best_candidate_state", "no_match_detail_subtree_found"
            ),
            "recommended_next_action": rec,
        },
        "raw_write_readiness": {
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
            "raw_write_blocked_until_json_validated": True,
            "subtree_validation_required": True,
        },
        "safety": safety,
        "embedded_review": {
            "controlled_subtree_extraction_status": "pass",
            "review_report_path": "",
        },
        "recommended_next_phase": rec,
    }


def _bullet_map(mapping: dict[str, Any]) -> str:
    return "".join(f"- {key}: {value}\n" for key, value in mapping.items())


def write_report(path: Path, manifest: dict[str, Any]) -> None:
    samples = "".join(
        f"- {r['match_id']} / {r['route_code']} / {r['team_pair']}\n"
        for r in manifest["extraction_results"]
    )
    scans = "".join(
        f"- {r['extraction_id']}: fallback={r['fallback_present']}, target_mid={r['target_match_id_seen']}, best={r['best_candidate_path']}, score={r['best_candidate_score']}, state={r['best_candidate_state']}\n"
        for r in manifest["extraction_results"]
    )
    text = (
        "<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->\n"
        "# FotMob Controlled Match Detail Subtree Extraction No Write\n\n"
        f"- lifecycle: current-state\n- phase: {PHASE}\n- run_id: {manifest['run_id']}\n- mode: {manifest['mode']}\n\n"
        "## 当前阶段背景\n\n- #1446 已确认 `/matches/{route_code}/{match_id}` 是当前唯一主路线。\n- 本阶段只保存结构 metadata，不保存完整 HTML、完整 NEXT_DATA、candidate subtree value 或 raw JSON。\n- 本阶段不写 DB，也不进入 L2 raw harvesting。\n\n"
        f"## #1446 Subtree Extraction Plan Inheritance\n\n{_bullet_map(manifest['inherited_subtree_plan'])}\n"
        f"## Selected Extraction Samples\n\n{samples}\n## Route Template\n\n`{ROUTE_TEMPLATE}`\n\n"
        f"## Bounded Body Summary\n\n{_bullet_map(manifest['extraction_summary'])}\n## Subtree Scan Summary\n\n{scans}\n"
        f"## Candidate Decision\n\n{_bullet_map(manifest['match_detail_subtree_decision'])}\n## Raw Write Readiness Gate\n\n{_bullet_map(manifest['raw_write_readiness'])}\n"
        f"## No-Write Safety Review\n\n{_bullet_map(manifest['safety'])}\n## Remaining Blockers\n\n- candidate subtree 尚未做下一阶段 validation no-write。\n- json_validated_count 仍为 0，raw_write_eligible_count 仍为 0。\n- 即使发现 strong candidate，下一阶段也只是 subtree validation no-write，不是直接入库。\n\n## Recommended Next Phase\n\n- **{manifest['recommended_next_phase']}**\n"
    )
    path.write_text(text, encoding="utf-8")


def write_decision_report(path: Path, manifest: dict[str, Any]) -> None:
    lines = [
        "<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->\n",
        "# FotMob Match Detail Subtree Candidate Decision\n\n",
        "- lifecycle: current-state\n",
        f"- phase: {PHASE} decision\n",
        f"- run_id: {manifest['run_id']}\n\n",
    ]
    for result in manifest["extraction_results"]:
        presence = result.get("best_candidate_key_presence", {})
        key_hits = [key for key, value in presence.items() if value]
        lines.append(
            f"## {result['extraction_id']} — {result['match_id']}\n\n- props.pageProps found: {result['root_path_found']}\n- fallback found: {result['fallback_present']}\n- target match_id seen: {result['target_match_id_seen']}\n- team names seen: {result['team_names_seen']}\n- best_candidate_path: {result['best_candidate_path']}\n- best_candidate_score: {result['best_candidate_score']}\n- best_candidate_state: {result['best_candidate_state']}\n- key presence: {', '.join(key_hits) if key_hits else 'none'}\n\n"
        )
    lines.append("## Why Raw Write Is Still Blocked\n\n")
    lines.append("- 本阶段只识别 subtree path/score metadata，没有验证 JSON schema。\n")
    lines.append("- 未保存 candidate subtree value，也未保存 raw JSON。\n")
    lines.append("- json_validated_count=0 且 raw_write_eligible_count=0。\n\n")
    lines.append("## Recommended Next Phase\n\n")
    lines.append(f"- **{manifest['recommended_next_phase']}**\n")
    path.write_text("".join(lines), encoding="utf-8")


def write_review_report(path: Path, manifest: dict[str, Any]) -> bool:
    selection = manifest["extraction_selection"]
    summary = manifest["extraction_summary"]
    safety = manifest["safety"]
    readiness = manifest["raw_write_readiness"]
    rec = manifest["recommended_next_phase"]
    checks = []
    checks.append(
        (
            "#1446 subtree plan inherited",
            manifest["inherited_subtree_plan"]["root_path"] == ROOT_PATH,
        )
    )
    checks.append(
        (
            "route template restricted to /matches/{route_code}/{match_id}",
            selection["route_template"] == ROUTE_TEMPLATE,
        )
    )
    checks.append(("max_samples<=2", selection["selected_sample_count"] <= MAX_SAMPLES))
    checks.append(
        ("max_network_requests<=2", summary["max_network_requests"] <= MAX_NETWORK_REQUESTS)
    )
    checks.append(("max_body_bytes<=524288", selection["max_body_bytes"] <= MAX_BODY_BYTES))
    checks.append(
        ("max_subtree_scan_depth<=8", selection["max_subtree_scan_depth"] <= MAX_SUBTREE_SCAN_DEPTH)
    )
    checks.extend((f"{flag}=false", safety[flag] is False) for flag in REVIEW_FALSE_FLAGS)
    checks.extend(
        (
            ("json_validated_count=0", readiness["json_validated_count"] == 0),
            ("raw_write_eligible_count=0", readiness["raw_write_eligible_count"] == 0),
            ("recommended next phase safe", "RAW-WRITE" not in rec and "RAW-JSON-WRITE" not in rec),
            ("no direct raw write recommendation", "DIRECT" not in rec),
        )
    )
    ok = all(item[1] for item in checks)
    lines = [
        "<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->\n",
        "# FotMob Controlled Match Detail Subtree Extraction No Write Review\n\n",
        "- lifecycle: current-state\n",
        f"- phase: {PHASE} review\n",
        f"- run_id: {manifest['run_id']}\n\n",
    ]
    for name, passed in checks:
        lines.append(f"- [{'pass' if passed else 'FAIL'}] {name}\n")
    lines.append(f"\n## Overall: {'pass' if ok else 'blocked'}\n")
    path.write_text("".join(lines), encoding="utf-8")
    return ok


def run_extraction(args: argparse.Namespace) -> dict[str, Any]:
    subtree_plan = _load_json(Path(args.subtree_plan_manifest), "subtree plan manifest")
    _load_json(Path(args.hydration_validation_manifest), "hydration validation manifest")
    _load_json(Path(args.seed_manifest), "seed manifest")
    selected = SAMPLES[: args.max_samples]
    results: list[dict[str, Any]] = []
    for sample in selected:
        attempted = sum(1 for item in results if item.get("network_performed"))
        if args.allow_network_probe and attempted < args.max_network_requests:
            results.append(
                probe_and_extract(sample, args.max_body_bytes, args.max_subtree_scan_depth)
            )
        else:
            results.append(_base_result(sample, args.max_body_bytes))
    mode = (
        "controlled_subtree_extraction_no_write"
        if args.allow_network_probe
        else "dry_run_subtree_extraction_plan_only"
    )
    return build_manifest(
        args.run_id,
        mode,
        args.max_samples,
        args.max_body_bytes,
        args.max_subtree_scan_depth,
        args.max_network_requests,
        args.allow_network_probe,
        results,
        subtree_plan,
    )


def _validate_args(args: argparse.Namespace) -> int:
    limits = {
        "max_samples": MAX_SAMPLES,
        "max_network_requests": MAX_NETWORK_REQUESTS,
        "max_body_bytes": MAX_BODY_BYTES,
        "max_subtree_scan_depth": MAX_SUBTREE_SCAN_DEPTH,
    }
    for name, limit in limits.items():
        if getattr(args, name) > limit:
            print(f"ERROR: {name.replace('_', '-')} > {limit}", file=sys.stderr)
            return 1
    return 0


def _validate_safety(manifest: dict[str, Any]) -> int:
    safety = manifest["safety"]
    for flag in SAFETY_FALSE_FLAGS:
        if safety.get(flag) is not False:
            print(f"ERROR: safety flag is not false: {flag}", file=sys.stderr)
            return 1
    readiness = manifest["raw_write_readiness"]
    if readiness["json_validated_count"] > 0:
        print("ERROR: json_validated_count > 0", file=sys.stderr)
        return 1
    if readiness["raw_write_eligible_count"] > 0:
        print("ERROR: raw_write_eligible_count > 0", file=sys.stderr)
        return 1
    for result in manifest["extraction_results"]:
        for flag in RESULT_FALSE_FLAGS:
            if result.get(flag) is not False:
                print(f"ERROR: result safety flag is not false: {flag}", file=sys.stderr)
                return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Controlled FotMob subtree extraction no-write")
    for arg in REQUIRED_ARGS:
        parser.add_argument(f"--{arg}", required=True)
    parser.add_argument("--max-samples", type=int, default=MAX_SAMPLES)
    parser.add_argument("--max-body-bytes", type=int, default=MAX_BODY_BYTES)
    parser.add_argument("--max-subtree-scan-depth", type=int, default=MAX_SUBTREE_SCAN_DEPTH)
    parser.add_argument("--max-network-requests", type=int, default=MAX_NETWORK_REQUESTS)
    parser.add_argument("--allow-network-probe", action="store_true", default=False)
    args = parser.parse_args()

    arg_error = _validate_args(args)
    if arg_error:
        return arg_error

    manifest = run_extraction(args)
    Path(args.output_manifest).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    manifest["embedded_review"]["review_report_path"] = str(Path(args.review_report))
    review_ok = write_review_report(Path(args.review_report), manifest)
    manifest["embedded_review"]["controlled_subtree_extraction_status"] = (
        "pass" if review_ok else "blocked"
    )
    Path(args.output_manifest).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_report(Path(args.report), manifest)
    write_decision_report(Path(args.decision_report), manifest)
    safety_error = _validate_safety(manifest)
    if safety_error:
        return safety_error
    if not review_ok:
        print("ERROR: embedded review blocked", file=sys.stderr)
        return 1
    summary = manifest["extraction_summary"]
    print(
        f"SUCCESS: mode={manifest['mode']} requests={summary['network_requests_attempted']} strong={summary['strong_candidate_count']} weak={summary['weak_candidate_count']} target_mid={summary['target_match_id_seen_count']} next={manifest['recommended_next_phase']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
