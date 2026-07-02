# L3G Warning-Only Changed-File Classifier Report

## Snapshot

- main head: `822f32e3710e01e9af2b37d26a805228d34f6124`
- main CI run: `28621896257`
- main CI conclusion: `success`
- branch: `techdebt/l3g-warning-only-changed-file-classifier`
- scan date: 2026-07-03

## Source documents

- `docs/techdebt/L3_LEGACY_ENTRYPOINT_ISOLATION_PLAN.md` (L3A)
- `docs/_reports/L3A_LEGACY_ENTRYPOINT_INVENTORY_REPORT.md`
- `docs/techdebt/L3_ACTIVE_ENTRYPOINT_WHITELIST.md` (L3B)
- `docs/_reports/L3B_ACTIVE_ENTRYPOINT_WHITELIST_CONFIRMATION_REPORT.md`
- `docs/techdebt/L3_LEGACY_LABEL_AND_GUARD_WORDING_PROPOSAL.md` (L3C)
- `docs/_reports/L3C_LEGACY_LABEL_GUARD_WORDING_PROPOSAL_REPORT.md`
- `docs/techdebt/L3_REVIEW_OWNERSHIP_AND_CODEOWNERS_WORDING_PROPOSAL.md` (L3D)
- `docs/_reports/L3D_REVIEW_OWNERSHIP_CODEOWNERS_WORDING_PROPOSAL_REPORT.md`
- `docs/techdebt/L3_UNKNOWN_ENTRYPOINT_OWNER_DECISIONS.md` (L3E)
- `docs/_reports/L3E_UNKNOWN_ENTRYPOINT_OWNER_DECISIONS_REPORT.md`
- `docs/techdebt/L3_ENFORCEMENT_DESIGN_PROPOSAL.md` (L3F)
- `docs/_reports/L3F_ENFORCEMENT_DESIGN_PROPOSAL_REPORT.md`
- New: `docs/techdebt/L3_WARNING_ONLY_CHANGED_FILE_CLASSIFIER.md` (L3G)

## Implementation summary

| Item | Value |
|---|---|
| Script added | `scripts/ci/l3_changed_file_classifier.py` |
| Tests added | `tests/unit/ci/test_l3_changed_file_classifier.py` (57 tests) |
| Workflow file changed | `.github/workflows/production-gate.yml` |
| Warning-only step added | yes: `L3 warning-only changed-file classifier` |
| `continue-on-error` used | yes |
| Gatekeeper changed | no |
| AI Workflow Gate changed | no |
| CODEOWNERS changed | no |
| Hard enforcement added | no |
| Runtime code changed | no |
| Docker/build changed | no |
| DB/migration changed | no |

## Classifier behavior

### Inputs

- `--changed-files-file <path>`: Read a file listing changed paths (path-only or `git diff --name-status` format).
- `--base-ref <ref> --head-ref <ref>`: Run `git diff --name-status` between two refs.
- Default (no args): Diff `HEAD` against `origin/main`.

### Outputs

- Header with "TECHDEBT-L3G warning-only changed-file classifier".
- Non-blocking notice.
- Summary: changed file count, labels touched, attention items, high-risk count, deletion/move/rename count, restricted legacy touched yes/no, unclassified touched yes/no.
- Markdown table: `| Status | Path | Labels | Attention |`.
- Footer: `[L3-ENFORCEMENT][Layer-2][WARNING-ONLY]` with non-blocking disclaimer.

### Labels (16 total)

`l3-docs`, `documentation`, `active-runtime`, `active-api-router`, `active-governance`, `operational-guarded`, `restricted-legacy`, `archive-read-only`, `test-only`, `codeowners-sensitive`, `github-workflow-sensitive`, `gate-sensitive`, `docker-sensitive`, `db-migration-sensitive`, `scraper-training-sensitive`, `high-risk`, `unclassified-path`.

### Special detection

- Deletion (D status) → "DELETION DETECTED" note.
- Rename (R status) → "RENAME/MOVE DETECTED" note.
- `scripts/ops/sentinel_watch.js` → `restricted-legacy` + `high-risk` with shutdown warning.
- `CODEOWNERS` → `codeowners-sensitive` + `github-workflow-sensitive`.
- Gatekeeper / AI Workflow Gate paths → `active-governance` + `gate-sensitive`.
- `archive_vault_2026/**` → `archive-read-only`.
- `Dockerfile`, `docker-compose*`, `.devcontainer/**` → `docker-sensitive`.
- `alembic/**`, `migrations/**` → `db-migration-sensitive`.
- Unknown paths → `unclassified-path` with manual review note.

### Exit behavior

Always exits 0. Warnings are printed to stdout only. No non-zero exit for any classification result.

## Validation

| Check | Result |
|---|---|
| `python3 -m compileall` | Pass (both files) |
| `pytest tests/unit/ci/test_l3_changed_file_classifier.py` | 57 passed, 0 failed |
| Sample changed-files run (10 entries) | All labels correct, all markers present |
| Changed-file scope check | Only authorized files modified |
| PR CI | Pending (to be verified after PR creation) |

## Non-decisions

This implementation explicitly does **not** decide:

- No hard gate.
- No CODEOWNERS.
- No Gatekeeper change.
- No AI Workflow Gate change.
- No branch protection change.
- No automatic owner decision.
- No deletion/move/rename authorization.
- No L4 API boundary decision.
- No restricted-legacy promotion.
- No unknown entrypoint reclassification.
- No entrypoint execution, migration, or deletion.

## Report Lifecycle

- Owner: TECHDEBT-L3 legacy entrypoint isolation track.
- Purpose: bounded L3G implementation snapshot for warning-only changed-file classifier.
- Source-of-truth relationship: supports `docs/techdebt/L3_WARNING_ONLY_CHANGED_FILE_CLASSIFIER.md`.
- Supersession: may be superseded by future soft-gate implementation proposal (L3H or later).
- Cleanup: no immediate cleanup required; future cleanup requires explicit user authorization.
- Raw scan outputs: temporary `/tmp` artifacts only, not committed.

## Remaining risks

- Warning-only output may have false positives (e.g., new files not yet in whitelist get `unclassified-path`).
- Warnings may be ignored by future agents.
- Classifier path rules may need tuning after observing real PRs.
- It does **not** prevent unsafe changes — it only prints warnings.
- Any future blocking behavior requires separate explicit authorization.
- The `continue-on-error: true` setting means CI will never fail because of this classifier, even if the script itself encounters an error.

## Recommended next step

Do not start automatically.

Recommended:

- Review and merge L3G if CI is green.
- Observe warning output across future PRs.
- Do not implement hard gate, CODEOWNERS, Gatekeeper changes, AI Workflow Gate changes, or L4 without separate authorization.
