#!/usr/bin/env python3
"""Report generators for hydration structure validation no-write.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-STRUCTURE-VALIDATION-NO-WRITE
"""

from __future__ import annotations

from pathlib import Path

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HYDRATION-STRUCTURE-VALIDATION-NO-WRITE"
MD = "<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 MD001 -->\n"


def write_report(path, run_id, mode, manifest, samples, results, summary):
    l = [MD, "# FotMob Hydration Structure Validation No Write\n\n"]
    l.append(
        f"- lifecycle: current-state\n- phase: {PHASE}\n- run_id: {run_id}\n- mode: {mode}\n\n"
    )
    l.append(
        "## 当前阶段背景\n\n- #1444 确认 /matches/{rc}/{id} 中存在 __NEXT_DATA__ + pageProps。\n- 本阶段在内存中解析 __NEXT_DATA__ JSON 结构寻找 match detail subtree。\n- 只保存结构 metadata（key paths, key presence, score），不保存完整 JSON。\n\n"
    )
    l.append("## #1444 Inspection Inheritance\n\n")
    for k, v in manifest["inherited_inspection"].items():
        l.append(f"- {k}: {v}\n")
    l.append("\n## Selected Validation Samples\n\n")
    for s in samples:
        l.append(f"- match_id={s[0]}, route_code={s[1]}, pair={s[2]}\n")
    l.append(f"\n## Route Template\n\n`{manifest['validation_selection']['route_template']}`\n\n")
    l.append("## Bounded Body Validation Summary\n\n")
    for k, v in summary.items():
        l.append(f"- {k}: {v}\n")
    l.append("\n## Match Detail Candidate Decision\n\n")
    md = manifest["match_detail_candidate_decision"]
    l.append(
        f"- viable candidates: {md['viable_candidate_count']}\n- best score: {md['best_candidate_score']}\n- next action: {md['recommended_next_action']}\n\n"
    )
    if results:
        l.append(
            "| Validation ID | Match ID | ND Parse | pageProps | mid Seen | Candidate Score | Top pageProps Keys | State |\n"
        )
        l.append("|---|---|---|---:|---:|---|---|\n")
        for r in results:
            pp_keys = ", ".join(r.get("pageProps_key_names", [])[:6]) or "-"
            l.append(
                f"| {r['validation_id']} | {r['match_id']} | {r.get('next_data_json_parse_ok', False)} | {r.get('pageProps_present', False)} | {r.get('target_match_id_seen', False)} | {r.get('candidate_match_detail_score', 0)} | {pp_keys} | {r.get('validation_state', '-')} |\n"
            )
        l.append("\n")
    l.append("## Raw Write Readiness Gate\n\n")
    for k, v in manifest["raw_write_readiness"].items():
        l.append(f"- {k}: {v}\n")
    l.append(f"\n## Recommended Next Phase\n\n- **{manifest['recommended_next_phase']}**\n\n")
    path.write_text("".join(l), encoding="utf-8")


def write_decision_report(path, results, samples, summary):
    l = [MD, "# FotMob Match Detail Candidate — Decision Report\n\n"]
    for r in results:
        l.append(f"### {r['validation_id']}: {r['match_id']} ({r['team_pair']})\n\n")
        l.append(f"- __NEXT_DATA__ parse: {r.get('next_data_json_parse_ok', False)}\n")
        l.append(f"- pageProps present: {r.get('pageProps_present', False)}\n")
        l.append(f"- target match_id seen: {r.get('target_match_id_seen', False)}\n")
        l.append(f"- candidate score: {r.get('candidate_match_detail_score', 0)}\n")
        l.append(
            f"- pageProps keys: {', '.join(r.get('pageProps_key_names', [])[:12]) or 'none'}\n"
        )
        l.append(f"- state: {r.get('validation_state', '-')}\n")
        kp = r.get("candidate_match_detail_key_presence", {})
        if kp:
            l.append("- candidate key presence:\n")
            for k, v in kp.items():
                l.append(f"  - {k}: {v}\n")
        l.append("\n")
    cand = summary.get("match_detail_candidate_observed_count", 0)
    if not any(r.get("network_performed") for r in results):
        l.append("## Note\n\n- dry-run，无实际网络探测。\n")
    elif cand >= 1:
        l.append(
            "## Recommendation\n\n- 发现 match detail candidate。\n- 下一阶段建议：match detail subtree extraction plan no-write。\n- 仍然不直接 raw write。\n"
        )
    else:
        l.append(
            "## Recommendation\n\n- 未发现明确 match detail candidate。\n- 建议进入 partial structure / structure review followup。\n"
        )
    path.write_text("".join(l), encoding="utf-8")


def write_review_report(path, run_id, manifest, summary) -> bool:
    sel = manifest["validation_selection"]
    rec = manifest["recommended_next_phase"]
    checks = [
        (
            "#1444 inspection inherited",
            manifest["inherited_inspection"]["hydration_structure_observed_count"] == 2,
            "",
        ),
        ("route restricted to /matches/{rc}/{id}", "/matches/" in sel["route_template"], ""),
        ("max samples <= 2", sel["selected_sample_count"] <= 2, ""),
        ("max network requests <= 2", summary.get("max_network_requests", 0) <= 2, ""),
        ("max body bytes <= 524288", sel["max_body_bytes"] <= 524288, ""),
        (
            "full_body_read_performed false",
            manifest["safety"]["full_body_read_performed"] is False,
            "",
        ),
        ("full_html_saved false", manifest["safety"]["full_html_saved"] is False, ""),
        ("full_next_data_saved false", manifest["safety"]["full_next_data_saved"] is False, ""),
        (
            "raw_json_write_performed false",
            manifest["safety"]["raw_json_write_performed"] is False,
            "",
        ),
        ("db_write_performed false", manifest["safety"]["db_write_performed"] is False, ""),
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
        ("next phase safe", "RAW-JSON-DEV-WRITE" not in rec, rec),
    ]
    lines = ["<!-- markdownlint-disable MD013 MD012 -->\n\n"]
    lines.append("# FotMob Hydration Structure Validation No Write — Embedded Review\n\n")
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
