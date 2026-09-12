"""Remote per-mission scope enforcement for the required PR CI gate.

lifecycle: test-fixture
created: 2026-09-13
task: AGENTIC_WORKFLOW_V1_1B_F03A_REMOTE_PER_MISSION_SCOPE_ENFORCEMENT

Required remote PR CI used to validate only the global Agentic Workflow
contract.  These tests pin the F03-A behaviour that closes that gap: the PR
body may *select* exactly one tracked mission-scope contract, the contract
bytes are read from the exact PR HEAD commit, and the canonical validator
authorizes every changed path against it.

Every negative case here is a fail-closed control, not a warning.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ops import ai_workflow_gate
from scripts.ops.helpers import agent_workflow_scope_context as scope_context
from scripts.ops.helpers.agent_workflow_contract import (
    MISSION_SCOPE_MISSION_ID_MISMATCH,
    MISSION_SCOPE_SCHEMA_INVALID,
    MISSION_SCOPE_TASK_TYPE_MISMATCH,
    MISSION_SCOPE_WORKFLOW_CLASS_MISMATCH,
    MissionScope,
    MissionScopeError,
    validate_mission_scope,
)
from scripts.ops.helpers.agent_workflow_scope_context import (
    MISSION_SCOPE_ALLOWED_ROOT,
    MISSION_SCOPE_REFERENCE_ABSOLUTE_PATH,
    MISSION_SCOPE_REFERENCE_CONFLICTING,
    MISSION_SCOPE_REFERENCE_EMPTY,
    MISSION_SCOPE_REFERENCE_FILE_MISSING_AT_HEAD,
    MISSION_SCOPE_REFERENCE_MISSING,
    MISSION_SCOPE_REFERENCE_MULTIPLE,
    MISSION_SCOPE_REFERENCE_NOT_TRACKED_AT_HEAD,
    MISSION_SCOPE_REFERENCE_OUTSIDE_ALLOWED_ROOT,
    MISSION_SCOPE_REFERENCE_SYNTAX_INVALID,
    MISSION_SCOPE_REFERENCE_TRAVERSAL,
    MISSION_SCOPE_REFERENCE_UNTRUSTED_TABLE,
    MissionScopeReferenceError,
    mission_scope_reference,
    validate_mission_scope_reference_path,
)
from tests.helpers.agent_workflow_remote_scope_fixtures import (
    BAD_SCHEMA_SCOPE,
    DELETED_SCOPE,
    DRIFT_SCOPE,
    MALFORMED_SCOPE,
    OTHER_SCOPE,
    OUTSIDE_ROOT,
    SHA256_HEX_LENGTH,
    SYMLINK_SCOPE,
    UNAUTHORIZED_PATH,
    UNTRACKED_SCOPE,
    WORKFLOW_FILE,
    Repo,
    _minimal_body,
    _resolve,
    _scope,
    _scope_document,
    _scope_row,
    make_gate_repo,
    make_scope_repo,
)
from tests.helpers.agentic_workflow_fixtures import (
    MISSION_ID,
    MISSION_SCOPE_PATH,
    mission_scope_payload,
)
from tests.helpers.agentic_workflow_fixtures import body as _fixture_body


@pytest.fixture
def gate_repo(tmp_path: Path) -> Repo:
    return make_gate_repo(tmp_path)


@pytest.fixture
def scope_repo(tmp_path: Path) -> Repo:
    return make_scope_repo(tmp_path)


def _code(exc_info: pytest.ExceptionInfo[MissionScopeError]) -> str:
    """Return the coded reason a scope reference was refused."""

    assert isinstance(exc_info.value, MissionScopeReferenceError), exc_info.value
    return exc_info.value.code


def _assert_error(errors: list[str], fragment: str) -> None:
    """Assert the first gate error carries *fragment* (repository convention)."""

    assert errors
    assert fragment in errors[0]


# ---------------------------------------------------------------------------
# 1. Path safety of a PR-supplied reference (untrusted input)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("reference", "code"),
    [
        ("", MISSION_SCOPE_REFERENCE_EMPTY),
        ("   ", MISSION_SCOPE_REFERENCE_EMPTY),
        (None, MISSION_SCOPE_REFERENCE_EMPTY),
        (123, MISSION_SCOPE_REFERENCE_EMPTY),
        ("/etc/passwd", MISSION_SCOPE_REFERENCE_ABSOLUTE_PATH),
        ("/docs/agentic/missions/current.json", MISSION_SCOPE_REFERENCE_ABSOLUTE_PATH),
        ("\\docs\\agentic\\missions\\current.json", MISSION_SCOPE_REFERENCE_ABSOLUTE_PATH),
        ("C:/docs/agentic/missions/current.json", MISSION_SCOPE_REFERENCE_ABSOLUTE_PATH),
        ("docs/agentic/missions\\current.json", MISSION_SCOPE_REFERENCE_SYNTAX_INVALID),
        ("docs/agentic/../../etc/passwd.json", MISSION_SCOPE_REFERENCE_TRAVERSAL),
        ("../docs/agentic/missions/current.json", MISSION_SCOPE_REFERENCE_TRAVERSAL),
        ("docs/agentic/missions/current.json/../other.json", MISSION_SCOPE_REFERENCE_TRAVERSAL),
        ("docs/agentic/missions/../missions/current.json", MISSION_SCOPE_REFERENCE_TRAVERSAL),
        ("not-a-scope.json", MISSION_SCOPE_REFERENCE_OUTSIDE_ALLOWED_ROOT),
        ("docs/agentic/current.json", MISSION_SCOPE_REFERENCE_OUTSIDE_ALLOWED_ROOT),
        ("docs/AGENTIC/missions/current.json", MISSION_SCOPE_REFERENCE_OUTSIDE_ALLOWED_ROOT),
        ("Makefile", MISSION_SCOPE_REFERENCE_OUTSIDE_ALLOWED_ROOT),
        ("scripts/ops/ai_workflow_gate.py", MISSION_SCOPE_REFERENCE_OUTSIDE_ALLOWED_ROOT),
        ("docs/agentic/missions", MISSION_SCOPE_REFERENCE_OUTSIDE_ALLOWED_ROOT),
        ("docs/agentic/missions/x/current.json", MISSION_SCOPE_REFERENCE_SYNTAX_INVALID),
        ("docs/agentic/missions/current.txt", MISSION_SCOPE_REFERENCE_SYNTAX_INVALID),
        ("docs/agentic/missions/.json", MISSION_SCOPE_REFERENCE_SYNTAX_INVALID),
        ("docs/agentic/missions/current.json\x00", MISSION_SCOPE_REFERENCE_SYNTAX_INVALID),
        ("docs/agentic/missions/cur\nrent.json", MISSION_SCOPE_REFERENCE_SYNTAX_INVALID),
        ("docs/agentic/missions/cur\trent.json", MISSION_SCOPE_REFERENCE_SYNTAX_INVALID),
        ("docs/agentic/missions/cur\x1frent.json", MISSION_SCOPE_REFERENCE_SYNTAX_INVALID),
        ("docs/agentic/missions/cur\x7frent.json", MISSION_SCOPE_REFERENCE_SYNTAX_INVALID),
        ("docs/agentic/missions/current.json\u202e", MISSION_SCOPE_REFERENCE_SYNTAX_INVALID),
        # Unicode lookalikes must not alias the allowed root.
        ("d\u043ecs/agentic/missions/current.json", MISSION_SCOPE_REFERENCE_OUTSIDE_ALLOWED_ROOT),
        ("\uff44ocs/agentic/missions/current.json", MISSION_SCOPE_REFERENCE_OUTSIDE_ALLOWED_ROOT),
    ],
)
def test_scope_reference_path_rejects_unsafe_values(reference: object, code: str) -> None:
    with pytest.raises(MissionScopeReferenceError) as exc_info:
        validate_mission_scope_reference_path(reference)
    assert _code(exc_info) == code


def test_scope_reference_path_accepts_and_normalizes_the_only_allowed_root() -> None:
    assert MISSION_SCOPE_ALLOWED_ROOT == "docs/agentic/missions/"
    assert (
        validate_mission_scope_reference_path("  docs/agentic/missions/current.json  ")
        == "docs/agentic/missions/current.json"
    )
    assert (
        validate_mission_scope_reference_path("docs//agentic/./missions/current.json")
        == "docs/agentic/missions/current.json"
    )


# ---------------------------------------------------------------------------
# 2. Exactly one unambiguous reference is required
# ---------------------------------------------------------------------------


def test_single_scope_reference_is_extracted() -> None:
    assert mission_scope_reference(_minimal_body(MISSION_SCOPE_PATH)) == MISSION_SCOPE_PATH


def test_missing_scope_row_fails_closed() -> None:
    body = _minimal_body(MISSION_SCOPE_PATH).replace("Mission scope contract", "Notes")
    with pytest.raises(MissionScopeReferenceError) as exc_info:
        mission_scope_reference(body)
    assert _code(exc_info) == MISSION_SCOPE_REFERENCE_MISSING


def test_absent_scope_section_fails_closed() -> None:
    with pytest.raises(MissionScopeReferenceError) as exc_info:
        mission_scope_reference("## Summary\n\nNo scope section at all.\n")
    assert _code(exc_info) == MISSION_SCOPE_REFERENCE_MISSING


def test_empty_scope_reference_value_fails_closed() -> None:
    with pytest.raises(MissionScopeReferenceError) as exc_info:
        mission_scope_reference(_minimal_body(""))
    assert _code(exc_info) == MISSION_SCOPE_REFERENCE_EMPTY


def test_duplicate_identical_references_fail_closed() -> None:
    with pytest.raises(MissionScopeReferenceError) as exc_info:
        mission_scope_reference(_minimal_body(MISSION_SCOPE_PATH, rows=2))
    assert _code(exc_info) == MISSION_SCOPE_REFERENCE_MULTIPLE


def test_conflicting_references_fail_closed() -> None:
    body = _minimal_body(MISSION_SCOPE_PATH).replace(
        _scope_row(MISSION_SCOPE_PATH).splitlines()[0],
        f"{_scope_row(MISSION_SCOPE_PATH).splitlines()[0]}\n"
        f"| Mission scope contract | `{OTHER_SCOPE}` |",
    )
    with pytest.raises(MissionScopeReferenceError) as exc_info:
        mission_scope_reference(body)
    assert _code(exc_info) == MISSION_SCOPE_REFERENCE_CONFLICTING


def test_scope_table_with_extra_delimiters_fails_closed() -> None:
    body = _minimal_body(MISSION_SCOPE_PATH).replace(
        _scope_row(MISSION_SCOPE_PATH).splitlines()[0],
        f"| Mission scope contract | `{MISSION_SCOPE_PATH}` | smuggled |",
    )
    with pytest.raises(MissionScopeReferenceError) as exc_info:
        mission_scope_reference(body)
    assert _code(exc_info) == MISSION_SCOPE_REFERENCE_UNTRUSTED_TABLE


# ---------------------------------------------------------------------------
# 3. Injection attempts never execute
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        "$(touch {canary})",
        "`touch {canary}`",
        "; touch {canary}",
        "&& touch {canary}",
        "|| touch {canary}",
        "| touch {canary}",
        "${{IFS}}touch {canary}",
        "docs/agentic/missions/$(touch {canary}).json",
        "docs/agentic/missions/`touch {canary}`.json",
        "docs/agentic/missions/current.json; touch {canary}",
        "docs/agentic/missions/current.json && touch {canary}",
        "docs/agentic/missions/current.json | tee {canary}",
        "--upload-pack=touch {canary}",
        "docs/agentic/missions/current.json\\n touch {canary}",
        "docs/agentic/missions/current.json > {canary}",
        "$(id>/dev/null)",
    ],
)
def test_scope_reference_payloads_never_execute(
    tmp_path: Path, scope_repo: Repo, payload: str
) -> None:
    canary = tmp_path / "CANARY_MUST_NOT_EXIST"
    body = _minimal_body(payload.format(canary=canary))
    with pytest.raises(MissionScopeError):
        _resolve(scope_repo, body)
    assert not canary.exists()
    assert not Path(str(canary) + ".json").exists()


def test_reference_never_reaches_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A rejected reference is refused before any Git or filesystem access."""

    calls: list[list[str]] = []
    monkeypatch.setattr(scope_context, "_run_git", lambda _root, args: calls.append(args))  # type: ignore[func-returns-value,misc]
    for reference in ("/etc/passwd", "../../etc/passwd", "Makefile", "$(id)"):
        with pytest.raises(MissionScopeError):
            scope_context.resolve_exact_head_mission_scope(
                _minimal_body(reference), repo_root=tmp_path, head_sha="a" * 40
            )
    assert calls == []


