"""Receipt-authoritative verdict propagation for the independent reviewer.

lifecycle: test-fixture

These tests pin the contract that made mission
``INVESTIGATE_AND_REPAIR_CODEX_REVIEW_PARENT_AUTO_RESUME`` necessary.  The
review process used to print ``{"status": "PASS"}`` and exit ``0`` no matter
what the receipt said, and there was no blocking primitive that turned a
receipt into a verdict, so callers launched reviews asynchronously and then
hand-rolled watchers that could not observe completion.  Both halves of that
failure are covered here: the exit status must carry the reviewed verdict, and
``wait`` must be able to establish that verdict inside one blocking command —
including when it has to refuse one.

The CLI/make invocation contract and the round-identity model are pinned in
``test_codex_review_wait_invocation_contract`` and
``test_codex_review_round_identity``.
"""

from __future__ import annotations

import json
import os
import stat
import time
from typing import TYPE_CHECKING

import pytest

from scripts.devops import codex_independent_review as reviewer
from scripts.devops.codex_review_provenance import ReviewReceiptError
from scripts.devops.codex_review_verdict import (
    EXIT_REVIEW_BLOCKING_FINDINGS,
    EXIT_REVIEW_INFRASTRUCTURE_ERROR,
    EXIT_REVIEW_PASS,
    REVIEW_RECEIPT_GLOB,
    WAIT_STATE_RECEIPT_MISSING,
    WAIT_STATE_REVIEW_FAILED,
    WAIT_STATE_REVIEW_FINISHED,
    read_receipt_verdict,
    verdict_exit_code,
)
from scripts.devops.codex_review_wait import _receipt_candidates, process_starttime
from tests.helpers.agentic_workflow_fixtures import make_repo

if TYPE_CHECKING:
    from pathlib import Path

from tests.helpers.codex_review_evidence_fixtures import (
    BLOCKING_FINDING,
    DELIBERATE_TIMEOUT_SECONDS,
    FAST_FAILURE_CEILING_SECONDS,
    OWNER_ONLY_DIRECTORY_MODE,
    OWNER_ONLY_FILE_MODE,
    SHORT_TIMEOUT_SECONDS,
    TWO_REVIEW_ROUNDS,
    git_output,
    payload_of,
    place_receipt,
    run_end_to_end,
    run_wait,
    seal_receipt,
)

# --------------------------------------------------------------------------
# The verdict must travel in the process exit status, not only in the receipt.
# --------------------------------------------------------------------------


def test_run_exit_status_carries_the_reviewed_verdict(tmp_path: Path) -> None:
    repo, base, head = make_repo(tmp_path)
    passing = seal_receipt(tmp_path, repo, base, head, slot="pass")
    failing = seal_receipt(
        tmp_path, repo, base, head, result="FAIL", finding=BLOCKING_FINDING, slot="fail"
    )

    verdict = read_receipt_verdict(passing)
    assert verdict[0] == "PASS"
    assert verdict[1] == 0
    assert verdict_exit_code(verdict[0], verdict[1]) == EXIT_REVIEW_PASS

    verdict = read_receipt_verdict(failing)
    assert verdict[0] == "FAIL"
    assert verdict[1] > 0
    assert verdict_exit_code(verdict[0], verdict[1]) == EXIT_REVIEW_BLOCKING_FINDINGS


def test_run_end_to_end_pass_exits_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, payload = run_end_to_end(tmp_path, monkeypatch, capsys, result="PASS", finding=None)
    assert exit_code == EXIT_REVIEW_PASS
    assert payload["status"] == "PASS"
    assert payload["review_result"] == "PASS"
    assert payload["finding_counts_by_severity"]["P2"] == 0


