#!/usr/bin/env python3
"""把 independent review 的 receipt 投影成 verdict 与 exit status。

lifecycle: permanent
owner: engineering workflow governance

本模块是 ``codex_independent_review`` 的 verdict 层，也是 review 产物的命名与读取
规则所在：receipt 叫什么名字、怎么回读、怎么变成 verdict、evidence 必须满足什么权限，
都在这里定义。它不启动 reviewer、不解析 Codex 输出，也不等待任何进程——阻塞等待与
存活探测在 ``codex_review_wait``。

* ``read_receipt_verdict`` 回读 receipt、重算 payload integrity digest，并把
  ``review_result``/``blocking_findings`` 变成 verdict。receipt 是唯一 authority，
  stdout 与 exit status 都只是它的投影。
* exit-status contract：``0`` = 已审 PASS 且无 blocking finding，``3`` = 已审 FAIL 或
  存在任何 blocking finding，``1`` = 无法建立 verdict。
* receipt 的 ``receipt_payload_sha256`` 是**可重算**的完整性字段：它只能证明 receipt
  内部自洽，不能证明它由本项目的 reviewer 产出。因此读取侧先要求 evidence directory
  为 owner-only（``0700``）、receipt 本身亦为 owner-only（``0600``）且属于当前 uid；
  否则任何能往该目录写入的进程都能伪造一份自洽的 exact-head PASS。读取侧与写入侧
  （``_ensure_private_directory``）共用 ``assert_owner_only_directory``，规则只有一条。
* 一个 head 可以有多个 review round，产物文件名里的 run id 是**唯一**的轮次身份：它由
  writer 生成并写在每一份产物名里（``codex-review-receipt-<head12>-<runid>.json``、
  ``codex-review-writer-<head12>-<runid>.json``），因此"这轮是谁"可以从名字本身恢复，
  不需要打开 receipt 去猜。不允许 ``--run-id`` 给出命名规则不可能产生的值。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import stat
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.devops.codex_review_contract import _canonical_json, sha256_bytes  # noqa: E402
from scripts.devops.codex_review_provenance import ReviewReceiptError  # noqa: E402

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
REVIEW_RECEIPT_PREFIX = "codex-review-receipt-"
REVIEW_RECEIPT_GLOB = REVIEW_RECEIPT_PREFIX + "{head12}-*.json"

# The writer's own launch record.  It is a liveness hint, never evidence: it
# carries no verdict and is never read for one.
WRITER_IDENTITY_PREFIX = "codex-review-writer-"
WRITER_IDENTITY_GLOB = WRITER_IDENTITY_PREFIX + "{head12}-*.json"


def writer_identity_path(directory: Path, head_sha: str, run_id: str) -> Path:
    """Return the canonical path of one review run's writer identity record."""

    return directory / f"{WRITER_IDENTITY_PREFIX}{head_sha[:12]}-{run_id}.json"


def writer_identity_pattern(head_sha: str) -> str:
    """Return the glob ``wait`` uses to find a writer identity record."""

    return WRITER_IDENTITY_GLOB.format(head12=head_sha[:12])


# One review *round* is one ``run`` invocation.  A head that produced blocking
# findings is reviewed again after they are fixed, so two receipts under the
# same head name are two verdicts about two different source states, and the
# run id in the artifact name is the only thing that tells them apart.  The
# writer mints ``uuid4().hex``; the shape is pinned here so ``--run-id`` cannot
# smuggle in a value the naming rule could never have produced.
_RUN_ID_RE = re.compile(r"^[0-9a-f]{1,64}$")


def is_canonical_run_id(run_id: str) -> bool:
    """Return whether a run id has the shape the artifact naming rule produces."""

    return bool(_RUN_ID_RE.match(run_id))


def run_id_refusal(run_id: str) -> str:
    """Return why a run id cannot serve as a round identity."""

    return (
        f"--run-id 不是 canonical run id（小写 hex，1-64 位）: {run_id!r}"
        "（round identity 决定消费哪一份 receipt，无法核对的值不如不给出）"
    )


def assert_canonical_run_id(run_id: str | None) -> None:
    """Refuse a run id the artifact naming rule could not have produced."""

    if run_id is not None and not is_canonical_run_id(run_id):
        raise ReviewReceiptError(run_id_refusal(run_id))


def run_id_from_name(path: Path, prefix: str, head_sha: str) -> str | None:
    """Return the run id one evidence filename encodes, or None if it does not.

    Every artifact of a round is named ``<prefix><head12>-<runid>.json``, so
    the round a receipt belongs to is recoverable from its name alone.  That
    matters here because the receipt being opened *is* the thing in question:
    deciding which round a verdict speaks for must not depend on reading it.
    """

    name = path.name
    stem = f"{prefix}{head_sha[:12]}-"
    if not name.startswith(stem) or not name.endswith(".json"):
        return None
    return name[len(stem) : -len(".json")] or None


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
