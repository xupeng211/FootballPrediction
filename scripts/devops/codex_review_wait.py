#!/usr/bin/env python3
"""阻塞等待 independent review 的 exact-head receipt，并取回它的 verdict。

lifecycle: permanent
owner: engineering workflow governance

本模块是 ``codex_independent_review`` 的等待与存活探测层：它不定义 receipt 的命名规则、
也不决定 verdict 的含义（那在 ``codex_review_verdict``），只负责在一个阻塞命令内等到
真实产物出现，并把它的 verdict 变成 exit status。

* ``wait_for_receipt`` 在**一个**阻塞命令内等到 exact-head receipt 出现并返回它的
  verdict，因此整个 review lifecycle 不需要"子进程结束后唤醒父 agent"这一机制。它按
  ``codex-review-receipt-<head12>-<runid>.json`` 轮询真实产物、只做数字 pid 存活探测
  （``pgrep -f`` 会匹配 watcher 自己的命令行），并在超时、writer 异常退出、receipt 缺失
  或 head 不匹配时以显式失败状态结束，绝不静默交还控制权。
* pid 不是身份：``/proc/<pid>`` 可能在 waiter 查看之前就属于另一个进程。writer 因此在
  启动时把**自己**的 pid 与 ``/proc`` start time 写进 evidence directory 的 identity
  record，``wait`` 默认绑定这条**已记录**的身份并逐次核对 start time，而不是把首次看到的
  进程当成 writer。非正 ``--pid`` 一律拒绝：``0`` 与负数会让存活探测命中进程组或全部可访问
  进程，无法表达"指定的那个 writer"。
* 一个 head 可以有多个 review round，因此 mtime 顺序不是身份：``wait`` 把一个 head 的
  receipt 绑定到**它正在等待的那个 round**。round 从 ``--run-id`` 显式给出，否则取该 head
  最新 writer record 所记录的 run id；不属于被等待 round 的 receipt 永远不会被当作本轮
  verdict 消费（同一个 evidence directory 被复用时，旧 round 的 PASS 不能替新 round 说话），
  两者都拿不到时才退回按 mtime 取最新——round 无法确定时的诚实降级。
* 非法输入不是 traceback：无法规范化成完整 40 位 SHA 的 ``--head-sha``、非法 ``--run-id``
  等都在报告机制建立后以结构化失败结束（``REVIEW_FAILED``、exit ``1``、``--json`` 时 stdout
  仍是一行 JSON），而不是让调用方去解析 stderr 里的栈。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.devops.codex_review_provenance import ReviewReceiptError  # noqa: E402
from scripts.devops.codex_review_verdict import (  # noqa: E402
    EXIT_REVIEW_INFRASTRUCTURE_ERROR,
    EXIT_REVIEW_PASS,
    REVIEW_RECEIPT_GLOB,
    REVIEW_RECEIPT_PREFIX,
    WAIT_STATE_PARENT_CONTINUING,
    WAIT_STATE_PARENT_WAITING,
    WAIT_STATE_RECEIPT_MISSING,
    WAIT_STATE_REVIEW_FAILED,
    WAIT_STATE_REVIEW_FINISHED,
    WAIT_STATE_REVIEW_RUNNING,
    WRITER_IDENTITY_PREFIX,
    _candidate_verdict,
    assert_owner_only_directory,
    is_canonical_run_id,
    run_id_from_name,
    run_id_refusal,
    verdict_exit_code,
    writer_identity_pattern,
)
from scripts.devops.exact_head import ExactHeadError, normalize_full_sha  # noqa: E402


def _proc_stat_tail(pid: int) -> list[str] | None:
    """Return the ``/proc/<pid>/stat`` fields that follow the ``comm`` field.

    ``comm`` is parenthesized and may itself contain spaces and parentheses, so
    the only safe split is after the final ``)``.
    """

    try:
        raw = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
    except OSError:
        return None
    head, sep, tail = raw.rpartition(")")
    if not sep or not head:
        return None
    fields = tail.split()
    return fields or None


# Field 22 of /proc/<pid>/stat is the process start time in clock ticks.  The
# parenthesized comm field sits at 2, so the tail returned by _proc_stat_tail
# starts at field 3: index 0 is the state, index 19 is the start time.
_PROC_STAT_STATE_INDEX = 0
_PROC_STAT_STARTTIME_INDEX = 19


def _process_stat(pid: int) -> tuple[str, str] | None:
    """Return ``(state, starttime)`` for one pid, or None when unreadable.

    The second element is field 22 of ``/proc/<pid>/stat``: the process start
    time in clock ticks.  Two observations of the same pid with different start
    times are two different processes, which is how pid recycling is caught.
    """

    fields = _proc_stat_tail(pid)
    if fields is None or len(fields) <= _PROC_STAT_STARTTIME_INDEX:
        return None
    return fields[_PROC_STAT_STATE_INDEX], fields[_PROC_STAT_STARTTIME_INDEX]


def process_starttime(pid: int) -> str | None:
    """Return the start time that identifies one process for its whole life."""

    stat = _process_stat(pid)
    return None if stat is None else stat[1]


def _process_exists(pid: int) -> bool:
    """Probe process existence by signal 0, without any pattern matching."""

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


class _WriterProbe:
    """Decide whether the writer that was launched is still running.

    A pattern probe cannot answer this question, and this is the exact defect
    that stranded the incident this module is being repaired for: the watcher
    ran ``pgrep -f codex_independent_review``, the watcher's own command line
    contains that literal string, so the probe matched itself and the
    "writer has exited" branch was unreachable forever.

    Only an explicit numeric pid can be probed honestly, and a pid alone is not
    an identity: the process holding ``/proc/<pid>`` when the waiter looks may
    not be the one that was launched.  The probe therefore compares the
    ``/proc`` start time, taken from the caller or from the record the writer
    published at launch, and reports a mismatching pid as gone.

    A pid that carries no start time is not probed at all.  Adopting the first
    start time observed for it would make the pid its own baseline, so a pid
    recycled before the first poll would be indistinguishable from the writer
    and would hide the writer's death for the rest of the deadline.
    """

    def __init__(
        self,
        pid: int | None,
        *,
        starttime: str | None = None,
        directory: Path | None = None,
        pattern: str | None = None,
        expected_head: str | None = None,
    ) -> None:
        self._pid = pid
        self._starttime = starttime
        self._directory = directory
        self._pattern = pattern
        self._expected_head = expected_head
        self._source = "argument" if pid is not None else "none"

    @property
    def pid(self) -> int | None:
        """The pid under observation, once one is known."""

        return self._pid

    @property
    def source(self) -> str:
        """Where the probed identity came from: ``argument``, ``writer-record`` or ``none``."""

        return self._source

    def alive(self) -> bool:
        """Return whether the launched writer is still running.

        Returns ``True`` when no probe is available.  Absence of a probe is not
        evidence of death, and inventing one would abandon a healthy wait.
        """

        if self._pid is None:
            self._bind_recorded_writer()
            if self._pid is None:
                return True
        if self._starttime is None:
            # An unbound pid is not an identity, and the first start time read
            # for it would be a baseline the pid itself supplied: a writer that
            # died and had its pid recycled would then pass for the writer
            # forever.  Nothing is probed here, so the wait runs to its deadline
            # and reports an explicit timeout instead of a guess.
            return True
        stat = _process_stat(self._pid)
        if stat is None:
            # No readable /proc entry: fall back to the existence probe alone.
            return _process_exists(self._pid)
        state, starttime = stat
        if starttime != self._starttime:
            return False
        return state != "Z"

    def _bind_recorded_writer(self) -> None:
        """Adopt the identity the writer recorded for itself, once it exists."""

        if self._directory is None or self._pattern is None or self._expected_head is None:
            return
        recorded = _recorded_writer_identity(
            self._directory, self._pattern, expected_head=self._expected_head
        )
        if recorded is None:
            return
        self._pid, self._starttime = recorded[0], recorded[1]
        self._source = "writer-record"


def _newest_first(directory: Path, pattern: str) -> list[Path]:
    """Return the files matching one pattern, newest mtime first."""

    def _mtime(path: Path) -> int:
        try:
            return path.stat().st_mtime_ns
        except OSError:
            return -1

    try:
        paths = [p for p in directory.glob(pattern) if p.is_file()]
    except OSError:
        return []
    paths.sort(key=lambda p: (_mtime(p), p.name), reverse=True)
    return paths


def _receipt_candidates(directory: Path, pattern: str) -> tuple[list[Path], Path | None]:
    """Return JSON-loadable candidates newest-first, plus one unreadable one.

    A writer observed mid-``_write_exclusive`` is a real state, not a verdict,
    so a candidate that does not yet parse is reported separately rather than
    treated as evidence.
    """

    readable: list[Path] = []
    unreadable: Path | None = None
    for path in _newest_first(directory, pattern):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            unreadable = unreadable or path
            continue
        if isinstance(document, dict):
            readable.append(path)
        else:
            unreadable = unreadable or path
    return readable, unreadable


class _WaitProgress:
    """Emit each wait-state transition exactly once, to the chosen stream."""

    def __init__(self, stream: Any) -> None:
        self._stream = stream
        self._announced: str | None = None

    def announce(self, state: str, detail: str) -> None:
        """Report one state, unless it is the state already reported."""

        if state != self._announced:
            self._announced = state
            print(f"INDEPENDENT_REVIEW_WAIT={state} {detail}", file=self._stream, flush=True)


def _success_detail(
    candidate: Path,
    review_result: str,
    blocking: int,
    found: list[Path],
    *,
    run_id: str | None = None,
    other_rounds: list[Path] | None = None,
) -> str:
    """Describe a settled verdict, naming the receipt and the round it speaks for.

    When the watched round is known, the verdict is reported as *that round's*
    verdict and any sibling round is named as deliberately untouched.  When it
    is not, the newest candidate decided the outcome and the detail says so:
    a head reviewed twice has two verdicts, and only the caller knows which one
    it is asking about.
    """

    detail = f"receipt={candidate} review_result={review_result} blocking_findings={blocking}"
    if run_id is not None:
        detail += f" review_run_id={run_id}{_other_round_note(other_rounds or [])}"
    elif len(found) > 1:
        detail += (
            " (NOTE: multiple receipts exist for this head and no review round was named, "
            "so the newest by mtime was used; use a fresh evidence directory per review "
            "round, or name the round with --run-id)"
        )
    return detail


def _recorded_writer_identity(
    directory: Path, pattern: str, *, expected_head: str
) -> tuple[int, str, str | None] | None:
    """Return the ``(pid, starttime, run_id)`` the newest writer record claims.

    The writer publishes this at launch, so a waiter can bind to the process
    that was actually started rather than to whichever process holds that pid
    later.  A record that is absent, unreadable, malformed or bound to another
    head yields ``None``: no probe is not evidence of death, and a hint that
    cannot be verified is not a hint.

    The run id comes from the record's own name, which is how the waiter learns
    *which* round it is watching without being told — the same rule that named
    the receipt it is waiting for.

    Records are read newest-first for the same reason receipts are, so a reused
    evidence directory resolves to the most recent writer.  A stale record whose
    writer is gone therefore ends a wait early, but only ever with an explicit
    ``REVIEW_FAILED`` — never a PASS, and never a verdict.
    """

    for path in _newest_first(directory, pattern):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(document, dict) or document.get("head_sha") != expected_head:
            continue
        pid = document.get("pid")
        starttime = document.get("starttime")
        if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
            continue
        if not isinstance(starttime, str) or not starttime:
            continue
        return pid, starttime, run_id_from_name(path, WRITER_IDENTITY_PREFIX, expected_head)
    return None


def _watched_round(directory: Path, pattern: str, expected_head: str) -> str | None:
    """Return the run id of the round whose writer record the waiter can see."""

    recorded = _recorded_writer_identity(directory, pattern, expected_head=expected_head)
    if recorded is None or recorded[2] is None or not is_canonical_run_id(recorded[2]):
        return None
    return recorded[2]


def _split_by_round(
    found: list[Path], requested_head: str, watched_run: str | None
) -> tuple[list[Path], list[Path]]:
    """Split readable candidates into the watched round's and every other one.

    A receipt that belongs to a different round of the same head is not this
    round's verdict, so it is reported and never consumed.  With no watched
    round there is nothing to bind to, and every candidate stays eligible: the
    caller is then told outright that mtime chose, because inventing a round
    would be worse than naming the ambiguity.
    """

    if watched_run is None:
        return list(found), []
    mine: list[Path] = []
    others: list[Path] = []
    for path in found:
        if run_id_from_name(path, REVIEW_RECEIPT_PREFIX, requested_head) == watched_run:
            mine.append(path)
        else:
            others.append(path)
    return mine, others


def _other_round_note(other_rounds: list[Path]) -> str:
    """Name the receipts that were left alone because they are another round's."""

    if not other_rounds:
        return ""
    return (
        f"; {len(other_rounds)} receipt(s) for this head belong to other review rounds "
        f"({', '.join(sorted(p.name for p in other_rounds))}) and were not consumed"
    )


