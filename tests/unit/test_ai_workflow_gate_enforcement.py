"""Tests for AI workflow gate — DB write guard enforcement phase2.

lifecycle: test-fixture
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "scripts/ops/ai_workflow_gate.py"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts/ops"))
import textwrap  # noqa: E402

import ai_workflow_gate as gate  # noqa: E402


def _valid_pr_body() -> str:
    """A minimal-valid PR body with all required sections."""
    return textwrap.dedent(
        """\
    ## Summary

    - Test PR for AI workflow gate validation.

    ## Scope

    | Item | Value |
    |---|---|
    | Task type | governance-only |
    | Workflow class | NORMAL |
    | One task / one branch / one PR | yes |
    | Business code changed | no |

    ## Dangerous File Authorization

    This fixture only exercises the gate CLI and does not authorize a production change.

    ## PR Authorization Matrix

    | Authorized paths | scripts/ops/ai_workflow_gate.py, tests/unit/test_ai_workflow_gate_enforcement.py |
    |---|---|

    ## Documentation Impact

    | Item | Value |
    |---|---|
    | New docs added | 0 |
    | Modified docs | AGENT_WORKFLOW.md — added section 19.5 hollow-compliance rules |
    | Reason | Updated workflow documentation to record new content-quality gate rules |

    ## Safety Impact

    | Item | Value |
    |---|---|
    | DB used | n/a |
    | Browser automation used | no |
    | Scraper run | no |

    ## Validation

    | Validation | Result |
    |---|---|
    | Unit tests (pytest) | 47 passed, 0 failed |
    | Ruff check | clean |
    | Ruff format --check | clean |
    | Gate CLI smoke | AI workflow gate passes with valid body |

    ## CI Gate Scope

    - What the validation proves: CI passes.
    - What the validation does not prove: runtime correctness.

    ## No deletion / no move / no rename confirmation

    | Item | Value |
    |---|---|
    | Deleted files | 0 |

    ## Rollback Plan

    - Revert this commit via `git revert <merge-commit-sha>`.
    - No database migrations, schema changes, or data writes are involved.
    - After revert, re-run `make ci-local` to confirm the gate still passes.

    ## SC-002 status

    - SC-002 remains unchanged; this test covers only gate enforcement behavior.

    ## Remaining risks

    - No additional risk is introduced by this test fixture.

    ## Next Recommended Task

    Do not start automatically.

    Recommended next task only after user confirmation:

    - TBD
    """
    )


def test_db_write_guard_enforcement_function_exists():
    """check_db_write_guard_enforcement must be importable."""
    assert callable(gate.check_db_write_guard_enforcement)


@pytest.mark.parametrize("operation", ["delete", "rename"])
@pytest.mark.parametrize("declaration", ["yes", "no", "maybe", "missing"])
def test_canonical_contract_real_git_removal_reaches_shared_gate(tmp_path, operation, declaration):
    """A real D/R diff must fail backflow even while final review is pending."""
    doc = "docs/data/CANONICAL_PREMATCH_FEATURE_FRAME_CONTRACT.md"

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, text=True).strip()

    git("init", "-q", "-b", "fixture/canonical-contract-status")
    git("config", "user.name", "Offline fixture")
    git("config", "user.email", "fixture@example.invalid")
    target = tmp_path / doc
    target.parent.mkdir(parents=True)
    target.write_text("# Canonical contract fixture\n", encoding="utf-8")
    git("add", doc)
    git("commit", "-qm", "fixture baseline")
    base = git("rev-parse", "HEAD")
    if operation == "delete":
        target.unlink()
    else:
        target.rename(tmp_path / (doc + ".bak"))
    git("add", "-A")
    git("commit", "-qm", "fixture removal")
    changes = gate.parse_name_status(git("diff", "--name-status", "-M", base, "HEAD"))
    assert len(changes) == 1
    change = changes[0]
    assert change.status == ("D" if operation == "delete" else "R")
    assert (change.path if operation == "delete" else change.old_path) == doc
    body = textwrap.dedent(
        f"""\
        ## Summary
        Negative fixture: actual contract removal must be rejected.
        ## Scope
        | Task type | source-code |
        | Workflow class | CRITICAL |
        ## Tests
        Offline Git fixture only, no completed Reviewer receipt.
        ## Risk
        The update claim below is deliberately invalid for this negative test.
        ## Rollback
        Disposable fixture only; no real repository rollback.
        ## Documentation Impact
        | Capability changed? | no |
        | Milestone changed? | no |
        | Canonical entrypoint changed? | no |
        | Current blocker changed? | no |
        | Data/model/authorization contract changed? | {declaration} |
        | Repository structure/authority navigation changed? | no |
        | Project vision / target-state changed? | no |
        | Source-of-truth docs updated | yes |
        | Updated authoritative docs | {doc} |
        | If not updated, explicit reason | No other capability or workflow authority is changed by this negative fixture. |
        """
    )
    if declaration == "missing":
        body = body.replace("| Data/model/authorization contract changed? | missing |\n", "")
    helper_errors = gate.check_documentation_backflow(
        body, gate.changed_paths(changes), changes=changes
    )
    assert any("cannot be deleted or renamed away as an update" in e for e in helper_errors)
    errors = gate.validate(body, changes)
    # Check the deletion-specific error, not an unrelated PENDING/metadata block.
    assert any("cannot be deleted or renamed away as an update" in error for error in errors)


def test_db_write_guard_enforcement_no_js_ops_changed():
    """When no scripts/ops/*.js files changed, returns empty errors/warnings."""
    errors, warnings = gate.check_db_write_guard_enforcement({"docs/README.md", "src/main.py"})
    assert errors == []
    assert warnings == []


_ENFORCEMENT_TUPLE_LEN = 2


def test_db_write_guard_enforcement_guarded_file():
    """A known guarded scripts/ops file should produce no errors."""
    errors, _warnings = gate.check_db_write_guard_enforcement({"scripts/ops/purge_orphans.js"})
    assert errors == [], f"Expected no errors for guarded file, got: {errors}"


def test_db_write_guard_enforcement_returns_tuple():
    """check_db_write_guard_enforcement must return a 2-tuple of lists."""
    result = gate.check_db_write_guard_enforcement({"scripts/ops/purge_orphans.js"})
    assert isinstance(result, tuple)
    assert len(result) == _ENFORCEMENT_TUPLE_LEN
    errors, warnings = result
    assert isinstance(errors, list)
    assert isinstance(warnings, list)


def test_enforcement_validate_integration_clean():
    """validate() should pass when DB write guard enforcement finds no violations."""
    body = _valid_pr_body()
    changes = [
        gate.Change("M", "scripts/ops/purge_orphans.js"),
        gate.Change("M", "docs/CODEX_WORKFLOW.md"),
    ]
    errors = gate.validate(body, changes)
    db_errors = [e for e in errors if "DB-WRITE-GUARD ENFORCEMENT" in e]
    assert db_errors == [], f"Should not have DB enforcement errors: {db_errors}"


def _review_test_scope(task_type, workflow_class, paths):
    return gate.MissionScope.from_mapping(
        {
            "schema_version": "agentic-mission-scope/v1",
            "mission_id": "REVIEW_EVIDENCE_TEST",
            "task_type": task_type,
            "workflow_class": workflow_class,
            "authorized_paths": paths,
            "authorized_prefixes": [],
            "excluded_paths": [],
            "excluded_prefixes": [],
            "excluded_tokens": [],
            "protected_invariants": ["Exercise review metadata without executing a reviewer."],
            "forbidden_side_effects": ["No deployment, migration or provider calls."],
        }
    )


def test_strict_review_evidence_is_enforced_by_blocking_path():
    """A genuine STRICT path accepts current evidence and rejects stale evidence."""
    current_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    # Dockerfile is docker-deploy/STRICT, unlike unknown paths or workflow governance.
    paths = ["Dockerfile"]
    scope = _review_test_scope("docker-deploy", "STRICT", paths)
    changes = [gate.Change("M", path) for path in paths]
    body = (
        _valid_pr_body()
        .replace("| Task type | governance-only |", "| Task type | docker-deploy |")
        .replace("| Workflow class | NORMAL |", "| Workflow class | STRICT |")
        .replace(
            "This fixture only exercises the gate CLI and does not authorize a production change.",
            "The test fixture authorizes a Dockerfile packaging change only.\n"
            "Validate the container build and review metadata before release; "
            "rollback is a focused commit revert. This test does not deploy the container.",
        )
        .replace(
            "scripts/ops/ai_workflow_gate.py, tests/unit/test_ai_workflow_gate_enforcement.py",
            "Dockerfile",
        )
    )
    body += f"""

## Strict Review Evidence

| Field | Value |
| --- | --- |
| Version | 1 |
| Task type | STRICT |
| Provider | test-independent-reviewer |
| Reviewed full SHA | {current_sha} |
| Result | PASS |
| Timestamp | 2026-08-21T12:00:00Z |
"""
    kwargs = {
        "block_matrix": True,
        "enforce_strict_review": True,
        "enforce_agent_workflow_scope": True,
        "mission_scope": scope,
        "base_ref": current_sha,
        "head_ref": current_sha,
    }
    errors = gate.validate(body, changes, **kwargs)
    assert errors == [], errors

    stale_sha = "b" * 40 if current_sha != "b" * 40 else "c" * 40
    stale_body = body.replace(
        f"| Reviewed full SHA | {current_sha} |", f"| Reviewed full SHA | {stale_sha} |"
    )
    stale_errors = gate.validate(stale_body, changes, **kwargs)
    assert stale_errors, "Stale STRICT evidence must be rejected."
    assert all(error.startswith("STRICT_REVIEW_STALE") for error in stale_errors), stale_errors

    normal_body = body.replace("| Workflow class | STRICT |", "| Workflow class | NORMAL |")
    normal_errors = gate.validate(normal_body, changes, **kwargs)
    assert any(
        error.startswith("STRICT_REVIEW_CLASSIFICATION_REQUIRED") for error in normal_errors
    ), normal_errors
    assert not any(error.startswith("CRITICAL_REVIEW_") for error in normal_errors), normal_errors


@pytest.mark.parametrize("workflow_class", ["NORMAL", "STRICT"])
def test_blocking_path_rejects_normal_for_high_risk_changed_path(workflow_class):
    """Neither NORMAL nor STRICT can waive database migration CRITICAL review."""
    body = (
        _valid_pr_body()
        .replace("| Task type | governance-only |", "| Task type | db-migration-sql |")
        .replace("| Workflow class | NORMAL |", f"| Workflow class | {workflow_class} |")
    )
    paths = ["database/migrations/001.sql"]
    changes = [gate.Change("M", path) for path in paths]
    scope = _review_test_scope("db-migration-sql", workflow_class, paths)
    current_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    errors = gate.validate(
        body,
        changes,
        block_matrix=True,
        enforce_strict_review=True,
        enforce_agent_workflow_scope=True,
        mission_scope=scope,
        base_ref=current_sha,
        head_ref=current_sha,
    )
    classification_errors = [
        error for error in errors if error.startswith("CRITICAL_REVIEW_CLASSIFICATION_REQUIRED")
    ]
    assert classification_errors, errors
    assert any(
        "db-migration-sql" in error and workflow_class in error for error in classification_errors
    ), classification_errors
    assert not any(error.startswith("STRICT_REVIEW_CLASSIFICATION_REQUIRED") for error in errors), (
        errors
    )


def test_production_gate_rechecks_current_pr_body_after_edit():
    """PR body edits must start a fresh required governance check for the same HEAD."""
    workflow = (ROOT / ".github" / "workflows" / "production-gate.yml").read_text()
    trigger = "  pull_request:\n    types:\n"
    assert trigger in workflow
    assert "      - edited\n" in workflow


def test_gate_cli_with_skip_body_checks_and_clean_files_passes():
    """Gate CLI with --skip-body-checks and clean changed files should exit 0."""
    result = subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--pr-body-file",
            "/dev/null",
            "--base-ref",
            "HEAD",
            "--head-ref",
            "HEAD",
            "--skip-body-checks",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"


def test_gate_cli_with_valid_body_and_clean_files_passes():
    """Gate CLI with valid PR body and clean changed files should exit 0."""
    body = _valid_pr_body()
    result = subprocess.run(
        [
            sys.executable,
            str(GATE),
            "--pr-body-stdin",
            "--base-ref",
            "HEAD",
            "--head-ref",
            "HEAD",
        ],
        input=body,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"
