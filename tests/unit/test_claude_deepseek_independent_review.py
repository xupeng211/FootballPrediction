"""Regression tests for the explicit DeepSeek exact-head runner."""

from __future__ import annotations

from argparse import Namespace
import errno
import json
import os
from pathlib import Path
import stat
from types import SimpleNamespace

import pytest

from scripts.devops import claude_deepseek_independent_review as runner
from scripts.devops import deepseek_receipt_evidence as consumer
from scripts.devops.review_policy import CandidateBinding, ReviewEvidence, evaluate_review_policy
from tests.unit.test_claude_code_deepseek_backend import _approve_test_binary, _safe_digest

_FAILED_CHUNK_INDEX = 1
_FAKE_CHUNK_COUNT = 3
_PRIVATE_FILE_MODE = 0o600
_PRIVATE_DIRECTORY_MODE = 0o700


def test_runner_rejects_non_current_head_before_creating_external_evidence(tmp_path: Path):
    args = Namespace(
        repo_root=Path(__file__).resolve().parents[2],
        base_sha="HEAD^",
        head_sha="HEAD^",
        mission_id="CLAUDE_CODE_DEEPSEEK_INDEPENDENT_REVIEW_BACKEND",
        mission_scope_file=Path(__file__).resolve().parents[2]
        / "docs/agentic/missions/CLAUDE_CODE_DEEPSEEK_INDEPENDENT_REVIEW_BACKEND.json",
        evidence_dir=tmp_path / "evidence",
    )
    with pytest.raises(runner.DeepSeekReviewError, match="current exact HEAD"):
        runner.run_review(args)
    assert not args.evidence_dir.exists()


def _args(tmp_path: Path) -> Namespace:
    return Namespace(repo_root=tmp_path, evidence_dir=tmp_path / "evidence")


def test_runner_removes_only_new_worktree_after_success(monkeypatch, tmp_path: Path):
    args = _args(tmp_path)
    args.evidence_dir.mkdir()
    unrelated = args.evidence_dir / "claude-deepseek-worktree-unrelated"
    unrelated.mkdir()

    def fake_run_review(_args):
        created = _args.evidence_dir / "claude-deepseek-worktree-current"
        created.mkdir()
        receipt = _args.evidence_dir / "claude-deepseek-receipt-current.json"
        receipt.write_text("{}", encoding="utf-8")
        return receipt

    calls: list[list[str]] = []

    def fake_subprocess(command, **_kwargs):
        calls.append(command)
        Path(command[-1]).rmdir()
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(runner, "_run_review", fake_run_review)
    monkeypatch.setattr(runner.subprocess, "run", fake_subprocess)
    receipt = runner.run_review(args)
    assert receipt.exists()
    assert unrelated.exists()
    assert calls == [
        [
            "git",
            "worktree",
            "remove",
            "--force",
            str(args.evidence_dir / "claude-deepseek-worktree-current"),
        ]
    ]


@pytest.mark.parametrize(
    "failure",
    [
        runner.backend.BackendInfrastructureError("timeout"),
        runner.DeepSeekReviewError("validation"),
    ],
)
def test_runner_removes_new_worktree_and_partial_evidence_on_failure(
    monkeypatch, tmp_path: Path, failure
):
    args = _args(tmp_path)
    args.evidence_dir.mkdir()
    retained = args.evidence_dir / "claude-deepseek-raw-prior.json"
    retained.write_text("prior", encoding="utf-8")

    def fake_run_review(_args):
        (_args.evidence_dir / "claude-deepseek-worktree-current").mkdir()
        (_args.evidence_dir / "claude-deepseek-raw-current.json").write_text(
            "partial", encoding="utf-8"
        )
        raise failure

    def fake_subprocess(command, **_kwargs):
        Path(command[-1]).rmdir()
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(runner, "_run_review", fake_run_review)
    monkeypatch.setattr(runner.subprocess, "run", fake_subprocess)
    with pytest.raises(type(failure)):
        runner.run_review(args)
    assert retained.exists()
    assert not (args.evidence_dir / "claude-deepseek-worktree-current").exists()
    assert not (args.evidence_dir / "claude-deepseek-raw-current.json").exists()