def _pid_identity_refusal(pid: int | None, starttime: str | None) -> str | None:
    """Return why the requested writer identity cannot be used, or None."""

    if pid is not None and pid <= 0:
        return (
            f"--pid 必须是正整数: {pid}"
            "（0 与负数会让存活探测命中进程组或全部可访问进程，无法指定 writer）"
        )
    if pid is not None and starttime is None:
        return (
            f"--pid {pid} 未绑定身份: 单独一个 pid 会被复用，无法证明它仍是那个 writer，"
            "必须同时用 --pid-starttime 给出启动时观察到的 /proc start time"
        )
    if starttime is not None and pid is None:
        return "--pid-starttime 需要同时给出 --pid"
    return None


def _wait_precondition_error(
    directory: Path,
    timeout_seconds: int,
    pid: int | None,
    starttime: str | None,
    run_id: str | None = None,
) -> str | None:
    """Return why a wait cannot start at all, or None when it can."""

    if not directory.is_dir():
        return f"evidence directory 不存在: {directory}"
    if timeout_seconds <= 0:
        return f"--timeout-seconds 必须为正数: {timeout_seconds}"
    if run_id is not None and not is_canonical_run_id(run_id):
        return run_id_refusal(run_id)
    return _pid_identity_refusal(pid, starttime)


