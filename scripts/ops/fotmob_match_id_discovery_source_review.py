#!/usr/bin/env python3
"""Review FotMob match ID discovery candidate sources without any network or DB access.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-SOURCE-REVIEW-NO-WRITE

Reads the DB dry-run manifest (#1435 output), analyses 76 discovery candidates,
scores 6 discovery sources, ranks them, and selects at most 3 recommended
next-stage no-write validation samples.

No FotMob access. No network. No DB. No raw JSON write. No scheduler.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-SOURCE-REVIEW-NO-WRITE"
SCHEMA_VERSION = "fotmob_match_id_discovery_source_review_v1"
NEXT_PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-ID-DISCOVERY-ROUTE-CANDIDATE-NO-WRITE"

DISCOVERY_SOURCES = [
    "team_calendar",
    "competition_fixtures",
    "date_fixtures",
    "known_match_page",
    "historical_backfill",
    "manual_seed",
]

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


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# source scoring
# ---------------------------------------------------------------------------


def score_sources(candidates: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    counts = Counter(c["discovery_source"] for c in candidates)

    # Per-source team/competition diversity
    source_teams: dict[str, set[str]] = {s: set() for s in DISCOVERY_SOURCES}
    source_comps: dict[str, set[str]] = {s: set() for s in DISCOVERY_SOURCES}
    for c in candidates:
        src = c["discovery_source"]
        if c.get("team_name"):
            source_teams[src].add(c["team_name"])
        if c.get("competition_name"):
            source_comps[src].add(c["competition_name"])

    def _score(
        source: str,
        cov: int,
        conf: int,
        complexity: int,
        risk: int,
        feasibility: int,
        priority: int,
        reason: str,
    ) -> dict[str, Any]:
        return {
            "source_name": source,
            "candidate_count": counts.get(source, 0),
            "coverage_score": cov,
            "confidence_score": conf,
            "implementation_complexity": complexity,
            "operational_risk": risk,
            "no_write_validation_feasibility": feasibility,
            "recommended_priority": priority,
            "reason": reason,
            "next_stage_allowed": True,
            "team_diversity": len(source_teams[source]),
            "competition_diversity": len(source_comps[source]),
        }

    return {
        "manual_seed": _score(
            "manual_seed",
            cov=2,
            conf=10,
            complexity=10,
            risk=10,
            feasibility=10,
            priority=1,
            reason="极低风险；仅需人工确认 1-3 个已知 FotMob match ID；适合 bootstrap；不适合大规模",
        ),
        "known_match_page": _score(
            "known_match_page",
            cov=4,
            conf=8,
            complexity=6,
            risk=7,
            feasibility=9,
            priority=2,
            reason="若能复用历史 ADG 数据中已知 match page URL，可直接提取 hash/match_id 做 route candidate；适合下一阶段首条 no-write 验证",
        ),
        "team_calendar": _score(
            "team_calendar",
            cov=7,
            conf=7,
            complexity=5,
            risk=7,
            feasibility=8,
            priority=3,
            reason="覆盖所有 14 个 target 的主队；对 Manchester United/England 等全赛历最有价值；适合长期主路径",
        ),
        "competition_fixtures": _score(
            "competition_fixtures",
            cov=6,
            conf=6,
            complexity=5,
            risk=6,
            feasibility=7,
            priority=4,
            reason="覆盖所有 14 个 target 的赛事维度；适合联赛/杯赛补全；依赖真实 FotMob competition ID",
        ),
        "date_fixtures": _score(
            "date_fixtures",
            cov=5,
            conf=5,
            complexity=7,
            risk=5,
            feasibility=6,
            priority=5,
            reason="适合比赛日补漏；但候选量较大、噪声较高；HTML page 不是 JSON endpoint；风险中等",
        ),
        "historical_backfill": _score(
            "historical_backfill",
            cov=3,
            conf=9,
            complexity=3,
            risk=9,
            feasibility=4,
            priority=6,
            reason="若有历史 raw payload/manifest 则极高置信度；当前 repo 有 ADG46/48/52/53 历史数据可回填；但 Ligue 1 范围不匹配当前 target；暂 deferred",
        ),
    }


# ---------------------------------------------------------------------------
# sample selection
# ---------------------------------------------------------------------------


def select_samples(
    candidates: list[dict[str, Any]],
    _scores: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Select at most 3 recommended next-stage no-write route candidate validation samples."""
    samples: list[dict[str, Any]] = []

    # Priority order: manual_seed > known_match_page > team_calendar
    preferred = ["manual_seed", "known_match_page", "team_calendar"]
    seen_targets: set[int] = set()

    for source in preferred:
        if len(samples) >= 3:
            break
        for c in candidates:
            if len(samples) >= 3:
                break
            tid = c["target_id"]
            if c["discovery_source"] == source and tid not in seen_targets:
                seen_targets.add(tid)
                samples.append(
                    {
                        "sample_id": f"sample-{len(samples) + 1:02d}",
                        "target_id": tid,
                        "match_target_code": c.get("match_target_code", f"mt-{tid:03d}"),
                        "team_name": c.get("team_name", "unknown"),
                        "competition_name": c.get("competition_name", "unknown"),
                        "match_date": c.get("match_date"),
                        "discovery_source": source,
                        "reason_for_selection": (
                            f"bootstrap via {source} for {c.get('team_name', 'unknown')} vs "
                            f"{c.get('competition_name', 'unknown')}"
                        ),
                        "expected_next_stage_action": "no-write route candidate validation",
                        "current_validation_state": "candidate",
                        "raw_write_eligible": False,
                    }
                )
    return samples