def test_runner_cleanup_failure_removes_receipt_and_returns_controlled_error(
    monkeypatch, tmp_path: Path
):
    args = _args(tmp_path)
    args.evidence_dir.mkdir()

    def fake_run_review(_args):
        (_args.evidence_dir / "claude-deepseek-worktree-current").mkdir()
        receipt = _args.evidence_dir / "claude-deepseek-receipt-current.json"
        receipt.write_text("{}", encoding="utf-8")
        return receipt

    monkeypatch.setattr(runner, "_run_review", fake_run_review)
    monkeypatch.setattr(
        runner.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=1)
    )
    with pytest.raises(runner.DeepSeekReviewError, match="worktree cleanup failed"):
        runner.run_review(args)
    assert not (args.evidence_dir / "claude-deepseek-receipt-current.json").exists()


def test_backend_failure_exposes_only_allowlisted_classification():
    assert (
        runner._safe_backend_failure_code(
            runner.backend.BackendInfrastructureError("AUTH_FAILURE: private detail")
        )
        == "AUTH_FAILURE"
    )


def test_chunked_receipt_prompt_bytes_hash_without_double_encoding():
    """The chunk aggregate prompt is already canonical bytes at receipt construction."""

    prompt = b'{"manifest":"chunked"}'
    assert runner._canonical_prompt_bytes(prompt) is prompt
    assert runner.sha256_bytes(runner._canonical_prompt_bytes(prompt)) == runner.sha256_bytes(
        prompt
    )


def test_canonical_prompt_bytes_encodes_text_once():
    assert runner._canonical_prompt_bytes("chunked") == b"chunked"
    assert (
        runner._safe_backend_failure_code(
            runner.backend.BackendInfrastructureError("unexpected sensitive detail")
        )
        == "CLI_RUNTIME_FAILURE"
    )


def test_chunked_consumer_accepts_command_with_canonical_empty_tools_argument(
    monkeypatch, tmp_path: Path
):
    """Chunked receipts retain the required empty value after ``--tools``."""

    receipt = {
        "protocol_version": "INDEPENDENT_REVIEW_PROTOCOL_V1",
        "review_backend": "claude-code-deepseek",
        "requested_model": "deepseek-flash",
        "resolved_model": "deepseek-flash",
        "base_sha": "a" * 40,
        "head_sha": "b" * 40,
        "diff_sha256": "d" * 64,
        "mission_id": "MISSION",
        "mission_scope_sha256": "c" * 64,
        "review_run_id": "a",
        "review_result": "PASS",
        "findings": [],
        "finding_counts_by_severity": {"P0": 0, "P1": 0, "P2": 0, "P3": 0},
        "integrity": {"receipt_payload_sha256": "ok"},
        "provenance": {
            "chunked_review": True,
            "reviewer_command": ["claude", "--tools", ""],
            "command_sha256": "d" * 64,
            "claude_cli_version": "2.1.276",
            "claude_binary_sha256": "e" * 64,
            "settings_sha256": "f" * 64,
            "provider_endpoint": "https://api.deepseek.com/anthropic",
            "session_id": "session",
        },
    }
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir(mode=0o700)
    path = evidence_dir / "claude-deepseek-receipt-bbbbbbbbbbbb-a.json"
    path.write_text(__import__("json").dumps(receipt), encoding="utf-8")
    registry = {
        "claude-code-deepseek": {
            "status": "active",
            "allowed_requested_models": ["deepseek-flash"],
            "required_provenance_fields": list(receipt["provenance"].keys())[1:],
        }
    }
    monkeypatch.setattr(consumer, "load_backend_registry", lambda _path: registry)
    monkeypatch.setattr(consumer, "receipt_payload_sha256", lambda _value: "ok")
    monkeypatch.setattr(
        consumer,
        "validate_result",
        lambda _value: {
            "review_result": "PASS",
            "findings": [],
            "finding_counts_by_severity": receipt["finding_counts_by_severity"],
        },
    )
    monkeypatch.setattr(consumer, "sha256_bytes", lambda _value: "d" * 64)
    monkeypatch.setattr(consumer, "validate_receipt", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        consumer.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(stdout=b"diff")
    )
    top = {"chunks": [], "manifest": {"chunks": []}}
    raw = evidence_dir / "claude-deepseek-raw-bbbbbbbbbbbb-a.json"
    final = evidence_dir / "claude-deepseek-final-bbbbbbbbbbbb-a.json"
    raw.write_text(__import__("json").dumps(top), encoding="utf-8")
    final.write_bytes(
        consumer.canonical_json(
            {
                "protocol_version": "INDEPENDENT_REVIEW_PROTOCOL_V1",
                "review_result": "PASS",
                "findings": [],
            }
        )
    )
    raw.chmod(0o600)
    final.chmod(0o600)
    receipt["raw_output_sha256"] = receipt["final_result_sha256"] = "d" * 64
    path.write_text(__import__("json").dumps(receipt), encoding="utf-8")
    path.chmod(0o600)
    result = consumer._deepseek_receipt_evidence(
        path,
        repo_root=repo_root,
        expected_base="a" * 40,
        expected_head="b" * 40,
        expected_mission_id="MISSION",
        expected_scope_hash="c" * 64,
    )
    assert result.trusted is True