def _wait_start_refusal(
    directory: Path,
    timeout_seconds: int,
    pid: int | None,
    starttime: str | None,
    run_id: str | None,
    head_fault: str | None,
) -> str | None:
    """Return why this wait cannot start, or None when it can begin watching.

    Every refusal the wait has to make before it watches for a writer is
    produced here, so there is one place where "the wait never started" is
    decided — and therefore one place that has to keep reporting it in the
    structured shape a machine caller reads.
    """

    if head_fault is not None:
        return f"--head-sha 无法规范化为 exact head: {head_fault}（必须给出完整 40 位 SHA）"
    precondition = _wait_precondition_error(directory, timeout_seconds, pid, starttime, run_id)
    if precondition is not None:
        return precondition
    try:
        assert_owner_only_directory(directory)
    except ReviewReceiptError as exc:
        return str(exc)
    return None


def _timeout_outcome(
    *,
    unreadable: Path | None,
    requested_head: str,
    timeout_seconds: int,
    directory: Path,
    pattern: str,
    watched_run: str | None = None,
    other_rounds: list[Path] | None = None,
) -> tuple[str, str]:
    """Describe why the deadline passed without establishing a verdict."""

    round_note = f"; watched run {watched_run}" if watched_run is not None else ""
    sibling_note = _other_round_note(other_rounds or [])
    if unreadable is None:
        return WAIT_STATE_RECEIPT_MISSING, (
            f"no receipt for head {requested_head} after {timeout_seconds}s "
            f"in {directory} (pattern {pattern}){round_note}{sibling_note}"
        )
    return WAIT_STATE_REVIEW_FAILED, (
        f"receipt candidate present but never became a readable receipt "
        f"after {timeout_seconds}s: {unreadable}{round_note}{sibling_note}"
    )


