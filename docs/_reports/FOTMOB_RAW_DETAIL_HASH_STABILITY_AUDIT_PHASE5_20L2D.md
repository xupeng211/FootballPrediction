# FotMob Raw Detail Hash Stability Audit - Phase 5.20L2D

## 1. Executive summary

Phase 5.20L2C 的 controlled remaining `raw_match_data` write 被正确拦下，未发生误写库。

触发点是首个目标 `4830747 / Auxerre vs Nice`：

- Phase 5.20L2B baseline `raw_data_hash`:
  `435296093b7d73ec822262c00a22903fa1d28d260a5a2b982b0bf8006e191728`
- Phase 5.20L2C live recapture `raw_data_hash`:
  `9ebf69175565788ed92e4c0f3dc599b3aedef5dfb531972d9334979050b485c8`
- write 前 `raw_data.matchId` 缺失
- transaction 未开始
- DB 未变化

Phase 5.20L2D 的落地结果已经并入主线：

- PR: `#1244`
- PR URL: `https://github.com/xupeng211/FootballPrediction/pull/1244`
- merge commit / current main HEAD:
  `0dd62a54628439121ee43b152e32bd820eb37ecc`
- main push CI:
  `success` on `2026-05-15`

本阶段没有写 DB，没有重试 controlled write，也没有触网复抓。工作内容限于：

- 审计 `FotMobRawDetailFetcher` 的 hash 稳定性
- 审计 `raw_data` canonical shape
- 统一 `matchId` normalization / fallback
- 让 preflight / write 共用同一 stable hash 策略

## 2. Incident details

- target: `4830747`
- Phase 5.20L2B baseline `body_sha256`:
  `d9f70d8ed1f7858af284280dda4b0cd4ce22f8873ae27d2082460b4db7570718`
- Phase 5.20L2B baseline `raw_data_hash`:
  `435296093b7d73ec822262c00a22903fa1d28d260a5a2b982b0bf8006e191728`
- Phase 5.20L2C live recapture `raw_data_hash`:
  `9ebf69175565788ed92e4c0f3dc599b3aedef5dfb531972d9334979050b485c8`
- Phase 5.20L2C failure:
  `raw_data.matchId missing`
- transaction:
  `not begun`

DB after incident and after Phase 5.20L2D verification remains:

- `matches=10`
- `raw_match_data=3`
- `bookmaker_odds_history=2`
- `l3_features=2`
- `match_features_training=2`
- `predictions=2`

Remaining targets still absent from `raw_match_data`:

- `4830747`
- `4830748`
- `4830750`
- `4830751`
- `4830752`
- `4830753`
- `4830754`

## 3. Root cause analysis

结论：

1. 旧 `FotMobRawDetailFetcher` 在构造 `raw_data` 后，直接对整份 `raw_data` 做
   `sha256CanonicalJson(raw_data)`。
2. 旧 hash 会把 `_meta` 一并算进去，因此以下 volatile fetch metadata 会参与 hash：
    - `_meta.fetched_at`
    - `_meta.request_url`
    - `_meta.final_url`
    - `_meta.http_status`
    - `_meta.content_type`
    - `_meta.body_byte_length`
    - `_meta.fetch_body_sha256`
3. 这意味着 stable payload 本身不变时，只要抓取时间、URL、HTTP metadata 或 body hash 变化，
   旧 `raw_data_hash` 也会 drift。
4. Phase 5.20L2B preflight 与 Phase 5.20L2C write 虽然都调用 consolidated
   `FotMobRawDetailFetcher`，但它们比较的是“含 `_meta` 的 raw_data hash”，不是稳定内容 hash。
5. `raw_data.matchId` 缺失的原因，是旧 fetcher 只在 transformed payload 顶层已经有
   `matchId` 时才保留该字段；当 parser 输出把 `matchId` 放在 `general.matchId`，或者顶层未归一化，
   write 的 canonical shape gate 会判定 `raw_data` invalid。
6. 因此 Phase 5.20L2B 旧 baseline 不是 stable baseline，不能继续作为 future controlled write
   的可信 hash gate 基线。

明确回答：

- hash drift 是由 volatile metadata 参与旧 hash 导致的：`yes`
- `raw_data.matchId` 缺失是因为旧 normalize 逻辑不统一：`yes`
- 5.20L2B 和 5.20L2C 走的是同一 fetcher，但比较的不是 stable payload hash：`yes`
- `body_sha256` / `fetched_at` / URL / HTTP metadata 参与旧 hash：`yes`
- old baseline 需要重新生成 stable baseline：`yes`

