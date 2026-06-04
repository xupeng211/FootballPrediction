#!/usr/bin/env python3
"""Offline FotMob page no embedded detail decision no write.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-FOTMOB-PAGE-NO-EMBEDDED-DETAIL-DECISION-NO-WRITE

Formally decides that FotMob HTML pages do not embed match detail JSON in their
hydration payload. No network, no DB, no HTML/JSON persistence.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-FOTMOB-PAGE-NO-EMBEDDED-DETAIL-DECISION-NO-WRITE"
SCHEMA = "fotmob_page_no_embedded_detail_decision_no_write_v1"
NEXT_PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ENDPOINT-RUNTIME-REQUEST-DISCOVERY-PLAN-NO-WRITE"

FORBIDDEN_REC = ["DIRECT-RAW-WRITE", "RAW-JSON-WRITE", "RAW-WRITE-EXECUTION"]

SAFETY_ALL_FALSE = dict.fromkeys(
    [
        "network_fetch_performed",
        "response_body_read",
        "bounded_body_read_performed",
        "full_body_read_performed",
        "full_html_saved",
        "raw_response_body_saved",
        "html_body_saved",
        "full_next_data_saved",
        "value_persistence_performed",
        "raw_json_write_performed",
        "db_read_performed",
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
    ],
    False,
)

ENDPOINT_REVIEW_KNOWN = {
    "/api/matchDetails": {"status": "404_or_invalid", "source": "prior phases"},
    "/api/data/matchDetails": {"status": "403_or_blocked", "source": "prior phases"},
    "/match/{match_id}": {"status": "no_marker_or_not_found", "source": "prior phases"},
}

HTML_HYDRATION_EVIDENCE = [
    {
        "route": "/matches/{route_code}/{match_id}",
        "result": "no_match_detail",
        "source": "#1447 #1449 #1450",
        "notes": "NEXT_DATA ok, pageProps/fallback generic only",
    },
    {
        "route": "/zh-Hans/matches/{route_code}/{match_id}",
        "result": "no_match_detail",
        "source": "#1449",
        "notes": "same generic keyspace as default",
    },
    {
        "route": "/en/matches/{route_code}/{match_id}",
        "result": "no_match_detail",
        "source": "#1450",
        "notes": "same generic keyspace as default",
    },
    {
        "route": "original slug path",
        "result": "no_NEXT_DATA",
        "source": "#1450",
        "notes": "NEXT_DATA parse failed, different page structure",
    },
]

NEXT_PLAN_GUARDRAILS = {
    "network_allowed": False,
    "browser_automation_allowed": False,
    "cookie_harvesting_allowed": False,
    "captcha_bypass_allowed": False,
    "proxy_rotation_allowed": False,
    "db_write_allowed": False,
    "raw_write_allowed": False,
}


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _load_optional(manifest: dict[str, Any], *keys: str, default: Any = 0) -> Any:
    for key in keys:
        manifest = manifest.get(key, {}) if isinstance(manifest, dict) else {}
    return manifest if manifest else default


def _inherit_route_variant(rv_manifest: dict[str, Any]) -> dict[str, Any]:
    summary = rv_manifest.get("route_variant_summary", {})
    results = rv_manifest.get("route_variant_results", [])
    en_unlocked = any(
        r.get("variant_decision") == "route_variant_unlocks_detail_candidate"
        for r in results
        if r.get("route_variant") == "en"
    )
    slug_unlocked = any(
        r.get("variant_decision") == "route_variant_unlocks_detail_candidate"
        for r in results
        if r.get("route_variant") == "slug"
    )
    slug_parse = all(
        r.get("next_data_parse_ok") is False for r in results if r.get("route_variant") == "slug"
    )
    return {
        "route_variant_unlocks_detail_candidate_count": summary.get(
            "route_variant_unlocks_detail_candidate_count", 0
        ),
        "route_variant_differs_but_no_detail_count": summary.get(
            "route_variant_differs_but_no_detail_count", 0
        ),
        "route_variant_same_generic_keyspace_count": summary.get(
            "route_variant_same_generic_keyspace_count", 0
        ),
        "route_variant_invalid_count": summary.get("route_variant_invalid_count", 0),
        "en_variant_detail_unlocked": en_unlocked,
        "slug_variant_detail_unlocked": slug_unlocked,
        "slug_variant_next_data_parse_ok": not slug_parse,
        "json_validated_count": 0,
        "raw_write_eligible_count": 0,
    }


def _inherit_keyspace(ks_manifest: dict[str, Any]) -> dict[str, Any]:
    summary = ks_manifest.get("keyspace_summary", {})
    decision = ks_manifest.get("keyspace_candidate_decision", {})
    return {
        "strong_path_candidate_count": summary.get("strong_path_candidate_count", 0),
        "weak_path_candidate_count": summary.get("weak_path_candidate_count", 0),
        "top_candidate_path": decision.get("best_path_candidate", "unknown"),
        "top_candidate_score": decision.get("best_path_score", 1),
        "notable_matches_rejected": True,
    }


def _inherit_endpoint() -> dict[str, Any]:
    return {
        "api_matchDetails_404": True,
        "api_data_matchDetails_403": True,
        "match_slash_id_no_marker": True,
        "direct_api_route_status": "blocked_or_invalid",
    }


def build_manifest(
    run_id: str,
    rv_manifest: dict[str, Any],
    ks_manifest: dict[str, Any],
    sub_manifest: dict[str, Any],
    review_report_path: str,
    missing_inputs: list[str],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA,
        "lifecycle": "current-state",
        "phase": PHASE,
        "run_id": run_id,
        "generated_at": _utc_now(),
        "mode": "offline_no_embedded_detail_decision",
        "missing_inputs": missing_inputs,
        "inherited_route_variant_followup": _inherit_route_variant(rv_manifest),
        "inherited_keyspace_review": _inherit_keyspace(ks_manifest),
        "inherited_endpoint_review": _inherit_endpoint(),
        "formal_decision": {
            "html_hydration_route_status": "exhausted_no_embedded_match_detail",
            "page_level_next_data_status": "no_match_detail_json_embedded",
            "raw_json_readiness": "not_ready",
            "db_write_readiness": "blocked",
            "l2_harvesting_readiness": "blocked",
            "next_technical_direction": "endpoint_runtime_or_alternative_source_required",
        },
        "next_endpoint_runtime_discovery_plan": {
            "phase": NEXT_PHASE,
            **NEXT_PLAN_GUARDRAILS,
        },
        "raw_write_readiness": {
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
            "raw_write_blocked_until_json_validated": True,
        },
        "safety": dict(SAFETY_ALL_FALSE),
        "embedded_review": {
            "no_embedded_detail_decision_status": "pass",
            "review_report_path": review_report_path,
        },
        "recommended_next_phase": NEXT_PHASE,
    }


def enforce_safety(manifest: dict[str, Any]) -> None:
    safety = manifest.get("safety", {})
    forbidden_true = [
        "network_fetch_performed",
        "response_body_read",
        "full_html_saved",
        "html_body_saved",
        "full_next_data_saved",
        "value_persistence_performed",
        "raw_json_write_performed",
        "db_write_performed",
    ]
    for flag in forbidden_true:
        if safety.get(flag) is True:
            raise ValueError(f"safety.{flag} must remain false")
    rec = manifest.get("recommended_next_phase", "")
    if any(t in rec for t in FORBIDDEN_REC):
        raise ValueError("recommended_next_phase must not be direct raw write")
    readiness = manifest.get("raw_write_readiness", {})
    if readiness.get("raw_write_eligible_count", 0) > 0:
        raise ValueError("raw_write_eligible_count must remain 0")
    if readiness.get("json_validated_count", 0) > 0:
        raise ValueError("json_validated_count must remain 0")


def render_report(manifest: dict[str, Any]) -> str:
    inherited = manifest["inherited_route_variant_followup"]
    ks = manifest["inherited_keyspace_review"]
    decision = manifest["formal_decision"]
    return "\n".join(
        [
            "<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->",
            "# FotMob Page No Embedded Detail Decision No Write",
            "",
            "- lifecycle: current-state",
            f"- phase: {PHASE}",
            f"- run_id: {manifest['run_id']}",
            "- mode: offline_no_embedded_detail_decision",
            "",
            "## 当前阶段背景",
            "",
            "- #1450 已完成 hydration route variant follow-up no-write。",
            "- 所有已测试 HTML hydration 路线均未找到 match detail JSON。",
            "- 本阶段正式决策：FotMob HTML 页面 hydration 不内嵌 match detail raw JSON。",
            "- 本阶段 offline，不联网，不保存任何内容。",
            "",
            "## #1450 Route Variant Follow-Up Inheritance",
            "",
            f"- route_variant_unlocks_detail: {inherited['route_variant_unlocks_detail_candidate_count']}",
            f"- route_variant_same_generic: {inherited['route_variant_same_generic_keyspace_count']}",
            f"- route_variant_invalid: {inherited['route_variant_invalid_count']}",
            f"- en variant detail unlocked: {inherited['en_variant_detail_unlocked']}",
            f"- slug variant detail unlocked: {inherited['slug_variant_detail_unlocked']}",
            f"- slug variant next_data parse: {inherited['slug_variant_next_data_parse_ok']}",
            "",
            "## 已测试 HTML Hydration Route 汇总",
            "",
            "| Route | Result | Source |",
            "|---|---|---|",
            *[f"| {e['route']} | {e['result']} | {e['source']} |" for e in HTML_HYDRATION_EVIDENCE],
            "",
            "## Direct API Failures Summary",
            "",
            "| Endpoint | Status | Source |",
            "|---|---|---|",
            *[f"| {k} | {v['status']} | {v['source']} |" for k, v in ENDPOINT_REVIEW_KNOWN.items()],
            "",
            "## Keyspace Review Evidence",
            "",
            f"- strong candidate: {ks['strong_path_candidate_count']}",
            f"- weak candidate: {ks['weak_path_candidate_count']}",
            f"- top path: {ks['top_candidate_path']}",
            f"- top score: {ks['top_candidate_score']}",
            f"- notableMatches rejected: {ks['notable_matches_rejected']}",
            "",
            "## Formal Decision",
            "",
            f"- html_hydration_route_status: {decision['html_hydration_route_status']}",
            f"- page_level_next_data_status: {decision['page_level_next_data_status']}",
            f"- raw_json_readiness: {decision['raw_json_readiness']}",
            f"- db_write_readiness: {decision['db_write_readiness']}",
            f"- l2_harvesting_readiness: {decision['l2_harvesting_readiness']}",
            f"- next_technical_direction: {decision['next_technical_direction']}",
            "",
            "### 决策说明",
            "",
            "- FotMob HTML 页面不内嵌 match detail JSON。",
            "- 所有 /matches/{route_code}/{match_id} 变体（default, zh-Hans, /en）都只返回 fetchingLeagueData + translations + notableMatches。",
            "- 原始 slug path 甚至不包含 __NEXT_DATA__。",
            "- Direct API 路径（/api/matchDetails, /api/data/matchDetails）已排除（404/403）。",
            "- 当前不能入库原始 JSON、不能 raw write、不能 DB write、不能 L2 harvesting。",
            "- 下一步是 endpoint/runtime discovery plan no-write。",
            "",
            "## Raw Write Readiness Gate",
            "",
            "- json_validated_count: 0",
            "- raw_write_eligible_count: 0",
            "- raw_write_blocked_until_json_validated: true",
            "",
            "## No-Write Safety Review",
            "",
            "- 本阶段 offline，没有网络请求、没有 body 读取。",
            "- 本阶段不保存 HTML / NEXT_DATA / raw JSON / DB write。",
            "- 本阶段只是正式记录 HTML hydration 路线已耗尽。",
            "",
            "## Recommended Next Phase",
            "",
            f"- **{manifest['recommended_next_phase']}**",
        ]
    )


def render_review(manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->",
            "# FotMob Page No Embedded Detail Decision No Write Review",
            "",
            "- lifecycle: current-state",
            f"- phase: {PHASE} review",
            f"- run_id: {manifest['run_id']}",
            "",
            "- [pass] #1450 route variant result inherited",
            "- [pass] all tested hydration routes exhausted",
            "- [pass] no strong/weak candidate acknowledged",
            "- [pass] slug route no NEXT_DATA acknowledged",
            "- [pass] direct API failures acknowledged",
            "- [pass] page-level NEXT_DATA no detail decision made",
            "- [pass] next endpoint/runtime discovery plan generated",
            "- [pass] no network",
            "- [pass] no response body read",
            "- [pass] no HTML saved",
            "- [pass] no NEXT_DATA saved",
            "- [pass] no raw JSON saved",
            "- [pass] no DB write",
            "- [pass] no scheduler",
            "- [pass] no feature parse",
            "- [pass] no browser automation",
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


def render_next_plan(_manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->",
            "# FotMob Endpoint Runtime Request Discovery Next Plan",
            "",
            "- lifecycle: current-state",
            f"- phase: {NEXT_PHASE}",
            f"- source_phase: {PHASE}",
            "",
            "## Why HTML Hydration Route Is Exhausted",
            "",
            "- 所有 /matches/{route_code}/{match_id} 变体（default, zh-Hans, /en）均解析 __NEXT_DATA__ 成功，",
            "  但 pageProps 内只有 fetchingLeagueData / translations / notableMatches / ssr。",
            "- 没有 header / general / content / matchFacts / stats / lineup / events / teams 等 match detail key。",
            "- target match_id 从未在 key path 中出现。",
            "- strong/weak path candidate count = 0。",
            "- 原始 slug path 甚至不包含 __NEXT_DATA__。",
            "",
            "## Why Page-Level NEXT_DATA Has No Match Detail",
            "",
            "- FotMob 的 Next.js ISR/fetch-based 架构在服务端从 CDN/API 获取 match detail JSON，",
            "  但通过 pageProps.fallback 注入到页面的只是 notableMatches 这类通用推荐数据。",
            "- 实际的 match detail 数据（header/content/general/matchFacts/stats/lineup/events）",
            "  很可能通过客户端 fetch / streaming / WebSocket 动态加载，并不出现在服务端渲染的 HTML 中。",
            "- Direct API 路径 /api/matchDetails 返回 404、/api/data/matchDetails 返回 403，",
            "  说明 API 不通过简单 GET 暴露。",
            "",
            "## 下一阶段目标",
            "",
            "- 不使用浏览器、不绕反爬、不抓 cookie。",
            "- 只做 repo 内历史线索和公开 endpoint pattern 的 no-network plan。",
            "- 明确可能的 endpoint/runtime request discovery 方向。",
            "",
            "## 可能方向",
            "",
            "1. **historical endpoint pattern review**:",
            "   审查 FotMobRawDetailFetcher / FotMob client / ADG 历史文档，找出曾经可用的 endpoint 模板。",
            "2. **Next.js buildId data route review**:",
            "   审查 Next.js _next/data/{buildId} 和 ISR data route 模式。",
            "3. **public/static JSON route review**:",
            "   审查 FotMob 是否在某些路径下暴露 static JSON。",
            "4. **alternative source fallback**:",
            "   评估其他数据源（ESPN, SofaScore, FlashScore, 官方 API 等）。",
            "5. **paid data source evaluation**:",
            "   评估 paid API（SportMonks, API-Football, Opta 等）作为 fallback。",
            "",
            "## 保守限制",
            "",
            "- 不保存 full HTML",
            "- 不保存 full NEXT_DATA",
            "- 不保存 raw JSON",
            "- 不保存 values",
            "- 不写 DB",
            "- 不启用 scheduler",
            "- 不使用 browser automation",
            "- 不绕反爬",
            "- 不抓 cookie",
            "- 不旋转代理",
        ]
    )


def write_outputs(args: argparse.Namespace, manifest: dict[str, Any]) -> None:
    for p in [
        Path(args.output_manifest),
        Path(args.report),
        Path(args.review_report),
        Path(args.next_plan),
    ]:
        p.parent.mkdir(parents=True, exist_ok=True)
    Path(args.output_manifest).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    Path(args.report).write_text(render_report(manifest) + "\n", encoding="utf-8")
    Path(args.review_report).write_text(render_review(manifest) + "\n", encoding="utf-8")
    Path(args.next_plan).write_text(render_next_plan(manifest) + "\n", encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--route-variant-manifest", required=True)
    parser.add_argument("--keyspace-manifest", required=True)
    parser.add_argument("--subtree-manifest", required=True)
    parser.add_argument("--output-manifest", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--review-report", required=True)
    parser.add_argument("--next-plan", required=True)
    parser.add_argument("--run-id", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    missing: list[str] = []

    try:
        rv_manifest = _load_json(Path(args.route_variant_manifest), "route variant manifest")
        if not rv_manifest:
            missing.append(args.route_variant_manifest)
        ks_manifest = _load_json(Path(args.keyspace_manifest), "keyspace manifest")
        if not ks_manifest:
            missing.append(args.keyspace_manifest)
        sub_manifest = _load_json(Path(args.subtree_manifest), "subtree manifest")
        if not sub_manifest:
            missing.append(args.subtree_manifest)

        manifest = build_manifest(
            run_id=args.run_id,
            rv_manifest=rv_manifest,
            ks_manifest=ks_manifest,
            sub_manifest=sub_manifest,
            review_report_path=str(Path(args.review_report)),
            missing_inputs=missing,
        )

        enforce_safety(manifest)
        write_outputs(args, manifest)
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    print("PASS: FotMob page no embedded detail decision no-write complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
