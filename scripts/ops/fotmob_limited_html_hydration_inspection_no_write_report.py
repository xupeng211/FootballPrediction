#!/usr/bin/env python3
"""Report generators for limited HTML hydration inspection no-write.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-LIMITED-HTML-HYDRATION-INSPECTION-NO-WRITE
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-LIMITED-HTML-HYDRATION-INSPECTION-NO-WRITE"


def write_report(path, run_id, mode, manifest, samples, routes, summary):
    l = ["<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 -->\n"]
    l.append("# FotMob Limited HTML Hydration Inspection No Write\n\n")
    l.append(
        f"- lifecycle: current-state\n- phase: {PHASE}\n- run_id: {run_id}\n- mode: {mode}\n\n"
    )
    l.append("## 当前阶段背景\n\n")
    l.append(
        "- #1443 extraction plan 设计完成。本阶段执行 limited bounded body inspection。\n- 只读取最多 262144 bytes，在内存中扫描 structure markers。\n- 不保存 HTML body，不保存 raw JSON，不写 DB。\n\n"
    )
    l.append("## #1443 Extraction Plan Inheritance\n\n")
    for k, v in manifest["inherited_extraction_plan"].items():
        l.append(f"- {k}: {v}\n")
    l.append("\n## Selected Inspection Samples\n\n")
    for i, s in enumerate(samples):
        l.append(
            f"{i + 1}. match_id={s['match_id']}, route_code={s['route_code']}, pair={s['team_pair']}\n"
        )
    l.append("\n## Route Templates Inspected\n\n")
    for i, r in enumerate(routes[:2]):
        l.append(f"{i + 1}. `{r['template']}`\n")
    l.append("\n## Network / Bounded Body Summary\n\n")
    for k, v in summary.items():
        l.append(f"- {k}: {v}\n")
    results = manifest.get("inspection_results", [])
    if results:
        l.append("\n## Structural Signals\n\n")
        l.append(
            "| Inspection ID | Match ID | Route Code | Bytes Read | NEXT_DATA | pageProps | matchId Seen | Top-Level Keys |\n"
        )
        l.append("|---|---:|---|---|---|---|---|\n")
        for r in results:
            nd = r.get("marker_presence", {}).get("__NEXT_DATA__", False)
            pp = r.get("marker_presence", {}).get("pageProps", False)
            keys = ", ".join(r.get("top_level_key_names", [])[:5]) or "-"
            l.append(
                f"| {r['inspection_id']} | {r['match_id']} | {r['route_code']} | {r.get('bytes_read', 0)} | {nd} | {pp} | {r.get('match_id_seen', False)} | {keys} |\n"
            )
        l.append("\n")
    l.append("## Hydration Structure Decision\n\n")
    hd = manifest["hydration_decision"]
    l.append(
        f"- viable routes: {hd['viable_routes'] or 'none'}\n- recommended extraction route: {hd['recommended_extraction_route'] or 'none'}\n\n"
    )
    l.append("## Raw Write Readiness Gate\n\n")
    for k, v in manifest["raw_write_readiness"].items():
        l.append(f"- {k}: {v}\n")
    l.append("\n## No-Write Safety Review\n\n")
    for k, v in manifest["safety"].items():
        st = (
            "pass"
            if v is False or k in ("network_fetch_performed", "bounded_body_read_performed")
            else "WARN"
        )
        l.append(f"- {k}: {v} ({st})\n")
    l.append("\n## Remaining Blockers\n\n")
    l.append(
        "- 本阶段只做 bounded body read，不保存 HTML，不保存 raw JSON，不写 DB\n- 如果 marker 找到，下一阶段也只是 hydration structure validation no-write\n- L2 raw harvesting 仍然 blocked\n\n"
    )
    l.append(f"## Recommended Next Phase\n\n- **{manifest['recommended_next_phase']}**\n\n")
    path.write_text("".join(l), encoding="utf-8")


def write_decision_report(path, results, routes, summary):
    l = ["<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 -->\n\n"]
    l.append("# FotMob Hydration Structure — Decision Report\n\n")
    rs = {}
    for r in results:
        t = r["route_template"]
        if t not in rs:
            rs[t] = {"att": 0, "marker": 0, "struct": 0, "missing": 0, "blocked": 0, "invalid": 0}
        rs[t]["att"] += 1
        if r["validation_state"] in ("hydration_marker_observed", "hydration_structure_observed"):
            rs[t]["marker"] += 1
        if r["validation_state"] == "hydration_structure_observed":
            rs[t]["struct"] += 1
        if r["validation_state"] == "hydration_marker_missing":
            rs[t]["missing"] += 1
        if r["validation_state"] == "hydration_route_blocked":
            rs[t]["blocked"] += 1
        if r["validation_state"] == "hydration_route_invalid":
            rs[t]["invalid"] += 1
    l.append(
        "| Route Template | Attempted | Marker | Structure | Missing | Blocked | Invalid | Decision |\n"
    )
    l.append("|---|---:|---:|---:|---:|---:|---:|---|\n")
    for tmpl, st in rs.items():
        if st["struct"] > 0:
            d = "use — viable for extraction"
        elif st["marker"] > 0:
            d = "use — marker found, can proceed"
        elif st["blocked"] > 0:
            d = "reject — blocked"
        elif st["invalid"] > 0:
            d = "reject — invalid"
        else:
            d = "review"
        l.append(
            f"| `{tmpl[:60]}` | {st['att']} | {st['marker']} | {st['struct']} | {st['missing']} | {st['blocked']} | {st['invalid']} | {d} |\n"
        )
    l.append("\n")
    has_net = any(r.get("network_performed") for r in results)
    has_marker = any(s["marker"] > 0 for s in rs.values())
    if not has_net:
        l.append("## Note\n\n- 本报告为 dry-run，无实际网络探测。\n")
    elif has_marker:
        l.append(
            "## Recommendation\n\n- 发现 hydration marker。\n- 下一阶段建议：hydration structure validation no-write。\n- 仍然不直接 raw write。\n"
        )
    else:
        l.append("## Recommendation\n\n- 未发现 marker。\n- 建议进入 marker review followup。\n")
    l.append("\n")
    path.write_text("".join(l), encoding="utf-8")


def write_review_report(path, run_id, manifest, summary) -> bool:
    sel = manifest["inspection_selection"]
    rec = manifest["recommended_next_phase"]
    checks = [
        (
            "#1443 extraction plan inherited",
            manifest["inherited_extraction_plan"]["html_route_observed_count"] == 6,
            "",
        ),
        (
            "max samples <= 2",
            sel["selected_sample_count"] <= 2,
            f"count={sel['selected_sample_count']}",
        ),
        (
            "max route templates <= 2",
            len(sel["selected_route_templates"]) <= 2,
            f"count={len(sel['selected_route_templates'])}",
        ),
        ("max network requests <= 4", summary.get("max_network_requests", 0) <= 4, ""),
        ("max body bytes <= 524288", sel["max_body_bytes"] <= 524288, ""),
        (
            "no network when dry-run",
            (
                not summary.get("allow_network_probe")
                and summary.get("network_requests_attempted", 0) == 0
            )
            or summary.get("allow_network_probe"),
            "",
        ),
        (
            "full_body_read_performed false",
            manifest["safety"]["full_body_read_performed"] is False,
            "",
        ),
        ("no full HTML saved", manifest["safety"]["full_html_saved"] is False, ""),
        ("no HTML body saved", manifest["safety"]["html_body_saved"] is False, ""),
        ("no raw JSON saved", manifest["safety"]["raw_json_write_performed"] is False, ""),
        ("no DB write", manifest["safety"]["db_write_performed"] is False, ""),
        ("no scheduler", manifest["safety"]["scheduler_enabled"] is False, ""),
        ("no browser", manifest["safety"]["browser_automation_performed"] is False, ""),
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
        ("next phase safe", rec != "DIRECT-RAW-WRITE" and "RAW-JSON-DEV-WRITE" not in rec, rec),
    ]
    lines = ["<!-- markdownlint-disable MD013 MD012 -->\n\n"]
    lines.append("# FotMob Limited HTML Hydration Inspection No Write — Embedded Review\n\n")
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
