"""One head, many review rounds: the verdict must name its round.

lifecycle: test-fixture

A head is reviewed again after findings are fixed, and the new review reuses
the evidence directory.  Both verdicts then live under one head name, and
"newest by mtime" is a guess about which round the caller is asking about: it
let an older round's PASS answer a wait that was started for a newer round,
which is the same class of stale-evidence acceptance the exact-head binding
exists to prevent.  A round is identified by its run id, which every artifact
of that round carries in its name, so the round can be recovered from the
artifact name alone rather than inferred from a timestamp.
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from scripts.devops import codex_independent_review as reviewer
from scripts.devops.codex_review_verdict import (
    EXIT_REVIEW_BLOCKING_FINDINGS,
    EXIT_REVIEW_INFRASTRUCTURE_ERROR,
    EXIT_REVIEW_PASS,
    REVIEW_RECEIPT_PREFIX,
    WAIT_STATE_RECEIPT_MISSING,
    WAIT_STATE_REVIEW_FAILED,
    WRITER_IDENTITY_PREFIX,
    is_canonical_run_id,
    run_id_from_name,
)
from scripts.devops.codex_review_wait import process_starttime
from tests.helpers.agentic_workflow_fixtures import MISSION_ID, make_repo
from tests.helpers.codex_review_evidence_fixtures import (
    BLOCKING_FINDING,
    DELIBERATE_TIMEOUT_SECONDS,
    SHORT_TIMEOUT_SECONDS,
    TWO_REVIEW_ROUNDS,
    payload_of,
    place_receipt,
    record_writer,
    run_end_to_end,
    run_wait,
    seal_receipt,
)

# --------------------------------------------------------------------------
# TEST E / TEST F — one head, two rounds: the verdict must name its round.
# --------------------------------------------------------------------------
# A head is reviewed again after findings are fixed, and the new review reuses
# the evidence directory.  Both verdicts then live under one head name, and
# "newest by mtime" is a guess about which round the caller is asking about: it
# let an older round's PASS answer a wait that was started for a newer round,
# which is the same class of stale-evidence acceptance the exact-head binding
# exists to prevent.  A round is identified by its run id, which every artifact
# of that round carries in its name.


def test_round_identity_is_recoverable_from_the_artifact_name() -> None:
    """The naming rule is the model: every artifact of a round names the round."""

    head = "0c33c078" + "0" * 32
    receipt = Path(f"{REVIEW_RECEIPT_PREFIX}{head[:12]}-{'a' * 32}.json")
    writer = Path(f"{WRITER_IDENTITY_PREFIX}{head[:12]}-{'a' * 32}.json")
    assert run_id_from_name(receipt, REVIEW_RECEIPT_PREFIX, head) == "a" * 32
    assert run_id_from_name(writer, WRITER_IDENTITY_PREFIX, head) == "a" * 32
    # A name that encodes nothing must not be read as a round.
    assert run_id_from_name(Path("review-receipt.json"), REVIEW_RECEIPT_PREFIX, head) is None
    assert (
        run_id_from_name(
            Path(f"{REVIEW_RECEIPT_PREFIX}{head[:12]}-.json"), REVIEW_RECEIPT_PREFIX, head
        )
        is None
    )
    assert run_id_from_name(receipt, REVIEW_RECEIPT_PREFIX, "f" * 40) is None
    assert is_canonical_run_id("a" * 32)
    assert not is_canonical_run_id("A" * 32)
    assert not is_canonical_run_id("")


def test_wait_does_not_consume_another_round_pass_for_a_live_round(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The reproduced defect, pinned: an older PASS must not answer a newer round.

    Round A's PASS receipt is in the directory and is newer by mtime than
    nothing else — under the unfixed selection it satisfied the wait
    immediately with ``writer_pid=None`` while round B's writer was still
    running, so a caller waiting on B was told A's verdict.
    """

    repo, base, head = make_repo(tmp_path)
    evidence = tmp_path / "evidence-live-newer-round"
    place_receipt(
        evidence,
        seal_receipt(tmp_path, repo, base, head, slot="round-a"),
        name_head=head,
        run_id="a" * 32,
    )
    record_writer(evidence, head, run_id="b" * 32)

    exit_code = run_wait(evidence, head, timeout_seconds=SHORT_TIMEOUT_SECONDS)
    payload = payload_of(capsys)
    assert exit_code != EXIT_REVIEW_PASS, "round A's PASS cannot speak for round B"
    assert payload["state"] == WAIT_STATE_RECEIPT_MISSING
    assert payload["review_run_id"] == "b" * 32
    assert payload["receipts_from_other_rounds"] == [
        f"{REVIEW_RECEIPT_PREFIX}{head[:12]}-{'a' * 32}.json"
    ]


