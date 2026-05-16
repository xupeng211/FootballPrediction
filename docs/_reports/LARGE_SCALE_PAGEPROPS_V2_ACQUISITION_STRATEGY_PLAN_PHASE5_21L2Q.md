# Large-Scale PageProps V2 Acquisition Strategy Plan - Phase 5.21L2Q

## 1. Executive summary

当前 8 场 `fotmob_pageprops_v2` 仍然只是 validation samples，不是训练集。

Phase 5.21L2M/N/O/P 已经证明 pageProps v2 raw storage、canonical selector、raw
completeness audit、parser boundary planning 和 leakage-safe planning 路径已经跑通。

本阶段的重点不是采集，而是规划如何从这 8 场 seeded validation samples 安全扩展到几千 /
几万场 pageProps v2 raw 数据。

本阶段严格保持 planning-only：

- 不采集
- 不触网
- 不写库
- 不实现 parser / features / training

## 2. Current validated baseline

只读确认基线：

| table                     | rows |
| ------------------------- | ---: |
| `matches`                 |   10 |
| `raw_match_data`          |   18 |
| `bookmaker_odds_history`  |    2 |
| `l3_features`             |    2 |
| `match_features_training` |    2 |
| `predictions`             |    2 |

当前 `raw_match_data` data_version 分布：

| data_version          | rows |
| --------------------- | ---: |
| `PHASE4.23`           |    1 |
| `PHASE4.43_SYNTHETIC` |    1 |
| `fotmob_html_hyd_v1`  |    8 |
| `fotmob_pageprops_v2` |    8 |

已验证状态：

- 8 个 seeded Ligue 1 matches 都已有 `fotmob_pageprops_v2`
- canonical read 对这 8 场全部选择 v2
- completeness audit 显示 seeded Ligue 1 sample 为 high coverage

限制必须明确：

- 当前 8 场只证明 pageProps v2 pipeline 在 seeded sample 上技术可行
- 它们不构成训练集
- 它们也不能外推为“所有联赛都具备同样 coverage”

## 3. Expansion tiers

### Tier 0 current seeded validation

- Purpose:
    - 保留当前 8 场 seeded Ligue 1 作为技术验证基线
- Estimated scale:
    - 8 场
- Expected risk:
    - 技术风险低，但代表性风险高
- Required preflight:
    - 无新增 live preflight；只保留现有 baseline
- Required completeness audit:
    - 已完成
- Go/no-go gate:
    - 只能作为 validation baseline，不得视为训练数据

### Tier 1 single-league single-season small batch

- Purpose:
    - 在同联赛同赛季上验证 inventory -> preflight -> write -> audit 全链路
- Estimated scale:
    - 每批 20-50 场
- Priority:
    - 先扩 `Ligue 1 / 2025/2026`
    - 先 finished slices，再把 scheduled status 作为独立 profile slice
- Expected risk:
    - 中等，主要是 inventory / version state / hash gate 风险
- Required preflight:
    - future no-write preflight，逐目标生成 `stable_pageprops_payload_v1`
      baseline
- Required completeness audit:
    - 每批写后都做 completeness audit 和 seeded baseline 对照
- Go/no-go gate:
    - 只有连续多批 preflight/write/canonical/audit 全绿后，才允许进入 Tier 2

### Tier 2 top European multi-season

- Purpose:
    - 在顶级联赛和 recent seasons 上扩大样本规模
- Estimated scale:
    - 几百到几千场，仍然按批次推进
- Priority:
    - `Ligue 1 / EPL / La Liga / Bundesliga / Serie A`
    - 优先 recent seasons，例如 `2025/2026`、`2024/2025`、`2023/2024`
- Expected risk:
    - 跨联赛、跨赛季 coverage variance
- Required preflight:
    - 仍按 league/season/status slice 做 no-write preflight
- Required completeness audit:
    - 每个 league-season 都必须产出 coverage profile
- Go/no-go gate:
    - 没有 repeated green audits，不得放大 batch

### Tier 3 second-tier / broader UEFA

- Purpose:
    - 测试更广泛 UEFA 和 second-tier leagues 的结构稳定性
- Estimated scale:
    - 按联赛分波次进入，通常每波几百场以内
- Priority:
    - `Championship / 2. Bundesliga / Ligue 2 / Segunda / Serie B`
- Expected risk:
    - coverage variance 更高，advanced modules 缺失概率更高
- Required preflight:
    - 联赛专属 preflight slice
- Required completeness audit:
    - 每个 second-tier league 单独出 profile
- Go/no-go gate:
    - 没有 league-specific completeness profile，不得进入更大范围写入

