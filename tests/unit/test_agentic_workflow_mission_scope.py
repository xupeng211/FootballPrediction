"""Dynamic bounded-mission scope contract tests for Agentic Workflow V1."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

import pytest

from scripts.devops import agent_workflow, agent_workflow_preflight, codex_independent_review
from scripts.devops.codex_independent_review import _codex_prompt
from scripts.ops import ai_workflow_gate
from scripts.ops.helpers.agent_workflow_contract import (
    DECISION_ESCALATE,
    MissionScope,
    MissionScopeError,
    classify_failure,
    contract_summary,
    load_mission_scope_file,
    mission_scope_sha256,
    validate_mission_scope,
    validate_mission_scope_reference,
    validate_pr_metadata,
)
from scripts.ops.helpers.git_change_helpers import Change
from tests.helpers.agentic_workflow_fixtures import (
    BASE_SHA,
    MISSION_ID,
    MISSION_SCOPE_PATH,
    mission_scope_payload,
)
from tests.helpers.agentic_workflow_fixtures import body as _body
from tests.helpers.agentic_workflow_fixtures import make_repo as _make_repo
from tests.helpers.agentic_workflow_fixtures import write_valid_receipt as _write_valid_receipt

ROOT = Path(__file__).resolve().parents[2]


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True)
    return result.stdout.strip()


def _mission_scope(*, mission_id: str = MISSION_ID, **overrides: object) -> MissionScope:
    payload = mission_scope_payload(mission_id=mission_id)
    payload.update(overrides)
    return MissionScope.from_mapping(payload)


def _scope_file(repo: Path) -> Path:
    return repo / MISSION_SCOPE_PATH


def _assert_error(errors: list[str], fragment: str) -> None:
    assert errors
    assert fragment in errors[0]


def _stage_d_scope() -> MissionScope:
    payload = mission_scope_payload(mission_id="FUTURE_STAGE_D_MISSION")
    payload.update(
        {
            "task_type": "source-code",
            "authorized_paths": [
                "docs/agentic/missions/current.json",
                "src/infrastructure/market_evidence/stageDOperations.js",
                "scripts/ops/stage_d_controlled_initialization.js",
                "tests/unit/market_evidence/stage_d_controlled_initialization.test.js",
            ],
            "authorized_prefixes": ["docs/agentic/stage-d/"],
            "excluded_prefixes": ["src/infrastructure/market_evidence/private/"],
            "excluded_tokens": ["pr1903"],
        }
    )
    return MissionScope.from_mapping(payload)


@pytest.fixture(autouse=True)
def _synthetic_codex_provenance_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Give merge-gate fixtures a disposable local Codex executable."""

    codex_root = tmp_path / "codex-home"
    codex_root.mkdir(mode=0o700)
    bin_root = tmp_path / "bin"
    bin_root.mkdir(mode=0o700)
    codex_binary = bin_root / "codex"
    codex_binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    codex_binary.chmod(0o700)
    monkeypatch.setenv("CODEX_HOME", str(codex_root))
    monkeypatch.setenv("PATH", f"{bin_root}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setattr(codex_independent_review, "resolve_codex_binary", lambda _: codex_binary)


def test_protected_stage_d_path_is_out_of_scope():
    errors = validate_mission_scope(["scripts/ops/stage_d_cycle.js"], _mission_scope())
    assert errors
    assert "SCOPE_ESCALATE" in errors[0]


@pytest.mark.parametrize(
    "path",
    [
        "scripts/ops/helpers/db_write_guard.js",
        "scripts/ops/helpers/python_db_write_guard.py",
        "scripts/ops/helpers/python_db_write_enforcement_check.py",
    ],
)
def test_production_db_write_guard_paths_are_out_of_scope(path: str):
    errors = validate_mission_scope([path], _mission_scope())
    assert errors
    assert "SCOPE_ESCALATE" in errors[0]


def test_workflow_mission_authorizes_workflow_paths_and_rejects_stage_d():
    scope_path = (
        ROOT / "docs/agentic/missions/AGENTIC_WORKFLOW_V1_DYNAMIC_MISSION_SCOPE_GENERALIZATION.json"
    )
    scope = load_mission_scope_file(scope_path, repo_root=ROOT)
    assert (
        validate_mission_scope(
            ["scripts/devops/agent_workflow.py", "schemas/agentic/mission_scope.schema.json"],
            scope,
        )
        == []
    )
    errors = validate_mission_scope(
        ["src/infrastructure/market_evidence/stageDOperations.js"], scope
    )
    _assert_error(errors, "SCOPE_ESCALATE")


def test_stage_d_synthetic_mission_authorizes_only_selected_paths():
    scope = _stage_d_scope()
    selected = [
        "src/infrastructure/market_evidence/stageDOperations.js",
        "scripts/ops/stage_d_controlled_initialization.js",
        "tests/unit/market_evidence/stage_d_controlled_initialization.test.js",
        "docs/agentic/stage-d/runbook.md",
    ]
    assert validate_mission_scope(selected, scope) == []
    errors = validate_mission_scope(["src/infrastructure/market_evidence/unlisted.js"], scope)
    _assert_error(errors, "SCOPE_ESCALATE")


def test_different_missions_have_different_scope():
    workflow = _mission_scope()
    stage_d = _stage_d_scope()
    assert validate_mission_scope(["Makefile"], workflow) == []
    assert validate_mission_scope(["Makefile"], stage_d)
    assert (
        validate_mission_scope(["src/infrastructure/market_evidence/stageDOperations.js"], stage_d)
        == []
    )
    assert validate_mission_scope(
        ["src/infrastructure/market_evidence/stageDOperations.js"], workflow
    )


def test_missing_or_empty_mission_scope_fails_closed():
    errors = validate_mission_scope(["Makefile"], None)
    _assert_error(errors, "missing/UNKNOWN")
    payload = mission_scope_payload()
    payload["authorized_paths"] = []
    payload["authorized_prefixes"] = []
    with pytest.raises(MissionScopeError, match="cannot both be empty"):
        MissionScope.from_mapping(payload)


def test_mission_scope_symlink_is_rejected(tmp_path: Path):
    target = tmp_path / "scope-target.json"
    target.write_text(
        json.dumps(mission_scope_payload(), ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    link = tmp_path / "scope-link.json"
    link.symlink_to(target)
    with pytest.raises(MissionScopeError, match="must not be a symlink"):
        load_mission_scope_file(link, repo_root=tmp_path)


def test_excluded_path_overrides_authorized_prefix():
    scope = _mission_scope(
        authorized_paths=[],
        authorized_prefixes=["src/"],
        excluded_prefixes=["src/private/"],
    )
    assert validate_mission_scope(["src/public/file.js"], scope) == []
    errors = validate_mission_scope(["src/private/file.js"], scope)
    _assert_error(errors, "explicitly excluded")


def test_unknown_path_and_unauthorized_scope_expansion_are_rejected():
    scope = _mission_scope()
    errors = validate_mission_scope(["unlisted/file.txt"], scope)
    _assert_error(errors, "not authorized")
    assert classify_failure("mission_scope_expansion") == DECISION_ESCALATE


@pytest.mark.parametrize(
    "path",
    [
        "/etc/passwd",
        "../Makefile",
        "src/../../Makefile",
        "",
        ".",
    ],
)
def test_mission_scope_rejects_absolute_traversal_and_root_paths(path: str):
    errors = validate_mission_scope([path], _mission_scope())
    _assert_error(errors, "SCOPE_INVALID")


def test_mission_scope_normalizes_backslashes_and_duplicate_separators_safely():
    scope = _mission_scope(authorized_paths=[], authorized_prefixes=["src/foo"])
    assert validate_mission_scope([r"src\\foo\\./bar.js"], scope) == []
    assert validate_mission_scope(["src//foo/bar.js"], scope) == []


def test_mission_scope_rejects_prefix_confusion():
    scope = _mission_scope(authorized_paths=[], authorized_prefixes=["src/foo"])
    assert validate_mission_scope(["src/foo/bar.js"], scope) == []
    errors = validate_mission_scope(["src/foobar/bar.js"], scope)
    _assert_error(errors, "not authorized")


def test_current_scope_is_not_advertised_as_global_policy():
    summary = contract_summary()
    assert "mission_allowed_prefixes" not in summary
    assert "mission_excluded_prefixes" not in summary
    contract = (ROOT / "scripts/ops/helpers/agent_workflow_contract.py").read_text(encoding="utf-8")
    assert "MISSION_ALLOWED_PREFIXES" not in contract
    assert "MISSION_EXCLUDED_PREFIXES" not in contract


def test_current_pr_scope_remains_workflow_only():
    scope = load_mission_scope_file(
        ROOT
        / "docs/agentic/missions/AGENTIC_WORKFLOW_V1_DYNAMIC_MISSION_SCOPE_GENERALIZATION.json",
        repo_root=ROOT,
    )
    assert (
        validate_mission_scope(
            ["scripts/devops/agent_workflow.py", "docs/agentic/missions/current.json"],
            scope,
        )
        == []
    )
    stage_d_paths = [
        "src/infrastructure/market_evidence/stageDOperations.js",
        "scripts/ops/stage_d_controlled_initialization.js",
        "tests/unit/market_evidence/stage_d_controlled_initialization.test.js",
    ]
    assert validate_mission_scope(stage_d_paths, scope)


def test_global_metadata_gate_does_not_apply_bootstrap_scope():
    assert validate_pr_metadata(_body(), ["src/application.js"]) == []
    source = (ROOT / "scripts/ops/ai_workflow_gate.py").read_text(encoding="utf-8")
    assert "enforce_agent_workflow_scope" in source
    assert "mission_scope=mission_scope" in source


@pytest.mark.parametrize("skip_body_checks", [False, True])
def test_explicit_scope_enforcement_cannot_be_skipped_by_metadata_mode(
    skip_body_checks: bool,
):
    errors = ai_workflow_gate.validate(
        _body(),
        [Change("M", "src/not-authorized.py")],
        skip_body_checks=skip_body_checks,
        enforce_agent_workflow_scope=True,
        mission_scope=None,
    )
    _assert_error(errors, "current mission scope contract is required")


def test_explicit_scope_enforcement_checks_paths_when_body_checks_are_skipped():
    errors = ai_workflow_gate.validate(
        "",
        [Change("M", "src/not-authorized.py")],
        skip_body_checks=True,
        enforce_agent_workflow_contract=False,
        enforce_agent_workflow_scope=True,
        mission_scope=_mission_scope(),
    )
    _assert_error(errors, "not authorized")


def test_scope_reference_binds_mission_task_and_workflow():
    scope = _mission_scope()
    errors = validate_mission_scope_reference(
        _body(task_type="source-code"),
        mission_scope=scope,
        scope_path=MISSION_SCOPE_PATH,
    )
    assert any("Task type" in error for error in errors)


def test_explicit_remote_scope_context_binds_exact_ci_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo, _base, head = _make_repo(tmp_path)
    scope_file = _scope_file(repo)
    scope = load_mission_scope_file(scope_file, repo_root=repo)
    monkeypatch.setattr(ai_workflow_gate, "ROOT", repo)
    assert (
        ai_workflow_gate._validate_mission_scope_context(
            _body(reviewed_sha=head),
            scope_file,
            scope,
            resolved_head=head,
            skip_body_checks=False,
        )
        == []
    )
    scope_file.write_text(scope_file.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    errors = ai_workflow_gate._validate_mission_scope_context(
        _body(reviewed_sha=head),
        scope_file,
        scope,
        resolved_head=head,
        skip_body_checks=False,
    )
    _assert_error(errors, "differ from exact CI HEAD")


def test_local_preflight_uses_explicit_current_mission_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo, base, head = _make_repo(tmp_path)
    _git(repo, "checkout", "-qb", "feature")
    monkeypatch.setattr(agent_workflow_preflight, "ROOT", repo)
    monkeypatch.setattr("scripts.ops.helpers.git_change_helpers.ROOT_HELPER", repo)
    monkeypatch.setattr("scripts.ops.ai_workflow_gate.ROOT", repo)
    monkeypatch.setattr(
        "scripts.ops.ai_workflow_gate.run_governance_growth_gate",
        lambda *_args, **_kwargs: [],
    )
    result = agent_workflow_preflight.run_preflight(
        _body(reviewed_sha=head),
        base_ref=base,
        head_ref=head,
        mission_scope_file=_scope_file(repo),
    )
    assert result["verdict"] == "PASS"
    assert result["mission_scope"]["mission_id"] == MISSION_ID
    assert result["mission_scope_path"] == MISSION_SCOPE_PATH


def test_preflight_cli_forwards_current_mission_scope_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    body_path = tmp_path / "pr-body.md"
    body_path.write_text(_body(), encoding="utf-8")
    scope_path = tmp_path / "scope.json"
    captured: dict[str, object] = {}

    def fake_run_preflight(*_args: object, **kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"verdict": "PASS"}

    monkeypatch.setattr(agent_workflow_preflight, "run_preflight", fake_run_preflight)
    assert (
        agent_workflow_preflight.main(
            [
                "--pr-body-file",
                str(body_path),
                "--mission-scope-file",
                str(scope_path),
                "--json",
            ]
        )
        == 0
    )
    assert captured["mission_scope_file"] == scope_path


def test_reviewer_receives_current_mission_scope():
    scope = _stage_d_scope()
    prompt = _codex_prompt(
        mission_id=scope.mission_id,
        base_sha=BASE_SHA,
        head_sha="2" * 40,
        mission_scope=scope,
        mission_scope_path=MISSION_SCOPE_PATH,
        mission_scope_sha256="a" * 64,
    )
    assert f"MISSION_SCOPE_PATH={MISSION_SCOPE_PATH}" in prompt
    assert "src/infrastructure/market_evidence/stageDOperations.js" in prompt
    assert "FUTURE_STAGE_D_MISSION" in prompt


def test_pr_1903_sample_files_are_valid_only_under_explicit_future_scope():
    stage_d = _stage_d_scope()
    workflow = load_mission_scope_file(
        ROOT
        / "docs/agentic/missions/AGENTIC_WORKFLOW_V1_DYNAMIC_MISSION_SCOPE_GENERALIZATION.json",
        repo_root=ROOT,
    )
    sample = [
        "src/infrastructure/market_evidence/stageDOperations.js",
        "scripts/ops/stage_d_controlled_initialization.js",
        "tests/unit/market_evidence/stage_d_controlled_initialization.test.js",
    ]
    assert validate_mission_scope(sample, stage_d) == []
    assert validate_mission_scope(sample, workflow)


def test_merge_ready_uses_dynamic_mission_scope_and_never_merges(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    repo, _base, initial_head = _make_repo(tmp_path)
    base = initial_head
    stage_d = _stage_d_scope()
    _scope_file(repo).write_text(
        json.dumps(stage_d.to_dict(), ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    selected = repo / "src/infrastructure/market_evidence/stageDOperations.js"
    selected.parent.mkdir(parents=True)
    selected.write_text("export const stageD = true;\n", encoding="utf-8")
    _git(repo, "add", MISSION_SCOPE_PATH, "src/infrastructure/market_evidence/stageDOperations.js")
    _git(repo, "commit", "-qm", "future mission scope fixture")
    head = _git(repo, "rev-parse", "HEAD")
    receipt = _write_valid_receipt(tmp_path, repo, base, head, mission_id=stage_d.mission_id)
    scope_hash = mission_scope_sha256(_scope_file(repo))
    local = tmp_path / "local.json"
    preflight = {
        "schema_version": "agentic-engineering-workflow/v1",
        "workflow": "agentic_engineering_workflow_v1",
        "verdict": "PASS",
        "base_sha": base,
        "head_sha": head,
        "current_head_sha": head,
        "changed_paths": ["Makefile", "src/infrastructure/market_evidence/stageDOperations.js"],
        "mission_scope": stage_d.to_dict(),
        "mission_scope_path": MISSION_SCOPE_PATH,
        "mission_scope_sha256": scope_hash,
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
            stage_d.mission_id,
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
        ]
    )
    monkeypatch.setattr(
        agent_workflow,
        "_remote_pr_check",
        lambda _pr_number, *, expected_head, **_kwargs: (
            agent_workflow.GateCheck("remote-required-ci", "PASS", "mock exact-head CI"),
            {"verdict": "PASS", "head_sha": expected_head},
            _body(
                mission_id=stage_d.mission_id,
                task_type=stage_d.task_type,
                workflow_class=stage_d.workflow_class,
                review_result="PASS",
                reviewed_sha=expected_head,
                provider="codex",
            ),
        ),
    )
    monkeypatch.setattr(
        "scripts.devops.agent_workflow_preflight.run_preflight",
        lambda *_args, **_kwargs: preflight,
    )
    assert agent_workflow.merge_ready_command(args) == 0