def test_run_end_to_end_fail_must_not_exit_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The defect this mission exists for, reproduced end to end.

    Against the unfixed wrapper this returned ``0`` and printed
    ``{"status": "PASS"}`` for a receipt whose own ``review_result`` was
    ``FAIL`` — a foreground caller was lied to exactly as loudly as a
    background one.
    """

    exit_code, payload = run_end_to_end(
        tmp_path, monkeypatch, capsys, result="FAIL", finding=BLOCKING_FINDING
    )
    assert exit_code == EXIT_REVIEW_BLOCKING_FINDINGS
    assert payload["status"] == "FAIL"
    assert payload["review_result"] == "FAIL"
    assert payload["blocking_findings"] == 1


def test_a_receipt_that_was_edited_after_sealing_is_refused(tmp_path: Path) -> None:
    """The `stdout PASS != receipt verdict` trap, pinned as a failing case.

    Rewriting ``review_result`` to ``PASS`` without resealing is exactly what a
    caller that trusted stdout would have believed.
    """

    repo, base, head = make_repo(tmp_path)
    sealed = seal_receipt(tmp_path, repo, base, head, result="FAIL", finding=BLOCKING_FINDING)
    document = json.loads(sealed.read_text(encoding="utf-8"))
    document["review_result"] = "PASS"
    document["blocking_findings"] = 0
    sealed.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ReviewReceiptError, match="integrity"):
        read_receipt_verdict(sealed)


# --------------------------------------------------------------------------
# CASE 1 / CASE 2 — the two honest outcomes.
# --------------------------------------------------------------------------


def test_wait_case_1_pass(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo, base, head = make_repo(tmp_path)
    evidence = tmp_path / "evidence-pass"
    place_receipt(
        evidence,
        seal_receipt(tmp_path, repo, base, head, slot="pass"),
        name_head=head,
        run_id="a" * 32,
    )

    assert run_wait(evidence, head) == EXIT_REVIEW_PASS
    payload = payload_of(capsys)
    assert payload["state"] == WAIT_STATE_REVIEW_FINISHED
    assert payload["status"] == "PASS"
    assert payload["review_result"] == "PASS"
    assert payload["blocking_findings"] == 0
    assert payload["head_sha"] == head


def test_wait_case_2_fail(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo, base, head = make_repo(tmp_path)
    evidence = tmp_path / "evidence-fail"
    place_receipt(
        evidence,
        seal_receipt(tmp_path, repo, base, head, result="FAIL", finding=BLOCKING_FINDING, slot="f"),
        name_head=head,
        run_id="b" * 32,
    )

    exit_code = run_wait(evidence, head)
    payload = payload_of(capsys)
    assert exit_code == EXIT_REVIEW_BLOCKING_FINDINGS
    assert exit_code != EXIT_REVIEW_PASS
    assert payload["state"] == WAIT_STATE_REVIEW_FINISHED
    assert payload["status"] == "FAIL"
    assert payload["review_result"] == "FAIL"
    assert payload["blocking_findings"] > 0


def test_wait_refuses_a_non_private_evidence_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A writable-by-others evidence directory can be seeded with a forged PASS.

    The payload digest is recomputable by anyone who can write the file, so a
    receipt that verifies is only meaningful when the directory it lives in is
    owner-only.  A group- or world-writable directory must be refused outright,
    not merely observed.
    """

    repo, base, head = make_repo(tmp_path)
    evidence = tmp_path / "evidence-shared"
    place_receipt(
        evidence,
        seal_receipt(tmp_path, repo, base, head, slot="shared"),
        name_head=head,
        run_id="d" * 32,
    )
    evidence.chmod(0o777)

    exit_code = run_wait(evidence, head)
    payload = payload_of(capsys)
    assert exit_code == EXIT_REVIEW_INFRASTRUCTURE_ERROR
    assert exit_code != EXIT_REVIEW_PASS
    assert payload["state"] == WAIT_STATE_REVIEW_FAILED


