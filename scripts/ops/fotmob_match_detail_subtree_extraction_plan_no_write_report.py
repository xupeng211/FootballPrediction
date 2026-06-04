#!/usr/bin/env python3
"""Report generators for match detail subtree extraction plan no-write."""

from pathlib import Path

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-MATCH-DETAIL-SUBTREE-EXTRACTION-PLAN-NO-WRITE"
MD = "<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->\n"


def write_report(path, run_id, manifest):
    ih = manifest["inherited_hydration_validation"]
    plan = manifest["subtree_extraction_plan"]
    l = [MD, "# FotMob Match Detail Subtree Extraction Plan No Write\n\n"]
    l.append(
        f"- lifecycle: current-state\n- phase: {PHASE}\n- run_id: {run_id}\n- mode: offline_subtree_extraction_plan\n\n"
    )
    l.append(
        "## 当前阶段背景\n\n- #1445 确认 /matches/{rc}/{id} 中存在 __NEXT_DATA__ + pageProps。\n- match_detail_candidate_observed=2 但 target_match_id_seen=0。\n- pageProps 顶层 keys 是 fallback/fetchingLeagueData/ssr/translations（Next.js 框架层）。\n- 真正 match detail 数据很可能藏在 props.pageProps.fallback 或更深的 nested subtree。\n- 本阶段只设计 subtree scan 方案，不执行 live extraction。\n\n"
    )
    l.append("## #1445 Hydration Structure Validation Inheritance\n\n")
    for k, v in ih.items():
        l.append(f"- {k}: {v}\n")
    l.append(
        "\n## Why props.pageProps Is Only the Candidate Root\n\n- target_match_id_seen_count=0 — match id 不在 pageProps 直接 key 中。\n- pageProps 顶层是 Next.js 框架配置（fallback, fetchingLeagueData, ssr, translations）。\n- 历史 production code (FotMobRawDetailFetcher.js) 从 __NEXT_DATA__.props.pageProps 提取数据。\n- match detail 数据应在 pageProps. 的 nested subtree 中（fallback cache entry）。\n\n"
    )
    l.append("## Subtree Extraction Plan\n\n")
    l.append(
        f"- root path: `{plan['root_path']}`\n- key search terms: {', '.join(plan['key_search_terms'][:8])}\n- persistence policy: {plan['persistence_policy']}\n\n"
    )
    l.append("## Priority Path Matrix\n\n")
    l.append("| Priority | Path | Purpose |\n|---|---|---|\n")
    for pp in plan["priority_paths"]:
        l.append(f"| {pp['priority']} | `{pp['path']}` | {pp['purpose']} |\n")
    l.append("\n## Scoring Rules\n\n")
    l.append("| Signal | Score |\n|---|---:|\n")
    for sr in plan["scoring_rules"]:
        l.append(f"| {sr['signal']} | {sr['score']} |\n")
    l.append("\n## Candidate Classification Rules\n\n")
    l.append("| Min Score | State |\n|---:|---|\n")
    for cc in plan["candidate_classification_rules"]:
        l.append(f"| {cc['min_score']} | {cc['state']} |\n")
    l.append("\n## Next Controlled Subtree Extraction Plan\n\n")
    np = manifest["controlled_subtree_extraction_next_plan"]
    for k, v in np.items():
        if isinstance(v, list):
            l.append(f"- **{k}**: {', '.join(str(x) for x in v[:5])}\n")
        else:
            l.append(f"- **{k}**: {v}\n")
    l.append("\n## Raw Write Readiness Gate\n\n")
    for k, v in manifest["raw_write_readiness"].items():
        l.append(f"- {k}: {v}\n")
    l.append("\n## No-Write Safety Review\n\n")
    for k, v in manifest["safety"].items():
        st = "pass" if v is False else "WARN"
        l.append(f"- {k}: {v} ({st})\n")
    l.append(
        "\n## Remaining Blockers\n\n- 本阶段没有联网、没有读取 body、没有保存 HTML、没有保存 NEXT_DATA、没有保存 raw JSON、没有写 DB\n- 下一阶段只是 controlled subtree extraction no-write，仍然不是 raw JSON 入库\n- L2 raw harvesting 仍然 blocked\n\n"
    )
    l.append(f"## Recommended Next Phase\n\n- **{manifest['recommended_next_phase']}**\n\n")
    path.write_text("".join(l), encoding="utf-8")


