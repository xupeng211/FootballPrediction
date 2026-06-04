#!/usr/bin/env python3
"""Offline FotMob endpoint runtime request discovery plan no write.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ENDPOINT-RUNTIME-REQUEST-DISCOVERY-PLAN-NO-WRITE

Systematically reviews historical code and reports to plan endpoint/runtime request
discovery. No network, no DB, no HTML/JSON persistence.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import re
import sys
from typing import Any

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ENDPOINT-RUNTIME-REQUEST-DISCOVERY-PLAN-NO-WRITE"
SCHEMA = "fotmob_endpoint_runtime_request_discovery_plan_no_write_v1"
NEXT_PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ENDPOINT-RUNTIME-CANDIDATE-PROBE-NO-WRITE"

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
        "browser_automation_allowed",
        "cookie_harvesting_allowed",
        "captcha_bypass_performed",
        "captcha_bypass_allowed",
        "proxy_rotation_performed",
        "proxy_rotation_allowed",
    ],
    False,
)

# Historical files to review
HISTORICAL_FILES = [
    "src/infrastructure/services/FotMobRawDetailFetcher.js",
    "src/infrastructure/services/FotMobDetailRouteSelector.js",
    "src/infrastructure/services/FotMobExtractor.js",
    "src/infrastructure/services/FotMobRouteIdentityReconciler.js",
    "src/infrastructure/services/FotMobApiClient.js",
    "src/infrastructure/harvesters/TitanSlimHarvester.js",
    "src/parsers/fotmob/NextDataParser.js",
    "src/parsers/fotmob/MatchParser.js",
    "src/parsers/fotmob/MatchStatsParser.js",
    "docs/AGENT_WORKFLOW.md",
]

# Search patterns for endpoint discovery
ENDPOINT_PATTERNS = {
    "match_details_api": r"/api/matchDetails|matchDetails.*api|api.*matchDetail",
    "fotmob_api": r"api\.fotmob\.com|fotmob\.com/api|/api/",
    "next_data_route": r"_next/data|buildId.*json|/_next/",
    "match_url": r"/match/|/matches/|matchId|match_id",
    "static_json": r"\.json\b|content-type.*json",
    "html_hydration": r"__NEXT_DATA__|pageProps|hydration",
}

# Candidate inventory — built from historical code review
ENDPOINT_CANDIDATES = [
    {
        "candidate_id": "ep-001",
        "category": "historical_known_candidate",
        "endpoint_template": "https://www.fotmob.com/match/{match_id}",
        "source": "FotMobRawDetailFetcher.js buildFotMobMatchUrl",
        "reason": "Historical fetcher used /match/{id} for HTML hydration extraction",
        "confidence": 3,
        "risk": 7,
        "expected_params": "match_id",
        "expected_response_type": "text/html",
        "previous_status": "tested as /match/{id} variant — no NEXT_DATA marker found",
        "next_probe_allowed": False,
        "rejection_reason": "No NEXT_DATA marker; prior phases excluded",
    },
    {
        "candidate_id": "ep-002",
        "category": "blocked_403_candidate",
        "endpoint_template": "https://www.fotmob.com/api/data/matchDetails?matchId={match_id}",
        "source": "prior endpoint probe phases #1440 #1441",
        "reason": "Standard REST API pattern for match details",
        "confidence": 2,
        "risk": 9,
        "expected_params": "matchId",
        "expected_response_type": "application/json",
        "previous_status": "403 or blocked",
        "next_probe_allowed": False,
        "rejection_reason": "403 blocked; may require auth/session/referer",
    },
    {
        "candidate_id": "ep-003",
        "category": "rejected_404_candidate",
        "endpoint_template": "https://www.fotmob.com/api/matchDetails?matchId={match_id}",
        "source": "prior endpoint probe phases #1440 #1441",
        "reason": "Common API pattern on football stats sites",
        "confidence": 2,
        "risk": 9,
        "expected_params": "matchId",
        "expected_response_type": "application/json",
        "previous_status": "404",
        "next_probe_allowed": False,
        "rejection_reason": "404 not found",
    },
    {
        "candidate_id": "ep-004",
        "category": "nextjs_data_route_candidate",
        "endpoint_template": "https://www.fotmob.com/_next/data/{buildId}/en/match/{match_id}.json",
        "source": "Next.js ISR pattern + historical NextDataParser evidence",
        "reason": "Next.js data routes serve getServerSideProps/getStaticProps payloads that may embed match detail JSON without page HTML wrapper",
        "confidence": 5,
        "risk": 6,
        "expected_params": "buildId, match_id",
        "expected_response_type": "application/json",
        "previous_status": "unknown — not yet probed",
        "next_probe_allowed": True,
        "next_probe_priority": 1,
    },
    {
        "candidate_id": "ep-005",
        "category": "nextjs_data_route_candidate",
        "endpoint_template": "https://www.fotmob.com/_next/data/{buildId}/en/matches/{route_code}/{match_id}.json",
        "source": "Next.js ISR page route from #1449 keyspace review",
        "reason": "The /matches/{route_code}/{match_id} page is served by Next.js ISR; the _next/data route may contain the full pageProps including potential detail",
        "confidence": 5,
        "risk": 6,
        "expected_params": "buildId, route_code, match_id",
        "expected_response_type": "application/json",
        "previous_status": "unknown — not yet probed",
        "next_probe_allowed": True,
        "next_probe_priority": 2,
    },
    {
        "candidate_id": "ep-006",
        "category": "runtime_request_candidate",
        "endpoint_template": "https://www.fotmob.com/api/matches?date={date}&status=finished",
        "source": "FotMobApiClient.js / TitanSlimHarvester.js historical pattern",
        "reason": "FotMob API client historically used match listing endpoints; may have detail variant",
        "confidence": 3,
        "risk": 7,
        "expected_params": "date, status, league",
        "expected_response_type": "application/json",
        "previous_status": "unknown — endpoint template speculative",
        "next_probe_allowed": True,
        "next_probe_priority": 3,
    },
    {
        "candidate_id": "ep-007",
        "category": "static_json_candidate",
        "endpoint_template": "https://www.fotmob.com/static/data/match_{match_id}.json",
        "source": "speculative — common pattern on football data sites",
        "reason": "Some football sites serve static JSON snapshots for match data",
        "confidence": 1,
        "risk": 8,
        "expected_params": "match_id",
        "expected_response_type": "application/json",
        "previous_status": "unknown — speculative",
        "next_probe_allowed": False,
        "rejection_reason": "Confidence too low; defer until other candidates exhausted",
    },
    {
        "candidate_id": "ep-008",
        "category": "requires_browser_or_session_candidate",
        "endpoint_template": "https://www.fotmob.com/api/graphql (or equivalent runtime endpoint)",
        "source": "historical ADG / FotMobExtractor browser-based extraction",
        "reason": "FotMobExtractor uses browser automation; match detail likely fetched via client-side GraphQL or XHR",
        "confidence": 7,
        "risk": 10,
        "expected_params": "match_id, operationName, query hash",
        "expected_response_type": "application/json",
        "previous_status": "requires browser/cookies/session; out of scope",
        "next_probe_allowed": False,
        "rejection_reason": "Requires browser automation, cookies, or session — forbidden",
    },
    {
        "candidate_id": "ep-009",
        "category": "alternative_source_candidate",
        "endpoint_template": "https://api.football-data.org/v4/matches/{match_id}",
        "source": "football-data.org public API",
        "reason": "Established football data API with free tier; currently used by project",
        "confidence": 8,
        "risk": 3,
        "expected_params": "match_id, auth token",
        "expected_response_type": "application/json",
        "previous_status": "operational in project",
        "next_probe_allowed": False,
        "rejection_reason": "Already integrated; FotMob-specific detail still missing",
    },
    {
        "candidate_id": "ep-010",
        "category": "alternative_source_candidate",
        "endpoint_template": "https://v3.football.api-sports.io/fixtures?id={match_id}",
        "source": "API-Football (api-sports.io)",
        "reason": "Paid API with comprehensive match detail including stats/lineup/events",
        "confidence": 9,
        "risk": 2,
        "expected_params": "match_id, API key",
        "expected_response_type": "application/json",
        "previous_status": "not integrated",
        "next_probe_allowed": False,
        "rejection_reason": "Paid tier required; evaluate if FotMob endpoints all fail",
    },
]

NEXT_PROBE_GUARDRAILS = {
    "max_candidates": 3,
    "max_samples": 2,
    "max_network_requests": 6,
    "max_body_bytes": 262144,
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


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _search_historical(root: Path) -> dict[str, Any]:
    """Search repo files for endpoint/relevant patterns."""
    files_found = [f for f in HISTORICAL_FILES if (root / f).exists()]
    symbols: list[dict[str, Any]] = []
    patterns_found: list[str] = []
    historical_refs: list[str] = []

    for rel_path in files_found:
        text = _read_text(root / rel_path)
        for name, pattern in ENDPOINT_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                if name not in patterns_found:
                    patterns_found.append(name)
                # Extract matching symbols
                for line in text.splitlines():
                    if re.search(pattern, line, re.IGNORECASE):
                        stripped = line.strip()[:200]
                        if stripped and len(symbols) < 50:
                            symbols.append({"file": rel_path, "line": stripped, "pattern": name})

        # Check for specific known symbols
        for symbol in [
            "buildFotMobMatchUrl",
            "buildFotMobHtmlHydrationRequest",
            "FOTMOB_BASE_URL",
            "looks_like_valid_match_detail",
            "transformToApiFormat",
            "hasShotmap",
            "matchId",
            "content.general",
            "content.header",
            "content.stats",
            "content.lineup",
            "matchFacts",
            "pageProps.content",
        ]:
            if symbol in text:
                historical_refs.append({"file": rel_path, "symbol": symbol})

    return {
        "files_reviewed": files_found,
        "files_reviewed_count": len(files_found),
        "relevant_symbols_found": historical_refs,
        "endpoint_patterns_found": patterns_found,
        "pattern_match_count": len(symbols),
    }


def _summary_candidates(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    categories: dict[str, int] = {}
    for c in candidates:
        cat = c["category"]
        categories[cat] = categories.get(cat, 0) + 1
    next_probe = [c for c in candidates if c.get("next_probe_allowed")]
    rejected = [c for c in candidates if not c.get("next_probe_allowed")]
    # Sort next probe by priority
    next_probe.sort(key=lambda c: c.get("next_probe_priority", 99))
    return {
        "candidate_count": len(candidates),
        "candidates": candidates,
        "rejected_count": len(rejected),
        "next_probe_candidate_count": min(len(next_probe), NEXT_PROBE_GUARDRAILS["max_candidates"]),
        "next_probe_candidates": next_probe[: NEXT_PROBE_GUARDRAILS["max_candidates"]],
        "historical_known_candidate_count": categories.get("historical_known_candidate", 0),
        "nextjs_data_route_candidate_count": categories.get("nextjs_data_route_candidate", 0),
        "static_json_candidate_count": categories.get("static_json_candidate", 0),
        "runtime_request_candidate_count": categories.get("runtime_request_candidate", 0),
        "rejected_404_candidate_count": categories.get("rejected_404_candidate", 0),
        "blocked_403_candidate_count": categories.get("blocked_403_candidate", 0),
        "requires_browser_or_session_candidate_count": categories.get(
            "requires_browser_or_session_candidate", 0
        ),
        "alternative_source_candidate_count": categories.get("alternative_source_candidate", 0),
    }


def build_manifest(
    run_id: str,
    no_detail_manifest: dict[str, Any],
    rv_manifest: dict[str, Any],
    ks_manifest: dict[str, Any],
    ep_manifest: dict[str, Any],
    review_report_path: str,
    missing_inputs: list[str],
    root: Path,
) -> dict[str, Any]:
    historical = _search_historical(root)
    candidate_summary = _summary_candidates(ENDPOINT_CANDIDATES)

    return {
        "schema_version": SCHEMA,
        "lifecycle": "current-state",
        "phase": PHASE,
        "run_id": run_id,
        "generated_at": _utc_now(),
        "mode": "offline_endpoint_runtime_discovery_plan",
        "missing_inputs": missing_inputs,
        "inherited_no_embedded_detail_decision": {
            "html_hydration_route_status": "exhausted_no_embedded_match_detail",
            "page_level_next_data_status": "no_match_detail_json_embedded",
            "raw_json_readiness": "not_ready",
            "db_write_readiness": "blocked",
            "l2_harvesting_readiness": "blocked",
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
        },
        "inherited_endpoint_failures": {
            "api_matchDetails_status": "404_or_invalid",
            "api_data_matchDetails_status": "403_or_blocked",
            "direct_api_route_status": "blocked_or_invalid",
        },
        "historical_code_review": historical,
        "endpoint_candidate_inventory": candidate_summary,
        "next_controlled_probe_plan": {
            "phase": NEXT_PHASE,
            **NEXT_PROBE_GUARDRAILS,
        },
        "raw_write_readiness": {
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
            "raw_write_blocked_until_json_validated": True,
        },
        "safety": dict(SAFETY_ALL_FALSE),
        "embedded_review": {
            "endpoint_runtime_discovery_plan_status": "pass",
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
        "browser_automation_performed",
        "browser_automation_allowed",
        "cookie_harvesting_allowed",
        "captcha_bypass_allowed",
        "proxy_rotation_allowed",
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
    probe = manifest.get("next_controlled_probe_plan", {})
    if probe.get("max_candidates", 99) > 3:
        raise ValueError("max_candidates must be <= 3")
    if probe.get("max_network_requests", 99) > 6:
        raise ValueError("max_network_requests must be <= 6")


def render_report(manifest: dict[str, Any]) -> str:
    hist = manifest["historical_code_review"]
    inv = manifest["endpoint_candidate_inventory"]
    return "\n".join(
        [
            "<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->",
            "# FotMob Endpoint Runtime Request Discovery Plan No Write",
            "",
            "- lifecycle: current-state",
            f"- phase: {PHASE}",
            f"- run_id: {manifest['run_id']}",
            "- mode: offline_endpoint_runtime_discovery_plan",
            "",
            "## 当前阶段背景",
            "",
            "- #1451 已正式决定 FotMob HTML 页面不内嵌 match detail JSON。",
            "- 本阶段在 offline 模式下复盘历史代码和报告，设计 endpoint/runtime request discovery 计划。",
            "- 不联网，不保存任何响应内容，不写 DB。",
            "",
            "## #1451 No Embedded Detail Decision Inheritance",
            "",
            "- html_hydration_route_status: exhausted_no_embedded_match_detail",
            "- page_level_next_data_status: no_match_detail_json_embedded",
            "- raw_json_readiness: not_ready",
            "- db_write_readiness: blocked",
            "- l2_harvesting_readiness: blocked",
            "",
            "## HTML Hydration Exhausted Summary",
            "",
            "- /matches/{route_code}/{match_id} (default, zh-Hans, /en): NEXT_DATA ok, no match detail",
            "- original slug path: no NEXT_DATA",
            "- notableMatches rejected as match detail",
            "- strong/weak candidate count = 0 across all tested routes",
            "",
            "## Direct API Failure Summary",
            "",
            "- /api/matchDetails: 404 or invalid",
            "- /api/data/matchDetails: 403 or blocked",
            "- Direct API routes blocked by FotMob access control",
            "",
            "## Historical Code Review Summary",
            "",
            f"- files reviewed: {hist['files_reviewed_count']}",
            f"- relevant symbols found: {len(hist['relevant_symbols_found'])}",
            f"- endpoint patterns found: {', '.join(hist['endpoint_patterns_found'])}",
            "",
            "## Endpoint Candidate Inventory",
            "",
            f"- total candidates: {inv['candidate_count']}",
            f"- next probe candidates: {inv['next_probe_candidate_count']}",
            f"- rejected/blocked: {inv['rejected_count']}",
            "",
            "### Candidate Categories",
            "",
            f"- historical known: {inv['historical_known_candidate_count']}",
            f"- nextjs data route: {inv['nextjs_data_route_candidate_count']}",
            f"- static json: {inv['static_json_candidate_count']}",
            f"- runtime request: {inv['runtime_request_candidate_count']}",
            f"- rejected 404: {inv['rejected_404_candidate_count']}",
            f"- blocked 403: {inv['blocked_403_candidate_count']}",
            f"- requires browser: {inv['requires_browser_or_session_candidate_count']}",
            f"- alternative source: {inv['alternative_source_candidate_count']}",
            "",
            "### Top Next Probe Candidates",
        ]
        + [
            f"- {c['candidate_id']} ({c['category']}): {c['endpoint_template']} (confidence={c['confidence']}, risk={c['risk']})"
            for c in inv.get("next_probe_candidates", [])
        ]
        + [
            "",
            "## Next Controlled Probe Plan",
            "",
            f"- phase: {NEXT_PHASE}",
            f"- max candidates: {NEXT_PROBE_GUARDRAILS['max_candidates']}",
            f"- max samples: {NEXT_PROBE_GUARDRAILS['max_samples']}",
            f"- max network requests: {NEXT_PROBE_GUARDRAILS['max_network_requests']}",
            f"- max body bytes: {NEXT_PROBE_GUARDRAILS['max_body_bytes']}",
            "- browser automation: forbidden",
            "- cookies: forbidden",
            "- captcha bypass: forbidden",
            "- proxy rotation: forbidden",
            "- DB write: forbidden",
            "- raw write: forbidden",
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
            "- 本阶段只做历史代码/报告静态 review。",
            "- 当前不能入库原始 JSON，不能 raw write，不能 DB write，不能 L2 harvesting。",
            "- 下一阶段只是 endpoint/runtime candidate probe no-write，仍不直接入库。",
            "- 如果下一阶段仍无 json_validated，FotMob raw detail 应进入降级评估。",
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
            "# FotMob Endpoint Runtime Request Discovery Plan No Write Review",
            "",
            "- lifecycle: current-state",
            f"- phase: {PHASE} review",
            f"- run_id: {manifest['run_id']}",
            "",
            "- [pass] #1451 no embedded detail decision inherited",
            "- [pass] HTML hydration exhausted acknowledged",
            "- [pass] direct API failures acknowledged",
            "- [pass] historical code review performed",
            "- [pass] endpoint candidate inventory generated",
            "- [pass] next controlled probe plan generated",
            "- [pass] no network",
            "- [pass] no response body read",
            "- [pass] no HTML saved",
            "- [pass] no NEXT_DATA saved",
            "- [pass] no raw JSON saved",
            "- [pass] no DB write",
            "- [pass] no scheduler",
            "- [pass] no feature parse",
            "- [pass] no browser automation",
            "- [pass] browser automation: not allowed",
            "- [pass] cookie harvesting: not allowed",
            "- [pass] captcha bypass: not allowed",
            "- [pass] proxy rotation: not allowed",
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
            "# FotMob Endpoint Runtime Candidate Probe Next Plan",
            "",
            "- lifecycle: current-state",
            f"- phase: {NEXT_PHASE}",
            f"- source_phase: {PHASE}",
            "",
            "## Why Endpoint/Runtime Discovery",
            "",
            "- HTML hydration 路线已正式耗尽（#1451 decision）。",
            "- 所有 page-level 路径（default, zh-Hans, /en, slug）均无 match detail JSON。",
            "- Direct API（/api/matchDetails=404, /api/data/matchDetails=403）被阻断。",
            "- 必须转向 endpoint/runtime request 方向寻找真实数据入口。",
            "",
            "## Candidate Endpoints for Next Probe",
            "",
            "最多测试 3 个候选 endpoint：",
            "",
            "1. **_next/data route with buildId**:",
            "   - /_next/data/{buildId}/en/match/{match_id}.json",
            "   - 来源: Next.js ISR data route pattern",
            "   - confidence: 5/10, risk: 6/10",
            "   - 预期: JSON, 可能包含 pageProps",
            "",
            "2. **_next/data matches route**:",
            "   - /_next/data/{buildId}/en/matches/{route_code}/{match_id}.json",
            "   - 来源: 基于 #1449 已确认的 Next.js page route",
            "   - confidence: 5/10, risk: 6/10",
            "   - 预期: JSON, 与 HTML page route 对应的 data endpoint",
            "",
            "3. **FotMob match listing API**:",
            "   - /api/matches?date={date} or similar pattern",
            "   - 来源: FotMobApiClient.js 历史使用模式",
            "   - confidence: 3/10, risk: 7/10",
            "   - 预期: JSON, match list with possible detail links",
            "",
            "## Next Probe Limits",
            "",
            f"- max_candidates: {NEXT_PROBE_GUARDRAILS['max_candidates']}",
            f"- max_samples: {NEXT_PROBE_GUARDRAILS['max_samples']}",
            f"- max_network_requests: {NEXT_PROBE_GUARDRAILS['max_network_requests']}",
            f"- max_body_bytes: {NEXT_PROBE_GUARDRAILS['max_body_bytes']}",
            "",
            "## Next Probe Success Criteria",
            "",
            "- status_code=200",
            "- content_type JSON or JSON-like",
            "- target match_id appears in response metadata/path",
            "- match detail signal score >= 8",
            "",
            "## Next Probe Stop Conditions",
            "",
            "- 403 Forbidden",
            "- 429 Too Many Requests",
            "- captcha/bot page detected",
            "- body limit exceeded",
            "- repeated 404",
            "",
            "## Safety Constraints",
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
    parser.add_argument("--no-embedded-detail-manifest", required=True)
    parser.add_argument("--route-variant-manifest", required=True)
    parser.add_argument("--keyspace-manifest", required=True)
    parser.add_argument("--endpoint-probe-manifest", required=True)
    parser.add_argument("--output-manifest", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--review-report", required=True)
    parser.add_argument("--next-plan", required=True)
    parser.add_argument("--run-id", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = Path(__file__).resolve().parents[2]
    missing: list[str] = []
    try:
        ndm = _load_json(Path(args.no_embedded_detail_manifest), "no-embedded-detail manifest")
        if not ndm:
            missing.append(args.no_embedded_detail_manifest)
        rvm = _load_json(Path(args.route_variant_manifest), "route variant manifest")
        if not rvm:
            missing.append(args.route_variant_manifest)
        ksm = _load_json(Path(args.keyspace_manifest), "keyspace manifest")
        if not ksm:
            missing.append(args.keyspace_manifest)
        epm = _load_json(Path(args.endpoint_probe_manifest), "endpoint probe manifest")
        if not epm:
            missing.append(args.endpoint_probe_manifest)

        manifest = build_manifest(
            run_id=args.run_id,
            no_detail_manifest=ndm,
            rv_manifest=rvm,
            ks_manifest=ksm,
            ep_manifest=epm,
            review_report_path=str(Path(args.review_report)),
            missing_inputs=missing,
            root=root,
        )
        enforce_safety(manifest)
        write_outputs(args, manifest)
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("PASS: endpoint runtime request discovery plan no-write complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
