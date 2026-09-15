"""What the review wait promises across a CLI and a GNU make boundary.

lifecycle: test-fixture

The advisories against the merged repair included one reproduced case: a
``--head-sha`` that cannot be normalized raised out of ``wait`` before its
report/fail machinery existed, so a caller got a stack trace on stderr and an
empty stdout even under ``--json``.  "I could not establish a verdict" and "the
tool crashed" must not be the same observable, and they must not be the same
observable to a wrapper either — a wrapper sees only an exit status and one
stdout line.

GNU make is the other half.  It preserves a recipe's success and collapses
every non-zero child status into its own exit 2, so the child's 3 and 1 are one
status at the make layer.  These tests record that measured behavior and the
help text that states it, rather than promising a classification make cannot
carry.
"""

from __future__ import annotations

import json
import shutil
from typing import TYPE_CHECKING

import pytest

from scripts.devops import codex_independent_review as reviewer
from scripts.devops.codex_review_verdict import (
    EXIT_REVIEW_BLOCKING_FINDINGS,
    EXIT_REVIEW_INFRASTRUCTURE_ERROR,
    EXIT_REVIEW_PASS,
    WAIT_STATE_REVIEW_FAILED,
    WAIT_STATE_REVIEW_FINISHED,
)
from tests.helpers.agentic_workflow_fixtures import MISSION_ID, make_repo

if TYPE_CHECKING:
    from pathlib import Path

from tests.helpers.codex_review_evidence_fixtures import (
    BLOCKING_FINDING,
    MAKE_FAILURE_EXIT_CODE,
    make_help_line,
    payload_of,
    place_receipt,
    run_make_wait,
    run_wait,
    run_wait_process,
    seal_receipt,
)

# --------------------------------------------------------------------------
# TEST A — invalid input is a structured refusal, never a traceback.
# --------------------------------------------------------------------------
# The advisories against the merged repair included one reproduced case: a
# `--head-sha` that cannot be normalized raised out of `wait` before its
# report/fail machinery existed, so a caller got a stack trace on stderr and an
# empty stdout even under `--json`.  "I could not establish a verdict" and "the
# tool crashed" must not be the same observable.


@pytest.mark.parametrize(
    "bad_head",
    [
        "0c33c07",  # short SHA
        "0" * 39,  # one character short of a full SHA
        "0" * 41,  # one character too long
        "z" * 40,  # right length, not hex
        "0c33c07894daeb904a70e1c2b5bc90c9d28117bd ",  # full SHA with trailing space
        "",  # nothing at all
    ],
)
def test_wait_refuses_an_unusable_head_sha_structurally(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], bad_head: str
) -> None:
    evidence = tmp_path / "evidence-bad-head"
    evidence.mkdir(mode=0o700)

    exit_code = run_wait(evidence, bad_head)
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == EXIT_REVIEW_INFRASTRUCTURE_ERROR, (
        "invalid input is exit 1, deterministically"
    )
    assert exit_code != EXIT_REVIEW_PASS, "an unusable head can never look like a pass"
    assert payload["status"] == "FAIL"
    assert payload["state"] == WAIT_STATE_REVIEW_FAILED
    assert payload["head_sha"] == bad_head, "the refusal names the input as it was given"
    assert "--head-sha" in payload["detail"]
    assert "Traceback" not in captured.err


def test_wait_refuses_an_unusable_head_before_it_touches_the_evidence_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The refusal must not depend on the rest of the environment being usable."""

    exit_code = run_wait(tmp_path / "absent", "not-a-sha")
    payload = payload_of(capsys)
    assert exit_code == EXIT_REVIEW_INFRASTRUCTURE_ERROR
    assert payload["state"] == WAIT_STATE_REVIEW_FAILED
    assert "--head-sha" in payload["detail"]


def test_wait_refuses_a_run_id_that_could_not_have_named_a_round(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A round identity the naming rule cannot produce designates nothing."""

    evidence = tmp_path / "evidence-bad-run"
    evidence.mkdir(mode=0o700)
    exit_code = run_wait(evidence, "3" * 40, run_id="NOT-A-RUN-ID")
    payload = payload_of(capsys)
    assert exit_code == EXIT_REVIEW_INFRASTRUCTURE_ERROR
    assert payload["state"] == WAIT_STATE_REVIEW_FAILED
    assert "--run-id" in payload["detail"]


