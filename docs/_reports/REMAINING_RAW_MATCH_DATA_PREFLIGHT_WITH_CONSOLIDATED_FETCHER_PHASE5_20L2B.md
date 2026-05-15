# Remaining Raw Match Data Preflight With Consolidated Fetcher - Phase 5.20L2B

## 1. Executive summary

Phase 5.20L2A 已完成 `FotMobRawDetailFetcher` 收敛。本阶段目标是在
post-merge `main` 健康且 CI 绿灯后，使用 consolidated fetcher 对剩余 7 场
seeded matches 重新执行一次真实 preflight。

本阶段只允许 live preflight：

- no DB writes
- no raw_match_data writes
- no parser/features
- no training/prediction
- no browser/proxy
- no full body save/print

## 2. Baseline

起始 baseline 约束：

- `matches=10`
- `raw_match_data=3`
- `bookmaker_odds_history=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

seeded raw coverage 目标：

- has_raw target: `53_20252026_4830746 / 4830746 / Angers vs Strasbourg`
- missing_raw target count: `7`
- missing raw external_ids:
  `4830747, 4830748, 4830750, 4830751, 4830752, 4830753, 4830754`

## 3. Consolidated fetcher confirmation

确认项：

- fetcher file:
  `src/infrastructure/services/FotMobRawDetailFetcher.js`
- remaining preflight entry:
  `scripts/ops/l2_remaining_raw_match_data_acquisition_preflight.js`
- remaining preflight 的 `recaptureTarget` 已委托
  `fetchFotMobRawDetail(...)`
- fetcher 按调用参数接收 `externalId`，不硬编码 `4830746`
- fetcher 只做 `html_hydration` 获取、hydration parse、canonical raw_data hash
- fetcher 不写 DB
- fetcher 不保存或打印完整 body
- fetcher 不启动 browser/proxy
- fetcher 禁止 retry > 0

## 4. Actual preflight result

post-merge live preflight pending at report creation time.

本节将在 `main` merge 完成且 `main` push CI success 后，执行：

- route=`html_hydration`
- concurrency=`1`
- retry=`0`
- network authorization=`yes`
- browser/proxy=`no`
- DB/raw_match_data write=`no`

待填写项：

- attempted_target_count
- valid_payload_count
- failed_target_count
- would_insert_count
- would_update_count
- would_skip_count
- per-target request_url / final_url / http_status
- per-target body_sha256 / raw_data_hash
- DB unchanged confirmation

## 5. Next phase

若 7/7 targets 全部 valid 且 `would_insert=7`，下一阶段建议进入：

`Phase 5.20L2C controlled remaining raw_match_data write`

否则停止在 preflight，等待用户决定。

## 6. Explicit non-execution

本阶段明确不执行：

- no DB writes
- no raw_match_data writes
- no matches writes
- no bookmaker_odds_history writes
- no l3_features writes
- no match_features_training writes
- no predictions writes
- no parser/features
- no harvest/ingest/backfill
- no training/prediction
- no browser/proxy
- no full body save/print
- no file deletion
