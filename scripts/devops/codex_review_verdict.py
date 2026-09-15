#!/usr/bin/env python3
"""把 independent review 的 receipt verdict 投影成 exit status，并提供阻塞式等待。

lifecycle: permanent
owner: engineering workflow governance

本模块是 ``codex_independent_review`` 的 verdict 与等待层，单独成文件是为了让 reviewer
CLI 主体保持在一个可评审的模块长度内。它不启动 reviewer，也不解析 Codex 输出。

* ``read_receipt_verdict`` 回读 receipt、重算 payload integrity digest，并把
  ``review_result``/``blocking_findings`` 变成 verdict。receipt 是唯一 authority，
  stdout 与 exit status 都只是它的投影。
* exit-status contract：``0`` = 已审 PASS 且无 blocking finding，``3`` = 已审 FAIL 或
  存在任何 blocking finding，``1`` = 无法建立 verdict。
* ``wait_for_receipt`` 在**一个**阻塞命令内等到 exact-head receipt 出现并返回它的
  verdict，因此整个 review lifecycle 不需要"子进程结束后唤醒父 agent"这一机制。它按
  ``codex-review-receipt-<head12>-<runid>.json`` 轮询真实产物、只做数字 pid 存活探测
  （``pgrep -f`` 会匹配 watcher 自己的命令行），并在超时、writer 异常退出、receipt 缺失
  或 head 不匹配时以显式失败状态结束，绝不静默交还控制权。
* receipt 的 ``receipt_payload_sha256`` 是**可重算**的完整性字段：它只能证明 receipt
  内部自洽，不能证明它由本项目的 reviewer 产出。因此 ``wait`` 在读 verdict 前先要求
  evidence directory 为 owner-only（``0700``）、receipt 本身亦为 owner-only
  （``0600``）且属于当前 uid；否则任何能往该目录写入的进程都能伪造一份自洽的
  exact-head PASS。读取侧与写入侧（``_ensure_private_directory``）共用
  ``assert_owner_only_directory``，规则只有一条。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.devops.codex_review_contract import _canonical_json, sha256_bytes  # noqa: E402
from scripts.devops.codex_review_provenance import ReviewReceiptError  # noqa: E402
from scripts.devops.exact_head import normalize_full_sha  # noqa: E402

# Exit-status contract for the ``run`` and ``wait`` subcommands.  A receipt is
# the authority for the reviewed verdict, so the process exit status must carry
# that verdict and never merely "a receipt file was written".  A caller that
# follows the ordinary Unix contract (exit 0 == success) must never be able to
# mistake a review that produced blocking findings for a passing one.
EXIT_REVIEW_PASS = 0
EXIT_REVIEW_INFRASTRUCTURE_ERROR = 1
EXIT_REVIEW_BLOCKING_FINDINGS = 3

# ``wait`` states.  Every one of them is reported explicitly; the workflow is
# never silently returned to the caller without a verdict.
WAIT_STATE_PARENT_WAITING = "PARENT_WAITING"
WAIT_STATE_REVIEW_RUNNING = "REVIEW_RUNNING"
WAIT_STATE_REVIEW_FINISHED = "REVIEW_FINISHED"
WAIT_STATE_REVIEW_FAILED = "REVIEW_FAILED"
WAIT_STATE_RECEIPT_MISSING = "RECEIPT_MISSING"
WAIT_STATE_PARENT_CONTINUING = "PARENT_CONTINUING"

# The writer owns this naming rule; ``wait`` only reads it back.  The receipt
# filename binds the head at 12 hex characters, which is the same prefix the
# receipt body records in ``reviewed_head_sha``.
REVIEW_RECEIPT_GLOB = "codex-review-receipt-{head12}-*.json"


def assert_owner_only_directory(path: Path) -> None:
    """Refuse an evidence directory another uid could have written into.

    The receipt payload digest is a *recomputable* integrity field, so it
    proves a receipt is internally consistent, not that this project's reviewer
    produced it.  Anything that can create a file in the evidence directory can
    therefore mint a self-consistent exact-head PASS receipt and have ``wait``
    report it as a verdict.  Owner-only access is what closes that gap, and it
    is the same constraint the writing side already applies.
    """

    try:
        info = path.stat()
    except OSError as exc:
        raise ReviewReceiptError(f"无法读取 evidence directory metadata: {path}: {exc}") from exc
    if not stat.S_ISDIR(info.st_mode):
        raise ReviewReceiptError(f"evidence path 不是目录: {path}")
    _assert_owner_only(info, path, kind="evidence directory", expected_mode=0o700)


def assert_owner_only_file(path: Path) -> None:
    """Refuse a receipt file another uid could have created or replaced."""

    try:
        info = path.stat()
    except OSError as exc:
        raise ReviewReceiptError(f"无法读取 receipt metadata: {path}: {exc}") from exc
    if not stat.S_ISREG(info.st_mode):
        raise ReviewReceiptError(f"receipt 不是普通文件: {path}")
    _assert_owner_only(info, path, kind="receipt", expected_mode=0o600)


def _assert_owner_only(info: os.stat_result, path: Path, *, kind: str, expected_mode: int) -> None:
    """Shared owner/group/other check for one evidence path."""

    if info.st_uid != os.getuid():
        raise ReviewReceiptError(
            f"{kind} 的 owner uid={info.st_uid} 与当前进程 uid={os.getuid()} 不一致: {path}"
        )
    mode = stat.S_IMODE(info.st_mode)
    if mode & 0o077:
        raise ReviewReceiptError(
            f"{kind} 必须只对 owner 开放（期望 {oct(expected_mode)}）: {path} (mode={oct(mode)})"
        )


def read_receipt_verdict(
    receipt_path: Path, *, expected_head: str | None = None
) -> tuple[str, int, dict[str, int]]:
    """Read a written receipt back from disk and derive its verdict.

    The file is read back rather than trusting the in-memory document: doing so
    also proves the receipt was persisted in a form a later consumer can load,
    and recomputing the payload digest proves the bytes on disk are the bytes
    that were signed over.  A ``None`` verdict is not representable here: an
    unreadable, digest-mismatched, wrong-head or non-verdict receipt raises
    instead of degrading into an accidental PASS.
    """

    try:
        receipt = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ReviewReceiptError(f"无法回读已写入的 receipt: {receipt_path}: {exc}") from exc
    if not isinstance(receipt, dict):
        raise ReviewReceiptError(f"receipt 必须是 object: {receipt_path}")
    unsigned = dict(receipt)
    integrity = unsigned.pop("integrity", None)
    if not isinstance(integrity, dict) or not isinstance(
        integrity.get("receipt_payload_sha256"), str
    ):
        raise ReviewReceiptError(f"receipt 缺少 payload integrity: {receipt_path}")
    if integrity["receipt_payload_sha256"] != sha256_bytes(_canonical_json(unsigned)):
        raise ReviewReceiptError(f"receipt payload integrity 不匹配: {receipt_path}")
    if expected_head is not None:
        receipt_head = str(receipt.get("reviewed_head_sha") or "").lower()
        if receipt_head != expected_head:
            raise ReviewReceiptError(
                f"receipt 绑定的 reviewed_head_sha={receipt_head or 'MISSING'} "
                f"与请求的 head={expected_head} 不一致: {receipt_path}"
            )
    review_result = str(receipt.get("review_result") or "").upper()
    if review_result not in {"PASS", "FAIL"}:
        raise ReviewReceiptError(f"receipt.review_result 非法: {review_result!r}")
    blocking = receipt.get("blocking_findings")
    if not isinstance(blocking, int) or isinstance(blocking, bool):
        raise ReviewReceiptError(f"receipt.blocking_findings 非法: {blocking!r}")
    counts = receipt.get("finding_counts_by_severity")
    return review_result, blocking, (counts if isinstance(counts, dict) else {})


def verdict_exit_code(review_result: str, blocking_findings: int) -> int:
    """Map a receipt verdict onto the process exit status."""

    if review_result == "PASS" and blocking_findings == 0:
        return EXIT_REVIEW_PASS
    return EXIT_REVIEW_BLOCKING_FINDINGS


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


def _process_identity(pid: int) -> str | None:
    """Identify one running process as ``<state>:<starttime>``, or None if gone.

    Two observations of the same pid with different start times are two
    different processes, which is how pid recycling is caught.
    """

    fields = _proc_stat_tail(pid)
    if fields is None or len(fields) <= _PROC_STAT_STARTTIME_INDEX:
        return None
    return f"{fields[_PROC_STAT_STATE_INDEX]}:{fields[_PROC_STAT_STARTTIME_INDEX]}"


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
    """Decide whether an explicitly-named writer process is still running.

    A pattern probe cannot answer this question, and this is the exact defect
    that stranded the incident this module is being repaired for: the watcher
    ran ``pgrep -f codex_independent_review``, the watcher's own command line
    contains that literal string, so the probe matched itself and the
    "writer has exited" branch was unreachable forever.  Only an explicit
    numeric pid can be probed honestly, and it is cross-checked against its
    start time so a recycled pid is never mistaken for the original writer.
    """

    def __init__(self, pid: int | None) -> None:
        self._pid = pid
        self._identity: str | None = None
        self._primed = False

    def alive(self) -> bool:
        """Return whether the named writer is still running.

        Returns ``True`` when no pid was supplied.  Absence of a probe is not
        evidence of death, and inventing one would abandon a healthy wait.
        """

        if self._pid is None:
            return True
        identity = _process_identity(self._pid)
        if identity is None:
            # No readable /proc entry: fall back to the existence probe alone.
            return _process_exists(self._pid)
        if identity.startswith("Z:"):
            return False
        if not self._primed:
            self._identity = identity
            self._primed = True
            return True
        return identity == self._identity


def _receipt_candidates(directory: Path, pattern: str) -> tuple[list[Path], Path | None]:
    """Return JSON-loadable candidates newest-first, plus one unreadable one.

    A writer observed mid-``_write_exclusive`` is a real state, not a verdict,
    so a candidate that does not yet parse is reported separately rather than
    treated as evidence.
    """

    def _mtime(path: Path) -> int:
        try:
            return path.stat().st_mtime_ns
        except OSError:
            return -1

    try:
        paths = [p for p in directory.glob(pattern) if p.is_file()]
    except OSError:
        return [], None
    paths.sort(key=lambda p: (_mtime(p), p.name), reverse=True)
    readable: list[Path] = []
    unreadable: Path | None = None
    for path in paths:
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


def _candidate_verdict(
    found: list[Path], requested_head: str
) -> tuple[Path, str, int, dict[str, int]]:
    """Derive the verdict of the newest readable candidate for one head.

    The candidate must also be owner-only.  A receipt another uid could have
    created or replaced is refused rather than skipped: the writer always emits
    ``0600`` files, so any other mode means the file is not the one this
    harness wrote, and accepting it would hand the verdict to whoever could
    write there.
    """

    candidate = found[0]
    assert_owner_only_file(candidate)
    review_result, blocking, counts = read_receipt_verdict(candidate, expected_head=requested_head)
    return candidate, review_result, blocking, counts


def _success_detail(candidate: Path, review_result: str, blocking: int, found: list[Path]) -> str:
    """Describe a settled verdict, naming the receipt that carries it."""

    detail = f"receipt={candidate} review_result={review_result} blocking_findings={blocking}"
    if len(found) > 1:
        detail += (
            " (NOTE: multiple receipts exist for this head; the newest by mtime was "
            "used, so use a fresh evidence directory per review round)"
        )
    return detail


def _wait_precondition_error(directory: Path, timeout_seconds: int) -> str | None:
    """Return why a wait cannot start at all, or None when it can."""

    if not directory.is_dir():
        return f"evidence directory 不存在: {directory}"
    if timeout_seconds <= 0:
        return f"--timeout-seconds 必须为正数: {timeout_seconds}"
    return None


def _timeout_outcome(
    *,
    unreadable: Path | None,
    requested_head: str,
    timeout_seconds: int,
    directory: Path,
    pattern: str,
) -> tuple[str, str]:
    """Describe why the deadline passed without establishing a verdict."""

    if unreadable is None:
        return WAIT_STATE_RECEIPT_MISSING, (
            f"no receipt for head {requested_head} after {timeout_seconds}s "
            f"in {directory} (pattern {pattern})"
        )
    return WAIT_STATE_REVIEW_FAILED, (
        f"receipt candidate present but never became a readable receipt "
        f"after {timeout_seconds}s: {unreadable}"
    )


def wait_for_receipt(
    *,
    evidence_dir: Path,
    head_sha: str,
    timeout_seconds: int = 1800,
    poll_interval: float = 5.0,
    pid: int | None = None,
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
    explicit failure state — never a silent return of control.

    A candidate whose body names a different ``reviewed_head_sha`` than the one
    requested is refused outright rather than skipped: the writer derives both
    the filename and that field from the same normalized value, so a mismatch
    can only mean corruption or tampering.  Likewise the newest readable
    candidate is authoritative — falling back to an older receipt for the same
    head would be exactly the stale-evidence acceptance this must prevent.
    """

    requested_head = normalize_full_sha(head_sha, role="waited-for head SHA")
    directory = Path(evidence_dir)
    precondition = _wait_precondition_error(directory, timeout_seconds)
    if precondition is not None:
        print(f"INDEPENDENT_REVIEW_WAIT=FAIL: {precondition}", file=sys.stderr)
        return EXIT_REVIEW_INFRASTRUCTURE_ERROR
    interval = max(float(poll_interval), 0.05)
    pattern = REVIEW_RECEIPT_GLOB.format(head12=requested_head[:12])
    started = time.monotonic()
    deadline = started + timeout_seconds
    probe = _WriterProbe(pid)
    progress = _WaitProgress(sys.stderr if json_output else sys.stdout)

    def report(state: str, detail: str, exit_code: int, **extra: Any) -> int:
        payload: dict[str, Any] = {
            "state": state,
            "status": "PASS" if exit_code == EXIT_REVIEW_PASS else "FAIL",
            "head_sha": requested_head,
            "evidence_dir": str(directory),
            "detail": detail,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "writer_pid": pid,
        }
        payload.update(extra)
        print(json.dumps(payload, ensure_ascii=False), flush=True)
        return exit_code

    def fail(state: str, detail: str) -> int:
        """Report one terminal failure to both streams and return its status."""

        progress.announce(state, detail)
        print(f"INDEPENDENT_REVIEW_WAIT=FAIL: {detail}", file=sys.stderr)
        return report(state, detail, EXIT_REVIEW_INFRASTRUCTURE_ERROR)

    try:
        assert_owner_only_directory(directory)
    except ReviewReceiptError as exc:
        return fail(WAIT_STATE_REVIEW_FAILED, str(exc))

    progress.announce(
        WAIT_STATE_PARENT_WAITING,
        f"head={requested_head} evidence_dir={directory} timeout={timeout_seconds}s",
    )
    while True:
        found, unreadable = _receipt_candidates(directory, pattern)
        if found:
            try:
                candidate, review_result, blocking, counts = _candidate_verdict(
                    found, requested_head
                )
            except ReviewReceiptError as exc:
                return fail(WAIT_STATE_REVIEW_FAILED, str(exc))
            exit_code = verdict_exit_code(review_result, blocking)
            detail = _success_detail(candidate, review_result, blocking, found)
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
            )
        if time.monotonic() >= deadline:
            state, detail = _timeout_outcome(
                unreadable=unreadable,
                requested_head=requested_head,
                timeout_seconds=timeout_seconds,
                directory=directory,
                pattern=pattern,
            )
            return fail(state, detail)
        if not probe.alive():
            return fail(
                WAIT_STATE_REVIEW_FAILED,
                f"writer pid {pid} exited without producing a receipt for head "
                f"{requested_head} in {directory}",
            )
        progress.announce(
            WAIT_STATE_REVIEW_RUNNING,
            f"no receipt yet for head={requested_head} "
            f"({round(time.monotonic() - started, 1)}s elapsed)",
        )
        time.sleep(min(interval, max(deadline - time.monotonic(), 0.0)))
