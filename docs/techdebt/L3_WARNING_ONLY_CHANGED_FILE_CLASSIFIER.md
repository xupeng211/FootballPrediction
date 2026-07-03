# L3 Warning-Only Changed-File Classifier

## Status

- Phase: L3G warning-only changed-file classifier
- Runtime behavior changed: no
- Production source changed: no
- CI/workflow changed: yes, warning-only step only
- Gatekeeper changed: no
- AI Workflow Gate changed: no
- CODEOWNERS changed: no
- Hard enforcement added: no
- Warning-only classifier added: yes
- Deletion/move/rename performed: no

## Purpose

L3A identified legacy entrypoints. L3B confirmed the active whitelist. L3C proposed labels and guard wording. L3D proposed review ownership and future CODEOWNERS wording. L3E resolved the 7 unknown-owner-decision categories. L3F proposed a future enforcement design with 7 layers.

L3G now implements **Layer 2: Warning-only changed-file classifier** from the L3F enforcement design. This classifier:

1. Reads changed files from a PR (via git diff or a changed-files file).
2. Classifies each file by its L3 entrypoint label (based on L3B whitelist and L3E owner decisions).
3. Prints a markdown summary with labels, attention notes, and risk signals.
4. Does **not** block CI, decide ownership, authorize changes, or enforce policy.

## Non-enforcement statement

This classifier explicitly does **not**:

- Block CI or cause CI failure (`continue-on-error: true` in workflow, `sys.exit(0)` in script).
- Modify Gatekeeper (`scripts/devops/gatekeeper.sh`).
- Modify AI Workflow Gate (`scripts/ops/ai_workflow_gate.py`).
- Modify CODEOWNERS or create a CODEOWNERS file.
- Decide ownership or review requirements.
- Authorize restricted-legacy changes, deletions, moves, or renames.
- Promote legacy entrypoints to active.
- Execute any entrypoint.
- Implement hard gate, soft gate, or any blocking enforcement.
- Start L4 API boundary reconciliation.

## Classification scope

The classifier assigns one or more labels to each changed file:

| Label | Meaning | Source of truth |
|---|---|---|
| `l3-docs` | L3 governance documentation | `docs/techdebt/L3_*`, `docs/_reports/L3*` |
| `documentation` | General project documentation | `docs/**`, `*.md`, `README.md` |
| `active-runtime` | Production application entrypoint | `src/main.py`, `src/**` (default) |
| `active-api-router` | Router mounted by active runtime | L3B whitelist: health, monitoring, model_management, admin |
| `active-governance` | CI/gate/quality infrastructure | L3B whitelist: gatekeeper, AI Workflow Gate, AST check, helpers |
| `operational-guarded` | Makefile target or manual operational script | L3B whitelist guarded targets |
| `restricted-legacy` | Historical/legacy CLI, pipeline, scraper, or router | L3B whitelist (18 entries) + L3E owner decisions (6 entries) |
| `archive-read-only` | Historical reference material | `archive_vault_2026/**`, `tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/**` |
| `test-only` | Test files and helpers | `tests/**`, `scripts/test/run_test_suite.js` |
| `codeowners-sensitive` | CODEOWNERS file touched | Exact path match for `CODEOWNERS`, `.github/CODEOWNERS` |
| `github-workflow-sensitive` | `.github/` directory touched | `.github/**` |
| `gate-sensitive` | Gate infrastructure touched | Gatekeeper, AI Workflow Gate, helpers |
| `docker-sensitive` | Docker/build files touched | `Dockerfile`, `docker-compose*`, `.devcontainer/**` |
| `db-migration-sensitive` | Database/migration paths touched | `alembic/**`, `migrations/**` |
| `scraper-training-sensitive` | Data ingestion/training paths touched | FotMob scripts, training, pipeline, scraper |
| `high-risk` | High-risk operational path | `scripts/ops/sentinel_watch.js` (automated shutdown capability) |
| `unclassified-path` | Path not in L3 taxonomy | Any path not matching the above patterns |

### Key classification rules

- **L3E owner decisions** are fully incorporated: `scripts/ops/fotmob_*.py`, `check_health.js`, `sentinel_watch.js`, `audit_dataset.js`, `scripts/maintenance/integrity_guard.sh` → `restricted-legacy`; `scripts/test/run_test_suite.js` → `test-only`; `src/core/**`, `src/utils/**`, `src/schemas/**` modules with `__main__` → `active-runtime` (with self-test note).
- **sentinel_watch.js** is both `restricted-legacy` and `high-risk` (L3E Decision 3: automated shutdown capability).
- **L3 docs** (`docs/techdebt/L3_*`, `docs/_reports/L3*`) get their own `l3-docs` label and are not mixed with general documentation.
- **Classification order** is specific-to-general: exact restricted-legacy paths match before wildcard `src/**` patterns.
- **CODEOWNERS** matched exactly before `.github/**` catch-all.

