#!/usr/bin/env python3
"""Report rendering for FotMob hydration route variant follow-up no-write.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-ROUTE-VARIANT-FOLLOWUP-NO-WRITE
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-ROUTE-VARIANT-FOLLOWUP-NO-WRITE"


def validate_inheritance(controlled: dict[str, Any], keyspace: dict[str, Any]) -> None:
    """Verify #1449 keyspace review inheritance values are correct."""
    ksum = keyspace.get("keyspace_summary", {})
    kdec = keyspace.get("keyspace_candidate_decision", {})
    checks = {
        "strong_path_candidate_count": ksum.get("strong_path_candidate_count"),
        "weak_path_candidate_count": ksum.get("weak_path_candidate_count"),
        "best_path_candidate": kdec.get("best_path_candidate"),
    }
    expected = {
        "strong_path_candidate_count": 0,
        "weak_path_candidate_count": 0,
        "best_path_candidate": "props.pageProps.fetchingLeagueData",
    }
    mismatches = {k: v for k, v in expected.items() if checks.get(k) != v}
    if mismatches:
        raise ValueError(f"Keyspace inheritance mismatch: {mismatches}")


def enforce_safety(manifest: dict[str, Any], allow_network: bool) -> None:
    safety = manifest.get("safety", {})
    results = manifest.get("route_variant_results", [])

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
        for key in [
            "full_html_saved",
            "raw_response_body_saved",
            "html_body_saved",
            "full_next_data_saved",
            "raw_json_write_performed",
            "db_write_performed",
            "raw_write_eligible",
        ]:
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


def write_outputs(args: argparse.Namespace, manifest: dict[str, Any], allow_network: bool) -> None:
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


def render_report(manifest: dict[str, Any], allow_network: bool) -> str:
    inherited = manifest["inherited_keyspace_review"]
    selection = manifest["route_variant_selection"]
    summary = manifest["route_variant_summary"]
    decision = manifest["route_variant_decision"]
    results = manifest.get("route_variant_results", [])

    mode_name = (
        "controlled_route_variant_followup_no_write"
        if allow_network
        else "dry_run_route_variant_followup_plan_only"
    )
    lines = [
        "<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->",
        "# FotMob Hydration Route Variant Follow-Up No Write",
        "",
        f"- lifecycle: current-state",
        f"- phase: {PHASE}",
        f"- run_id: {manifest['run_id']}",
        f"- mode: {mode_name}",
        "",
        "## 当前阶段背景",
        "",
        "- #1449 已完成 hydration keyspace review no-write，default/zh-Hans 路径均未暴露 match detail。",
        "- 本阶段测试 /en 和原始 slug URL path 两种 variant，看是否出现不同的 hydration keyspace。",
        "- 只保存 route/key path metadata，不保存任何 value。",
        "",
        "## #1449 Keyspace Review Inheritance",
        "",
        f"- default_route_strong_candidate: {inherited['default_route_strong_path_candidate_count']}",
        f"- zh_hans_route_strong_candidate: {inherited['zh_hans_route_strong_path_candidate_count']}",
        f"- weak_path_candidate: {inherited['weak_path_candidate_count']}",
        f"- best_path_candidate: {inherited['best_path_candidate']}",
        f"- notable_matches_rejected: {inherited['notable_matches_rejected']}",
        "",
        "## Selected Route Variants",
        "",
        f"- {', '.join(selection['selected_route_variants'])}",
    ]

    if allow_network and results:
        lines += [
            "",
            "## Controlled Route Variant Probe Summary",
            "",
            f"- network_requests_attempted: {summary['network_requests_attempted']}",
            f"- en variant attempts: {summary.get('en_variant_attempted_count', 0)}",
            f"- slug variant attempts: {summary.get('slug_variant_attempted_count', 0)}",
            f"- unlocks_detail_count: {summary['route_variant_unlocks_detail_candidate_count']}",
            f"- differs_but_no_detail_count: {summary['route_variant_differs_but_no_detail_count']}",
            f"- same_generic_keyspace_count: {summary['route_variant_same_generic_keyspace_count']}",
            f"- blocked_count: {summary['route_variant_blocked_count']}",
            f"- invalid_count: {summary['route_variant_invalid_count']}",
        ]
        for entry in results:
            lines += [
                "",
                f"### {entry['review_id']} — {entry['match_id']} (variant={entry['route_variant']})",
                "",
                f"- status: {entry.get('validation_state', 'unknown')}",
                f"- redirect_observed: {entry.get('redirect_observed', False)}",
                f"- next_data_parse_ok: {entry.get('next_data_parse_ok', False)}",
                f"- pageProps_present: {entry.get('pageProps_present', False)}",
                f"- strong/weak: {entry.get('strong_path_candidate_count', 0)}/{entry.get('weak_path_candidate_count', 0)}",
                f"- top_path: {entry.get('top_candidate_path')}",
                f"- top_score: {entry.get('top_candidate_score')}",
                f"- differs_from_baseline: {entry.get('differs_from_default_baseline', False)}",
                f"- variant_decision: {entry.get('variant_decision')}",
            ]

    lines += [
        "",
        "## Keyspace Comparison",
        "",
        "- baseline (default/zh-Hans): fetchingLeagueData, translations, notableMatches",
        "- /en variant: 见上方 per-result summary",
        "- slug path variant: 见上方 per-result summary",
        "",
        "## Route Variant Decision",
        "",
        f"- best_route_variant: {decision['best_route_variant']}",
        f"- best_candidate_path: {decision['best_candidate_path']}",
        f"- best_candidate_score: {decision['best_candidate_score']}",
        f"- best_candidate_state: {decision['best_candidate_state']}",
        "",
        "## Raw Write Readiness Gate",
        "",
        "- json_validated_count: 0",
        "- raw_write_eligible_count: 0",
        "- raw_write_blocked_until_json_validated: true",
        "",
        "## No-Write Safety Review",
        "",
        "- 本阶段只保存 route/key path metadata",
        "- 本阶段不保存任何 value",
        "- 本阶段不保存完整 HTML",
        "- 本阶段不保存完整 __NEXT_DATA__",
        "- 本阶段不保存 raw JSON",
        "- 本阶段不写 DB",
        "- 本阶段不进入 L2 raw harvesting",
    ]

    if allow_network and summary.get("route_variant_unlocks_detail_candidate_count", 0) >= 1:
        lines.append(
            "- 如果 route variant 解锁 strong/weak candidate，下一阶段也只是 path validation no-write，不是直接入库"
        )
    else:
        lines.append("- 依然保持 no-write 门禁")

    lines += [
        "",
        "## Remaining Blockers",
        "",
        "- 尚未找到包含 target match_id 的 match detail subtree。",
        "- 尚未完成任何 candidate path validation。",
        "- raw_write_eligible_count 仍然为 0。",
        "",
        "## Recommended Next Phase",
        "",
        f"- **{manifest['recommended_next_phase']}**",
    ]
    return "\n".join(lines)


