# Repo Slimming Phase 3.3 Manual Path Mirror Dry Run

## 1. Scope

This phase performed a manual-path mirror clone dry run.

It executed `git filter-repo` only in a disposable mirror clone under `/home/xupeng/repo_history_cleanup_dryruns/`.

It did not modify the main working repository history and did not push rewritten history to GitHub.

## 2. Safety Confirmation

This dry run did not execute:

- force push
- mirror push
- history rewrite in the main working repository
- BFG
- local data deletion
- Docker cleanup

The dry-run mirror was separate from `/home/xupeng/FootballPrediction`.

## 3. Backup

- Backup mirror path: `/home/xupeng/repo_history_cleanup_backups/FootballPrediction.backup.manual.20260429_082225.git`
- Backup tar.gz path: `/home/xupeng/repo_history_cleanup_backups/FootballPrediction.backup.manual.20260429_082225.git.tar.gz`
- Backup mirror size: `230M`
- Backup tar.gz size: `225M`
- Backup Git object state:
  - `in-pack`: `213797`
  - `packs`: `1`
  - `size-pack`: `228.66 MiB`

The backup mirror and tarball were retained for manual inspection.

## 4. Dry-Run Mirror

- Dry-run mirror path: `/home/xupeng/repo_history_cleanup_dryruns/FootballPrediction.history-cleanup-manual-dryrun.20260429_082225.git`
- Verification worktree path: `/home/xupeng/repo_history_cleanup_dryruns/FootballPrediction.history-cleanup-manual-verify.20260429_082225`
- Dry-run mirror type: bare mirror
- Rewritten history pushed: no

`git filter-repo` removed the `origin` remote from the dry-run mirror as part of its normal safety behavior. No mirror push was performed.

## 5. Manual Cleanup Input

Exact paths passed to `git filter-repo`:

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

- Number of manual paths: `8`
- Forbidden path check result: no matches

Explicitly excluded:

- `src/`
- `docs/`
- `scripts/`
- `tests/`
- `config/`
- `.github/`
- `patches/`
- `archive/`
- `data/raw/`

## 6. Deferred Manual Review

Large objects remain under paths that were intentionally not cleaned in this low-risk dry run.

Examples from the pre-cleanup and post-cleanup audits:

- `patches/P2_final_backend_complete.patch`
- `patches/P1_5_async_unification_final.patch`
- `patches/P1-2_proxy_pool_implementation.patch`
- `patches/backup_before_featurestore_20251205_225855.sql`
- `tests/generated_multilang/python`
- `tests/generated_multilang/javascript`
- `src/data/models/xgb_football_v3.0_global.joblib`
- `src/ml/data/models/xgb_v43_real_20251221_121749.joblib`
- `src/production_models/v9_5_walk_forward_model.pkl`
- `data/raw/archive_2023_2024.json`
- `archive/phase_g_multilang_analysis_report_20251030_121619.json.gz`
- `backups/git_backup_20251004_215227/repo_full_backup.bundle`
- `data/archive/football_prediction_v4_optuna.pkl`
- `data/archive/xgboost_match_result_20251126_171156.pkl`
- `data/prometheus/wal/00000001`

These paths should require separate manual approval before any real history cleanup includes them.

## 7. Before / After Size

Before:

- mirror size: `230M`
- Git object count: `213797` in pack
- Git pack count: `1`
- Git pack size: `228.66 MiB`

Before cleanup, the largest objects included:

| Size bytes | Path |
| ---: | --- |
| 13825460 | `backups/git_before_filter_repo_20251004_220053/repo_backup.bundle` |
| 7958197 | `patches/P2_final_backend_complete.patch` |
| 7820996 | `patches/P1_5_async_unification_final.patch` |
| 5996810 | `data/grafana/plugins/redis-datasource/redis-datasource_windows_amd64.exe` |
| 5984478 | `data/grafana/plugins/redis-datasource/redis-datasource_darwin_arm64` |
| 5902791 | `data/grafana/plugins/redis-datasource/redis-datasource_linux_amd64` |
| 5570683 | `data/grafana/plugins/redis-datasource/redis-datasource_linux_arm` |
| 5376574 | `data/grafana/plugins/redis-datasource/redis-datasource_linux_arm64` |
| 3980762 | `archive/phase_g_multilang_analysis_report_20251030_121619.json.gz` |
| 3544140 | `patches/P1-2_proxy_pool_implementation.patch` |
| 3366352 | `patches/backup_before_featurestore_20251205_225855.sql` |
| 3152822 | `models/pilot_v320_pure/xgboost_model.json` |
| 3037315 | `models/pilot_v320_hybrid/xgboost_model.json` |
| 2941742 | `data/processed/v51_features_all.csv` |
| 2828788 | `data/archive/football_prediction_direct.pkl` |

After:

- mirror size: `162M`
- Git object count: `212766` in pack
- Git pack count: `1`
- Git pack size: `159.10 MiB`

After cleanup, the largest remaining objects included:

| Size bytes | Path |
| ---: | --- |
| 7958197 | `patches/P2_final_backend_complete.patch` |
| 7820996 | `patches/P1_5_async_unification_final.patch` |
| 7037025 | `backups/git_backup_20251004_215227/repo_full_backup.bundle` |
| 3980762 | `archive/phase_g_multilang_analysis_report_20251030_121619.json.gz` |
| 3544140 | `patches/P1-2_proxy_pool_implementation.patch` |
| 3366352 | `patches/backup_before_featurestore_20251205_225855.sql` |
| 3081752 | `tests/generated_multilang/python` |
| 1280985 | `src/data/models/xgb_football_v3.0_global.joblib` |
| 1150630 | `tests/generated_multilang/javascript` |
| 1037190 | `data/raw/archive_2023_2024.json` |
| 850001 | `data/prometheus/wal/00000001` |
| 814043 | `data/archive/football_prediction_v4_optuna.pkl` |
| 686526 | `src/ml/data/models/xgb_v43_real_20251221_121749.joblib` |
| 619232 | `data/audit/failure_screenshot.png` |

## 8. Reduction Estimate

- Estimated mirror size reduction: `68M` (`230M` to `162M`)
- Estimated mirror size reduction percentage: approximately `29.6%`
- Estimated Git pack reduction: `69.56 MiB` (`228.66 MiB` to `159.10 MiB`)
- Estimated Git pack reduction percentage: approximately `30.4%`
- Clone size is expected to improve meaningfully if an equivalent real cleanup is approved.

This manual whitelist run produced less reduction than Phase 3.2, but it used a lower-risk input set.

## 9. Removed Path Verification

- Number of paths checked: `8`
- Number removed by the prescribed check: `7`
- Number still present by the prescribed check: `1`

Prescribed check result still present:

- `models/`

Follow-up exact check:

- Top-level `models/` paths remaining: `0`
- The `models/` still-present result was caused by broader substring matches under intentionally excluded paths such as `src/.../models` and `tests/.../models`.

The following manual inputs were removed:

- `backups/git_before_filter_repo_20251004_220053/repo_backup.bundle`
- `data/grafana/plugins/redis-datasource/`
- `data/processed/v51_features_all.csv`
- `data/archive/football_prediction_direct.pkl`
- `model_zoo/`
- `venv/`
- `.venv/`

## 10. Functional Verification

- Fresh clone from cleaned mirror: passed
- Verification worktree status: clean
- Rewritten verification `main` tip: `96a9457ce docs(repo): record narrow history cleanup dry run (#1127)`
- Verification worktree size: `179M`
- Verification `.git` size: `162M`
- Verification Git pack size: `159.10 MiB`
- Required docs/config/scripts present:
  - `docs/REPO_HISTORY_CLEANUP_PLAN.md`
  - `docs/MODEL_ARTIFACTS.md`
  - `config/model_artifacts.example.json`
  - `scripts/model_artifacts/check_model_artifacts.py`
- `docker compose config`: passed
- model artifact checker:
  - `python3 scripts/model_artifacts/check_model_artifacts.py --allow-missing` ran successfully
  - expected missing artifacts: `2`

Artifact checker output:

```text
Manifest: config/model_artifacts.example.json
MISSING: baseline_v1_result_1x2 -> models/baseline_v1/baseline_v1_result_1x2.calibrated.joblib
MISSING: titan_v4468_combat -> models/titan_v4468_combat.joblib
total=2
missing=2
```

Limitations:

- No `docker compose up` was run.
- No full test suite was run.
- The dry-run mirror was not pushed anywhere.
- Large objects remain in excluded paths and need separate manual review.

## 11. Risk Assessment

- Risk level: low-to-medium for the manual whitelist itself
- Potential risk of over-cleaning: low, because only 8 high-confidence paths were used
- Potential risk of recontamination from old clones: high for any future real history rewrite
- Need for collaborator re-clone: yes, if a real rewrite is later approved

The dry run demonstrates a useful reduction while avoiding broad automated cleanup. The remaining size is mostly from paths intentionally deferred for manual review.

## 12. Recommendation

Recommendation: proceed to real cleanup only after manual approval.

This manual whitelist is a plausible low-risk candidate for a real rewrite, but it must still be approved before execution. If maintainers want a larger reduction, do another dry run with explicitly approved additions such as selected backup archives, generated test output, or patch files.

Do not execute real history cleanup until the final path list, backup, maintenance window, collaborator migration, and push strategy are all confirmed.

## 13. Required Manual Approval Before Real Cleanup

Before any real cleanup:

- Confirm backup is usable.
- Confirm maintenance window.
- Confirm collaborator notice.
- Confirm all open PRs are handled.
- Confirm no old clone will push stale history.
- Confirm force-with-lease or mirror-push strategy.
- Confirm the final manual cleanup path file.
- Confirm fresh-clone validation from a rewritten dry-run mirror.
- Confirm whether deferred paths under `patches/`, `tests/`, `src/`, `archive/`, `data/raw/`, and other backup directories should remain.