def write_next_plan_report(path, manifest):
    np = manifest["controlled_subtree_extraction_next_plan"]
    l = [MD, "# FotMob Controlled Match Detail Subtree Extraction — Next Plan\n\n"]
    l.append(
        "## Why Subtree Extraction Is Needed\n\n- #1445 proved NEXT_DATA parses but target match_id not found at pageProps level.\n- pageProps contains Next.js framework config (fallback, fetchingLeagueData, ssr, translations).\n- Real match detail data is likely nested under fallback cache entries.\n- This phase does in-memory subtree scan WITHOUT persisting values.\n\n"
    )
    l.append("## Route and Samples\n\n")
    l.append(
        f"- route: `{np['route_template']}`\n- match IDs: {', '.join(np['selected_match_ids'])}\n- route codes: {', '.join(np['selected_route_codes'])}\n\n"
    )
    l.append("## Constraints\n\n")
    for k in [
        "max_samples",
        "max_network_requests",
        "max_body_bytes",
        "max_subtree_scan_depth",
        "max_key_paths_recorded",
    ]:
        l.append(f"- {k}: {np.get(k, 'N/A')}\n")
    l.append("\n## Allowed Metadata\n\n")
    for a in np.get("allowed_metadata", []):
        l.append(f"- {a}\n")
    l.append("\n## Forbidden Persistence\n\n")
    for f in np.get("forbidden_persistence", []):
        l.append(f"- {f}\n")
    l.append("\n## Scoring Rules\n\n")
    for sr in manifest["subtree_extraction_plan"]["scoring_rules"][:8]:
        l.append(f"- {sr['signal']}: {sr['score']:+d}\n")
    l.append("\n## Success/Failure Criteria\n\n")
    l.append("**Success:**\n")
    for s in np.get("success_criteria", []):
        l.append(f"- {s}\n")
    l.append("**Failure:**\n")
    for f in np.get("failure_criteria", []):
        l.append(f"- {f}\n")
    l.append("\n## Stop Conditions\n\n")
    for s in np.get("stop_conditions", []):
        l.append(f"- {s}\n")
    l.append("\n## After Success\n\n")
    l.append(
        f"- Next: **{np.get('next_phase_after_success')}**\n- Still not raw JSON write\n- L2 raw harvesting remains blocked\n\n"
    )
    l.append("## After Failure\n\n- Fallback: hydration structure review followup no-write\n\n")
    l.append(
        "## Safety Reminder\n\n- 不保存 full HTML\n- 不保存 full NEXT_DATA\n- 不保存 raw JSON\n- 不写 DB\n- 不启用 scheduler\n- 不使用 browser automation\n- 不绕过反爬\n\n"
    )
    path.write_text("".join(l), encoding="utf-8")


def write_review_report(path, run_id, manifest) -> bool:
    ih = manifest["inherited_hydration_validation"]
    rec = manifest["recommended_next_phase"]
    checks = [
        (
            "#1445 hydration validation inherited",
            ih["match_detail_candidate_observed_count"] == 2,
            "",
        ),
        ("target_match_id_seen_count=0 acknowledged", ih["target_match_id_seen_count"] == 0, ""),
        (
            "subtree extraction plan generated",
            len(manifest.get("subtree_extraction_plan", {}).get("priority_paths", [])) >= 1,
            "",
        ),
        (
            "next controlled extraction plan generated",
            bool(manifest.get("controlled_subtree_extraction_next_plan", {}).get("max_samples")),
            "",
        ),
        ("no network", manifest["safety"]["network_fetch_performed"] is False, ""),
        ("no response body read", manifest["safety"]["response_body_read"] is False, ""),
        ("no HTML body saved", manifest["safety"]["html_body_saved"] is False, ""),
        ("no NEXT_DATA saved", manifest["safety"]["full_next_data_saved"] is False, ""),
        ("no raw JSON saved", manifest["safety"]["raw_json_write_performed"] is False, ""),
        ("no DB write", manifest["safety"]["db_write_performed"] is False, ""),
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
            "next phase safe",
            rec == manifest["recommended_next_phase"] and "RAW-JSON-DEV-WRITE" not in rec,
            rec,
        ),
    ]
    lines = ["<!-- markdownlint-disable MD013 MD012 -->\n\n"]
    lines.append("# FotMob Match Detail Subtree Extraction Plan No Write — Embedded Review\n\n")
    lines.append(f"- lifecycle: current-state\n- phase: {PHASE} (review)\n- run_id: {run_id}\n\n")
    all_ok = True
    for name, ok, detail in checks:
        st = "pass" if ok else "FAIL"
        if not ok:
            all_ok = False
        d = f" ({detail})" if detail else ""
        lines.append(f"- [{st}] {name}{d}\n")
    lines.append(f"\n## Overall: {'pass' if all_ok else 'BLOCKED'}\n\n")
    path.write_text("".join(lines), encoding="utf-8")
    return all_ok