def test_chunked_consumer_rejects_incomplete_or_repo_local_artifacts(tmp_path: Path):
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir(mode=0o700)
    artifact = evidence_dir / "chunk.json"
    artifact.write_text("{}", encoding="utf-8")
    artifact.chmod(0o644)
    with pytest.raises(ValueError, match="invalid chunk artifact metadata"):
        consumer._assert_external_artifact(
            artifact, repo_root=tmp_path / "repo", kind="chunk artifact"
        )

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    local = repo_root / "receipt.json"
    local.write_text("{}", encoding="utf-8")
    local.chmod(0o600)
    with pytest.raises(ValueError, match="outside repository"):
        consumer._assert_external_artifact(local, repo_root=repo_root, kind="receipt")


@pytest.mark.parametrize("oversized_chunk", [0, 1])
def test_all_chunk_prompts_are_bounded_before_any_provider_call(
    monkeypatch, tmp_path: Path, oversized_chunk
):
    diff = b"diff --git a/a b/a\n" + b"+line\n" * 7000
    prompts = []
    calls = []

    def prompt(**kwargs):
        index = kwargs["chunk"].index
        prompts.append(index)
        return "x" * (runner.MAX_CHUNK_PROMPT_BYTES + 1) if index == oversized_chunk else "small"

    monkeypatch.setattr(runner, "_chunk_prompt", prompt)
    monkeypatch.setattr(runner.backend, "run", lambda **kwargs: calls.append(kwargs))
    with pytest.raises(runner.DeepSeekReviewError, match="canonical byte limit"):
        runner._run_chunked_review(
            diff=diff,
            base="a" * 40,
            head="b" * 40,
            scope=SimpleNamespace(mission_id="MISSION"),
            scope_sha="c" * 64,
            worktree=tmp_path,
        )
    assert prompts == [0, 1]
    assert calls == []


def test_full_inventory_is_never_truncated_to_fit_prompt_limit(monkeypatch, tmp_path: Path):
    path_count = 300
    diff = b"".join(
        f"diff --git a/{index:04d}-{'x' * 120} b/{index:04d}-{'x' * 120}\n+line\n".encode()
        for index in range(path_count)
    )
    manifest = runner.plan(
        diff,
        base_sha="a" * 40,
        head_sha="b" * 40,
        mission_id="MISSION",
        mission_scope_sha256="c" * 64,
    )
    assert len(manifest.full_changed_paths) == path_count
    first = manifest.chunks[0]
    prompt = runner._chunk_prompt(
        chunk=first, source=diff[first.start : first.end], manifest=manifest, scope_sha="c" * 64
    )
    assert len(prompt.encode()) > runner.MAX_CHUNK_PROMPT_BYTES
    assert manifest.full_changed_paths[-1] in prompt
    calls = []
    monkeypatch.setattr(runner.backend, "run", lambda **kwargs: calls.append(kwargs))
    with pytest.raises(runner.DeepSeekReviewError, match="canonical byte limit"):
        runner._run_chunked_review(
            diff=diff,
            base="a" * 40,
            head="b" * 40,
            scope=SimpleNamespace(mission_id="MISSION"),
            scope_sha="c" * 64,
            worktree=tmp_path,
        )
    assert calls == []