def test_wait_refuses_a_receipt_another_uid_could_have_written(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The writer always emits 0600, so any other mode is not its output."""

    repo, base, head = make_repo(tmp_path)
    evidence = tmp_path / "evidence-loose"
    placed = place_receipt(
        evidence,
        seal_receipt(tmp_path, repo, base, head, slot="loose"),
        name_head=head,
        run_id="e" * 32,
    )
    placed.chmod(0o644)

    exit_code = run_wait(evidence, head)
    payload = payload_of(capsys)
    assert exit_code == EXIT_REVIEW_INFRASTRUCTURE_ERROR
    assert exit_code != EXIT_REVIEW_PASS
    assert payload["state"] == WAIT_STATE_REVIEW_FAILED


def test_the_writer_side_refuses_a_directory_that_is_not_owner_only(tmp_path: Path) -> None:
    """`run` and `wait` must apply one rule, not two."""

    evidence = tmp_path / "evidence-writer-side"
    evidence.mkdir(mode=0o700)
    reviewer._ensure_private_directory(evidence)
    evidence.chmod(0o750)
    with pytest.raises(ReviewReceiptError):
        reviewer._ensure_private_directory(evidence)


# --------------------------------------------------------------------------
# CASE 3 — the review child dies without ever writing a receipt.
# --------------------------------------------------------------------------
# A pid is not an identity: the writer publishes the one it can be held to.
# --------------------------------------------------------------------------
def test_run_publishes_the_writer_identity_it_can_be_held_to(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`wait` can only verify a launched writer if the writer said who it was."""

    evidence = tmp_path / "identity-evidence"
    evidence.mkdir(mode=0o700)
    exit_code, _ = run_end_to_end(
        tmp_path, monkeypatch, capsys, result="PASS", finding=None, evidence=evidence
    )
    records = sorted(evidence.glob("codex-review-writer-*.json"))
    assert exit_code == EXIT_REVIEW_PASS
    assert len(records) == 1, "exactly one launch record per review run"
    record = json.loads(records[0].read_text(encoding="utf-8"))
    assert record["pid"] == os.getpid()
    assert record["starttime"] == process_starttime(os.getpid())
    assert stat.S_IMODE(records[0].stat().st_mode) == OWNER_ONLY_FILE_MODE
    assert stat.S_IMODE(evidence.stat().st_mode) == OWNER_ONLY_DIRECTORY_MODE


# --------------------------------------------------------------------------
# CASE 4 — a receipt for a head that is no longer the reviewed head.
# --------------------------------------------------------------------------


def test_wait_case_4_superseded_head_receipt_is_not_accepted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo, base, head = make_repo(tmp_path)
    (repo / "Makefile").write_text("all:\n\t@echo repaired\n", encoding="utf-8")
    git_output(repo, "add", "Makefile")
    git_output(repo, "commit", "-qm", "repair")
    repaired_head = git_output(repo, "rev-parse", "HEAD")

    # A genuine, sealed PASS receipt for the superseded head sits in the very
    # same evidence directory the caller is watching.
    evidence = tmp_path / "evidence-superseded"
    place_receipt(
        evidence,
        seal_receipt(tmp_path, repo, base, head, slot="old"),
        name_head=head,
        run_id="c" * 32,
    )

    exit_code = run_wait(evidence, repaired_head, timeout_seconds=SHORT_TIMEOUT_SECONDS)
    payload = payload_of(capsys)
    assert exit_code == EXIT_REVIEW_INFRASTRUCTURE_ERROR
    assert exit_code != EXIT_REVIEW_PASS
    assert payload["state"] == WAIT_STATE_RECEIPT_MISSING
    assert payload["head_sha"] == repaired_head


def test_wait_case_4_newest_receipt_wins_over_an_older_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Never fall back to the older PASS once a later round has spoken."""

    repo, base, head = make_repo(tmp_path)
    evidence = tmp_path / "evidence-two-rounds"
    place_receipt(
        evidence,
        seal_receipt(tmp_path, repo, base, head, slot="r1"),
        name_head=head,
        run_id="d" * 32,
        mtime=1_700_000_000,
    )
    place_receipt(
        evidence,
        seal_receipt(
            tmp_path, repo, base, head, result="FAIL", finding=BLOCKING_FINDING, slot="r2"
        ),
        name_head=head,
        run_id="e" * 32,
        mtime=1_700_000_100,
    )

    exit_code = run_wait(evidence, head)
    payload = payload_of(capsys)
    assert exit_code == EXIT_REVIEW_BLOCKING_FINDINGS
    assert payload["review_result"] == "FAIL"
    assert len(payload["receipt_candidates"]) == TWO_REVIEW_ROUNDS
    assert "multiple receipts" in payload["detail"]


# --------------------------------------------------------------------------
# CASE 5 — the file name says one head and the receipt body says another.
# --------------------------------------------------------------------------


def test_wait_case_5_wrong_reviewed_head_sha_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo, base, head = make_repo(tmp_path)
    evidence = tmp_path / "evidence-wrong-head"
    # Sealed for `base`, but filed under `head`'s name: the integrity digest is
    # valid, so only the explicit head binding can catch this.
    place_receipt(
        evidence,
        seal_receipt(tmp_path, repo, base, base, slot="wrong"),
        name_head=head,
        run_id="f" * 32,
    )

    started = time.monotonic()
    exit_code = run_wait(evidence, head, timeout_seconds=DELIBERATE_TIMEOUT_SECONDS)
    elapsed = time.monotonic() - started
    payload = payload_of(capsys)
    assert exit_code == EXIT_REVIEW_INFRASTRUCTURE_ERROR
    assert exit_code != EXIT_REVIEW_PASS
    assert payload["state"] == WAIT_STATE_REVIEW_FAILED
    assert "reviewed_head_sha" in payload["detail"]
    assert elapsed < FAST_FAILURE_CEILING_SECONDS, (
        "a wrong-head receipt must be refused, not waited out"
    )


# --------------------------------------------------------------------------
# Boundedness: absence and partial writes are explicit failure states.
# --------------------------------------------------------------------------


def test_wait_reports_a_missing_receipt_instead_of_returning_control(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    evidence = tmp_path / "evidence-empty"
    evidence.mkdir(mode=0o700)

    exit_code = run_wait(evidence, "1" * 40, timeout_seconds=SHORT_TIMEOUT_SECONDS)
    payload = payload_of(capsys)
    assert exit_code == EXIT_REVIEW_INFRASTRUCTURE_ERROR
    assert payload["state"] == WAIT_STATE_RECEIPT_MISSING
    assert payload["status"] == "FAIL"
    assert payload["elapsed_seconds"] >= SHORT_TIMEOUT_SECONDS


def test_wait_reports_a_missing_evidence_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A wait that cannot even start still reports why, in the same shape."""

    exit_code = run_wait(tmp_path / "absent", "2" * 40)
    payload = payload_of(capsys)
    assert exit_code == EXIT_REVIEW_INFRASTRUCTURE_ERROR
    assert payload["state"] == WAIT_STATE_REVIEW_FAILED
    assert "evidence directory 不存在" in payload["detail"]


def test_a_partially_written_receipt_is_not_a_verdict(tmp_path: Path) -> None:
    repo, base, head = make_repo(tmp_path)
    evidence = tmp_path / "evidence-partial"
    evidence.mkdir(mode=0o700)
    sealed = seal_receipt(tmp_path, repo, base, head, slot="partial")
    partial = evidence / f"codex-review-receipt-{head[:12]}-{'9' * 32}.json"
    partial.write_bytes(sealed.read_bytes()[:120])

    readable, unreadable = _receipt_candidates(
        evidence, REVIEW_RECEIPT_GLOB.format(head12=head[:12])
    )
    assert readable == []
    assert unreadable == partial


def test_a_completed_receipt_is_picked_up_after_a_partial_one(tmp_path: Path) -> None:
    """A partial write must not block the real receipt that follows it."""

    repo, base, head = make_repo(tmp_path)
    evidence = tmp_path / "evidence-recovering"
    evidence.mkdir(mode=0o700)
    sealed = seal_receipt(tmp_path, repo, base, head, slot="recovering")
    partial = evidence / f"codex-review-receipt-{head[:12]}-{'9' * 32}.json"
    partial.write_bytes(sealed.read_bytes()[:120])
    complete = place_receipt(evidence, sealed, name_head=head, run_id="8" * 32, mtime=1_700_000_500)

    readable, unreadable = _receipt_candidates(
        evidence, REVIEW_RECEIPT_GLOB.format(head12=head[:12])
    )
    assert readable == [complete]
    assert unreadable == partial


# --------------------------------------------------------------------------
# The launch contract the incident violated.
# --------------------------------------------------------------------------


def test_wait_binds_to_the_real_receipt_name_not_a_fixed_one(tmp_path: Path) -> None:
    """A fixed `review-receipt.json` name is invisible to the writer."""

    repo, base, head = make_repo(tmp_path)
    evidence = tmp_path / "evidence-naming"
    evidence.mkdir(mode=0o700)
    (evidence / "review-receipt.json").write_bytes(
        seal_receipt(tmp_path, repo, base, head, slot="naming").read_bytes()
    )

    readable, unreadable = _receipt_candidates(
        evidence, REVIEW_RECEIPT_GLOB.format(head12=head[:12])
    )
    assert readable == []
    assert unreadable is None
    assert run_wait(evidence, head, timeout_seconds=1) == EXIT_REVIEW_INFRASTRUCTURE_ERROR