### Tier 4 low-tier / obscure leagues

- Purpose:
    - 先回答“这些联赛是否足够完整到值得 parser assumptions”
- Estimated scale:
    - 小样本 profile-only，取 profile batch 区间下限
- Expected risk:
    - 缺失 `lineup / playerStats / shotmap / momentum / stats / table` 风险最高
- Required preflight:
    - 只能先做 profile-only sample planning
- Required completeness audit:
    - 必须先完成 league-specific completeness profile
- Go/no-go gate:
    - 在 coverage 未证明前，不得进入 advanced parser/feature assumptions

## 4. Batch acquisition lifecycle

未来大规模 acquisition 应固定为以下生命周期：

1. `target inventory`
2. `existing-version audit`
3. `no-write preflight`
4. `stable_pageprops_payload_v1` baseline hash capture
5. `controlled write`
6. `post-write canonical verification`
7. `raw completeness audit`
8. `coverage profile update`
9. `parser eligibility decision`

关键要求：

- inventory 必须先确定 exact scope
- existing versions / duplicate targets 必须先审计
- write 前必须先有 stable baseline hash
- write 后必须先 canonical verify，再 completeness audit
- 没有 coverage profile，就不能进入下一个扩展 tier

## 5. Target inventory design

未来 inventory 至少应保存以下字段：

- `match_id`
- `external_id`
- `league_id`
- `season`
- `home_team`
- `away_team`
- `kickoff_time`
- `status`
- `source`
- `route`
- `data_version`
- `batch_id`
- `priority`
- `existing_versions`
- `expected_coverage_tier`
- `acquisition_state`

设计原则：

- `match_id` 必须保持稳定，作为 raw version 和未来 odds join 的主键锚点
- `external_id` 必须保留 source-native identity
- `league_id` 必须显式持久化，不能只依赖 display `league_name`
- `kickoff_time` 必须可稳定复用，不能只作为显示字段
- `existing_versions` 必须在 preflight 前就审计清楚
- `acquisition_state` 必须能表达：
    - planned
    - preflight_ready
    - preflight_blocked
    - write_authorized
    - written
    - canonical_verified
    - completeness_profiled
    - manual_review

当前只读 schema 观察到一个重要限制：

- `matches` 当前有 `league_name` 和 `match_date`
- 但没有独立 `league_id` 字段
- 因此 `Phase 5.21L2R` 必须先决定 future acquisition inventory/staging doc
  如何显式保存 source-native `league_id` 和 `kickoff_time`

## 6. Safety policy

安全策略必须固定：

- 不允许 direct bulk write
- 不允许 uncontrolled harvest
- first batch 必须小
- `profile batch` 建议 `20-50`
- `controlled write batch` 建议 `20-100`
- 更大 batch 只有在 repeated green audits 后才允许讨论
- 初始 `concurrency=1`
- 初始 `retry=0`
- `stable_pageprops_payload_v1` hash gate 是硬门禁
- 任何 hash drift 都必须阻断目标；若多目标漂移，则阻断整批
- 任何 systemic `403/captcha/forbidden` 都必须阻断整批
- 所有 writes 必须 batch 或 target-group 事务化
- 除非未来明确授权 reduced scope，否则不允许 partial write
- full body / full JSON 默认不得打印、不得保存

失败处理矩阵：

- `403 / captcha / forbidden`
    - stop whole batch
    - no retry
    - require route-health review
- `invalid hydration`
    - block target
    - no write
    - route to source-fidelity review
- `hash drift`
    - block target immediately
    - repeated drift blocks batch and requires fresh preflight baseline
- `duplicate target`
    - block before preflight/write
- `post-write mismatch`
    - stop rollout
    - run SELECT-only canonical reconciliation
    - do not proceed to next batch

## 7. Coverage profile policy

coverage profile 必须按 `league / season / status` 输出，而不是只看全局均值。

每个 tracked module 都应输出：

- `present_count`
- `missing_count`
- `coverage_percent`
- `sample_size`
- `coverage_tier`

tracked modules：

- `content`
- `content.lineup`
- `content.matchFacts`
- `content.playerStats`
- `content.shotmap`
- `content.stats`
- `content.h2h`
- `content.table`
- `content.momentum`
- `seo`
- `fallback`
- `translations`
- `header`
- `general`
- `nav`
- `ssr`
- `fetchingLeagueData`
- `hasPendingVAR`

coverage tier 分类：

- `high_coverage`
- `medium_coverage`
- `sparse_coverage`
- `unusable_for_advanced_parser`

profile 还必须附带：

- module coverage
- path coverage
- missing core modules
- suspicious payloads
- league/season/status profile summary

