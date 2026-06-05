#!/usr/bin/env python3
"""Offline safe FotMob parser/schema reuse plan — no write, no network, no DB.

lifecycle: permanent
phase: SAFE-PARSER-SCHEMA-REUSE-PLAN-NO-WRITE

Identifies which historical FotMob parser/schema/fixture/validation assets can be
safely reused, and which browser/session/cookie/anti-bot assets must remain
read-only reference only. No network, no DB, no browser automation.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

PHASE = "SAFE-PARSER-SCHEMA-REUSE-PLAN-NO-WRITE"
SCHEMA = "fotmob_safe_parser_schema_reuse_plan_no_write_v1"
NEXT_PHASE_RECONSTRUCTION = "HISTORICAL-FOTMOB-PAYLOAD-SHAPE-RECONSTRUCTION-READONLY"
NEXT_PHASE_ADAPTER = "FOTMOB-CANONICAL-PAYLOAD-SCHEMA-ADAPTER-PLAN-NO-WRITE"
NEXT_PHASE_MAPPING = "ALTERNATIVE-SOURCE-TO-FOTMOB-SCHEMA-MAPPING-PLAN-NO-WRITE"
NEXT_PHASE_DOWNGRADE = "FOTMOB-RAW-DETAIL-DOWNGRADE-DECISION-NO-WRITE"

ALLOWED_NEXT = [
    NEXT_PHASE_RECONSTRUCTION,
    NEXT_PHASE_ADAPTER,
    NEXT_PHASE_MAPPING,
    NEXT_PHASE_DOWNGRADE,
]
FORBIDDEN_REC = [
    "DIRECT-RAW-WRITE",
    "RAW-JSON-WRITE",
    "RAW-WRITE-EXECUTION",
    "BROWSER-AUTOMATION",
    "COOKIE-HARVEST",
    "CAPTCHA-BYPASS",
    "PROXY-ROTATION",
]

# Safe reuse assets
SAFE_REUSE_ASSETS = [
    {
        "asset_id": "parser-nextdata",
        "category": "parser",
        "path": "src/parsers/fotmob/NextDataParser.js",
        "symbol": "transformToApiFormat, extractFromHtml, validateNextDataStructure",
        "reason": "Pure function; regex-extracts __NEXT_DATA__ from HTML; transforms props.pageProps.content/general/header into apiFormat. No network, no browser, no DB.",
        "recommended_use": "Parse HTML/JSON responses from any FotMob data source into canonical apiFormat",
    },
    {
        "asset_id": "parser-match",
        "category": "parser",
        "path": "src/parsers/fotmob/MatchParser.js",
        "symbol": "parseMatchData, firstValue, resolveMatchId",
        "reason": "Pure function; cascading resolution of matchId/general/header/status; handles nested payload shapes.",
        "recommended_use": "Parse match-level metadata regardless of data source format",
    },
    {
        "asset_id": "parser-stats",
        "category": "parser",
        "path": "src/parsers/fotmob/MatchStatsParser.js",
        "symbol": "extractMatchStats, normalizeStat",
        "reason": "Pure function; probes multiple stats paths (content.stats, stats, matchStats); normalizes stat rows with flexible key mapping.",
        "recommended_use": "Extract and normalize match statistics from any source",
    },
    {
        "asset_id": "parser-team",
        "category": "parser",
        "path": "src/parsers/fotmob/TeamParser.js",
        "symbol": "parseTeamData",
        "reason": "Pure function; extracts team identity data from general/header.",
        "recommended_use": "Parse team identity fields",
    },
    {
        "asset_id": "parser-player",
        "category": "parser",
        "path": "src/parsers/fotmob/PlayerParser.js",
        "symbol": "parsePlayerData",
        "reason": "Pure function; extracts player-level data from lineup sections.",
        "recommended_use": "Parse player identity and stats from lineup",
    },
    {
        "asset_id": "parser-xg",
        "category": "parser",
        "path": "src/parsers/fotmob/XGExtractor.js",
        "symbol": "extractAllStats, extractXG",
        "reason": "Pure function; extracts xG/expectedGoals from stats/shotmap sections.",
        "recommended_use": "Extract expected goals data from match statistics",
    },
    {
        "asset_id": "parser-league",
        "category": "parser",
        "path": "src/parsers/fotmob/LeagueParser.js",
        "symbol": "parseLeagueData",
        "reason": "Pure function; extracts league/tournament metadata.",
        "recommended_use": "Parse league and tournament context",
    },
    {
        "asset_id": "schema-raw-payloads",
        "category": "schema",
        "path": "database/migrations/V26.5__create_fotmob_raw_match_payloads.sql",
        "symbol": "CREATE TABLE fotmob_raw_match_payloads",
        "reason": "Clean DB schema for storing raw __NEXT_DATA__ and pageProps as JSONB with proper indexes and unique constraints.",
        "recommended_use": "Reuse table structure for future raw JSON storage (not for direct DB write in this phase)",
    },
    {
        "asset_id": "schema-raw-match-data",
        "category": "schema",
        "path": "database/migrations/V12.6__allow_numeric_fotmob_ids_in_raw_match_data.sql",
        "symbol": "ALTER TABLE raw_match_data match_id constraint",
        "reason": "Allows both legacy 3-segment and plain numeric FotMob IDs.",
        "recommended_use": "Reuse ID format flexibility for future match_id storage",
    },
    {
        "asset_id": "fixture-match-success",
        "category": "fixture",
        "path": "tests/fixtures/match_success.json",
        "symbol": "match_success.json full payload structure",
        "reason": "Complete synthetic payload: content.stats(xG), content.lineup(11+subs), content.shotmap(xG+outcome), content.events, general.homeTeam/awayTeam, header.tournament/venue. Average size aligned with historical 205KB.",
        "recommended_use": "Use as canonical payload shape reference; adapt new data sources to this structure",
    },
    {
        "asset_id": "validation-hash",
        "category": "validation",
        "path": "src/infrastructure/services/FotMobRawDetailFetcher.js",
        "symbol": "sha256CanonicalJson, canonicalizeJson, HASH_STRATEGY_STABLE_RAW_PAYLOAD_V1",
        "reason": "Pure functions for SHA-256 hashing of canonical JSON; key-sorted recursive canonicalization; stable hash excludes metadata fields.",
        "recommended_use": "Reuse hash strategy for payload integrity verification",
    },
    {
        "asset_id": "validation-shape",
        "category": "validation",
        "path": "src/infrastructure/services/FotMobRawDetailFetcher.js",
        "symbol": "validateCanonicalRawDataShape, looksLikeValidRawDetail",
        "reason": "Pure validation functions; checks _meta/content/general/header/matchId keys; checks numeric matchId; checks external_id/home_team/away_team markers.",
        "recommended_use": "Reuse shape validation to verify future payloads match canonical structure",
    },
    {
        "asset_id": "validation-status",
        "category": "validation",
        "path": "src/infrastructure/services/FotMobRawDetailFetcher.js",
        "symbol": "classifyStatus, isBlockHttpStatus (403, 429)",
        "reason": "Pure status classification functions; no browser/cookie/session dependency.",
        "recommended_use": "Reuse HTTP status classification for future data source evaluation",
    },
    {
        "asset_id": "report-collection",
        "category": "report",
        "path": "docs/_reports/FOTMOB_COLLECTION_REPORT.md",
        "symbol": "Collection health report with schema diff evidence",
        "reason": "Historical evidence: 2,501 raw JSON rows, 64.58% coverage, 205KB avg, lineup/stats/details/teams present.",
        "recommended_use": "Reference for historical payload shape and collection metrics",
    },
    {
        "asset_id": "report-adg60",
        "category": "report",
        "path": "docs/_reports/FOTMOB_ADG60_RAW_JSON_DB_STORAGE_REVIEW_NO_FEATURE_PARSE.md",
        "symbol": "ADG60 storage review: 32 samples, JSONB structural integrity confirmed",
        "reason": "Confirms next_data_json and page_props_json parse successfully; raw_layer_db_ready=true.",
        "recommended_use": "Reference for JSONB storage architecture validation",
    },
    {
        "asset_id": "state-current",
        "category": "report",
        "path": "docs/data/FOTMOB_CURRENT_STATE.md",
        "symbol": "Current pipeline state: raw_write_ready_count=0, ADG59B completed",
        "reason": "Authoritative current-state document; lists active guards, blockers, forbidden operations.",
        "recommended_use": "Reference for current pipeline governance and authorization requirements",
    },
]

# Read-only reference assets (high risk — browser/session/cookie/anti-bot)
READ_ONLY_ASSETS = [
    {
        "asset_id": "risk-fotmob-api-client",
        "category": "browser_session",
        "path": "src/infrastructure/network/FotMobApiClient.js",
        "risk_reason": "Requires Playwright browser bootstrap for cf_clearance cookie capture; targets /api/data/matchDetails which returns 403 without session. Browser/session/cookie/anti-bot stack.",
        "safety_status": "read_only_reference_only",
    },
    {
        "asset_id": "risk-session-manager",
        "category": "browser_session",
        "path": "src/infrastructure/network/SessionManager.js",
        "risk_reason": "Automates Turnstile bypass; manages 22-node port map for FotMob sessions; opens visible browsers; captures and persists Cloudflare cookies.",
        "safety_status": "do_not_reactivate",
    },
    {
        "asset_id": "risk-auto-auth",
        "category": "browser_session",
        "path": "src/infrastructure/auth/AutoAuthManager.js",
        "risk_reason": "Opens visible browser for FotMob login/cookie capture; saves authenticated session state.",
        "safety_status": "do_not_reactivate",
    },
    {
        "asset_id": "risk-session-warmer",
        "category": "browser_session",
        "path": "src/infrastructure/harvesters/SessionWarmer.js",
        "risk_reason": "Progressive navigation + proxy rotation + Cloudflare cookie establishment methodology (though targets OddsPortal, technique is site-agnostic).",
        "safety_status": "read_only_reference_only",
    },
    {
        "asset_id": "risk-stealth-navigator",
        "category": "anti_bot",
        "path": "src/infrastructure/harvesters/StealthNavigator.js",
        "risk_reason": "Bezier mouse movement, scroll simulation, vision healing, CAPTCHA bypass primitives.",
        "safety_status": "do_not_reactivate",
    },
    {
        "asset_id": "risk-stealth-fingerprint",
        "category": "anti_bot",
        "path": "src/infrastructure/network/StealthFingerprint.js",
        "risk_reason": "30+ spoofed browser fingerprint pool; WebGL renderer pool; matches capture_auth.js fingerprint for FotMob.",
        "safety_status": "do_not_reactivate",
    },
    {
        "asset_id": "risk-stealth-config",
        "category": "anti_bot",
        "path": "src/infrastructure/network/enhanced_stealth_config.js",
        "risk_reason": "Enhanced stealth configuration for anti-detection.",
        "safety_status": "do_not_reactivate",
    },
    {
        "asset_id": "risk-browser-factory",
        "category": "browser_core",
        "path": "src/infrastructure/browser/BrowserFactory.js",
        "risk_reason": "Generic Playwright browser lifecycle; not FotMob-specific but enables anti-bot bypass via stealth scripts.",
        "safety_status": "read_only_reference_only",
    },
    {
        "asset_id": "risk-context-pool",
        "category": "browser_core",
        "path": "src/infrastructure/browser/ContextPoolManager.js",
        "risk_reason": "Playwright context pool management for multi-session harvesting.",
        "safety_status": "read_only_reference_only",
    },
    {
        "asset_id": "risk-fotmob-extractor",
        "category": "browser_core",
        "path": "src/infrastructure/services/FotMobExtractor.js",
        "risk_reason": "Uses Playwright browser; league-level scraping with NetworkInterceptor; browser-based DOM scanning.",
        "safety_status": "do_not_reactivate",
    },
    {
        "asset_id": "risk-network-interceptor",
        "category": "browser_core",
        "path": "src/infrastructure/services/NetworkInterceptor.js",
        "risk_reason": "Passive API endpoint discovery via Playwright page request/response events; requires browser runtime.",
        "safety_status": "read_only_reference_only",
    },
    {
        "asset_id": "risk-archive-v6",
        "category": "archive",
        "path": "archive_vault_2026/archive_v6/*",
        "risk_reason": "Full harvesting pipeline: capture_auth.js, inject_golden_cookies.js, auto_harvest_v6.js, sniffer_harvest_v6.js. Contains cookie injection, auth capture, automated harvesting with anti-bot bypass.",
        "safety_status": "do_not_reactivate",
    },
    {
        "asset_id": "risk-archive-legacy",
        "category": "archive",
        "path": "archive_vault_2026/legacy_v446/*",
        "risk_reason": "Legacy hyper_swarm_stealth.js and related scripts; massive-scale anti-bot harvesting infrastructure.",
        "safety_status": "do_not_reactivate",
    },
]

CANONICAL_SHAPE = [
    {
        "section": "general",
        "required": True,
        "evidence": "match_success.json, NextDataParser.transformToApiFormat, collection report schema diff",
        "fields": "matchId, homeTeam{id,name,shortName}, awayTeam{id,name,shortName}, league{id,name}, season, matchRound, matchTime, status, score{home,away}",
        "purpose": "Match identity and status",
    },
    {
        "section": "header",
        "required": True,
        "evidence": "match_success.json, NextDataParser.transformToApiFormat",
        "fields": "matchName, tournament, venue",
        "purpose": "Tournament and venue context",
    },
    {
        "section": "content.stats",
        "required": True,
        "evidence": "match_success.json (Possession, Shots, ShotsOnTarget, xG), NextDataParser._meta.hasStats",
        "fields": "keyed by stat name, each with home/away numeric values; xG as separate sub-section",
        "purpose": "Match statistics",
    },
    {
        "section": "content.lineup",
        "required": True,
        "evidence": "match_success.json (homeTeam/awayTeam with starters + subs), NextDataParser._meta.hasLineup",
        "fields": "homeTeam{teamId,teamName,starters[],subs[]}, awayTeam{teamId,teamName,starters[],subs[]}; each player: playerId,playerName,position,marketValue,rating",
        "purpose": "Team lineups with player details",
    },
    {
        "section": "content.shotmap",
        "required": False,
        "evidence": "match_success.json (array of shot objects), NextDataParser._meta.hasShotmap",
        "fields": "[{id,team,player,x,y,xG,outcome,minute}]",
        "purpose": "Shot map with xG coordinates",
    },
    {
        "section": "content.events",
        "required": True,
        "evidence": "match_success.json (Goal, YellowCard events with minute/score/player)",
        "fields": "[{id,type,team,player,minute,score}]",
        "purpose": "Match incidents/timeline",
    },
    {
        "section": "xG/expectedGoals",
        "required": False,
        "evidence": "match_success.json content.stats.xG, content.shotmap[].xG",
        "fields": "Stats-level xG (home/away totals) and shot-level xG (per-shot probability)",
        "purpose": "Expected goals for advanced analysis",
    },
    {
        "section": "tournament/venue",
        "required": False,
        "evidence": "match_success.json header.tournament, header.venue, _extra fields",
        "fields": "tournament{name,round}, venue{name,city,capacity}, attendance, referee, weather",
        "purpose": "Match context metadata",
    },
]

SAFETY_ALL_FALSE = dict.fromkeys(
    [
        "network_fetch_performed",
        "db_read_performed",
        "db_write_performed",
        "production_db_write_performed",
        "raw_json_write_performed",
        "feature_parse_performed",
        "scheduler_enabled",
        "browser_automation_performed",
        "browser_automation_allowed",
        "cookie_harvesting_performed",
        "cookie_harvesting_allowed",
        "captcha_bypass_performed",
        "captcha_bypass_allowed",
        "proxy_rotation_performed",
        "proxy_rotation_allowed",
        "secrets_printed",
    ],
    False,
)


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_manifest(
    args: argparse.Namespace, review_report_path: str, missing_inputs: list[str]
) -> dict[str, Any]:
    return {
        "schema_version": "fotmob_safe_parser_schema_reuse_plan_no_write_v1",
        "lifecycle": "current-state",
        "phase": PHASE,
        "run_id": args.run_id,
        "generated_at": _utc_now(),
        "mode": "offline_safe_parser_schema_reuse_plan",
        "missing_inputs": missing_inputs,
        "inherited_current_status": {
            "html_hydration_route_status": "exhausted_no_embedded_match_detail",
            "page_level_next_data_status": "no_match_detail_json_embedded",
            "endpoint_candidate_probe_result": "all_skipped_missing_parameters",
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
            "raw_json_readiness": "not_ready",
            "db_write_readiness": "blocked",
            "l2_harvesting_readiness": "blocked",
        },
        "historical_success_context": {
            "historical_raw_rows_count": 2501,
            "historical_coverage_percent": 64.58,
            "average_payload_bytes": 205773,
            "historical_success_confirmed": True,
            "historical_payload_is_match_detail": True,
        },
        "safe_reuse_assets": SAFE_REUSE_ASSETS,
        "read_only_reference_assets": READ_ONLY_ASSETS,
        "canonical_payload_shape_plan": {
            "required_sections": [s["section"] for s in CANONICAL_SHAPE if s["required"]],
            "optional_sections": [s["section"] for s in CANONICAL_SHAPE if not s["required"]],
            "field_aliases": {
                "matchId": ["match_id", "externalId", "id"],
                "homeTeam": ["home", "home_team"],
                "awayTeam": ["away", "away_team"],
                "stats": ["statistics"],
                "lineup": ["lineups"],
                "events": ["incidents", "timeline"],
            },
            "source_adapter_requirements": [
                "Map source fields to canonical general/header/content structure",
                "Normalize team identity (id + name + shortName)",
                "Normalize stat names to standard keys",
                "Preserve xG data at both aggregate and shot level",
                "Map events to type/min/player/team format",
            ],
            "validation_rules": [
                "matchId must be present and numeric/string-compatible",
                "content must have at minimum: stats OR lineup OR events",
                "general.homeTeam and general.awayTeam must be present",
                "header.tournament should be present for league matches",
            ],
        },
        "raw_write_gate": {
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
            "raw_write_allowed": False,
            "db_write_allowed": False,
            "raw_write_blocked_until_validated_payload": True,
            "required_before_raw_write": [
                "validated raw detail payload",
                "schema mapping reviewed",
                "parser test coverage",
                "no production DB write without explicit authorization",
            ],
        },
        "safety": SAFETY_ALL_FALSE,
        "embedded_review": {
            "status": "pass",
            "review_report_path": review_report_path,
        },
        "recommended_next_phase": NEXT_PHASE_RECONSTRUCTION,
    }


def enforce_safety(manifest: dict[str, Any]) -> None:
    # Check no high-risk assets in safe_reuse
    high_risk_paths = [
        "SessionManager",
        "AutoAuthManager",
        "SessionWarmer",
        "StealthNavigator",
        "StealthFingerprint",
        "enhanced_stealth_config",
        "FotMobApiClient",
        "BrowserFactory",
        "ContextPoolManager",
        "NetworkInterceptor",
        "archive_vault_2026",
        "legacy_v446",
    ]
    for asset in manifest.get("safe_reuse_assets", []):
        path = asset.get("path", "")
        for risk_path in high_risk_paths:
            if risk_path.lower() in path.lower():
                raise ValueError(f"HIGH-RISK ASSET IN SAFE_REUSE: {asset['asset_id']} ({path})")

    safety = manifest.get("safety", {})
    for flag in [
        "db_write_performed",
        "raw_json_write_performed",
        "browser_automation_performed",
        "cookie_harvesting_performed",
        "captcha_bypass_performed",
        "proxy_rotation_performed",
    ]:
        if safety.get(flag) is True:
            raise ValueError(f"safety.{flag} must remain false")

    gate = manifest.get("raw_write_gate", {})
    if gate.get("raw_write_allowed", False):
        raise ValueError("raw_write_allowed must be false")
    if gate.get("json_validated_count", 0) > 0:
        raise ValueError("json_validated_count must remain 0")

    rec = manifest.get("recommended_next_phase", "")
    if any(t in rec for t in FORBIDDEN_REC):
        raise ValueError("recommended_next_phase must not be direct raw write")


def render_report(manifest: dict[str, Any]) -> str:
    safe = manifest["safe_reuse_assets"]
    risky = manifest["read_only_reference_assets"]
    lines = [
        "<!-- markdownlint-disable MD013 MD012 -->",
        "# FotMob Safe Parser Schema Reuse Plan No Write",
        "",
        "- lifecycle: current-state",
        f"- phase: {PHASE}",
        f"- run_id: {manifest['run_id']}",
        "- mode: offline_safe_parser_schema_reuse_plan",
        "",
        "## 1. 当前阶段背景",
        "",
        "- 历史审计确认：项目过去成功采集了 2,501 条 FotMob raw detail JSON（64.58% 覆盖，平均 205KB）。",
        "- 当前保守路线（/matches/{route_code}/{match_id} HTML hydration, direct API, endpoint candidate probe）全部失败或跳过。",
        "- 本阶段整理历史资产中可安全复用的 parser/schema/fixture/validation 部分，不恢复任何 browser/session/cookie/anti-bot 体系。",
        "",
        "## 2. 安全可复用资产清单",
        "",
        "| Asset ID | Category | Path | Symbol | Recommended Use |",
        "|---|---|---|---|---|",
        *[
            f"| {a['asset_id']} | {a['category']} | {a['path']} | {a['symbol']} | {a['recommended_use']} |"
            for a in safe
        ],
        "",
        f"Total safe reuse: {len(safe)}",
        "",
        "## 3. 只能只读参考资产清单",
        "",
        "| Asset ID | Category | Path | Risk Reason | Safety Status |",
        "|---|---|---|---|---|",
        *[
            f"| {a['asset_id']} | {a['category']} | {a['path']} | {a['risk_reason']} | {a['safety_status']} |"
            for a in risky
        ],
        "",
        f"Total read-only reference: {len(risky)}",
        "",
        "## 4. Canonical Payload Shape 草案",
        "",
        "| Section | Required | Evidence | Purpose |",
        "|---|---|---|---|",
        *[
            f"| {s['section']} | {s['required']} | {s['evidence']} | {s['purpose']} |"
            for s in CANONICAL_SHAPE
        ],
        "",
        "## 5. Source Adapter 设计原则",
        "",
        "- future FotMob source → map to canonical general/header/content",
        "- alternative source → adapter layer normalizes equivalent fields",
        "- paid source → same canonical mapping, different auth layer",
        "- historical fixture → validate against canonical shape",
        "",
        "## 6. Raw Write Gate",
        "",
        "- json_validated_count: 0",
        "- raw_write_eligible_count: 0",
        "- raw_write_allowed: false",
        "- db_write_allowed: false",
        "- raw_write_blocked_until_validated_payload: true",
        "- 需要 validated raw detail payload + schema mapping review + parser test coverage + explicit authorization",
        "",
        "## 7. 推荐下一步",
        "",
        f"- **{manifest['recommended_next_phase']}**",
        "",
        "本阶段明确：不恢复旧浏览器/cookie/anti-bot体系，不使用 Playwright，不抓 cookie，不绕反爬，不写 DB，不 raw write。只复用安全 parser/schema/fixture/validation 资产。",
    ]
    return "\n".join(lines)


def render_review(manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "<!-- markdownlint-disable MD013 MD012 -->",
            "# FotMob Safe Parser Schema Reuse Plan No Write Review",
            "",
            "- lifecycle: current-state",
            f"- phase: {PHASE} review",
            f"- run_id: {manifest['run_id']}",
            "",
            "- [pass] #1453 merged status inherited",
            "- [pass] historical success acknowledged",
            "- [pass] current conservative route failure acknowledged",
            f"- [pass] safe reuse assets identified: {len(manifest['safe_reuse_assets'])}",
            f"- [pass] read-only reference assets identified: {len(manifest['read_only_reference_assets'])}",
            "- [pass] no high-risk asset marked safe_reuse",
            "- [pass] canonical payload shape plan generated",
            "- [pass] raw write gate remains blocked",
            "- [pass] json_validated_count=0",
            "- [pass] raw_write_eligible_count=0",
            "- [pass] network_fetch_performed=false",
            "- [pass] db_read_performed=false",
            "- [pass] db_write_performed=false",
            "- [pass] browser_automation_performed=false",
            "- [pass] cookie_harvesting_performed=false",
            "- [pass] captcha_bypass_performed=false",
            "- [pass] proxy_rotation_performed=false",
            "- [pass] no direct raw write recommendation",
            "- [pass] recommended next phase safe",
            "",
            "## Overall: pass",
        ]
    )


def render_next_plan(_manifest: dict[str, Any]) -> str:
    return "\n".join(
        [
            "<!-- markdownlint-disable MD013 MD012 -->",
            "# FotMob Payload Shape Reconstruction Next Plan",
            "",
            "- lifecycle: current-state",
            f"- phase: {NEXT_PHASE_RECONSTRUCTION}",
            f"- source_phase: {PHASE}",
            "",
            "## Why Payload Shape Reconstruction",
            "",
            "- 历史有 2,501 条 raw JSON 但没有 canonical shape 文档。",
            "- 测试 fixture (match_success.json) 只覆盖部分结构。",
            "- 不同 FotMob API 版本的 payload 形状可能不同。",
            "- 需要系统性地重构 canonical payload shape 作为未来所有 parser 的接口契约。",
            "",
            "## Reconstruction Tasks",
            "",
            "1. Validate canonical shape against match_success.json fixture",
            "2. Validate canonical shape against FotMobRawDetailFetcher hash/validation expectations",
            "3. Document field aliases (matchId vs external_id vs id)",
            "4. Document type constraints (numeric IDs, score strings, coordinate types)",
            "5. Create lightweight canonical schema definition (JSON Schema or TypeScript interface)",
            "6. Ensure parser tests cover all canonical sections",
            "",
            "## Safety",
            "",
            "- 不访问网络",
            "- 不读 DB",
            "- 不写 DB",
            "- 不使用 browser automation",
            "- 不抓 cookie",
            "- 不绕反爬",
            "- 只基于 repo 内已有 fixture/report/代码",
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
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-manifest", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--review-report", required=True)
    p.add_argument("--next-plan", required=True)
    p.add_argument("--run-id", required=True)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        manifest = build_manifest(args, str(Path(args.review_report)), [])
        enforce_safety(manifest)
        write_outputs(args, manifest)
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("PASS: safe parser schema reuse plan no-write complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
