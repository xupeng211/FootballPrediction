# Phase 4.51 - real finished match data source strategy / license / provenance / schema mapping report

## 1. 当前 HEAD

- 当前分支：`docs/real-data-source-strategy-phase451`
- 起始 HEAD：`243eb01c201133a7e6413bbbaaba954aff30be86`
- HEAD 摘要：`243eb01 docs(data): add synthetic chain closure report`

本阶段仅进行了：

- `git fetch origin main`
- `git switch main`
- `git reset --hard origin/main`，且执行前已确认工作区 clean
- 创建本地工作分支
- SELECT-only DB / dataset 审计
- 本地文件只读扫描
- 本地源码 / 文档只读审计

本阶段没有下载任何外部数据，也没有访问外部数据源。

## 2. 当前 DB / dataset status

只读确认结果：

| table                     | rows |
| ------------------------- | ---: |
| `matches`                 |    2 |
| `bookmaker_odds_history`  |    2 |
| `raw_match_data`          |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

`make data-dataset-status` 关键结果：

- `trainable = false`
- `finished_matches = 1`
- `matches_with_actual_result = 1`
- `matches_with_scores = 1`
- `trainable_label_rows = 1`
- `scheduled_or_unlabeled_rows = 1`
- `full_feature_chain_rows = 1`
- `baseline_prediction_rows = 1`
- `prediction_rows_not_training_labels = 2`

训练 readiness 结论：

- 当前 dev DB 只有 `1` 条可训练 label
- 当前 dev DB 只有 `1` 条 full feature-chain row
- 当前 dev DB 仍不具备真实模型训练条件
- 推荐下一步仍然是 `Build a finished-match sample audit before training.`

## 3. Phase 4.50 synthetic closure 摘要

Phase 4.50 已确认目标比赛 `47_20242025_900002` 完成 synthetic engineering chain closure：

- `matches` exists
- `raw_match_data` exists, synthetic only
- `l3_features` exists, synthetic only
- `match_features_training` exists, synthetic only
- `predictions` exists, synthetic baseline only

并已确认：

- synthetic chain 只能用于工程验证
- synthetic chain 不能用于真实训练
- synthetic chain 不能用于 production prediction

相关报告：

- `docs/_reports/SYNTHETIC_PREDICTION_SINGLE_INSERT_PHASE4_49.md`
- `docs/_reports/SYNTHETIC_CHAIN_CLOSURE_PHASE4_50.md`

## 4. 为什么不继续堆 synthetic 数据

继续新增 synthetic 数据不能解决当前真实训练前置问题，原因如下：

1. synthetic rows 不能证明真实数据 source / license / provenance 合法性
2. synthetic rows 不能证明真实 finished historical coverage
3. synthetic rows 不能替代真实 kickoff 前可得 feature timing 审计
4. synthetic rows 不能作为真实训练 label 或真实预测输出
5. 当前缺口已从“工程链路是否能闭环”转变为“真实数据是否可合法、可追溯、可映射、可防 leakage 地进入 dry-run staging”

因此，Phase 4.51 的重点必须从 synthetic 扩展切换为真实数据策略设计。

## 5. 本地数据候选扫描摘要

本地只读扫描范围：

- `data/`
- `tests/`
- `docs/`
- 排除了 `data/postgres/`
- 排除了 `data/backups/`

扫描结果：

- 本地候选文件总数：`102`
- 其中 CSV / JSON / MD 混合存在
- 明显可作为 finished CSV 形态参考的本地样本极少

### 5.1 仍然存在的小样本 CSV

`data/mock/sample_history.csv`

- 4 行
- 含 `match_id`、`league_name`、`season`、`home_team`、`away_team`、`match_date`
- 含 `status`
- 含赔率列
- 含 `home_score` / `away_score`
- 当前只提供极小样本

结论：

- 它仍然只是小样本 / gate preview fixture
- 适合作为本地 CSV schema preview 参考
- 不构成真实 finished historical dataset
- 不能单独支撑真实训练

### 5.2 不可作为真实 source-of-truth 的本地候选

`docs/audit/yield_audit_data_20251223_182618.csv`

- 行数较多
- 含 `result_score`、`predicted_result`、赔率和误差列

结论：

- 更像评估 / 审计产物
- 不是原始 finished historical import source
- 不能直接当作真实标签源

### 5.3 synthetic / synthetic-derived 文件

例如：

