#!/usr/bin/env python3
"""FotMob raw JSON long-run collector dry-run helper.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-DRY-RUN

This helper reads synthetic target fixtures and generates a dry-run collection plan.
It does NOT access the network, connect to a database, write raw JSON, or parse features.

Usage:
    python scripts/ops/fotmob_raw_json_long_run_collector_dry_run.py \
        --input-targets docs/_fixtures/fotmob_long_run_collector_dry_run_targets.json \
        --output-manifest docs/_manifests/fotmob_raw_json_long_run_collector_dry_run_manifest.json \
        --report docs/_reports/FOTMOB_RAW_JSON_LONG_RUN_COLLECTOR_DRY_RUN.md \
        --request-budget 10 \
        --per-team-budget 5 \
        --per-competition-budget 4 \
        --run-id fotmob_long_run_collector_dry_run_v1
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------------
SELECTABLE_STATES = {"pending_raw_fetch", "failed"}
"""target_state values that are eligible for selection."""

SKIP_STATES = {"blocked"}
"""target_state values that are skipped by default (unless include_blocked)."""

SKIP_RAW_JSON_STATUSES = {"stored"}
"""raw_json_status values that mean the target already has stored raw JSON."""

SELECTABLE_RAW_JSON_STATUSES = {"missing", "stale", "failed"}
"""raw_json_status values that mean raw JSON collection is still needed."""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_fixture(targets: list[dict]) -> list[str]:
    """Run pre-flight checks on the loaded target fixture.  Returns a list of
    validation error messages (empty = all good)."""
    errors: list[str] = []

    if not targets:
        errors.append("targets 数组为空")
        return errors

    team_names: set[str] = set()
    competition_types: set[str] = set()
    competition_names: set[str] = set()
    team_types: set[str] = set()
    target_states: set[str] = set()
    raw_json_statuses: set[str] = set()
    calendar_cases: set[str] = set()

    for i, t in enumerate(targets):
        prefix = f"targets[{i}]"
        for field in (
            "source",
            "source_match_id",
            "team_names",
            "competition_name",
            "competition_type",
            "target_state",
            "raw_json_status",
            "priority",
            "match_date",
        ):
            if field not in t:
                errors.append(f"{prefix}: 缺少必填字段 {field}")

        team_names.update(t.get("team_names", []))
        competition_types.add(t.get("competition_type", ""))
        competition_names.add(t.get("competition_name", ""))
        team_types.add(t.get("team_type", ""))
        target_states.add(t.get("target_state", ""))
        raw_json_statuses.add(t.get("raw_json_status", ""))
        calendar_cases.add(t.get("team_calendar_case", ""))

    # Coverage checks
    if "club" not in team_types:
        errors.append("缺少 club 样例")
    if "national" not in team_types:
        errors.append("缺少 national team 样例")
    if "domestic_cup" not in competition_types:
        errors.append("缺少 domestic_cup 样例")
    if "continental_club" not in competition_types:
        errors.append("缺少 continental_club 样例")
    if "international_qualifier" not in competition_types:
        errors.append("缺少 international_qualifier 样例")
    if "nations_league" not in competition_types:
        errors.append("缺少 nations_league 样例")
    if "friendly" not in competition_types:
        errors.append("缺少 friendly 样例")

    has_j_league_or_japanese = any(
        "J1" in cn or "J.League" in cn or "Emperor" in cn for cn in competition_names
    )
    if not has_j_league_or_japanese:
        errors.append("缺少 J League 或 Japanese club 样例")

    has_secondary = any(
        "Championship" in cn or "secondary" in cc.lower()
        for cn in competition_names
        for cc in calendar_cases
    )
    if not has_secondary:
        errors.append("缺少 secondary league 样例")

    has_blocked = "blocked" in target_states
    if not has_blocked:
        errors.append("缺少 blocked target 样例（无法验证 skip 逻辑）")

    has_stored = "stored" in raw_json_statuses
    if not has_stored:
        errors.append("缺少 raw_json_status=stored 样例（无法验证 skip 逻辑）")

    return errors


# ---------------------------------------------------------------------------
# Target selection
# ---------------------------------------------------------------------------
def classify_targets(
    targets: list[dict], include_blocked: bool = False
) -> tuple[list[dict], list[dict]]:
    """Split targets into (selectable, skipped).  Skipped targets carry a
    `skip_reason` string."""
    selectable: list[dict] = []
    skipped: list[dict] = []

    for t in targets:
        state = t.get("target_state", "")
        raw_status = t.get("raw_json_status", "")

        if state in SKIP_STATES and not include_blocked:
            skipped.append({**t, "skip_reason": f"target_state={state} (默认跳过)"})
            continue

        if raw_status in SKIP_RAW_JSON_STATUSES:
            skipped.append({**t, "skip_reason": f"raw_json_status={raw_status} (已存储)"})
            continue

        if state not in SELECTABLE_STATES:
            skipped.append({**t, "skip_reason": f"target_state={state} (不可选状态)"})
            continue

        selectable.append(t)

    # Sort: lower priority first, then earlier match_date first
    selectable.sort(key=lambda x: (x.get("priority", 999), x.get("match_date", "9999")))
    return selectable, skipped


def apply_budget(
    selectable: list[dict],
    request_budget: int,
    per_team_budget: int,
    per_competition_budget: int,
) -> tuple[list[dict], list[dict]]:
    """Apply budgets and produce (selected, budget_skipped)."""
    selected: list[dict] = []
    budget_skipped: list[dict] = []

    team_counts: dict[str, int] = {}
    competition_counts: dict[str, int] = {}

    for t in selectable:
        if request_budget > 0 and len(selected) >= request_budget:
            budget_skipped.append({**t, "skip_reason": "request_budget exhausted"})
            continue

        # Count teams for this target
        team_ids = t.get("team_ids", t.get("team_names", []))
        # Check per-team budget
        team_skip = False
        for tid in team_ids:
            current = team_counts.get(tid, 0)
            if current >= per_team_budget:
                budget_skipped.append({**t, "skip_reason": f"per_team_budget exhausted for {tid}"})
                team_skip = True
                break

        if team_skip:
            continue

        # Check per-competition budget
        comp_id = t.get("competition_id", t.get("competition_name", ""))
        current_comp = competition_counts.get(comp_id, 0)
        if current_comp >= per_competition_budget:
            budget_skipped.append(
                {**t, "skip_reason": f"per_competition_budget exhausted for {comp_id}"}
            )
            continue

        # All budgets pass — select this target
        selected.append(t)
        for tid in team_ids:
            team_counts[tid] = team_counts.get(tid, 0) + 1
        competition_counts[comp_id] = current_comp + 1

    return selected, budget_skipped


# ---------------------------------------------------------------------------
# Coverage analysis
# ---------------------------------------------------------------------------
def analyze_coverage(selected: list[dict]) -> dict:
    """Return coverage flags for the selected target set."""
    competition_types = {t.get("competition_type", "") for t in selected}
    calendar_cases = {t.get("team_calendar_case", "") for t in selected}
    team_types = {t.get("team_type", "") for t in selected}

    def _has_competition(name_str: str) -> bool:
        return any(name_str.lower() in ct.lower() for ct in competition_types)

    return {
        "club_calendar_case_present": "club" in team_types,
        "national_team_case_present": "national" in team_types,
        "domestic_cup_case_present": _has_competition("domestic_cup"),
        "continental_club_case_present": _has_competition("continental_club"),
        "international_qualifier_case_present": _has_competition("international_qualifier"),
        "nations_league_case_present": _has_competition("nations_league"),
        "friendly_case_present": _has_competition("friendly"),
        "japanese_club_case_present": any(
            "japanese" in cc.lower() or "j1" in cc.lower() or "j_league" in cc.lower()
            for cc in calendar_cases
        ),
        "secondary_league_case_present": any(
            "secondary" in cc.lower() or "championship" in cc.lower() for cc in calendar_cases
        ),
        "man_united_cross_competition_present": any(
            "man_united" in cc.lower() for cc in calendar_cases
        ),
        "england_national_team_present": any(
            "england_national" in cc.lower() for cc in calendar_cases
        ),
    }


# ---------------------------------------------------------------------------
# Output generators
# ---------------------------------------------------------------------------
def build_manifest(
    run_id: str,
    generated_at: str,
    input_target_count: int,
    selected: list[dict],
    all_skipped: list[dict],
    request_budget: int,
    per_team_budget: int,
    per_competition_budget: int,
    coverage: dict,
) -> dict:
    """Build the dry-run manifest dict."""
    return {
        "schema_version": "fotmob_raw_json_long_run_collector_dry_run_v1",
        "lifecycle": "current-state",
        "phase": "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-DRY-RUN",
        "run_id": run_id,
        "generated_at": generated_at,
        "input_target_count": input_target_count,
        "selected_target_count": len(selected),
        "skipped_target_count": len(all_skipped),
        "request_budget": request_budget,
        "per_team_budget": per_team_budget,
        "per_competition_budget": per_competition_budget,
        "selected_targets": [
            {
                "source_match_id": t["source_match_id"],
                "team_names": t.get("team_names", []),
                "competition_name": t.get("competition_name", ""),
                "competition_type": t.get("competition_type", ""),
                "team_calendar_case": t.get("team_calendar_case", ""),
                "target_state": t.get("target_state", ""),
                "raw_json_status": t.get("raw_json_status", ""),
                "priority": t.get("priority"),
                "match_date": t.get("match_date", ""),
            }
            for t in selected
        ],
        "skipped_targets": [
            {
                "source_match_id": t["source_match_id"],
                "team_names": t.get("team_names", []),
                "competition_name": t.get("competition_name", ""),
                "competition_type": t.get("competition_type", ""),
                "target_state": t.get("target_state", ""),
                "raw_json_status": t.get("raw_json_status", ""),
                "skip_reason": t.get("skip_reason", "unknown"),
            }
            for t in all_skipped
        ],
        "budget": {
            "request_budget": request_budget,
            "per_team_budget": per_team_budget,
            "per_competition_budget": per_competition_budget,
            "selected_count": len(selected),
            "remaining_budget": max(0, request_budget - len(selected)),
        },
        "stop_policy": {
            "stop_on_403": True,
            "stop_on_429": True,
            "stop_on_captcha": True,
            "stop_on_unexpected_html": True,
            "stop_on_schema_shift": True,
            "no_retry_storm": True,
            "no_proxy_rotation": True,
            "no_anti_bot_bypass": True,
            "no_browser_automation": True,
        },
        "coverage": coverage,
        "safety": {
            "network_fetch_performed": False,
            "db_write_performed": False,
            "raw_json_write_performed": False,
            "feature_parse_performed": False,
            "scheduler_enabled": False,
            "raw_write_ready_marked": False,
        },
        "recommended_next_phase": "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-DRY-RUN-REVIEW",
    }


def _coverage_summary_lines(coverage: dict) -> list[str]:
    """Return Chinese-language coverage summary lines."""
    return [
        f"- 俱乐部赛程覆盖: {'是' if coverage.get('club_calendar_case_present') else '否'}",
        f"- 国家队赛程覆盖: {'是' if coverage.get('national_team_case_present') else '否'}",
        f"- 国内杯赛覆盖: {'是' if coverage.get('domestic_cup_case_present') else '否'}",
        f"- 洲际俱乐部赛事覆盖: {'是' if coverage.get('continental_club_case_present') else '否'}",
        f"- 国际预选赛覆盖: {'是' if coverage.get('international_qualifier_case_present') else '否'}",
        f"- 欧国联覆盖: {'是' if coverage.get('nations_league_case_present') else '否'}",
        f"- 友谊赛覆盖: {'是' if coverage.get('friendly_case_present') else '否'}",
        f"- 日本俱乐部/J League 覆盖: {'是' if coverage.get('japanese_club_case_present') else '否'}",
        f"- 次级联赛覆盖: {'是' if coverage.get('secondary_league_case_present') else '否'}",
        f"- Manchester United 跨赛事覆盖: {'是' if coverage.get('man_united_cross_competition_present') else '否'}",
        f"- England 国家队覆盖: {'是' if coverage.get('england_national_team_present') else '否'}",
    ]


def build_report(
    run_id: str,
    generated_at: str,
    input_target_count: int,
    selected: list[dict],
    all_skipped: list[dict],
    request_budget: int,
    per_team_budget: int,
    per_competition_budget: int,
    coverage: dict,
    validation_errors: list[str],
) -> str:
    """Build the dry-run report as Markdown (Chinese-language)."""
    lines = [
        "<!-- markdownlint-disable MD013 -->",
        "",
        "# FotMob Raw JSON 长期采集器 Dry-run 报告",
        "",
        "- lifecycle: current-state",
        "- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-DRY-RUN",
        f"- run_id: {run_id}",
        f"- generated_at: {generated_at}",
        "",
        "## 1. 概要",
        "",
        f"- 输入目标总数: {input_target_count}",
        f"- 选中目标数: {len(selected)}",
        f"- 跳过目标数: {len(all_skipped)}",
        f"- 请求预算: {request_budget}",
        f"- 单队预算: {per_team_budget}",
        f"- 单赛事预算: {per_competition_budget}",
        "",
        "## 2. 阶段安全声明",
        "",
        "- **本阶段没有 live fetch**",
        "- **本阶段没有 DB write**",
        "- **本阶段没有 raw JSON write**",
        "- **本阶段没有 feature parse**",
        "- **本阶段没有 scheduler 启用**",
        "- 这只是采集计划模拟（dry-run）",
        "- 支持跨赛事球队全年赛程",
        "- 所有目标是 synthetic metadata-only",
        "",
        "## 3. 预算结果",
        "",
        f"- request_budget={request_budget}，已使用 {len(selected)}",
        f"- per_team_budget={per_team_budget}",
        f"- per_competition_budget={per_competition_budget}",
        f"- 剩余预算: {max(0, request_budget - len(selected))}",
        "",
    ]

    # Validation errors
    if validation_errors:
        lines.append("## 4. 验证警告")
        lines.append("")
        for e in validation_errors:
            lines.append(f"- ⚠ {e}")
        lines.append("")
    else:
        lines.append("## 4. 验证结果")
        lines.append("")
        lines.append("- 全部通过 ✓")
        lines.append("")

    # Coverage
    lines.append("## 5. 覆盖范围")
    lines.append("")
    lines.extend(_coverage_summary_lines(coverage))
    lines.append("")

    # Selected targets
    lines.append("## 6. 选中目标明细")
    lines.append("")
    if selected:
        lines.append(
            "| # | source_match_id | team_names | competition | type | priority | match_date |"
        )
        lines.append(
            "|---|-----------------|------------|-------------|------|----------|------------|"
        )
        for i, t in enumerate(selected, 1):
            team_str = ", ".join(t.get("team_names", [])[:2])
            lines.append(
                f"| {i} | {t['source_match_id']} | {team_str} | "
                f"{t.get('competition_name', '')} | {t.get('competition_type', '')} | "
                f"{t.get('priority', '')} | {t.get('match_date', '')} |"
            )
    else:
        lines.append("（无）")
    lines.append("")

    # Skipped targets
    lines.append("## 7. 跳过目标明细")
    lines.append("")
    if all_skipped:
        lines.append("| # | source_match_id | team_names | skip_reason |")
        lines.append("|---|-----------------|------------|-------------|")
        for i, t in enumerate(all_skipped, 1):
            team_str = ", ".join(t.get("team_names", [])[:2])
            lines.append(
                f"| {i} | {t['source_match_id']} | {team_str} | {t.get('skip_reason', 'unknown')} |"
            )
    else:
        lines.append("（无）")
    lines.append("")

    # Team full-calendar examples
    lines.append("## 8. 球队全年赛程示例")
    lines.append("")

    lines.append("### 8.1 Manchester United 跨赛事示例")
    mun_targets = [t for t in selected if "man_united" in t.get("team_calendar_case", "").lower()]
    if mun_targets:
        lines.append("")
        lines.append(f"Manchester United 在本次 dry-run 中有 {len(mun_targets)} 个目标跨以下赛事：")
        lines.append("")
        for t in mun_targets:
            lines.append(
                f"- {t.get('competition_name', '')} ({t.get('competition_type', '')}) — {t.get('match_date', '')}"
            )
        lines.append("")
        lines.append(
            "这说明系统可以按球队跨 Premier League、FA Cup、EFL Cup、UEFA competitions 还原全年赛程。"
        )
    else:
        lines.append("")
        lines.append("Manchester United 跨赛事目标未出现在选中列表中（可能被预算裁剪）。")
    lines.append("")

    lines.append("### 8.2 England 国家队示例")
    eng_targets = [
        t for t in selected if "england_national" in t.get("team_calendar_case", "").lower()
    ]
    if eng_targets:
        lines.append("")
        lines.append(f"England 国家队在本次 dry-run 中有 {len(eng_targets)} 个目标跨以下赛事：")
        lines.append("")
        for t in eng_targets:
            lines.append(
                f"- {t.get('competition_name', '')} ({t.get('competition_type', '')}) — {t.get('match_date', '')}"
            )
        lines.append("")
        lines.append("这说明系统可以覆盖 World Cup qualifier、UEFA Nations League 和 Friendly。")
    else:
        lines.append("")
        lines.append("England 国家队目标未出现在选中列表中（可能被预算裁剪）。")
    lines.append("")

    lines.append("### 8.3 日本俱乐部示例")
    jpn_targets = [
        t for t in selected if "japanese_club" in t.get("team_calendar_case", "").lower()
    ]
    if jpn_targets:
        lines.append("")
        lines.append(f"日本俱乐部在本次 dry-run 中有 {len(jpn_targets)} 个目标：")
        lines.append("")
        for t in jpn_targets:
            lines.append(
                f"- {t.get('competition_name', '')} ({t.get('competition_type', '')}) — {t.get('match_date', '')}"
            )
    else:
        lines.append("")
        lines.append("日本俱乐部目标未出现在选中列表中（可能被预算裁剪）。")
    lines.append("")

    lines.append("### 8.4 次级联赛示例")
    sec_targets = [
        t for t in selected if "secondary_league" in t.get("team_calendar_case", "").lower()
    ]
    if sec_targets:
        lines.append("")
        lines.append(f"次级联赛俱乐部在本次 dry-run 中有 {len(sec_targets)} 个目标：")
        lines.append("")
        for t in sec_targets:
            lines.append(
                f"- {t.get('competition_name', '')} ({t.get('competition_type', '')}) — {t.get('match_date', '')}"
            )
    else:
        lines.append("")
        lines.append("次级联赛目标未出现在选中列表中（可能被预算裁剪）。")
    lines.append("")

    # Stop policy
    lines.append("## 9. Stop Policy")
    lines.append("")
    lines.append("未来真实采集器必须遵守以下策略：")
    lines.append("")
    lines.append("| 策略 | 值 |")
    lines.append("|------|----|")
    lines.append("| stop_on_403 | true |")
    lines.append("| stop_on_429 | true |")
    lines.append("| stop_on_captcha | true |")
    lines.append("| stop_on_unexpected_html | true |")
    lines.append("| stop_on_schema_shift | true |")
    lines.append("| no_retry_storm | true |")
    lines.append("| no_proxy_rotation | true |")
    lines.append("| no_anti_bot_bypass | true |")
    lines.append("| no_browser_automation | true |")
    lines.append("")

    # Safety review
    lines.append("## 10. Safety Review")
    lines.append("")
    lines.append("| 检查项 | 状态 |")
    lines.append("|--------|------|")
    lines.append("| network_fetch_performed | false ✅ |")
    lines.append("| db_write_performed | false ✅ |")
    lines.append("| raw_json_write_performed | false ✅ |")
    lines.append("| feature_parse_performed | false ✅ |")
    lines.append("| scheduler_enabled | false ✅ |")
    lines.append("| raw_write_ready_marked | false ✅ |")
    lines.append("")

    # Remaining gaps
    lines.append("## 11. Remaining Gaps")
    lines.append("")
    lines.append("- no real registry seed yet（还没有真实 registry 数据）")
    lines.append("- no live FotMob fetch（没有真实 FotMob 请求）")
    lines.append("- no DB write（没有数据库写入）")
    lines.append("- no raw JSON storage in this PR（本 PR 没有 raw JSON 存储）")
    lines.append("- no scheduler（没有调度器）")
    lines.append("- no parser/feature（没有解析器/特征工程）")
    lines.append("- no production rollout（没有生产上线）")
    lines.append("")

    # Recommended next phase
    lines.append("## 12. Recommended Next Phase")
    lines.append("")
    lines.append("推荐下一阶段：**FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-DRY-RUN-REVIEW**。")
    lines.append("")
    lines.append("注意：这一步后建议先 review dry-run，而不是直接 one-day live collection。")
    lines.append(
        "只有 dry-run review 通过后，才允许进入 "
        "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-ONE-DAY-NO-FEATURE-PARSE。"
    )
    lines.append("one-day collection 仍应低频、单线程、限预算、无 feature parse。")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="FotMob raw JSON long-run collector dry-run — generates collection plan only"
    )
    parser.add_argument(
        "--input-targets", required=True, help="Path to synthetic target fixture JSON"
    )
    parser.add_argument(
        "--output-manifest", required=True, help="Path for generated dry-run manifest JSON"
    )
    parser.add_argument(
        "--report", required=True, help="Path for generated dry-run report Markdown"
    )
    parser.add_argument(
        "--request-budget",
        type=int,
        default=50,
        help="Maximum total requests per run (default: 50)",
    )
    parser.add_argument(
        "--per-team-budget",
        type=int,
        default=10,
        help="Maximum requests per team per run (default: 10)",
    )
    parser.add_argument(
        "--per-competition-budget",
        type=int,
        default=20,
        help="Maximum requests per competition per run (default: 20)",
    )
    parser.add_argument("--run-id", required=True, help="Unique identifier for this dry-run")
    parser.add_argument(
        "--include-blocked",
        action="store_true",
        help="Include blocked targets (default: skip blocked)",
    )

    args = parser.parse_args()

    input_path = Path(args.input_targets)
    manifest_path = Path(args.output_manifest)
    report_path = Path(args.report)

    # ---- Load fixture ----
    if not input_path.exists():
        print(f"ERROR: input targets 文件不存在: {input_path}", file=sys.stderr)
        return 1

    try:
        fixture = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: 无法解析 input targets JSON: {e}", file=sys.stderr)
        return 1

    if "schema_version" not in fixture:
        print("ERROR: fixture 缺少 schema_version", file=sys.stderr)
        return 1

    targets: list[dict] = fixture.get("targets", [])
    if not targets:
        print("ERROR: fixture targets 数量为 0", file=sys.stderr)
        return 1

    input_target_count = len(targets)

    # ---- Validate ----
    validation_errors = validate_fixture(targets)
    if validation_errors:
        print("WARNING: 验证发现以下问题（继续执行）：")
        for e in validation_errors:
            print(f"  - {e}")

    # ---- Classify ----
    selectable, state_skipped = classify_targets(targets, include_blocked=args.include_blocked)
    print(f"Classified: {len(selectable)} selectable, {len(state_skipped)} skipped by state")

    # ---- Apply budget ----
    selected, budget_skipped = apply_budget(
        selectable,
        request_budget=args.request_budget,
        per_team_budget=args.per_team_budget,
        per_competition_budget=args.per_competition_budget,
    )
    print(f"Budget applied: {len(selected)} selected, {len(budget_skipped)} skipped by budget")

    all_skipped = state_skipped + budget_skipped

    # ---- Coverage ----
    coverage = analyze_coverage(selected)

    # ---- Timestamp ----
    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ---- Build manifest ----
    manifest = build_manifest(
        run_id=args.run_id,
        generated_at=generated_at,
        input_target_count=input_target_count,
        selected=selected,
        all_skipped=all_skipped,
        request_budget=args.request_budget,
        per_team_budget=args.per_team_budget,
        per_competition_budget=args.per_competition_budget,
        coverage=coverage,
    )

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Manifest written: {manifest_path}")

    # ---- Build report ----
    report_text = build_report(
        run_id=args.run_id,
        generated_at=generated_at,
        input_target_count=input_target_count,
        selected=selected,
        all_skipped=all_skipped,
        request_budget=args.request_budget,
        per_team_budget=args.per_team_budget,
        per_competition_budget=args.per_competition_budget,
        coverage=coverage,
        validation_errors=validation_errors,
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    print(f"Report written: {report_path}")

    # ---- Summary ----
    print()
    print("=== Dry-run Summary ===")
    print(f"Run ID:              {args.run_id}")
    print(f"Input targets:       {input_target_count}")
    print(f"Selected:            {len(selected)}")
    print(f"Skipped:             {len(all_skipped)}")
    print(f"Request budget:      {args.request_budget}")
    print(f"Per-team budget:     {args.per_team_budget}")
    print(f"Per-competition:     {args.per_competition_budget}")
    print("No network fetch:    True")
    print("No DB write:         True")
    print("No raw JSON write:   True")
    print("No feature parse:    True")

    return 0


if __name__ == "__main__":
    sys.exit(main())
