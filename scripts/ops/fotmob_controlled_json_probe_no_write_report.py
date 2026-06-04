#!/usr/bin/env python3
"""Report generators for FotMob controlled JSON probe no-write.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-JSON-PROBE-NO-WRITE
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-CONTROLLED-JSON-PROBE-NO-WRITE"


def write_report(
    report_path: Path,
    run_id: str,
    mode: str,
    manifest: dict[str, Any],
    selected: list[dict[str, Any]],
    probe_results: list[dict[str, Any]],
    probe_summary: dict[str, Any],
) -> None:
    """Write the human-readable report (Chinese-primary)."""
    lines: list[str] = []
    lines.append("<!-- markdownlint-disable MD013 MD034 -->")
    lines.append("")
    lines.append("# FotMob Controlled JSON Probe No Write")
    lines.append("")
    lines.append("- lifecycle: current-state")
    lines.append(f"- phase: {PHASE}")
    lines.append(f"- run_id: {run_id}")
    lines.append(f"- mode: {mode}")
    lines.append("")

    lines.append("## 当前阶段背景")
    lines.append("")
    lines.append("- 从 #1438 known match page seed parse 进入。")
    lines.append("- 使用 #1438 解析出的真实 FotMob match_id 进行 JSON endpoint 探测。")
    lines.append("- 最多 3 个样本，最多 3 个 endpoint / 样本，最多 9 个 HTTP request。")
    lines.append("- 只保存 metadata，不保存 response body。")
    lines.append("")

    lines.append("## #1438 Seed Inheritance")
    lines.append("")
    for k, v in manifest["inherited_seed_status"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")

    lines.append("## Selected Probe Samples")
    lines.append("")
    for i, s in enumerate(selected):
        lines.append(
            f"{i + 1}. {s['team_hint']} vs {s['opponent_hint']} "
            f"(route_code={s['route_code']}, match_id={s['fotmob_match_id']})"
        )
    lines.append("")

    lines.append("## Endpoint Candidate Plan")
    lines.append("")
    lines.append("| # | Endpoint Template | Reason |")
    lines.append("|---|---|")
    for i, ep in enumerate(manifest["endpoint_candidates"]):
        lines.append(f"| {i + 1} | `{ep['endpoint_template']}` | {ep['reason']} |")
    lines.append("")

    lines.append("## Network Probe Summary")
    lines.append("")
    for k, v in probe_summary.items():
        lines.append(f"- {k}: {v}")
    lines.append("")

    if probe_results:
        lines.append("## Probe Result Details")
        lines.append("")
        lines.append(
            "| Probe ID | Match ID | Endpoint | Status | Content-Type | JSON OK | "
            "Top-Level Keys | Validation State | Stop Reason |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for r in probe_results:
            keys = ", ".join(r.get("top_level_key_names", [])) or "-"
            lines.append(
                f"| {r['probe_id']} | {r['fotmob_match_id']} | "
                f"<{r['endpoint_template']}> | {r.get('status_code', '-')} | "
                f"{r.get('content_type', '-')} | {r.get('json_parse_ok', False)} | "
                f"{keys} | {r.get('validation_state', '-')} | "
                f"{r.get('stop_reason', '-')} |"
            )
        lines.append("")

    lines.append("## Raw Write Readiness Gate")
    lines.append("")
    for k, v in manifest["json_probe_readiness"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")

    lines.append("## No-Write Safety Review")
    lines.append("")
    safety = manifest["safety"]
    for k, v in safety.items():
        status = "✅" if v is False or k == "network_fetch_performed" else "⚠️"
        lines.append(f"- {k}: {v} {status}")
    lines.append("")

    lines.append("## Remaining Blockers")
    lines.append("")
    lines.append("- 本阶段最多只是 json_probe_observed")
    lines.append("- 本阶段不保存 raw JSON body")
    lines.append("- 本阶段不写 DB")
    lines.append("- 本阶段不进入 L2 raw harvesting")
    if probe_summary.get("json_parse_ok_count", 0) >= 1:
        lines.append(
            "- 即使 json_parse_ok，下一阶段也只能是 controlled raw JSON dev write planning"
        )
    lines.append("")

    lines.append("## Recommended Next Phase")
    lines.append("")
    lines.append(f"- **{manifest['recommended_next_phase']}**")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")


def write_endpoint_decision_report(
    path: Path,
    manifest: dict[str, Any],
    probe_results: list[dict[str, Any]],
) -> None:
    """Write the endpoint decision report."""
    lines: list[str] = []
    lines.append("<!-- markdownlint-disable MD013 MD034 -->")
    lines.append("")
    lines.append("# FotMob Controlled JSON Probe — Endpoint Decision Report")
    lines.append("")
    lines.append("## Endpoint Templates Tested")
    lines.append("")
    for ep in manifest["endpoint_candidates"]:
        lines.append(f"- `{ep['endpoint_template']}` — {ep['reason']}")
    lines.append("")

    ep_stats: dict[str, dict[str, int]] = {}
    for r in probe_results:
        tmpl = r["endpoint_template"]
        if tmpl not in ep_stats:
            ep_stats[tmpl] = {"attempted": 0, "json_ok": 0, "html": 0, "blocked": 0, "invalid": 0}
        ep_stats[tmpl]["attempted"] += 1
        if r.get("json_parse_ok"):
            ep_stats[tmpl]["json_ok"] += 1
        if r.get("validation_state") == "json_probe_not_json":
            ep_stats[tmpl]["html"] += 1
        if r.get("validation_state") == "json_probe_blocked":
            ep_stats[tmpl]["blocked"] += 1
        if r.get("validation_state") == "json_probe_invalid":
            ep_stats[tmpl]["invalid"] += 1

    lines.append(
        "| Endpoint Template | Attempted | JSON OK | HTML | Blocked | Invalid | Decision |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---|")
    json_ok_any = False
    for tmpl, stats in ep_stats.items():
        if stats["json_ok"] > 0:
            json_ok_any = True
            decision = "use (recommended for next phase)"
        elif stats["blocked"] > 0:
            decision = "blocked — review required"
        elif stats["invalid"] > 0:
            decision = "invalid — investigate endpoint"
        else:
            decision = "review — unexpected result"
        tmpl_short = tmpl[:60]
        lines.append(
            f"| `{tmpl_short}` | {stats['attempted']} | {stats['json_ok']} | "
            f"{stats['html']} | {stats['blocked']} | {stats['invalid']} | {decision} |"
        )
    lines.append("")

    if not probe_results or not any(r.get("network_performed") for r in probe_results):
        lines.append("## Note")
        lines.append("")
        lines.append("- 本报告为 dry-run 模式生成，无实际网络探测结果。")
        lines.append("- 执行 `--allow-network-probe` 后重新生成以获取实际决策数据。")
    elif not json_ok_any:
        lines.append("## Recommendation")
        lines.append("")
        lines.append("- 当前无 endpoint 返回成功 JSON。")
        lines.append("- 建议进入 endpoint review phase，检查 block/invalid 原因。")
        lines.append("- 在确认可用 endpoint 前，不要进入 raw JSON write。")
    else:
        lines.append("## Recommendation")
        lines.append("")
        lines.append("- 至少一个 endpoint 成功返回 JSON。")
        lines.append("- 下一阶段建议：controlled raw JSON dev write planning。")
        lines.append("- 仍然不直接 raw JSON write，不直接入库。")
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def write_review_report(
    path: Path,
    run_id: str,
    manifest: dict[str, Any],
    probe_summary: dict[str, Any],
) -> bool:
    """Write the embedded review report. Returns True if all pass."""
    checks: list[tuple[str, bool, str]] = []

    ih = manifest["inherited_seed_status"]
    checks.append(
        (
            "#1438 seed status inherited",
            ih["user_seed_count"] == 12,
            f"user_seed_count={ih['user_seed_count']}",
        )
    )

    sel = manifest["probe_selection"]
    checks.append(
        (
            "max samples <= 3",
            sel["selected_sample_count"] <= 3,
            f"count={sel['selected_sample_count']}",
        )
    )
    checks.append(
        (
            "max endpoint candidates <= 3 per sample",
            len(manifest["endpoint_candidates"]) <= 3,
            f"count={len(manifest['endpoint_candidates'])}",
        )
    )
    checks.append(
        (
            "max network requests <= 9",
            probe_summary.get("max_network_requests", 0) <= 9,
            f"max={probe_summary.get('max_network_requests')}",
        )
    )

    if not probe_summary.get("allow_network_probe"):
        checks.append(
            (
                "no network when allow_network_probe=false",
                probe_summary.get("network_requests_attempted", 0) == 0,
                "",
            )
        )
    else:
        checks.append(
            (
                "network requests <= max",
                probe_summary.get("network_requests_attempted", 0)
                <= probe_summary.get("max_network_requests", 9),
                "",
            )
        )

    safety = manifest["safety"]
    for key, label in [
        ("raw_response_body_saved", "no response body saved"),
        ("raw_json_write_performed", "no raw JSON saved"),
        ("db_write_performed", "no DB write"),
        ("scheduler_enabled", "no scheduler"),
        ("feature_parse_performed", "no feature parse"),
        ("browser_automation_performed", "no browser automation"),
        ("captcha_bypass_performed", "no captcha bypass"),
        ("proxy_rotation_performed", "no proxy rotation"),
    ]:
        checks.append((label, safety[key] is False, ""))

    rw = manifest["json_probe_readiness"]
    checks.append(("json_validated_count=0", rw["json_validated_count"] == 0, ""))
    checks.append(("raw_write_eligible_count=0", rw["raw_write_eligible_count"] == 0, ""))

    rec = manifest["recommended_next_phase"]
    safe = True
    for w in ["RAW-JSON-DEV-WRITE", "RAW-MATCH-DATA"]:
        if w in rec:
            safe = False
    checks.append(("recommended next phase safe", safe, rec))
    checks.append(("no direct raw write recommendation", "DIRECT" not in rec.upper(), ""))

    lines: list[str] = []
    lines.append("<!-- markdownlint-disable MD013 -->")
    lines.append("")
    lines.append("# FotMob Controlled JSON Probe No Write — Embedded Review")
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
