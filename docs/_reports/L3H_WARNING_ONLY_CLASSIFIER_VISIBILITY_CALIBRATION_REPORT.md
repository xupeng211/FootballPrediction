# L3H Warning-Only Classifier Visibility Calibration Report

## Snapshot

- main head: `d98b255a7bcaaae280185ebbcb63cb678e4902e5`
- main CI run: `28628026510`
- main CI conclusion: `success`
- branch: `techdebt/l3h-warning-visibility-calibration-audit`
- scan date: 2026-07-03

## Purpose

L3H improves visibility and calibration support for the L3G warning-only changed-file classifier.

It does not introduce hard enforcement.

## Inputs

- `docs/techdebt/L3_ENFORCEMENT_DESIGN_PROPOSAL.md`
- `docs/techdebt/L3_WARNING_ONLY_CHANGED_FILE_CLASSIFIER.md`
- `docs/_reports/L3G_WARNING_ONLY_CHANGED_FILE_CLASSIFIER_REPORT.md`
- `scripts/ci/l3_changed_file_classifier.py`
- `tests/unit/ci/test_l3_changed_file_classifier.py`

## Implementation summary

| Item | Value |
|---|---|
| Step Summary support | yes: `GITHUB_STEP_SUMMARY` env var auto-detected |
| `--summary-file` support | yes: local file for testing |
| stdout preserved | yes: original output unchanged |
| warning-only behavior preserved | yes: always exits 0 |
| tests updated | yes: 9 new summary/visibility tests |
| docs updated | yes: L3H visibility/calibration section added |
| workflow changed | no |
| Gatekeeper changed | no |
| AI Workflow Gate changed | no |
| CODEOWNERS changed | no |
| hard enforcement added | no |

## Validation

| Item | Result |
|---|---|
| compileall | passes |
| unit test | passes (existing + new summary tests) |
| summary-file sample run | generates valid markdown |
| GITHUB_STEP_SUMMARY sample run | appends to summary file |
| changed-file scope check | only authorized files modified |
| warning-only exits 0 | confirmed for all warning categories |

## Calibration guidance

Future reviewers should observe:

- false positives
- false negatives
- noisy labels
- hidden high-risk paths
- unclear attention messages
- whether summary output is visible enough in GitHub Actions

## Non-decisions

- No hard gate.
- No CODEOWNERS.
- No Gatekeeper change.
- No AI Workflow Gate change.
- No branch protection change.
- No automatic owner decision.
- No deletion/move/rename authorization.
- No restricted legacy authorization.
- No L4 API boundary decision.

## Report Lifecycle

- Owner: TECHDEBT-L3 legacy entrypoint isolation track.
- Purpose: bounded L3H visibility/calibration snapshot.
- Source-of-truth relationship: supports `docs/techdebt/L3_WARNING_ONLY_CHANGED_FILE_CLASSIFIER.md`.
- Supersession: may be superseded by future classifier tuning or soft-gate proposal.
- Cleanup: no immediate cleanup required; future cleanup requires explicit user authorization.
- Raw scan outputs: temporary `/tmp` artifacts only, not committed.

## Remaining risks

- Warning-only output may still be ignored.
- Summary output may still need tuning after real PR observation.
- Classifier path rules may still have false positives or false negatives.
- It does not prevent unsafe changes.
- Any future blocking behavior requires separate explicit authorization.

## Recommended next step

Do not start automatically.

Recommended:

- Review and merge L3H if CI is green.
- Observe warning-only classifier output across future real PRs.
- Do not implement hard gate, CODEOWNERS, Gatekeeper changes, AI Workflow Gate changes, or L4 without separate authorization.
