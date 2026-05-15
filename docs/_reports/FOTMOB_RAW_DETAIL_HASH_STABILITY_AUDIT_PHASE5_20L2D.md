# FotMob Raw Detail Hash Stability Audit - Phase 5.20L2D

## 1. Executive summary

Phase 5.20L2C 的 controlled remaining `raw_match_data` write 被正确拦下。

拦截原因出现在首个目标 `4830747 / Auxerre vs Nice`：

- write 前 live recapture `raw_data_hash` 与 Phase 5.20L2B baseline 不一致
- write 前 `raw_data.matchId` 缺失
- transaction 未开始
- DB 未变化

本阶段不写 DB，不重试 controlled write。本阶段只审计：

- `FotMobRawDetailFetcher` hash stability
- `raw_data` shape stability
- `matchId` normalization / fallback
- remaining preflight / write 是否共用同一 stable hash 逻辑

## 2. Incident details

- target: `4830747`
- Phase 5.20L2B baseline `raw_data_hash`:
  `435296093b7d73ec822262c00a22903fa1d28d260a5a2b982b0bf8006e191728`
- Phase 5.20L2C live recapture `raw_data_hash`:
  `9ebf69175565788ed92e4c0f3dc599b3aedef5dfb531972d9334979050b485c8`
- Phase 5.20L2C failure:
  `raw_data.matchId missing`
- transaction:
  `not begun`
- DB after incident:
  `matches=10`
  `raw_match_data=3`
  `bookmaker_odds_history=2`
  `l3_features=2`
  `match_features_training=2`
  `predictions=2`

## 3. Root cause analysis

结论：

1. 旧 `FotMobRawDetailFetcher` 把 volatile fetch metadata 放进 `_meta` 后，直接对整份
   `raw_data` 做 `sha256CanonicalJson(raw_data)`。
2. 参与旧 hash 的 volatile 字段包括：
    - `_meta.fetched_at`
    - `_meta.request_url`
    - `_meta.final_url`
    - `_meta.http_status`
    - `_meta.content_type`
    - `_meta.body_byte_length`
    - `_meta.fetch_body_sha256`
3. 因为旧 hash 直接覆盖整份 `raw_data`，即便 stable payload 不变，只要 fetch metadata 变化，
   `raw_data_hash` 就会 drift。
4. Phase 5.20L2B 和 Phase 5.20L2C 虽然都走了 consolidated `FotMobRawDetailFetcher`，
   但它们比较的是旧的“含 `_meta` 的 raw_data hash”，不是稳定 payload hash。
5. `raw_data.matchId` 缺失的直接原因是旧 fetcher 只在 transformed payload 顶层已经带
   `matchId` 时才保留该字段；当 parser 输出把 `matchId` 放在 `general.matchId` 或压根缺失顶层
   `matchId` 时，remaining write 的 shape gate 会把它判为 invalid。
6. remaining preflight 和 remaining write 的 valid gate 不完全一致：
    - preflight 更关注 `hydration_parse_ok + looks_like_valid_match_detail`
    - write 额外强制 `raw_data` 顶层必须有 `matchId`
7. 因此旧 baseline 不是 stable baseline。它不能继续作为 future controlled write 的可信基线。

## 4. Fix

本阶段实现了 `stable_raw_payload_v1`：

- `stable_raw_payload`
    - 只包含稳定的 match detail 内容
    - 结构固定为：`content` / `general` / `header` / `matchId`
    - 不包含 fetch timestamp、URL、HTTP metadata、body SHA 等 volatile metadata
- `raw_data`
    - 继续保留 `_meta`
    - `_meta` 可记录 request/final URL、HTTP metadata、body SHA、fetched_at、parser、`match_id_source`
    - 但 `_meta` 不参与 `data_hash`
- `data_hash` / `raw_data_hash`
    - 统一改为 `SHA-256(canonical_json(stable_raw_payload))`
- `raw_data_with_meta_hash`
    - 仅保留为 debug / audit 信息
    - 不参与 hash gate，不参与 future DB baseline

`matchId` normalization / fallback：

- 优先 `payload.matchId`
- 其次 `payload.general.matchId`
- 若两者缺失，但 `externalId` 数字合法且 payload/URL/team markers 一致，则 fallback 为
  `input_external_id_fallback`
- fallback 时保留：
  `raw_data._meta.match_id_source = "input_external_id_fallback"`
- 若连 fallback 条件也不满足，则 payload invalid

remaining preflight / write 修复：

- preflight 输出 `hash_strategy = stable_raw_payload_v1`
- write hash gate 只比较 stable hash
- write 在 baseline `hash_strategy` 缺失或不匹配时直接 blocked
- old baseline 不再被默认为可写 baseline

## 5. Validation

本阶段验证目标：

- `tests/unit/FotMobRawDetailFetcher.test.js`
    - stable hash excludes volatile metadata
    - metadata-only drift does not change `raw_data_hash`
    - content drift changes stable hash
    - `matchId` fallback works
    - `raw_data` 保留 `_meta`
- `tests/unit/l2_remaining_raw_match_data_acquisition_preflight.test.js`
    - preflight 输出 `hash_strategy=stable_raw_payload_v1`
    - metadata-only drift does not change per-target `raw_data_hash`
    - `matchId` fallback reaches top-level `raw_data.matchId`
- `tests/unit/l2_remaining_raw_match_data_write.test.js`
    - write rejects missing / mismatched baseline strategy
    - write uses stable hash
    - metadata-only drift does not block
    - stable payload drift still blocks
- `tests/unit/fotmob_raw_detail_hash_stability_audit.test.js`
    - audit proves stable hash ignores metadata drift
    - audit proves payload drift changes stable hash
- quality:
    - `npm test`
    - `npm run test:coverage`
    - `eslint`
    - `prettier`
    - `git diff --check`
- DB unchanged:
    - `matches=10`
    - `raw_match_data=3`
    - `bookmaker_odds_history=2`
    - `l3_features=2`
    - `match_features_training=2`
    - `predictions=2`

## 6. Next phase recommendation

不要直接重试 Phase 5.20L2C。

下一阶段建议进入：

`Phase 5.20L2E: remaining raw_match_data stable-hash preflight refresh`

要求：

- 使用 `stable_raw_payload_v1`
- 对剩余 7 场重新执行 preflight
- 生成新的 stable baseline hashes
- no DB write
- no parser/features/training/prediction

之后再进入：

`Phase 5.20L2F: controlled remaining raw_match_data write using stable baselines`

## 7. Explicit non-execution

本阶段明确未执行：

- no DB writes
- no raw_match_data writes
- no matches writes
- no parser/features
- no harvest/ingest/backfill
- no training/prediction
- no browser/proxy
- no full body save/print
- no file deletion
