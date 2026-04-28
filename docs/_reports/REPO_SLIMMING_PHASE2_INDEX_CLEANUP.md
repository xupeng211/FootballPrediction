# Repo Slimming Phase 2 Index Cleanup

## 1. Purpose

This phase removes already-tracked generated/data/model artifacts from the Git index while keeping local files intact.

## 2. Safety Rules

This phase did not execute:

- history rewrite
- git filter-repo
- BFG
- force push
- local data deletion
- Docker volume deletion

## 3. Removed From Git Index

Total removed from Git index: 39 files.

Removed files by category:

- data: 0
- models: 36
- model_zoo: 3
- backups: 0
- archive: 0
- generated/cache/log/build artifacts: 0

This phase intentionally removed only clear model artifacts under `models/` and `model_zoo/`.

Candidates reviewed but retained for later manual confirmation:

- `data/manual_html/.gitkeep`
- `data/manual_html/test_sample.html`
- `data/regression/golden_master_4803308.json`
- `data/snapshots/.gitkeep`
- `archive/recon_v2_research/debug_decrypt_failure.js`
- `archive/recon_v2_research/j1_probe_final.js`
- `archive/recon_v2_research/research_api_direct.js`

These retained files are small samples, directory placeholders, or source-like archive scripts. They should not be removed from the index without a separate review.

## 4. Local File Preservation

`git rm --cached` was used for all removed files. Local files were preserved.

Local preservation verification result:

- missing local files: 0

## 5. Still Not Solved

History still contains old large objects until a separate Phase 3 history cleanup is planned.

The `.git` directory may remain large after this phase because removing files from the current index does not rewrite existing commits.

## 6. Pre-Merge Impact Assessment

A pre-merge impact assessment was performed after the index cleanup.

Findings:

- A temporary clean worktree was created from this branch to approximate a fresh clone.
- The clean worktree did not contain the removed `models/` or `model_zoo/` artifacts.
- `docker compose -f docker-compose.dev.yml config` passed in the clean worktree.
- Lightweight npm and pytest checks were not run because the temporary worktree had no installed project dependencies.
- Runtime code still references model artifacts under `models/`, `model_zoo/`, and `data/models/`.
- Basic service startup is not expected to fail solely because these model files are absent, but prediction and model-validation workflows may require external artifact restoration or model regeneration.
- Integration tests that explicitly check model files may fail in a fresh clone unless they are scoped as artifact-dependent tests.

Documentation added:

- `docs/MODEL_ARTIFACTS.md`

PR merge recommendation:

- Create a PR and run CI before merge.
- Confirm model artifact storage or regeneration workflow before relying on fresh clones for prediction workloads.

## 7. Next Phase Recommendation

Phase 3 should evaluate `git filter-repo` or BFG only after:

- full backup
- PR merge
- collaborator notice
- fresh clone / migration plan

Before Phase 3, a separate review should decide whether to remove any remaining tracked `data/` or `archive/` files from the Git index.
