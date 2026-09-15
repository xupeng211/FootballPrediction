"""Liveness probing for a review writer that a waiter did not launch itself.

lifecycle: test-fixture

``wait`` may only decide "the writer is gone" from an identity it can verify.
The incident this module guards against came from a probe that could not: a
``pgrep -f`` pattern matched the watcher's own command line, so the writer's
death was unobservable.  A bare pid is the next-best trap — the process holding
``/proc/<pid>`` later is not necessarily the one that was launched — so the
writer publishes its own ``/proc`` start time at launch and these tests pin that
binding, the refusal of pids that cannot designate one process, and the rule
that an unusable hint is not evidence of death.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import time
from typing import Any

import pytest

from scripts.devops import codex_independent_review as reviewer
from scripts.devops.codex_review_verdict import (
    EXIT_REVIEW_INFRASTRUCTURE_ERROR,
    WAIT_STATE_RECEIPT_MISSING,
    WAIT_STATE_REVIEW_FAILED,
    _proc_stat_tail,
    _WriterProbe,
    process_starttime,
    writer_identity_path,
)
from tests.helpers.agentic_workflow_fixtures import make_repo

# A refusal or a dead-writer detection must end promptly, not consume the whole
# deadline; the waits below are given long deadlines so the assertion is
# meaningful rather than trivially satisfied by the timeout itself.
FAST_FAILURE_CEILING_SECONDS = 30
SHORT_TIMEOUT_SECONDS = 2
DELIBERATE_TIMEOUT_SECONDS = 60


def _wait(evidence: Path, head: str, **overrides: Any) -> int:
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


def _payload(capsys: pytest.CaptureFixture[str]) -> dict[str, Any]:
    return json.loads(capsys.readouterr().out)


# --------------------------------------------------------------------------


def _await_zombie(process: subprocess.Popen[bytes]) -> bool:
    """Wait until the child is an unreaped zombie, so its pid cannot be reused."""

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        fields = _proc_stat_tail(process.pid)
        if fields and fields[0] == "Z":
            return True
        time.sleep(0.01)
    return False


def test_wait_case_3_writer_exit_without_receipt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    if not Path("/proc").is_dir():
        pytest.skip("liveness probing requires /proc")

    writer = subprocess.Popen(["sh", "-c", "exit 0 # codex_independent_review"])
    decoy: subprocess.Popen[bytes] | None = None
    try:
        if not _await_zombie(writer):
            pytest.skip("could not observe an unreaped child on this platform")
        # A live process whose command line contains the wrapper name: a
        # `pgrep -f` probe answers "still running" here and can never notice
        # the writer is gone, which is the defect this guards.
        decoy = subprocess.Popen(["sh", "-c", "sleep 30 # codex_independent_review"])
        assert _WriterProbe(None).alive() is True, "no probe is not evidence of death"
        assert _WriterProbe(writer.pid).alive() is False

        evidence = tmp_path / "evidence-dead-writer"
        evidence.mkdir(mode=0o700)
        started = time.monotonic()
        exit_code = _wait(
            evidence, "0" * 39 + "1", timeout_seconds=DELIBERATE_TIMEOUT_SECONDS, pid=writer.pid
        )
        elapsed = time.monotonic() - started
    finally:
        if decoy is not None:
            decoy.kill()
            decoy.wait()
        writer.wait()

    assert exit_code == EXIT_REVIEW_INFRASTRUCTURE_ERROR
    assert elapsed < FAST_FAILURE_CEILING_SECONDS, "a dead writer must be detected, not waited out"
    payload = _payload(capsys)
    assert payload["state"] == WAIT_STATE_REVIEW_FAILED
    assert payload["status"] == "FAIL"
    assert "exited without producing a receipt" in payload["detail"]


def _reaped_pid() -> int:
    """Return a pid that is provably gone, so it cannot be a live writer.

    The assertion is the point: this helper witnesses its own precondition, so
    a test that depends on "no process holds this pid" cannot pass vacuously
    after pid recycling.
    """

    child = subprocess.Popen(["sh", "-c", "exit 0"])
    child.wait()
    assert process_starttime(child.pid) is None
    return child.pid


def _record_writer(
    evidence: Path, head: str, *, pid: int, starttime: str | None, run_id: str = "f" * 32
) -> Path:
    """Write the launch record a real writer publishes for itself."""

    evidence.mkdir(mode=0o700, exist_ok=True)
    target = writer_identity_path(evidence, head, run_id)
    target.write_text(
        json.dumps(
            {
                "pid": pid,
                "starttime": starttime,
                "head_sha": head,
                "recorded_at": "2026-09-16T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    target.chmod(0o600)
    return target


def test_wait_refuses_a_pid_whose_recorded_starttime_does_not_match(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A recycled pid must be reported gone, not adopted as the writer.

    The record names a live process but a different start time, which is
    exactly what a recycled pid looks like from the outside.
    """

    repo, _base, head = make_repo(tmp_path)
    del repo
    live = subprocess.Popen(["sleep", "30"])
    try:
        real = process_starttime(live.pid)
        assert real is not None
        evidence = tmp_path / "evidence-recycled"
        _record_writer(evidence, head, pid=live.pid, starttime=str(int(real) + 1))
        started = time.monotonic()
        exit_code = _wait(evidence, head, timeout_seconds=DELIBERATE_TIMEOUT_SECONDS)
        elapsed = time.monotonic() - started
    finally:
        live.kill()
        live.wait()

    assert exit_code == EXIT_REVIEW_INFRASTRUCTURE_ERROR
    assert elapsed < FAST_FAILURE_CEILING_SECONDS, "a recycled pid must not be waited out"
    payload = _payload(capsys)
    assert payload["state"] == WAIT_STATE_REVIEW_FAILED
    assert payload["writer_identity_source"] == "writer-record"
    assert payload["writer_pid"] == live.pid


