# Controlled Remaining Raw Match Data Write - Phase 5.20L2C

## 1. Executive summary

本阶段执行 controlled remaining `raw_match_data` write，目标范围固定为剩余 7 场
seeded Ligue 1 matches：

- `4830747`
- `4830748`
- `4830750`
- `4830751`
- `4830752`
- `4830753`
- `4830754`

本阶段实现并执行的链路要求：

- 使用 consolidated `FotMobRawDetailFetcher`
- 使用 Phase 5.20L2B `raw_data_hash` baseline
- 写入前逐场 recapture exact payload
- 逐场比较 `raw_data_hash`
- 只写 `raw_match_data`
- 不写其他表

## 2. Baseline before write

执行前 baseline 约束：

- `matches=10`
- `raw_match_data=3`
- `bookmaker_odds_history=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

seeded raw coverage 约束：

- existing raw target: `53_20252026_4830746 / 4830746 / Angers vs Strasbourg`
- remaining 7 raw rows absent before execution

## 3. Baseline hashes

Phase 5.20L2B baseline `raw_data_hash`:

- `4830747` → `435296093b7d73ec822262c00a22903fa1d28d260a5a2b982b0bf8006e191728`
- `4830748` → `e98b0adb557d54ba0ada53ff836a5f6eea2629a0ed06389b78f23d83fbe617e5`
- `4830750` → `5c02a11384459581821026aa2c85677e05877f219e158e5f733aef2ddb484880`
- `4830751` → `b391b896c3260446b7185d81b31949ac47ad50cf956f733c87920f36579aed0f`
- `4830752` → `dfe719cae63e09710b04aba411bf74b9662c554aff284a1f414fa255ee5cd93f`
- `4830753` → `6b4438453fa7d0ceb99c80fb736d3cb7dcc51d5593b4ca48bb1ba682fe78fe4f`
- `4830754` → `c843897451773c8317111a4c010da59223f1bb98cb7ce12253eafa4f57f550f7`

## 4. Pre-write recapture and hash gate

post-merge `main` healthy 且 `main` push CI success 后，真实执行时填写：

- selected route per target
- request URL / final URL per target
- body SHA-256 per target
- `raw_data_hash` per target
- baseline hash per target
- hash matched / drifted

本阶段 gate：

- route=`html_hydration`
- concurrency=`1`
- retry=`0`
- no browser/proxy
- no full body print/save
- any hash drift => stop, no DB write

## 5. Transaction execution

真实执行后记录：

- transaction began
- inserted_count
- updated_count
- skipped_count
- committed / rolled_back

本阶段只允许：

- one transaction
- `INSERT INTO raw_match_data`
- rows=`7`

## 6. Post-write verification

真实执行后记录：

- `raw_match_data=10`
- `matches=10`
- protected tables unchanged
- inserted row metadata:
    - `id`
    - `match_id`
    - `external_id`
    - `collected_at`
    - `data_version`
    - `data_hash`
- raw_data key checks:
    - `_meta`
    - `content`
    - `general`
    - `header`
    - `matchId`

不打印完整 `raw_data`。

## 7. Next phase

推荐进入：

`Phase 5.21L2 raw_match_data inventory and parser-deferred training design`

要求：

- 只读盘点 `raw_match_data=10`
- 不触网
- 不写 features
- 不训练/预测
- 先设计训练目标、标签、时间切分、数据泄漏策略
- parser 继续 deferred，直到训练数据设计明确

## 8. Explicit non-execution

本阶段明确不执行：

- no matches writes
- no bookmaker_odds_history writes
- no l3_features writes
- no match_features_training writes
- no predictions writes
- no parser/features
- no harvest/backfill
- no training/prediction
- no browser/proxy
- no full body save/print
- no file deletion