@pytest.mark.parametrize("severity", [None, "P2"])
def test_chunked_runner_preserves_full_coverage_and_verdict_without_extra_calls(
    monkeypatch, tmp_path: Path, severity
):
    diff = (
        b"diff --git a/source b/source\n" + b"+line\n" * 7000 + b"diff --git a/test b/test\n+test\n"
    )
    calls = []

    def fake_run(*, prompt, cwd):
        calls.append((prompt, cwd))
        result = {
            "protocol_version": runner.PROTOCOL_VERSION,
            "review_result": "FAIL" if severity else "PASS",
            "findings": [{"severity": severity, "title": "risk", "evidence": "source"}]
            if severity
            else [],
        }
        execution = SimpleNamespace(
            command=("offline-test-double", prompt),
            resolved_model="deepseek-flash",
            cli_version="2.1.278",
            binary_sha256="d" * 64,
            settings_sha256="e" * 64,
            endpoint="https://api.deepseek.com/anthropic",
            session_id=f"offline-session-{len(calls)}",
        )
        return runner.canonical_json(result), result, execution

    monkeypatch.setattr(runner.backend, "run", fake_run)
    _raw, result, trusted = runner._run_chunked_review(
        diff=diff,
        base="a" * 40,
        head="b" * 40,
        scope=SimpleNamespace(mission_id="MISSION"),
        scope_sha="c" * 64,
        worktree=tmp_path,
    )
    expected_chunk_count = 2
    assert len(calls) == len(trusted) == expected_chunk_count
    assert b"".join(item["source"] for item in trusted) == diff
    assert all('Full PR changed paths: ["source","test"]' in prompt for prompt, _cwd in calls)
    assert result["review_result"] == ("FAIL" if severity else "PASS")
    if severity:
        assert result["finding_counts_by_severity"][severity] == len(trusted)


def test_chunked_runner_does_not_retry_infrastructure_failure(monkeypatch, tmp_path: Path):
    calls = []

    def fail(**kwargs):
        calls.append(kwargs)
        raise runner.backend.BackendInfrastructureError("timeout")

    monkeypatch.setattr(runner.backend, "run", fail)
    with pytest.raises(runner.DeepSeekReviewError, match="chunk 0 infrastructure failure"):
        runner._run_chunked_review(
            diff=b"diff --git a/a b/a\n" + b"+line\n" * 7000,
            base="a" * 40,
            head="b" * 40,
            scope=SimpleNamespace(mission_id="MISSION"),
            scope_sha="c" * 64,
            worktree=tmp_path,
        )
    assert len(calls) == 1