def test_a_failed_run_reports_its_refusal_as_json_when_asked(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`run` owes the same structure to a caller that asked for it."""

    exit_code = reviewer.main(
        [
            "run",
            "--repo-root",
            str(tmp_path),
            "--base-sha",
            "1" * 40,
            "--head-sha",
            "short",
            "--mission-id",
            MISSION_ID,
            "--mission-scope-file",
            str(tmp_path / "absent.json"),
            "--evidence-dir",
            str(tmp_path / "evidence-run-refusal"),
            "--json",
        ]
    )
    captured = capsys.readouterr()
    assert exit_code == EXIT_REVIEW_INFRASTRUCTURE_ERROR
    assert json.loads(captured.out)["status"] == "FAIL"
    assert "Traceback" not in captured.err


# --------------------------------------------------------------------------
# TEST D — what GNU make can and cannot carry, and the help text that says so.
# --------------------------------------------------------------------------


def test_the_make_help_text_does_not_promise_what_make_cannot_carry() -> None:
    """GNU make collapses every non-zero recipe status into its own exit 2.

    The help text used to advertise the Python contract ("0=PASS 3=FAIL
    1=无法建立 verdict") on a make target, which reads as if `make` preserved
    that classification.  It does not, and a caller that trusted the help would
    have read a refused wait as an ordinary failure.
    """

    line = make_help_line("agent-review-wait")
    assert "exit 2" in line, "the collapse must be named, not implied"
    assert "GNU make" in line
    assert "python3 scripts/devops/codex_independent_review.py wait" in line, (
        "the help must point at the invocation that does preserve 0/3/1"
    )
    assert "0=PASS 3=FAIL" not in line, "the old unqualified claim must not come back"


def test_both_make_targets_document_the_round_identity_knob() -> None:
    """A round can only be named at launch and at wait if both targets carry it."""

    assert "RUN_ID=" in make_help_line("agent-review")
    assert "RUN_ID=" in make_help_line("agent-review-wait")


def test_the_process_boundary_carries_the_refusal_of_an_unusable_head(tmp_path: Path) -> None:
    """Exit status plus stdout is the whole contract a wrapper can see.

    The in-process test above proves the mechanism; this pins the pair at the
    boundary, because the failure being repaired was observable there as "a
    traceback on stderr, nothing on stdout, exit 1".
    """

    completed = run_wait_process(tmp_path, "not-a-sha")

    assert completed.returncode == EXIT_REVIEW_INFRASTRUCTURE_ERROR
    payload = json.loads(completed.stdout)  # one JSON line, nothing else
    assert payload["state"] == WAIT_STATE_REVIEW_FAILED
    assert payload["status"] == "FAIL"
    assert payload["head_sha"] == "not-a-sha"
    assert "Traceback" not in completed.stderr


@pytest.mark.skipif(shutil.which("make") is None, reason="GNU make is unavailable")
def test_make_wrapper_keeps_a_pass_at_zero(tmp_path: Path) -> None:
    repo, base, head = make_repo(tmp_path)
    evidence = tmp_path / "evidence-make-pass"
    place_receipt(
        evidence,
        seal_receipt(tmp_path, repo, base, head, slot="make-pass"),
        name_head=head,
        run_id="a" * 32,
    )

    result = run_make_wait(evidence, head)
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert result.returncode == 0
    assert payload["status"] == "PASS"
    assert payload["state"] == WAIT_STATE_REVIEW_FINISHED


@pytest.mark.skipif(shutil.which("make") is None, reason="GNU make is unavailable")
def test_make_wrapper_reports_a_fail_as_non_zero_without_claiming_three(tmp_path: Path) -> None:
    """The measured behavior, pinned: make says 2, not the child's 3.

    This is not a defect to be worked around — the mission that authorized this
    repair forbade hacking make's exit status — so the test records the real
    contract instead: "not zero is not PASS", and the distinction lives in the
    JSON the target prints.
    """

    repo, base, head = make_repo(tmp_path)
    evidence = tmp_path / "evidence-make-fail"
    place_receipt(
        evidence,
        seal_receipt(
            tmp_path, repo, base, head, result="FAIL", finding=BLOCKING_FINDING, slot="mf"
        ),
        name_head=head,
        run_id="b" * 32,
    )

    result = run_make_wait(evidence, head)
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert result.returncode == MAKE_FAILURE_EXIT_CODE, (
        "make collapses the child's 3 into its own 2"
    )
    assert result.returncode != EXIT_REVIEW_BLOCKING_FINDINGS
    assert payload["status"] == "FAIL"
    assert payload["review_result"] == "FAIL"


@pytest.mark.skipif(shutil.which("make") is None, reason="GNU make is unavailable")
def test_the_python_entrypoint_keeps_the_full_classification(tmp_path: Path) -> None:
    """The contract make cannot carry is still carried where it was promised.

    This drives the CLI as a *process*, because the claim is about a process
    exit status and an in-process return value would not prove it.
    """

    repo, base, head = make_repo(tmp_path)
    for slot, result, finding, expected in (
        ("pass", "PASS", None, EXIT_REVIEW_PASS),
        ("fail", "FAIL", BLOCKING_FINDING, EXIT_REVIEW_BLOCKING_FINDINGS),
    ):
        evidence = tmp_path / f"evidence-cli-{slot}"
        place_receipt(
            evidence,
            seal_receipt(
                tmp_path, repo, base, head, result=result, finding=finding, slot=f"cli-{slot}"
            ),
            name_head=head,
            run_id=("c" if slot == "pass" else "d") * 32,
        )
        completed = run_wait_process(evidence, head)
        assert completed.returncode == expected, completed.stderr
