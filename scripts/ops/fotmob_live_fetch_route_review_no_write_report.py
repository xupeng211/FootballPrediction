#!/usr/bin/env python3
"""Report builders for the FotMob live fetch route review phase.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-LIVE-FETCH-ROUTE-REVIEW-NO-WRITE

Extracted from fotmob_live_fetch_route_review_no_write.py to keep the main
script under the 800-line gatekeeper limit.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

# Constants replicated here to avoid circular imports.
PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-LIVE-FETCH-ROUTE-REVIEW-NO-WRITE"
NEXT_RAW_WRITE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-RAW-JSON-DEV-WRITE"

# ---------------------------------------------------------------------------
# report builders
# ---------------------------------------------------------------------------


def build_report(manifest: dict[str, Any]) -> str:
    review = manifest["route_review"]
    prev = manifest["reviewed_previous_phase"]
    candidates = manifest.get("route_candidates", [])
    probe_results = manifest.get("probe_results", [])

    candidate_rows = [
        (
            f"| {c['candidate_label']} | {c['candidate_source']} | "
            f"{c['candidate_confidence']} | {str(c.get('probe_attempted', False)).lower()} | "
            f"{c.get('status_code') or 'none'} | "
            f"{c.get('content_type') or 'none'} | "
            f"{str(c.get('json_parse_ok', False)).lower()} | "
            f"{c.get('error_category') or 'none'} |"
        )
        for c in candidates
    ]
    if not candidate_rows:
        candidate_rows = [
            "| none (no reliable route candidate) | n/a | n/a | false | none | none | false | none |"
        ]

    probe_rows = [
        (
            f"| {r.get('candidate_label', 'unknown')} | "
            f"{str(r.get('probe_attempted', False)).lower()} | "
            f"{r.get('status_code') or 'none'} | "
            f"{r.get('content_type') or 'none'} | "
            f"{r.get('response_size_bytes', 0)} | "
            f"{str(r.get('json_parse_ok', False)).lower()} | "
            f"{r.get('error_category') or 'none'} | "
            f"{str(r.get('stop_policy_triggered', False)).lower()} |"
        )
        for r in probe_results
    ]
    if not probe_rows:
        probe_rows = [
            "| none (no probe executed) | false | none | none | 0 | false | none | false |"
        ]

    return "\n".join(
        [
            "<!-- markdownlint-disable MD013 -->",
            "",
            "# FotMob Live Fetch Route Review No Write",
            "",
            "- lifecycle: current-state",
            f"- phase: {PHASE}",
            f"- run_id: {manifest['run_id']}",
            "- purpose: 审查 FotMob live fetch route 和 source identity，诊断 #1432 失败原因",
            f"- explicit_allow_flag_present: {str(manifest['explicit_allow_flag_present']).lower()}",
            "- DB target source: db_backed_registry (read-only)",
            "- 本阶段没有保存 raw response body",
            "- 本阶段没有写 raw JSON",
            "- 本阶段没有写 DB",
            "- 本阶段没有 parser",
            "- 本阶段没有 scheduler",
            "- 本阶段不是大规模采集",
            "",
            "## Background",
            "",
            "- PR #1432 执行了首次受控 FotMob live fetch probe",
            "- 结果：attempted=1, completed=1, stopped_early=true",
            f"- stop_reason={prev['previous_stop_reason']}",
            f"- status_code={prev['previous_status_code']}",
            f"- content_type={prev['previous_content_type']}",
            f"- json_parse_ok_count={prev['previous_json_parse_ok_count']}",
            "- 目标 URL: `https://www.fotmob.com/matches/fixture-eng-friend-001` 返回 HTML 404",
            "- 本阶段审查失败原因，不做 raw write",
            "",
            "## Why #1432 Failed",
            "",
            "### 直接原因",
            "",
            "- `source_match_id = fixture-eng-friend-001` 是 synthetic/fixture-only 占位符",
            "- URL 拼接结果 `https://www.fotmob.com/matches/fixture-eng-friend-001` 指向不存在的页面",
            "- FotMob 使用数字 match ID（如 `4830473`）或 hash_id 对（如 `2o4ahb#4830473`）",
            "- `fixture-eng-friend-001` 不符合任何已知 FotMob match ID 格式",
            "",
            "### 根本原因",
            "",
            "- Registry seed phase 明确声明所有 source_match_id 是 `synthetic/fixture-only`",
            "- 所有 source_entity_id（team/competition）也是 `fixture-*` 占位符",
            "- target_selection_db_dry_run 虽然正确选择了 targets，但 targets 持有的是 fixture ID",
            "- 在 fixture ID 被替换为真实 FotMob ID 之前，任何 live fetch 都会得到 404",
            "",
            "## Source Identity Review",
            "",
            f"- total_identities: {manifest['source_identity_analysis']['total']}",
            f"- fixture_like_count: {manifest['source_identity_analysis']['fixture_like_count']}",
            f"- numeric_count: {manifest['source_identity_analysis']['numeric_count']}",
            f"- quality: {manifest['source_identity_analysis']['quality']}",
            "",
            "### 分析",
            "",
            "- 所有 source_identity 的 source_entity_id 均以 `fixture-` 开头",
            "- 例如: `fixture-mun-01` (Manchester United), `fixture-comp-epl` (Premier League)",
            "- FotMob 真实 team ID 和 competition ID 是数字（如 team_id=9825, league_id=47）",
            "- 当前 fixture ID 只能用于 DB schema 验证和 pipeline 演练",
            "- **不能** 用于真实 FotMob live fetch",
            "",
            "## Route Candidate Review",
            "",
            f"- reliable_route_candidate_found: {str(review['reliable_route_candidate_found']).lower()}",
            f"- match_id_discovery_required: {str(review['match_id_discovery_required']).lower()}",
            f"- endpoint_route_realism: {review['endpoint_route_realism']}",
            "",
            "### Known FotMob Route Patterns (from historical ADG data)",
            "",
            "| pattern | example | status |",
            "|---------|---------|--------|",
            "| match detail page (SSR) | `/matches/{hash}/{match_id}` | ADG46 confirmed 200 with `__NEXT_DATA__` |",
            "| match detail page (hash) | `/matches/{hash}#{match_id}` | redirect pattern |",
            "| match detail API | `/api/matchDetails?matchId={id}` | ADG44 returned 404 |",
            "| league fixtures API | `/api/leagues?id={id}` | ADG44 returned 404 |",
            "| team page | `/teams?id={id}` | not tested |",
            "| date fixtures | `/fixtures?date={date}` | HTML only |",
            "",
            "### Current Route Candidates",
            "",
            "| candidate | source | confidence | probed | status_code | content_type | json_ok | error |",
            "|-----------|--------|------------|--------|-------------|--------------|---------|-------|",
            *candidate_rows,
            "",
            "## Match ID Discovery Gap",
            "",
            "### 缺失的能力",
            "",
            "- **Match ID Discovery**：从 FotMob 公开页面发现真实 match ID 的能力",
            "- 当前 pipeline 在设计上假设已有真实 source_match_id",
            "- Registry seed 明确只是 metadata/calendar 验证，不含真实 FotMob ID",
            "- 需要新增 match ID discovery 阶段来填充真实 source_match_id",
            "",
            "### 建议的 Discovery 方法（设计，不执行）",
            "",
            "1. **Team Calendar Discovery**",
            "   - 从 FotMob team page 获取该队的 fixtures 列表",
            "   - 从 `__NEXT_DATA__` 或 API 中提取真实 match ID",
            "2. **League Fixtures Discovery**",
            "   - 从 FotMob league page 获取 fixtures 列表",
            "   - 提取 match ID 和 route_hash_pair",
            "3. **Date Fixtures Discovery**",
            "   - 从 FotMob date fixtures page 获取当日所有比赛",
            "4. **Source Identity Validation States**",
            "   - unknown → candidate → route_validated → json_validated → blocked → invalid",
            "",
            "## Optional Probe Result",
            "",
            "| candidate | attempted | status_code | content_type | size | json_ok | error | stop |",
            "|-----------|-----------|-------------|--------------|------|---------|-------|------|",
            *probe_rows,
            "",
            "## Stop Policy Result",
            "",
            f"- route_review_status: {review['route_review_status']}",
            f"- detailed_reason: {review.get('detailed_reason', 'none')}",
            f"- network_fetch_performed: {str(manifest['safety']['network_fetch_performed']).lower()}",
            f"- probes_attempted: {manifest['request_budget']['used']}",
            f"- probes_remaining: {manifest['request_budget']['remaining']}",
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
            "- 所有 source_match_id 仍然是 fixture-like 占位符",
            "- 没有真实 FotMob match ID",
            "- 没有 match ID discovery 能力",
            "- 没有 route validation confirmation",
            "- 尚未授权 raw JSON dev write",
            "- 尚未启用 scheduler",
            "- 尚未实现 parser/features/training/prediction",
            "",
            "## Recommended Next Phase",
            "",
            f"- {manifest['recommended_next_phase']}",
            "- 若 source_match_id 仍为 fixture-like，推荐 match ID discovery design no-write",
            "- 不得在 fixture ID 状态下直接 raw write",
            "- 若后续获得真实 match ID，仍需先做极小规模 controlled route validation no-write",
            "",
        ]
    )


def build_review_report(manifest: dict[str, Any]) -> str:
    status = manifest["embedded_review"]["live_fetch_route_review_no_write_status"]
    review = manifest["route_review"]
    prev = manifest["reviewed_previous_phase"]
    safety = manifest["safety"]

    checks = [
        (
            "previous partial result correctly interpreted",
            "pass"
            if prev["previous_stop_reason"] == "unexpected_html"
            and prev["previous_status_code"] == 404
            else "fail",
        ),
        ("no raw write", "pass" if not safety["raw_json_write_performed"] else "blocked"),
        ("no DB write", "pass" if not manifest["db_write_performed"] else "blocked"),
        ("no raw body persistence", "pass" if not safety["raw_response_body_saved"] else "blocked"),
        (
            "route candidate source explained",
            "pass" if review["reliable_route_candidate_found"] is not None else "fail",
        ),
        (
            "match id discovery gap documented",
            "pass" if review["match_id_discovery_required"] else "fail",
        ),
        (
            "no browser automation",
            "pass" if not safety["browser_automation_performed"] else "blocked",
        ),
        ("no proxy rotation", "pass" if not safety["proxy_rotation_performed"] else "blocked"),
        ("no captcha bypass", "pass" if not safety["captcha_bypass_performed"] else "blocked"),
        (
            "rate limits respected",
            "pass"
            if manifest["rate_limit"]["concurrency"] == 1
            and manifest["rate_limit"]["max_attempts_per_route"] == 1
            and manifest["rate_limit"]["sleep_seconds"] >= 5
            else "fail",
        ),
        (
            "recommended next phase safe",
            "pass"
            if manifest["recommended_next_phase"] != NEXT_RAW_WRITE
            or (manifest.get("json_parse_ok_count", 0) > 0 and status == "pass")
            else "blocked_unsafe_raw_write_recommendation",
        ),
    ]

    check_rows = "\n".join(f"- {label}: {result}" for label, result in checks)

    return "\n".join(
        [
            "<!-- markdownlint-disable MD013 -->",
            "",
            "# FotMob Live Fetch Route Review No Write Embedded Review",
            "",
            "- lifecycle: current-state",
            f"- reviewed_phase: {PHASE}",
            f"- status: {status}",
            f"- run_id: {manifest['run_id']}",
            "",
            "## Checks",
            "",
            check_rows,
            "",
            "## Result Review",
            "",
            f"- previous_stop_reason: {prev['previous_stop_reason']} (expected: unexpected_html)",
            f"- previous_status_code: {prev['previous_status_code']} (expected: 404)",
            f"- source_identity_quality: {review['source_identity_quality']}",
            f"- source_match_id_realism: {review['source_match_id_realism']}",
            f"- likely_failure_reason: {review['likely_failure_reason']}",
            f"- reliable_route_candidate_found: {review['reliable_route_candidate_found']}",
            f"- match_id_discovery_required: {review['match_id_discovery_required']}",
            f"- route_review_status: {review['route_review_status']}",
            f"- network_fetch_performed: {safety['network_fetch_performed']}",
            f"- probes_used: {manifest['request_budget']['used']}",
            f"- probes_remaining: {manifest['request_budget']['remaining']}",
            "",
            "## Recommended Next Phase",
            "",
            f"- {manifest['recommended_next_phase']}",
            "- 只有在 JSON-like route 被稳定验证后，才允许推荐 raw write",
            "- 当前 fixture-like source identity 状态不支持 raw write",
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


def blocked_manifest(args: argparse.Namespace, reason: str, explicit: bool) -> dict[str, Any]:
    from fotmob_live_fetch_route_review_no_write import (
        build_manifest,  # lazy to avoid circular import
    )

    return build_manifest(
        args,
        db_env="not_checked",
        guard_reasons=[],
        explicit=explicit,
        db_read=False,
        previous_manifest={},
        identity_analysis={
            "quality": "unknown",
            "total_identities": 0,
            "fixture_like_count": 0,
            "numeric_count": 0,
        },
        target_analysis={
            "match_id_realism": "unknown",
            "total_match_targets": 0,
            "fixture_like_source_match_ids": 0,
            "numeric_source_match_ids": 0,
            "has_source_url_count": 0,
        },
        candidates=[],
        probe_results=[],
        stop_reason=reason,
        blocked=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FotMob live fetch route review no write")
    parser.add_argument(
        "--input-live-probe-manifest",
        default="docs/_manifests/fotmob_one_day_live_fetch_no_raw_write_manifest.json",
    )
    parser.add_argument(
        "--input-target-selection-manifest",
        default="docs/_manifests/fotmob_target_selection_db_dry_run_manifest.json",
    )
    parser.add_argument(
        "--output-manifest",
        default="docs/_manifests/fotmob_live_fetch_route_review_no_write_manifest.json",
    )
    parser.add_argument(
        "--report",
        default="docs/_reports/FOTMOB_LIVE_FETCH_ROUTE_REVIEW_NO_WRITE.md",
    )
    parser.add_argument(
        "--review-report",
        default="docs/_reports/FOTMOB_LIVE_FETCH_ROUTE_REVIEW_NO_WRITE_REVIEW.md",
    )
    parser.add_argument("--max-route-candidates", type=int, default=3)
    parser.add_argument("--max-live-probe-requests", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=int, default=15)
    parser.add_argument("--sleep-seconds", type=int, default=5)
    parser.add_argument("--run-id", default="fotmob_live_fetch_route_review_no_write_v1")
    parser.add_argument("--require-dev-db", action="store_true", default=True)
    return parser.parse_args()
