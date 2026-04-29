# Repository History Rewrite Go / No-Go Checklist

## 1. Purpose

This document is the final approval checklist before any real Git history rewrite.

It is an approval artifact only. It does not authorize automated execution, and it must not be treated as a script.

## 2. Current Status

- Phase 1 completed: `.gitignore` guardrails and data/model storage policy are merged.
- Phase 2 completed: `models/` and `model_zoo/` were removed from the current Git index.
- Phase 2.5 completed: model artifact recovery/checking scaffold is merged.
- Phase 3 planning completed: history cleanup plan and audit are merged.
- Phase 3.1 dry run recorded: first automatic candidate run stopped at the safety gate.
- Phase 3.2 dry run recorded: narrower mirror dry run completed.
- Phase 3.3 manual dry run recorded: manual-path mirror dry run completed.
- Real history rewrite not yet executed.

Current repository state before any real rewrite:

- Working tree size: `217M`
- `.git` size: `200M`
- Git pack size: `197.71 MiB`

GitHub readiness snapshot:

- Open PR count: `0`
- PR gate: clear at the time of this checklist
- Remote branch review: required
- Unmerged remote branch detected: `origin/chore/ci-hardening`

## 3. Proposed Cleanup Paths

The final candidate paths are exactly:

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

## 4. Explicitly Excluded Paths

The following paths are explicitly excluded from the proposed real rewrite:

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

These paths may still contain large objects, but they require separate review and are out of scope for the proposed low-risk cleanup.

## 5. Expected Benefit

Phase 3.3 manual mirror dry run result:

- Before mirror size: `230M`
- After mirror size: `162M`
- Estimated reduction: `68M`
- Estimated reduction percentage: approximately `29.6%`
- Before Git pack size: `228.66 MiB`
- After Git pack size: `159.10 MiB`
- Estimated Git pack reduction: `69.56 MiB`
- Estimated Git pack reduction percentage: approximately `30.4%`

Functional validation from the cleaned dry-run mirror:

- Fresh clone: passed
- `docker compose config`: passed
- model artifact checker with `--allow-missing`: passed

## 6. Required Go Criteria

- [ ] Final cleanup path list approved
- [ ] Backup mirror exists
- [ ] Backup tar.gz exists
- [ ] Backup restore / clone verified
- [ ] No open PRs
- [ ] No important unmerged branches
- [ ] Maintenance window selected
- [ ] Collaborator notice sent
- [ ] Re-clone / migration instructions prepared
- [ ] Model artifact recovery docs merged
- [ ] CI passing before rewrite
- [ ] Dry-run cleaned mirror fresh clone validated
- [ ] Rollback plan reviewed
- [ ] Force push / mirror push strategy approved

## 7. No-Go Conditions

Do not proceed if:

- Any open PR remains
- Any collaborator has unmerged work
- Backup is missing or unverified
- Maintenance window is not approved
- Final path list is not approved
- CI is failing
- Re-clone plan is not ready
- Owner has not explicitly said `GO`

Current status: `NO-GO until remote branch review and explicit owner approval are complete`.

## 8. Execution Strategy Draft

Important: Example only. Do not execute from this document automatically.

High-level execution steps:

1. Freeze merges.
2. Create final mirror backup.
3. Verify backup clone and archive.
4. Create execution mirror.
5. Run the approved history rewrite command on the execution mirror only.
6. Validate the cleaned mirror size and object list.
7. Fresh clone from the cleaned mirror and run validation checks.
8. Push rewritten history only after explicit `GO`.
9. Require all users to re-clone or follow the approved migration plan.
10. Keep the backup until the team confirms the rewritten repository is stable.

## 9. Rollback Strategy

Rollback depends on the final mirror backup.

- Use the mirror backup if pushed history is bad.
- Re-push backup mirror only under emergency approval.
- Prevent old clones from pushing stale history.
- Announce rollback status to all collaborators.
- Require fresh clone after rollback if the remote history changed again.

## 10. Approval

Final decision:

- [ ] GO
- [ ] NO-GO

Approver:
Date:
Notes:
