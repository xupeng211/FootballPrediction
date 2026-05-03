# Phase 4.23 - raw_match_data Single Insert

日期: `2026-05-03`

## 1. 当前 HEAD

- 分支: `main`
- HEAD: `a559e9492640c042c51371eab9594e19f09acace`
- 提交: `a559e94 feat(data): add raw match data local ingest gate`

## 2. 备份

- 备份文件: `data/backups/phase423_pre_raw_match_data_insert_20260503_153326.dump`
- 文件大小: `68K`
- 备份命令: `pg_dump --format=custom`
- 备份结果: 成功，文件非空

## 3. 写入前行数

```text
matches                 1
bookmaker_odds_history  2
raw_match_data          0
l3_features             0
match_features_training 0
predictions             0
```

目标 match:

- `match_id`: `140_20252026_4837496`
- `external_id`: `4837496`
- `league_name`: `Segunda División`
- `season`: `2025/2026`
- `home_team`: `Cultural Leonesa`
- `away_team`: `Burgos CF`
- `match_date`: `2026-05-24 17:00:00+00`
- `status`: `scheduled`
- `pipeline_status`: `pending`

写入前目标 raw rows:

- `target_raw_rows`: `0`

## 4. Fixture

- Fixture path: `tests/fixtures/l3/raw_match_data_phase419_sample.json`
- `match_id`: `140_20252026_4837496`
- `external_id`: `4837496`
- `raw_data` top-level keys:
    - `_meta`
    - `content`
    - `general`
    - `header`
    - `matchId`

## 5. Data Hash

- `data_hash`: `b13b7c2bf4f9b825e337124f51431d8594ef3a9af03e76dced88ee132addece1`
- 算法: 稳定 JSON 字符串 + `sha256`
- 与 `data-raw-dry-run` 输出一致

## 6. INSERT 结果

人工授权范围:

- 只允许写入 `raw_match_data`
- 只允许写入 `match_id = 140_20252026_4837496`
- 不允许写入任何其他业务表

结果:

- `INSERT 0 1`
- `COMMIT`
- returned `id`: `1`
- returned `match_id`: `140_20252026_4837496`
- returned `external_id`: `4837496`
- returned `data_version`: `PHASE4.23`
- returned `data_hash`: `b13b7c2bf4f9b825e337124f51431d8594ef3a9af03e76dced88ee132addece1`
- returned `collected_at`: `2026-05-03 07:33:43.721507+00`

## 7. 写入后 raw_match_data 验证

目标行数:

- `target_raw_rows`: `1`

关键字段:

```text
has_match_id  true
has_general   true
has_header    true
has_content   true
```

写入后 top-level keys:

- `_meta`
- `content`
- `general`
- `header`
- `matchId`

## 8. 写入后总体行数

```text
matches                 1
bookmaker_odds_history  2
raw_match_data          1
l3_features             0
match_features_training 0
predictions             0
```

结论:

- 只有 `raw_match_data` 从 `0` 变为 `1`
- 其他主要表行数未变

## 9. data-raw-dry-run 写入后识别结果

写入后重新运行:

```bash
make data-raw-dry-run SAMPLE_RAW=tests/fixtures/l3/raw_match_data_phase419_sample.json MATCH_ID=140_20252026_4837496
```

结果摘要:

- `mode`: `dry-run`
- `match_found`: `true`
- `raw_match_data_exists`: `true`
- `raw_match_data_rows`: `1`
- `odds_history_rows`: `2`
- `would_insert_raw_match_data`: `false`
- `no_db_writes`: present

## 10. data-l3-dry-run 仍然只读结果

写入后运行:

```bash
make data-l3-dry-run SAMPLE_RAW=tests/fixtures/l3/raw_match_data_phase419_sample.json MATCH_ID=140_20252026_4837496
```

结果摘要:

- `match_found`: `true`
- `odds_history_rows`: `2`
- `would_write_l3_features`: `false`
- `would_update_matches`: `false`
- `would_trigger_elo`: `false`
- `no_db_writes`: present
- `no_l3_write`: present
- `no_elo`: present
- `no_external_network`: present

未执行:

- `npm run smelt`
- `npm run l3:stitch`
- ELO recalculation

## 11. 风险与下一步建议

风险:

- 当前仅写入 1 条本地脱敏 fixture raw 数据。
- 尚未执行真实 L3 写入。
- 尚未验证基于已入库 raw_match_data 的 L3 小范围写入。

下一步建议:

- Phase 4.24: 提交 Phase 4.23 报告
- 或设计 `l3_features` 小范围写入 runbook

## 12. 明确未执行事项

本阶段未执行:

- `UPDATE`
- `DELETE`
- `CREATE`
- `ALTER`
- `DROP`
- `TRUNCATE`
- `INSERT` 到除 `raw_match_data` 外的任何表
- raw_match_data 重复写入
- `npm run smelt`
- `npm run l3:stitch`
- ELO recalculation
- L3 feature computation write
- model training
- prediction write
- `local_dom_ingestor --commit`
- `csv_bulk_loader --commit`
- 外网访问
- 真实 harvest / scrape / ingest
- batch backfill
- network dry-run
- bulk harvest
- Docker volume 清理
- `git push`
- `git pull`
- `git fetch --all`
- commit
