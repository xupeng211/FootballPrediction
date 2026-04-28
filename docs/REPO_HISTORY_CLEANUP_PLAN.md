# Repository History Cleanup Plan

## 1. Purpose

Phase 1 added `.gitignore` guardrails and data/model storage policy docs.
Phase 2 removed tracked `models/` and `model_zoo/` artifacts from the current Git index.
Phase 2.5 added a model artifact manifest template and checking scaffold.

Those phases protect the current tree, but they do not shrink old Git history. Existing pack files still contain historical model files, processed datasets, backup bundles, generated reports, a vendored Grafana plugin, and virtual environment assets. Phase 3 should clean history only after a controlled dry run, backup, and collaborator migration plan.

This document is a plan only. No history rewrite was executed while creating it.

## 2. Current State

- Current working tree size: `217M`
- Current `.git` size: `200M`
- Current Git pack size: `197.71 MiB`
- Largest pack file: `.git/objects/pack/pack-a8d051c17ef8bb80edafaa4426f231cbc0873612.pack` at `201656210` bytes
- Historical audit sample: top 150 objects by on-disk object size
- Cleanup candidates from that sample: 129 paths
- Current model artifact policy: model binaries are not stored in Git
- Current model recovery scaffold: `config/model_artifacts.example.json` and `scripts/model_artifacts/check_model_artifacts.py`

Known large historical objects include:

| Size bytes | Path |
| ---: | --- |
| 13825460 | `backups/git_before_filter_repo_20251004_220053/repo_backup.bundle` |
| 5996810 | `data/grafana/plugins/redis-datasource/redis-datasource_windows_amd64.exe` |
| 5984478 | `data/grafana/plugins/redis-datasource/redis-datasource_darwin_arm64` |
| 5902791 | `data/grafana/plugins/redis-datasource/redis-datasource_linux_amd64` |
| 5570683 | `data/grafana/plugins/redis-datasource/redis-datasource_linux_arm` |
| 5376574 | `data/grafana/plugins/redis-datasource/redis-datasource_linux_arm64` |
| 3980762 | `archive/phase_g_multilang_analysis_report_20251030_121619.json.gz` |
| 3152822 | `models/pilot_v320_pure/xgboost_model.json` |
| 3037315 | `models/pilot_v320_hybrid/xgboost_model.json` |
| 2994689 | `data/grafana/plugins/redis-datasource/redis-datasource_darwin_amd64` |
| 2941742 | `data/processed/v51_features_all.csv` |
| 2828788 | `data/archive/football_prediction_direct.pkl` |
| 1376394 | `models/baseline_v1/baseline_v1_result_1x2.calibrated.joblib` |
| 1280985 | `src/data/models/xgb_football_v3.0_global.joblib` |
| 1165385 | `model_zoo/v41_430_catboost_model_20260121_152451.cbm` |
| 1119071 | `model_zoo/v41_430_catboost_model_20260121_152618.cbm` |
| 1037190 | `data/raw/archive_2023_2024.json` |
| 991294 | `models/titan_v4468_combat.joblib` |

## 3. Why This Is Dangerous

History cleanup rewrites commit object IDs. After the rewrite, old clones and the rewritten repository no longer share the same history graph. If an old clone pushes or merges old history back, removed large objects can be reintroduced.

Risks include:

- Force-push impact on all collaborators.
- Open branches based on old history becoming unsafe to merge directly.
- CI, release tags, and deployment references pointing to old commit IDs.
- Accidental removal of small fixtures or documentation assets if the cleanup path set is too broad.
- Need for every contributor to re-clone or migrate local work carefully.

Phase 3 must therefore be handled as a maintenance operation, not as a normal PR-only change.

## 4. Candidate Paths

The following candidates were extracted from the top 150 historical objects. Before a real rewrite, regenerate the full candidate list from a fresh mirror clone and review it again.

### models

Count in current sample: 23 top-level paths.

- `models/`
- `models/TITAN_CORE_V5_PROD.joblib`
- `models/baseline_v1/baseline_v1_result_1x2.calibrated.joblib`
- `models/baseline_v1/baseline_v1_result_1x2.json`
- `models/pilot_v320_hybrid/xgboost_model.json`
- `models/pilot_v320_pure/xgboost_model.json`
- `models/titan_v4468_combat.joblib`
- `models/war_god_v31_final.joblib`