def test_scope_enforcement_code_is_argv_only_shell_free() -> None:
    gate_source = Path(ai_workflow_gate.__file__).read_text(encoding="utf-8")
    helper_source = Path(scope_context.__file__).read_text(encoding="utf-8")
    for source in (gate_source, helper_source):
        assert "shell=True" not in source
        assert "os.system" not in source
        assert "os.popen" not in source
    # Git is invoked with an argv list, never a PR-controlled command string.
    assert '["git", *args]' in helper_source
    assert 'f"show"' not in helper_source
    assert '["show", f"{commit_sha}:{relative_path}"]' in helper_source


# ---------------------------------------------------------------------------
# 4. Exact-head binding
# ---------------------------------------------------------------------------


def test_scope_is_read_from_the_exact_head_commit(scope_repo: Repo) -> None:
    resolved = _resolve(scope_repo, _minimal_body(DRIFT_SCOPE, mission_id="DRIFT_MISSION"))
    assert resolved.head_sha == scope_repo.head
    assert resolved.relative_path == DRIFT_SCOPE
    assert "scripts/ops/ai_workflow_gate.py" in resolved.scope.authorized_paths
    assert validate_mission_scope(["scripts/ops/ai_workflow_gate.py"], resolved.scope) == []
    assert len(resolved.sha256) == SHA256_HEX_LENGTH