关键判断：

- 当前 seeded Ligue 1 sample 可以是 `high_coverage`
- 但这个结论不能默认复制到 EPL、Serie B、Ligue 2、低级别联赛或 scheduled/live statuses

## 8. Low-tier league risk policy

低级别 / 冷门联赛默认按高风险处理：

- 不能假设 `lineup` 一定存在
- 不能假设 `playerStats` 一定存在
- 不能假设 `shotmap` 一定存在
- 不能假设 `momentum` 一定存在
- 不能假设 `stats` 一定存在
- 不能假设 `table` snapshot 一定稳定可用

因此：

- parser 必须 optional-first
- feature groups 必须 coverage-aware
- 缺少 `shotmap` 的联赛，仍可能支持基础 metadata / table / h2h features
- 缺少 `table` snapshots 的联赛，可能需要直接排除 table-based features
- missing advanced modules 不应导致 raw ingestion 失败

最重要的是：

不能把当前 8 场 Ligue 1 high coverage sample 当作所有联赛都高覆盖的证据。

## 9. Source fidelity / data version policy

未来 source fidelity / version policy 必须保持：

- canonical raw version：`fotmob_pageprops_v2`
- fallback / legacy：`fotmob_html_hyd_v1`
- `PHASE4.43_SYNTHETIC` / `PHASE4.23` / unknown 默认排除
- canonical hash strategy：`stable_pageprops_payload_v1`
- v2 `raw_data` shape：`_meta + matchId + pageProps`
- source route 必须记录
- body sha 只能作为 metadata，不参与 canonical payload hash gate
- 未经明确授权，不得 rewrite 已有 rows

## 10. Odds alignment readiness

L2Q 不做 odds ingestion。

但 large-scale match inventory 现在就必须为未来 odds join 做准备：

- `match_id` 必须稳定
- `kickoff_time` 必须可靠
- `league / season / team identity` 必须可归一化
- odds raw 不应混入 `raw_match_data`
- future odds raw 应通过 `match_id + prediction_cutoff_time / odds_timestamp` 对齐

这意味着 future acquisition inventory 至少要为 odds alignment 保留：

- `match_id`
- `external_id`
- `league_id`
- `season`
- `home_team`
- `away_team`
- `kickoff_time`
- `status`
- `source`
- `route`

odds raw 仍应进入独立路线，而不是在 L2Q 阶段混进 FotMob raw planning。

## 11. Recommended next phases

推荐下一阶段：

### Phase 5.21L2R

`large-scale acquisition target inventory planning / schema-readiness audit`

要求：

- no DB write
- no network
- no raw acquisition execution
- inspect `matches` schema and source mapping
- decide how to represent future acquisition candidates
- define target inventory schema or staging doc
- still no FotMob access

### Phase 5.21L2S

`single-league small-batch pageProps v2 acquisition preflight`

要求：

- only after explicit network authorization
- no DB write
- e.g. small batch `20-50`
- collect hashes / coverage summary only

### Phase 5.22L2A

`odds raw schema / source / leakage policy planning and existing module audit`

要求：

- parallel track
- no odds access
- no DB write

## 12. Verification results

本阶段验证项：

- new planning tests:
    - `tests/unit/large_scale_pageprops_v2_acquisition_strategy_plan.test.js`
- previous planning tests:
    - `tests/unit/pageprops_v2_parser_boundary_leakage_plan.test.js`
- raw completeness tests:
    - `tests/unit/pageprops_v2_raw_completeness_audit.test.js`
- canonical read tests:
    - `tests/unit/all_seeded_pageprops_v2_canonical_read_verification.test.js`
    - `tests/unit/RawMatchDataVersionSelector.test.js`
- Makefile planning target:
    - `make data-large-scale-pageprops-v2-acquisition-strategy-plan ...`
- full test gates:
    - `npm test`
    - `npm run test:coverage`
- quality:
    - `eslint`
    - `prettier --check`
    - `git diff --check`
- safety:
    - DB row counts unchanged
    - `tests/fixtures/l1-config-*` residue absent
    - `docs/_staging_preview` absent
    - PR CI green before merge
    - main push CI green after merge

## 13. Explicit non-execution

本阶段明确未执行：

- no DB writes
- no `raw_match_data` writes
- no `bookmaker_odds_history` writes
- no network / FotMob access
- no odds access
- no raw acquisition
- no schema migration
- no `matches` writes
- no parser implementation
- no feature extraction
- no `l3_features` write
- no `match_features_training` write
- no training / prediction
- no browser / proxy
- no full raw_data print / save
- no file deletion