- `tests/fixtures/synthetic/raw_match_data_47_20242025_900002_phase442.json`
- `docs/_reports/SYNTHETIC_*`

结论：

- synthetic 文件不能算真实数据源
- 只能作为工程验证或 provenance 反例

### 5.4 legacy / mock / fixture JSON

例如：

- `tests/fixtures/match_success.json`
- `tests/fixtures/l3/raw_match_data_phase419_sample.json`
- `tests/mocks/fulham_api_sample.json`
- `tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/fixtures/*`

结论：

- 可作为 schema reference / parser reference / dry-run fixture reference
- 不能冒充真实合法来源
- 没有明确 license / provenance 结论前，不得当作真实 import source

## 6. 现有 ingest / loader / harvest 入口风险审计

### 6.1 已有安全 dry-run / read-only 入口

- `make data-dataset-status`
- `make data-training-dataset-dry-run`
- `make data-finished-csv-dry-run SAMPLE_CSV=<local csv>`
- `make data-finished-backfill-dry-run MATCH_ID=<id>`
- `make data-raw-dry-run SAMPLE_RAW=<local fixture> MATCH_ID=<id>`
- `make data-raw-fixture-dry-run MATCH_ID=<id> FIXTURE=<local json>`
- `make data-synthetic-l3-dry-run MATCH_ID=<id>`
- `make data-synthetic-training-feature-dry-run MATCH_ID=<id>`
- `make data-synthetic-prediction-dry-run MATCH_ID=<id>`

这些入口的共同点：

- dry-run / preflight only
- no DB writes
- no training
- no prediction execution
- no model artifact load
- no external network

### 6.2 已有 blocked commit 入口

- `make data-finished-csv-commit`
- `make data-finished-backfill-commit`
- `make data-raw-commit`
- `make data-raw-fixture-commit`
- `make data-synthetic-l3-commit`
- `make data-synthetic-training-feature-commit`
- `make data-synthetic-prediction-commit`
- `make data-training-dataset-export`
- `make data-training-commit`
- `make data-prediction-commit`
- `make data-prediction-write-commit`

这些入口当前仍应保持 blocked，不能替代真实授权流程。

### 6.3 危险真实入口 / 不应执行入口

脚本 / npm script 审计发现以下高风险入口仍存在：

- `scripts/ops/csv_bulk_loader.js`
- `scripts/ops/local_dom_ingestor.js`
- `scripts/ops/raw_match_data_local_ingest.js`
- `scripts/ops/backfill_historical_raw_match_data.js`
- `scripts/ops/batch_historical_backfill.js`
- `scripts/ops/odds_harvest_pipeline.js`
- `scripts/ops/run_production.js`
- `scripts/ops/train_model.py`
- `scripts/ops/predict_pipeline.py`
- `npm run odds:harvest`
- `npm run harvest:production`
- `npm run train`
- `npm run predict`

这些入口要么会触发真实 ingest / harvest / train / predict，要么会触发 commit 型路径，不应在真实数据策略阶段执行。

### 6.4 后续需要新建的 real data dry-run gate

本仓库还缺少一个围绕真实数据 source manifest + local staging 文件的专用 dry-run gate。Phase 4.52 应补这个缺口，但本阶段不实现脚本。

## 7. 真实数据源候选矩阵

以下矩阵是 Phase 4.51 的策略设计，不代表本阶段已访问、下载或验证外部源。所有 source / license / terms / coverage 都需要后续人工确认。

| Candidate                                       | 数据类型                            | 优点                                               | 风险                                                                           | 适合用途                                      | 不适合                                        | 下一步                                                          |
| ----------------------------------------------- | ----------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------------------ | --------------------------------------------- | --------------------------------------------- | --------------------------------------------------------------- |
| `A. OpenFootball / football.db / football.json` | 赛程、赛果、teams、competitions     | 公开数据生态，结构通常较清晰                       | 可能缺少 odds / rich raw event / L3 所需字段；具体 license/coverage 需人工确认 | `matches` + labels dry-run                    | `raw_match_data` rich event、L3 rich features | 先做 license / provenance verification，不下载                  |
| `B. Football-Data.co.uk CSV`                    | 历史结果、赔率、部分比赛统计 CSV    | 结构化 CSV，适合 `matches` / labels / odds mapping | license / terms / attribution / commercial use 需人工确认                      | finished matches + score + odds dry-run       | rich raw event JSON                           | 先做人类许可确认，再手动下载到本地 staging，不让 Codex 直接下载 |
| `C. StatsBomb Open Data`                        | open event data / lineups / matches | event-level schema 丰富，适合 raw/event 映射       | 比赛覆盖有限；terms / attribution 需遵守；目标联赛覆盖不确定                   | `raw_match_data` adapter / event data mapping | 大范围 finished odds coverage                 | 先审计 license 和 subset，不直接下载                            |
| `D. 用户自有合法 CSV / 手动导出`                | 用户手动提供的 CSV / JSON           | 来源可控，最适合本地 staging dry-run               | 字段质量、重复、编码、日期、team mapping 风险                                  | 真实 import dry-run 首选                      | 无 provenance 的直接写库                      | 让用户提供本地路径或上传，不让 Codex 抓取                       |