def test_resolving_at_the_base_sha_yields_the_base_contract_not_the_head_contract(
    scope_repo: Repo,
) -> None:
    """Same PR body, different commit → different authorization.  No drift."""

    at_head = _resolve(scope_repo, _minimal_body(DRIFT_SCOPE, mission_id="DRIFT_MISSION"))
    at_base = _resolve(
        scope_repo, _minimal_body(DRIFT_SCOPE, mission_id="DRIFT_MISSION"), head_sha=scope_repo.base
    )
    assert at_head.sha256 != at_base.sha256
    assert at_head.head_sha != at_base.head_sha
    assert validate_mission_scope(["scripts/ops/ai_workflow_gate.py"], at_head.scope) == []
    errors = validate_mission_scope(["scripts/ops/ai_workflow_gate.py"], at_base.scope)
    _assert_error(errors, "SCOPE_ESCALATE")


def test_a_dirty_worktree_copy_cannot_move_the_authorization_boundary(
    scope_repo: Repo,
) -> None:
    before = _resolve(scope_repo, _minimal_body(DRIFT_SCOPE, mission_id="DRIFT_MISSION"))
    scope_repo.path_of(DRIFT_SCOPE).write_text(
        _scope_document("DRIFT_MISSION", [UNAUTHORIZED_PATH]), encoding="utf-8"
    )
    after = _resolve(scope_repo, _minimal_body(DRIFT_SCOPE, mission_id="DRIFT_MISSION"))
    assert after.sha256 == before.sha256
    assert after.scope.authorized_paths == before.scope.authorized_paths


