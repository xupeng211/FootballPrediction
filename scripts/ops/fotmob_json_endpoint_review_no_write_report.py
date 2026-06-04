#!/usr/bin/env python3
"""Report generators for FotMob JSON endpoint review no-write.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-JSON-PROBE-ENDPOINT-REVIEW-NO-WRITE
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-JSON-PROBE-ENDPOINT-REVIEW-NO-WRITE"
NEXT_PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-ENDPOINT-CANDIDATE-PROBE-NO-WRITE"


def write_report(
    report_path: Path,
    run_id: str,
    manifest: dict[str, Any],
    rejected: list[dict[str, Any]],
    reviewed: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    next_probe_plan: dict[str, Any],
) -> None:
    """Write the human-readable endpoint review report."""
    lines: list[str] = []
    lines.append("<!-- markdownlint-disable MD013 MD034 -->")
    lines.append("")
    lines.append("# FotMob JSON Endpoint Review No Write")
    lines.append("")
    lines.append("- lifecycle: current-state")
    lines.append(f"- phase: {PHASE}")
    lines.append(f"- run_id: {run_id}")
    lines.append("- mode: offline_endpoint_review")
    lines.append("")
    lines.append("## 当前阶段背景")
    lines.append("")
    lines.append("- #1439 用 3 个真实 match_id 测试了 3 个 endpoint templates，9 个请求全部 404。")
    lines.append("- 当前使用的 `/api/matchDetails?matchId={id}` 模式无效或已过时。")
    lines.append(
        "- 本阶段离线复盘仓库历史 FotMob endpoint/route 审计材料，找出更靠谱的 endpoint 候选。"
    )
    lines.append(
        "- 已经有真实 match_id 和 route_code。当前任务不是继续抓数据，而是找正确的 endpoint pattern。"
    )
    lines.append("")
    lines.append("## #1439 失败结果继承")
    lines.append("")
    for k, v in manifest["inherited_probe_status"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## 404 Endpoint Rejection Summary")
    lines.append("")
    lines.append("| # | Endpoint Template | Prior Attempts | Result | Decision |")
    lines.append("|---|---:|---|---|")
    for i, ep in enumerate(rejected):
        lines.append(
            f"| {i + 1} | `{ep['endpoint_template']}` | {ep['prior_attempts']} | "
            f"{ep['prior_result']} | {ep['decision']} |"
        )
    lines.append("")
    lines.append("## Historical File Review Summary")
    lines.append("")
    lines.append("| File | Exists | Endpoint Patterns Found | Notes |")
    lines.append("|---|---:|---|")
    for hf in reviewed:
        status = "yes" if hf["exists"] else "missing"
        lines.append(
            f"| {hf['path']} | {status} | {hf['extracted_candidate_count']} | {hf['notes'][:80]} |"
        )
    lines.append("")
    lines.append("## Endpoint Candidate Matrix")
    lines.append("")
    lines.append(
        "| ID | Category | Endpoint Template | Source | Confidence | Risk | Priority | Next Probe |"
    )
    lines.append("|---|---|---|---:|---:|---:|---|")
    for c in candidates:
        probe = "yes" if c["next_phase_probe_allowed"] else "no"
        lines.append(
            f"| {c['endpoint_candidate_id']} | {c['category']} | `{c['endpoint_template'][:60]}` | "
            f"{c['source']} | {c['confidence_score']} | {c['risk_score']} | "
            f"{c['recommended_probe_priority']} | {probe} |"
        )
    lines.append("")
    lines.append("## Next Probe Plan Summary")
    lines.append("")
    for k, v in next_probe_plan.items():
        if isinstance(v, list):
            lines.append(f"- **{k}**:")
            for item in v:
                lines.append(f"  - {item}")
        else:
            lines.append(f"- **{k}**: {v}")
    lines.append("")
    lines.append("## Raw Write Readiness Gate")
    lines.append("")
    for k, v in manifest["raw_write_readiness"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("## No-Write Safety Review")
    lines.append("")
    for k, v in manifest["safety"].items():
        status = "pass" if v is False else "WARN"
        lines.append(f"- {k}: {v} ({status})")
    lines.append("")
    lines.append("## Remaining Blockers")
    lines.append("")
    lines.append("- 已经有真实 match_id")
    lines.append("- 但旧 endpoint /api/matchDetails (without /data/) 全部 404")
    lines.append("- 本阶段没有联网、没有 raw body、没有 raw JSON、没有 DB write")
    lines.append("- 下一阶段仍然是 controlled endpoint candidate probe no-write，不是 raw write")
    lines.append("")
    lines.append("## Recommended Next Phase")
    lines.append("")
    lines.append(f"- **{NEXT_PHASE}**")
    lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")


def write_next_probe_plan_report(
    path: Path,
    candidates: list[dict[str, Any]],
    next_probe_plan: dict[str, Any],
) -> None:
    """Write the detailed next probe plan."""
    lines: list[str] = []
    lines.append("<!-- markdownlint-disable MD013 MD034 -->")
    lines.append("")
    lines.append("# FotMob JSON Endpoint — Next Probe Plan")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append("- 本计划基于 #1439 失败结果和仓库历史 endpoint 审计材料生成。")
    lines.append("- #1439 的 /api/matchDetails (without /data/) 全部 404，已 reject。")
    lines.append("- 本计划推荐新的 endpoint candidates 供下一阶段 controlled probe。")
    lines.append("- 下一阶段仍然是 no-write：只保存 metadata，不保存 body。")
    lines.append("")

    probe_allowed = [c for c in candidates if c.get("next_phase_probe_allowed")]
    probe_allowed.sort(key=lambda c: c.get("recommended_probe_priority", 99))
    selected = probe_allowed[:3]

    lines.append("## Recommended Endpoint Templates for Next Probe")
    lines.append("")
    lines.append("| # | Endpoint Template | Source | Why Better Than #1439 |")
    lines.append("|---|---|---|")
    for i, c in enumerate(selected):
        why = ""
        if "/api/data/" in c["endpoint_template"]:
            why = "Has /data/ prefix — canonical path from production code"
        elif "/match/" in c["endpoint_template"] and "/matches/" not in c["endpoint_template"]:
            why = "HTML hydration route — known HTTP 200 from ADG60"
        elif "/matches/" in c["endpoint_template"]:
            why = "SSR page route — ADG60 validated, user seeds use this pattern"
        else:
            why = c["evidence_summary"][:60]
        lines.append(f"| {i + 1} | `{c['endpoint_template'][:70]}` | {c['source']} | {why} |")
    lines.append("")

    lines.append("## Probe Parameters")
    lines.append("")
    skip_keys = {
        "selected_endpoint_templates",
        "stop_conditions",
        "safety_boundaries",
        "next_phase_notes",
    }
    for k, v in next_probe_plan.items():
        if k in skip_keys:
            continue
        lines.append(f"- **{k}**: {v}")
    lines.append("")

    lines.append("## Selected Match IDs")
    lines.append("")
    mids = next_probe_plan["selected_match_ids"]
    rcs = next_probe_plan["selected_route_codes"]
    for i in range(len(mids)):
        rc = rcs[i] if i < len(rcs) else "N/A"
        lines.append(f"- match_id={mids[i]}, route_code={rc}")
    lines.append("")

    lines.append("## Stop Conditions")
    lines.append("")
    for cond in next_probe_plan.get("stop_conditions", []):
        lines.append(f"- {cond}")
    lines.append("")

    lines.append("## Safety Boundaries")
    lines.append("")
    for sb in next_probe_plan.get("safety_boundaries", []):
        lines.append(f"- {sb}")
    lines.append("")

    lines.append("## Why Next Phase Is Still No-Write")
    lines.append("")
    lines.append("- 这仍然是 endpoint discovery，不是 data harvesting。")
    lines.append("- 即使 endpoint 返回 200 + JSON，也只能记录 metadata。")
    lines.append("- 不允许 raw JSON body 保存、raw JSON write、DB write。")
    lines.append("- L2 raw harvesting 仍然 blocked。")
    lines.append("")

    lines.append("## Next Phase Recommendation")
    lines.append("")
    lines.append(f"- **{NEXT_PHASE}**")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def write_review_report(
    path: Path,
    run_id: str,
    manifest: dict[str, Any],
    reviewed: list[dict[str, Any]],
) -> bool:
    """Write the embedded review report. Returns True if all pass."""
    rejected_count = len(manifest["rejected_endpoints"])
    cand_count = len(manifest["endpoint_candidates"])
    next_count = manifest["next_probe_plan"]["selected_candidate_count"]
    files_reviewed = sum(1 for hf in reviewed if hf["exists"])

    checks: list[tuple[str, bool, str]] = [
        (
            "#1439 probe status inherited",
            manifest["inherited_probe_status"]["network_requests_attempted"] == 9,
            "",
        ),
        ("rejected endpoints captured", rejected_count >= 3, f"count={rejected_count}"),
        ("historical files reviewed", files_reviewed >= 3, f"found={files_reviewed}"),
        ("endpoint candidate matrix generated", cand_count >= 1, f"count={cand_count}"),
        ("next probe plan generated", next_count >= 1, f"count={next_count}"),
        ("no network", manifest["safety"]["network_fetch_performed"] is False, ""),
        ("no DB read", manifest["safety"]["db_read_performed"] is False, ""),
        ("no DB write", manifest["safety"]["db_write_performed"] is False, ""),
        ("no raw JSON", manifest["safety"]["raw_json_write_performed"] is False, ""),
        ("no response body", manifest["safety"]["raw_response_body_saved"] is False, ""),
        ("no scheduler", manifest["safety"]["scheduler_enabled"] is False, ""),
        ("no feature parse", manifest["safety"]["feature_parse_performed"] is False, ""),
        ("no browser automation", manifest["safety"]["browser_automation_performed"] is False, ""),
        ("no captcha bypass", manifest["safety"]["captcha_bypass_performed"] is False, ""),
        ("no proxy rotation", manifest["safety"]["proxy_rotation_performed"] is False, ""),
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
            manifest["recommended_next_phase"] == NEXT_PHASE,
            manifest["recommended_next_phase"],
        ),
        (
            "no direct raw write recommendation",
            "RAW-JSON-DEV-WRITE" not in manifest["recommended_next_phase"],
            "",
        ),
    ]

    lines: list[str] = []
    lines.append("<!-- markdownlint-disable MD013 -->")
    lines.append("")
    lines.append("# FotMob JSON Endpoint Review No Write — Embedded Review")
    lines.append("")
    lines.append("- lifecycle: current-state")
    lines.append(f"- phase: {PHASE} (review)")
    lines.append(f"- run_id: {run_id}")
    lines.append("")

    all_pass = True
    for name, passed, detail in checks:
        status = "pass" if passed else "FAIL"
        if not passed:
            all_pass = False
        detail_str = f" ({detail})" if detail else ""
        lines.append(f"- [{status}] {name}{detail_str}")

    lines.append("")
    lines.append(f"## Overall: {'pass' if all_pass else 'BLOCKED'}")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return all_pass