明确不推荐：

- 未授权 scraping
- FotMob scraping
- 绕过 ToS 的采集
- 用浏览器自动化批量抓真实数据
- 无 provenance 的数据源
- 把 synthetic 当真实

## 8. license / provenance checklist

真实数据接入前，source manifest 至少要包含以下字段：

- `source_name`
- `source_url`
- `license_url`
- `terms_url`
- `license_type`
- `allowed_use`
- `attribution_required`
- `commercial_use_allowed`
- `redistribution_allowed`
- `rate_limit_or_access_rules`
- `data_owner`
- `downloaded_by`
- `downloaded_at`
- `original_filename`
- `sha256`
- `row_count`
- `competition_coverage`
- `season_coverage`
- `field_dictionary_path`
- `mapping_version`
- `import_dry_run_report_path`
- `approval_status`
- `human_approval_note`

强制规则：

- 没有 license / terms 结论前，不得导入
- 没有 provenance metadata，不得导入
- 外部下载必须单独授权
- 写库必须单独授权 + `pg_dump`

## 9. schema mapping 设计

本阶段只做 mapping 设计，不实现写库。

### 9.1 `matches` mapping

常见字段映射：

| source field             | target field         |
| ------------------------ | -------------------- |
| `Date` / `date`          | `match_date`         |
| `HomeTeam` / `home_team` | `home_team`          |
| `AwayTeam` / `away_team` | `away_team`          |
| `FTHG` / `home_score`    | `home_score`         |
| `FTAG` / `away_score`    | `away_score`         |
| `FTR` / `actual_result`  | `actual_result`      |
| `Div` / `league`         | `league_name`        |
| `season`                 | `season`             |
| `status`                 | `finished`           |
| derived                  | `is_finished = true` |
| source manifest          | `data_source`        |
| import batch version     | `data_version`       |

补充规则：

- `FTR H/D/A` 规范化为 `home_win/draw/away_win`
- 若无直接 `FTR`，只允许在 `finished + complete score` 条件下由比分推导 label
- `scheduled` / `postponed` / `abandoned` 不能进入 label-ready rows

### 9.2 `bookmaker_odds_history` mapping

常见字段映射：

| source field             | target field                      |
| ------------------------ | --------------------------------- |
| `B365H` / `PSH` 等       | `odds_home`                       |
| `B365D` / `PSD` 等       | `odds_draw`                       |
| `B365A` / `PSA` 等       | `odds_away`                       |
| bookmaker column         | `bookmaker`                       |
| fixed                    | `market_type = 1x2`               |
| source timestamp         | `captured_at` / source-time field |
| source manifest metadata | provenance sidecar                |

设计要求：

- 必须保留 bookmaker 名称
- 必须保留时间戳
- 不允许把赛后 closing odds 冒充赛前 odds
- 同一 match 多快照要能做时间排序

### 9.3 `raw_match_data` mapping

只有 event-level / raw JSON 数据源才适合映射到 `raw_match_data`。

目标结构至少包括：

- `matchId`
- `general`
- `header`
- `content`
- provider metadata
- license / provenance metadata
- `raw_data` hash

设计要求：

- raw payload 必须保留来源
- raw payload 必须保留 provider / manifest 对应关系
- raw payload 进入库前必须能计算 `sha256` / hash

### 9.4 labels 设计

标签规则：

- `FTR H/D/A -> home_win / draw / away_win`
- 只有 `finished` 且比分完整时，才允许由比分推导 label
- `scheduled` / `postponed` / `abandoned` / status 不明确的行不可作为 label

## 10. leakage 防护规则

真实训练前必须明确以下规则：