def test_scope_must_be_a_regular_tracked_file(scope_repo: Repo) -> None:
    with pytest.raises(MissionScopeReferenceError) as exc_info:
        _resolve(scope_repo, _minimal_body(SYMLINK_SCOPE))
    assert _code(exc_info) == MISSION_SCOPE_REFERENCE_NOT_TRACKED_AT_HEAD


def test_untracked_worktree_scope_is_rejected(scope_repo: Repo) -> None:
    with pytest.raises(MissionScopeReferenceError) as exc_info:
        _resolve(scope_repo, _minimal_body(UNTRACKED_SCOPE))
    assert _code(exc_info) == MISSION_SCOPE_REFERENCE_NOT_TRACKED_AT_HEAD


def test_scope_deleted_at_head_is_rejected(scope_repo: Repo) -> None:
    with pytest.raises(MissionScopeReferenceError) as exc_info:
        _resolve(scope_repo, _minimal_body(DELETED_SCOPE))
    assert _code(exc_info) == MISSION_SCOPE_REFERENCE_FILE_MISSING_AT_HEAD


def test_scope_outside_the_tracked_root_is_never_read(scope_repo: Repo) -> None:
    with pytest.raises(MissionScopeReferenceError) as exc_info:
        _resolve(scope_repo, _minimal_body(OUTSIDE_ROOT))
    assert _code(exc_info) == MISSION_SCOPE_REFERENCE_OUTSIDE_ALLOWED_ROOT


