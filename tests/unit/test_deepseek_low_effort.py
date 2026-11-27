"""Stage D 独立收据、真实子进程设置和既有 Harness 停止证明的离线回归。"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import importlib
import json
import os
from pathlib import Path
import shutil
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


def _trusted_test_repo(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    adapters = pytest.importorskip("harness.adapters")
    harness_root = Path(adapters.__file__).resolve().parents[2]
    if (
        subprocess.check_output(
            ["git", "-C", str(harness_root), "rev-parse", "HEAD"], text=True
        ).strip()
        != low.HARNESS_REVISION
    ):
        pytest.skip("integration requires the pinned Controller revision")
    adapter = adapters.FootballPredictionAdapter()
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

    # 两个真实 Git 版本：BASE 提供项目工具，非 detached Builder 候选另行改动工具。
    policy_files = {*adapter.REVIEW_CONTRACT_PATHS, "scripts/devops/percent_repair_input.py"}
    project = runner.ROOT
    policy_files.update(
        Path(module.__file__).relative_to(project).as_posix()
        for name, module in tuple(sys.modules.items())
        if name.startswith("scripts.")
        and getattr(module, "__file__", None)
        and Path(module.__file__).is_relative_to(project)
    )
    for relative in policy_files:
        dest = args.repo_root / relative
        dest.parent.mkdir(exist_ok=True, parents=True)
        shutil.copy(project / relative, dest)
    git("add", "Makefile", "scripts", "schemas", "docs")
    git("commit", "-qm", "trusted offline tooling base")
    args.base_sha = git("rev-parse", "HEAD").decode().strip()
    with (args.repo_root / low.CAPTURE_PATH).open("a") as stream:
        stream.write("\n# independent Builder worktree marker\n")
    git("add", ".")
    git("commit", "-qm", "offline four-packet candidate")
    args.head_sha = git("rev-parse", "HEAD").decode().strip()
    checkout = adapter._trusted_base_checkout(str(args.repo_root), args.base_sha)
    # 模拟长驻 pytest 中隔离加载，另有新 -I/-B 子进程执行文档中的真实启动顺序。
    original_paths = [
        path for path in sys.path if not (Path(path or ".").resolve() / "scripts").exists()
    ]
    monkeypatch.setattr(sys, "path", [str(checkout), *original_paths])
    original_modules = {
        k: v for k, v in sys.modules.items() if k == "scripts" or k.startswith("scripts.")
    }
    for k in original_modules:
        monkeypatch.delitem(sys.modules, k)
    for name, suffix in (
        ("low", "deepseek_low_effort"),
        ("runner", "claude_deepseek_independent_review"),
        ("consumer", "deepseek_receipt_evidence"),
        ("agent_workflow", "agent_workflow"),
    ):
        monkeypatch.setitem(globals(), name, importlib.import_module("scripts.devops." + suffix))
    origin = low.ToolOrigin(args.repo_root.resolve(), args.base_sha, checkout, harness_root)
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
    return args, origin, target, original_modules


@pytest.fixture
def controller(tmp_path, monkeypatch):
    args, origin, target, original_modules = _trusted_test_repo(tmp_path, monkeypatch)
    supervised = (
        pytest.importorskip("harness.factory_runtime").LocalRuntime()._supervised_review_step
    )
    stop = pytest.importorskip("harness.appserver_process").validate_supervised_stop
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
        uuid.uuid4().hex,
        trusted,
        args.evidence_dir,
        canonical_json(target),
        supervised,
        stop,
        origin,
    )
    yield args, pilot, mode
    for name in tuple(sys.modules):
        if name.startswith("scripts.") and name not in original_modules:
            del sys.modules[name]


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


def test_unknown_stop_preserves_originals_and_blocks_next(controller, monkeypatch):
    args, pilot, _ = controller

    def unknown(*_):
        raise ValueError("unknown stop")

    monkeypatch.setattr(
        sys.modules["harness.appserver_process"], "validate_supervised_stop", unknown
    )
    with pytest.raises(ValueError, match="supervision incomplete"):
        runner.run_review(args, pilot=replace(pilot, verify_stop=unknown))
    assert len(list(pilot.trusted_dir.glob("*.started"))) == 1
    assert len(list(pilot.trusted_dir.glob("*.stop.json"))) == 1
    assert not list(pilot.trusted_dir.glob("*.seal"))


def test_exclusive_approval_claim(tmp_path):
    tx = low.LowReview("0" * 32, tmp_path, tmp_path, b"fixture", None, None, None)

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


def test_real_supervisor_timeout_preserves_incomplete_second_chunk(controller, monkeypatch):
    args, pilot, mode = controller
    mode.write_text("timeout")

    def bounded(_runtime, binding, argv, cwd, environment, transcript, timeout):
        return pilot.supervise(
            binding,
            argv,
            cwd,
            environment,
            transcript,
            0.2 if binding["chunk_index"] == low.LOW_INDEX else timeout,
        )

    runtime = pilot.supervise.__self__
    monkeypatch.setattr(type(runtime), "_supervised_review_step", bounded)
    with pytest.raises(ValueError, match="supervision incomplete"):
        runner.run_review(args, pilot=replace(pilot, supervise=runtime._supervised_review_step))
    stop = json.loads((pilot.trusted_dir / "chunk-1.stdout.stop.json").read_bytes())
    assert stop["outcome"] == "timeout"
    assert stop["stop"]["proof"] == "ECHILD"
    assert len(list(pilot.trusted_dir.glob("*.started"))) == low.LOW_INDEX + 1
    assert not (pilot.trusted_dir / "chunk-1.seal").exists()


def test_controller_preimport_and_supervised_round_in_fresh_process(controller):
    args, pilot, mode = controller
    docs = (Path(__file__).resolve().parents[2] / "docs/AGENT_WORKFLOW.md").read_text()
    bootstrap = (
        docs.split("<!-- stage-d-controller-bootstrap -->", 1)[1]
        .split("```python\n", 1)[1]
        .split("\n```", 1)[0]
    )
    client = mode.with_suffix("")
    # 外部 Controller 的独立新解释器执行真实启动段及正式 runner 正例。
    driver = """
