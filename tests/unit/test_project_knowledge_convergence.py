"""Targeted tests for the current-state knowledge map and documentation backflow."""

from __future__ import annotations

from pathlib import Path
import re

from scripts.ops.helpers.documentation_backflow import check_documentation_backflow

ROOT = Path(__file__).resolve().parents[2]


def _impact_body(
    *,
    capability: str = "no",
    milestone: str = "no",
    entrypoint: str = "no",
    blocker: str = "no",
    contract: str = "no",
    navigation: str = "no",
    source_updated: str = "no",
    updated_docs: str = "none",
    reason: str = "The patch fixes a local behavior without changing the capability or current state.",
) -> str:
    return f"""## Documentation Impact

| Item | Value |
|---|---|
| Capability changed? | {capability} |
| Milestone changed? | {milestone} |
| Canonical entrypoint changed? | {entrypoint} |
| Current blocker changed? | {blocker} |
| Data/model/authorization contract changed? | {contract} |
| Repository structure/authority navigation changed? | {navigation} |
| Source-of-truth docs updated | {source_updated} |
| Updated authoritative docs | {updated_docs} |
| If not updated, explicit reason | {reason} |
"""


def test_capability_index_exists_and_agents_points_to_it():
    capability_index = ROOT / "docs/CAPABILITY_INDEX.md"
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert capability_index.is_file()
    assert "docs/CAPABILITY_INDEX.md" in agents
    assert "EXISTING_CAPABILITIES_REVIEWED=YES" in agents


def test_project_map_reading_order_uses_current_authorities():
    project_map = (ROOT / "docs/PROJECT_MAP.md").read_text(encoding="utf-8")
    order_start = project_map.index("## 当前可信阅读顺序")
    order_end = project_map.index("## 技术栈摘要")
    reading_order = project_map[order_start:order_end]

    labels = (
        "`AGENTS.md`",
        'README "Canonical Business Entrypoints"',
        "`docs/AGENT_WORKFLOW.md`",
        "本文档",
        "`docs/CAPABILITY_INDEX.md`",
        "`docs/ACTIVE_MILESTONE.md`",
        "`docs/PROJECT_STATUS.md`",
        "领域 current-state docs",
    )
    positions = [reading_order.index(label) for label in labels]
    assert positions == sorted(positions)
    assert "COMMAND_CENTER.md" not in reading_order


def test_active_milestone_snapshot_has_current_state_shape():
    milestone = (ROOT / "docs/ACTIVE_MILESTONE.md").read_text(encoding="utf-8")
    current_snapshot = milestone.split("## Historical evidence", maxsplit=1)[0]

    for field in (
        "CURRENT_MAIN_SHA=",
        "CURRENT_BUSINESS_STAGE=",
        "RECENTLY_COMPLETED=",
        "CURRENT_MODEL_ASSET=",
        "CURRENT_DATA_ASSETS=",
        "CURRENT_MARKET_ASSETS=",
        "CURRENT_HARD_BLOCKERS=",
        "NEXT_OWNER_DECISION=",
        "DO_NOT_START_WITHOUT_AUTHORIZATION=",
    ):
        assert field in current_snapshot
    assert re.search(r"CURRENT_MAIN_SHA=[0-9a-f]{40}", current_snapshot)
    assert "Active Issue: **#1793" not in current_snapshot


def test_project_status_current_summary_precedes_historical_evidence():
    status = (ROOT / "docs/PROJECT_STATUS.md").read_text(encoding="utf-8")

    assert status.index("## Current State") < status.index("## Historical evidence")
    for field in (
        "Current main",
        "Current system stage",
        "Completed canonical pipeline",
        "Predictive evidence",
        "Market / odds evidence",
        "Hard blockers",
        "Non-capabilities",
        "Next Owner decision",
    ):
        assert field in status[: status.index("## Historical evidence")]


def test_capability_change_without_current_state_update_fails():
    body = _impact_body(capability="yes")
    errors = check_documentation_backflow(body, {"src/ml/training/new_capability.py"})

    assert any("capability changed=yes cannot" in error for error in errors)


def test_capability_change_with_index_update_passes():
    body = _impact_body(
        capability="yes",
        source_updated="yes",
        updated_docs="docs/CAPABILITY_INDEX.md",
        reason="The capability row and status evidence are updated in the index.",
    )
    changed = {"src/ml/training/new_capability.py", "docs/CAPABILITY_INDEX.md"}

    assert check_documentation_backflow(body, changed) == []


def test_bugfix_without_capability_change_accepts_specific_reason():
    body = _impact_body(
        reason="This fixes validation of an existing path and changes no capability, status, or contract."
    )

    assert check_documentation_backflow(body, {"src/ml/training/existing.py"}) == []


def test_hollow_no_update_reasons_are_rejected():
    for reason in ("n/a", "none", "not needed", "no update needed", "无需"):
        body = _impact_body(reason=reason)
        errors = check_documentation_backflow(body, {"src/ml/training/existing.py"})
        assert any("specific, non-hollow" in error for error in errors)


def test_entrypoint_change_requires_entrypoint_and_capability_docs():
    body = _impact_body(
        entrypoint="yes",
        source_updated="yes",
        updated_docs="README.md",
    )
    errors = check_documentation_backflow(body, {"README.md"})

    assert any(
        "entrypoint changed=yes requires docs/CAPABILITY_INDEX.md" in error for error in errors
    )


def test_project_map_change_requires_navigation_declaration():
    body = _impact_body(
        navigation="yes",
        source_updated="yes",
        updated_docs="docs/PROJECT_MAP.md",
    )

    assert check_documentation_backflow(body, {"docs/PROJECT_MAP.md"}) == []


def test_fotmob_current_state_is_the_blocker_mapping_when_changed():
    body = _impact_body(
        blocker="yes",
        source_updated="yes",
        updated_docs="docs/PROJECT_STATUS.md, docs/data/FOTMOB_CURRENT_STATE.md",
    )
    changed = {
        "docs/data/FOTMOB_CURRENT_STATE.md",
        "docs/PROJECT_STATUS.md",
    }

    assert check_documentation_backflow(body, changed) == []
