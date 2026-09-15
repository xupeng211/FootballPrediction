"""Shared harness for the independent-review verdict, wait and round tests.

lifecycle: test-fixture

The review harness is addressed through three test modules: the verdict/wait
contract, the CLI + GNU make invocation contract, and the round-identity model.
They share one way of producing evidence: a real sealed receipt, filed under
the canonical name a real writer would have used, inside an owner-only
directory.  Building that twice would let the two copies drift, and the drift
would be invisible — every assertion here is about which file the reader picked
up, so a harness that names files even slightly differently would quietly stop
testing the naming rule it exists to pin.

Everything that fabricates evidence lives here; the test modules only assert.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import TYPE_CHECKING, Any

from scripts.devops import codex_independent_review as reviewer
from scripts.devops.codex_review_contract import review_challenge
from scripts.devops.codex_review_verdict import writer_identity_path
from scripts.devops.codex_review_wait import process_starttime
from scripts.ops.helpers.agent_workflow_contract import mission_scope_sha256
from tests.helpers.agentic_workflow_fixtures import (
    MISSION_ID,
    MISSION_SCOPE_PATH,
    make_repo,
    write_valid_receipt,
)

if TYPE_CHECKING:
    import pytest

ROOT = Path(__file__).resolve().parents[2]

BLOCKING_FINDING: dict[str, Any] = {
    "severity": "P2",
    "title": "state block contradicts itself",
    "summary": "the document calls itself current-state while asserting the superseded value",
}

SHORT_TIMEOUT_SECONDS = 2
TWO_REVIEW_ROUNDS = 2

# GNU make's own failure status.  It preserves a recipe's success and collapses
# every non-zero child status into this one value, so 3 and 1 are the same
# status at the make layer; the child status is only readable from the JSON.
MAKE_FAILURE_EXIT_CODE = 2

# A refusal must end promptly, not consume the whole deadline; the waits below
# are given long deadlines so the assertion is meaningful rather than trivially
# satisfied by the timeout itself.
FAST_FAILURE_CEILING_SECONDS = 30
DELIBERATE_TIMEOUT_SECONDS = 60

# The writer's own modes: anything else is a file this harness did not write.
OWNER_ONLY_FILE_MODE = 0o600
OWNER_ONLY_DIRECTORY_MODE = 0o700


def git_output(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, text=True, capture_output=True, check=True)
    return result.stdout.strip()


def seal_receipt(
    tmp_path: Path,
    repo: Path,
    base: str,
    head: str,
    *,
    result: str = "PASS",
    finding: dict[str, Any] | None = None,
    slot: str = "a",
) -> Path:
    """Seal one real receipt through the canonical fixture writer."""

    workdir = tmp_path / f"seal-{slot}"
    workdir.mkdir()
    return write_valid_receipt(workdir, repo, base, head, result=result, finding=finding)


def place_receipt(
    evidence: Path,
    sealed: Path,
    *,
    name_head: str,
    run_id: str,
    mtime: float | None = None,
) -> Path:
    """Place a sealed receipt at the canonical name the writer actually uses."""

    evidence.mkdir(mode=0o700, exist_ok=True)
    target = evidence / f"codex-review-receipt-{name_head[:12]}-{run_id}.json"
    target.write_bytes(sealed.read_bytes())
    target.chmod(0o600)
    if mtime is not None:
        os.utime(target, (mtime, mtime))
    return target


def run_wait(evidence: Path, head: str, **overrides: Any) -> int:
    argv = [
        "wait",
        "--evidence-dir",
        str(evidence),
        "--head-sha",
        head,
        "--timeout-seconds",
        str(overrides.pop("timeout_seconds", 5)),
        "--poll-interval",
        "0.05",
        "--json",
    ]
    for key, value in overrides.items():
        argv += [f"--{key.replace('_', '-')}", str(value)]
    return reviewer.main(argv)


def payload_of(capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    return json.loads(capsys.readouterr().out)


def make_help_line(target: str) -> str:
    makefile = Path(reviewer.__file__).resolve().parents[2] / "Makefile"
    for line in makefile.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{target}: ##"):
            return line
    raise AssertionError(f"no help line for target {target}")


def stub_codex(stub_path: Path) -> Path:
    """Write a transport-only stand-in for the Codex CLI.

    It answers ``--version``, replays a synthesized JSONL turn, and materializes
    the final message handed to it through the environment.  It decides nothing:
    the verdict it carries is the one the test chose, which is the point — the
    wrapper's exit status must follow the receipt, whatever that verdict is.
    """

    stub_path.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys\n"
        "if '--version' in sys.argv:\n"
        "    print('codex-stub 1.2.3')\n"
        "    raise SystemExit(0)\n"
        "payload = os.environ['STUB_FINAL_DOCUMENT']\n"
        "target = sys.argv[sys.argv.index('--output-last-message') + 1]\n"
        "with open(target, 'w', encoding='utf-8') as stream:\n"
        "    stream.write(payload)\n"
        "for event in (\n"
        "    {'type': 'thread.started', 'thread_id': 'stub-reviewer-thread'},\n"
        "    {'type': 'item.completed', 'item': {'id': 'i1', 'type': 'agent_message',"
        " 'text': payload}},\n"
        "    {'type': 'turn.completed'},\n"
        "):\n"
        "    print(json.dumps(event), flush=True)\n",
        encoding="utf-8",
    )
    stub_path.chmod(0o755)
    return stub_path


def run_end_to_end(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    *,
    result: str,
    finding: dict[str, Any] | None,
    evidence: Path | None = None,
    run_id: str | None = None,
    repo_state: tuple[Path, str, str] | None = None,
) -> tuple[int, dict[str, Any]]:
    """Drive the real `run` subcommand against a stub reviewer binary."""

    repo, base, head = repo_state if repo_state is not None else make_repo(tmp_path)
    scope_path = repo / MISSION_SCOPE_PATH
    document = {
        "result": result,
        "review_challenge": review_challenge(
            mission_id=MISSION_ID,
            base_sha=base,
            head_sha=head,
            mission_scope_sha256=mission_scope_sha256(scope_path),
        ),
        "findings": [finding] if finding else [],
    }
    payload = json.dumps(document, ensure_ascii=False)
    monkeypatch.setenv("CODEX_CLI_PATH", str(stub_codex(tmp_path / "codex-stub")))
    monkeypatch.setenv("STUB_FINAL_DOCUMENT", payload)
    if evidence is None:
        evidence = tmp_path / "e2e-evidence"
        evidence.mkdir(mode=0o700)

    exit_code = reviewer.main(
        [
            "run",
            "--repo-root",
            str(repo),
            "--base-sha",
            base,
            "--head-sha",
            head,
            "--mission-id",
            MISSION_ID,
            "--mission-scope-file",
            str(scope_path),
            "--evidence-dir",
            str(evidence),
            "--builder-context-id",
            "builder-process:999999",
            "--json",
            *([] if run_id is None else ["--run-id", run_id]),
        ]
    )
    return exit_code, json.loads(capsys.readouterr().out)


def run_wait_process(
    evidence: Path, head: str, *extra: str, timeout_seconds: int = 30
) -> subprocess.CompletedProcess[str]:
    """Drive the CLI as the process a wrapper actually observes."""

    root = Path(reviewer.__file__).resolve().parents[2]
    return subprocess.run(
        [
            "python3",
            "scripts/devops/codex_independent_review.py",
            "wait",
            "--evidence-dir",
            str(evidence),
            "--head-sha",
            head,
            "--timeout-seconds",
            str(timeout_seconds),
            "--poll-interval",
            "0.05",
            "--json",
            *extra,
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )


def run_make_wait(
    evidence: Path, head: str, *, timeout_seconds: int = 30
) -> subprocess.CompletedProcess[str]:
    root = Path(reviewer.__file__).resolve().parents[2]
    return subprocess.run(
        [
            "make",
            "agent-review-wait",
            f"HEAD_SHA={head}",
            f"EVIDENCE_DIR={evidence}",
            f"TIMEOUT_SECONDS={timeout_seconds}",
            "POLL_INTERVAL=0.05",
            "JSON=1",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )


def record_writer(
    evidence: Path, head: str, *, run_id: str, pid: int | None = None, starttime: str | None = None
) -> Path:
    """Publish the launch record a real writer writes for itself."""

    evidence.mkdir(mode=0o700, exist_ok=True)
    target = writer_identity_path(evidence, head, run_id)
    target.write_text(
        json.dumps(
            {
                "pid": os.getpid() if pid is None else pid,
                "starttime": process_starttime(os.getpid()) if starttime is None else starttime,
                "head_sha": head,
                "recorded_at": "2026-09-16T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    target.chmod(0o600)
    return target