### model_zoo

Count in current sample: 6 top-level paths.

- `model_zoo/`
- `model_zoo/v172_beta.model`
- `model_zoo/v41_430_catboost_model_20260121_152445.cbm`
- `model_zoo/v41_430_catboost_model_20260121_152451.cbm`
- `model_zoo/v41_430_catboost_model_20260121_152618.cbm`
- `model_zoo/v41_430_catboost_model_20260121_152624.cbm`

### data

Count in current sample: 41 top-level paths.

- `data/archive/`
- `data/archive/football_prediction_direct.pkl`
- `data/archive/football_prediction_v4_optuna.pkl`
- `data/archive/xgb_football_v1.joblib`
- `data/archive/xgb_football_v2.3_467real.joblib`
- `data/processed/`
- `data/processed/v51_features_all.csv`
- `data/processed/V26_Baseline_40D.parquet`
- `data/raw/archive_2023_2024.json`
- `data/pilot_v320_hybrid/X_features.npy`
- `data/pilot_v41_300/X_features.npy`
- `data/prometheus/`
- `data/grafana/plugins/redis-datasource/`

Do not remove `data/mock/` if it exists in history and contains intentionally small sample files.

### backups

Count in current sample: 32 top-level paths.

- `backups/git_backup_20251004_215227/repo_full_backup.bundle`
- `backups/git_before_filter_repo_20251004_220053/repo_backup.bundle`
- `backups/v1.0_stable_20251214/src/data/raw_landing/fbref/`

### archive

Count in current sample: 2 top-level paths.

- `archive/final_project_coverage.json`
- `archive/phase_g_multilang_analysis_report_20251030_121619.json.gz`

### binary plugins

Count in current sample: 8 Grafana plugin paths.

- `data/grafana/plugins/redis-datasource/redis-datasource_windows_amd64.exe`
- `data/grafana/plugins/redis-datasource/redis-datasource_darwin_amd64`
- `data/grafana/plugins/redis-datasource/redis-datasource_darwin_arm64`
- `data/grafana/plugins/redis-datasource/redis-datasource_linux_amd64`
- `data/grafana/plugins/redis-datasource/redis-datasource_linux_arm`
- `data/grafana/plugins/redis-datasource/redis-datasource_linux_arm64`

### compressed/generated artifacts

Count in current sample: 66 paths by generated or compressed file type. This count overlaps with the directory counts above.

- `scripts_backup_20251005_103855.tar.gz`
- `V9_0_MODEL_ANALYSIS.png`
- `V9_1_CALIBRATION_COMPARISON.png`
- `V9_2_CALIBRATION_COMPARISON.png`
- `V9_2_TRADE_ANALYSIS.png`
- `V9_3_LARGE_SCALE_CALIBRATION_COMPARISON.png`
- `feature_importance_v7.png`
- `feature_importance_v7_enhanced.png`
- `reports/v34_market/v34_alpha_charts_20251228_030427.png`
- `docs/audit/yield_audit_chart_20251223_182617.png`
- `venv/share/jupyter/`

Some generated images may be useful documentation artifacts. Treat them as review-required unless they are obsolete or reproducible.

## 5. Recommended Tool

Use `git filter-repo` for this repository.

Reasons:

- The candidate set is path-specific and mixed: model files, processed data, backup bundles, plugin binaries, virtual environment files, and selected generated reports.
- The cleanup should preserve source history while removing precise paths.
- It supports explicit path lists and a repeatable dry run workflow.
- It is easier to audit than broad extension-based deletion when the repository contains small fixtures and docs that should remain.

BFG Repo-Cleaner is a valid fallback for broad cleanup, especially when deleting all blobs above a size threshold or by extension. It is less suitable as the primary tool here because coarse rules such as `*.png`, `*.json`, or `*.pkl` could remove documentation assets, fixtures, or templates that require review.

Both tools rewrite history. Either approach requires coordinated migration for all clones.

## 6. Dry Run Plan

Perform the first rewrite only in a mirror clone dry-run repository.

Example only, not executed:

```bash
cd ~
git clone --mirror git@github.com:xupeng211/FootballPrediction.git FootballPrediction.history-cleanup-dryrun.git
cd FootballPrediction.history-cleanup-dryrun.git
```

Create a candidate path file from the audit, review it manually, then run `git filter-repo` in the dry-run mirror only.

Example only, not executed:

