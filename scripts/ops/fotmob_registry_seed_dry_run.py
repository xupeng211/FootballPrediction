#!/usr/bin/env python3
"""FotMob registry seed dry-run helper.

lifecycle: permanent
phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DRY-RUN

Reads a registry-like seed plan fixture (metadata only), validates coverage,
generates a commented SQL preview (not executed), performs target selection
dry-run, and produces manifest + report.

No network fetch. No DB connection. No SQL execution. No raw JSON write.

Usage:
    python scripts/ops/fotmob_registry_seed_dry_run.py \
        --input-plan docs/_fixtures/fotmob_registry_seed_dry_run_plan.json \
        --sql-preview docs/_reports/FOTMOB_REGISTRY_SEED_DRY_RUN_SQL_PREVIEW.sql \
        --output-manifest docs/_manifests/fotmob_registry_seed_dry_run_manifest.json \
        --report docs/_reports/FOTMOB_REGISTRY_SEED_DRY_RUN.md \
        --request-budget 10 \
        --per-team-budget 5 \
        --per-competition-budget 4 \
        --run-id fotmob_registry_seed_dry_run_v1
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys

from _registry_seed_sql_preview import generate as generate_sql_preview

ROOT = Path(__file__).resolve().parents[2]

SELECTABLE_STATES = {"pending_raw_fetch"}
SKIP_STATES = {"blocked"}
SKIP_RAW_JSON_STATUSES = {"stored"}
SELECTABLE_RAW_JSON_STATUSES = {"missing", "stale", "failed"}

REQUIRED_COMPETITION_TYPES = [
    "league",
    "domestic_cup",
    "continental_club",
    "international_qualifier",
    "nations_league",
    "friendly",
]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_plan(plan: dict) -> list[str]:
    """Validate the registry seed plan fixture. Returns list of error messages."""
    errors: list[str] = []

    for section in [
        "teams",
        "competitions",
        "competition_editions",
        "team_competition_participation",
        "match_targets",
        "match_target_teams",
        "source_identities",
    ]:
        if section not in plan:
            errors.append(f"缺少 section: {section}")

    teams = plan.get("teams", [])
    competitions = plan.get("competitions", [])
    editions = plan.get("competition_editions", [])
    participations = plan.get("team_competition_participation", [])
    match_targets = plan.get("match_targets", [])
    match_target_teams = plan.get("match_target_teams", [])

    if len(teams) < 5:
        errors.append(f"teams 数量 < 5: got {len(teams)}")
    if len(competitions) < 8:
        errors.append(f"competitions 数量 < 8: got {len(competitions)}")
    if len(editions) < 8:
        errors.append(f"editions 数量 < 8: got {len(editions)}")
    if len(participations) < 10:
        errors.append(f"participations 数量 < 10: got {len(participations)}")
    if len(match_targets) < 12:
        errors.append(f"match_targets 数量 < 12: got {len(match_targets)}")
    if len(match_target_teams) < 24:
        errors.append(f"match_target_teams 数量 < 24: got {len(match_target_teams)}")

    team_types = {t.get("team_type") for t in teams}
    if "club" not in team_types:
        errors.append("缺少 club team")
    if "national" not in team_types:
        errors.append("缺少 national team")

    comp_types = {c.get("competition_type") for c in competitions}
    for ct in REQUIRED_COMPETITION_TYPES:
        if ct not in comp_types:
            errors.append(f"缺少 competition_type: {ct}")

    target_states = {mt.get("target_state") for mt in match_targets}
    raw_json_statuses = {mt.get("raw_json_status") for mt in match_targets}
    if "blocked" not in target_states:
        errors.append("缺少 blocked match_target")
    if "stored" not in raw_json_statuses:
        errors.append("缺少 raw_json_status=stored")
    if "failed" not in raw_json_statuses:
        errors.append("缺少 raw_json_status=failed")

    # Fixture ID uniqueness
    fixture_ids = [t.get("fixture_id") for t in teams]
    if len(fixture_ids) != len(set(fixture_ids)):
        errors.append("teams 有重复 fixture_id")

    comp_ids = [c.get("fixture_id") for c in competitions]
    if len(comp_ids) != len(set(comp_ids)):
        errors.append("competitions 有重复 fixture_id")

    mt_ids = [mt.get("fixture_id") for mt in match_targets]
    if len(mt_ids) != len(set(mt_ids)):
        errors.append("match_targets 有重复 fixture_id")

    return errors


# ---------------------------------------------------------------------------
# Target selection
# ---------------------------------------------------------------------------
def classify_targets(
    match_targets: list[dict], include_blocked: bool = False
) -> tuple[list[dict], list[dict]]:
    """Split match_targets into (selectable, skipped)."""
    selectable: list[dict] = []
    skipped: list[dict] = []

    for t in match_targets:
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

    selectable.sort(key=lambda x: (x.get("priority", 999), x.get("match_date", "9999")))
    return selectable, skipped


def apply_budget(
    selectable: list[dict],
    request_budget: int,
    per_team_budget: int,
    per_competition_budget: int,
) -> tuple[list[dict], list[dict]]:
    """Apply budgets. Returns (selected, budget_skipped)."""
    selected: list[dict] = []
    budget_skipped: list[dict] = []

    team_counts: dict[str, int] = {}
    competition_counts: dict[str, int] = {}

    for t in selectable:
        if request_budget > 0 and len(selected) >= request_budget:
            budget_skipped.append({**t, "skip_reason": "request_budget exhausted"})
            continue

        home_id = t.get("home_team_fixture_id", "")
        away_id = t.get("away_team_fixture_id", "")
        team_ids = [home_id, away_id] if home_id and away_id else []

        team_skip = False
        for tid in team_ids:
            if team_counts.get(tid, 0) >= per_team_budget:
                budget_skipped.append({**t, "skip_reason": f"per_team_budget exhausted for {tid}"})
                team_skip = True
                break
        if team_skip:
            continue

        comp_id = t.get("competition_fixture_id", "")
        if competition_counts.get(comp_id, 0) >= per_competition_budget:
            budget_skipped.append(
                {**t, "skip_reason": f"per_competition_budget exhausted for {comp_id}"}
            )
            continue

        selected.append(t)
        for tid in team_ids:
            team_counts[tid] = team_counts.get(tid, 0) + 1
        competition_counts[comp_id] = competition_counts.get(comp_id, 0) + 1

    return selected, budget_skipped


# ---------------------------------------------------------------------------
# Team full-calendar dry-run
# ---------------------------------------------------------------------------
def team_calendar(
    team_id: str,
    match_targets: list[dict],
    competitions: list[dict],
    match_target_teams: list[dict],
) -> list[dict]:
    """Find all match targets for a given team (by fixture_id)."""
    comp_map = {c["fixture_id"]: c for c in competitions}

    relevant_mtt = [mtt for mtt in match_target_teams if mtt.get("team_fixture_id") == team_id]
    relevant_mt_ids = {mtt["match_target_fixture_id"] for mtt in relevant_mtt}

    results = []
    for mt in match_targets:
        if mt["fixture_id"] in relevant_mt_ids:
            comp = comp_map.get(mt.get("competition_fixture_id", ""), {})
            results.append(
                {
                    "source_match_id": mt["source_match_id"],
                    "competition_name": comp.get("competition_name", ""),
                    "competition_type": comp.get("competition_type", ""),
                    "target_state": mt.get("target_state", ""),
                    "raw_json_status": mt.get("raw_json_status", ""),
                    "priority": mt.get("priority"),
                    "match_date": mt.get("match_date", ""),
                }
            )

    results.sort(key=lambda x: (x.get("priority", 999), x.get("match_date", "9999")))
    return results


def build_report(
    run_id: str,
    generated_at: str,
    plan: dict,
    selected: list[dict],
    all_skipped: list[dict],
    request_budget: int,
    per_team_budget: int,
    per_competition_budget: int,
    validation_errors: list[str],
    man_cal: list[dict],
    eng_cal: list[dict],
    jpn_cal: list[dict],
    lee_cal: list[dict],
) -> str:
    """Build Chinese-language Markdown report."""
    teams = plan.get("teams", [])
    competitions = plan.get("competitions", [])
    editions = plan.get("competition_editions", [])
    participations = plan.get("team_competition_participation", [])
    match_targets = plan.get("match_targets", [])
    match_target_teams = plan.get("match_target_teams", [])
    source_identities = plan.get("source_identities", [])

    lines = [
        "<!-- markdownlint-disable MD013 -->",
        "",
        "# FotMob Registry Seed Dry-run 报告",
        "",
        "- lifecycle: current-state",
        "- phase: FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DRY-RUN",
        f"- run_id: {run_id}",
        f"- generated_at: {generated_at}",
        "",
        "## 1. 概要",
        "",
        f"- teams: {len(teams)}",
        f"- competitions: {len(competitions)}",
        f"- competition_editions: {len(editions)}",
        f"- team_competition_participation: {len(participations)}",
        f"- match_targets: {len(match_targets)}",
        f"- match_target_teams: {len(match_target_teams)}",
        f"- source_identities: {len(source_identities)}",
        "",
        "## 2. 阶段安全声明",
        "",
        "- **本 PR 没有执行 SQL**",
        "- **本 PR 没有写 DB**",
        "- **本 PR 没有访问 FotMob**",
        "- **本 PR 没有写 raw JSON**",
        "- **本 PR 没有启用 scheduler**",
        "- **本 PR 没有 feature parse**",
        "- SQL preview 文件顶部已标注 DO NOT EXECUTE",
        "- 所有 INSERT statements 已注释",
        "- 这只是 registry seed plan dry-run",
        "",
        "## 3. 生成实体统计",
        "",
        "| 表 | 数量 |",
        "|----|------|",
        f"| football_teams | {len(teams)} |",
        f"| football_competitions | {len(competitions)} |",
        f"| football_competition_editions | {len(editions)} |",
        f"| football_team_competition_participation | {len(participations)} |",
        f"| football_match_targets | {len(match_targets)} |",
        f"| football_match_target_teams | {len(match_target_teams)} |",
        f"| football_source_identities | {len(source_identities)} |",
        "",
    ]

    # Validation
    if validation_errors:
        lines.append("## 4. 验证警告")
        lines.append("")
        for e in validation_errors:
            lines.append(f"- ⚠ {e}")
    else:
        lines.append("## 4. 验证结果")
        lines.append("")
        lines.append("- 全部通过 ✓")
    lines.append("")

    # Coverage
    lines.append("## 5. 覆盖范围")
    lines.append("")
    team_types = {t.get("team_type") for t in teams}
    comp_types = {c.get("competition_type") for c in competitions}
    lines.append(f"- club teams: {'是' if 'club' in team_types else '否'}")
    lines.append(f"- national teams: {'是' if 'national' in team_types else '否'}")
    for ct in REQUIRED_COMPETITION_TYPES:
        lines.append(f"- {ct}: {'是' if ct in comp_types else '否'}")
    lines.append("")

    # Target selection
    lines.append("## 6. Target Selection Dry-run")
    lines.append("")
    lines.append(f"- 输入 match_targets: {len(match_targets)}")
    lines.append(f"- 选中: {len(selected)}")
    lines.append(f"- 跳过: {len(all_skipped)}")
    lines.append(f"- request_budget: {request_budget}")
    lines.append(f"- per_team_budget: {per_team_budget}")
    lines.append(f"- per_competition_budget: {per_competition_budget}")
    lines.append("")

    if all_skipped:
        lines.append("### 跳过明细")
        lines.append("")
        lines.append("| source_match_id | skip_reason |")
        lines.append("|-----------------|-------------|")
        for t in all_skipped:
            lines.append(f"| {t.get('source_match_id', '')} | {t.get('skip_reason', '')} |")
        lines.append("")

    # Team full-calendar
    lines.append("## 7. 球队全年赛程 Dry-run")
    lines.append("")

    lines.append("### 7.1 Manchester United")
    lines.append("")
    if man_cal:
        lines.append(f"Man United 全年赛程有 {len(man_cal)} 场比赛：")
        lines.append("")
        for t in man_cal:
            lines.append(
                f"- {t['competition_name']} ({t['competition_type']}) — {t['match_date']} [state={t['target_state']}, raw={t['raw_json_status']}]"
            )
    else:
        lines.append("（无）")
    lines.append("")

    lines.append("### 7.2 England 国家队")
    lines.append("")
    if eng_cal:
        lines.append(f"England 全年赛程有 {len(eng_cal)} 场比赛：")
        lines.append("")
        for t in eng_cal:
            lines.append(
                f"- {t['competition_name']} ({t['competition_type']}) — {t['match_date']} [state={t['target_state']}]"
            )
    else:
        lines.append("（无）")
    lines.append("")

    lines.append("### 7.3 Kashima Antlers (Japanese club)")
    lines.append("")
    if jpn_cal:
        lines.append(f"Kashima Antlers 全年赛程有 {len(jpn_cal)} 场比赛：")
        lines.append("")
        for t in jpn_cal:
            lines.append(
                f"- {t['competition_name']} ({t['competition_type']}) — {t['match_date']} [state={t['target_state']}]"
            )
    else:
        lines.append("（无）")
    lines.append("")

    lines.append("### 7.4 Leeds United (Secondary league)")
    lines.append("")
    if lee_cal:
        lines.append(f"Leeds United 全年赛程有 {len(lee_cal)} 场比赛：")
        lines.append("")
        for t in lee_cal:
            lines.append(
                f"- {t['competition_name']} ({t['competition_type']}) — {t['match_date']} [state={t['target_state']}]"
            )
    else:
        lines.append("（无）")
    lines.append("")

    # Skip logic
    lines.append("## 8. Skip Logic")
    lines.append("")
    skip_reasons = {t.get("skip_reason", "") for t in all_skipped}
    lines.append(
        f"- blocked target skipped: {'是' if any('blocked' in r for r in skip_reasons) else '否'}"
    )
    lines.append(
        f"- stored target skipped: {'是' if any('stored' in r for r in skip_reasons) else '否'}"
    )
    lines.append(
        f"- budget_exhausted present: {'是' if any('budget' in r for r in skip_reasons) else '否'}"
    )
    lines.append("")

    # Safety
    lines.append("## 9. Safety Review")
    lines.append("")
    lines.append("| 检查项 | 状态 |")
    lines.append("|--------|------|")
    lines.append("| network_fetch_performed | false ✅ |")
    lines.append("| db_write_performed | false ✅ |")
    lines.append("| sql_executed | false ✅ |")
    lines.append("| raw_json_write_performed | false ✅ |")
    lines.append("| feature_parse_performed | false ✅ |")
    lines.append("| scheduler_enabled | false ✅ |")
    lines.append("| raw_write_ready_marked | false ✅ |")
    lines.append("")

    # Gaps
    lines.append("## 10. Remaining Gaps")
    lines.append("")
    lines.append("- SQL preview 生成但未执行")
    lines.append("- 没有真实 DB seed")
    lines.append("- 没有真实 FotMob live fetch")
    lines.append("- 没有 raw JSON write")
    lines.append("- 没有 scheduler")
    lines.append("- 没有 parser/feature")
    lines.append("- 没有 production rollout")
    lines.append("")

    # Next phase
    lines.append("## 11. Recommended Next Phase")
    lines.append("")
    lines.append("推荐下一阶段：")
    lines.append("")
    lines.append("### FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DRY-RUN-REVIEW")
    lines.append("")
    lines.append("审查通过后再：")
    lines.append("")
    lines.append("### FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DEV-EXECUTION-NO-LIVE-FETCH")
    lines.append("")
    lines.append("当前阶段不允许 live fetch。")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------
def build_manifest(
    run_id: str,
    generated_at: str,
    plan: dict,
    selected: list[dict],
    all_skipped: list[dict],
    request_budget: int,
    per_team_budget: int,
    per_competition_budget: int,
    man_cal: list[dict],
    eng_cal: list[dict],
    jpn_cal: list[dict],
    lee_cal: list[dict],
) -> dict:
    """Build manifest dict."""
    teams = plan.get("teams", [])
    competitions = plan.get("competitions", [])
    editions = plan.get("competition_editions", [])
    participations = plan.get("team_competition_participation", [])
    match_targets = plan.get("match_targets", [])
    match_target_teams = plan.get("match_target_teams", [])
    source_identities = plan.get("source_identities", [])

    comp_types = {c.get("competition_type") for c in competitions}
    skip_reasons = [t.get("skip_reason", "") for t in all_skipped]

    return {
        "schema_version": "fotmob_registry_seed_dry_run_v1",
        "lifecycle": "current-state",
        "phase": "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DRY-RUN",
        "run_id": run_id,
        "generated_at": generated_at,
        "input_plan_path": "docs/_fixtures/fotmob_registry_seed_dry_run_plan.json",
        "sql_preview_path": "docs/_reports/FOTMOB_REGISTRY_SEED_DRY_RUN_SQL_PREVIEW.sql",
        "teams_count": len(teams),
        "competitions_count": len(competitions),
        "editions_count": len(editions),
        "participation_count": len(participations),
        "match_targets_count": len(match_targets),
        "match_target_teams_count": len(match_target_teams),
        "source_identities_count": len(source_identities),
        "coverage": {
            "manchester_united_calendar_present": len(man_cal) >= 4,
            "england_national_team_calendar_present": len(eng_cal) >= 3,
            "japanese_club_calendar_present": len(jpn_cal) >= 2,
            "secondary_league_calendar_present": len(lee_cal) >= 2,
            "domestic_cup_present": "domestic_cup" in comp_types,
            "continental_club_present": "continental_club" in comp_types,
            "international_qualifier_present": "international_qualifier" in comp_types,
            "nations_league_present": "nations_league" in comp_types,
            "friendly_present": "friendly" in comp_types,
        },
        "target_selection": {
            "input_target_count": len(match_targets),
            "selected_target_count": len(selected),
            "skipped_target_count": len(all_skipped),
            "skip_reasons": list(set(skip_reasons)),
            "request_budget": request_budget,
            "per_team_budget": per_team_budget,
            "per_competition_budget": per_competition_budget,
            "budget_respected": len(selected) <= request_budget,
        },
        "team_full_calendar": {
            "manchester_united_target_count": len(man_cal),
            "england_target_count": len(eng_cal),
            "japanese_club_target_count": len(jpn_cal),
            "secondary_league_target_count": len(lee_cal),
        },
        "safety": {
            "network_fetch_performed": False,
            "db_write_performed": False,
            "sql_executed": False,
            "raw_json_write_performed": False,
            "feature_parse_performed": False,
            "scheduler_enabled": False,
            "raw_write_ready_marked": False,
        },
        "recommended_next_phase": "FOTMOB-RAW-JSON-LONG-RUN-COLLECTOR-REGISTRY-SEED-DRY-RUN-REVIEW",
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="FotMob registry seed dry-run — generates SQL preview, target selection, and team calendar plan"
    )
    parser.add_argument("--input-plan", required=True)
    parser.add_argument("--sql-preview", required=True)
    parser.add_argument("--output-manifest", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--request-budget", type=int, default=10)
    parser.add_argument("--per-team-budget", type=int, default=5)
    parser.add_argument("--per-competition-budget", type=int, default=4)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--include-blocked", action="store_true")

    args = parser.parse_args()

    input_path = Path(args.input_plan)
    if not input_path.exists():
        print(f"ERROR: input plan 不存在: {input_path}", file=sys.stderr)
        return 1

    plan = json.loads(input_path.read_text(encoding="utf-8"))
    if "schema_version" not in plan:
        print("ERROR: plan 缺少 schema_version", file=sys.stderr)
        return 1

    # Validate
    validation_errors = validate_plan(plan)
    if validation_errors:
        print("WARNING: 验证警告：")
        for e in validation_errors:
            print(f"  - {e}")

    # Target selection
    match_targets = plan.get("match_targets", [])
    selectable, state_skipped = classify_targets(match_targets, args.include_blocked)
    selected, budget_skipped = apply_budget(
        selectable, args.request_budget, args.per_team_budget, args.per_competition_budget
    )
    all_skipped = state_skipped + budget_skipped

    print(
        f"Target selection: {len(selectable)} selectable, {len(selected)} selected, {len(all_skipped)} skipped"
    )

    # Team full-calendar
    teams_list = plan.get("teams", [])
    competitions_list = plan.get("competitions", [])
    mtt_list = plan.get("match_target_teams", [])

    man_cal = team_calendar("team-mun-01", match_targets, competitions_list, mtt_list)
    eng_cal = team_calendar("team-eng-01", match_targets, competitions_list, mtt_list)
    jpn_cal = team_calendar("team-kas-01", match_targets, competitions_list, mtt_list)
    lee_cal = team_calendar("team-lee-01", match_targets, competitions_list, mtt_list)

    print(
        f"Full-calendar: MU={len(man_cal)}, ENG={len(eng_cal)}, JPN={len(jpn_cal)}, LEE={len(lee_cal)}"
    )

    # Timestamp
    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    # SQL preview
    sql = generate_sql_preview(plan)
    sql_path = Path(args.sql_preview)
    sql_path.parent.mkdir(parents=True, exist_ok=True)
    sql_path.write_text(sql, encoding="utf-8")
    print(f"SQL preview written: {sql_path}")

    # Manifest
    manifest = build_manifest(
        args.run_id,
        generated_at,
        plan,
        selected,
        all_skipped,
        args.request_budget,
        args.per_team_budget,
        args.per_competition_budget,
        man_cal,
        eng_cal,
        jpn_cal,
        lee_cal,
    )
    manifest_path = Path(args.output_manifest)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Manifest written: {manifest_path}")

    # Report
    report = build_report(
        args.run_id,
        generated_at,
        plan,
        selected,
        all_skipped,
        args.request_budget,
        args.per_team_budget,
        args.per_competition_budget,
        validation_errors,
        man_cal,
        eng_cal,
        jpn_cal,
        lee_cal,
    )
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"Report written: {report_path}")

    print()
    print("=== Registry Seed Dry-run Summary ===")
    print(f"Run ID:              {args.run_id}")
    print(f"Teams:               {len(teams_list)}")
    print(f"Competitions:        {len(competitions_list)}")
    print(f"Match targets:       {len(match_targets)}")
    print(f"Selected:            {len(selected)}")
    print(f"Skipped:             {len(all_skipped)}")
    print("No network fetch:    True")
    print("No DB write:         True")
    print("SQL executed:        False")
    print("No raw JSON write:   True")

    return 0


if __name__ == "__main__":
    sys.exit(main())