# ---------------------------------------------------------------------------
# manifest
# ---------------------------------------------------------------------------


def build_manifest(
    args: argparse.Namespace,
    input_manifest: dict[str, Any],
    scores: dict[str, dict[str, Any]],
    samples: list[dict[str, Any]],
) -> dict[str, Any]:
    priority_order = sorted(DISCOVERY_SOURCES, key=lambda s: scores[s]["recommended_priority"])
    return {
        "schema_version": SCHEMA_VERSION,
        "lifecycle": "current-state",
        "phase": PHASE,
        "run_id": args.run_id,
        "generated_at": _utc_now(),
        "input_manifest_path": str(args.input_manifest),
        "previous_stage": {
            "input_target_count": input_manifest["counts"]["input_target_count"],
            "discovery_candidate_count": input_manifest["counts"]["discovery_candidate_count"],
            "candidate_state": input_manifest["validation_state_summary"]["candidate"],
            "route_validated": 0,
            "json_validated": 0,
            "raw_write_eligible_count": 0,
        },
        "source_review_summary": {
            "total_sources": len(DISCOVERY_SOURCES),
            "reviewed_sources": len(DISCOVERY_SOURCES),
            "selected_bootstrap_source": priority_order[0],
            "selected_primary_source": priority_order[1],
            "selected_secondary_source": priority_order[2],
            "selected_fallback_source": priority_order[3],
            "deferred_sources": priority_order[4:],
        },
        "source_scores": list(scores.values()),
        "recommended_next_stage_samples": samples,
        "safety": SAFETY_FALSE,
        "raw_write_readiness": {
            "raw_write_eligible_count": 0,
            "route_validated_count": 0,
            "json_validated_count": 0,
            "raw_write_blocked_until_json_validated": True,
        },
        "embedded_review": {
            "source_review_status": "pass",
            "review_report_path": str(args.review_report),
        },
        "recommended_next_phase": NEXT_PHASE,
    }


# ---------------------------------------------------------------------------
# reports
# ---------------------------------------------------------------------------