## Warning output contract

The classifier always prints:

1. **Header**: `TECHDEBT-L3G warning-only changed-file classifier`
2. **Non-blocking notice**: `This step is warning-only and does not block CI.`
3. **Summary statistics**:
   - Changed file count
   - Labels touched (comma-separated)
   - Attention items (deletions, renames, restricted legacy, high-risk, unclassified, CODEOWNERS, .github, gate, Docker, DB, scraper/training, archive)
   - High-risk path count
   - Deletion/move/rename count
   - Restricted legacy touched (yes/no)
   - Unknown/unclassified touched (yes/no)
4. **Markdown table**: `| Status | Path | Labels | Attention |`
5. **Footer**: `[L3-ENFORCEMENT][Layer-2][WARNING-ONLY]` with non-blocking disclaimer.

The classifier always exits 0.

## CI integration

The classifier is integrated into `.github/workflows/production-gate.yml` as a single warning-only step in the `production-gate` job:

- **Step name**: `L3 warning-only changed-file classifier`
- **Condition**: `if: github.event_name == 'pull_request'` (only runs on PR events)
- **Error handling**: `continue-on-error: true` (CI continues regardless of classifier output)
- **Placement**: After "Validate Python UTF-8 and AST parse", before the `docker-build` job
- **Script exit code**: Always 0 (classifier warnings never cause non-zero exit)

The step fetches the base ref (`git fetch --no-tags --prune --depth=200 origin ${{ github.base_ref }}`) and runs:
```
python3 scripts/ci/l3_changed_file_classifier.py \
  --repo-root . \
  --base-ref "origin/${{ github.base_ref }}" \
  --head-ref "HEAD"
```

## Future rollout

1. **Observe**: Review warning-only output across multiple PRs to validate classification accuracy.
2. **Tune**: Adjust path patterns if false positives or gaps are discovered.
3. **Soft gate (Layer 4)**: After dry-run period, consider making restricted-legacy touch detection a soft gate (warning that requires explicit acknowledgment in PR body). Requires separate PR and explicit authorization.
4. **Hard gate (Layer 6)**: Only after all prior layers are stable and owner approval is obtained. Requires separate PR, dry-run period, and explicit authorization.

Any future blocking behavior requires separate explicit authorization. This classifier does **not** pre-authorize any escalation.

## Relationship to L3F

This classifier implements **Layer 2 (Warning-only changed-file classifier)** from `docs/techdebt/L3_ENFORCEMENT_DESIGN_PROPOSAL.md`.

It satisfies the L3F design principles:
- **Advisory before blocking**: warning-only, not blocking.
- **Avoid false positives before hard gates**: outputs labels for human review; does not block.
- **Never auto-promote**: classification is based on static whitelist; unknown paths get `unclassified-path`.
- **Never auto-authorize deletion/move/rename**: flags them, does not allow them.
- **Keep L3 separate from L4**: only classifies entrypoint boundaries, not API boundaries.

## Next recommended task

Do not start automatically.

Recommended next task only after user confirmation:

- Review and merge L3G if CI is green.
- Observe warning-only output across future PRs.
- Do not implement hard gate, CODEOWNERS, Gatekeeper changes, AI Workflow Gate changes, or L4 without separate authorization.

## L3H visibility and calibration update

L3H improves classifier visibility during the warning-only observation period.

The classifier may write a GitHub Step Summary when `GITHUB_STEP_SUMMARY` is available, and may write a local summary via `--summary-file` for testing.

This remains warning-only:

- It does not block CI.
- It does not modify Gatekeeper.
- It does not modify AI Workflow Gate.
- It does not modify CODEOWNERS.
- It does not authorize restricted legacy changes.
- It does not authorize deletion, move, or rename.
- It does not decide ownership.
- It does not start L4.
- It does not run any entrypoint.

### Observation-period checklist

For future PRs, reviewers should check:

- Did the classifier run on pull_request?
- Are high-risk paths visible?
- Are restricted legacy paths visible?
- Are unclassified paths visible?
- Are deletion / rename / move signals visible?
- Is the output noisy?
- Is the output missing any obviously sensitive path?
- Should a future PR tune classifier labels?

Warnings should be observed across multiple future PRs before any soft gate or hard gate is considered.
