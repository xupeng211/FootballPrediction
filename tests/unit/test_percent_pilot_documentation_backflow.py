"""Percent pilot 的精确文档回流映射与越权拒绝测试。

lifecycle: permanent
"""

import pytest

from scripts.ops.ai_workflow_gate import check_mixed_governance_business
from scripts.ops.helpers.documentation_backflow import check_documentation_backflow
from scripts.ops.helpers.pr_authorization_matrix import validate_authorization
from tests.unit.test_project_knowledge_convergence import (
    _CANONICAL_DOC,
    _STAGE_D_DOC,
    _canonical_contract_body,
)

_PERCENT_PILOT_PATHS = {
    "docs/agentic/missions/FP_QUALITY_MARKDOWN_PERCENT_20261105.json",
    "docs/data/CANONICAL_PREMATCH_FEATURE_FRAME_CONTRACT.md",
    "src/infrastructure/golden_dataset/CanonicalPrematchFeatureQualityDiagnostics.js",
    "tests/unit/canonical_prematch_feature_quality_diagnostics.test.js",
}


def test_percent_pilot_exact_mapping_uses_real_contract():
    body = _canonical_contract_body(entrypoint="no", capability="no", milestone="no", blocker="no")
    assert check_documentation_backflow(body, _PERCENT_PILOT_PATHS) == []
    assert check_mixed_governance_business(_PERCENT_PILOT_PATHS) == []
    assert validate_authorization("source-code", _PERCENT_PILOT_PATHS, pr_body=body).errors == ()
    assert check_documentation_backflow(body, _PERCENT_PILOT_PATHS - {_CANONICAL_DOC})
    assert check_documentation_backflow(
        _canonical_contract_body(
            contract="no", entrypoint="no", capability="no", milestone="no", blocker="no"
        ),
        _PERCENT_PILOT_PATHS,
    )


@pytest.mark.parametrize(
    ("extra", "expected_error"),
    [
        (
            "docs/agentic/missions/UNAPPROVED.json",
            "contract mapping mixes Canonical prematch with other domains or workflow paths:",
        ),
        (
            "scripts/ops/canonical_prematch_feature_frame.js",
            "contract mapping mixes Canonical prematch with other domains or workflow paths:",
        ),
        (
            "scripts/ops/helpers/documentation_backflow.py",
            "contract mapping mixes Canonical prematch with other domains or workflow paths:",
        ),
        (
            "AGENTS.md",
            "contract mapping mixes Canonical prematch with other domains or workflow paths:",
        ),
        ("src/other_domain/model.py", "contract paths have no approved domain mapping:"),
        (
            _STAGE_D_DOC,
            "contract mapping mixes Canonical prematch with other domains or workflow paths:",
        ),
    ],
)
def test_percent_pilot_does_not_expand_domain_or_mission_authority(extra, expected_error):
    body = _canonical_contract_body(entrypoint="no", capability="no", milestone="no", blocker="no")
    assert check_documentation_backflow(body, _PERCENT_PILOT_PATHS) == []
    errors = check_documentation_backflow(body, _PERCENT_PILOT_PATHS | {extra})
    assert any(error.startswith(expected_error) and extra in error for error in errors)