def _offline_failure_setup(monkeypatch, tmp_path, *, chunked=False, quality=False):
    """Exercise the real backend/runner using only local process substitutes."""
    repo = tmp_path / "repo"
    repo.mkdir()
    scope_path = "docs/agentic/missions/OFFLINE_TEST.json"
    scope = repo / scope_path
    scope.parent.mkdir(parents=True)
    scope.write_bytes(b"{}")
    args = Namespace(
        repo_root=repo,
        base_sha="a" * 40,
        head_sha="b" * 40,
        mission_id="OFFLINE_TEST",
        mission_scope_file=scope,
        evidence_dir=tmp_path / "evidence",
    )
    args.evidence_dir.mkdir(mode=0o700)
    prior = args.evidence_dir / "claude-deepseek-raw-prior.json"
    prior.write_bytes(b"prior evidence")
    binary = tmp_path / "claude"
    binary.write_bytes(b"offline fake cli")
    _approve_test_binary(monkeypatch, binary)
    monkeypatch.setattr(runner.backend, "_secret", lambda _path: "synthetic-secret")
    monkeypatch.setattr(
        runner,
        "load_mission_scope_file",
        lambda *_a, **_kw: SimpleNamespace(mission_id="OFFLINE_TEST"),
    )
    monkeypatch.setattr(runner, "mission_scope_relative_path", lambda *_a: scope_path)
    diff = b"diff --git a/a b/a\n" + b"+line\n" * (14000 if chunked else 1)
    calls = []

    def git(_root, *argv, **_kwargs):
        if argv[0] == "rev-parse":
            return "a" * 40 if argv[1].startswith("a" * 40) else "b" * 40
        if argv[:2] == ("worktree", "add"):
            Path(argv[3]).mkdir()
            return ""
        responses = {"status": "", "show": b"{}", "diff": diff}
        assert argv[0] in responses, "unexpected Git call"
        return responses[argv[0]]

    def invoke(command, **_kwargs):
        if command[:3] == ["git", "worktree", "remove"]:
            Path(command[-1]).rmdir()
            return SimpleNamespace(returncode=0)
        if command[1:] == ["--version"]:
            return SimpleNamespace(stdout="2.1.278 (Claude Code)")
        calls.append(command[-1])
        if not chunked or len(calls) == _FAILED_CHUNK_INDEX + 1:
            if not quality:
                return SimpleNamespace(
                    returncode=7, stdout=b"partial", stderr=b"Authorization: Bearer private-token"
                )
            result = {
                "protocol_version": runner.PROTOCOL_VERSION,
                "review_result": "FAIL",
                "findings": [{"severity": "P2", "title": "placeholder", "evidence": "placeholder"}],
            }
        else:
            result = {
                "protocol_version": runner.PROTOCOL_VERSION,
                "review_result": "PASS",
                "findings": [],
            }
        event = {
            "is_error": False,
            "session_id": f"offline-{len(calls)}",
            "structured_output": result,
            "modelUsage": {"deepseek-flash": {"canonicalModel": "deepseek-flash"}},
        }
        return SimpleNamespace(returncode=0, stdout=json.dumps(event).encode(), stderr=b"")

    monkeypatch.setattr(runner, "_git", git)
    monkeypatch.setattr(runner.subprocess, "run", invoke)
    return args, diff, calls


def _read_diagnostic(args):
    paths = list(args.evidence_dir.glob("review-failure-deepseek-*.json"))
    assert len(paths) == 1
    payload = json.loads(paths[0].read_bytes())
    unsigned = dict(payload)
    digest = unsigned.pop("payload_sha256")
    assert digest == runner.sha256_bytes(runner.canonical_json(unsigned))
    assert paths[0].stat().st_mode & 0o777 == _PRIVATE_FILE_MODE
    assert args.evidence_dir.stat().st_mode & 0o777 == _PRIVATE_DIRECTORY_MODE
    assert payload["artifact_kind"] == "independent-review-failure-diagnostic/v1"
    assert payload["head_sha"] == args.head_sha
    assert payload["base_sha"] == args.base_sha
    assert payload["mission_scope_sha256"] == runner.sha256_bytes(b"{}")
    assert payload["mission_id"] == args.mission_id
    assert not list(args.evidence_dir.glob("claude-deepseek-receipt-*"))
    assert not list(args.evidence_dir.glob("claude-deepseek-worktree-*"))
    assert (args.evidence_dir / "claude-deepseek-raw-prior.json").read_bytes() == b"prior evidence"
    for marker in ("Authorization", "private-token", "synthetic-secret", "placeholder", "partial"):
        assert marker not in paths[0].read_text()
    return paths[0], payload