```bash
git filter-repo \
  --path backups/git_before_filter_repo_20251004_220053/repo_backup.bundle \
  --path backups/git_backup_20251004_215227/repo_full_backup.bundle \
  --path data/grafana/plugins/redis-datasource/ \
  --path data/processed/v51_features_all.csv \
  --path data/archive/football_prediction_direct.pkl \
  --path data/archive/football_prediction_v4_optuna.pkl \
  --path data/raw/archive_2023_2024.json \
  --path data/prometheus/ \
  --path models/ \
  --path model_zoo/ \
  --path venv/ \
  --invert-paths
```

After the dry run, inspect object size, refs, tags, branches, and a fresh checkout from the rewritten mirror.

## 7. Backup Plan

Create a mirror backup before any real rewrite.

Example only, not executed:

```bash
cd ~
git clone --mirror git@github.com:xupeng211/FootballPrediction.git FootballPrediction.backup.git
tar -czf FootballPrediction.backup.git.tar.gz FootballPrediction.backup.git
```

Store the archive outside the working tree, preferably in durable storage with restricted access. Confirm the archive can be extracted and inspected before proceeding.

## 8. Validation Plan

Validate the dry run before considering a real rewrite.

Example only, not executed:

```bash
git count-objects -vH
git rev-list --objects --all \
  | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize:disk) %(rest)' \
  | sort -k3 -n \
  | tail -50
```

Functional validation should include:

- Fresh clone from the rewritten dry-run mirror.
- `git status` clean after checkout.
- Expected source files, docs, configs, and tests present.
- Model artifacts absent from Git but restorable through the Phase 2.5 scaffold.
- CI-equivalent checks for docs and lightweight repository validation.
- Explicit verification that `models/`, `model_zoo/`, backup bundles, and plugin binaries no longer appear in history.

## 9. Migration Plan

After real history cleanup:

- Old clones should not push directly.
- The safest path is a fresh clone from the rewritten repository.
- Contributors with local work should export patches or push work to a temporary location before the maintenance window.
- Do not merge old branches into the rewritten main without review.
- Merging old history can reintroduce removed large objects.
- Update any deployment, release, or CI references that point to old commit IDs.

## 10. Rollback Plan

Rollback depends on the mirror backup.

If the real rewrite produces bad history:

- Stop all pushes.
- Restore the mirror backup into a separate repository first.
- Compare refs, tags, and branch tips.
- Re-publish the backup only after confirming the intended rollback target.
- Notify collaborators that any clones based on the failed rewrite must be discarded or handled manually.

Do not attempt rollback from a partially rewritten working tree.

## 11. Go / No-Go Checklist

Proceed only if every item is true:

- [ ] Mirror backup exists outside the working tree.
- [ ] Backup extraction was tested.
- [ ] Dry-run mirror rewrite completed.
- [ ] Dry-run size reduction was measured.
- [ ] Top historical objects were re-audited after dry run.
- [ ] Fresh clone from dry-run mirror was validated.
- [ ] Candidate paths were reviewed for fixtures and docs.
- [ ] CI strategy is confirmed.
- [ ] Maintainers approved the rewrite window.
- [ ] Collaborators were notified.
- [ ] Re-clone and migration instructions are ready.
- [ ] No active release depends on old commit IDs.

No-go if any item is unresolved.

## 12. Commands Appendix

All commands in this appendix are examples only. They were not executed while creating this document.

### Inspect Large Objects

```bash
git rev-list --objects --all \
  | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize:disk) %(rest)' \
  | sort -k3 -n \
  | tail -150
```

### git filter-repo Example

```bash
git filter-repo \
  --path backups/git_before_filter_repo_20251004_220053/repo_backup.bundle \
  --path data/grafana/plugins/redis-datasource/ \
  --path data/processed/v51_features_all.csv \
  --path data/archive/football_prediction_direct.pkl \
  --path models/ \
  --path model_zoo/ \
  --invert-paths
```

### BFG Examples

```bash
bfg --delete-files '*.joblib' repo.git
bfg --delete-files '*.pkl' repo.git
bfg --delete-folders models repo.git
bfg --delete-folders model_zoo repo.git
```

### Validate Rewritten Mirror

```bash
git count-objects -vH
git rev-list --objects --all \
  | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize:disk) %(rest)' \
  | sort -k3 -n \
  | tail -50
```