def test_scope_named_relative_to_the_repository_root_is_rejected(tmp_path: Path) -> None:
    """A ``../`` hop out of the checkout never resolves anywhere else."""

    body = _minimal_body("../FootballPrediction/docs/agentic/missions/current.json")
    with pytest.raises(MissionScopeReferenceError) as exc_info:
        scope_context.resolve_exact_head_mission_scope(body, repo_root=tmp_path, head_sha="a" * 40)
    assert _code(exc_info) == MISSION_SCOPE_REFERENCE_TRAVERSAL


@pytest.mark.parametrize("head_sha", ["HEAD", "main", "refs/pull/1/merge", "", "0123456789ab"])
def test_non_full_sha_head_fails_closed(scope_repo: Repo, head_sha: str) -> None:
    with pytest.raises(MissionScopeError):
        _resolve(scope_repo, _minimal_body(MISSION_SCOPE_PATH), head_sha=head_sha)


# ---------------------------------------------------------------------------
# 5. Schema / mission metadata binding
# ---------------------------------------------------------------------------


def test_malformed_scope_json_fails_closed(scope_repo: Repo) -> None:
    with pytest.raises(MissionScopeReferenceError) as exc_info:
        _resolve(scope_repo, _minimal_body(MALFORMED_SCOPE))
    assert _code(exc_info) == MISSION_SCOPE_SCHEMA_INVALID


def test_schema_version_mismatch_fails_closed(scope_repo: Repo) -> None:
    with pytest.raises(MissionScopeError):
        _resolve(scope_repo, _minimal_body(BAD_SCHEMA_SCOPE))


def test_mission_id_mismatch_between_body_and_contract_fails_closed(scope_repo: Repo) -> None:
    body = _minimal_body(MISSION_SCOPE_PATH, mission_id="SOME_OTHER_MISSION")
    with pytest.raises(MissionScopeReferenceError) as exc_info:
        _resolve(scope_repo, body)
    assert _code(exc_info) == MISSION_SCOPE_MISSION_ID_MISMATCH


