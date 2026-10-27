"""Targeted tests for the current-state knowledge map and documentation backflow."""

from __future__ import annotations

from pathlib import Path
import re
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ops.helpers.documentation_backflow import check_documentation_backflow  # noqa: E402, I001
from scripts.devops.review_policy import (  # noqa: E402
    CandidateBinding,
    evaluate_review_policy,
    required_backends,
)
from scripts.ops.ai_workflow_gate import (  # noqa: E402
    check_mixed_governance_business,
    validate as validate_workflow_gate,
)
from scripts.ops.helpers.agent_workflow_contract import (  # noqa: E402
    MissionScope,
    validate_mission_scope,
    validate_pr_metadata,
)
from scripts.ops.helpers.pr_authorization_matrix import (  # noqa: E402
    narrow_blocking_errors,
    parse_task_type,
    validate_authorization,
)
from scripts.ops.helpers.git_change_helpers import Change  # noqa: E402
from scripts.ops.helpers.strict_review_evidence import parse_workflow_class  # noqa: E402


_MARKDOWN_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_TOP_LEVEL_HEADING_LEVEL = 2


def _fixture_items(value):
    return tuple(value.split("|"))


_README_LEGACY_MARKERS = _fixture_items("TITAN|V4.51|TOTAL-WAR|12061|3-Model|67.2%|V11|Recon")


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
    labels = _fixture_items(
        '`AGENTS.md`|README "Canonical Business Entrypoints"|`docs/AGENT_WORKFLOW.md`|本文档'
        "|`docs/CAPABILITY_INDEX.md`|`docs/ACTIVE_MILESTONE.md`|`docs/PROJECT_STATUS.md`|"
        "领域 current-state docs"
    )
    positions = [reading_order.index(label) for label in labels]
    assert positions == sorted(positions)
    assert "COMMAND_CENTER.md" not in reading_order