import json, uuid
from argparse import Namespace
harness, harness_git, candidate, common = [Path(v) for v in sys.argv[1:5]]
base, head, mode = sys.argv[5:8]
if mode == "preloaded":
    sys.path.insert(0, str(candidate))
    from scripts.devops import independent_review_protocol
if mode == "wrong-repository":
    common = harness_git
origin = admitted_tools(harness, harness_git, candidate, common, base)
from harness.appserver_process import validate_supervised_stop
from harness.factory_runtime import LocalRuntime
from scripts.devops import claude_deepseek_independent_review as runner
from scripts.devops import deepseek_low_effort as low
from scripts.devops import deepseek_receipt_evidence as consumer
binary = Path(sys.argv[8])
evidence, trusted = [Path(v) for v in sys.argv[9:11]]
target = bytes.fromhex(sys.argv[11])
pilot = low.LowReview(sys.argv[12], trusted, evidence, target,
                      LocalRuntime()._supervised_review_step, validate_supervised_stop, origin)
scope = candidate / "docs/agentic/missions" / (low.MISSION + ".json")
args = Namespace(repo_root=candidate, base_sha=base, head_sha=head, mission_id=low.MISSION,
                 mission_scope_file=scope, evidence_dir=evidence, retain_invocation=True)
runner.backend.TRUSTED_CLAUDE_BINARY_ROOTS = (binary.parent,)
runner.backend.TRUSTED_CLAUDE_BINARY_SHA256 = {hashlib.sha256(binary.read_bytes()).hexdigest()}
def fake_secret(_):
    with (trusted / "mock-secret-read").open("a") as stream:
        stream.write("admitted\\n")
    return "synthetic-fixture-token"
runner.backend._secret = fake_secret
os.environ["PATH"] = str(binary.parent) + os.pathsep + os.environ["PATH"]
if mode == "run":
    path = runner.run_review(args, pilot=pilot)
    print(path.name)
else:
    path = evidence / ("claude-deepseek-receipt-" + head[:12] + "-" + pilot.run_id + ".json")
    verified = consumer._deepseek_receipt_evidence(path, repo_root=candidate, expected_base=base,
        expected_head=head, expected_mission_id=low.MISSION, expected_scope_hash=json.loads(target)["scope_sha256"],
        pilot=pilot)
    require(verified.trusted)
