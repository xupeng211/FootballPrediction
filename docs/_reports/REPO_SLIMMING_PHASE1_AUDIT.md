# Repo Slimming Phase 1 Audit

## 1. 当前仓库体积

- 工作区大小：`244M`
- `.git` 大小：`199M`
- Git pack 大小：`197.71 MiB`
- 判断：当前主要重量在 Git pack / 历史对象中，而不是工作区源码本身。

## 2. 当前风险文件

- 已跟踪的数据文件：`data/` 下 5 个文件；风险扩展扫描中数据类约 6 项。
- 已跟踪的模型文件：`models/` 下 36 个文件，`model_zoo/` 下 3 个文件；模型产物类约 39 项。
- 已跟踪的日志/缓存/备份：当前分支未发现 `logs/`、`htmlcov/`、`coverage/`、`backups/` 下的已跟踪文件。
- 已跟踪的二进制文件：当前风险扩展扫描命中 1 个媒体/二进制类文件，另有多个模型权重属于二进制产物。
- 当前已跟踪且超过 1M 的典型文件：
  - `models/baseline_v1/baseline_v1_result_1x2.calibrated.joblib`，约 5.6M
  - `models/titan_v4468_combat.joblib`，约 2.9M
  - `tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/test_data/quality_test_sample_20251130.json`，约 2.5M
  - `models/titan_real_test_20260314_021246.joblib`，约 2.2M
  - `models/titan_real_test_20260314_032238.joblib`，约 2.2M
  - `models/titan_real_test_20260314_024704.joblib`，约 2.1M

## 3. 历史大对象

- Top 大对象摘要：
  - `backups/git_before_filter_repo_20251004_220053/repo_backup.bundle`，约 13.8M
  - `data/grafana/plugins/redis-datasource/redis-datasource_windows_amd64.exe`，约 6.0M
  - `data/grafana/plugins/redis-datasource/redis-datasource_darwin_arm64`，约 6.0M
  - `data/grafana/plugins/redis-datasource/redis-datasource_linux_amd64`，约 5.9M
  - `data/grafana/plugins/redis-datasource/redis-datasource_linux_arm`，约 5.6M
  - `data/grafana/plugins/redis-datasource/redis-datasource_linux_arm64`，约 5.4M
  - `archive/phase_g_multilang_analysis_report_20251030_121619.json.gz`，约 4.0M
  - `models/pilot_v320_hybrid/xgboost_model.json`，约 3.0M
  - `data/processed/v51_features_all.csv`，约 2.9M
  - `data/archive/football_prediction_direct.pkl`，约 2.8M
- 是否需要第二阶段历史清理：建议需要，但必须独立规划。历史中已经包含数据、模型、备份、venv、Grafana 插件二进制等对象。

## 4. 本阶段修改

- `.gitignore` 修改摘要：
  - 增加仓库瘦身第一阶段护栏。
  - 默认忽略 `data/**`、`models/**`、`model_zoo/**`、日志、coverage、缓存、备份、构建产物和常见模型/数据/压缩/二进制扩展。
  - 明确保留 `data/mock/`、`data/manual_html/test_sample.html`、`data/snapshots/.gitkeep`、`docs/**`、`tests/fixtures/**`、`.env.example`、`config/.env.example`。
- 新增/更新文档：
  - `docs/DATA_MODEL_STORAGE_POLICY.md`
  - `docs/_reports/REPO_SLIMMING_PHASE1_AUDIT.md`
- 本阶段未执行 `git rm --cached`；当前已跟踪的大型数据/模型文件仍在 Git 当前版本中。

## 5. 未执行的高风险操作

本阶段没有执行：

- history rewrite
- `git filter-repo`
- BFG
- force push
- 删除本地数据
- Docker volume 删除

## 6. 下一阶段建议

- 第二阶段单独 PR 评估并执行 `git rm --cached`，移除当前已跟踪的大型数据、模型和产物文件，同时保留本地文件。
- 对 `data/`、`models/`、`model_zoo/`、`archive/` 的清理需要逐项确认，避免误删仍被业务或测试依赖的小型样例。
- 必要时第三阶段再规划 `git filter-repo` 或 BFG 历史清理。
- 历史清理前必须完整备份，并通知所有协作者需要重新 clone 或按迁移手册重置本地仓库。
