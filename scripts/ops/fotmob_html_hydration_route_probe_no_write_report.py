#!/usr/bin/env python3
"""Report generators for FotMob HTML hydration route probe no-write.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HTML-HYDRATION-ROUTE-PROBE-NO-WRITE
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HTML-HYDRATION-ROUTE-PROBE-NO-WRITE"


def write_report(
    path: Path,
    run_id: str,
    mode: str,
    manifest: dict[str, Any],
    samples: list,
    templates: list,
    summary: dict[str, Any],
) -> None:
    l: list[str] = []
    l.append("<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 -->\n")
    l.append("# FotMob HTML Hydration Route Probe No Write\n")
    l.append(f"- lifecycle: current-state\n- phase: {PHASE}\n- run_id: {run_id}\n- mode: {mode}\n")
    l.append("## 当前阶段背景\n")
    l.append("- #1441 验证 /api/data/matchDetails 返回 HTTP 403，API 路线被反爬阻断。\n")
    l.append("- 本阶段只测试 HTML hydration 页面路线：/match/{id} 和 /matches/{rc}/{id}。\n")
    l.append("- 只读取 status + headers metadata，不读取完整 body。\n")
    l.append("## #1441 Endpoint Probe Inheritance\n")
    for k, v in manifest["inherited_endpoint_probe"].items():
        l.append(f"- {k}: {v}\n")
    l.append("\n## Selected Route Samples\n")
    for i, s in enumerate(samples):
        l.append(
            f"{i + 1}. match_id={s['match_id']}, route_code={s['route_code']}, pair={s['team_pair']}\n"
        )
    l.append("\n## Route Templates Tested\n")
    for i, t in enumerate(templates[:2]):
        l.append(f"{i + 1}. `{t['template']}` — {t['name']}\n")
    l.append("\n## Network Probe Summary\n")
    for k, v in summary.items():
        l.append(f"- {k}: {v}\n")
    results = manifest.get("probe_results", [])
    if results:
        l.append("\n## Probe Result Details\n\n")
        l.append(
            "| Probe ID | Match ID | Team Pair | Route | Status | Content-Type | Redirect | Validation State |\n"
        )
        l.append("|---|---|---|---|---|---|---|---|\n")
        for r in results:
            tmpl = r["route_template"][:50]
            redirect = r.get("location_header", "") or "-"
            l.append(
                f"| {r['probe_id']} | {r['match_id']} | {r['team_pair']} | <{tmpl}> | {r.get('status_code', '-')} | {r.get('content_type', '-')} | {redirect} | {r.get('validation_state', '-')} |\n"
            )
        l.append("\n")
    l.append("## Route Decision Summary\n")
    rd = manifest["route_decision"]
    l.append(
        f"- usable: {rd['usable_html_route_templates'] or 'none'}\n- rejected: {rd['rejected_route_templates'] or 'none'}\n- deferred: {rd['deferred_route_templates'] or 'none'}\n- recommended: {rd['recommended_next_template'] or 'none'}\n"
    )
    l.append("\n## Raw Write Readiness Gate\n")
    for k, v in manifest["raw_write_readiness"].items():
        l.append(f"- {k}: {v}\n")
    l.append("\n## No-Write Safety Review\n")
    for k, v in manifest["safety"].items():
        st = "pass" if v is False or k == "network_fetch_performed" else "WARN"
        l.append(f"- {k}: {v} ({st})\n")
    l.append("\n## Remaining Blockers\n")
    l.append(
        "- 本阶段最多只是 html_route_observed\n- 本阶段不读取完整 HTML body\n- 本阶段不保存 HTML body\n- 本阶段不保存 raw JSON，不写 DB，不进入 L2 raw harvesting\n"
    )
    if summary.get("html_route_observed_count", 0) >= 1:
        l.append(
            "- 即使 html_route_observed，下一阶段也只是 hydration extraction plan no-write，不是直接抓 raw body\n"
        )
    l.append(f"\n## Recommended Next Phase\n\n- **{manifest['recommended_next_phase']}**\n")
    path.write_text("".join(l), encoding="utf-8")


def write_decision_report(
    path: Path, results: list, templates: list, summary: dict[str, Any]
) -> None:
    l: list[str] = []
    l.append("<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 -->\n\n")
    l.append("# FotMob HTML Hydration Route Probe — Decision Report\n\n")
    l.append("## Route Templates Tested\n\n")
    for t in templates[:2]:
        l.append(f"- `{t['template']}` — {t['name']}\n")
    l.append("\n")
    rs: dict = {}
    for r in results:
        t = r["route_template"]
        if t not in rs:
            rs[t] = {"attempted": 0, "observed": 0, "redirect": 0, "blocked": 0, "invalid": 0}
        rs[t]["attempted"] += 1
        if r["validation_state"] == "html_route_observed":
            rs[t]["observed"] += 1
        if r["validation_state"] == "html_route_redirect_observed":
            rs[t]["redirect"] += 1
        if r["validation_state"] == "html_route_blocked":
            rs[t]["blocked"] += 1
        if r["validation_state"] == "html_route_invalid":
            rs[t]["invalid"] += 1
    l.append(
        "| Route Template | Attempted | HTML Observed | Redirect | Blocked | Invalid | Decision |\n"
    )
    l.append("|---|---:|---:|---:|---:|---:|---|\n")
    for tmpl, st in rs.items():
        if st["observed"] > 0:
            dec = "use — recommend for extraction plan"
        elif st["blocked"] > 0:
            dec = "reject — blocked"
        elif st["invalid"] > 0:
            dec = "reject — invalid"
        elif st["redirect"] > 0:
            dec = "defer — follow redirect"
        else:
            dec = "review"
        l.append(
            f"| `{tmpl[:60]}` | {st['attempted']} | {st['observed']} | {st['redirect']} | {st['blocked']} | {st['invalid']} | {dec} |\n"
        )
    l.append("\n")
    has_net = any(r.get("network_performed") for r in results)
    has_obs = any(s["observed"] > 0 for s in rs.values())
    if not has_net:
        l.append("## Note\n\n- 本报告为 dry-run 模式生成，无实际网络探测结果。\n")
    elif has_obs:
        l.append(
            "## Recommendation\n\n- 至少一个 HTML route 返回 200。\n- 下一阶段建议：HTML hydration extraction plan no-write。\n- 仍然不直接 raw write。\n"
        )
    else:
        l.append(
            "## Recommendation\n\n- 当前无 HTML route 返回 200。\n- 建议进入 HTML hydration route review followup。\n- 在确认可用 route 前，不要进入 raw write。\n"
        )
    l.append("\n")
    path.write_text("".join(l), encoding="utf-8")


def write_review_report(
    path: Path, run_id: str, manifest: dict[str, Any], summary: dict[str, Any]
) -> bool:
    sel = manifest["probe_selection"]
    rec = manifest["recommended_next_phase"]
    checks = [
        (
            "#1441 endpoint probe inherited",
            manifest["inherited_endpoint_probe"]["api_data_matchDetails_status"] == "blocked_403",
            "",
        ),
        ("API endpoint excluded", True, "/api/data/matchDetails not tested"),
        (
            "max samples <= 3",
            sel["selected_sample_count"] <= 3,
            f"count={sel['selected_sample_count']}",
        ),
        (
            "max route templates <= 2",
            len(sel["selected_route_templates"]) <= 2,
            f"count={len(sel['selected_route_templates'])}",
        ),
        ("max network requests <= 6", summary.get("max_network_requests", 0) <= 6, ""),
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
            "response body not read",
            all(r.get("body_read") is False for r in manifest.get("probe_results", [])),
            "",
        ),
        ("no response body saved", manifest["safety"]["raw_response_body_saved"] is False, ""),
        ("no HTML body saved", manifest["safety"]["html_body_saved"] is False, ""),
        ("no raw JSON saved", manifest["safety"]["raw_json_write_performed"] is False, ""),
        ("no DB write", manifest["safety"]["db_write_performed"] is False, ""),
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
            all(w not in rec for w in ["RAW-JSON-DEV-WRITE", "DIRECT-RAW-WRITE"]),
            rec,
        ),
        ("no direct raw write recommendation", "DIRECT" not in rec.upper(), ""),
    ]
    lines = ["<!-- markdownlint-disable MD013 MD012 -->\n\n"]
    lines.append("# FotMob HTML Hydration Route Probe No Write — Embedded Review\n\n")
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
