"""Stage D 独立收据、真实子进程设置和既有 Harness 停止证明的离线回归。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import os
import subprocess
import sys
import uuid

import pytest

from scripts.devops import agent_workflow
from scripts.devops import claude_deepseek_independent_review as runner
from scripts.devops import deepseek_low_effort as low
from scripts.devops import deepseek_receipt_evidence as consumer
from scripts.devops.independent_review_protocol import canonical_json, sha256_bytes
from tests.unit.test_claude_deepseek_independent_review import _retained_fixture_repo

_FAKE_CLIENT = """
import json, os, sys, time, uuid
from pathlib import Path

if "--version" in sys.argv:
    print("2.1.276 (Claude Code)")
    sys.exit(0)
time.sleep(.04)
home = Path(os.environ["HOME"])
cwd = os.getcwd()
session = str(uuid.uuid4())
level = os.environ.get("CLAUDE_CODE_EFFORT_LEVEL", "high")
mode = Path(__file__).with_suffix(".mode").read_text()
if mode == "repeat":
    session = "aaaaaaaa-1111-2222-3333-1234567890ab"
def row(kind, content):
    return {"cwd":cwd, "sessionId":session, "type":kind, "message":content}
rows = [row("user", {"content":sys.argv[-1]}),
        dict(row("assistant", {"model":"deepseek-flash"}), effort=level)]
if level == "low":
    if mode == "fast-exit":
        sys.exit(0)
    if mode == "timeout":
        time.sleep(3)
    if mode == "mixed":
        rows.append(dict(row("assistant", {"model":"deepseek-flash"}), effort="high"))
    if mode == "conflict":
        rows[-1]["perTurnEffort"] = "high"
    if mode == "empty":
        rows[-1]["message"]["model"] = "<synthetic>"
    if mode == "leak":
        print(os.environ["ANTHROPIC_API_KEY"], file=sys.stderr)
    if mode == "auth":
        print("authentication_error", file=sys.stderr)
        sys.exit(23)
    if mode == "cap":
        print(json.dumps({"type":"result","subtype":"error_during_execution","is_error":True, "errors":[
            "Claude's response exceeded the 32000 output token maximum. "
            "To configure this behavior, set the CLAUDE_CODE_MAX_OUTPUT_TOKENS environment variable."]}))
        sys.exit(1)
    if mode == "wrong-session":
        rows[-1]["sessionId"] = str(uuid.uuid4())
folder = home/".claude"/"projects"/"review"
folder.mkdir(parents=True)
trace = folder/(session+".jsonl")
trace.write_text("".join(json.dumps(v)+"\\n" for v in rows))
trace.chmod(0o600)
findings = [] if mode not in ("P0","P1","P2","P3") or level != "low" else [
    {"severity":mode, "title":"offline finding","evidence":"fixture.py"}]
result = {"protocol_version":"INDEPENDENT_REVIEW_PROTOCOL_V1","review_result":
          "FAIL" if findings and mode != "P3" else "PASS", "findings":findings}
print(json.dumps({"is_error":False,"type":"result","subtype":"success","structured_output":result,
                  "session_id":session,"modelUsage":{"deepseek-flash":{"canonicalModel":"deepseek-flash"}}}))
