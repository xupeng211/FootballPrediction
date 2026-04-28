# Repo Slimming Phase 3 History Audit

## 1. Scope

This audit plans repository history cleanup but does not execute it.

The scope is limited to:

- Measuring current repository and Git object size.
- Auditing top historical objects.
- Identifying candidate cleanup paths.
- Recommending a dry-run and backup approach.

This phase did not modify source code, Docker configuration, model inference logic, data collection logic, current Git history, or local data files.

## 2. Current Repository Size

- Working tree: `217M`
- `.git`: `200M`
- Git pack: `197.71 MiB`
- Pack count: `1`
- Largest pack file: `.git/objects/pack/pack-a8d051c17ef8bb80edafaa4426f231cbc0873612.pack`
- Largest pack file size: `201656210` bytes

The repository is still history-heavy because Phase 2 removed model artifacts from the current index only. Existing historical blobs remain in `.git`.

## 3. Top Historical Objects

Top large historical objects from the audit sample:

| Size bytes | Object type | Path |
| ---: | --- | --- |
| 13825460 | blob | `backups/git_before_filter_repo_20251004_220053/repo_backup.bundle` |
| 5996810 | blob | `data/grafana/plugins/redis-datasource/redis-datasource_windows_amd64.exe` |
| 5984478 | blob | `data/grafana/plugins/redis-datasource/redis-datasource_darwin_arm64` |
| 5902791 | blob | `data/grafana/plugins/redis-datasource/redis-datasource_linux_amd64` |
| 5570683 | blob | `data/grafana/plugins/redis-datasource/redis-datasource_linux_arm` |
| 5376574 | blob | `data/grafana/plugins/redis-datasource/redis-datasource_linux_arm64` |
| 3980762 | blob | `archive/phase_g_multilang_analysis_report_20251030_121619.json.gz` |
| 3152822 | blob | `models/pilot_v320_pure/xgboost_model.json` |
| 3081752 | tree | `tests/generated_multilang/python` |
| 3037315 | blob | `models/pilot_v320_hybrid/xgboost_model.json` |
| 2994689 | blob | `data/grafana/plugins/redis-datasource/redis-datasource_darwin_amd64` |
| 2941742 | blob | `data/processed/v51_features_all.csv` |
| 2828788 | blob | `data/archive/football_prediction_direct.pkl` |
| 1376394 | blob | `models/baseline_v1/baseline_v1_result_1x2.calibrated.joblib` |
| 1280985 | blob | `src/data/models/xgb_football_v3.0_global.joblib` |
| 1165385 | blob | `model_zoo/v41_430_catboost_model_20260121_152451.cbm` |
| 1150630 | tree | `tests/generated_multilang/javascript` |
| 1119071 | blob | `model_zoo/v41_430_catboost_model_20260121_152618.cbm` |
| 1037190 | blob | `data/raw/archive_2023_2024.json` |
| 991294 | blob | `models/titan_v4468_combat.joblib` |

Main concentrations:

- Backup bundles and backup-captured compressed raw data.
- Grafana Redis datasource plugin binaries.
- Processed datasets and model training artifacts.
- Historical model binaries in `models/`, `model_zoo/`, and legacy source data paths.
- Generated analysis charts and virtual environment assets.

## 4. Cleanup Candidates

The top 150 historical objects produced 129 candidate paths.

Directory counts:

| Category | Count |
| --- | ---: |
| `data/` | 41 |
| `backups/` | 32 |
| `models/` | 23 |
| `venv/` | 12 |
| `model_zoo/` | 6 |
| `src/` legacy model paths | 3 |
| `archive/` | 2 |
| Root-level or report/generated assets | 10 |

Extension counts:

| Extension | Count |
| --- | ---: |
| `.gz` | 32 |
| `.joblib` | 21 |
| `.png` | 14 |
| `.json` | 11 |
| `.pkl` | 11 |
| no extension | 10 |
| `.csv` | 7 |
| `.js` | 7 |
| `.cbm` | 4 |
| `.bundle` | 2 |
| `.npy` | 2 |
| `.svg` | 2 |
| `.exe` | 1 |
| `.parquet` | 1 |
| `.model` | 1 |
| `.eot` | 1 |
| `.ttf` | 1 |
| `.map` | 1 |

Recommended cleanup candidate groups:

### models