def test_active_milestone_snapshot_has_current_state_shape():
    milestone = (ROOT / "docs/ACTIVE_MILESTONE.md").read_text(encoding="utf-8")
    current_snapshot = milestone.split("## Historical evidence", maxsplit=1)[0]
    for field in _fixture_items(
        "LAST_KNOWLEDGE_AUDIT_BASE_SHA=|DOCUMENTED_SHA_ROLE=LAST_KNOWLEDGE_AUDIT_SNAPSHOT"
        "_ONLY|REALTIME_MAIN_AUTHORITY=Git/GitHub|CURRENT_BUSINESS_STAGE=|RECENTLY_COMPLE"
        "TED=|CURRENT_MODEL_ASSET=|CURRENT_DATA_ASSETS=|CURRENT_MARKET_ASSETS=|CURRENT_HA"
        "RD_BLOCKERS=|NEXT_OWNER_DECISION=|DO_NOT_START_WITHOUT_AUTHORIZATION="
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
    for field in _fixture_items(
        "Last knowledge audit base|Current system stage|Completed canonical "
        "pipeline|Predictive evidence|Market / odds evidence|Hard "
        "blockers|Non-capabilities|Next Owner decision"
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
    for forbidden_current_claim in _fixture_items(
        "Production-Ready|67.2%|65.52%|12061|3-Model|3 Model"
    ):
        assert forbidden_current_claim.casefold() not in current.casefold()


def test_readme_current_model_status_matches_current_state_docs():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_current = readme.split("## Historical / Legacy Background", maxsplit=1)[0]
    status = (ROOT / "docs/PROJECT_STATUS.md").read_text(encoding="utf-8")
    status_current = status[: status.index("## Historical evidence")]
    for fact in _fixture_items(
        "canonical-prematch-vnext-a74c9a9ad63dd48a86f15d41|xgboost_multiclass_1x2|canonic"
        "al_prematch/vnext-v1|545|343|436|109|CONSUMED_FOR_OFFLINE_EVALUATION|MODEL_OFFLI"
        "NE_QUALITY_STATUS=PROMISING|VALUE_MVP-1|MARKET_BETTER_THAN_MODEL"
    ):
        assert fact in readme_current
        assert fact in status_current
    assert "13-feature" in readme_current
    assert "canonical candidate" in readme_current


def test_odds_and_l3_entrypoint_classification_converges_across_authorities():
    """Implemented direct npm callers must not be advertised as canonical surfaces."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    capability_index = (ROOT / "docs/CAPABILITY_INDEX.md").read_text(encoding="utf-8")
    canonical_section_start = readme.index("## Canonical Business Entrypoints")
    table_start = readme.index("| Domain | Canonical status |", canonical_section_start)
    table_end = readme.index("\n\n### Implemented but non-canonical surfaces", table_start)
    canonical_table = readme[table_start:table_end]
    non_canonical_section = readme[
        table_end : readme.index("\n### Prediction authority", table_end)
    ]
    for command in ("odds:harvest", "l3:stitch"):
        assert f"`npm run {command}`" not in canonical_table
        assert f"`npm run {command}`" in non_canonical_section
        assert "DOCUMENTED_ONLY" in non_canonical_section
        assert "not default new-work entrypoints" in non_canonical_section
        row = next(
            line
            for line in capability_index.splitlines()
            if line.startswith("|") and command in line
        )
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        assert cells[2] == "DOCUMENTED_ONLY"
        assert "IMPLEMENTED" in row
        assert "REFERENCED" in row
        assert "NOT DEFAULT NEW-WORK ENTRYPOINT" in row
        assert "README canonical table登记为 Primary canonical" not in row


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


def test_retired_agent_specific_skills_are_absent_from_current_surface():
    skill_paths = _fixture_items(
        ".claude/skills/api-testing/SKILL.md|.claude/skills/data-collection/SKILL.md|.cla"
        "ude/skills/data-engineering/SKILL.md|.claude/skills/data-engineering/README.md|."
        "claude/skills/database-operations/SKILL.md|.claude/skills/deployment-management/"
        "SKILL.md|.claude/skills/deployment-operations/SKILL.md|.claude/skills/docker-dev"
        "ops/SKILL.md|.claude/skills/football-prediction/SKILL.md|.claude/skills/feature-"
        "engineering/SKILL.md|.claude/skills/machine-learning-engineering/SKILL.md|.claud"
        "e/skills/machine-learning-engineering/README.md|.claude/skills/fastapi-developme"
        "nt/SKILL.md|.claude/skills/fastapi-development/README.md|.claude/skills/performa"
        "nce-monitoring/SKILL.md|.claude/skills/report-generation/SKILL.md|.claude/skills"
        "/v26-harvest/SKILL.md"
    )
    for relative_path in skill_paths:
        assert not (ROOT / relative_path).exists(), relative_path
    claude_readme = (ROOT / ".claude/README.md").read_text(encoding="utf-8")
    settings = (ROOT / ".claude/settings.json").read_text(encoding="utf-8")
    assert "retired" in claude_readme.casefold()
    assert '"enabled": false' in settings


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


_STAGE_D_DOC = "docs/data/STAGE_D_CONTINUOUS_OPERATIONS_CONTRACT.md"
_STAGE_D_NINE_PATHS = {
    "src/infrastructure/market_evidence/stageDOperations.js",
    "scripts/ops/stage_d_quota_adjudication.js",
    "tests/unit/market_evidence/stage_d_billing_period_rollover.test.js",
    _STAGE_D_DOC,
    "README.md",
    "docs/CAPABILITY_INDEX.md",
    "docs/ACTIVE_MILESTONE.md",
    "docs/PROJECT_STATUS.md",
    "docs/agentic/missions/FP_STAGE_D_MINIMUM_BILLING_PERIOD_ROLLOVER.json",
}
_STAGE_D_DECLARED_DOCS = (
    f"{_STAGE_D_DOC}, README.md, docs/CAPABILITY_INDEX.md, "
    "docs/ACTIVE_MILESTONE.md, docs/PROJECT_STATUS.md"
)


def _stage_d_contract_body(**overrides):
    fields = {
        "capability": "yes",
        "milestone": "yes",
        "blocker": "yes",
        "contract": "yes",
        "source_updated": "yes",
        "updated_docs": _STAGE_D_DECLARED_DOCS,
        "reason": "Existing CLI and project navigation remain unchanged; domain evidence changes do not grant live authority.",
    }
    fields.update(overrides)
    return (
        "## Scope\n\n| Field | Value |\n| --- | --- |\n"
        "| Task type | source-code |\n| Workflow class | CRITICAL |\n\n" + _impact_body(**fields)
    )


def test_stage_d_original_nine_paths_require_only_domain_contract():
    body = _stage_d_contract_body()
    assert len(_STAGE_D_NINE_PATHS) == 9  # noqa: PLR2004 -- frozen original candidate count
    assert parse_task_type(body) == "source-code"
    assert parse_workflow_class(body) == "CRITICAL"
    assert validate_pr_metadata(body) == []
    assert check_documentation_backflow(body, _STAGE_D_NINE_PATHS) == []


@pytest.mark.parametrize(
    "workflow_path",
    [
        "scripts/ops/ai_workflow_gate.py",
        "scripts/devops/pr_ready_check.py",
        "scripts/ops/helpers/strict_review_evidence.py",
    ],
)
def test_workflow_contract_still_requires_both_engineering_docs(workflow_path):
    body = _impact_body(
        contract="yes", source_updated="yes", updated_docs="AGENTS.md, docs/AGENT_WORKFLOW.md"
    )
    changed = {workflow_path, "AGENTS.md", "docs/AGENT_WORKFLOW.md"}
    assert check_documentation_backflow(body, changed) == []


def test_pure_stage_d_contract_keeps_its_domain_mapping():
    body = _impact_body(contract="yes", source_updated="yes", updated_docs=_STAGE_D_DOC)
    changed = {"scripts/ops/stage_d_quota_adjudication.js", _STAGE_D_DOC}
    assert check_documentation_backflow(body, changed) == []


@pytest.mark.parametrize(
    "domain_path",
    [
        "src/infrastructure/market_evidence/stageDOperations.js",
        "scripts/ops/stage_d_quota_adjudication.js",
        "tests/unit/market_evidence/stage_d_billing_period_rollover.test.js",
    ],
)
def test_stage_d_missing_actual_contract_fails_even_when_declared(domain_path):
    body = _impact_body(contract="yes", source_updated="yes", updated_docs=_STAGE_D_DOC)
    errors = check_documentation_backflow(body, {domain_path})
    assert any(f"requires {_STAGE_D_DOC}" in error for error in errors)


def test_stage_d_unrelated_domain_contract_is_not_a_substitute():
    other = "docs/data/UNRELATED_DOMAIN_CONTRACT.md"
    body = _stage_d_contract_body(updated_docs=_STAGE_D_DECLARED_DOCS.replace(_STAGE_D_DOC, other))
    changed = (_STAGE_D_NINE_PATHS - {_STAGE_D_DOC}) | {other}
    errors = check_documentation_backflow(body, changed)
    assert any("no approved domain mapping" in error for error in errors)


@pytest.mark.parametrize("missing_doc", ["AGENTS.md", "docs/AGENT_WORKFLOW.md"])
def test_workflow_contract_omitting_required_engineering_doc_fails(missing_doc):
    declared = "AGENTS.md, docs/AGENT_WORKFLOW.md"
    body = _impact_body(contract="yes", source_updated="yes", updated_docs=declared)
    changed = {"scripts/ops/ai_workflow_gate.py", "AGENTS.md", "docs/AGENT_WORKFLOW.md"} - {
        missing_doc
    }
    errors = check_documentation_backflow(body, changed)
    assert any(f"requires {missing_doc}" in error for error in errors)


def test_stage_d_contract_cannot_declare_source_of_truth_not_updated():
    errors = check_documentation_backflow(
        _stage_d_contract_body(source_updated="no"), _STAGE_D_NINE_PATHS
    )
    assert any("contract changed=yes cannot" in error for error in errors)


@pytest.mark.parametrize(
    "claimed_doc", ["docs/data/UNRELATED_DOMAIN_CONTRACT.md", _STAGE_D_DOC + ".bak", "none"]
)
def test_stage_d_missing_exact_declared_contract_fails(claimed_doc):
    body = _stage_d_contract_body(
        updated_docs=_STAGE_D_DECLARED_DOCS.replace(_STAGE_D_DOC, claimed_doc)
    )
    errors = check_documentation_backflow(body, _STAGE_D_NINE_PATHS)
    assert any(f"requires {_STAGE_D_DOC}" in error for error in errors)


@pytest.mark.parametrize("contract", ["yes", "no"])
def test_stage_d_mapping_does_not_weaken_mixed_governance_business_ban(contract):
    changed = _STAGE_D_NINE_PATHS | {"AGENTS.md", "docs/AGENT_WORKFLOW.md"}
    body = _stage_d_contract_body(
        contract=contract,
        updated_docs=_STAGE_D_DECLARED_DOCS + ", AGENTS.md, docs/AGENT_WORKFLOW.md",
    )
    assert any("mixes Stage D" in error for error in check_documentation_backflow(body, changed))
    assert any(
        "Mixed governance + business code" in error
        for error in check_mixed_governance_business(changed)
    )


@pytest.mark.parametrize(
    ("extra_path", "expected_error"),
    [
        ("src/other_domain/model.py", "no approved domain mapping"),
        ("config/other_domain.json", "mixes Stage D"),
        ("scripts/ops/helpers/documentation_backflow.py", "mixes Stage D"),
        ("scripts/ops/unknown_provider_domain.js", "no approved domain mapping"),
    ],
)
def test_stage_d_document_cannot_cover_unmapped_or_workflow_changes(extra_path, expected_error):
    errors = check_documentation_backflow(
        _stage_d_contract_body(), _STAGE_D_NINE_PATHS | {extra_path}
    )
    assert any(expected_error in error for error in errors)


@pytest.mark.parametrize(
    "unknown_path", ["src/other_domain/model.py", "docs/data/OTHER_CONTRACT.md"]
)
def test_unknown_contract_domain_fails_closed(unknown_path):
    body = _impact_body(
        contract="yes", source_updated="yes", updated_docs="AGENTS.md, docs/AGENT_WORKFLOW.md"
    )
    errors = check_documentation_backflow(body, {unknown_path})
    assert any("no approved domain" in error for error in errors)


@pytest.mark.parametrize(
    "unknown_path",
    [
        "src/other_domain/model.py",
        "docs/data/OTHER_CONTRACT.md",
        "database/migrations/001.sql",
        "scripts/ops/unknown_provider_domain.js",
        "scripts/data/unknown_domain.py",
        "scripts/model_training/unknown_domain.py",
    ],
)
def test_unknown_domain_contract_still_fails_when_engineering_docs_are_present(unknown_path):
    body = _impact_body(
        contract="yes",
        source_updated="yes",
        updated_docs="AGENTS.md, docs/AGENT_WORKFLOW.md, docs/data/OTHER_CONTRACT.md",
    )
    changed = {"AGENTS.md", "docs/AGENT_WORKFLOW.md", unknown_path}
    assert any(
        "no approved domain" in error for error in check_documentation_backflow(body, changed)
    )


@pytest.mark.parametrize("declaration", ["no", "maybe", "", "missing_row", "missing_section"])
def test_unknown_script_workflow_mixture_cannot_hide_behind_impact_declarations(declaration):
    body = _impact_body(
        contract=declaration, source_updated="yes", updated_docs="AGENTS.md, docs/AGENT_WORKFLOW.md"
    )
    if declaration == "missing_row":
        body = body.replace("| Data/model/authorization contract changed? | missing_row |\n", "")
    elif declaration == "missing_section":
        body = ""
    changed = {"scripts/ops/unknown_provider_domain.js", "AGENTS.md", "docs/AGENT_WORKFLOW.md"}
    assert any(
        "no approved domain mapping" in error
        for error in check_documentation_backflow(body, changed)
    )
    # Exercise the existing formal gate caller, including its real changed-path input.
    errors = validate_workflow_gate(body, changes=[Change("M", path) for path in sorted(changed)])
    assert any("no approved domain mapping" in error for error in errors)


@pytest.mark.parametrize(
    "path", ["scripts/ops/ordinary_bugfix.js", "scripts/data/ordinary_bugfix.py"]
)
def test_unrelated_script_bugfix_without_contract_context_is_unchanged(path):
    assert check_documentation_backflow("", {path}) == []


def test_stage_d_exact_mapping_does_not_authorize_excluded_scope_paths():
    scope = MissionScope.from_mapping(
        {
            "schema_version": "agentic-mission-scope/v1",
            "mission_id": "FP_STAGE_D_MINIMUM_BILLING_PERIOD_ROLLOVER",
            "task_type": "source-code",
            "workflow_class": "CRITICAL",
            "authorized_paths": sorted(_STAGE_D_NINE_PATHS),
            "authorized_prefixes": [],
            "excluded_paths": ["AGENTS.md", "docs/AGENT_WORKFLOW.md"],
            "excluded_prefixes": [],
            "excluded_tokens": [],
            "protected_invariants": ["Gate 3 not authorized; immutable historical evidence."],
            "forbidden_side_effects": ["No production writes or provider requests."],
        }
    )
    assert validate_mission_scope(_STAGE_D_NINE_PATHS, scope) == []
    assert any(
        "explicitly excluded" in error
        for error in validate_mission_scope(_STAGE_D_NINE_PATHS | {"AGENTS.md"}, scope)
    )


def test_stage_d_domain_mapping_does_not_lower_critical_dual_review():
    assert required_backends("CRITICAL") == ("codex-cli", "claude-code-deepseek")
    candidate = CandidateBinding("a" * 40, "b" * 40, "c" * 64, "stage-d", "d" * 64)
    result = evaluate_review_policy("CRITICAL", candidate, [])
    assert result.status != "SATISFIED"
    assert result.required_backends == ("codex-cli", "claude-code-deepseek")


@pytest.mark.parametrize("value", ["yes: explained", "maybe", ""])
def test_stage_d_contract_mapping_preserves_strict_yes_no(value):
    errors = check_documentation_backflow(
        _stage_d_contract_body(contract=value), _STAGE_D_NINE_PATHS
    )
    assert errors


def test_stage_d_bugfix_still_requires_substantive_no_change_reason():
    body = _stage_d_contract_body(contract="no", reason="none")
    errors = check_documentation_backflow(body, _STAGE_D_NINE_PATHS)
    assert any("specific reason" in error for error in errors)


_CANONICAL_DOC = "docs/data/CANONICAL_PREMATCH_FEATURE_FRAME_CONTRACT.md"
_CANONICAL_PATHS = {
    _CANONICAL_DOC,
    "src/infrastructure/golden_dataset/CanonicalPrematchFeatureQualityDiagnostics.js",
    "scripts/ops/canonical_prematch_feature_frame.js",
    "tests/unit/canonical_prematch_feature_frame.test.js",
    "tests/unit/canonical_prematch_feature_quality_diagnostics.test.js",
    "README.md",
    "docs/CAPABILITY_INDEX.md",
    "docs/ACTIVE_MILESTONE.md",
    "docs/PROJECT_STATUS.md",
    "docs/agentic/missions/FP_CANONICAL_PREMATCH_FEATURE_QUALITY_DIAGNOSTICS_V1.json",
    "docs/agentic/missions/FP_FEATURE_QUALITY_CRITICAL_SCOPE_BRIDGE.json",
    "docs/agentic/missions/FP_FEATURE_QUALITY_REPACKAGE_BUSINESS.json",
}
_CANONICAL_DOCS = _STAGE_D_DECLARED_DOCS.replace(_STAGE_D_DOC, _CANONICAL_DOC)


def _canonical_contract_body(**overrides):
    return _stage_d_contract_body(
        **({"entrypoint": "yes", "updated_docs": _CANONICAL_DOCS} | overrides)
    )


def test_canonical_exact_business_paths_use_actual_domain_contract():
    body = _canonical_contract_body()
    assert check_documentation_backflow(body, _CANONICAL_PATHS) == []
    for status in ("A", "M"):
        updates = [Change(status, _CANONICAL_DOC)]
        assert check_documentation_backflow(body, _CANONICAL_PATHS, changes=updates) == []
    assert check_mixed_governance_business(_CANONICAL_PATHS) == []
    assert validate_authorization("source-code", _CANONICAL_PATHS, pr_body=body).errors == ()
    matrix = validate_authorization(
        "source-code",
        _CANONICAL_PATHS | {"scripts/ops/helpers/documentation_backflow.py"},
        pr_body=body,
    )
    assert any("source-code" in e for e in narrow_blocking_errors(matrix))
    assert check_documentation_backflow(
        _stage_d_contract_body(), _CANONICAL_PATHS | _STAGE_D_NINE_PATHS
    )


def _canonical_rejections():
    for path in sorted(
        path for path in _CANONICAL_PATHS if path.startswith(("src/", "scripts/", "tests/"))
    ):
        for declaration in ("yes", "no"):
            yield {path}, {"contract": declaration}, "actual update of " + _CANONICAL_DOC
    for declaration in ("no", "maybe", "", "missing"):
        yield _CANONICAL_PATHS, {"contract": declaration}, "require contract changed=yes"
    for substitute in ("docs/data/OTHER_CONTRACT.md", _STAGE_D_DOC, _CANONICAL_DOC + ".bak"):
        yield (_CANONICAL_PATHS - {_CANONICAL_DOC}) | {substitute}, {}, ""
    for extra in (
        "src/other_domain/model.py",
        "scripts/ops/unknown_domain.js",
        "docs/data/OTHER_CONTRACT.md",
        "config/other_domain.json",
        "tests/unit/unrelated.test.js",
        "docs/agentic/missions/UNAPPROVED.json",
        "scripts/ops/helpers/documentation_backflow.py",
        "AGENTS.md",
        "docs/AGENT_WORKFLOW.md",
        _STAGE_D_DOC,
        "src/infrastructure/market_evidence/stageDOperations.js",
    ):
        for declaration in ("yes", "no"):
            yield _CANONICAL_PATHS | {extra}, {"contract": declaration}, ""
    yield _CANONICAL_PATHS, {"source_updated": "no"}, "contract changed=yes cannot"
    yield (
        _CANONICAL_PATHS,
        {"updated_docs": "docs/CAPABILITY_INDEX.md"},
        "requires " + _CANONICAL_DOC,
    )


@pytest.mark.parametrize(("paths", "overrides", "expected"), list(_canonical_rejections()))
def test_canonical_domain_rejects_invalid_evidence(paths, overrides, expected):
    body = _canonical_contract_body(**overrides)
    if overrides.get("contract") == "missing":
        body = body.replace("| Data/model/authorization contract changed? | missing |\n", "")
    errors = check_documentation_backflow(body, paths)
    assert errors
    assert any(expected in error for error in errors)


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
        body, {"src/feature_engine/extractors/GoldenFeatureExtractor.js"}
    )
    assert any("capability changed=yes cannot" in error for error in errors)


def test_api_bugfix_without_capability_change_accepts_specific_reason():
    body = _impact_body(
        reason="This API bugfix changes validation only and does not change capability, status, or contract."
    )
    assert check_documentation_backflow(body, {"src/api/health.py"}) == []


def test_bugfix_without_capability_change_accepts_specific_reason():
    body = _impact_body(
        reason="This fixes validation of an existing path and changes no capability, status, or contract."
    )
    assert check_documentation_backflow(body, {"src/ml/training/existing.py"}) == []


def test_hollow_no_update_reasons_are_rejected():
    for reason in _fixture_items("n/a|none|not needed|no update needed|无需|无需更新"):
        body = _impact_body(reason=reason)
        errors = check_documentation_backflow(body, {"src/ml/training/existing.py"})
        assert any("specific, non-hollow" in error for error in errors)


def test_entrypoint_change_requires_entrypoint_and_capability_docs():
    body = _impact_body(entrypoint="yes", source_updated="yes", updated_docs="README.md")
    errors = check_documentation_backflow(body, {"README.md"})
    assert any(
        "entrypoint changed=yes requires docs/CAPABILITY_INDEX.md" in error for error in errors
    )


def test_project_map_change_requires_navigation_declaration():
    body = _impact_body(navigation="yes", source_updated="yes", updated_docs="docs/PROJECT_MAP.md")
    assert check_documentation_backflow(body, {"docs/PROJECT_MAP.md"}) == []


def test_fotmob_current_state_is_the_blocker_mapping_when_changed():
    body = _impact_body(
        blocker="yes",
        source_updated="yes",
        updated_docs="docs/PROJECT_STATUS.md, docs/data/FOTMOB_CURRENT_STATE.md",
    )
    changed = {"docs/data/FOTMOB_CURRENT_STATE.md", "docs/PROJECT_STATUS.md"}
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
    body = _impact_body(vision="yes", source_updated="yes", updated_docs="docs/PROJECT_VISION.md")
    assert check_documentation_backflow(body, {"docs/PROJECT_VISION.md"}) == []
