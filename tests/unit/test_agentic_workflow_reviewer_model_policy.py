"""Reviewer model pin: policy-transition and merge-readiness tests.

lifecycle: test-fixture

The canonical reviewer model is a reviewed policy constant, never a runtime
choice.  These tests cover the transition itself: evidence recorded under the
retired ``gpt-6-astra`` pin stays genuine history but can never approve the
current head, a receipt that merely *declares* the pinned model over a command
that ran another one is tamper rather than drift, no argument or environment
seam can replace the pin, and the receipt schema plus the finding-severity
contract are unaffected by the model change.

They live in their own module because the repository gatekeeper rejects Python
modules longer than 800 lines and the sibling classification matrix in
``test_agentic_workflow_receipt_classification`` already spends most of that
budget on the tamper/drift matrix.  The shared scaffolding below is deliberately
duplicated rather than moved into ``tests/helpers``: that module is outside this
mission's authorized scope and is depended on by other suites.
"""

from __future__ import annotations

from contextlib import redirect_stdout
import inspect
import io
import json
import os
from pathlib import Path

import pytest

from scripts.devops import agent_workflow, codex_independent_review
from scripts.devops.codex_review_classification import (
    CLASSIFICATION_INVALID,
    CLASSIFICATION_STALE_TOOLING,
    CLASSIFICATION_VALID_CURRENT,
    INTEGRITY_INTACT,
    INTEGRITY_TAMPERED,
    classify_receipt,
    validate_receipt,
)
from scripts.devops.codex_review_contract import REVIEW_MODEL_PINNED, build_reviewer_command
from scripts.devops.codex_review_provenance import ReviewReceiptError
from scripts.devops.codex_review_receipt import REVIEW_OUTPUT_SCHEMA
from tests.helpers.agentic_workflow_fixtures import BASE_SHA, MISSION_ID, MISSION_SCOPE_PATH
from tests.helpers.agentic_workflow_fixtures import body as _body
from tests.helpers.agentic_workflow_fixtures import make_repo as _make_repo
from tests.helpers.agentic_workflow_fixtures import write_valid_receipt as _write_valid_receipt


def _scope_file(repo: Path) -> Path:
    return repo / MISSION_SCOPE_PATH


