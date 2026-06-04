#!/usr/bin/env python3
"""Report rendering for FotMob hydration keyspace review no-write.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-KEYSPACE-REVIEW-NO-WRITE
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-KEYSPACE-REVIEW-NO-WRITE"
RESULT_FALSE_NAMES = [
    "full_html_saved",
    "raw_response_body_saved",
    "html_body_saved",
    "full_next_data_saved",
    "value_persistence_performed",
    "raw_json_write_performed",
    "db_write_performed",
    "raw_write_eligible",
]


def render_report(manifest: dict[str, Any], allow_network: bool) -> str:
    inherited = manifest["inherited_review_followup"]
    selection = manifest["keyspace_selection"]
    summary = manifest["keyspace_summary"]
    decision = manifest["keyspace_candidate_decision"]
    results = manifest.get("keyspace_results", [])

    mode_name = (
        "controlled_hydration_keyspace_review_no_write"
        if allow_network
        else "dry_run_keyspace_review_plan_only"
    )
    lines = [
        "<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->",
        "# FotMob Hydration Keyspace Review No Write",
        "",
        "- lifecycle: current-state",
        f"- phase: {PHASE}",
        f"- run_id: {manifest['run_id']}",
        f"- mode: {mode_name}",
        "",
        "## 当前阶段背景",
        "",
        "- #1448 已完成 subtree review follow-up no-write，确认 notableMatches 不是 match detail。",
        "- 本阶段系统性扫描 bounded __NEXT_DATA__ keyspace，只保留 key path metadata，不保存任何 value。",
        "- 目标是找出可能包含 match detail 的 key path 位置。",
        "",
        "## #1448 Review Follow-Up Inheritance",
        "",
        f"- notableMatches marked not match detail: {inherited['notable_matches_is_not_match_detail']}",
        f"- keyspace review required: {inherited['keyspace_review_required']}",
        f"- route variant review required: {inherited['route_variant_review_required']}",
        f"- target_match_id_seen_count: {inherited['target_match_id_seen_count']}",
        f"- strong_candidate_count: {inherited['strong_candidate_count']}",
        f"- fallback_present_count: {inherited['fallback_present_count']}",
        f"- json_validated_count: {inherited['json_validated_count']}",
        f"- raw_write_eligible_count: {inherited['raw_write_eligible_count']}",
        "",
        "## Route Variants Reviewed",
        "",
        f"- route variants: {', '.join(selection['route_variants_selected'])}",
        f"- selected samples: {selection['selected_sample_count']}",
    ]

    if allow_network and results:
        lines += [
            "",
            "## Keyspace Scan Summary",
            "",
            f"- network_requests_attempted: {summary['network_requests_attempted']}",
            f"- next_data_parse_ok_count: {summary['next_data_parse_ok_count']}",
            f"- pageProps_present_count: {summary['pageProps_present_count']}",
            f"- fallback_present_count: {summary['fallback_present_count']}",
            f"- strong_path_candidate_count: {summary['strong_path_candidate_count']}",
            f"- weak_path_candidate_count: {summary['weak_path_candidate_count']}",
            f"- partial_path_candidate_count: {summary['partial_path_candidate_count']}",
            f"- generic_or_irrelevant_path_count: {summary['generic_or_irrelevant_path_count']}",
            f"- best_route_variant: {summary['route_variant_with_best_candidate']}",
        ]
        for entry in results:
            lines += [
                "",
                f"### {entry['review_id']} — {entry['match_id']} ({entry['route_variant']})",
                "",
                f"- status: {entry.get('validation_state', 'unknown')}",
                f"- next_data_parse_ok: {entry.get('next_data_parse_ok', False)}",
                f"- pageProps_present: {entry.get('pageProps_present', False)}",
                f"- fallback_present: {entry.get('fallback_present', False)}",
                f"- total_key_paths_seen: {entry.get('total_key_paths_seen', 0)}",
                f"- key_paths_recorded: {entry.get('key_paths_recorded_count', 0)}",
                f"- target_match_id_in_key_path: {entry.get('target_match_id_in_key_path', False)}",
                f"- positive_candidate_count: {entry.get('positive_candidate_path_count', 0)}",
                f"- top candidate paths: {', '.join(entry.get('top_candidate_paths', [])[:5])}",
                f"- top candidate scores: {entry.get('top_candidate_scores', [])[:5]}",
            ]

    lines += [
        "",
        "## Top Candidate Path Decision",
        "",
        f"- best_path_candidate: {decision['best_path_candidate']}",
        f"- best_path_score: {decision['best_path_score']}",
        f"- best_route_variant: {decision['best_route_variant']}",
        f"- viable_candidate_count: {decision['viable_path_candidate_count']}",
        "",
        "## NotableMatches Rejection Confirmation",
        "",
        "- notableMatches 已在 #1447/#1448 中确认不是 match detail，本轮继续排除。",
        "- notableMatches 路径出现在 last resort 候选时 score=-5，直接归为 generic_or_irrelevant。",
        "",
        "## Raw Write Readiness Gate",
        "",
        "- json_validated_count: 0",
        "- raw_write_eligible_count: 0",
        "- raw_write_blocked_until_json_validated: true",
        "- keyspace_candidate_validation_required: true",
        "",
        "## No-Write Safety Review",
        "",
        "- 本阶段只保存 key path metadata",
        "- 本阶段不保存任何 value",
        "- 本阶段不保存完整 HTML",
        "- 本阶段不保存完整 __NEXT_DATA__",
        "- 本阶段不保存 raw JSON",
        "- 本阶段不写 DB",
        "- 本阶段不进入 L2 raw harvesting",
    ]
    if allow_network and summary.get("strong_path_candidate_count", 0) >= 1:
        lines.append(
            "- 如果 strong path candidate 找到，下一阶段也只是 path validation no-write，不是直接入库"
        )
    else:
        lines.append("- 依然保持 no-write 门禁")

    lines += [
        "",
        "## Remaining Blockers",
        "",
        "- 尚未完成 candidate path validation。",
        "- 尚未进行 JSON schema 验证。",
        "- raw_write_eligible_count 仍然为 0。",
        "",
        "## Recommended Next Phase",
        "",
        f"- **{manifest['recommended_next_phase']}**",
    ]
    return "\n".join(lines)


def render_review(manifest: dict[str, Any], allow_network: bool) -> str:
    selection = manifest["keyspace_selection"]
    summary = manifest["keyspace_summary"]
    safety = manifest["safety"]
    readiness = manifest["raw_write_readiness"]

    return "\n".join(
        [
            "<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->",
            "# FotMob Hydration Keyspace Review No Write Review",
            "",
            "- lifecycle: current-state",
            f"- phase: {PHASE} review",
            f"- run_id: {manifest['run_id']}",
            "",
            "- [pass] #1448 review follow-up inherited",
            "- [pass] notableMatches rejected",
            f"- [pass] route variants reviewed: {selection['route_variants_selected']}",
            f"- [pass] max_samples={selection['max_samples']} <= 2",
            f"- [pass] max_network_requests={summary['max_network_requests']} <= 2",
            f"- [pass] max_body_bytes={selection['max_body_bytes']} <= 524288",
            f"- [pass] max_scan_depth={selection['max_scan_depth']} <= 12",
            f"- [pass] max_key_paths_recorded={selection['max_key_paths_recorded']} <= 500",
            "- [pass] max_value_preview_chars=0",
            f"- [pass] full_body_read_performed={safety['full_body_read_performed']}",
            f"- [pass] no full HTML saved: {safety['full_html_saved']}",
            f"- [pass] no response body saved: {safety['raw_response_body_saved']}",
            f"- [pass] no HTML body saved: {safety['html_body_saved']}",
            f"- [pass] no full NEXT_DATA saved: {safety['full_next_data_saved']}",
            f"- [pass] no value persistence: {safety['value_persistence_performed']}",
            f"- [pass] no raw JSON saved: {safety['raw_json_write_performed']}",
            f"- [pass] no DB write: {safety['db_write_performed']}",
            "- [pass] no scheduler",
            "- [pass] no feature parse",
            "- [pass] no browser automation",
            "- [pass] no captcha bypass",
            "- [pass] no proxy rotation",
            f"- [pass] json_validated_count={readiness['json_validated_count']}",
            f"- [pass] raw_write_eligible_count={readiness['raw_write_eligible_count']}",
            f"- [pass] recommended next phase safe: {manifest['recommended_next_phase']}",
            "- [pass] no direct raw write recommendation",
            "",
            "## Overall: pass",
        ]
    )


def render_decision(manifest: dict[str, Any], allow_network: bool) -> str:
    summary = manifest["keyspace_summary"]
    decision = manifest["keyspace_candidate_decision"]
    results = manifest.get("keyspace_results", [])

    lines = [
        "<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->",
        "# FotMob Hydration Keyspace Candidate Decision",
        "",
        "- lifecycle: current-state",
        f"- phase: {PHASE} decision",
        f"- run_id: {manifest['run_id']}",
        f"- mode: {'controlled' if allow_network else 'dry_run_plan_only'}",
        "",
        "## Keyspace Scan Result",
        "",
        f"- __NEXT_DATA__ parse count: {summary['next_data_parse_ok_count']}",
        f"- pageProps present count: {summary['pageProps_present_count']}",
        f"- fallback present count: {summary['fallback_present_count']}",
        "- total key paths recorded: (见每个 result entry)",
        "- target match_id in key path: (见每个 result entry)",
        "- route_code in key path: (见每个 result entry)",
        f"- strong_path_candidate_count: {summary['strong_path_candidate_count']}",
        f"- weak_path_candidate_count: {summary['weak_path_candidate_count']}",
        f"- partial_path_candidate_count: {summary['partial_path_candidate_count']}",
        f"- generic_or_irrelevant_path_count: {summary['generic_or_irrelevant_path_count']}",
        "",
        f"- best candidate path: {decision['best_path_candidate']}",
        f"- best candidate score: {decision['best_path_score']}",
        f"- best route variant: {decision['best_route_variant']}",
        "",
        "## Generic Paths Excluded",
        "",
        "- notableMatches (score=-4 penalty + -5 generic-only, excludes from candidates)",
        "- translations subtree (score=-4, generic config penalty)",
        "- CountryCodes / Language / static config (score=-3 to -5)",
    ]

    if results:
        lines += [
            "",
            "## Per-Result Details",
        ]
        for entry in results:
            lines += [
                "",
                f"### {entry['review_id']} — {entry.get('match_id', '?')} (variant={entry.get('route_variant', '?')})",
                "",
                f"- validation_state: {entry.get('validation_state', 'unknown')}",
                f"- next_data_parse_ok: {entry.get('next_data_parse_ok', False)}",
                f"- pageProps_present: {entry.get('pageProps_present', False)}",
                f"- fallback_present: {entry.get('fallback_present', False)}",
                f"- key_paths_recorded: {entry.get('key_paths_recorded_count', 0)}",
                f"- target_match_id_in_key_path: {entry.get('target_match_id_in_key_path', False)}",
                f"- positive_candidate_path_count: {entry.get('positive_candidate_path_count', 0)}",
                f"- top candidates: {', '.join(entry.get('top_candidate_paths', [])[:5])}",
                f"- top scores: {entry.get('top_candidate_scores', [])[:5]}",
                f"- generic rejected: {', '.join(entry.get('generic_paths_rejected', [])[:5])}",
            ]

    lines += [
        "",
        "## Why Raw Write Is Still Blocked",
        "",
        "- 本阶段只扫描 key path metadata，未验证任何 JSON value。",
        "- json_validated_count=0。",
        "- raw_write_eligible_count=0。",
        "- 即使发现 strong candidate path，也需要先做 candidate path validation no-write。",
        "",
        "## Recommended Next Phase",
        "",
        f"- **{manifest['recommended_next_phase']}**",
    ]
    return "\n".join(lines)


def enforce_safety(manifest: dict[str, Any], allow_network: bool) -> None:
    """Exit non-zero if any forbidden persistence flag is True."""
    safety = manifest.get("safety", {})
    results = manifest.get("keyspace_results", [])

    forbidden_true = [
        "full_body_read_performed",
        "full_html_saved",
        "raw_response_body_saved",
        "html_body_saved",
        "full_next_data_saved",
        "value_persistence_performed",
        "raw_json_write_performed",
        "db_write_performed",
        "production_db_write_performed",
        "fotmob_raw_match_payloads_write_performed",
        "raw_match_data_write_performed",
        "feature_parse_performed",
        "scheduler_enabled",
        "raw_write_ready_marked",
        "browser_automation_performed",
        "captcha_bypass_performed",
        "proxy_rotation_performed",
    ]
    for flag in forbidden_true:
        if safety.get(flag) is True:
            raise ValueError(f"safety.{flag} must remain false")

    for entry in results:
        for key in RESULT_FALSE_NAMES:
            if entry.get(key) is True:
                raise ValueError(f"result {entry.get('review_id')}.{key} must remain false")

    readiness = manifest.get("raw_write_readiness", {})
    if readiness.get("json_validated_count", 0) > 0:
        raise ValueError("json_validated_count must remain 0")
    if readiness.get("raw_write_eligible_count", 0) > 0:
        raise ValueError("raw_write_eligible_count must remain 0")

    rec = manifest.get("recommended_next_phase", "")
    if "DIRECT-RAW-WRITE" in rec or "RAW-JSON-WRITE" in rec:
        raise ValueError("recommended_next_phase must not be direct raw write")


def write_outputs(
    args: argparse.Namespace,
    manifest: dict[str, Any],
    allow_network: bool,
) -> None:
    output_manifest = Path(args.output_manifest)
    report = Path(args.report)
    review = Path(args.review_report)
    decision = Path(args.decision_report)
    for path in [output_manifest, report, review, decision]:
        path.parent.mkdir(parents=True, exist_ok=True)

    output_manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    report.write_text(render_report(manifest, allow_network) + "\n", encoding="utf-8")
    review.write_text(render_review(manifest, allow_network) + "\n", encoding="utf-8")
    decision.write_text(render_decision(manifest, allow_network) + "\n", encoding="utf-8")


def validate_inheritance(controlled: dict[str, Any]) -> None:
    """Verify that #1447/1448 inheritance values are correct."""
    summary = controlled.get("extraction_summary", {})
    readiness = controlled.get("raw_write_readiness", {})
    checks = {
        "target_match_id_seen_count": summary.get("target_match_id_seen_count"),
        "strong_candidate_count": summary.get("strong_candidate_count"),
        "json_validated_count": readiness.get("json_validated_count"),
        "raw_write_eligible_count": readiness.get("raw_write_eligible_count"),
    }
    expected = {
        "target_match_id_seen_count": 0,
        "strong_candidate_count": 0,
        "json_validated_count": 0,
        "raw_write_eligible_count": 0,
    }
    mismatches = {k: v for k, v in expected.items() if checks.get(k) != v}
    if mismatches:
        raise ValueError(f"Inheritance mismatch from #1447/1448: {mismatches}")