"""
    git = ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"]
    harness_common = subprocess.check_output(
        git, cwd=pilot.origin.harness_checkout, text=True
    ).strip()
    project_common = subprocess.check_output(git, cwd=args.repo_root, text=True).strip()

    def invoke(case):
        return subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                "-c",
                bootstrap + "\n" + driver,
                str(pilot.origin.harness_checkout),
                harness_common,
                str(args.repo_root),
                project_common,
                args.base_sha,
                args.head_sha,
                case,
                str(client),
                str(args.evidence_dir),
                str(pilot.trusted_dir),
                pilot.approved_target.hex(),
                pilot.run_id,
            ],
            cwd=pilot.trusted_dir,
            env={"PATH": "/usr/bin:/bin"},
            capture_output=True,
            text=True,
            check=False,
        )

    for case in ("preloaded", "wrong-repository"):
        refused = invoke(case)
        assert refused.returncode != 0
        assert "unverified Stage D Controller tool origin" in refused.stderr
        assert not list(pilot.trusted_dir.iterdir())
    executed = invoke("run")
    assert executed.returncode == 0, executed.stderr
    checked = invoke("consume")
    assert checked.returncode == 0, checked.stderr
    assert len((pilot.trusted_dir / "mock-secret-read").read_text().splitlines()) == low.CHUNKS
    assert len(list(pilot.trusted_dir.glob("*.started"))) == low.CHUNKS


@pytest.mark.parametrize(
    "source", ["builder", "wrong-base", "wrong-origin", "dirty-capture", "foreign-method"]
)
def test_refuse_untrusted_helper_before_reading_credentials(controller, source, monkeypatch):
    args, pilot, _ = controller
    base_origin = pilot.origin
    if source == "foreign-method":
        pilot = replace(pilot, supervise=lambda *_: pytest.fail("unexpected dispatch"))
    if source == "builder":
        pilot = replace(pilot, origin=replace(base_origin, checkout=args.repo_root))
    if source == "wrong-base":
        pilot = replace(pilot, origin=replace(base_origin, project_base=args.head_sha))
    if source == "wrong-origin":
        pilot = replace(pilot, origin=replace(base_origin, harness_checkout=args.repo_root))
    if source == "dirty-capture":
        helper = base_origin.checkout / low.CAPTURE_PATH
        helper.write_bytes(helper.read_bytes() + b"\n# harmless drift\n")
    monkeypatch.setattr(
        runner.backend, "_secret", lambda _: pytest.fail("unexpected credential access")
    )
    with pytest.raises((ValueError, RuntimeError)):
        runner.run_review(args, pilot=pilot)
    assert not list(pilot.trusted_dir.iterdir())


def test_recheck_physical_helper_at_secret_read_and_consume(controller, monkeypatch):
    args, pilot, _ = controller
    receipt = runner.run_review(args, pilot=pilot)
    assert _read(args, receipt, pilot).trusted
    helper = pilot.origin.checkout / low.CAPTURE_PATH
    original = helper.read_bytes()
    helper.write_bytes(original + b"\n# harmless drift\n")
    assert not _read(args, receipt, pilot).trusted
    monkeypatch.setattr(
        runner.backend, "_secret", lambda _: pytest.fail("unexpected credential access")
    )
    with pytest.raises((ValueError, RuntimeError)):
        runner.backend.run(prompt="offline", cwd=pilot.worktree(), supervised_chunk=(pilot, 0))
    assert len(list(pilot.trusted_dir.glob("*.started"))) == low.CHUNKS


def test_capture_drift_after_secret_check_refuses_supervised_dispatch(controller, monkeypatch):
    args, pilot, _ = controller
    helper = pilot.origin.checkout / low.CAPTURE_PATH

    def change_after_check(_):
        helper.write_bytes(helper.read_bytes() + b"\n# harmless drift after credential check\n")
        return "synthetic-fixture-token"

    monkeypatch.setattr(runner.backend, "_secret", change_after_check)
    with pytest.raises((RuntimeError, ValueError)):
        runner.run_review(args, pilot=pilot)
    assert (pilot.trusted_dir / "claimed.json").exists()
    assert not list(pilot.trusted_dir.glob("*.started"))
    assert not list(pilot.trusted_dir.glob("*.stdout"))