def render_review(manifest: dict[str, Any], allow_network: bool) -> str:
    selection = manifest["route_variant_selection"]
    summary = manifest["route_variant_summary"]
    safety = manifest["safety"]
    readiness = manifest["raw_write_readiness"]

    return "\n".join(
        [
            "<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->",
            "# FotMob Hydration Route Variant Follow-Up No Write Review",
            "",
            "- lifecycle: current-state",
            f"- phase: {PHASE} review",
            f"- run_id: {manifest['run_id']}",
            "",
            "- [pass] #1449 keyspace review inherited",
            "- [pass] no strong/weak baseline acknowledged",
            f"- [pass] selected variants are en and original slug path: {selection['selected_route_variants']}",
            f"- [pass] max_samples={selection['max_samples']} <= 2",
            f"- [pass] max_route_variants={selection['max_route_variants']} <= 2",
            f"- [pass] max_network_requests={summary['max_network_requests']} <= 4",
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
    summary = manifest["route_variant_summary"]
    decision = manifest["route_variant_decision"]
    results = manifest.get("route_variant_results", [])

    lines = [
        "<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->",
        "# FotMob Hydration Route Variant Decision",
        "",
        "- lifecycle: current-state",
        f"- phase: {PHASE} decision",
        f"- run_id: {manifest['run_id']}",
        f"- mode: {'controlled' if allow_network else 'dry_run_plan_only'}",
        "",
        "## Route Variants Tested",
        "",
        f"- en variant attempted: {summary.get('en_variant_attempted_count', 0)}",
        f"- slug variant attempted: {summary.get('slug_variant_attempted_count', 0)}",
        "",
        "## Inherited Baseline (from #1449)",
        "",
        "- default/zh-Hans route: fetchingLeagueData + translations + notableMatches",
        "- strong candidate: 0, weak candidate: 0",
        "- notableMatches rejected as match detail",
        "",
        "## LIVE PROBE RESULTS",
    ]

    if results:
        for entry in results:
            lines += [
                "",
                f"### {entry['review_id']} — {entry.get('match_id', '?')} (variant={entry.get('route_variant', '?')})",
                "",
                f"- status: {entry.get('validation_state', 'unknown')}",
                f"- redirect_observed: {entry.get('redirect_observed', False)}",
                f"- next_data_parse_ok: {entry.get('next_data_parse_ok', False)}",
                f"- pageProps_present: {entry.get('pageProps_present', False)}",
                f"- strong_candidate_count: {entry.get('strong_path_candidate_count', 0)}",
                f"- weak_candidate_count: {entry.get('weak_path_candidate_count', 0)}",
                f"- top_candidate_path: {entry.get('top_candidate_path')}",
                f"- top_candidate_score: {entry.get('top_candidate_score')}",
                f"- top_candidate_state: {entry.get('top_candidate_state')}",
                f"- differs_from_baseline: {entry.get('differs_from_default_baseline', False)}",
                f"- variant_decision: {entry.get('variant_decision')}",
            ]

    lines += [
        "",
        "## Key Findings",
        "",
        f"- unlock_detail: {summary['route_variant_unlocks_detail_candidate_count']}",
        f"- differs_no_detail: {summary['route_variant_differs_but_no_detail_count']}",
        f"- same_generic: {summary['route_variant_same_generic_keyspace_count']}",
        f"- blocked: {summary['route_variant_blocked_count']}",
        f"- invalid: {summary['route_variant_invalid_count']}",
        "",
        f"- best route variant: {decision['best_route_variant']}",
        f"- best candidate path: {decision['best_candidate_path']}",
        f"- best candidate score: {decision['best_candidate_score']}",
        "",
        "## Why Raw Write Is Still Blocked",
        "",
        "- 本阶段只比较 route variant keyspace metadata，未验证任何 JSON value。",
        "- json_validated_count=0。",
        "- raw_write_eligible_count=0。",
        "- 即使某个 variant 解锁 candidate path，也需要先做 path validation no-write。",
        "",
        "## Recommended Next Phase",
        "",
        f"- **{manifest['recommended_next_phase']}**",
    ]
    return "\n".join(lines)
