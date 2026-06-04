#!/usr/bin/env python3
"""Report generators for FotMob HTML hydration extraction plan no-write.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HTML-HYDRATION-EXTRACTION-PLAN-NO-WRITE
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-HTML-HYDRATION-EXTRACTION-PLAN-NO-WRITE"
NEXT_PHASE = "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-LIMITED-HTML-HYDRATION-INSPECTION-NO-WRITE"


def write_report(
    path: Path,
    run_id: str,
    manifest: dict[str, Any],
    candidates: list,
    next_plan: dict[str, Any],
) -> None:
    l: list[str] = []
    l.append("<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 -->\n")
    l.append("# FotMob HTML Hydration Extraction Plan No Write\n\n")
    l.append(
        f"- lifecycle: current-state\n- phase: {PHASE}\n- run_id: {run_id}\n- mode: offline_extraction_plan\n\n"
    )
    l.append("## 当前阶段背景\n\n")
    l.append(
        "- #1442 验证 6/6 HTML routes 返回 200 text/html。\n- API 路线 (/api/data/matchDetails) 被 403 阻断。\n- HTML hydration route 现在是主要数据入口路径。\n- 本阶段只离线设计下一阶段安全提取方案，不读取 body。\n\n"
    )
    l.append("## #1442 Route Probe Inheritance\n\n")
    for k, v in manifest["inherited_route_probe"].items():
        l.append(f"- {k}: {v}\n")
    l.append("\n## Why HTML Route Is Now Primary Path\n\n")
    l.append(
        "- /api/data/matchDetails → HTTP 403 (anti-bot blocked)\n- /api/matchDetails → HTTP 404 (no /data/ prefix)\n- /match/{id} → HTTP 200 text/html ✅\n- /matches/{rc}/{id} → HTTP 200 text/html ✅\n- HTML hydration (__NEXT_DATA__ + pageProps) is the viable data extraction route.\n\n"
    )
    l.append("## Extraction Plan Candidate Matrix\n\n")
    l.append("| Candidate | Route | Match ID | RC | Body Limit | Markers | Priority |\n")
    l.append("|---|---|---|---:|---:|---|\n")
    for c in candidates:
        l.append(
            f"| {c['candidate_id']} | {c['route_template'][:50]} | {c['sample_match_id']} | {c['sample_route_code']} | {c['body_read_limit_bytes']} | {', '.join(c['allowed_markers'][:3])} | {c['recommended_priority']} |\n"
        )
    l.append("\n## Allowed Markers\n\n")
    for m in candidates[0]["allowed_markers"] if candidates else []:
        l.append(f"- `{m}`\n")
    l.append("\n## Forbidden Persistence\n\n")
    fp = next_plan.get("forbidden_persistence", [])
    for f in fp:
        l.append(f"- {f}\n")
    l.append("\n## Limited Inspection Next Plan\n\n")
    for k, v in next_plan.items():
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
    l.append("\n## Remaining Blockers\n\n")
    l.append(
        "- 本阶段没有联网、没有读取 HTML body、没有保存 HTML body、没有保存 raw JSON、没有写 DB\n- 下一阶段只是 limited inspection no-write，仍然不是 raw JSON 入库\n- L2 raw harvesting 仍然 blocked\n\n"
    )
    l.append(f"## Recommended Next Phase\n\n- **{manifest['recommended_next_phase']}**\n\n")
    path.write_text("".join(l), encoding="utf-8")


def write_next_plan_report(path: Path, candidates: list, next_plan: dict[str, Any]) -> None:
    l: list[str] = []
    l.append("<!-- markdownlint-disable MD013 MD034 MD012 MD022 MD032 MD050 -->\n\n")
    l.append("# FotMob Limited HTML Hydration Inspection — Next Plan\n\n")
    l.append("## Why Limited Inspection\n\n")
    l.append(
        "- HTML routes are confirmed viable (6/6 HTTP 200).\n- Before extracting full pageProps, we must verify __NEXT_DATA__ markers exist in first 256KB.\n- Limited inspection confirms structural viability without full body capture.\n\n"
    )
    l.append("## Selected Routes\n\n")
    for c in candidates[:2]:
        l.append(
            f"- `{c['route_template']}` — match_id={c['sample_match_id']}, pair={c['sample_pair']}\n"
        )
    l.append("\n## Probe Parameters\n\n")
    for k, v in next_plan.items():
        if isinstance(v, list):
            l.append(f"- **{k}**:\n")
            for item in v[:5]:
                l.append(f"  - {item}\n")
        else:
            l.append(f"- **{k}**: {v}\n")
    l.append("\n## Success Criteria\n\n")
    for s in next_plan.get("success_criteria", []):
        l.append(f"- {s}\n")
    l.append("\n## Stop Conditions\n\n")
    for s in next_plan.get("stop_conditions", []):
        l.append(f"- {s}\n")
    l.append("\n## What Must NOT Be Persisted\n\n")
    l.append(
        "- Full HTML body\n- Raw JSON\n- DB write\n- pageProps full extraction\n- __NEXT_DATA__ full dump\n- Any raw response body\n\n"
    )
    l.append("## After Success\n\n")
    l.append(
        f"- Next phase: **{next_plan.get('next_phase_after_success', 'extraction validation no-write')}**\n- Still not raw JSON write\n- L2 raw harvesting remains blocked\n\n"
    )
    l.append("## After Failure\n\n")
    l.append(f"- Fallback: **{next_plan.get('next_phase_after_failure', 'review followup')}**\n\n")
    path.write_text("".join(l), encoding="utf-8")


def write_review_report(path: Path, run_id: str, manifest: dict[str, Any]) -> bool:
    ih = manifest["inherited_route_probe"]
    np = manifest["limited_inspection_next_plan"]
    rec = manifest["recommended_next_phase"]
    checks = [
        ("#1442 route probe inherited", ih["html_route_observed_count"] == 6, ""),
        ("response_body_read=false inherited", ih["response_body_read"] is False, ""),
        ("extraction plan generated", len(manifest.get("extraction_plan_candidates", [])) >= 1, ""),
        ("next limited inspection plan generated", bool(np.get("max_network_requests")), ""),
        ("no network", manifest["safety"]["network_fetch_performed"] is False, ""),
        ("no response body read", manifest["safety"]["response_body_read"] is False, ""),
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
        ("recommended next phase safe", rec == NEXT_PHASE, rec),
        ("no direct raw write recommendation", "RAW-JSON-DEV-WRITE" not in rec, ""),
    ]
    lines = ["<!-- markdownlint-disable MD013 MD012 -->\n\n"]
    lines.append("# FotMob HTML Hydration Extraction Plan No Write — Embedded Review\n\n")
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