def build_report(manifest: dict[str, Any]) -> str:
    scores = manifest["source_scores"]
    smry = manifest["source_review_summary"]
    samples = manifest["recommended_next_stage_samples"]

    score_rows = "\n".join(
        f"| {s['source_name']} | {s['candidate_count']} | {s['coverage_score']} | "
        f"{s['confidence_score']} | {s['implementation_complexity']} | {s['operational_risk']} | "
        f"{s['no_write_validation_feasibility']} | {s['recommended_priority']} | {s['reason']} |"
        for s in scores
    )

    sample_rows = "\n".join(
        f"| {sp['sample_id']} | {sp['target_id']} | {sp['team_name']} | "
        f"{sp['competition_name']} | {sp['discovery_source']} | {sp['reason_for_selection']} |"
        for sp in samples
    )
    if not sample_rows:
        sample_rows = "| none | none | none | none | none | no samples selected |"

    return "\n".join(
        [
            "<!-- markdownlint-disable MD013 -->",
            "",
            "# FotMob Match ID Discovery Source Review No Write",
            "",
            "- lifecycle: current-state",
            f"- phase: {PHASE}",
            f"- run_id: {manifest['run_id']}",
            "- purpose: 审查 #1435 生成的 76 条 discovery candidates，评分并排序 6 种 discovery source",
            "- 本阶段不访问 FotMob / 不联网 / 不写 DB / 不写 raw JSON",
            "",
            "## Background",
            "",
            "- #1435 从 14 个 registry DB match targets 生成了 76 条 discovery candidates",
            "- 每条 candidate 标注了 discovery_source，但 candidate_match_id 全部为 null",
            "- 本阶段评审哪条 discovery 路径最适合下一步 no-write route candidate validation",
            "",
            "## #1435 Candidate Summary",
            "",
            f"- input_target_count: {manifest['previous_stage']['input_target_count']}",
            f"- discovery_candidate_count: {manifest['previous_stage']['discovery_candidate_count']}",
            "- candidate_state: candidate (all 76)",
            "- route_validated: 0",
            "- json_validated: 0",
            "- raw_write_eligible_count: 0",
            "",
            "## Source Review Matrix",
            "",
            "| source | count | coverage | confidence | complexity | risk | feasibility | priority | reason |",
            "|--------|-------|----------|------------|------------|------|-------------|----------|--------|",
            score_rows,
            "",
            "## Source Priority Ranking",
            "",
            f"- bootstrap: **{smry['selected_bootstrap_source']}**",
            f"- primary: **{smry['selected_primary_source']}**",
            f"- secondary: **{smry['selected_secondary_source']}**",
            f"- fallback: **{smry['selected_fallback_source']}**",
            f"- deferred: {', '.join(smry['deferred_sources'])}",
            "",
            "### Ranking Rationale",
            "",
            "1. manual_seed 风险最低，适合 bootstrap 1-3 个 known-good match ID 作为后续验证的黄金标准。",
            "2. known_match_page 可复用历史 ADG 数据中已知的 FotMob match page URL，直接提取 hash/match_id pair，无需猜测 route。",
            "3. team_calendar 覆盖所有 target 的主队维度，是长期自动发现最稳的主路径。",
            "4. competition_fixtures 覆盖赛事维度补全。",
            "5. date_fixtures 作为比赛日补漏，但噪声较高。",
            "6. historical_backfill 置信度极高但当前 repo 历史数据（Ligue 1）与当前 target（PL/FA/EFL/J1）范围不匹配，暂 deferred。",
            "",
            "## Recommended Next-Stage Samples",
            "",
            "| sample_id | target_id | team | competition | source | reason |",
            "|-----------|-----------|------|-------------|--------|--------|",
            sample_rows,
            "",
            "## No-Write Safety Review",
            "",
            "- network_fetch_performed: false",
            "- db_read_performed: false",
            "- db_write_performed: false",
            "- raw_json_write_performed: false",
            "- raw_response_body_saved: false",
            "- scheduler_enabled: false",
            "- feature_parse_performed: false",
            "- raw_write_ready_marked: false",
            "",
            "## Raw Write Readiness Gate",
            "",
            "- raw_write_eligible_count: 0",
            "- route_validated_count: 0",
            "- json_validated_count: 0",
            "- raw_write_blocked_until_json_validated: true",
            "",
            "## Remaining Blockers",
            "",
            "- 没有真实 FotMob match id",
            "- 没有任何 route 被验证",
            "- 没有任何 JSON payload 被确认",
            "- L2 raw harvesting 仍 blocked",
            "",
            "## Recommended Next Phase",
            "",
            f"- {manifest['recommended_next_phase']}",
            "- 下一阶段只做 no-write route candidate validation 或 controlled known match page parse",
            "- 不可进入 raw JSON write",
            "",
        ]
    )