- 训练特征只能使用 kickoff 前可得信息
- finished score / `actual_result` 只能作为 label，不能作为 feature
- 赛后 stats / xG / shotmap / events 不可作为赛前预测特征，除非明确研究的是 post-match task
- odds snapshot 必须有时间戳，不能使用赛后 closing odds 冒充赛前 odds
- chronological split，禁止 random split
- 同一 match 不可同时出现在 train / validation / test
- synthetic rows 不可进入真实训练集
- baseline predictions 不可作为 label 或 feature
- `predictions` 表不可反哺训练
- manual / synthetic / model-generated prediction 必须区分

附加 timing 审计要求：

- `feature_time <= cutoff_time <= kickoff_time`
- 缺少时间戳的特征不得直接进入真实训练
- 任何 backfill 特征若无法证明原始观察时点，应先隔离

## 11. source manifest 建议格式

建议 Phase 4.52 使用本地 manifest 文件，例如 JSON：

```json
{
    "source_name": "example-real-source",
    "source_url": "MANUAL_ONLY",
    "license_url": "MANUAL_ONLY",
    "terms_url": "MANUAL_ONLY",
    "license_type": "PENDING_HUMAN_REVIEW",
    "allowed_use": "PENDING_HUMAN_REVIEW",
    "attribution_required": true,
    "commercial_use_allowed": false,
    "redistribution_allowed": false,
    "rate_limit_or_access_rules": "MANUAL_ONLY",
    "data_owner": "PENDING",
    "downloaded_by": "human_name",
    "downloaded_at": "2026-05-05T00:00:00Z",
    "original_filename": "sample.csv",
    "local_staging_path": "staging/real/sample.csv",
    "sha256": "REQUIRED",
    "row_count": 0,
    "competition_coverage": ["Segunda"],
    "season_coverage": ["2024/2025"],
    "field_dictionary_path": "docs/path/to/field_dictionary.md",
    "mapping_version": "PHASE4.52_REAL_SOURCE_AUDIT_V1",
    "import_dry_run_report_path": "docs/_reports/TBD.md",
    "approval_status": "pending",
    "human_approval_note": "required before any import"
}
```

规则：

- manifest 不完整则 dry-run 直接 fail
- manifest 完整也不代表可写库，只代表可进入 staging dry-run

## 12. Phase 4.52 real source staging dry-run gate 设计

建议下一阶段新增：

```bash
make data-real-source-audit SOURCE_MANIFEST=<path>
make data-real-finished-csv-dry-run SOURCE_MANIFEST=<path> SAMPLE_CSV=<path>
make data-real-finished-csv-commit SOURCE_MANIFEST=<path> SAMPLE_CSV=<path> CONFIRM_REAL_CSV_COMMIT=1
```

Phase 4.52 只做：

- 读取本地 staging 文件
- 读取 source manifest
- license / provenance completeness check
- CSV schema detection
- row count
- finished row count
- trainable label row count
- duplicate detection
- team name normalization preview
- `match_id` generation preview
- `would_insert_matches = false`
- `would_insert_odds = false`
- `no_db_writes`

commit gate 仍 blocked。

本阶段不实现这些脚本，只定义接口和验收方向。

## 13. 下一步建议

- Phase 4.52：实现 `source manifest + real finished CSV staging dry-run gate`
- 仍不下载外部数据
- 仍不写数据库
- 用户需先提供本地 staging 数据，或单独授权某个来源的人工下载与许可确认
- 在真实写库前，先完成 license / provenance / mapping / duplicate / label-readiness / leakage 审计

## 14. 明确未执行事项

本阶段明确未执行：

- `INSERT`
- `UPDATE`
- `DELETE`
- `CREATE`
- `ALTER`
- `DROP`
- `TRUNCATE`
- `COPY`
- `\copy`
- DB writes
- external download
- `curl`
- `wget`
- `git clone`
- 外网数据源访问
- scraping / browser automation
- harvest / ingest
- `local_dom_ingestor --commit`
- `csv_bulk_loader --commit`
- `raw_match_data_local_ingest --commit`
- `npm run smelt`
- `npm run l3:stitch`
- `npm run elo:recalc`
- model training
- real prediction execution
- model artifact loading
- `npm run train`
- `npm run predict`
- `npm run predict:dry`
- `npm run predict:json`
- batch backfill
- network dry-run
- bulk harvest
- Docker volume 清理
- `git push --force`
- `git push --mirror`
- `git fetch --all`
- `git pull`
- 删除文件
