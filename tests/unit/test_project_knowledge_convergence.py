"""Targeted tests for the current-state knowledge map and documentation backflow."""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ops.helpers.documentation_backflow import check_documentation_backflow  # noqa: E402, I001


_MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_TOP_LEVEL_HEADING_LEVEL = 2
_README_LEGACY_MARKERS = (
    "TITAN",
    "V4.51",
    "TOTAL-WAR",
    "12061",
    "3-Model",
    "67.2%",
    "V11",
    "Recon",
)


def _readme_headings_with_ancestry(readme: str):
    """Return Markdown headings with their structural parent headings.

    This intentionally handles only the ATX headings needed by the README gate;
    fenced code blocks are ignored so command examples cannot become headings.
    """

    headings = []
    ancestry = []
    in_fenced_code = False

    for line_number, line in enumerate(readme.splitlines(), start=1):
        if line.lstrip().startswith("```"):
            in_fenced_code = not in_fenced_code
            continue
        if in_fenced_code:
            continue

        match = _MARKDOWN_HEADING_RE.match(line)
        if match is None:
            continue

        level = len(match.group(1))
        title = match.group(2).strip()
        while ancestry and ancestry[-1][0] >= level:
            ancestry.pop()
        ancestry.append((level, title))
        headings.append(
            {
                "line": line_number,
                "level": level,
                "title": title,
                "ancestry": tuple(item[1] for item in ancestry),
            }
        )

    return headings


def _contains_legacy_fence(titles) -> bool:
    return any("historical" in title.casefold() or "legacy" in title.casefold() for title in titles)


def _heading_for_line(headings, line_number):
    current = None
    for heading in headings:
        if heading["line"] > line_number:
            break
        current = heading
    return current


def _paragraph_for_line(lines, line_number):
    index = line_number - 1
    start = index
    end = index + 1
    while start > 0 and lines[start - 1].strip():
        start -= 1
    while end < len(lines) and lines[end].strip():
        end += 1
    return "\n".join(lines[start:end])


