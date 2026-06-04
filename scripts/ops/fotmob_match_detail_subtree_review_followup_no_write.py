#!/usr/bin/env python3
"""Offline FotMob match detail subtree review follow-up.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-DETAIL-SUBTREE-REVIEW-FOLLOWUP-NO-WRITE

Reviews the negative #1447 subtree extraction result without network, body
reads, DB access, raw JSON persistence, or parser/feature execution.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-DETAIL-SUBTREE-REVIEW-FOLLOWUP-NO-WRITE"
SCHEMA = "fotmob_match_detail_subtree_review_followup_no_write_v1"
MODE = "offline_subtree_review_followup"
NEXT_PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-KEYSPACE-REVIEW-NO-WRITE"

BEST_GENERIC_PATH = "props.pageProps.fallback.notableMatches:en:USA"
BEST_GENERIC_STATE = "generic_or_irrelevant_subtree"
SELECTED_MATCH_IDS = ["4813722", "4813492"]
SELECTED_ROUTE_CODES = ["2ygkcb", "2ynv4k"]

SAFETY = {
    "network_fetch_performed": False,
    "response_body_read": False,
    "bounded_body_read_performed": False,
    "full_body_read_performed": False,
    "full_html_saved": False,
    "raw_response_body_saved": False,
    "html_body_saved": False,
    "full_next_data_saved": False,
    "candidate_subtree_value_saved": False,
    "raw_json_write_performed": False,
    "db_read_performed": False,
    "db_write_performed": False,
    "production_db_write_performed": False,
    "fotmob_raw_match_payloads_write_performed": False,
    "raw_match_data_write_performed": False,
    "feature_parse_performed": False,
    "scheduler_enabled": False,
    "raw_write_ready_marked": False,
    "browser_automation_performed": False,
    "captcha_bypass_performed": False,
    "proxy_rotation_performed": False,
}

HISTORICAL_FILES = [
    "src/parsers/fotmob/NextDataParser.js",
    "src/parsers/fotmob/MatchParser.js",
    "src/parsers/fotmob/TeamParser.js",
    "src/parsers/fotmob/MatchStatsParser.js",
    "src/infrastructure/services/FotMobRawDetailFetcher.js",
    "scripts/ops/pageprops_v2_no_write_preview.js",
    "scripts/ops/pageprops_v2_target_identity_reconciliation_plan.js",
    "docs/_reports/FOTMOB_HYDRATION_STRUCTURE_DECISION.md",
    "docs/_reports/FOTMOB_MATCH_DETAIL_CANDIDATE_DECISION.md",
]


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"{label} missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text_if_exists(root: Path, rel_path: str) -> str:
    path = root / rel_path
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def extract_controlled_inheritance(controlled: dict[str, Any]) -> dict[str, Any]:
    summary = controlled.get("extraction_summary", {})
    decision = controlled.get("match_detail_subtree_decision", {})
    readiness = controlled.get("raw_write_readiness", {})
    inherited = {
        "fallback_present_count": summary.get("fallback_present_count"),
        "target_match_id_seen_count": summary.get("target_match_id_seen_count"),
        "strong_candidate_count": summary.get("strong_candidate_count"),
        "weak_candidate_count": summary.get("weak_candidate_count"),
        "partial_candidate_count": summary.get("partial_candidate_count"),
        "generic_or_irrelevant_count": summary.get("generic_or_irrelevant_count"),
        "best_candidate_path": decision.get("best_candidate_path"),
        "best_candidate_score": decision.get("best_candidate_score"),
        "best_candidate_state": decision.get("best_candidate_state"),
        "json_validated_count": readiness.get("json_validated_count"),
        "raw_write_eligible_count": readiness.get("raw_write_eligible_count"),
    }
    expected = {
        "fallback_present_count": 2,
        "target_match_id_seen_count": 0,
        "strong_candidate_count": 0,
        "weak_candidate_count": 0,
        "partial_candidate_count": 0,
        "generic_or_irrelevant_count": 2,
        "best_candidate_path": BEST_GENERIC_PATH,
        "best_candidate_score": -5,
        "best_candidate_state": BEST_GENERIC_STATE,
        "json_validated_count": 0,
        "raw_write_eligible_count": 0,
    }
    mismatches = {
        key: {"expected": value, "actual": inherited.get(key)}
        for key, value in expected.items()
        if inherited.get(key) != value
    }
    if mismatches:
        raise ValueError(f"#1447 controlled extraction inheritance mismatch: {mismatches}")
    return inherited


def build_historical_code_review(root: Path) -> dict[str, Any]:
    reviewed = [path for path in HISTORICAL_FILES if (root / path).exists()]
    texts = {path: _read_text_if_exists(root, path) for path in reviewed}
    relevant_paths = []
    if "props.pageProps.content" in texts.get("src/parsers/fotmob/NextDataParser.js", ""):
        relevant_paths.append(
            {
                "file": "src/parsers/fotmob/NextDataParser.js",
                "evidence": "transformToApiFormat expects props.pageProps.content/general/header",
                "candidate_paths": [
                    "props.pageProps.content",
                    "props.pageProps.general",
                    "props.pageProps.header",
                ],
            }
        )
    if "rawData?.props?.pageProps" in texts.get("src/parsers/fotmob/MatchParser.js", ""):
        relevant_paths.append(
            {
                "file": "src/parsers/fotmob/MatchParser.js",
                "evidence": "match parser unwraps props.pageProps through NextDataParser",
                "candidate_paths": ["content.general", "content.header", "general.matchId"],
            }
        )
    if "rawData.content?.stats" in texts.get("src/parsers/fotmob/MatchStatsParser.js", ""):
        relevant_paths.append(
            {
                "file": "src/parsers/fotmob/MatchStatsParser.js",
                "evidence": "stats parser expects stats under rawData.stats or content.stats",
                "candidate_paths": ["content.stats", "stats", "matchStats"],
            }
        )
    if "buildFotMobMatchUrl" in texts.get(
        "src/infrastructure/services/FotMobRawDetailFetcher.js", ""
    ):
        relevant_paths.append(
            {
                "file": "src/infrastructure/services/FotMobRawDetailFetcher.js",
                "evidence": "legacy html_hydration fetcher transforms hydrated page data into content/general/header/matchId",
                "candidate_paths": ["content", "general", "header", "matchId"],
            }
        )
    if "function getPageProps" in texts.get("scripts/ops/pageprops_v2_no_write_preview.js", ""):
        relevant_paths.append(
            {
                "file": "scripts/ops/pageprops_v2_no_write_preview.js",
                "evidence": "pageProps v2 preview extracts __NEXT_DATA__.props.pageProps and computes metadata/hash",
                "candidate_paths": ["props.pageProps", "props.pageProps.content"],
            }
        )

    return {
        "files_reviewed": reviewed,
        "relevant_paths_found": relevant_paths,
        "suspected_existing_parser_paths": [
            "props.pageProps.content",
            "props.pageProps.general",
            "props.pageProps.header",
            "content.matchFacts",
            "content.stats",
            "content.lineup",
            "header.teams",
            "general.homeTeam",
            "general.awayTeam",
        ],
        "missing_evidence": [
            "no historical parser treats props.pageProps.fallback.notableMatches as match detail",
            "no target match_id was observed in #1447 candidate metadata",
            "no team-name/detail-key evidence was observed under notableMatches",
            "no json validation or raw-write eligibility exists",
        ],
    }


def build_route_variant_review(seed_manifest: dict[str, Any]) -> dict[str, Any]:
    parsed = seed_manifest.get("parsed_seeds", [])
    target_seed_paths = [
        {
            "match_id": str(item.get("fotmob_match_id")),
            "locale": item.get("locale"),
            "match_slug": item.get("match_slug"),
            "route_code": item.get("route_code"),
        }
        for item in parsed
        if str(item.get("fotmob_match_id")) in SELECTED_MATCH_IDS
    ]
    candidates = [
        {
            "variant": "/matches/{route_code}/{match_id}",
            "recommendation": "keep",
            "reason": "current working route parses __NEXT_DATA__/pageProps/fallback but only found generic notableMatches",
        },
        {
            "variant": "/zh-Hans/matches/{route_code}/{match_id}",
            "recommendation": "review next",
            "reason": "target user seeds were supplied with zh-Hans locale and should be compared as metadata only",
        },
        {
            "variant": "/en/matches/{route_code}/{match_id}",
            "recommendation": "review next",
            "reason": "English locale variant may change hydration keyspace or fallback cache keys",
        },
        {
            "variant": "original user URL path without fragment",
            "recommendation": "review next",
            "reason": "seed slug paths provide canonical slug evidence without using the fragment as a request path",
        },
        {
            "variant": "/matches/{slug}/{route_code}",
            "recommendation": "defer unless slug evidence is used",
            "reason": "supported by seed URL shape, but should only be executed after keyspace plan selects slug routes",
        },
    ]
    return {
        "target_seed_paths": target_seed_paths,
        "candidates": candidates,
        "recommended": candidates[:4],
        "deferred": [candidates[4]],
        "rejected": [
            {
                "variant": "/api/matchDetails or /api/data/matchDetails",
                "reason": "prior phases observed 404/403 and this follow-up forbids API endpoint probing",
            },
            {
                "variant": "browser/cookie/session route",
                "reason": "browser automation, login, cookie/session capture, proxy, and bypass behavior are forbidden",
            },
        ],
    }


def build_next_keyspace_review_plan() -> dict[str, Any]:
    return {
        "phase": NEXT_PHASE,
        "max_samples": 2,
        "max_network_requests": 2,
        "max_body_bytes": 524288,
        "max_key_paths_recorded": 500,
        "max_value_preview_chars": 0,
        "max_scan_depth": 12,
        "no_value_persistence": True,
        "route_variants": [
            "/matches/{route_code}/{match_id}",
            "/zh-Hans/matches/{route_code}/{match_id}",
            "/en/matches/{route_code}/{match_id}",
            "original user URL path without fragment",
        ],
        "metadata_only": [
            "key path",
            "data type",
            "depth",
            "approximate size",
            "key name",
            "marker flags",
            "score",
            "classification",
            "route variant",
        ],
        "forbidden_persistence": [
            "value content",
            "subtree value",
            "full JSON",
            "full HTML",
            "DB write",
        ],
    }


def build_manifest(
    *,
    run_id: str,
    controlled: dict[str, Any],
    subtree_plan: dict[str, Any],
    hydration_validation: dict[str, Any],
    seed_manifest: dict[str, Any],
    root: Path,
    review_report_path: str,
) -> dict[str, Any]:
    inherited = extract_controlled_inheritance(controlled)
    historical = build_historical_code_review(root)
    route_review = build_route_variant_review(seed_manifest)
    next_plan = build_next_keyspace_review_plan()
    manifest = {
        "schema_version": SCHEMA,
        "lifecycle": "current-state",
        "phase": PHASE,
        "run_id": run_id,
        "generated_at": _utc_now(),
        "mode": MODE,
        "inherited_controlled_subtree_extraction": inherited,
        "negative_findings": {
            "notable_matches_is_not_match_detail": True,
            "target_match_id_missing": True,
            "fallback_scan_too_narrow_possible": True,
            "route_variant_review_required": True,
            "keyspace_review_required": True,
            "route_template_still_current_baseline": controlled.get("extraction_selection", {}).get(
                "route_template"
            ),
            "prior_root_path": subtree_plan.get("subtree_extraction_plan", {}).get("root_path"),
            "prior_pageProps_keys": hydration_validation.get("validation_results", [{}])[0].get(
                "pageProps_key_names", []
            ),
        },
        "historical_code_review": historical,
        "route_variant_review": route_review,
        "next_keyspace_review_plan": next_plan,
        "raw_write_readiness": {
            "json_validated_count": 0,
            "raw_write_eligible_count": 0,
            "raw_write_blocked_until_json_validated": True,
            "keyspace_review_required": True,
        },
        "safety": dict(SAFETY),
        "embedded_review": {
            "subtree_review_followup_status": "pass",
            "review_report_path": review_report_path,
        },
        "recommended_next_phase": NEXT_PHASE,
    }
    enforce_safety(manifest)
    return manifest


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def _path_for_report(path: Path) -> str:
    return str(path).replace("\\", "/")


def render_report(manifest: dict[str, Any]) -> str:
    inherited = manifest["inherited_controlled_subtree_extraction"]
    historical = manifest["historical_code_review"]
    route_review = manifest["route_variant_review"]
    next_plan = manifest["next_keyspace_review_plan"]
    relevant = ", ".join(item["file"] for item in historical["relevant_paths_found"])
    return "\n".join(
        [
            "<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->",
            "# FotMob Match Detail Subtree Review Follow-Up No Write",
            "",
            "- lifecycle: current-state",
            f"- phase: {PHASE}",
            f"- run_id: {manifest['run_id']}",
            "- mode: offline_subtree_review_followup",
            "",
            "## 当前阶段背景",
            "",
            "- #1447 已完成 controlled subtree extraction no-write，并给出负向结果。",
            "- 本阶段没有联网、没有读取 HTML body、没有保存 HTML body、没有保存 NEXT_DATA、没有保存 raw JSON、没有写 DB。",
            "- 目标是复盘为什么只命中 notableMatches，并规划下一阶段 keyspace review no-write。",
            "",
            "## #1447 Negative Finding Inheritance",
            "",
            f"- fallback_present_count: {inherited['fallback_present_count']}",
            f"- target_match_id_seen_count: {inherited['target_match_id_seen_count']}",
            f"- strong_candidate_count: {inherited['strong_candidate_count']}",
            f"- weak_candidate_count: {inherited['weak_candidate_count']}",
            f"- partial_candidate_count: {inherited['partial_candidate_count']}",
            f"- generic_or_irrelevant_count: {inherited['generic_or_irrelevant_count']}",
            f"- best_candidate_path: {inherited['best_candidate_path']}",
            f"- best_candidate_score: {inherited['best_candidate_score']}",
            "",
            "## Why NotableMatches Is Not Match Detail",
            "",
            "- notableMatches 是通用推荐/导航 fallback key，不含目标 match_id、球队名或 header/general/content/matchFacts/stats/lineup/events/teams。",
            "- target_match_id_seen_count=0 是关键阻断：没有目标比赛身份，不能把任何 subtree 视为已验证详情。",
            "- #1447 的 score=-5，state=generic_or_irrelevant_subtree，说明当前路径只应作为排除项。",
            "",
            "## Route / Locale / Keyspace Review",
            "",
            "- 当前结果可能来自 route/locale/header 返回的通用 fallback，也可能是只从 props.pageProps/fallback 扫描导致范围过窄。",
            "- 仍建议下一阶段先保持 max_body_bytes=524288：#1447 两个 response 均低于 512KB，问题不是 body 截断。",
            "- 下一阶段应扫描 bounded __NEXT_DATA__ 的 top-level keyspace metadata，而不是继续只扫 fallback.notableMatches。",
            "- slug、route code、team names 应作为 metadata scoring signal；也要检查 SWR/Apollo/Relay/react-query/dehydratedState/fallback cache key 名称。",
            "",
            "## Historical Code Review",
            "",
            f"- files_reviewed: {len(historical['files_reviewed'])}",
            f"- relevant_paths_found: {relevant}",
            "- suspected parser paths: props.pageProps.content, props.pageProps.general, props.pageProps.header, content.matchFacts, content.stats, content.lineup。",
            "- missing evidence: 没有历史 parser 证明 props.pageProps.fallback.notableMatches 是 match detail。",
            "",
            "## Route Variant Review",
            "",
            "| Variant | Recommendation | Reason |",
            "|---|---|---|",
            *[
                f"| {item['variant']} | {item['recommendation']} | {item['reason']} |"
                for item in route_review["candidates"]
            ],
            "",
            "## Keyspace Review Next Plan",
            "",
            f"- phase: {next_plan['phase']}",
            f"- max_samples: {next_plan['max_samples']}",
            f"- max_network_requests: <= {next_plan['max_network_requests']}",
            f"- max_body_bytes: <= {next_plan['max_body_bytes']}",
            f"- max_key_paths_recorded: <= {next_plan['max_key_paths_recorded']}",
            f"- max_scan_depth: <= {next_plan['max_scan_depth']}",
            "- value persistence: forbidden",
            "",
            "## Raw Write Readiness Gate",
            "",
            "- json_validated_count: 0",
            "- raw_write_eligible_count: 0",
            "- raw_write_blocked_until_json_validated: true",
            "- keyspace_review_required: true",
            "- 下一阶段只是 hydration keyspace review no-write，仍然不是 raw JSON 入库。",
            "",
            "## No-Write Safety Review",
            "",
            "- network_fetch_performed: false",
            "- response_body_read: false",
            "- html_body_saved: false",
            "- full_next_data_saved: false",
            "- raw_json_write_performed: false",
            "- db_write_performed: false",
            "- scheduler_enabled: false",
            "- feature_parse_performed: false",
            "- browser_automation_performed: false",
            "- captcha_bypass_performed: false",
            "- proxy_rotation_performed: false",
            "",
            "## Remaining Blockers",
            "",
            "- 尚未找到包含目标 match_id 的 match detail subtree。",
            "- notableMatches 已排除，但完整 bounded keyspace 仍未复盘。",
            "- route variant 只完成规划，尚未执行下一阶段受控 review。",
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
            "# FotMob Match Detail Subtree Review Follow-Up No Write Review",
            "",
            "- lifecycle: current-state",
            f"- phase: {PHASE} review",
            f"- run_id: {manifest['run_id']}",
            "",
            "- [pass] #1447 negative finding inherited",
            "- [pass] notableMatches marked not match detail",
            "- [pass] target_match_id_seen_count=0 acknowledged",
            "- [pass] keyspace review required",
            "- [pass] route variant review required",
            "- [pass] next keyspace review plan generated",
            "- [pass] no network",
            "- [pass] no response body read",
            "- [pass] no HTML body saved",
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


def render_next_plan(manifest: dict[str, Any]) -> str:
    next_plan = manifest["next_keyspace_review_plan"]
    routes = manifest["route_variant_review"]["recommended"]
    return "\n".join(
        [
            "<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->",
            "# FotMob Hydration Keyspace Review Next Plan",
            "",
            "- lifecycle: current-state",
            f"- phase: {NEXT_PHASE}",
            f"- source_phase: {PHASE}",
            "",
            "## Why Keyspace Review Is Needed",
            "",
            "- #1447 只命中 props.pageProps.fallback.notableMatches:en:USA，且 score=-5。",
            "- notableMatches 是 generic notable matches，不是 match detail；它缺少目标 match_id、球队名和详情模块 key。",
            "- 继续只扫 fallback.notableMatches 会重复命中已排除路径，不能推进 raw write readiness。",
            "",
            "## Next Scan Scope",
            "",
            "- bounded __NEXT_DATA__ keyspace metadata review。",
            "- 记录 key path、data type、depth、approximate size、key name、marker flags、score、classification、route variant。",
            "- 不保存 value，不保存 subtree values，不保存 full JSON，不保存 full HTML。",
            "",
            "## Route Variants",
            "",
            "| Variant | Recommendation | Reason |",
            "|---|---|---|",
            *[
                f"| {item['variant']} | {item['recommendation']} | {item['reason']} |"
                for item in routes
            ],
            "",
            "## Bounds",
            "",
            f"- max_samples: {next_plan['max_samples']}",
            f"- max_network_requests: <= {next_plan['max_network_requests']}",
            f"- max_body_bytes: <= {next_plan['max_body_bytes']}",
            f"- max_key_paths_recorded: <= {next_plan['max_key_paths_recorded']}",
            "- max_value_preview_chars: 0",
            f"- max_scan_depth: <= {next_plan['max_scan_depth']}",
            "",
            "## Forbidden",
            "",
            "- 不保存 full HTML",
            "- 不保存 full NEXT_DATA",
            "- 不保存 raw JSON",
            "- 不保存 subtree values",
            "- 不写 DB",
            "- 不启用 scheduler",
            "- 不使用 browser automation",
            "- 不绕过反爬",
            "",
            "## Success Criteria",
            "",
            "- 找到非 notableMatches 的 candidate key path metadata。",
            "- 发现含 match/detail/header/content/general/stats/events/lineup/matchFacts marker 的路径。",
            "- 仍保持 json_validated_count=0 和 raw_write_eligible_count=0。",
            "",
            "## Failure Criteria",
            "",
            "- 两个样本仍只出现 generic notableMatches / translations / static config。",
            "- route variants 没有增加任何 detail keyspace evidence。",
            "",
            "## Recommended Next Step",
            "",
            f"- **{NEXT_PHASE}**",
        ]
    )


def enforce_safety(manifest: dict[str, Any]) -> None:
    rec = manifest.get("recommended_next_phase", "")
    forbidden_rec = ["DIRECT-RAW-WRITE", "RAW-JSON-WRITE", "RAW-WRITE-EXECUTION"]
    if any(token in rec for token in forbidden_rec):
        raise ValueError("recommended_next_phase must not be direct raw write")
    safety = manifest.get("safety", {})
    forbidden_true_flags = [
        "network_fetch_performed",
        "response_body_read",
        "html_body_saved",
        "full_next_data_saved",
        "raw_json_write_performed",
        "db_write_performed",
    ]
    for flag in forbidden_true_flags:
        if safety.get(flag) is True:
            raise ValueError(f"{flag} must remain false")
    readiness = manifest.get("raw_write_readiness", {})
    if readiness.get("raw_write_eligible_count") != 0:
        raise ValueError("raw_write_eligible_count must remain 0")
    if readiness.get("json_validated_count") != 0:
        raise ValueError("json_validated_count must remain 0")


def write_outputs(args: argparse.Namespace, manifest: dict[str, Any]) -> None:
    output_manifest = Path(args.output_manifest)
    report = Path(args.report)
    review = Path(args.review_report)
    next_plan = Path(args.next_plan)
    for path in [output_manifest, report, review, next_plan]:
        path.parent.mkdir(parents=True, exist_ok=True)
    output_manifest.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    report.write_text(render_report(manifest) + "\n", encoding="utf-8")
    review.write_text(render_review(manifest) + "\n", encoding="utf-8")
    next_plan.write_text(render_next_plan(manifest) + "\n", encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--controlled-subtree-manifest", required=True)
    parser.add_argument("--subtree-plan-manifest", required=True)
    parser.add_argument("--hydration-validation-manifest", required=True)
    parser.add_argument("--seed-manifest", required=True)
    parser.add_argument("--output-manifest", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--review-report", required=True)
    parser.add_argument("--next-plan", required=True)
    parser.add_argument("--run-id", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = Path(__file__).resolve().parents[2]
    try:
        controlled = _load_json(
            Path(args.controlled_subtree_manifest), "controlled subtree manifest"
        )
        subtree_plan = _load_json(Path(args.subtree_plan_manifest), "subtree plan manifest")
        hydration_validation = _load_json(
            Path(args.hydration_validation_manifest),
            "hydration validation manifest",
        )
        seed_manifest = _load_json(Path(args.seed_manifest), "seed manifest")
        manifest = build_manifest(
            run_id=args.run_id,
            controlled=controlled,
            subtree_plan=subtree_plan,
            hydration_validation=hydration_validation,
            seed_manifest=seed_manifest,
            root=root,
            review_report_path=_path_for_report(Path(args.review_report)),
        )
        write_outputs(args, manifest)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("PASS: offline subtree review follow-up no-write complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