def test_wait_lets_a_live_recorded_writer_run_to_its_deadline(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Binding to an identity must not turn into "always dead"."""

    repo, _base, head = make_repo(tmp_path)
    del repo
    live = subprocess.Popen(["sleep", "30"])
    try:
        evidence = tmp_path / "evidence-live-writer"
        _record_writer(evidence, head, pid=live.pid, starttime=process_starttime(live.pid) or "")
        exit_code = _wait(evidence, head, timeout_seconds=SHORT_TIMEOUT_SECONDS)
    finally:
        live.kill()
        live.wait()

    assert exit_code == EXIT_REVIEW_INFRASTRUCTURE_ERROR
    payload = _payload(capsys)
    assert payload["state"] == WAIT_STATE_RECEIPT_MISSING
    assert payload["writer_identity_source"] == "writer-record"


def test_wait_ignores_a_writer_record_it_cannot_verify(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unusable hint is not evidence of death, so the wait still runs out.

    Both records here are refused for a different reason: the first names a
    non-positive pid, which cannot designate a process at all, and the second
    is bound to a different head.  Neither may be read as "the writer is gone".
    """

    repo, _base, head = make_repo(tmp_path)
    del repo
    evidence = tmp_path / "evidence-unusable"
    _record_writer(evidence, head, pid=0, starttime="12345", run_id="0" * 32)
    _record_writer(evidence, "f" * 40, pid=_reaped_pid(), starttime="12345", run_id="1" * 32)

    exit_code = _wait(evidence, head, timeout_seconds=SHORT_TIMEOUT_SECONDS)
    payload = _payload(capsys)
    assert exit_code == EXIT_REVIEW_INFRASTRUCTURE_ERROR
    assert payload["state"] == WAIT_STATE_RECEIPT_MISSING
    assert payload["writer_identity_source"] == "none"
    assert payload["writer_pid"] is None


def test_wait_refuses_a_pid_that_cannot_designate_one_process(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`0` and negative pids address a process group, not a writer."""

    evidence = tmp_path / "evidence-nonpositive"
    evidence.mkdir(mode=0o700)
    exit_code = _wait(evidence, "0" * 39 + "1", pid=0)
    payload = _payload(capsys)
    assert exit_code == EXIT_REVIEW_INFRASTRUCTURE_ERROR
    assert payload["state"] == WAIT_STATE_REVIEW_FAILED
    assert "--pid 必须是正整数" in payload["detail"]


def test_wait_refuses_a_starttime_without_a_pid(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An identity with no process to bind it to cannot be verified."""

    evidence = tmp_path / "evidence-orphan-starttime"
    evidence.mkdir(mode=0o700)
    exit_code = _wait(evidence, "0" * 39 + "1", pid_starttime="12345")
    payload = _payload(capsys)
    assert exit_code == EXIT_REVIEW_INFRASTRUCTURE_ERROR
    assert payload["state"] == WAIT_STATE_REVIEW_FAILED
    assert "--pid-starttime 需要同时给出 --pid" in payload["detail"]