## 4. Fix

本阶段引入并统一了 `stable_raw_payload_v1`。

### stable payload

`stable_raw_payload` 只保留稳定的 match detail 内容：

- `content`
- `general`
- `header`
- `matchId`

它不包含以下 volatile fetch metadata：

- `fetched_at`
- `request_url`
- `final_url`
- `http_status`
- `content_type`
- `body_byte_length`
- `fetch_body_sha256`
- 其他 `_meta` 抓取元信息

### raw_data

`raw_data` 继续保留 `_meta`，用于入库和审计：

- `_meta.request_url`
- `_meta.final_url`
- `_meta.http_status`
- `_meta.content_type`
- `_meta.fetch_body_sha256`
- `_meta.fetched_at`
- `_meta.hash_strategy`
- `_meta.match_id_source`
- `_meta.metadata_hash_excluded_fields`

但 `_meta` 不参与 `data_hash` / `raw_data_hash`。

### new hash strategy

- `data_hash = SHA-256(canonical_json(stable_raw_payload))`
- `raw_data_hash = SHA-256(canonical_json(stable_raw_payload))`
- `stable_raw_payload_hash = SHA-256(canonical_json(stable_raw_payload))`
- `raw_data_with_meta_hash` 仅保留为 debug / audit，不参与 hash gate

### matchId normalization

统一规则：

1. 优先 `payload.matchId`
2. 其次 `payload.general.matchId`
3. 若两者缺失，但 `externalId` 数字合法且 payload / URL / team markers 一致，则 fallback 为
   `input_external_id_fallback`
4. fallback 会记录：
   `raw_data._meta.match_id_source = "input_external_id_fallback"`
5. 若 fallback 条件也不成立，则 payload invalid，write blocked

### preflight / write guard

- preflight 输出 `hash_strategy = stable_raw_payload_v1`
- write hash gate 只比较 stable hash
- write 在 baseline `hash_strategy` 缺失或不匹配时直接 blocked
- write 不会把旧 5.20L2B baseline 当作默认可写 baseline
- old baselines 需要在下一阶段按 stable strategy refresh

## 5. Validation

已验证：

- `tests/unit/FotMobRawDetailFetcher.test.js`
    - stable hash excludes `fetched_at`
    - stable hash excludes `collected_at`
    - stable hash excludes `body_sha256`
    - stable hash excludes request / final URL
    - stable hash excludes HTTP metadata
    - metadata-only drift does not change `raw_data_hash`
    - content drift changes stable hash
    - `raw_data` 保留 `_meta`
    - `matchId` fallback works
- `tests/unit/l2_remaining_raw_match_data_acquisition_preflight.test.js`
    - preflight 输出 `hash_strategy=stable_raw_payload_v1`
    - metadata-only drift does not change per-target `raw_data_hash`
    - fallback 后顶层 `raw_data.matchId` 可用
- `tests/unit/l2_remaining_raw_match_data_write.test.js`
    - write rejects missing / mismatched baseline strategy
    - write hash gate uses stable hash
    - metadata-only drift does not block
    - stable payload drift still blocks
- `tests/unit/fotmob_raw_detail_hash_stability_audit.test.js`
    - audit proves stable hash ignores metadata drift
    - audit proves `raw_data_with_meta_hash` changes when `_meta` changes

本次复核时已再次确认：

- `node --test tests/unit/FotMobRawDetailFetcher.test.js`: pass
- `node --test tests/unit/l2_remaining_raw_match_data_acquisition_preflight.test.js`: pass
- `node --test tests/unit/l2_remaining_raw_match_data_write.test.js`: pass
- `node --test tests/unit/fotmob_raw_detail_hash_stability_audit.test.js`: pass
- `npm test`: pass
- `npm run test:coverage`: pending at time of report refresh; prior Phase 5.20L2D main CI was green
- `eslint`: pass
- `prettier --check`: pass
- `git diff --check`: pass

Safety re-check:

- DB row counts unchanged:
    - `matches=10`
    - `raw_match_data=3`
    - `bookmaker_odds_history=2`
    - `l3_features=2`
    - `match_features_training=2`
    - `predictions=2`
- remaining 7 rows still absent from `raw_match_data`
- no `tests/fixtures/l1-config-*` residue
- no `docs/_staging_preview` directory

## 6. Next phase recommendation

不要直接重试 Phase 5.20L2C。

下一阶段应进入：

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
