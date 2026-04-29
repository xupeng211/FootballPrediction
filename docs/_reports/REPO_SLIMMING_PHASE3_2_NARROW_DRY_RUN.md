# Repo Slimming Phase 3.2 Narrow Mirror Dry Run

## 1. Scope

This phase performed a narrower mirror clone dry run.

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

- Backup mirror path: `/home/xupeng/repo_history_cleanup_backups/FootballPrediction.backup.narrow.20260429_035539.git`
- Backup tar.gz path: `/home/xupeng/repo_history_cleanup_backups/FootballPrediction.backup.narrow.20260429_035539.git.tar.gz`
- Backup mirror size: `230M`
- Backup tar.gz size: `225M`
- Backup Git object state:
  - `in-pack`: `213791`
  - `packs`: `1`
  - `size-pack`: `228.65 MiB`

The backup mirror and tarball were retained for manual inspection.

## 4. Dry-Run Mirror

- Dry-run mirror path: `/home/xupeng/repo_history_cleanup_dryruns/FootballPrediction.history-cleanup-narrow-dryrun.20260429_035539.git`
- Verification worktree path: `/home/xupeng/repo_history_cleanup_dryruns/FootballPrediction.history-cleanup-narrow-verify.20260429_035539`
- Dry-run mirror type: bare mirror
- Rewritten history pushed: no

`git filter-repo` removed the `origin` remote from the dry-run mirror as part of its normal safety behavior. No mirror push was performed.

## 5. Cleanup Input

- Number of paths passed to `git filter-repo`: `138`

Candidate categories:

| Category | Count |
| --- | ---: |
| `backups/` | 55 |
| `data/` | 29 |
| `models/` | 27 |
| `venv/` | 19 |
| `model_zoo/` | 6 |
| root backup archive | 1 |
| `archive/` | 1 |

Explicitly excluded:

- `src/`
- `docs/`
- `scripts/`
- `tests/`
- `config/`
- `.github/`
- `patches/`

The forbidden path check returned no matches before running `git filter-repo`.

## 6. Before / After Size

Before:

- mirror size: `230M`
- Git object count: `213791` in pack
- Git pack count: `1`
- Git pack size: `228.65 MiB`

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

- mirror size: `152M`
- Git object count: `213479` in pack
- Git pack count: `1`
- Git pack size: `148.84 MiB`

After cleanup, the largest remaining objects included:

| Size bytes | Path |
| ---: | --- |
| 7958197 | `patches/P2_final_backend_complete.patch` |
| 7820996 | `patches/P1_5_async_unification_final.patch` |
| 3980762 | `phase_g_multilang_analysis_report_20251030_121619.json.gz` |
| 3544140 | `patches/P1-2_proxy_pool_implementation.patch` |
| 3366352 | `patches/backup_before_featurestore_20251205_225855.sql` |
| 3081752 | `tests/generated_multilang/python` |
| 1280985 | `src/data/models/xgb_football_v3.0_global.joblib` |
| 1150630 | `tests/generated_multilang/javascript` |
| 1037190 | `data/raw/archive_2023_2024.json` |
| 850001 | `data/prometheus/wal/00000001` |
| 762255 | `lightgbm_v85_prematch.model` |
| 686526 | `src/ml/data/models/xgb_v43_real_20251221_121749.joblib` |
| 619232 | `data/audit/failure_screenshot.png` |

Several large objects remain because the dry run intentionally excluded source, docs, tests, scripts, config, `.github`, and patches. Some non-excluded data paths also remain and need a follow-up review if further reduction is required.

## 7. Reduction Estimate

- Estimated mirror size reduction: `78M` (`230M` to `152M`)
- Estimated mirror size reduction percentage: approximately `33.9%`
- Estimated Git pack reduction: `79.81 MiB` (`228.65 MiB` to `148.84 MiB`)
- Estimated Git pack reduction percentage: approximately `34.9%`
- Clone size is expected to improve meaningfully if an equivalent real cleanup is approved.

This dry run shows material size reduction while preserving the intentionally excluded source, docs, tests, scripts, config, GitHub workflow, and patch paths.

## 8. Removed Path Verification

- Number of paths checked: `138`
- Number removed: `130`
- Number still present: `8`

Paths still present:

- `data/processed/features_v1.csv`
- `data/processed/features_v2_rolling.csv`
- `data/processed/features_with_teams.csv`
- `venv/share/jupyter/lab/static/227.4c50874f32ac408174fc.js`
- `venv/share/jupyter/lab/static/8786.a2bc3dfc1ea13c04ba94.js`
- `venv/share/jupyter/labextensions/@jupyter-widgets/jupyterlab-manager/static/vendors-node_modules_base64-js_index_js-node_modules_sanitize-html_index_js.c79fc2bcc3f69676beda.js`
- `venv/share/jupyter/labextensions/@jupyter-widgets/jupyterlab-manager/static/vendors-node_modules_jquery_dist_jquery_js.3afdf979a9caffdf15a7.js`
- `venv/share/jupyter/nbextensions/jupyter-js-widgets/extension.js`

These remaining paths should be reviewed before any real cleanup. A follow-up dry run may use directory-level cleanup for approved directories such as `data/processed/` and `venv/`, rather than only file-level paths from a top-object sample.

## 9. Functional Verification

- Fresh clone from cleaned mirror: passed
- Verification worktree status: clean
- Rewritten verification `main` tip: `40b233b22 docs(repo): record history cleanup dry run (#1126)`
- Verification worktree size: `168M`
- Verification `.git` size: `152M`
- Verification Git pack size: `148.84 MiB`
- Required docs/config/scripts present:
  - `docs/REPO_HISTORY_CLEANUP_PLAN.md`
  - `docs/MODEL_ARTIFACTS.md`
  - `config/model_artifacts.example.json`
  - `scripts/model_artifacts/check_model_artifacts.py`
- `docker compose config`: passed
- model artifact checker:
  - `python` command was not available on the host shell
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
- The remaining 8 candidate paths indicate the path list should be refined before real cleanup.

## 10. Risk Assessment

- Risk level: medium
- Potential risk of over-cleaning: lower than Phase 3.1 because forbidden source/docs/tests/scripts/config/patch paths were excluded
- Potential risk of recontamination from old clones: high for any future real history rewrite
- Need for collaborator re-clone: yes, if a real rewrite is later approved

The dry run demonstrates a useful reduction, but it is not yet sufficient as a final execution plan because some intended paths remained and several large intentionally excluded objects still dominate the rewritten history.

## 11. Recommendation

Recommendation: do another narrower dry run.

Do not proceed directly to real cleanup yet.

The next dry run should use a manually curated path file with directory-level entries for approved generated artifact directories, especially:

- `backups/`
- `models/`
- `model_zoo/`
- `data/archive/`
- `data/processed/`
- `data/grafana/plugins/`
- `venv/`

It should still exclude unless separately approved:

- `src/`
- `docs/`
- `scripts/`
- `tests/`
- `config/`
- `.github/`
- `patches/`

## 12. Required Manual Approval Before Real Cleanup

Before any real cleanup:

- Confirm backup is usable.
- Confirm maintenance window.
- Confirm collaborator notice.
- Confirm all open PRs are handled.
- Confirm no old clone will push stale history.
- Confirm force-with-lease or mirror-push strategy.
- Confirm the final curated cleanup path file.
- Confirm fresh-clone validation from a rewritten dry-run mirror.
- Confirm whether large excluded paths under `patches/`, `tests/`, `src/`, and root-level generated artifacts should remain.