def _impact_body(
    *,
    capability: str = "no",
    milestone: str = "no",
    entrypoint: str = "no",
    blocker: str = "no",
    contract: str = "no",
    navigation: str = "no",
    vision: str = "no",
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
| Project vision / target-state changed? | {vision} |
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
        "LAST_KNOWLEDGE_AUDIT_BASE_SHA=",
        "DOCUMENTED_SHA_ROLE=LAST_KNOWLEDGE_AUDIT_SNAPSHOT_ONLY",
        "REALTIME_MAIN_AUTHORITY=Git/GitHub",
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
    assert re.search(r"LAST_KNOWLEDGE_AUDIT_BASE_SHA=[0-9a-f]{40}", current_snapshot)
    assert "CURRENT_MAIN_SHA=" not in current_snapshot
    assert "不是实时 Git branch pointer" in current_snapshot
    assert "Active Issue: **#1793" not in current_snapshot


def test_project_status_current_summary_precedes_historical_evidence():
    status = (ROOT / "docs/PROJECT_STATUS.md").read_text(encoding="utf-8")

    assert status.index("## Current State") < status.index("## Historical evidence")
    current_summary = status[: status.index("## Historical evidence")]
    for field in (
        "Last knowledge audit base",
        "Current system stage",
        "Completed canonical pipeline",
        "Predictive evidence",
        "Market / odds evidence",
        "Hard blockers",
        "Non-capabilities",
        "Next Owner decision",
    ):
        assert field in current_summary
    assert "Current main" not in current_summary
    assert "不是实时 main HEAD" in current_summary


def test_readme_current_framing_rejects_legacy_production_claims():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    current = readme.split("## Historical / Legacy Background", maxsplit=1)[0]

    assert "pre-production research / evidence-building" in current
    assert "docs/PROJECT_VISION.md" in current
    assert "Canonical Business Entrypoints" in current
    assert "MODEL_QUALITY_PROVEN=NO" in current
    assert "PROFITABILITY_PROVEN=NO" in current
    assert "PRODUCTION_READY=NO" in current
    assert "MODEL_ACTIVATED=NO" in current
    for forbidden_current_claim in (
        "Production-Ready",
        "67.2%",
        "65.52%",
        "12061",
        "3-Model",
        "3 Model",
    ):
        assert forbidden_current_claim.casefold() not in current.casefold()


def test_readme_current_model_status_matches_current_state_docs():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_current = readme.split("## Historical / Legacy Background", maxsplit=1)[0]
    status = (ROOT / "docs/PROJECT_STATUS.md").read_text(encoding="utf-8")
    status_current = status[: status.index("## Historical evidence")]

    for fact in (
        "canonical-prematch-vnext-a74c9a9ad63dd48a86f15d41",
        "xgboost_multiclass_1x2",
        "canonical_prematch/vnext-v1",
        "545",
        "343",
        "436",
        "109",
        "CONSUMED_FOR_OFFLINE_EVALUATION",
        "MODEL_OFFLINE_QUALITY_STATUS=PROMISING",
        "VALUE_MVP-1",
        "MARKET_BETTER_THAN_MODEL",
    ):
        assert fact in readme_current
        assert fact in status_current

    assert "13-feature" in readme_current
    assert "canonical candidate" in readme_current


def test_readme_legacy_markers_remain_structurally_fenced():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_lines = readme.splitlines()
    headings = _readme_headings_with_ancestry(readme)

    historical_background = next(
        heading for heading in headings if heading["title"] == "Historical / Legacy Background"
    )
    canonical_entrypoints = next(
        heading for heading in headings if heading["title"] == "Canonical Business Entrypoints"
    )

    assert historical_background["level"] == _TOP_LEVEL_HEADING_LEVEL
    assert canonical_entrypoints["level"] == _TOP_LEVEL_HEADING_LEVEL
    assert not _contains_legacy_fence(canonical_entrypoints["ancestry"])

    # A same-level generic heading would terminate the historical parent and
    # allow the old TITAN body to be retrieved as current material.
    for heading in headings:
        if (
            historical_background["line"] < heading["line"] < canonical_entrypoints["line"]
            and heading["level"] == historical_background["level"]
        ):
            assert _contains_legacy_fence((heading["title"],)), heading

    current_heading_titles = {
        "Current State",
        "Canonical Business Entrypoints",
        "Current Development Verification",
        "Current Repository Gates",
    }
    for heading in headings:
        if heading["title"] in current_heading_titles:
            assert heading["level"] == _TOP_LEVEL_HEADING_LEVEL

    for marker in _README_LEGACY_MARKERS:
        for line_number, line in enumerate(readme_lines, start=1):
            if marker.casefold() not in line.casefold():
                continue
            heading = _heading_for_line(headings, line_number)
            assert heading is not None
            paragraph = _paragraph_for_line(readme_lines, line_number)
            assert _contains_legacy_fence(heading["ancestry"]) or any(
                token in paragraph.casefold() for token in ("historical", "legacy")
            ), f"{marker!r} escaped historical/legacy fencing at README:{line_number}"


def test_agent_specific_skills_are_legacy_pointers():
    skill_paths = (
        ".claude/skills/api-testing/SKILL.md",
        ".claude/skills/data-collection/SKILL.md",
        ".claude/skills/data-engineering/SKILL.md",
        ".claude/skills/data-engineering/README.md",
        ".claude/skills/database-operations/SKILL.md",
        ".claude/skills/deployment-management/SKILL.md",
        ".claude/skills/deployment-operations/SKILL.md",
        ".claude/skills/docker-devops/SKILL.md",
        ".claude/skills/football-prediction/SKILL.md",
        ".claude/skills/feature-engineering/SKILL.md",
        ".claude/skills/machine-learning-engineering/SKILL.md",
        ".claude/skills/machine-learning-engineering/README.md",
        ".claude/skills/fastapi-development/SKILL.md",
        ".claude/skills/fastapi-development/README.md",
        ".claude/skills/performance-monitoring/SKILL.md",
        ".claude/skills/report-generation/SKILL.md",
        ".claude/skills/v26-harvest/SKILL.md",
    )
    stale_claims = (
        "58.69%",
        "67.2%",
        "65.52%",
        "65%+",
        "12061",
        "<100ms",
        "3-model",
        "production baseline",
        "predict_match_v2",
        "InferenceServiceV2",
        "xgboost_v2",
        "/api/predict",
        "当前端点",
    )

    for relative_path in skill_paths:
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        assert "Lifecycle: `LEGACY_BACKGROUND`" in text
        assert "## Historical / Legacy Reference" in text
        current_pointer = text.split("## Historical / Legacy Reference", maxsplit=1)[0]
        for stale_claim in stale_claims:
            assert stale_claim.casefold() not in current_pointer.casefold(), relative_path


def test_agents_keeps_agent_specific_files_out_of_project_authority():
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert ".claude/" in agents
    assert "GEMINI.md" in agents
    assert "agent skill/config" in agents
    assert "不能成为平行 project workflow authority" in agents


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


def test_contract_change_without_current_state_update_fails():
    body = _impact_body(
        contract="yes",
        reason="This local gate fix does not change the documented contract boundary or semantics.",
    )
    errors = check_documentation_backflow(body, {"scripts/ops/ai_workflow_gate.py"})

    assert any("contract changed=yes cannot" in error for error in errors)


def test_api_capability_change_without_current_state_update_fails():
    body = _impact_body(
        capability="yes",
        reason="This API change is described as a capability change but omits its current-state index update.",
    )
    errors = check_documentation_backflow(body, {"src/api/model_management.py"})

    assert any("capability changed=yes cannot" in error for error in errors)


def test_feature_engine_capability_change_without_current_state_update_fails():
    body = _impact_body(
        capability="yes",
        reason="This feature-engine change is described as a capability change but omits its current-state update.",
    )
    errors = check_documentation_backflow(
        body,
        {"src/feature_engine/extractors/GoldenFeatureExtractor.js"},
    )

    assert any("capability changed=yes cannot" in error for error in errors)


def test_api_bugfix_without_capability_change_accepts_specific_reason():
    body = _impact_body(
        reason="This API bugfix changes validation only and does not change capability, status, or contract.",
    )

    assert check_documentation_backflow(body, {"src/api/health.py"}) == []


def test_bugfix_without_capability_change_accepts_specific_reason():
    body = _impact_body(
        reason="This fixes validation of an existing path and changes no capability, status, or contract."
    )

    assert check_documentation_backflow(body, {"src/ml/training/existing.py"}) == []


def test_hollow_no_update_reasons_are_rejected():
    for reason in ("n/a", "none", "not needed", "no update needed", "无需", "无需更新"):
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


def test_project_vision_exists_and_is_not_workflow_authority():
    vision = ROOT / "docs/PROJECT_VISION.md"
    text = vision.read_text(encoding="utf-8")

    assert vision.is_file()
    assert "lifecycle: permanent" in text
    assert "North Star" in text
    assert "它不替代" in text
    assert "`AGENTS.md`" in text
    assert "不负责仓库的操作规则" in text


def test_project_vision_is_in_startup_order_and_project_map_role_is_clear():
    project_map = (ROOT / "docs/PROJECT_MAP.md").read_text(encoding="utf-8")
    workflow = (ROOT / "docs/AGENT_WORKFLOW.md").read_text(encoding="utf-8")
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    order_start = project_map.index("## 当前可信阅读顺序")
    order_end = project_map.index("## 技术栈摘要")
    reading_order = project_map[order_start:order_end]

    assert reading_order.index("`docs/AGENT_WORKFLOW.md`") < reading_order.index(
        "`docs/PROJECT_VISION.md`"
    )
    assert reading_order.index("`docs/PROJECT_VISION.md`") < reading_order.index("本文档")
    assert "PROJECT_VISION.md" in workflow
    assert "VISION_ALIGNMENT_REVIEWED=YES" in agents


def test_vision_change_requires_vision_source_update():
    body = _impact_body(vision="yes", source_updated="yes", updated_docs="docs/PROJECT_MAP.md")
    errors = check_documentation_backflow(body, {"docs/PROJECT_MAP.md"})

    assert any("vision changed=yes requires docs/PROJECT_VISION.md" in error for error in errors)


def test_vision_change_cannot_use_no_update_reason():
    body = _impact_body(
        vision="yes",
        reason="The target-state change is intentional but this PR omits the vision source document.",
    )
    errors = check_documentation_backflow(body, {"docs/PROJECT_MAP.md"})

    assert any("vision changed=yes cannot" in error for error in errors)


def test_vision_source_update_passes_when_declared():
    body = _impact_body(
        vision="yes",
        source_updated="yes",
        updated_docs="docs/PROJECT_VISION.md",
    )

    assert check_documentation_backflow(body, {"docs/PROJECT_VISION.md"}) == []
