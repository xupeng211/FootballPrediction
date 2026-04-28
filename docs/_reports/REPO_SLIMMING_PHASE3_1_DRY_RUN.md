# Repo Slimming Phase 3.1 Mirror Clone Dry Run

## 1. Scope

This phase prepared a mirror-clone dry run for repository history cleanup.

The safety gate stopped before executing `git filter-repo` because the generated cleanup candidate list contained source/documentation paths that require manual review.

This phase did not modify the main working repository history and did not push rewritten history to GitHub.

## 2. Safety Confirmation

This dry run did not execute:

- force push
- mirror push
- history rewrite in the main working repository
- `git filter-repo` in the main working repository
- `git filter-repo` in the dry-run mirror
- BFG
- local data deletion
- Docker cleanup

## 3. Backup

- Backup mirror path: `/home/xupeng/repo_history_cleanup_backups/FootballPrediction.backup.20260429_033540.git`
- Backup tar.gz path: `/home/xupeng/repo_history_cleanup_backups/FootballPrediction.backup.20260429_033540.git.tar.gz`
- Backup mirror size: `230M`
- Backup tar.gz size: `225M`
- Backup Git object state:
  - `in-pack`: `213785`
  - `packs`: `1`
  - `size-pack`: `228.65 MiB`

The backup mirror and tarball were retained for manual inspection.

## 4. Dry-Run Mirror

- Dry-run mirror path: `/home/xupeng/repo_history_cleanup_dryruns/FootballPrediction.history-cleanup-dryrun.20260429_033540.git`
- Verification worktree path planned: `/home/xupeng/repo_history_cleanup_dryruns/FootballPrediction.history-cleanup-verify.20260429_033540`
- Verification worktree created: no

The verification worktree was not created because the safety gate stopped before history rewriting.

## 5. Cleanup Input

- Number of generated candidate paths: `124`
- Number of safety-gate matches: `4`
- Final paths passed to `git filter-repo`: `0`

Generated candidate categories:

| Category | Count |
| --- | ---: |
| `data/` | 40 |
| `backups/` | 30 |
| `models/` | 25 |
| `venv/` | 9 |
| `model_zoo/` | 6 |
| `src/` | 3 |
| `archive/` | 2 |
| root/report/generated paths | 9 |

Generated candidate extension counts:

| Extension | Count |
| --- | ---: |
| `.gz` | 30 |
| `.joblib` | 23 |
| `.png` | 13 |
| `.pkl` | 11 |
| `.json` | 10 |
| no extension | 10 |
| `.csv` | 7 |
| `.js` | 6 |
| `.cbm` | 4 |
| `.bundle` | 2 |
| `.npy` | 2 |
| `.svg` | 2 |
| `.exe` | 1 |
| `.parquet` | 1 |
| `.model` | 1 |
| `.map` | 1 |

Safety-gate matches that blocked execution:

- `docs/audit/yield_audit_chart_20251223_182617.png`
- `src/data/models/xgb_football_v3.0_global.joblib`
- `src/ml/data/models/xgb_v43_real_20251221_121749.joblib`
- `src/production_models/v9_5_walk_forward_model.pkl`

These paths may be generated artifacts or historical model files, but they are under `docs/` or `src/`. They should not be removed by an automated broad candidate rule without explicit manual approval.

## 6. Before / After Size

Before:

- dry-run mirror size: `230M`
- Git object count: `213785` in pack
- Git pack count: `1`
- Git pack size: `228.65 MiB`

Top large objects before cleanup included:

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
| 2994689 | `data/grafana/plugins/redis-datasource/redis-datasource_darwin_amd64` |
| 2941742 | `data/processed/v51_features_all.csv` |
| 2828788 | `data/archive/football_prediction_direct.pkl` |

After:

- dry-run mirror size: not available
- Git object / pack size: not available
- top large objects summary: not available

No after-cleanup values exist because `git filter-repo` was not executed after the safety gate found suspicious paths.

## 7. Reduction Estimate

- Estimated size reduction: not measured
- Percentage reduction: not measured
- Whether clone size is expected to improve: likely yes after a reviewed cleanup, but this run did not produce a cleaned mirror.

The before-cleanup top objects show meaningful cleanup potential in backup bundles, data plugin binaries, data archives, and model artifacts. A precise reduction estimate requires a second dry run with a manually curated path file.

## 8. Removed Path Verification

- Number of paths checked for removal: `0`
- Number removed: `0`
- Number still present: not checked
- Examples still present: not applicable

No path removal verification was performed because no history rewrite was executed.

## 9. Functional Verification

- Fresh clone from cleaned mirror: not performed
- `docker compose config`: not performed
- model artifact checker: not performed
- docs present: not verified in a cleaned clone

Limitations:

- This run verified backup creation and candidate generation only.
- It did not validate a rewritten repository.
- It did not measure actual clone-size reduction.
- It did not prove that a cleaned repository can pass local checks.

## 10. Risk Assessment

- Risk level: medium
- Potential risk of over-cleaning: high if broad extension rules are used without manual curation
- Potential risk of recontamination from old clones: high for any future real history rewrite
- Need for collaborator re-clone: yes, if a real rewrite is later approved

The generated candidate list correctly found many data/model/backup artifacts, but it also captured `docs/` and `src/` paths. That makes the first automated path list too broad for real cleanup.

## 11. Recommendation

Recommendation: do another narrower dry run.

Do not proceed to real cleanup yet.

The next dry run should use a manually curated path file that removes only clearly approved artifact locations, such as:

- `backups/`
- `models/`
- `model_zoo/`
- selected `data/archive/`
- selected `data/processed/`
- `data/grafana/plugins/redis-datasource/`
- selected `data/prometheus/`
- `venv/`

The next dry run should explicitly exclude, unless separately approved:

- `src/`
- `scripts/`
- `tests/`
- `config/`
- `docs/`
- `.github/`
- `patches/`
- root-level generated images that might be documentation evidence

## 12. Required Manual Approval Before Real Cleanup

Before any real cleanup:

- Confirm backup is usable.
- Confirm maintenance window.
- Confirm collaborator notice.
- Confirm all open PRs are handled.
- Confirm no old clone will push stale history.
- Confirm the exact force-with-lease or mirror-push strategy.
- Confirm the manually curated cleanup path file.
- Confirm fresh-clone validation from a rewritten dry-run mirror.

No real history cleanup should be executed from the main working repository.