"""


@pytest.fixture
def controller(tmp_path, monkeypatch):
    # 仓库不拥有另一套进程监护器。完整集成在挂载已安装 Harness 的禁网环境中验证。
    runtime = None

    def supervised(*args):
        nonlocal runtime
        if runtime is None:
            runtime = pytest.importorskip("harness.factory_runtime").LocalRuntime()
        return runtime._supervised_review_step(*args)

    def stop(*args):
        return pytest.importorskip("harness.appserver_process").validate_supervised_stop(*args)

    args = _retained_fixture_repo(tmp_path, subprocess.run)
    old = args.mission_scope_file
    scope = json.loads(old.read_bytes())
    scope["mission_id"] = low.MISSION
    args.mission_scope_file = old.with_name(low.MISSION + ".json")
    args.mission_scope_file.write_bytes(canonical_json(scope))
    args.mission_id = low.MISSION
    (args.repo_root / "fixture.py").write_text(
        "".join(f"# {'x' * 72} {index}\n" for index in range(1260))
    )

    def git(*parts):
        return subprocess.check_output(
            [
                "git",
                "-c",
                "user.name=Offline Fixture",
                "-c",
                "user.email=offline@example.invalid",
                *parts,
            ],
            cwd=args.repo_root,
        )

    git("add", ".")
    git("commit", "-qm", "offline four-packet candidate")
    args.head_sha = git("rev-parse", "HEAD").decode().strip()
    diff = git("diff", "--binary", "--no-ext-diff", args.base_sha + "..." + args.head_sha)
    scope_sha = sha256_bytes(args.mission_scope_file.read_bytes())
    manifest = runner.plan(
        diff,
        base_sha=args.base_sha,
        head_sha=args.head_sha,
        mission_id=low.MISSION,
        mission_scope_sha256=scope_sha,
        repo_root=args.repo_root,
    )
    prompts = [
        runner._chunk_prompt(
            chunk=c, source=diff[c.start : c.end], manifest=manifest, scope_sha=scope_sha
        ).encode()
        for c in manifest.chunks
    ]
    target = low.frozen_target(args.repo_root, manifest, diff, prompts)
    binary = tmp_path / "claude"
    binary.write_text("#!" + sys.executable + "\n" + _FAKE_CLIENT)
    binary.chmod(0o700)
    mode = binary.with_suffix(".mode")
    mode.write_text("pass")
    monkeypatch.setattr(runner.backend, "TRUSTED_CLAUDE_BINARY_ROOTS", (tmp_path,))
    monkeypatch.setattr(
        runner.backend, "TRUSTED_CLAUDE_BINARY_SHA256", {sha256_bytes(binary.read_bytes())}
    )
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("CLAUDE_CODE_EFFORT_LEVEL", "low")
    monkeypatch.setattr(runner.backend, "_secret", lambda _path: "synthetic-fixture-token")
    trusted = tmp_path / "controller-originals"
    trusted.mkdir(mode=0o700)
    args.evidence_dir.mkdir(mode=0o700)
    pilot = low.LowReview(
        uuid.uuid4().hex, trusted, args.evidence_dir, canonical_json(target), supervised, stop
    )
    return args, pilot, mode


def _read(args, path, pilot):
    return consumer._deepseek_receipt_evidence(
        path,
        repo_root=args.repo_root,
        expected_base=args.base_sha,
        expected_head=args.head_sha,
        expected_mission_id=args.mission_id,
        expected_scope_hash=sha256_bytes(args.mission_scope_file.read_bytes()),
        pilot=pilot,
    )


def test_real_children_and_retained_originals(controller, capsys):
    args, pilot, _ = controller
    path = runner.run_review(args, pilot=pilot)
    receipt = json.loads(path.read_bytes())
    assert receipt["receipt_version"] == low.VERSION
    assert _read(args, path, pilot).trusted
    assert not _read(args, path, None).trusted
    gate = agent_workflow.build_parser().parse_args(
        [
            "merge-ready",
            "--repo-root",
            str(args.repo_root),
            "--base-sha",
            args.base_sha,
            "--head-sha",
            args.head_sha,
            "--mission-id",
            args.mission_id,
            "--mission-scope-file",
            str(args.mission_scope_file),
            "--deepseek-receipt",
            str(path),
            "--local-preflight-json",
            str(pilot.trusted_dir / "no-preflight"),
            "--json",
        ]
    )

    def gate_lane(context):
        assert agent_workflow.merge_ready_command(gate, pilot=context) == 1
        # 忽略其他独立门禁的未满足项，只核对本次 DeepSeek 是否被接受。
        return json.loads(capsys.readouterr().out)["satisfied_review_backends"]

    assert runner.backend.BACKEND_ID in gate_lane(pilot)
    assert runner.backend.BACKEND_ID not in gate_lane(None)
    originals = sorted(pilot.trusted_dir.glob("chunk-*.stdout"))
    assert [json.loads(p.read_bytes())["effort_request"] for p in originals] == [
        [],
        ["low"],
        [],
        [],
    ]
    assert all(
        b"synthetic-fixture-token" not in p.read_bytes() for p in pilot.trusted_dir.iterdir()
    )
    assert not _read(args, path, replace(pilot, run_id="3" * 32)).trusted

    for mutate in (
        lambda v: v.update(receipt_version="independent-review-receipt/v1"),
        lambda v: v["provenance"].update(chunked_review=False),
    ):
        wrong = json.loads(path.read_bytes())
        mutate(wrong)
        wrong["integrity"]["receipt_payload_sha256"] = runner.receipts.receipt_payload_sha256(wrong)
        path.write_bytes(canonical_json(wrong))
        assert not _read(args, path, pilot).trusted
        assert runner.backend.BACKEND_ID not in gate_lane(pilot)
        assert runner.backend.BACKEND_ID not in gate_lane(None)
        path.write_bytes(canonical_json(receipt))
    for original in [
        originals[1],
        pilot.trusted_dir / "chunk-0.stdout.process.jsonl",
        pilot.trusted_dir / "chunk-2.stop-ref",
        pilot.trusted_dir / "chunk-3.seal",
        next(args.evidence_dir.glob("*runtime*/*/.claude/projects/*/*.jsonl")),
    ]:
        before = original.read_bytes()
        original.write_bytes(before + b" ")
        assert not _read(args, path, pilot).trusted, original.name
        original.write_bytes(before)
    assert _read(args, path, pilot).trusted
    with pytest.raises((runner.DeepSeekReviewError, FileExistsError)):
        runner.run_review(args, pilot=pilot)
    assert len(list(pilot.trusted_dir.glob("*.started"))) == low.CHUNKS


@pytest.mark.parametrize(
    "mode",
    ["empty", "mixed", "conflict", "wrong-session", "repeat", "leak", "auth", "cap", "fast-exit"],
)
def test_refuse_failed_chunk_before_next_dispatch(controller, mode):
    args, pilot, setting = controller
    setting.write_text(mode)
    with pytest.raises((ValueError, runner.DeepSeekReviewError)) as error:
        runner.run_review(args, pilot=pilot)
    if mode == "cap":
        assert "OUTPUT_TOKEN_LIMIT" in str(error.value)
    assert len(list(pilot.trusted_dir.glob("*.started"))) == low.LOW_INDEX + 1
    assert not list(args.evidence_dir.glob("*receipt*"))
    assert b"synthetic-fixture-token" not in b"".join(
        p.read_bytes() for p in pilot.trusted_dir.iterdir()
    )


@pytest.mark.parametrize("severity", ["P0", "P1", "P2", "P3"])
def test_finding_semantics(controller, severity):
    args, pilot, mode = controller
    mode.write_text(severity)
    evidence = _read(args, runner.run_review(args, pilot=pilot), pilot)
    assert evidence.trusted
    assert evidence.finding_counts_by_severity[severity] == 1
    assert evidence.result == ("PASS" if severity == "P3" else "FAIL")


@pytest.mark.parametrize(
    "changed", ["tree", "base", "scope_sha256", "manifest_sha256", "chunks", "starts"]
)
def test_refuse_drift_before_first_dispatch(controller, changed):
    args, pilot, _ = controller
    target = json.loads(pilot.approved_target)
    target[changed] = "wrong"
    with pytest.raises((ValueError, runner.DeepSeekReviewError)):
        runner.run_review(args, pilot=replace(pilot, approved_target=canonical_json(target)))
    assert not list(pilot.trusted_dir.iterdir())


def test_unknown_stop_preserves_originals_and_blocks_next(controller):
    args, pilot, _ = controller

    def unknown(*_):
        raise ValueError("unknown stop")

    with pytest.raises(ValueError, match="supervision incomplete"):
        runner.run_review(args, pilot=replace(pilot, verify_stop=unknown))
    assert len(list(pilot.trusted_dir.glob("*.started"))) == 1
    assert len(list(pilot.trusted_dir.glob("*.stop.json"))) == 1
    assert not list(pilot.trusted_dir.glob("*.seal"))


def test_exclusive_approval_claim(tmp_path):
    tx = low.LowReview("0" * 32, tmp_path, tmp_path, b"fixture", None, None)

    def claim(_):
        try:
            tx.claim()
        except FileExistsError:
            return False
        return True

    with ThreadPoolExecutor(max_workers=4) as pool:
        assert sum(pool.map(claim, range(8))) == 1


def test_public_runner_requires_trusted_admission(tmp_path):
    args = _retained_fixture_repo(tmp_path, subprocess.run)
    args.mission_id = low.MISSION
    with pytest.raises(runner.DeepSeekReviewError, match="trusted Controller"):
        runner.run_review(args)
    assert not args.evidence_dir.exists()


@pytest.mark.parametrize("bad", ["--tools", "worktree", "env"])
def test_supervised_start_refuses_wrong_command_or_environment(controller, bad):
    args, pilot, _ = controller
    pilot.claim()
    tree = pilot.worktree()
    tree.mkdir(mode=0o700)
    runtime = args.evidence_dir / f"claude-deepseek-runtime-{args.head_sha[:12]}-{pilot.run_id}"
    runtime.mkdir(mode=0o700)
    home = runtime / "home"
    home.mkdir(mode=0o700)
    settings = home / "settings.json"
    settings.write_bytes(runner.backend.DEDICATED_SETTINGS)
    settings.chmod(0o600)
    prompt = "one frozen test prompt"
    target = json.loads(pilot.approved_target)
    target["chunks"][0]["prompt_sha256"] = sha256_bytes(prompt.encode())
    approved = canonical_json(target)
    pilot = replace(pilot, approved_target=approved)
    (pilot.trusted_dir / "claimed.json").write_bytes(approved)
    command = runner.backend.reviewer_command(pilot.trusted_dir.parent / "claude", settings, prompt)
    env = runner.backend.child_environment("synthetic")
    env["HOME"] = str(home)
    if bad == "--tools":
        command = tuple("Bash" if arg == "" else arg for arg in command)
    if bad == "env":
        env["CLAUDE_CODE_EFFORT_LEVEL"] = "high"
    with pytest.raises(ValueError, match="Stage D supervised review"):
        pilot.run_client(0, command, tree if bad != "worktree" else args.repo_root, env, 30)
    assert not list(pilot.trusted_dir.glob("chunk-*.stdout"))


def test_real_supervisor_timeout_preserves_incomplete_second_chunk(controller):
    args, pilot, mode = controller
    mode.write_text("timeout")

    def bounded(binding, argv, cwd, environment, transcript, timeout):
        return pilot.supervise(
            binding,
            argv,
            cwd,
            environment,
            transcript,
            0.2 if binding["chunk_index"] == low.LOW_INDEX else timeout,
        )

    with pytest.raises(ValueError, match="supervision incomplete"):
        runner.run_review(args, pilot=replace(pilot, supervise=bounded))
    stop = json.loads((pilot.trusted_dir / "chunk-1.stdout.stop.json").read_bytes())
    assert stop["outcome"] == "timeout"
    assert stop["stop"]["proof"] == "ECHILD"
    assert len(list(pilot.trusted_dir.glob("*.started"))) == low.LOW_INDEX + 1
    assert not (pilot.trusted_dir / "chunk-1.seal").exists()
