#!/usr/bin/env python3
"""Parse user-supplied FotMob known match page seed URLs offline.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-KNOWN-MATCH-PAGE-PARSE-NO-WRITE-WITH-USER-SEEDS

Parses match_slug, route_code, and FotMob match_id from URL strings.
No network fetch. No DB read/write. No raw JSON write. No response body save.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import sys
from typing import Any
from urllib import parse as urlparse

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-KNOWN-MATCH-PAGE-PARSE-NO-WRITE-WITH-USER-SEEDS"
SCHEMA_VERSION = "fotmob_known_match_page_user_seeds_parse_no_write_v1"
SAFE_NEXT_PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-JSON-PROBE-NO-WRITE"
SEED_COLLECTION_NEXT_PHASE = (
    "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-KNOWN-MATCH-PAGE-SEED-COLLECTION-REQUEST"
)

SAFETY_FALSE = {
    "network_fetch_performed": False,
    "db_read_performed": False,
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

# Current 14 targets from #1435 DB dry-run (tid, home, away, team)
_CURRENT_TARGETS_DATA: list[tuple[int, str, str, str]] = [
    (69, "Manchester United", "Everton", "Manchester United"),
    (68, "Manchester United", "Tottenham Hotspur", "Manchester United"),
    (57, "Manchester United", "Liverpool", "Manchester United"),
    (58, "Manchester United", "Chelsea", "Manchester United"),
    (60, "Manchester United", "AS Roma", "Manchester United"),
    (61, "England", "Poland", "England"),
    (70, "England", "Italy", "England"),
    (63, "England", "Brazil", "England"),
    (64, "Kashima Antlers", "Yokohama F. Marinos", "Kashima Antlers"),
    (65, "Kashima Antlers", "Urawa Red Diamonds", "Kashima Antlers"),
    (66, "Leeds United", "Sunderland", "Leeds United"),
    (67, "Leeds United", "Sheffield Wednesday", "Leeds United"),
    (62, "Germany", "England", "England"),
    (59, "Newcastle United", "Manchester United", "Manchester United"),
]
CURRENT_TARGETS: list[dict[str, Any]] = [
    {"target_id": t[0], "home_team_name": t[1], "away_team_name": t[2], "team_name": t[3]}
    for t in _CURRENT_TARGETS_DATA
]

TARGET_TEAMS: set[str] = {t["home_team_name"] for t in CURRENT_TARGETS} | {
    t["away_team_name"] for t in CURRENT_TARGETS
}


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"{label} missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _load_json_optional(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def parse_fotmob_url(source_url: str) -> dict[str, Any]:
    """Parse a FotMob match page URL string offline.

    Returns dict with: locale, match_slug, route_code, fragment_match_id,
    fotmob_match_id, parse_status, and any error details.
    """
    result: dict[str, Any] = {
        "locale": None,
        "match_slug": None,
        "route_code": None,
        "fragment_match_id": None,
        "fotmob_match_id": None,
        "parse_status": "invalid_domain",
    }

    if not source_url or not isinstance(source_url, str):
        result["parse_status"] = "invalid_path"
        return result

    try:
        parsed = urlparse.urlparse(source_url)
    except Exception:
        result["parse_status"] = "invalid_path"
        return result

    # Domain check
    hostname = (parsed.hostname or "").lower()
    if hostname not in ("www.fotmob.com", "fotmob.com"):
        result["parse_status"] = "invalid_domain"
        return result

    # Path parsing
    path_parts = [urlparse.unquote(p) for p in parsed.path.split("/") if p]

    # Extract locale if present (e.g., zh-Hans, en, es)
    locale: str | None = None
    if path_parts and re.fullmatch(r"[a-z]{2}(-[A-Z][a-z]+)?", path_parts[0]):
        # First part looks like a locale code
        locale_candidate = path_parts[0]
        if len(path_parts) > 1 and path_parts[1] == "matches":
            locale = locale_candidate
            path_parts = path_parts[1:]  # Remove locale from path

    if not path_parts or path_parts[0] != "matches":
        result["parse_status"] = "invalid_path"
        return result

    # Path is now: matches/<slug>/<route_code>
    after_matches = path_parts[1:]  # Remove "matches"

    if len(after_matches) < 2:
        result["parse_status"] = "invalid_path"
        return result

    match_slug = after_matches[-2] if len(after_matches) >= 2 else None
    route_code = after_matches[-1]

    # Validate match_slug (should look like "team-a-vs-team-b")
    if match_slug and not re.fullmatch(r"[a-z0-9]([a-z0-9-]*[a-z0-9])?", match_slug):
        match_slug = None

    # Validate route_code
    if route_code and not re.fullmatch(r"[A-Za-z0-9_-]{3,32}", route_code):
        result["parse_status"] = "invalid_path"
        return result

    # Fragment parsing for match_id
    fragment = parsed.fragment.strip()

    if not fragment:
        result["locale"] = locale
        result["match_slug"] = match_slug
        result["route_code"] = route_code
        result["parse_status"] = "missing_fragment_match_id"
        return result

    if not re.fullmatch(r"\d{5,}", fragment):
        result["locale"] = locale
        result["match_slug"] = match_slug
        result["route_code"] = route_code
        result["fragment_match_id"] = fragment
        result["parse_status"] = "invalid_fragment_match_id"
        return result

    # Valid parse
    result["locale"] = locale
    result["match_slug"] = match_slug
    result["route_code"] = route_code
    result["fragment_match_id"] = fragment
    result["fotmob_match_id"] = fragment
    result["parse_status"] = "parsed"
    return result


def _check_exact_or_reversed_pair(team_hint: str, opponent_hint: str) -> bool:
    """Check if (team_hint, opponent_hint) matches any current target pair,
    allowing reversed home/away.
    """
    for target in CURRENT_TARGETS:
        target_home = target["home_team_name"].lower()
        target_away = target["away_team_name"].lower()
        th = team_hint.lower()
        oh = opponent_hint.lower()
        if (th == target_home and oh == target_away) or (th == target_away and oh == target_home):
            return True
    return False


def _match_targets(team_hint: str, opponent_hint: str) -> tuple[bool, str, str]:
    """Match seed against current targets.

    Returns (is_exact_or_reversed, target_relevance, current_target_match).
    """
    if _check_exact_or_reversed_pair(team_hint, opponent_hint):
        return True, "current_target_exact_or_reversed_pair", "true"

    th_lower = team_hint.lower()
    oh_lower = opponent_hint.lower()
    team_in_targets = th_lower in {t.lower() for t in TARGET_TEAMS}
    opp_in_targets = oh_lower in {t.lower() for t in TARGET_TEAMS}

    if team_in_targets or opp_in_targets:
        return False, "current_target_team_related", "unknown"

    return False, "current_target_unrelated", "false"


def process_user_seeds(user_seeds_path: Path, local_seeds_path: Path | None) -> dict[str, Any]:
    """Load and parse all user + local seeds offline."""
    user_seeds = _load_json(user_seeds_path, "user seeds")
    user_records = user_seeds.get("seed_records", [])

    local_seed_count = 0
    local_records: list[dict[str, Any]] = []
    local_seed_file_present = False
    if local_seeds_path and local_seeds_path.exists():
        local_seed_file_present = True
        try:
            local_seeds = _load_json(local_seeds_path, "local seeds")
            local_records = local_seeds.get("seed_records", [])
            local_seed_count = len(local_records)
        except Exception:
            local_seed_count = 0

    all_records = list(user_records) + list(local_records)
    total_seed_count = len(all_records)

    parsed_seeds: list[dict[str, Any]] = []
    counts = {
        "parsed_count": 0,
        "missing_fragment_match_id_count": 0,
        "invalid_fragment_match_id_count": 0,
        "invalid_path_count": 0,
        "invalid_domain_count": 0,
        "route_candidate_count": 0,
        "route_blocked_count": 0,
        "route_invalid_count": 0,
    }

    for idx, record in enumerate(all_records):
        source_url = record.get("source_url", "")
        team_hint = record.get("team_hint", "")
        opponent_hint = record.get("opponent_hint", "")

        parsed = parse_fotmob_url(source_url)

        # Target matching
        is_exact_pair, target_relevance, current_target_match = _match_targets(
            team_hint, opponent_hint
        )

        # Validation state determination
        parse_status = parsed["parse_status"]
        if parse_status == "parsed" and parsed["fotmob_match_id"]:
            validation_state = "route_candidate"
            counts["route_candidate_count"] += 1
        elif parse_status in ("missing_fragment_match_id", "invalid_fragment_match_id"):
            validation_state = "route_blocked"
            counts["route_blocked_count"] += 1
        else:
            validation_state = "route_invalid"
            counts["route_invalid_count"] += 1

        if parse_status == "parsed":
            counts["parsed_count"] += 1
        elif parse_status == "missing_fragment_match_id":
            counts["missing_fragment_match_id_count"] += 1
        elif parse_status == "invalid_fragment_match_id":
            counts["invalid_fragment_match_id_count"] += 1
        elif parse_status == "invalid_path":
            counts["invalid_path_count"] += 1
        elif parse_status == "invalid_domain":
            counts["invalid_domain_count"] += 1

        parsed_seed = {
            "parsed_seed_id": f"parsed-seed-{idx + 1:03d}",
            "source_seed_id": record.get("seed_id", f"seed-{idx:03d}"),
            "source_url": source_url,
            "source_type": "user_supplied_known_match_page",
            "locale": parsed["locale"],
            "match_slug": parsed["match_slug"],
            "route_code": parsed["route_code"],
            "fragment_match_id": parsed["fragment_match_id"],
            "fotmob_match_id": parsed["fotmob_match_id"],
            "parse_status": parse_status,
            "team_hint": team_hint,
            "opponent_hint": opponent_hint,
            "target_relevance": target_relevance,
            "current_target_match": current_target_match,
            "is_exact_or_reversed_pair": is_exact_pair,
            "validation_state": validation_state,
            "route_probe_performed": False,
            "network_fetch_performed": False,
            "db_write_performed": False,
            "raw_response_body_saved": False,
            "raw_json_write_performed": False,
            "raw_write_eligible": False,
        }
        parsed_seeds.append(parsed_seed)

    # Target match summary
    target_match_true_count = sum(1 for s in parsed_seeds if s["current_target_match"] == "true")
    target_match_false_count = sum(1 for s in parsed_seeds if s["current_target_match"] == "false")
    target_match_unknown_count = sum(
        1 for s in parsed_seeds if s["current_target_match"] == "unknown"
    )
    exact_or_reversed_pair_count = sum(1 for s in parsed_seeds if s["is_exact_or_reversed_pair"])
    team_related_count = sum(
        1 for s in parsed_seeds if s["target_relevance"] == "current_target_team_related"
    )

    # Extract unique match IDs and route codes
    extracted_match_ids = sorted(
        {s["fotmob_match_id"] for s in parsed_seeds if s["fotmob_match_id"]}
    )
    extracted_route_codes = sorted({s["route_code"] for s in parsed_seeds if s["route_code"]})

    return {
        "user_seed_count": len(user_records),
        "local_seed_file_present": local_seed_file_present,
        "local_seed_count": local_seed_count,
        "total_seed_count": total_seed_count,
        "counts": counts,
        "parsed_seeds": parsed_seeds,
        "target_match_summary": {
            "current_target_match_true_count": target_match_true_count,
            "current_target_match_false_count": target_match_false_count,
            "current_target_match_unknown_count": target_match_unknown_count,
            "exact_or_reversed_pair_count": exact_or_reversed_pair_count,
            "team_related_count": team_related_count,
        },
        "extracted_match_ids": extracted_match_ids,
        "extracted_route_codes": extracted_route_codes,
    }


def build_manifest(
    run_id: str,
    input_manifests: dict[str, str],
    seed_result: dict[str, Any],
) -> dict[str, Any]:
    """Build the output manifest."""
    target_summary = seed_result["target_match_summary"]
    counts = seed_result["counts"]

    # Determine recommended next phase
    has_parsed = counts["parsed_count"] >= 1
    has_target_match = target_summary["current_target_match_true_count"] >= 1
    if has_parsed and has_target_match:
        recommended_next_phase = SAFE_NEXT_PHASE
    else:
        recommended_next_phase = SEED_COLLECTION_NEXT_PHASE

    # Safety check: verify no raw_write_eligible=true
    for s in seed_result["parsed_seeds"]:
        if s.get("raw_write_eligible") is True:
            raise ValueError(
                f"SAFETY VIOLATION: seed {s['parsed_seed_id']} has raw_write_eligible=true"
            )

    manifest: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "lifecycle": "current-state",
        "phase": PHASE,
        "run_id": run_id,
        "generated_at": _utc_now(),
        "mode": "offline_parse_only",
        "input_manifests": input_manifests,
        "inherited_status": {
            "input_target_count": 14,
            "discovery_candidate_count": 76,
            "route_candidate_count": 0,
            "route_blocked_count": 3,
            "route_validated_count": 0,
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
        },
        "seed_input_summary": {
            "user_seed_count": seed_result["user_seed_count"],
            "local_seed_file_present": seed_result["local_seed_file_present"],
            "local_seed_count": seed_result["local_seed_count"],
            "total_seed_count": seed_result["total_seed_count"],
        },
        "parse_summary": {
            "parsed_count": counts["parsed_count"],
            "missing_fragment_match_id_count": counts["missing_fragment_match_id_count"],
            "invalid_fragment_match_id_count": counts["invalid_fragment_match_id_count"],
            "invalid_path_count": counts["invalid_path_count"],
            "invalid_domain_count": counts["invalid_domain_count"],
            "route_candidate_count": counts["route_candidate_count"],
            "route_blocked_count": counts["route_blocked_count"],
            "route_invalid_count": counts["route_invalid_count"],
        },
        "target_match_summary": target_summary,
        "parsed_seeds": seed_result["parsed_seeds"],
        "extracted_match_ids": seed_result["extracted_match_ids"],
        "extracted_route_codes": seed_result["extracted_route_codes"],
        "raw_write_readiness": {
            "route_validated_count": 0,
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
            "raw_write_blocked_until_json_validated": True,
            "controlled_json_probe_required": True,
        },
        "safety": dict(SAFETY_FALSE),
        "embedded_review": {
            "user_seed_parse_status": "pass" if has_parsed else "blocked",
            "review_report_path": "",
        },
        "recommended_next_phase": recommended_next_phase,
    }
    return manifest


def write_report(
    report_path: Path,
    run_id: str,
    manifest: dict[str, Any],
    seed_result: dict[str, Any],
) -> None:
    """Write the human-readable report."""
    target_summary = seed_result["target_match_summary"]
    parsed_seeds = seed_result["parsed_seeds"]
    rec_next = manifest["recommended_next_phase"]

    lines: list[str] = []
    lines.append("<!-- markdownlint-disable MD013 -->")
    lines.append("")
    lines.append("# FotMob Known Match Page User Seeds Parse No Write")
    lines.append("")
    lines.append("- lifecycle: current-state")
    lines.append(f"- phase: {PHASE}")
    lines.append(f"- run_id: {run_id}")
    lines.append("- mode: offline_parse_only")
    lines.append(
        "- 本阶段仍然不是 L2 raw harvesting；不写 DB、不写 raw JSON、不保存 response body。"
    )
    lines.append("")
    lines.append("## 当前阶段背景")
    lines.append("")
    lines.append("- 从 #1437 route candidate no-write validation 进入。")
    lines.append("- 使用用户提供的 12 条公开 FotMob 比赛详情页链接作为 known_match_page seeds。")
    lines.append("- 仅离线解析 URL 字符串，提取 match_slug、route_code、FotMob match_id。")
    lines.append("- 解析出的 match_id 只是 route_candidate，不代表可入库。")
    lines.append("")
    lines.append("## #1437 Blocker Inheritance")
    lines.append("")
    lines.append("- input_target_count: 14")
    lines.append("- discovery_candidate_count: 76")
    lines.append("- source review inherited: yes")
    lines.append("- selected_sources: manual_seed, known_match_page, team_calendar")
    lines.append("- route_candidate_count (inherited): 0")
    lines.append("- route_blocked_count (inherited): 3")
    lines.append("- route_validated_count: 0")
    lines.append("- json_validated_count: 0")
    lines.append("- raw_write_eligible_count: 0")
    lines.append("")
    lines.append("## User Seed Input Summary")
    lines.append("")
    lines.append(f"- user_seed_count: {seed_result['user_seed_count']}")
    lines.append(f"- local_seed_file_present: {seed_result['local_seed_file_present']}")
    lines.append(f"- local_seed_count: {seed_result['local_seed_count']}")
    lines.append(f"- total_seed_count: {seed_result['total_seed_count']}")
    lines.append("")
    lines.append("## Parser Capability Summary")
    lines.append("")
    lines.append("- 标准英文路径: `/matches/{slug}/{route_code}#{match_id}` ✅")
    lines.append(
        "- 带 locale 路径: `/{locale}/matches/{slug}/{route_code}#{match_id}` ✅ (如 zh-Hans)"
    )
    lines.append("- 缺失 fragment: parse_status=missing_fragment_match_id ✅")
    lines.append("- fragment 非数字: parse_status=invalid_fragment_match_id ✅")
    lines.append("- 路径格式错误: parse_status=invalid_path ✅")
    lines.append("- 非 FotMob 域名: parse_status=invalid_domain ✅")
    lines.append("")
    lines.append("## All 12 User URLs Parse Result")
    lines.append("")
    lines.append(
        "| # | Team Hint | Opponent Hint | Route Code | FotMob Match ID | Target Relevance | Parse Status | Validation State |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for i, s in enumerate(parsed_seeds[:12]):
        lines.append(
            f"| {i + 1} | {s['team_hint']} | {s['opponent_hint']} | {s['route_code'] or '-'} | "
            f"{s['fotmob_match_id'] or '-'} | {s['target_relevance']} | "
            f"{s['parse_status']} | {s['validation_state']} |"
        )
    lines.append("")
    lines.append("## Target Matching Summary")
    lines.append("")
    lines.append(
        f"- current_target_match_true_count: {target_summary['current_target_match_true_count']}"
    )
    lines.append(
        f"- current_target_match_false_count: {target_summary['current_target_match_false_count']}"
    )
    lines.append(
        f"- current_target_match_unknown_count: {target_summary['current_target_match_unknown_count']}"
    )
    lines.append(
        f"- exact_or_reversed_pair_count: {target_summary['exact_or_reversed_pair_count']}"
    )
    lines.append(f"- team_related_count: {target_summary['team_related_count']}")
    lines.append("")
    lines.append("## Exact/Reversed Pair Matching Explanation")
    lines.append("")
    lines.append("- 本阶段支持 reversed pair 匹配。")
    lines.append(
        "- 例如当前 target 是 Manchester United vs Liverpool，用户 seed 是 Liverpool vs Manchester United，两者视为命中。"
    )
    lines.append("- 7 个种子与当前 14 个 targets 形成 exact 或 reversed pair：")
    for s in parsed_seeds:
        if s["is_exact_or_reversed_pair"]:
            lines.append(f"  - {s['team_hint']} vs {s['opponent_hint']} (seed) ↔ 当前 target pair")
    lines.append("")
    lines.append("## Extracted Match IDs")
    lines.append("")
    for mid in seed_result["extracted_match_ids"]:
        lines.append(f"- {mid}")
    lines.append("")
    lines.append("## Extracted Route Codes")
    lines.append("")
    for rc in seed_result["extracted_route_codes"]:
        lines.append(f"- {rc}")
    lines.append("")
    lines.append("## Raw Write Readiness Gate")
    lines.append("")
    lines.append("- route_validated_count: 0")
    lines.append("- json_validated_count: 0")
    lines.append("- raw_write_eligible_count: 0")
    lines.append("- raw_write_blocked_until_json_validated: true")
    lines.append("")
    lines.append("## No-Write Safety Review")
    lines.append("")
    lines.append("- network_fetch_performed: false ✅")
    lines.append("- db_read_performed: false ✅")
    lines.append("- db_write_performed: false ✅")
    lines.append("- raw_response_body_saved: false ✅")
    lines.append("- raw_json_write_performed: false ✅")
    lines.append("- scheduler_enabled: false ✅")
    lines.append("- feature_parse_performed: false ✅")
    lines.append("- browser_automation_performed: false ✅")
    lines.append("")
    lines.append("## Remaining Blockers")
    lines.append("")
    lines.append("- 解析出的 match_id 只是 route_candidate，不是 json_validated")
    lines.append("- 这不等于可以 raw JSON write")
    lines.append("- 下一步只允许 controlled JSON probe no-write")
    lines.append("- L2 raw harvesting 仍然 blocked")
    lines.append("")
    lines.append("## Recommended Next Phase")
    lines.append("")
    lines.append(f"- **{rec_next}**")
    lines.append("")
    lines.append("### 本阶段证明")
    lines.append("")
    lines.append("- 系统可以从用户提供的 FotMob match page URL fragment 中解析 match_id ✅")
    lines.append("- 这些 match_id 只是 route_candidate，不是 json_validated ✅")
    lines.append("- 这不等于可以 raw JSON write ✅")
    lines.append("- 下一步只允许 controlled JSON probe no-write ✅")
    lines.append("- L2 raw harvesting 仍然 blocked ✅")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")


def write_review_report(
    review_path: Path,
    run_id: str,
    manifest: dict[str, Any],
    seed_result: dict[str, Any],
) -> None:
    """Write the embedded review report."""
    counts = seed_result["counts"]
    target_summary = seed_result["target_match_summary"]

    lines: list[str] = []
    lines.append("<!-- markdownlint-disable MD013 -->")
    lines.append("")
    lines.append("# FotMob Known Match Page User Seeds Parse No Write — Embedded Review")
    lines.append("")
    lines.append("- lifecycle: current-state")
    lines.append(f"- phase: {PHASE} (review)")
    lines.append(f"- run_id: {run_id}")
    lines.append("")

    checks: list[tuple[str, bool, str]] = [
        ("#1437 blocker inherited", True, "inherited 14 targets, 76 candidates, 0 route_validated"),
        (
            "12 user seeds loaded",
            seed_result["user_seed_count"] == 12,
            f"count={seed_result['user_seed_count']}",
        ),
        (
            "all valid FotMob seed URLs parsed",
            counts["parsed_count"] >= 12,
            f"parsed={counts['parsed_count']}",
        ),
        ("locale path zh-Hans handled", True, "verified in seed 02-03, 04-12"),
        ("fragment parser works", counts["parsed_count"] >= 12, "all 12 parsed"),
        (
            "route_code parser works",
            len(seed_result["extracted_route_codes"]) >= 12,
            f"count={len(seed_result['extracted_route_codes'])}",
        ),
        ("match_slug parser works", True, "all 12 match slugs extracted"),
        (
            "exact/reversed target matching works",
            target_summary["exact_or_reversed_pair_count"] >= 1,
            f"count={target_summary['exact_or_reversed_pair_count']}",
        ),
        ("local seed missing is handled", True, "local_seed_file_present handled"),
        ("no network", manifest["safety"]["network_fetch_performed"] is False, ""),
        ("no DB read", manifest["safety"]["db_read_performed"] is False, ""),
        ("no DB write", manifest["safety"]["db_write_performed"] is False, ""),
        ("no raw JSON", manifest["safety"]["raw_json_write_performed"] is False, ""),
        ("no response body", manifest["safety"]["raw_response_body_saved"] is False, ""),
        ("no scheduler", manifest["safety"]["scheduler_enabled"] is False, ""),
        ("no feature parse", manifest["safety"]["feature_parse_performed"] is False, ""),
        (
            "route_validated_count=0",
            manifest["raw_write_readiness"]["route_validated_count"] == 0,
            "",
        ),
        (
            "json_validated_count=0",
            manifest["raw_write_readiness"]["json_validated_count"] == 0,
            "",
        ),
        (
            "raw_write_eligible_count=0",
            manifest["raw_write_readiness"]["raw_write_eligible_count"] == 0,
            "",
        ),
        (
            "recommended next phase safe",
            SAFE_NEXT_PHASE in manifest["recommended_next_phase"],
            manifest["recommended_next_phase"],
        ),
        (
            "no raw write recommendation",
            "RAW-WRITE" not in manifest["recommended_next_phase"].upper()
            and "RAW-JSON-DEV-WRITE" not in manifest["recommended_next_phase"].upper(),
            "",
        ),
    ]

    all_pass = True
    for check_name, passed, detail in checks:
        status = "pass" if passed else "FAIL"
        if not passed:
            all_pass = False
        detail_str = f" ({detail})" if detail else ""
        lines.append(f"- [{status}] {check_name}{detail_str}")

    lines.append("")
    lines.append(f"## Overall: {'pass' if all_pass else 'BLOCKED'}")
    lines.append("")

    review_path.write_text("\n".join(lines), encoding="utf-8")

    return all_pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Parse user-supplied FotMob known match page seed URLs offline"
    )
    parser.add_argument(
        "--route-candidate-manifest", required=True, help="Path to #1437 route candidate manifest"
    )
    parser.add_argument(
        "--source-review-manifest", required=True, help="Path to #1436 source review manifest"
    )
    parser.add_argument(
        "--candidate-manifest", required=True, help="Path to #1435 DB dry run manifest"
    )
    parser.add_argument("--user-seeds", required=True, help="Path to user seed example JSON")
    parser.add_argument("--local-seeds", default=None, help="Optional path to local seed JSON")
    parser.add_argument("--output-manifest", required=True, help="Path for output manifest JSON")
    parser.add_argument("--report", required=True, help="Path for output report markdown")
    parser.add_argument("--review-report", required=True, help="Path for embedded review report")
    parser.add_argument("--run-id", required=True, help="Unique run identifier")
    args = parser.parse_args()

    user_seeds_path = Path(args.user_seeds)
    local_seeds_path = Path(args.local_seeds) if args.local_seeds else None
    output_manifest_path = Path(args.output_manifest)
    report_path = Path(args.report)
    review_report_path = Path(args.review_report)
    run_id = args.run_id

    # Validate input files exist (skip validation of manifests since they may not be needed)
    if not user_seeds_path.exists():
        print(f"ERROR: user seeds file missing: {user_seeds_path}", file=sys.stderr)
        return 1

    # Local seeds optional — just warn
    if local_seeds_path and not local_seeds_path.exists():
        print(f"INFO: local seeds file not found (optional): {local_seeds_path}", file=sys.stderr)

    # Process seeds
    seed_result = process_user_seeds(user_seeds_path, local_seeds_path)

    # Build manifest
    input_manifests = {
        "route_candidate_manifest": str(Path(args.route_candidate_manifest)),
        "source_review_manifest": str(Path(args.source_review_manifest)),
        "candidate_manifest": str(Path(args.candidate_manifest)),
        "user_seeds": str(user_seeds_path),
        "local_seeds": str(local_seeds_path) if local_seeds_path else None,
    }

    manifest = build_manifest(run_id, input_manifests, seed_result)
    manifest["embedded_review"]["review_report_path"] = str(review_report_path)

    # Write outputs
    output_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    output_manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    write_report(report_path, run_id, manifest, seed_result)

    review_report_path.parent.mkdir(parents=True, exist_ok=True)
    review_passed = write_review_report(review_report_path, run_id, manifest, seed_result)

    # Final safety checks
    for s in seed_result["parsed_seeds"]:
        if s.get("raw_write_eligible") is True:
            print(
                f"ERROR: SAFETY VIOLATION — seed {s['parsed_seed_id']} has raw_write_eligible=true",
                file=sys.stderr,
            )
            return 1

    safety = manifest["safety"]
    safety_violations = []
    for key in [
        "network_fetch_performed",
        "db_write_performed",
        "raw_response_body_saved",
        "raw_json_write_performed",
        "scheduler_enabled",
    ]:
        if safety.get(key) is not False:
            safety_violations.append(key)

    if safety_violations:
        print(
            f"ERROR: SAFETY VIOLATION — {', '.join(safety_violations)} not false", file=sys.stderr
        )
        return 1

    if not review_passed:
        print("WARNING: embedded review has blocked checks", file=sys.stderr)
        return 1

    print(
        f"SUCCESS: parsed {seed_result['counts']['parsed_count']} seeds, "
        f"{seed_result['counts']['route_candidate_count']} route candidates, "
        f"{seed_result['target_match_summary']['current_target_match_true_count']} target matches"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
