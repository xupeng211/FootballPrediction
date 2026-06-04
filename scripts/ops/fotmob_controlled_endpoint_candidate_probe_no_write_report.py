#!/usr/bin/env python3
"""Report generators for FotMob controlled endpoint candidate probe no-write.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-ENDPOINT-CANDIDATE-PROBE-NO-WRITE
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-ENDPOINT-CANDIDATE-PROBE-NO-WRITE"


def write_report(
    path: Path,
    run_id: str,
    mode: str,
    manifest: dict[str, Any],
    samples: list[dict[str, str]],
    templates: list[dict[str, Any]],
    summary: dict[str, Any],
) -> None:
    lines: list[str] = []
    lines.append("<!-- markdownlint-disable MD013 MD034 -->")
    lines.append("")
    lines.append("# FotMob Controlled Endpoint Candidate Probe No Write")
    lines.append("")
    lines.append(f"- lifecycle: current-state")
    lines.append(f"- phase: {PHASE}")
    lines.append(f"- run_id: {run_id}")
    lines.append(f"- mode: {mode}")
    lines.append("")

    lines.append("## 当前阶段背景")
    lines.append("")
    lines.append("- #1440 endpoint review 完成，推荐了 3 个候选 endpoint templates。")
    lines.append("- 本阶段用真实 match_id 和 route_code 做 controlled live probe。")
    lines.append("- 只保存 metadata，不保存 response body。")
    lines.append("")

    lines.append("## #1440 Endpoint Review Inheritance")
    lines.append("")
    for k, v in manifest["inherited_endpoint_review"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")

    lines.append("## Selected Probe Samples")
    lines.append("")
    for i, s in enumerate(samples):
        lines.append(
            f"{i + 1}. match_id={s['match_id']}, route_code={s['route_code']}, pair={s['team_pair']}"
        )
    lines.append("")

    lines.append("## Endpoint Templates Tested")
    lines.append("")
    for i, t in enumerate(templates):
        lines.append(f"{i + 1}. `{t['template']}` — {t['reason']}")
    lines.append("")

    lines.append("## Network Probe Summary")
    lines.append("")
    for k, v in summary.items():
        lines.append(f"- {k}: {v}")
    lines.append("")

    results = manifest.get("probe_results", [])
    if results:
        lines.append("## Probe Result Details")
        lines.append("")
        lines.append(
            "| Probe ID | Match ID | Team Pair | Endpoint | Status | Content-Type | JSON OK | Top-Level Keys | Validation State |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for r in results:
            keys = ", ".join(r.get("top_level_key_names", [])) or "-"
            tmpl_short = r["endpoint_template"][:50]
            lines.append(
                f"| {r['probe_id']} | {r['match_id']} | {r['team_pair']} | "
                f"<{tmpl_short}> | {r.get('status_code', '-')} | "
                f"{r.get('content_type', '-')} | {r.get('json_parse_ok', False)} | "
                f"{keys} | {r.get('validation_state', '-')} |"
            )
        lines.append("")

    lines.append("## Endpoint Decision Summary")
    lines.append("")
    ed = manifest["endpoint_decision"]
    lines.append(f"- usable: {ed['usable_endpoint_templates'] or 'none'}")
    lines.append(f"- rejected: {ed['rejected_endpoint_templates'] or 'none'}")
    lines.append(f"- deferred: {ed['deferred_endpoint_templates'] or 'none'}")
    lines.append(f"- recommended: {ed['recommended_next_template'] or 'none'}")
    lines.append("")

    lines.append("## Raw Write Readiness Gate")
    lines.append("")
    for k, v in manifest["raw_write_readiness"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")

    lines.append("## No-Write Safety Review")
    lines.append("")
    for k, v in manifest["safety"].items():
        status = "pass" if v is False or k == "network_fetch_performed" else "WARN"
        lines.append(f"- {k}: {v} ({status})")
    lines.append("")

    lines.append("## Remaining Blockers")
    lines.append("")
    lines.append("- 本阶段最多只是 endpoint_candidate_json_observed")
    lines.append("- 本阶段不保存 raw JSON body，不写 DB，不进入 L2 raw harvesting")
    json_ok = summary.get("json_parse_ok_count", 0)
    if json_ok >= 1:
        lines.append(
            "- 即使 json_parse_ok，下一阶段也只是 raw body capture planning no-write，不是直接入库"
        )
    lines.append("")

    lines.append("## Recommended Next Phase")
    lines.append("")
    lines.append(f"- **{manifest['recommended_next_phase']}**")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def write_decision_report(
    path: Path,
    manifest: dict[str, Any],
    results: list[dict[str, Any]],
    templates: list[dict[str, Any]],
    summary: dict[str, Any],
) -> None:
    lines: list[str] = []
    lines.append("<!-- markdownlint-disable MD013 MD034 -->")
    lines.append("")
    lines.append("# FotMob Controlled Endpoint Candidate Probe — Decision Report")
    lines.append("")

    lines.append("## Endpoint Templates Tested")
    lines.append("")
    for t in templates:
        lines.append(f"- `{t['template']}` — {t['reason']}")
    lines.append("")

    # Per-template stats
    ep_stats: dict[str, dict] = {}
    for r in results:
        t = r["endpoint_template"]
        if t not in ep_stats:
            ep_stats[t] = {"attempted": 0, "json_ok": 0, "html": 0, "blocked": 0, "invalid": 0}
        ep_stats[t]["attempted"] += 1
        if r.get("json_parse_ok"):
            ep_stats[t]["json_ok"] += 1
        if r.get("validation_state") == "endpoint_candidate_html":
            ep_stats[t]["html"] += 1
        if r.get("validation_state") == "endpoint_candidate_blocked":
            ep_stats[t]["blocked"] += 1
        if r.get("validation_state") == "endpoint_candidate_invalid":
            ep_stats[t]["invalid"] += 1

    lines.append(
        "| Endpoint Template | Attempted | JSON Observed | HTML | Blocked | Invalid | Decision |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---|")
    for tmpl, stats in ep_stats.items():
        if stats["json_ok"] > 0:
            dec = "use — recommended for next phase"
        elif stats["blocked"] > 0:
            dec = "reject — blocked by anti-bot"
        elif stats["invalid"] > 0:
            dec = "reject — invalid endpoint"
        elif stats["html"] > 0:
            dec = "defer — HTML page, needs body parsing"
        else:
            dec = "review"
        short = tmpl[:60]
        lines.append(
            f"| `{short}` | {stats['attempted']} | {stats['json_ok']} | "
            f"{stats['html']} | {stats['blocked']} | {stats['invalid']} | {dec} |"
        )
    lines.append("")

    json_ok = any(s["json_ok"] > 0 for s in ep_stats.values())
    has_results = any(r.get("network_performed") for r in results)

    if not has_results:
        lines.append("## Note")
        lines.append("")
        lines.append("- 本报告为 dry-run 模式生成，无实际网络探测结果。")
    elif json_ok:
        lines.append("## Recommendation")
        lines.append("")
        lines.append("- 至少一个 endpoint 返回 JSON。")
        lines.append("- 下一阶段建议：controlled raw body capture planning no-write。")
        lines.append("- 仍然不直接 raw JSON write。")
    else:
        lines.append("## Recommendation")
        lines.append("")
        lines.append("- 当前无 endpoint 返回成功 JSON。")
        lines.append("- 建议进入 endpoint candidate review followup。")
        lines.append("- 在确认可用 endpoint 前，不要进入 raw JSON write。")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def write_review_report(
    path: Path,
    run_id: str,
    manifest: dict[str, Any],
    summary: dict[str, Any],
) -> bool:
    sel = manifest["probe_selection"]
    rec = manifest["recommended_next_phase"]

    checks: list[tuple[str, bool, str]] = [
        (
            "#1440 endpoint review inherited",
            manifest["inherited_endpoint_review"]["endpoint_candidate_count"] >= 1,
            "",
        ),
        (
            "max samples <= 3",
            sel["selected_sample_count"] <= 3,
            f"count={sel['selected_sample_count']}",
        ),
        (
            "max endpoint templates <= 3",
            len(sel["selected_endpoint_templates"]) <= 3,
            f"count={len(sel['selected_endpoint_templates'])}",
        ),
        ("max network requests <= 9", summary.get("max_network_requests", 0) <= 9, ""),
        (
            "no network when dry-run",
            (
                not summary.get("allow_network_probe")
                and summary.get("network_requests_attempted", 0) == 0
            )
            or summary.get("allow_network_probe"),
            "",
        ),
        ("no response body saved", manifest["safety"]["raw_response_body_saved"] is False, ""),
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

    lines: list[str] = []
    lines.append("<!-- markdownlint-disable MD013 -->")
    lines.append("")
    lines.append("# FotMob Controlled Endpoint Candidate Probe No Write — Embedded Review")
    lines.append("")
    lines.append(f"- lifecycle: current-state")
    lines.append(f"- phase: {PHASE} (review)")
    lines.append(f"- run_id: {run_id}")
    lines.append("")

    all_pass = True
    for name, passed, detail in checks:
        st = "pass" if passed else "FAIL"
        if not passed:
            all_pass = False
        d = f" ({detail})" if detail else ""
        lines.append(f"- [{st}] {name}{d}")

    lines.append("")
    lines.append(f"## Overall: {'pass' if all_pass else 'BLOCKED'}")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return all_pass