@pytest.fixture(autouse=True)
def _synthetic_codex_provenance_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Give policy fixtures an explicit non-production Codex binary."""

    codex_root = tmp_path / "codex-home"
    codex_root.mkdir(mode=0o700)
    bin_root = tmp_path / "bin"
    bin_root.mkdir(mode=0o700)
    codex_binary = bin_root / "codex"
    codex_binary.write_text(
        '#!/bin/sh\nif [ "$1" = "--version" ]; then echo "codex-cli 0.153.4"; exit 0; fi\nexit 0\n',
        encoding="utf-8",
    )
    codex_binary.chmod(0o700)
    monkeypatch.setenv("CODEX_HOME", str(codex_root))
    monkeypatch.setenv("PATH", f"{bin_root}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setattr(codex_independent_review, "canonical_codex_binary", lambda: codex_binary)


def _pinned_command() -> list[str]:
    return build_reviewer_command(
        codex_binary="codex",
        base_sha=BASE_SHA,
        output_schema=REVIEW_OUTPUT_SCHEMA,
        final_message_path=Path("/tmp/final.json"),
    )


# The model token the retired reviewer policy pinned.  Every other byte of the
# invocation is unchanged, so a fixture transformed with it is byte-for-byte the
# argv that policy actually executed, and its model_provenance is derived from
# that argv exactly as it was when the receipt was first written.
RETIRED_REVIEW_MODEL_PINNED = "gpt-6-astra"


def _retired_policy_command(command: list[str]) -> list[str]:
    """Rebuild the reviewer argv of the retired Astra-pinned policy."""

    mutated = list(command)
    mutated[mutated.index("-m") + 1] = RETIRED_REVIEW_MODEL_PINNED
    return mutated


def _classification(
    receipt: Path,
    repo: Path,
    *,
    current_head: str | None,
    expected_base: str | None = None,
    historical_audit: bool = False,
):
    return classify_receipt(
        receipt,
        repo_root=repo,
        current_head=current_head,
        expected_base=expected_base,
        expected_mission_id=MISSION_ID,
        historical_audit=historical_audit,
    )


def _merge_ready(
    repo: Path,
    base: str,
    head: str,
    receipt: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict:
    """Run the real merge-ready gate and return its structured output."""

    local = repo.parent / "local-preflight.json"
    preflight = {
        "schema_version": "agentic-engineering-workflow/v1",
        "workflow": "agentic_engineering_workflow_v1",
        "verdict": "PASS",
        "base_sha": base,
        "head_sha": head,
        "current_head_sha": head,
        "changed_paths": ["Makefile"],
    }
    local.write_text(json.dumps(preflight), encoding="utf-8")
    args = agent_workflow.build_parser().parse_args(
        [
            "merge-ready",
            "--repo-root",
            str(repo),
            "--base-sha",
            base,
            "--head-sha",
            head,
            "--mission-id",
            MISSION_ID,
            "--mission-scope-file",
            str(_scope_file(repo)),
            "--local-preflight-json",
            str(local),
            "--receipt",
            str(receipt),
            "--pr",
            "1",
            "--protected-invariants",
            "PASS",
            "--forbidden-side-effects",
            "NO",
            "--json",
        ]
    )
    monkeypatch.setattr(
        agent_workflow,
        "_remote_pr_check",
        lambda pr_number, *, expected_head, **_kwargs: (
            agent_workflow.GateCheck("remote-required-ci", "PASS", "mock exact-head CI"),
            {"pr": pr_number, "verdict": "PASS", "head_sha": expected_head},
            _body(review_result="PASS", reviewed_sha=expected_head, provider="codex"),
        ),
    )
    monkeypatch.setattr(
        "scripts.devops.agent_workflow_preflight.run_preflight",
        lambda *_args, **_kwargs: preflight,
    )
    stream = io.StringIO()
    with redirect_stdout(stream):
        exit_code = agent_workflow.merge_ready_command(args)
    output = json.loads(stream.getvalue())
    output["exit_code"] = exit_code
    return output


def test_retired_reviewer_policy_receipt_is_stale_not_current(tmp_path: Path):
    """Evidence recorded under a retired pin stays history, never approval."""

    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(
        tmp_path, repo, base, head, command_transform=_retired_policy_command
    )
    result = _classification(receipt, repo, current_head=head, expected_base=base)
    assert result.classification == CLASSIFICATION_STALE_TOOLING
    assert result.integrity == INTEGRITY_INTACT
    assert result.current_approval_eligible is False
    assert "REVIEW_POLICY_DRIFT" in result.reason_codes
    assert "REVIEW_MODEL_POLICY_DRIFT" in result.reason_codes
    # The recorded model survives verbatim; only its currency is retired.
    assert result.review_model == RETIRED_REVIEW_MODEL_PINNED
    assert result.approved_review_model == REVIEW_MODEL_PINNED
    assert not any("TAMPER" in code for code in result.reason_codes)
    with pytest.raises(ReviewReceiptError, match="STALE_TOOLING"):
        validate_receipt(receipt, repo_root=repo, current_head=head, expected_base=base)


def test_pinned_model_name_over_a_retired_command_is_invalid(tmp_path: Path):
    """Claiming the pinned model the recorded argv never ran is tamper."""

    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(
        tmp_path,
        repo,
        base,
        head,
        command_transform=_retired_policy_command,
        overrides={"model_provenance": {"review_model": REVIEW_MODEL_PINNED}},
    )
    result = _classification(receipt, repo, current_head=head)
    assert result.classification == CLASSIFICATION_INVALID
    assert result.integrity == INTEGRITY_TAMPERED
    assert "MODEL_FIELD_COMMAND_MISMATCH" in result.reason_codes
    assert result.current_approval_eligible is False
    with pytest.raises(ReviewReceiptError, match="MODEL_FIELD_COMMAND_MISMATCH"):
        validate_receipt(receipt, repo_root=repo, current_head=head)


def test_retired_reviewer_policy_receipt_cannot_satisfy_merge_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(
        tmp_path, repo, base, head, command_transform=_retired_policy_command
    )
    output = _merge_ready(repo, base, head, receipt, monkeypatch)
    assert output["merge_ready"] == "NO"
    assert output["ready_for_execution_controller_merge_review"] == "NO"
    assert output["receipt_classification"] == CLASSIFICATION_STALE_TOOLING
    assert output["model_provenance_valid"] == "NO"
    assert output["exit_code"] == 1


def test_pinned_policy_exposes_no_model_override_seam(monkeypatch: pytest.MonkeyPatch):
    """No argument or environment seam can replace the pinned reviewer model."""

    parameters = tuple(inspect.signature(build_reviewer_command).parameters)
    assert not any("model" in name or "effort" in name for name in parameters)
    for name in ("CODEX_MODEL", "OPENAI_MODEL", "MODEL", "CODEX_REVIEW_MODEL"):
        monkeypatch.setenv(name, RETIRED_REVIEW_MODEL_PINNED)
    command = _pinned_command()
    assert command[command.index("-m") + 1] == REVIEW_MODEL_PINNED
    assert 'model_reasoning_effort="medium"' in command
    # The explicit flag is what selects the model, so user config stays inert.
    assert "--ignore-user-config" in command


def test_reviewer_receipt_schema_stays_v3(tmp_path: Path):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(tmp_path, repo, base, head)
    document = json.loads(receipt.read_text(encoding="utf-8"))
    assert document["schema_version"] == "codex-independent-review-receipt/v3"


@pytest.mark.parametrize("severity", ["P0", "P1", "P2"])
def test_blocking_severities_still_block_merge_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, severity: str
):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(
        tmp_path,
        repo,
        base,
        head,
        result="FAIL",
        finding={
            "severity": severity,
            "title": f"{severity} blocking defect",
            "path": "Makefile",
            "line": 1,
            "summary": "A blocking defect for the merge-readiness contract.",
        },
    )
    # The receipt's provenance is intact; the blocking verdict is what fails.
    assert _classification(receipt, repo, current_head=head).classification == (
        CLASSIFICATION_VALID_CURRENT
    )
    output = _merge_ready(repo, base, head, receipt, monkeypatch)
    assert output["merge_ready"] == "NO"
    assert output["exit_code"] == 1


def test_p3_finding_remains_non_blocking(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo, base, head = _make_repo(tmp_path)
    receipt = _write_valid_receipt(
        tmp_path,
        repo,
        base,
        head,
        result="PASS",
        finding={
            "severity": "P3",
            "title": "P3 maintainability note",
            "path": "Makefile",
            "line": 1,
            "summary": "A non-blocking maintainability observation.",
        },
    )
    result = _classification(receipt, repo, current_head=head)
    assert result.classification == CLASSIFICATION_VALID_CURRENT
    output = _merge_ready(repo, base, head, receipt, monkeypatch)
    assert output["merge_ready"] == "YES"
    assert output["exit_code"] == 0