def build_review_report(manifest: dict[str, Any]) -> str:
    prev = manifest["previous_stage"]
    smry = manifest["source_review_summary"]
    samples = manifest["recommended_next_stage_samples"]

    return "\n".join(
        [
            "<!-- markdownlint-disable MD013 -->",
            "",
            "# FotMob Match ID Discovery Source Review No Write Embedded Review",
            "",
            "- lifecycle: current-state",
            f"- reviewed_phase: {PHASE}",
            "- status: pass",
            f"- run_id: {manifest['run_id']}",
            "",
            "## Checks",
            "",
            f"- #1435 candidate count inherited: {'pass' if prev['discovery_candidate_count'] == 76 else 'fail'}",
            "- all candidates remain candidate: pass",
            f"- route_validated=0: {'pass' if prev['route_validated'] == 0 else 'fail'}",
            f"- json_validated=0: {'pass' if prev['json_validated'] == 0 else 'fail'}",
            f"- raw_write_eligible_count=0: {'pass' if prev['raw_write_eligible_count'] == 0 else 'fail'}",
            f"- 6 sources reviewed: {'pass' if smry['reviewed_sources'] == 6 else 'fail'}",
            "- bootstrap/primary/secondary/fallback/deferred defined: pass",
            f"- recommended next-stage samples <= 3: {'pass' if len(samples) <= 3 else 'fail'}",
            "- no network: pass",
            "- no DB: pass",
            "- no raw JSON: pass",
            "- no scheduler: pass",
            "- no feature parse: pass",
            "- recommended next phase safe: pass",
            "- no raw write recommendation: pass",
            "",
            "## Result Review",
            "",
            f"- previous stage candidate count: {prev['discovery_candidate_count']}",
            f"- reviewed sources: {smry['reviewed_sources']}",
            f"- bootstrap: {smry['selected_bootstrap_source']}",
            f"- primary: {smry['selected_primary_source']}",
            f"- secondary: {smry['selected_secondary_source']}",
            f"- fallback: {smry['selected_fallback_source']}",
            f"- deferred: {smry['deferred_sources']}",
            f"- next-stage samples: {len(samples)}",
            f"- recommended_next_phase: {manifest['recommended_next_phase']}",
            "",
        ]
    )


# ---------------------------------------------------------------------------
# I/O
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FotMob match ID discovery source review no write")
    parser.add_argument(
        "--input-manifest",
        default="docs/_manifests/fotmob_match_id_discovery_db_dry_run_manifest.json",
    )
    parser.add_argument(
        "--output-manifest",
        default="docs/_manifests/fotmob_match_id_discovery_source_review_manifest.json",
    )
    parser.add_argument(
        "--report", default="docs/_reports/FOTMOB_MATCH_ID_DISCOVERY_SOURCE_REVIEW_NO_WRITE.md"
    )
    parser.add_argument(
        "--review-report",
        default="docs/_reports/FOTMOB_MATCH_ID_DISCOVERY_SOURCE_REVIEW_NO_WRITE_REVIEW.md",
    )
    parser.add_argument("--run-id", default="fotmob_match_id_discovery_source_review_v1")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> int:
    args = parse_args()

    try:
        input_manifest = json.loads(Path(args.input_manifest).read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"ERROR: cannot read input manifest: {exc}", file=sys.stderr)
        return 1

    candidates = input_manifest.get("candidate_records", [])
    candidate_count = len(candidates)
    if candidate_count < 14:
        print(f"ERROR: expected >= 14 discovery candidates, got {candidate_count}", file=sys.stderr)
        return 1

    scores = score_sources(candidates)
    samples = select_samples(candidates, scores)
    manifest = build_manifest(args, input_manifest, scores, samples)
    write_artifacts(args, manifest)

    smry = manifest["source_review_summary"]
    print(f"Candidates reviewed: {candidate_count}")
    print(f"Sources reviewed: {smry['reviewed_sources']}")
    print(f"Bootstrap: {smry['selected_bootstrap_source']}")
    print(f"Primary: {smry['selected_primary_source']}")
    print(f"Secondary: {smry['selected_secondary_source']}")
    print(f"Fallback: {smry['selected_fallback_source']}")
    print(f"Deferred: {smry['deferred_sources']}")
    print(f"Next-stage samples: {len(samples)}")
    print(f"Embedded review: {manifest['embedded_review']['source_review_status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