def test_another_prs_scope_cannot_be_reused(scope_repo: Repo) -> None:
    """A different PR's contract, named under this PR's mission id."""

    body = _minimal_body(OTHER_SCOPE, mission_id=MISSION_ID)
    with pytest.raises(MissionScopeReferenceError) as exc_info:
        _resolve(scope_repo, body)
    assert _code(exc_info) == MISSION_SCOPE_MISSION_ID_MISMATCH

    # Even when the body is consistent with that other contract, it still only
    # authorizes that other mission's paths.
    consistent = _resolve(scope_repo, _minimal_body(OTHER_SCOPE, mission_id="OTHER_MISSION"))
    assert consistent.scope.mission_id == "OTHER_MISSION"
    errors = validate_mission_scope(["Makefile"], consistent.scope)
    _assert_error(errors, "not authorized")


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("Task type", "source-code", MISSION_SCOPE_TASK_TYPE_MISMATCH),
        ("Workflow class", "NORMAL", MISSION_SCOPE_WORKFLOW_CLASS_MISMATCH),
    ],
)
def test_task_type_and_workflow_class_must_match_the_contract(
    scope_repo: Repo, field: str, value: str, code: str
) -> None:
    current = "workflow-governance" if field == "Task type" else "STRICT"
    body = _fixture_body().replace(f"| {field} | {current} |", f"| {field} | {value} |")
    with pytest.raises(MissionScopeReferenceError) as exc_info:
        _resolve(scope_repo, body)
    assert _code(exc_info) == code


# ---------------------------------------------------------------------------
# 6. Changed-path authorization keeps canonical semantics
# ---------------------------------------------------------------------------


def test_authorized_paths_pass_and_unauthorized_paths_fail() -> None:
    scope = _scope()
    assert validate_mission_scope(["Makefile"], scope) == []
    errors = validate_mission_scope([UNAUTHORIZED_PATH], scope)
    _assert_error(errors, "not authorized")


def test_exclusion_overrides_authorization() -> None:
    scope = _scope(
        authorized_paths=["Makefile", "scripts/ops/ai_workflow_gate.py"],
        authorized_prefixes=["scripts/"],
        excluded_paths=["Makefile"],
        excluded_prefixes=["scripts/ops/"],
    )
    assert "explicitly excluded" in validate_mission_scope(["Makefile"], scope)[0]
    assert (
        "explicitly excluded"
        in validate_mission_scope(["scripts/ops/ai_workflow_gate.py"], scope)[0]
    )
    assert validate_mission_scope(["scripts/devops/agent_workflow.py"], scope) == []


def test_excluded_token_overrides_authorization() -> None:
    scope = _scope(authorized_prefixes=["scripts/"], excluded_tokens=["stage_d"])
    assert validate_mission_scope(["scripts/stage_d_run.py"], scope)
    assert validate_mission_scope(["scripts/normal_run.py"], scope) == []


def test_directory_prefix_matching_is_boundary_safe() -> None:
    scope = _scope(authorized_paths=[], authorized_prefixes=["scripts/devops/"])
    assert validate_mission_scope(["scripts/devops/agent_workflow.py"], scope) == []
    errors = validate_mission_scope(["scripts/devops_evil.py"], scope)
    _assert_error(errors, "not authorized")


def test_empty_authorization_fails_closed() -> None:
    with pytest.raises(MissionScopeError):
        _scope(authorized_paths=[], authorized_prefixes=[])


def test_missing_scope_object_fails_closed() -> None:
    errors = validate_mission_scope(["Makefile"], None)
    _assert_error(errors, "current mission scope contract is required")


def test_unknown_scope_fields_fail_closed() -> None:
    payload = mission_scope_payload()
    payload["authorized_everything"] = True
    with pytest.raises(MissionScopeError):
        MissionScope.from_mapping(payload)


# ---------------------------------------------------------------------------
# 7. Gate-level: the remote flag set actually enforces the PR's own scope
# ---------------------------------------------------------------------------


def _patch_gate(monkeypatch: pytest.MonkeyPatch, repo: Repo) -> None:
    monkeypatch.setattr(ai_workflow_gate, "ROOT", repo.path)
    monkeypatch.setattr("scripts.ops.helpers.git_change_helpers.ROOT_HELPER", repo.path)
    monkeypatch.setattr(
        "scripts.ops.ai_workflow_gate.run_governance_growth_gate",
        lambda *_args, **_kwargs: [],
    )