def test_wait_does_not_consume_another_round_pass_after_that_writer_died(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A dead writer is still not a licence to accept a sibling round's verdict."""

    repo, base, head = make_repo(tmp_path)
    evidence = tmp_path / "evidence-dead-newer-round"
    place_receipt(
        evidence,
        seal_receipt(tmp_path, repo, base, head, slot="round-a-dead"),
        name_head=head,
        run_id="a" * 32,
    )
    reaped = subprocess.Popen(["sh", "-c", "exit 0"])
    reaped.wait()
    assert process_starttime(reaped.pid) is None
    record_writer(evidence, head, run_id="c" * 32, pid=reaped.pid, starttime="12345")

    exit_code = run_wait(evidence, head, timeout_seconds=DELIBERATE_TIMEOUT_SECONDS)
    payload = payload_of(capsys)
    assert exit_code != EXIT_REVIEW_PASS
    assert payload["state"] == WAIT_STATE_REVIEW_FAILED
    assert "exited without producing a receipt" in payload["detail"]
    assert payload["review_run_id"] == "c" * 32


def test_wait_named_round_cannot_consume_another_round_receipt(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """TEST F: the waiter for run A must not be answered by run B's receipt.

    Round B's receipt is the only one present and it is a FAIL, so an
    mtime-based waiter would report run B's verdict to a caller that asked for
    run A.  Naming the round turns that into an explicit "A has no receipt".
    """

    repo, base, head = make_repo(tmp_path)
    evidence = tmp_path / "evidence-named-round"
    place_receipt(
        evidence,
        seal_receipt(
            tmp_path, repo, base, head, result="FAIL", finding=BLOCKING_FINDING, slot="round-b"
        ),
        name_head=head,
        run_id="b" * 32,
    )

    exit_code = run_wait(evidence, head, timeout_seconds=SHORT_TIMEOUT_SECONDS, run_id="a" * 32)
    payload = payload_of(capsys)
    assert exit_code == EXIT_REVIEW_INFRASTRUCTURE_ERROR, "run A established no verdict here"
    assert exit_code != EXIT_REVIEW_BLOCKING_FINDINGS, "run B's FAIL is not run A's answer either"
    assert payload["state"] == WAIT_STATE_RECEIPT_MISSING
    assert payload["review_run_id"] == "a" * 32
    assert "review_result" not in payload, "a wait that established nothing reports no verdict"
    assert "other review rounds" in payload["detail"]


def test_wait_named_round_takes_its_own_receipt_even_when_a_newer_one_exists(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Naming a round is a selection, not a preference: mtime decides nothing."""

    repo, base, head = make_repo(tmp_path)
    evidence = tmp_path / "evidence-named-round-own"
    place_receipt(
        evidence,
        seal_receipt(tmp_path, repo, base, head, slot="own"),
        name_head=head,
        run_id="a" * 32,
        mtime=1_700_000_000,
    )
    place_receipt(
        evidence,
        seal_receipt(
            tmp_path, repo, base, head, result="FAIL", finding=BLOCKING_FINDING, slot="newer"
        ),
        name_head=head,
        run_id="b" * 32,
        mtime=1_700_000_900,
    )

    exit_code = run_wait(evidence, head, run_id="a" * 32)
    payload = payload_of(capsys)
    assert exit_code == EXIT_REVIEW_PASS
    assert payload["review_result"] == "PASS"
    assert payload["review_run_id"] == "a" * 32
    assert (
        run_id_from_name(Path(payload["review_receipt"]), REVIEW_RECEIPT_PREFIX, head) == "a" * 32
    )
    assert len(payload["receipt_candidates"]) == TWO_REVIEW_ROUNDS, "both rounds stay visible"
    assert payload["receipts_from_other_rounds"] == [
        f"{REVIEW_RECEIPT_PREFIX}{head[:12]}-{'b' * 32}.json"
    ]


def test_wait_keeps_watching_until_the_named_round_writes_its_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The end-to-end shape of the fix: round B's own receipt settles round B."""

    repo, base, head = make_repo(tmp_path)
    evidence = tmp_path / "evidence-two-real-rounds"
    evidence.mkdir(mode=0o700)
    place_receipt(
        evidence,
        seal_receipt(tmp_path, repo, base, head, slot="stale-pass"),
        name_head=head,
        run_id="a" * 32,
    )

    exit_code, run_payload = run_end_to_end(
        tmp_path,
        monkeypatch,
        capsys,
        result="FAIL",
        finding=BLOCKING_FINDING,
        evidence=evidence,
        run_id="b" * 32,
        repo_state=(repo, base, head),
    )
    assert exit_code == EXIT_REVIEW_BLOCKING_FINDINGS
    assert (
        run_id_from_name(Path(run_payload["review_receipt"]), REVIEW_RECEIPT_PREFIX, head)
        == "b" * 32
    )

    # Round A's PASS is still on disk and is still not the answer for round B.
    assert run_wait(evidence, head, run_id="a" * 32) == EXIT_REVIEW_PASS, (
        "round A's own receipt is still round A's verdict"
    )
    assert run_wait(evidence, head, run_id="b" * 32) == EXIT_REVIEW_BLOCKING_FINDINGS
    assert run_wait(evidence, head) == EXIT_REVIEW_BLOCKING_FINDINGS, (
        "without a named round the wait resolves to the writer record's round"
    )


def test_run_records_the_round_it_was_launched_with(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A caller that names the round at launch gets that name on every artifact."""

    evidence = tmp_path / "evidence-named-run"
    evidence.mkdir(mode=0o700)
    exit_code, payload = run_end_to_end(
        tmp_path,
        monkeypatch,
        capsys,
        result="PASS",
        finding=None,
        evidence=evidence,
        run_id="e" * 32,
    )
    assert exit_code == EXIT_REVIEW_PASS
    assert Path(payload["review_receipt"]).name.startswith(REVIEW_RECEIPT_PREFIX)
    assert Path(payload["review_receipt"]).name.endswith(f"-{'e' * 32}.json"), (
        "the receipt carries the round the caller named, not a minted one"
    )
    records = sorted(evidence.glob(f"{WRITER_IDENTITY_PREFIX}*.json"))
    assert len(records) == 1, "one round, one launch record"
    assert records[0].name.endswith(f"-{'e' * 32}.json")


def test_run_refuses_a_run_id_the_naming_rule_could_not_produce(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A round identity that could not have named a round is refused at launch."""

    exit_code = reviewer.main(
        [
            "run",
            "--repo-root",
            str(tmp_path),
            "--base-sha",
            "1" * 40,
            "--head-sha",
            "2" * 40,
            "--mission-id",
            MISSION_ID,
            "--mission-scope-file",
            str(tmp_path / "absent.json"),
            "--evidence-dir",
            str(tmp_path / "evidence-bad-run-id"),
            "--run-id",
            "../escape",
            "--json",
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == EXIT_REVIEW_INFRASTRUCTURE_ERROR
    assert "--run-id" in json.loads(captured.out)["error"]


# --------------------------------------------------------------------------
# The round names the artifact; the caller does not get to rename it.
# --------------------------------------------------------------------------
def test_run_refuses_to_move_this_rounds_receipt_out_of_the_evidence_directory(
    tmp_path: Path,
) -> None:
    """A receipt the wait cannot find is a round whose verdict nobody can establish.

    Round identity is carried by the artifact name inside the evidence
    directory, and `wait` consumes a round by scanning exactly that name.  A
    receipt written to another location, or under a name the naming rule could
    not have produced, belongs to no round any wait can name — so a launch that
    redirects it produces a review whose verdict is unreachable through the
    canonical single-command wait.  That is the ambiguity between rounds this
    model exists to remove, one layer down, so the launch entrypoint offers no
    such redirection and refuses it before any artifact is created.
    """

    evidence = tmp_path / "evidence-canonical-receipt"
    evidence.mkdir(mode=0o700)
    elsewhere = tmp_path / "elsewhere-receipt.json"
    with pytest.raises(SystemExit) as refusal:
        reviewer.main(
            [
                "run",
                "--repo-root",
                str(tmp_path),
                "--base-sha",
                "1" * 40,
                "--head-sha",
                "2" * 40,
                "--mission-id",
                MISSION_ID,
                "--mission-scope-file",
                str(tmp_path / "absent.json"),
                "--evidence-dir",
                str(evidence),
                "--receipt-path",
                str(elsewhere),
                "--json",
            ]
        )
    assert refusal.value.code != 0, "the redirection is refused, not honoured"
    assert not elsewhere.exists(), "no receipt may be written outside the evidence directory"
    assert not list(evidence.iterdir()), "the refusal lands before any artifact is created"


# --------------------------------------------------------------------------
# Every artifact of a round carries the whole run id, the worktree included.
# --------------------------------------------------------------------------
def test_two_rounds_of_one_head_whose_run_ids_share_a_prefix_both_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Two distinct rounds must not collide on a truncated round name.

    The run id is the round's identity, so a name that carries only a prefix of
    it is a name two rounds can share.  The worktree was named with
    ``run_id[:8]`` while the receipt, the writer record and the raw output all
    carried the full run id, so two legal rounds of one head whose run ids agree
    in their first eight characters collided: the second round found the first
    round's leftover worktree, died at ``mkdir`` before its reviewer ever
    started, and left a writer record whose receipt could never be produced.
    That round could therefore not be reviewed at all, and the wait for it could
    only ever report a missing receipt — the recoverability a round identity
    exists to provide, lost one layer below where it was repaired.
    """

    repo, base, head = make_repo(tmp_path)
    evidence = tmp_path / "evidence-shared-prefix"
    evidence.mkdir(mode=0o700)
    round_a = "deadbeef" + "1" * 24
    round_b = "deadbeef" + "2" * 24
    assert round_a != round_b
    assert round_a[:8] == round_b[:8], "the two rounds differ only past the truncation point"

    for run_id in (round_a, round_b):
        exit_code, payload = run_end_to_end(
            tmp_path,
            monkeypatch,
            capsys,
            result="PASS",
            finding=None,
            evidence=evidence,
            run_id=run_id,
            repo_state=(repo, base, head),
        )
        assert exit_code == EXIT_REVIEW_PASS, f"round {run_id} must be reviewable"
        assert Path(payload["review_receipt"]).name.endswith(f"-{run_id}.json")

    assert sorted(path.name for path in evidence.glob("review-worktree-*")) == [
        f"review-worktree-{head[:12]}-{round_a}",
        f"review-worktree-{head[:12]}-{round_b}",
    ], "each round keeps its own worktree, named by the whole run id, not by a prefix of it"
    assert run_wait(evidence, head, run_id=round_b) == EXIT_REVIEW_PASS