def test_invalid_chunk_aborts_run_without_aggregate(monkeypatch, tmp_path):
    args, diff, calls = _offline_failure_setup(monkeypatch, tmp_path, chunked=True, quality=True)
    with pytest.raises(runner.DeepSeekReviewError, match="INVALID_STRUCTURED_OUTPUT"):
        runner.run_review(args)
    _path, payload = _read_diagnostic(args)
    manifest = runner.plan(
        diff,
        base_sha=args.base_sha,
        head_sha=args.head_sha,
        mission_id=args.mission_id,
        mission_scope_sha256=runner.sha256_bytes(b"{}"),
    )
    assert len(calls) == _FAILED_CHUNK_INDEX + 1
    assert payload["chunk_index"] == 1
    assert payload["chunk_count"] == len(manifest.chunks) == _FAKE_CHUNK_COUNT
    assert payload["manifest_sha256"] == manifest.sha256
    assert payload["chunk_source_sha256"] == manifest.chunks[1].source_sha256
    assert payload["prompt_sha256"] == runner.sha256_bytes(calls[1].encode())
    assert payload["process_digest"]["returncode"] == 0
    assert payload["process_digest_status"] == "VALID"


@pytest.mark.parametrize("chunked", [True, False])
def test_failure_diagnostic_survives_cleanup(monkeypatch, tmp_path, chunked):
    args, diff, calls = _offline_failure_setup(monkeypatch, tmp_path, chunked=chunked)
    with pytest.raises(runner.DeepSeekReviewError, match="UNKNOWN_NONZERO_EXIT"):
        runner.run_review(args)
    path, payload = _read_diagnostic(args)
    assert payload["diff_sha256"] == runner.sha256_bytes(diff)
    assert payload["process_digest"]["returncode"] == _safe_digest()["returncode"]
    assert payload["process_digest"]["stdout_bytes"] == len(b"partial")
    assert payload["process_digest"]["stderr_bytes"] == len(b"Authorization: Bearer private-token")
    assert payload["process_digest"]["elapsed_seconds"] >= 0
    assert payload["process_digest_status"] == "VALID"
    assert payload["chunked"] is chunked
    assert len(calls) == (2 if chunked else 1)
    assert payload["cleanup_status"] == "COMPLETE"
    assert set(payload["toolchain_sha256"]) == {"runner", "backend", "protocol"}
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        runner._write_failure_diagnostic(args.evidence_dir, path.name, payload)
    assert path.read_bytes() == original
    link = args.evidence_dir / ("review-failure-deepseek-" + "c" * 12 + "-" + "d" * 32 + ".json")
    link.symlink_to(path)
    with pytest.raises(FileExistsError):
        runner._write_failure_diagnostic(args.evidence_dir, link.name, payload)
    assert path.read_bytes() == original
    assert not list(args.evidence_dir.glob(".*.tmp"))
    for observed, expected in [
        (None, "MISSING"),
        ({}, "INVALID"),
        ({"stdout_bytes": "secret"}, "INVALID"),
    ]:

        def missing(_observed=observed, **_kwargs):
            raise runner.backend.BackendInfrastructureError(
                "CLI_RUNTIME_FAILURE", process_digest=_observed
            )

        monkeypatch.setattr(runner.backend, "run", missing)
        with pytest.raises(runner.DeepSeekReviewError) as raised:
            runner._invoke_review(prompt="private prompt", worktree=args.repo_root)
        assert raised.value.diagnostic["process_digest_status"] == expected
        assert raised.value.diagnostic["process_digest"] is None
        assert "secret" not in json.dumps(raised.value.diagnostic)