def _run_gate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    repo: Repo,
    *,
    body: str,
    head: str,
    extra: list[str],
) -> tuple[int, str]:
    _patch_gate(monkeypatch, repo)
    body_path = tmp_path / "pr-body.md"
    body_path.write_text(body, encoding="utf-8")
    argv = [
        "--pr-body-file",
        str(body_path),
        "--base-ref",
        repo.base,
        "--head-ref",
        head,
        "--allow-review-pending",
        *extra,
    ]
    code = ai_workflow_gate.main(argv)
    return code, capsys.readouterr().out


def test_gate_remote_flag_set_enforces_the_prs_own_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    gate_repo: Repo,
) -> None:
    body = _fixture_body(reviewed_sha=gate_repo.head)
    code, out = _run_gate(
        tmp_path,
        monkeypatch,
        capsys,
        gate_repo,
        body=body,
        head=gate_repo.head,
        extra=["--enforce-agent-workflow-scope"],
    )
    assert code == 0, out
    for expected in (
        "REMOTE_SCOPE_ENFORCEMENT_ENABLED=YES",
        "REMOTE_SCOPE_REFERENCE_RESOLVED=YES",
        f"REMOTE_SCOPE_REFERENCE_PATH={MISSION_SCOPE_PATH}",
        "REMOTE_SCOPE_BOUND_TO_EXACT_HEAD=YES",
        f"REMOTE_SCOPE_EXACT_HEAD_SHA={gate_repo.head}",
        f"REMOTE_SCOPE_MISSION_ID={MISSION_ID}",
        "REMOTE_SCOPE_WORKFLOW_CLASS=STRICT",
        "REMOTE_SCOPE_SCHEMA_VALID=YES",
        "REMOTE_SCOPE_MISSION_MATCH=YES",
        "REMOTE_SCOPE_CHANGED_PATH_AUTHORIZATION=PASS",
    ):
        assert expected in out, out


def test_gate_without_the_scope_flag_does_not_enforce_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    gate_repo: Repo,
) -> None:
    """Regression guard for the F03-A gap itself."""

    body = _fixture_body(reviewed_sha=gate_repo.head)
    code, out = _run_gate(
        tmp_path,
        monkeypatch,
        capsys,
        gate_repo,
        body=body,
        head=gate_repo.head,
        extra=[],
    )
    assert code == 0, out
    assert "REMOTE_SCOPE_ENFORCEMENT_ENABLED" not in out
    assert "REMOTE_SCOPE_CHANGED_PATH_AUTHORIZATION" not in out


def test_gate_fails_closed_when_a_changed_path_is_not_authorized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    gate_repo: Repo,
) -> None:
    body = _fixture_body(reviewed_sha=gate_repo.head_bad)
    code, out = _run_gate(
        tmp_path,
        monkeypatch,
        capsys,
        gate_repo,
        body=body,
        head=gate_repo.head_bad,
        extra=["--enforce-agent-workflow-scope"],
    )
    assert code != 0
    assert f"REMOTE_SCOPE_REFERENCE_PATH={MISSION_SCOPE_PATH}" in out
    assert "REMOTE_SCOPE_CHANGED_PATH_AUTHORIZATION=FAIL" in out
    assert UNAUTHORIZED_PATH in out


def test_gate_fails_closed_when_the_pr_body_names_no_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    gate_repo: Repo,
) -> None:
    body = _fixture_body(reviewed_sha=gate_repo.head).replace(
        f"| Mission scope contract | `{MISSION_SCOPE_PATH}` |",
        "| Mission scope contract | (not declared) |",
    )
    code, out = _run_gate(
        tmp_path,
        monkeypatch,
        capsys,
        gate_repo,
        body=body,
        head=gate_repo.head,
        extra=["--enforce-agent-workflow-scope"],
    )
    assert code != 0
    assert "REMOTE_SCOPE_REFERENCE_RESOLVED=NO" in out
    assert "REMOTE_SCOPE_BOUND_TO_EXACT_HEAD=NO" in out
    assert "REMOTE_SCOPE_CHANGED_PATH_AUTHORIZATION=FAIL" in out
    assert "MISSION_SCOPE_REFERENCE_OUTSIDE_ALLOWED_ROOT" in out


