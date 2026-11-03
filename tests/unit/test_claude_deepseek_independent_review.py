"""Regression tests for the explicit DeepSeek exact-head runner."""

from __future__ import annotations

from argparse import Namespace
from hashlib import sha256
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from scripts.devops import claude_deepseek_independent_review as runner
from scripts.devops import deepseek_receipt_evidence as consumer


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


@pytest.mark.parametrize(
    "failure",
    [
        None,
        runner.DeepSeekReviewError("no verdict"),
        runner.backend.BackendInfrastructureError("timeout"),
    ],
)
def test_retain_invocation_preserves_only_existing_safe_files(monkeypatch, tmp_path, failure):
    args = _args(tmp_path)
    args.retain_invocation = True
    args.evidence_dir.mkdir(mode=0o700)
    previous = args.evidence_dir / "claude-deepseek-raw-prior.json"
    previous.write_text("prior")
    worktree = args.evidence_dir / "claude-deepseek-worktree-current"
    partial = args.evidence_dir / "claude-deepseek-raw-current.json"

    def fake_run(_args):
        worktree.mkdir()
        partial.write_text("already safely written")
        if failure is not None:
            raise failure
        return partial

    monkeypatch.setattr(runner, "_run_review", fake_run)
    monkeypatch.setattr(runner, "_cleanup_invocation", lambda **_: pytest.fail("must retain"))
    if failure is None:
        assert runner.run_review(args) == partial
    else:
        with pytest.raises(type(failure)):
            runner.run_review(args)
    assert worktree.is_dir()
    assert partial.read_text() == "already safely written"
    assert previous.read_text() == "prior"
    assert not list(args.evidence_dir.glob("claude-deepseek-receipt-*"))


def _retained_fixture_repo(tmp_path: Path, real_run):
    """只创建本轮本地 Git 输入，不接触审核认证或网络。"""
    repo = tmp_path / "fixture-repo"
    repo.mkdir()

    def git(*args):
        return (
            real_run(
                [
                    "git",
                    "-c",
                    "core.hooksPath=/dev/null",
                    "-c",
                    "user.name=Offline Fixture",
                    "-c",
                    "user.email=offline@example.invalid",
                    *args,
                ],
                cwd=repo,
                capture_output=True,
                check=True,
            )
            .stdout.decode()
            .strip()
        )

    git("init", "-b", "offline-fixture")
    scope_path = repo / "docs/agentic/missions/OFFLINE_RETAIN_BINDING.json"
    scope_path.parent.mkdir(parents=True)
    scope_path.write_text(
        json.dumps(
            {
                "schema_version": "agentic-mission-scope/v1",
                "mission_id": "OFFLINE_RETAIN_BINDING",
                "task_type": "source-code",
                "workflow_class": "CRITICAL",
                "authorized_paths": ["fixture.py"],
                "authorized_prefixes": [],
                "excluded_paths": [],
                "excluded_prefixes": [],
                "excluded_tokens": [],
                "protected_invariants": ["offline fixture"],
                "forbidden_side_effects": ["no network"],
            }
        )
    )
    registry = repo / "docs/agentic/independent_review_backends.json"
    shutil.copyfile(runner.ROOT / registry.relative_to(repo), registry)
    (repo / "fixture.py").write_text("value = 1\n")
    git("add", ".")
    git("commit", "-m", "offline base")
    base = git("rev-parse", "HEAD")
    (repo / "fixture.py").write_text("value = 2\n")
    git("add", "fixture.py")
    git("commit", "-m", "offline head")
    head = git("rev-parse", "HEAD")
    evidence = tmp_path / "evidence"
    return Namespace(
        repo_root=repo,
        base_sha=base,
        head_sha=head,
        mission_id="OFFLINE_RETAIN_BINDING",
        mission_scope_file=scope_path,
        evidence_dir=evidence,
        retain_invocation=True,
    )


@pytest.fixture
def retained_runtime_fixture(monkeypatch, tmp_path: Path):
    """真实 runner/backend/validator，仅替换凭据读取和 CLI 执行边界。"""
    real_run = runner.subprocess.run
    args = _retained_fixture_repo(tmp_path, real_run)
    binary = tmp_path / "synthetic-claude"
    binary.write_bytes(b"offline fixture; never execute")
    binary.chmod(0o700)
    backend = runner.backend
    monkeypatch.setattr(backend.shutil, "which", lambda _name: str(binary))
    monkeypatch.setattr(backend, "TRUSTED_CLAUDE_BINARY_ROOTS", (tmp_path,))
    monkeypatch.setattr(
        backend,
        "TRUSTED_CLAUDE_BINARY_SHA256",
        frozenset({sha256(binary.read_bytes()).hexdigest()}),
    )
    monkeypatch.setattr(backend, "_secret", lambda _path: "offline-synthetic-secret")
    calls = []
    mode = {"outcome": "PASS", "require_binding_before_cli": False}

    def fake_cli(command, **kwargs):
        if command[0] == "git":
            return real_run(command, **kwargs)
        assert command[0] == str(binary), "unexpected executable at offline boundary"
        if command[1:] == ["--version"]:
            return SimpleNamespace(returncode=0, stdout="2.1.276 (offline fixture)\n")
        settings = Path(command[command.index("--settings") + 1])
        home = Path(kwargs["env"]["HOME"])
        worktree = Path(kwargs["cwd"])
        assert settings.parent == home
        assert settings.read_bytes() == backend.DEDICATED_SETTINGS
        calls.append({"home": home, "worktree": worktree, "command": command})
        if mode["require_binding_before_cli"]:
            binding = json.loads((home.parent / "invocation.json").read_text())
            assert binding["review_run_id"] == worktree.name.rsplit("-", 1)[-1]
            assert binding["worktree"] == str(worktree)
        if mode["outcome"] == "timeout":
            raise backend.subprocess.TimeoutExpired(command, 30, output=b"offline-synthetic-secret")
        if mode["outcome"] == "nonzero":
            return SimpleNamespace(returncode=1, stdout=b"network offline fixture", stderr=b"")
        if mode["outcome"] == "invalid":
            return SimpleNamespace(returncode=0, stdout=b"not-json", stderr=b"")
        result = {
            "protocol_version": runner.PROTOCOL_VERSION,
            "review_result": mode["outcome"],
            "findings": [],
        }
        if mode["outcome"] == "FAIL":
            result["findings"] = [
                {"severity": "P2", "title": "offline finding", "evidence": "fixture.py"}
            ]
        event = {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "session_id": f"offline-session-{len(calls)}",
            "structured_output": result,
            "modelUsage": {"deepseek-flash": {"canonicalModel": "deepseek-flash"}},
        }
        return SimpleNamespace(returncode=0, stdout=json.dumps(event).encode(), stderr=b"")

    monkeypatch.setattr(backend.subprocess, "run", fake_cli)
    return SimpleNamespace(args=args, mode=mode, calls=calls)


