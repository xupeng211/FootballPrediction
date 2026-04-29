# Repo Slimming Phase 3.4 Go / No-Go Report

## 1. Scope

This phase prepares the final approval checklist for real history rewrite.

It does not execute history rewrite.

This phase only adds documentation for final review, collaborator notification, and execution-day planning.

## 2. Current Repository Size

- Working tree: `217M`
- `.git`: `200M`
- Git pack: `197.71 MiB`
- Packed objects: `201857`
- Pack count: `1`

The main repository still contains the old historical objects because no real history rewrite has been executed.

## 3. Phase 3.3 Dry Run Summary

Manual cleanup paths:

```text
backups/git_before_filter_repo_20251004_220053/repo_backup.bundle
data/grafana/plugins/redis-datasource/
data/processed/v51_features_all.csv
data/archive/football_prediction_direct.pkl
models/
model_zoo/
venv/
.venv/
```

Dry-run result:

- Before mirror size: `230M`
- After mirror size: `162M`
- Reduction estimate: `68M`, approximately `29.6%`
- Before Git pack size: `228.66 MiB`
- After Git pack size: `159.10 MiB`
- Git pack reduction estimate: `69.56 MiB`, approximately `30.4%`
- Fresh clone verification: passed
- `docker compose config`: passed
- Artifact checker: passed with `--allow-missing`

Phase 3.3 risk level: low-to-medium for the manual whitelist itself.

## 4. GitHub Readiness

- Open PR count: `0`
- Open PR list: none
- PR gate: clear

Remote branches observed after pruning:

```text
origin/HEAD -> origin/main
origin/chore/ci-hardening
origin/docs/tep-001-csv-bulk-loader
origin/feat/fix-csv-odds-pipeline
origin/feature/csv-bulk-loader
origin/feature/euro-leagues-expansion
origin/feature/final-orphan-purge
origin/feature/fotmob-reset-realignment
origin/feature/semi-auto-etl-factory
origin/hotfix/ci-gate-hardening
origin/main
```

Unmerged remote branch check:

```text
origin/chore/ci-hardening
```

Remote branch notes:

- No open PRs were found.
- `origin/chore/ci-hardening` is not merged into `origin/main`.
- The remaining remote branches still require owner review before real history rewrite.
- The current status must remain `NO-GO` until branch ownership and migration handling are confirmed.

## 5. Proposed Final Cleanup Paths

The proposed final cleanup paths are exactly:

```text
backups/git_before_filter_repo_20251004_220053/repo_backup.bundle
data/grafana/plugins/redis-datasource/
data/processed/v51_features_all.csv
data/archive/football_prediction_direct.pkl
models/
model_zoo/
venv/
.venv/
```

Do not expand this list without a new dry run and explicit approval.

## 6. Explicitly Excluded Paths

The proposed real rewrite excludes:

```text
src/
docs/
scripts/
tests/
config/
.github/
patches/
archive/
data/raw/
```

These paths are not approved for cleanup in the proposed low-risk rewrite.

## 7. Go / No-Go Status

Current status: `NO-GO`

Reasons:

- Human approval has not been granted.
- Backup usability has not been independently verified.
- Maintenance window has not been selected.
- Collaborator notice has not been sent.
- Re-clone / migration instructions have not been approved.
- Force push / mirror push strategy has not been approved.
- At least one remote branch is not merged into `origin/main`: `origin/chore/ci-hardening`.

If the branch review is resolved and all required approvals are completed, this can move to `READY FOR MANUAL GO REVIEW`. It must not become `GO` automatically.

## 8. Required Human Approval

Before any real rewrite, the owner must explicitly approve:

- final path list approval
- backup verification
- maintenance window
- collaborator notice
- re-clone plan
- force push / mirror push strategy
- handling plan for open PRs and non-main branches
- rollback plan

The owner must explicitly say `GO` before execution.

## 9. Explicitly Not Executed

This phase did not execute:

- `git filter-repo`
- BFG
- force push
- mirror push
- history rewrite
- local data deletion
- Docker cleanup

## 10. Next Recommended Action

Create a PR for this approval document.

After the PR is merged, review the Go / No-Go checklist with the repository owner. Do not execute the real history rewrite until the owner explicitly approves the final path list, branch handling plan, backup, maintenance window, collaborator notice, migration plan, and push strategy.