def test_gate_fails_closed_when_the_named_scope_does_not_exist_at_head(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    gate_repo: Repo,
) -> None:
    body = _fixture_body(reviewed_sha=gate_repo.head).replace(
        f"| Mission scope contract | `{MISSION_SCOPE_PATH}` |",
        _scope_row("docs/agentic/missions/absent.json").splitlines()[0],
    )
    code, out = _run_gate(
        tmp_path,
        monkeypatch,
        capsys,
        gate_repo,
        body=body,
        head=gate_repo.head,
        extra=["--enforce-agent-workflow-scope"],
    )
    assert code != 0
    assert "REMOTE_SCOPE_REFERENCE_RESOLVED=NO" in out
    assert MISSION_SCOPE_REFERENCE_FILE_MISSING_AT_HEAD in out


def test_gate_scope_enforcement_is_not_satisfiable_by_an_explicit_worktree_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    gate_repo: Repo,
) -> None:
    """The PR path never accepts a caller-supplied ``--mission-scope-file``."""

    body = _fixture_body(reviewed_sha=gate_repo.head_bad)
    code, out = _run_gate(
        tmp_path,
        monkeypatch,
        capsys,
        gate_repo,
        body=body,
        head=gate_repo.head_bad,
        extra=[
            "--enforce-agent-workflow-scope",
            "--mission-scope-file",
            MISSION_SCOPE_PATH,
        ],
    )
    assert code != 0
    assert "REMOTE_SCOPE_ENFORCEMENT_ENABLED" not in out


def test_explicit_scope_file_still_binds_the_worktree_copy_to_exact_head(
    monkeypatch: pytest.MonkeyPatch, gate_repo: Repo
) -> None:
    """The local/controlled path keeps its own exact-head equality proof."""

    _patch_gate(monkeypatch, gate_repo)
    scope_path = gate_repo.path_of(MISSION_SCOPE_PATH)
    scope_path.write_text(scope_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    errors = ai_workflow_gate._validate_mission_scope_context(
        _fixture_body(reviewed_sha=gate_repo.head),
        scope_path,
        ai_workflow_gate.load_mission_scope_file(scope_path, repo_root=gate_repo.path),
        resolved_head=gate_repo.head,
        skip_body_checks=False,
    )
    _assert_error(errors, "differ from exact CI HEAD")


# ---------------------------------------------------------------------------
# 8. Event-specific workflow behaviour
# ---------------------------------------------------------------------------


def _workflow_blocks() -> tuple[str, str, str]:
    raw = WORKFLOW_FILE.read_text(encoding="utf-8")
    step = raw[raw.index("      - name: AI Workflow Gate (P0)") :]
    step = step[: step.index("\n      - name:", 1)]
    pr_block, rest = step.split(
        '          elif [ "${GATE_EVENT_NAME}" = "workflow_dispatch" ]; then', maxsplit=1
    )
    dispatch_block, push_block = rest.split(
        '          elif [ "${GATE_EVENT_NAME}" = "push" ]; then', maxsplit=1
    )
    return pr_block, dispatch_block, push_block


def test_pull_request_block_enables_remote_scope_enforcement() -> None:
    pr_block, _dispatch, _push = _workflow_blocks()
    assert "--enforce-agent-workflow-scope" in pr_block
    assert "--mission-scope-file" not in pr_block
    assert "--enforce-agent-workflow-contract" in pr_block
    assert "--block-matrix" in pr_block
    assert "--pr-body-file" in pr_block


def test_non_pr_events_never_require_a_pr_mission_scope() -> None:
    _pr, dispatch_block, push_block = _workflow_blocks()
    for block in (dispatch_block, push_block):
        assert "--enforce-agent-workflow-scope" not in block
        assert "--mission-scope-file" not in block
        assert "--skip-body-checks" in block


def test_pr_scope_enforcement_does_not_downgrade_pr_metadata_checks() -> None:
    pr_block, _dispatch, _push = _workflow_blocks()
    assert "--skip-body-checks" not in pr_block
    assert "--mission-scope-file" not in pr_block