@pytest.mark.parametrize("verdict", ["PASS", "FAIL"])
def test_retained_success_command_already_binds_home_to_receipt(retained_runtime_fixture, verdict):
    """成功路径原有 command/settings 关联，不要求随机 HOME 自带 run id。"""
    f = retained_runtime_fixture
    f.mode["outcome"] = verdict
    receipts = []
    for _ in range(2):
        receipt = json.loads(runner.run_review(f.args).read_text())
        command = receipt["provenance"]["reviewer_command"]
        settings = Path(command[command.index("--settings") + 1])
        assert settings.parent == f.calls[-1]["home"]
        assert settings.read_bytes() == runner.backend.DEDICATED_SETTINGS
        assert f.calls[-1]["worktree"].name.endswith(receipt["review_run_id"])
        assert receipt["review_result"] == verdict
        receipts.append(receipt)
    assert receipts[0]["review_run_id"] != receipts[1]["review_run_id"]
    assert f.calls[0]["home"] != f.calls[1]["home"]


@pytest.mark.parametrize("outcome", ["nonzero", "timeout", "invalid"])
def test_retained_failure_binds_each_home_before_cli_without_receipt(
    retained_runtime_fixture, outcome
):
    """同一 evidence 父目录重复失败，原始关联先于CLI落盘且现场均保留。"""
    f = retained_runtime_fixture
    f.mode.update(outcome=outcome, require_binding_before_cli=True)
    calls_expected = 2
    private_dir_mode, private_file_mode = 0o700, 0o600
    for _ in range(calls_expected):
        with pytest.raises(runner.DeepSeekReviewError, match="infrastructure failure"):
            runner.run_review(f.args)
    assert len(f.calls) == calls_expected
    parents = []
    for call in f.calls:
        parent = call["home"].parent
        record = json.loads((parent / "invocation.json").read_text())
        run_id = call["worktree"].name.rsplit("-", 1)[-1]
        assert parent.name == f"claude-deepseek-runtime-{f.args.head_sha[:12]}-{run_id}"
        assert record == {
            "review_run_id": run_id,
            "base_sha": f.args.base_sha,
            "head_sha": f.args.head_sha,
            "mission_id": f.args.mission_id,
            "mission_scope_sha256": runner.sha256_bytes(f.args.mission_scope_file.read_bytes()),
            "worktree": str(call["worktree"]),
            "runtime_parent": str(parent),
        }
        assert parent.stat().st_mode & 0o777 == private_dir_mode
        assert (parent / "invocation.json").stat().st_mode & 0o777 == private_file_mode
        assert (call["home"] / "settings.json").read_bytes() == runner.backend.DEDICATED_SETTINGS
        assert call["worktree"].is_dir()
        assert b"offline-synthetic-secret" not in (parent / "invocation.json").read_bytes()
        parents.append(parent)
    assert parents[0] != parents[1]
    assert not list(f.args.evidence_dir.glob("claude-deepseek-receipt-*"))


def test_retained_chunked_homes_use_same_bound_run_parent(retained_runtime_fixture, monkeypatch):
    f = retained_runtime_fixture
    f.mode["require_binding_before_cli"] = True
    monkeypatch.setattr(runner, "MAX_CHUNK_DIFF_BYTES", 1)
    receipt = json.loads(runner.run_review(f.args).read_text())
    assert receipt["provenance"]["chunked_review"] is True
    assert f.calls
    assert all(call["home"].parent.name.endswith(receipt["review_run_id"]) for call in f.calls)


def test_legacy_review_does_not_create_retained_runtime_parent(retained_runtime_fixture):
    f = retained_runtime_fixture
    f.args.retain_invocation = False
    receipt = runner.run_review(f.args)
    assert receipt.is_file()
    assert not f.calls[0]["home"].exists()
    assert not list(f.args.evidence_dir.glob("claude-deepseek-runtime-*"))
    assert not list(f.args.evidence_dir.glob("claude-deepseek-worktree-*"))


def test_retained_binding_write_failure_prevents_cli_and_receipt(
    retained_runtime_fixture, monkeypatch
):
    f = retained_runtime_fixture
    original_write = runner._write

    def fail_binding(path, data):
        if path.name == "invocation.json":
            raise OSError("offline binding write failure")
        return original_write(path, data)

    monkeypatch.setattr(runner, "_write", fail_binding)
    with pytest.raises(OSError, match="binding write failure"):
        runner.run_review(f.args)
    assert not f.calls
    assert not list(f.args.evidence_dir.glob("claude-deepseek-receipt-*"))