@pytest.mark.parametrize("failure_stage", ["before_write", "during_write"])
def test_diagnostic_write_failure_preserves_no_verdict(
    monkeypatch, tmp_path, capsys, failure_stage
):
    stages = (
        ("before_write",)
        if failure_stage == "before_write"
        else ("file_fsync", "publish", "directory_fsync")
    )
    for stage in stages:
        case = tmp_path / stage
        case.mkdir()
        with monkeypatch.context() as patch:
            args, _diff, _calls = _offline_failure_setup(patch, case)

            def fail(
                *_args,
                _error_code=errno.EACCES if stage == "before_write" else errno.EIO,
                **_kwargs,
            ):
                raise OSError(_error_code, "Authorization: synthetic-secret private-token")

            if stage == "before_write":
                patch.setattr(runner, "_write_failure_diagnostic", fail)
            elif stage == "publish":
                patch.setattr(runner.os, "link", fail)
            else:
                original_fsync = runner.os.fsync

                def fail_selected_fsync(fd, _stage=stage, _fsync=original_fsync):
                    is_directory = stat.S_ISDIR(os.fstat(fd).st_mode)
                    if is_directory == (_stage == "directory_fsync"):
                        fail()
                    _fsync(fd)

                patch.setattr(runner.os, "fsync", fail_selected_fsync)
            with pytest.raises(runner.DeepSeekReviewError, match="UNKNOWN_NONZERO_EXIT"):
                runner.run_review(args)
            output = capsys.readouterr().err
            assert "DIAGNOSTIC_WRITE_FAILED" in output
            assert "private-token" not in output
            assert "Authorization" not in output
            assert "synthetic-secret" not in output
            payload = json.loads(output.split("DEEPSEEK_REVIEW_DIAGNOSTIC=", 1)[1])
            assert payload["process_digest"]["returncode"] == _safe_digest()["returncode"]
            assert not list(args.evidence_dir.glob("review-failure-*"))
            assert not list(args.evidence_dir.glob(".*.tmp"))
            assert not list(args.evidence_dir.glob("claude-deepseek-worktree-*"))
            assert not list(args.evidence_dir.glob("claude-deepseek-receipt-*"))


def test_cleanup_failure_retains_primary_diagnostic(monkeypatch, tmp_path):
    args, _diff, _calls = _offline_failure_setup(monkeypatch, tmp_path)
    cleanup = runner._cleanup_invocation

    def fail_cleanup(**kwargs):
        assert cleanup(**kwargs) is None
        return OSError("private cleanup text")

    monkeypatch.setattr(runner, "_cleanup_invocation", fail_cleanup)
    with pytest.raises(runner.DeepSeekReviewError, match="UNKNOWN_NONZERO_EXIT"):
        runner.run_review(args)
    _path, payload = _read_diagnostic(args)
    assert payload["cleanup_status"] == "FAILED"
    assert payload["process_digest"]["returncode"] == _safe_digest()["returncode"]
    assert payload["error_code"] == "CLI_RUNTIME_FAILURE:UNKNOWN_NONZERO_EXIT"


def test_diagnostic_is_not_receipt_and_cannot_satisfy_policy(monkeypatch, tmp_path):
    args, diff, _calls = _offline_failure_setup(monkeypatch, tmp_path)
    with pytest.raises(runner.DeepSeekReviewError):
        runner.run_review(args)
    path, _payload = _read_diagnostic(args)
    candidate = CandidateBinding(
        args.base_sha,
        args.head_sha,
        runner.sha256_bytes(diff),
        args.mission_id,
        runner.sha256_bytes(b"{}"),
    )
    for artifact in (path, args.evidence_dir / "missing-receipt.json"):
        facts = consumer._deepseek_receipt_evidence(
            artifact,
            repo_root=args.repo_root,
            expected_base=args.base_sha,
            expected_head=args.head_sha,
            expected_mission_id=args.mission_id,
            expected_scope_hash=candidate.mission_scope_sha256,
        )
        assert facts.result == "NO_VERDICT"
        assert not facts.trusted
        codex = ReviewEvidence(
            "codex-cli",
            True,
            "PASS",
            args.base_sha,
            args.head_sha,
            candidate.diff_sha256,
            args.mission_id,
            candidate.mission_scope_sha256,
            {"P0": 0, "P1": 0, "P2": 0, "P3": 0},
        )
        outcome = evaluate_review_policy(
            "CRITICAL",
            candidate,
            [codex, facts],
            backend_eligibility={
                "codex-cli": frozenset({"CRITICAL"}),
                "claude-code-deepseek": frozenset({"CRITICAL"}),
            },
        )
        assert outcome.status != "SATISFIED"