def wait_for_receipt(  # noqa: C901 - one poll iteration has three terminal outcomes
    *,
    evidence_dir: Path,
    head_sha: str,
    timeout_seconds: int = 1800,
    poll_interval: float = 5.0,
    pid: int | None = None,
    pid_starttime: str | None = None,
    run_id: str | None = None,
    json_output: bool = False,
) -> int:
    """Block until the exact-head review receipt exists, then return its verdict.

    This primitive keeps an entire review lifecycle inside one command.  A
    caller that starts a review and hands control back to an interactive session
    has to be *resumed* when the review ends, and every hand-rolled watcher that
    tried to detect that end failed structurally: the harness writes
    ``codex-review-receipt-<head12>-<runid>.json`` and never a fixed name, and
    ``pgrep -f`` matches the watcher's own command line.  Waiting inside one
    blocking command removes the resume requirement instead of trying to
    satisfy it.

    The exit status is the receipt's verdict: ``0`` reviewed PASS with no
    blocking findings, ``3`` reviewed FAIL or any blocking finding, ``1`` no
    verdict could be established.  The third case is always reported as an
    explicit failure state — never a silent return of control, and never a
    traceback: an input the wait cannot use is refused in the same structured
    shape as every other failure.

    A candidate whose body names a different ``reviewed_head_sha`` than the one
    requested is refused outright rather than skipped: the writer derives both
    the filename and that field from the same normalized value, so a mismatch
    can only mean corruption or tampering.  Likewise the newest readable
    candidate is authoritative — falling back to an older receipt for the same
    head would be exactly the stale-evidence acceptance this must prevent.

    "Newest" is only consulted when the round is unknown.  A head can be
    reviewed again after its findings are fixed, and then the directory holds
    two verdicts for one head name; the receipt of the round being waited for
    is identified by its run id — ``run_id`` when the caller names the round,
    otherwise the run id published in the writer's own launch record — and a
    receipt from another round is reported but never consumed.  Naming the round
    up front is also what removes the publication race: ``--run-id`` is known
    before the writer starts, whereas the launch record appears only once it
    has.

    Liveness is checked only as a bounded early exit, and only against a pid
    bound to a ``/proc`` start time: the caller's explicit ``pid``/``pid_starttime``
    pair, otherwise the identity the writer published at launch.  A ``pid`` with
    no ``pid_starttime`` is refused before the wait starts, because the only
    start time available for it would be one the pid itself supplies.  With
    neither source there is no probe at all — the wait then runs to its deadline
    and says so, rather than guessing that the writer died.
    """

    directory = Path(evidence_dir)
    interval = max(float(poll_interval), 0.05)
    started = time.monotonic()
    head_fault: str | None = None
    requested_head = ""
    try:
        requested_head = normalize_full_sha(head_sha, role="waited-for head SHA")
    except ExactHeadError as exc:
        # A head that cannot be normalized is a refusal, not a crash: the wait
        # has not started, and a caller reading stdout (the only stream a machine
        # caller has under --json) must still receive one structured line.
        head_fault = str(exc)
    pattern = REVIEW_RECEIPT_GLOB.format(head12=requested_head[:12])
    deadline = started + timeout_seconds
    # Set once the wait is genuinely watching for a writer.  A refusal before
    # that point reports no writer identity at all: nothing was probed, and
    # naming a pid there would suggest it had been accepted as the writer's.
    watching = False
    probe = _WriterProbe(
        pid,
        starttime=pid_starttime,
        directory=directory,
        pattern=writer_identity_pattern(requested_head),
        expected_head=requested_head,
    )
    progress = _WaitProgress(sys.stderr if json_output else sys.stdout)

    def report(state: str, detail: str, exit_code: int, **extra: Any) -> int:
        payload: dict[str, Any] = {
            "state": state,
            "status": "PASS" if exit_code == EXIT_REVIEW_PASS else "FAIL",
            # Echo the input as given when it could not be normalized, so the
            # refusal names what the caller actually passed.
            "head_sha": requested_head or str(head_sha),
            "evidence_dir": str(directory),
            "detail": detail,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "writer_pid": probe.pid if watching else None,
            "writer_identity_source": probe.source if watching else "none",
        }
        payload.update(extra)
        print(json.dumps(payload, ensure_ascii=False), flush=True)
        return exit_code

    def fail(state: str, detail: str, **extra: Any) -> int:
        """Report one terminal failure to both streams and return its status."""

        progress.announce(state, detail)
        print(f"INDEPENDENT_REVIEW_WAIT=FAIL: {detail}", file=sys.stderr)
        return report(state, detail, EXIT_REVIEW_INFRASTRUCTURE_ERROR, **extra)

    start_refusal = _wait_start_refusal(
        directory, timeout_seconds, pid, pid_starttime, run_id, head_fault
    )
    if start_refusal is not None:
        return fail(WAIT_STATE_REVIEW_FAILED, start_refusal)

    watching = True
    watched_run = run_id
    writer_pattern = writer_identity_pattern(requested_head)
    progress.announce(
        WAIT_STATE_PARENT_WAITING,
        f"head={requested_head} evidence_dir={directory} timeout={timeout_seconds}s"
        f"{f' run={watched_run}' if watched_run is not None else ''}",
    )
    while True:
        if watched_run is None:
            watched_run = _watched_round(directory, writer_pattern, requested_head)
        found, unreadable = _receipt_candidates(directory, pattern)
        mine, other_rounds = _split_by_round(found, requested_head, watched_run)
        # Every terminal outcome of this round names the round and the receipts
        # it declined to consume, so a caller never has to infer which of several
        # verdicts for one head it just received.
        round_extra: dict[str, Any] = {
            "review_run_id": watched_run,
            "receipts_from_other_rounds": [p.name for p in other_rounds],
        }
        if mine:
            try:
                candidate, review_result, blocking, counts = _candidate_verdict(
                    mine, requested_head
                )
            except ReviewReceiptError as exc:
                return fail(WAIT_STATE_REVIEW_FAILED, str(exc), **round_extra)
            exit_code = verdict_exit_code(review_result, blocking)
            detail = _success_detail(
                candidate,
                review_result,
                blocking,
                found,
                run_id=watched_run,
                other_rounds=other_rounds,
            )
            progress.announce(WAIT_STATE_REVIEW_FINISHED, detail)
            progress.announce(WAIT_STATE_PARENT_CONTINUING, f"exit={exit_code}")
            return report(
                WAIT_STATE_REVIEW_FINISHED,
                detail,
                exit_code,
                review_receipt=str(candidate),
                review_result=review_result,
                blocking_findings=blocking,
                finding_counts_by_severity=counts,
                receipt_candidates=[p.name for p in found],
                **round_extra,
            )
        if time.monotonic() >= deadline:
            state, detail = _timeout_outcome(
                unreadable=unreadable,
                requested_head=requested_head,
                timeout_seconds=timeout_seconds,
                directory=directory,
                pattern=pattern,
                watched_run=watched_run,
                other_rounds=other_rounds,
            )
            return fail(state, detail, **round_extra)
        if not probe.alive():
            detail = (
                f"writer pid {probe.pid} (identity from {probe.source}) exited without "
                f"producing a receipt for head {requested_head} in {directory}"
                f"{f' (watched run {watched_run})' if watched_run is not None else ''}"
                f"{_other_round_note(other_rounds)}"
            )
            return fail(WAIT_STATE_REVIEW_FAILED, detail, **round_extra)
        progress.announce(
            WAIT_STATE_REVIEW_RUNNING,
            f"no receipt yet for head={requested_head} "
            f"({round(time.monotonic() - started, 1)}s elapsed)",
        )
        time.sleep(min(interval, max(deadline - time.monotonic(), 0.0)))