- `models/`
- `models/baseline_v1/baseline_v1_result_1x2.calibrated.joblib`
- `models/pilot_v320_hybrid/xgboost_model.json`
- `models/pilot_v320_pure/xgboost_model.json`
- `models/titan_v4468_combat.joblib`
- `models/war_god_v31_final.joblib`

### model_zoo

- `model_zoo/`
- `model_zoo/v172_beta.model`
- `model_zoo/v41_430_catboost_model_20260121_152445.cbm`
- `model_zoo/v41_430_catboost_model_20260121_152451.cbm`
- `model_zoo/v41_430_catboost_model_20260121_152618.cbm`
- `model_zoo/v41_430_catboost_model_20260121_152624.cbm`

### data

- `data/archive/`
- `data/processed/`
- `data/raw/archive_2023_2024.json`
- `data/pilot_v320_hybrid/`
- `data/pilot_v41_300/`
- `data/prometheus/`
- `data/grafana/plugins/redis-datasource/`

### backups

- `backups/git_backup_20251004_215227/repo_full_backup.bundle`
- `backups/git_before_filter_repo_20251004_220053/repo_backup.bundle`
- `backups/v1.0_stable_20251214/src/data/raw_landing/fbref/`

### archive

- `archive/final_project_coverage.json`
- `archive/phase_g_multilang_analysis_report_20251030_121619.json.gz`

### binary/plugin artifacts

- `data/grafana/plugins/redis-datasource/`
- `venv/share/jupyter/`

### review-required generated artifacts

- `V9_0_MODEL_ANALYSIS.png`
- `V9_1_CALIBRATION_COMPARISON.png`
- `V9_2_CALIBRATION_COMPARISON.png`
- `V9_2_TRADE_ANALYSIS.png`
- `V9_3_LARGE_SCALE_CALIBRATION_COMPARISON.png`
- `feature_importance_v7.png`
- `feature_importance_v7_enhanced.png`
- `reports/v34_market/v34_alpha_charts_20251228_030427.png`
- `docs/audit/yield_audit_chart_20251223_182617.png`
- `scripts_backup_20251005_103855.tar.gz`

Review-required generated artifacts should not be removed blindly. Some may be documentation evidence, even if they are not ideal Git history contents.

## 5. Tool Recommendation

Recommended tool: `git filter-repo`.

Why:

- The target set is path-specific.
- The repository must preserve normal source history while removing selected large artifacts.
- Broad extension deletion could catch valid fixtures or documentation assets.
- Mirror clone dry runs are easier to repeat and audit with explicit path rules.

BFG Repo-Cleaner remains a fallback for broad cleanup, such as deleting all `*.joblib` or all `models` folders in a mirror clone. It is not the first recommendation here because this repository has mixed historical content and needs precise review.

Any chosen tool rewrites history and requires a coordinated migration.

## 6. Risk Assessment

History rewrite risk:

- Commit IDs change.
- Existing clones become based on old history.
- Old branches can reintroduce removed objects if merged directly.

Force-push risk:

- A real cleanup requires replacing remote history.
- This must happen only after dry run, backup validation, and a maintenance window.
- It must not be performed from the normal working tree.

Collaborator clone risk:

- The safest migration is a fresh clone.
- Local work should be exported or moved to fresh branches before the rewrite.
- Old clones should not push to the rewritten repository.

Risk of accidentally reintroducing old objects:

- Merging old branches or tags can bring large blobs back.
- Old release refs must be reviewed.
- Protected branch and permission rules should be checked before the rewrite.

## 7. Required Pre-Execution Steps

- Create and verify a mirror backup.
- Create a separate mirror clone for dry run.
- Regenerate the historical large object report in the mirror clone.
- Review candidate paths manually.
- Execute `git filter-repo` only in the dry-run mirror.
- Measure size reduction.
- Fresh clone from the dry-run result.
- Validate repository function and CI strategy.
- Confirm model artifacts remain external and restorable through the Phase 2.5 scaffold.
- Notify collaborators.
- Choose a maintenance window.
- Prepare re-clone and migration instructions.

## 8. Explicitly Not Executed

This phase did not run:

- `git filter-repo`
- BFG Repo-Cleaner
- force push
- mirror push
- history rewrite
- local data deletion
- Docker cleanup
- Git index removal

## 9. Next Recommended Action

Create a PR for this planning document and audit report.

After the planning PR is merged, run a separate Phase 3 dry run in a mirror clone. Do not perform a real history rewrite until backup, dry run, CI validation, collaborator notification, maintenance window, and re-clone plan are all approved.
