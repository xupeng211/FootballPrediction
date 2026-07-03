# DATA-L1A: FotMob Pre-match Data Boundary & Stability Audit

- lifecycle: phase-artifact
- scope: docs-only, read-only FotMob data boundary and stability audit
- branch: `docs/data-l1a-fotmob-boundary-audit`
- line-limit note: 本报告超过 120 行，因为任务要求固定 12 个章节、文件清单、字段分类和泄露风险表；未复制完整历史 manifest/report 清单。

## 1. 背景

TECHDEBT-L3A ~ L3H 已完成，`#1693` 主线重启决策审计已合并。当前进入 L3 观察期，不继续加治理强度。现在回到主线开发，第一步选择保数据，优先审计 FotMob。

本报告不是 scraper 改造，不是 collector 改造，不是 parser 改造，不是 DB / migration 改造，不是 training。本报告没有运行任何采集，只做仓库文件只读审计。

## 2. 当前基线

| 项目 | 结果 |
| --- | --- |
| 当前 `origin/main` SHA | `a1e1ecfc238b06b6014e803c961aa3ace191b704` |
| 最新 main CI 状态 | `Production Gate` 最新 run 为 `completed/success`，run id `28670822196`，时间 `2026-07-03T15:47:57Z` |
| 本次分支名 | `docs/data-l1a-fotmob-boundary-audit` |
| 本次改动范围 | 只新增本报告：`docs/_reports/data_l1a_fotmob_prematch_boundary_audit.md` |
| 本次实际只读审计范围 | `docs/**`、`scripts/**`、`src/**`、`tests/**`、`configs/**`、`database/migrations/**` 中 FotMob / raw / parser / odds / xG / leakage 线索 |
| 未验证事项 | 审计阶段没有主动运行 Docker、DB、migration、scraper、collector、tests、training、pipeline；没有访问 FotMob 网络。提交时仓库 Git hook 自动运行 Gatekeeper，进入 dev 容器执行 lint、冷启动 DB blueprint 和烟雾测试，这属于 commit hook 自动门禁，不是本报告的审计方法。 |

## 3. FotMob 相关文件清单

`git ls-files` 只读发现 FotMob 命中文件规模较大：`docs=406`、`scripts=152`、`src=19`、`tests=140`。为避免新报告变成大型索引，本节列关键文件和文件族，不逐条复制全部历史 phase artifact。

### docs

| 路径 | 类型 | 只读观察到的用途 | 是否可能影响数据链路 | 风险级别 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `docs/data/FOTMOB_CURRENT_STATE.md` | current-state | 当前 FotMob 状态、禁区、legacy ADG 状态和 retained raw 分流说明 | 是，作为状态源 | medium | 明确 live fetch / DB write / raw write 需授权 |
| `docs/data/FOTMOB_RETAINED_RAW_STAGE_STATUS.md` | current-state | 记录 `raw_match_data`、`fotmob_live_v1`、4 条 retained raw 审计结果 | 是，说明 raw storage 已有基础 | medium | 不证明 parser、feature、training |
| `docs/data/FOTMOB_RAW_PAYLOAD_STORAGE_POLICY.md` | governance | 规定 raw payload 文件、manifest、sha、captured_at、禁止提交 body | 是，定义 raw 保留策略 | medium | 强调 raw storage 不等于 DB write 授权 |
| `docs/data/FOTMOB_RAW_PARSER_CONTRACT.md` | current-state | `fotmob_live_v1` parser contract，列出 `general/header/content/stats/lineup/events/shotmap/playerStats` | 是，影响 parser 边界 | high | 合同不等于赛前字段合同 |
| `docs/_reports/PAGEPROPS_V2_PARSER_BOUNDARY_LEAKAGE_PLAN_PHASE5_21L2P.md` | phase report | 已把 pageProps v2 模块分成 metadata、conditional、live/post-match 等 | 是，直接是泄露边界线索 | medium | 本次 DATA-L1A 的重要依据 |
| `docs/_reports/PAGEPROPS_V2_RAW_COMPLETENESS_AUDIT_PHASE5_21L2O.md` | phase report | 8 条 seeded v2 rows 的本地 completeness audit | 是，说明 v2 结构丰富但不是训练集 | medium | SELECT-only 结论，不能泛化到低级别联赛 |
| `docs/_reports/RAW_MATCH_DATA_COMPLETENESS_SOURCE_FIDELITY_AUDIT_PHASE5_21L2A.md` | phase report | 说明 `raw_match_data` mixed provenance、`fotmob_html_hyd_v1` 是 transformed payload | 是，影响 source fidelity 判断 | medium | 不能把 transformed payload 当完整原始源 |
| `docs/_reports/training_dataset_leakage_dry_run_20260619.md` | phase report | 明确 raw FotMob 的 xG、shots、possession 等是赛后泄露风险 | 是，影响训练边界 | medium | 只读 dry-run，不是训练 |
| `docs/_reports/formal_training_dataset_design_dry_run_20260619.md` | phase report | 要求 `prediction_cutoff_time`、`feature_observed_at`、chronological split | 是，影响 future training | medium | 当前 formal feature-chain rows 为 0 |
| `docs/_manifests/fotmob_*` / `docs/_reports/FOTMOB_*` | historical artifacts | 记录 ADG、preflight、authorization、probe、route、identity、raw write 历史 | 间接影响 | low/medium | 有历史经验，不应现在删除 |

### scripts

| 路径 | 类型 | 只读观察到的用途 | 是否可能影响数据链路 | 风险级别 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `scripts/ops/fotmob_*` | ops scripts family | 大量 no-write / preflight / controlled write / probe / report 脚本 | 是 | high | 本次只读；未来执行或修改必须单独授权 |
| `scripts/ops/n3_live_fotmob_raw_retain.js` | ops script | 文件名显示 live retained raw 相关 | 是 | high | 未执行；live/network/raw 风险区 |
| `scripts/ops/single_live_fotmob_raw_ingest_smoke.js` | ops script | single live ingest smoke 入口线索 | 是 | high | 未执行；live/ingest 风险区 |
| `scripts/maintenance/fotmob_historical_backfill.py` | maintenance | 历史 backfill 入口线索 | 是 | high | 本次不运行、不修改 |
| `scripts/ops/odds_harvest_pipeline.js` / `.shared.js` | odds runtime | OddsPortal browser/network/DB/L3 风险线索；shared 可提取 open/current snapshots | 是，影响 odds timing | high | odds 不是 FotMob，但会影响赛前预测泄露边界 |
| `scripts/model_training/train_baseline_v1.py` | training | baseline 默认 pre-match，postmatch diagnostics 需显式 flag；同时含 open/current/close odds 字段 | 是，影响 training | high | 本次不运行；缺 cutoff policy 时不能直接信任 odds |

### src

| 路径 | 类型 | 只读观察到的用途 | 是否可能影响数据链路 | 风险级别 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `src/infrastructure/services/FotMobRawDetailFetcher.js` | runtime service | html_hydration fetcher，构建 stable raw payload，阻止 body print/save、retry、browser/proxy | 是 | high | 未来 scraper/raw acquisition 核心风险区 |
| `src/infrastructure/services/FotMobDetailRouteSelector.js` | runtime service | route selector，计划/执行 route、block signal、fallback route | 是 | high | 可参考稳定性，但本次未执行 |
| `src/infrastructure/network/FotMobApiClient.js` | runtime client | `matchDetails` API、proxy agent、browser bootstrap cookie/session、jitter | 是 | high | 含 browser/proxy/anti-bot 能力，需授权 |
| `src/infrastructure/harvesters/strategies/FotMobStrategy.js` | harvester strategy | API-first/browser fallback/NextData/DOM fallback 数据提取 | 是 | high | scraper/collector 相关，禁改禁跑 |
| `src/parsers/fotmob/FotMobRawParser.js` | parser | 纯函数解析 `fotmob_live_v1` 到 match/team/stats/lineup/events/shotmap/playerStats | 是 | high | 没有字段级 timing label |
| `src/parsers/fotmob/NextDataParser.js` | parser/helper | 从 `__NEXT_DATA__` / HTML 提取并转成 API-like payload | 是 | medium/high | `transformToApiFormat` 会构造较窄 payload |
| `src/parsers/fotmob/XGExtractor.js` / `MatchStatsParser.js` | parser | 提取 xG、possession、stats | 是 | high | 赛前模型必须默认禁用 current-match stats |
| `src/feature_engine/smelter/components/FotMobSchemaGuard.js` | guard/helper | key shape diff guard | 是 | medium | 稳定性线索，不是 timing guard |
| `src/infrastructure/services/RawMatchDataVersionSelector.js` | selector | 按 data_version 选择 canonical raw | 是 | high | 混合 provenance 下很关键 |

### tests

| 路径 | 类型 | 只读观察到的用途 | 是否可能影响数据链路 | 风险级别 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `tests/unit/FotMobRawDetailFetcher.test.js` | unit tests | fake fetch、阻止 file/network/browser/proxy/import 的 safety tests | 间接影响 | medium | 只读参考，未运行 |
| `tests/unit/FotMobApiClient.test.js` | unit tests | browser bootstrap cookie/session 行为测试 | 间接影响 | medium/high | 说明 API client 有 browser bootstrap 能力 |
| `tests/unit/fotmob_raw_parser.test.js` | unit tests | parser 最小 payload、stats/lineup/events/shotmap/playerStats 解析 | 是 | medium | 样例含 finished/score/xG，提示泄露风险 |
| `tests/unit/XGExtractor.test.js` | unit tests | xG / possession extraction 行为 | 是 | medium | 验证解析，不证明赛前可用 |
| `tests/unit/pageprops_v2_parser_boundary_leakage_plan.test.js` | unit tests | 验证 leakage plan 中 shotmap/live/post-match 等分类 | 间接影响 | medium | 只读参考 |
| `tests/Z_LEGACY_ARCHIVE_PRE_V4.46.8/**fotmob**` | legacy tests/fixtures | 旧 mock、Cloudflare/fixture 线索 | unknown | unknown | 不应因旧就删除 |

### 其他

| 路径 | 类型 | 只读观察到的用途 | 是否可能影响数据链路 | 风险级别 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `configs/data/fotmob_n3_raw_retain_candidates.json` | config/data | raw retain candidate 配置线索 | 是 | medium | 本次未修改 |
| `database/migrations/V12.6__allow_numeric_fotmob_ids_in_raw_match_data.sql` | migration | raw_match_data FotMob id 相关 schema 线索 | 是 | high | DB/migration 禁改禁跑 |
| `database/migrations/V26.5__create_fotmob_raw_match_payloads.sql` | migration | FotMob raw payload storage schema 线索 | 是 | high | DB/migration 禁改禁跑 |
| `docs/_examples/fotmob_known_match_page_user_seeds.example.json` / `docs/_fixtures/fotmob_*` | example/fixture | seed / dry-run target 线索 | 间接影响 | low/medium | 不代表 live source truth |

## 4. 当前 FotMob 数据链路初步图

本次只从文件推断，未运行任何链路：

```text
FotMob source
  ↓ unknown: live source shape changes over time; legacy API endpoint 曾有 404/403 线索
HTML hydration / __NEXT_DATA__ / matchDetails API
  ↓
NextDataParser / FotMobRawDetailFetcher
  ↓
stable raw payload: content + general + header + matchId + _meta
  ↓
raw retention
  - gitignored local raw files policy: data/raw/fotmob/...
  - DB rows: raw_match_data with data_version variants
  - pageProps v2 rows: raw_data includes _meta, matchId, pageProps
  ↓
RawMatchDataVersionSelector / parser contracts
  ↓
FotMobRawParser / legacy thin parsers
  ↓
future feature engineering
  ↓
future model / backtest
```

unknown: 当前哪条链路是生产唯一入口、本地 DB 真实最新行数、本次分支 PR CI 内具体 classifier step summary。以上都需要后续只读或人工复核；本报告没有连接 DB 或 staging server。

## 5. 赛前 / 赛后字段边界初步判断

| 字段或字段类别 | 初步分类 | 判断 |
| --- | --- | --- |
| fixture / external_id / match_id | `metadata_only` | 可用于 join、dedupe、version selection，不应直接当预测特征 |
| league / season / round | `safe_prematch_candidate` + `metadata_only` | 通常赛前存在，但仍要确认来源时间 |
| kickoff time / matchTimeUTC | `safe_prematch_candidate` + `metadata_only` | 是 cutoff 计算基础，不是强预测特征 |
| team names / home-away | `safe_prematch_candidate` + `metadata_only` | 可用于身份和主客场；队名 join 有 identity risk |
| venue / referee | `unknown_timing` | formal training 设计中列为可选直接字段，但当前样本缺失或未确认来源时间 |
| lineup / squad / formation / coach | `unknown_timing` | 只有 `lineup_timestamp <= prediction_cutoff_time` 才可能用于 late horizon；T-24H 默认不安全 |
| injury / suspension / unavailable | `unknown_timing` | 可能赛前可用，但需要字段来源、更新时间、是否赛后修订证明 |
| team form | `unknown_timing` | 只可由 cutoff 前历史比赛派生；FotMob 当前 payload 快照时间未证明 |
| league table | `unknown_timing` | 只有 `table_snapshot_at <= prediction_cutoff_time` 才可能安全 |
| head-to-head | `unknown_timing` | 必须过滤未来/当前比赛，并确认 snapshot 时间 |
| odds | `unknown_timing` | 初盘可能 safe；current/close/赛后记录必须按 `odds_timestamp <= prediction_cutoff_time` 判定 |
| xG / expected goals | `unsafe_postmatch_candidate` | `XGExtractor`、stats、shotmap 都是 current-match 结果派生，赛前模型默认禁用 |
| shots / shots on target / possession / passes / duels | `unsafe_postmatch_candidate` | match stats，通常比赛中或赛后才知道 |
| player stats / match rating / post-match rating | `unsafe_postmatch_candidate` | 当前比赛表现回放，直接泄露 |
| score / result / status finished / events / cards / substitutions | `unsafe_postmatch_candidate` | 直接或间接包含标签、比赛过程、结果 |
| `_meta`、hash、request/final URL、body size | `debug_or_raw_only` | 只用于审计、hash gate、source fidelity，不进模型 |
| full raw body / pageProps / raw_data | `debug_or_raw_only` | 用于 replay/audit；提 feature 前必须先做字段合同 |

## 6. 潜在数据泄露风险

| 风险描述 | 涉及文件或线索 | 为什么危险 | 建议处理方式 | 是否需要额外授权 |
| --- | --- | --- | --- | --- |
| 赛后技术统计进入赛前模型 | `src/parsers/fotmob/XGExtractor.js`、`MatchStatsParser.js`、`FotMobRawParser.js`、`docs/_reports/training_dataset_leakage_dry_run_20260619.md` | xG、shots、possession、shotmap 是当前比赛产生的数据 | DATA-L1B 建字段合同；feature 层默认拒绝 unsafe/unknown | 是，若改 parser/feature/training |
| parser 输出无字段级 timing label | `docs/data/FOTMOB_RAW_PARSER_CONTRACT.md`、`src/parsers/fotmob/FotMobRawParser.js` | parser 能输出 stats/events/playerStats，但没有说明每个字段赛前是否可用 | 字段合同中增加 timing category 和 cutoff 规则 | 是，若改 runtime contract |
| raw capture time 不等于 feature observed time | `FotMobRawDetailFetcher.js` 的 `_meta.fetched_at`、L2P cutoff policy | 赛后抓取的 JSON 可能同时包含赛前字段和赛后字段 | 每个 feature 必须有 `feature_observed_at <= prediction_cutoff_time` 证据 | 是，若落库或训练 |
| odds 混用初盘、现价、终盘 | `scripts/model_training/train_baseline_v1.py`、`odds_harvest_pipeline.shared.js`、L2P odds raw roadmap | `close_odds/current_odds` 对 T-24H 预测会泄露未来市场信息 | odds 单独建 timestamped raw contract；按 horizon 取样 | 是，odds 相关均需授权 |
| backtest 未模拟真实赛前可见信息 | `formal_training_dataset_design_dry_run_20260619.md`、`train_baseline_v1.py` | random split 或后验 feature 会夸大效果 | chronology split、prediction horizon、cutoff-time manifest | 是，training/backtest 禁跑禁改 |
| source fidelity / data_version 混用 | `RAW_MATCH_DATA_COMPLETENESS_SOURCE_FIDELITY_AUDIT_PHASE5_21L2A.md`、`RawMatchDataVersionSelector.js` | `raw_match_data` mixed provenance，synthetic/unknown 不应混入 FotMob parser/training | parser/feature 必须显式选择 data_version | 是，若改 selector/parser |
| legacy collector/browser/proxy 路径被误恢复 | `FotMobApiClient.js`、`FotMobStrategy.js`、`docs/data/FOTMOB_CURRENT_STATE.md` | 可能触网、绕过、写库或拿到不稳定 payload | 只在单独授权的 safe target 下使用 | 是，且应分 network/DB/raw write 授权 |

## 7. FotMob 稳定性初步判断

| 稳定性问题 | 只读线索 | 初步判断 |
| --- | --- | --- |
| raw payload 保留机制 | `FOTMOB_RAW_PAYLOAD_STORAGE_POLICY.md`、`FOTMOB_RETAINED_RAW_STAGE_STATUS.md` | 有 raw retention / manifest / sha / gitignore / `raw_match_data` 线索，但不同 phase 的 data_version 共存 |
| retained raw / replay | `FOTMOB_RAW_PARSER_CONTRACT.md`、retained raw 4 rows、pageProps v2 8 seeded rows报告 | 有结构审计和 parser contract，但不能证明大规模稳定 |
| anti-bot / rate limit / proxy / browser | `FotMobApiClient.js` 有 browser bootstrap、proxy agent、critical cookies；`FotMobRawDetailFetcher.js` 阻止 browser/proxy/retry | 既有高风险能力，也有后续 safe fetcher 的防护线索 |
| 失败记录 | current-state 记录 legacy API 404、SSR page 200、Phase 5.11 direct API 403 的治理背景；route selector 检测 403/429 | FotMob endpoint 稳定性不是默认可信 |
| 低频采集策略 | storage policy 写明 no parallel、no retry storm、stop on block、per-league/season batching | 未来采集应保持 controlled preflight/write，不应直接跑 legacy |

## 8. 当前不能碰的高风险区域

- `scripts/**`：包含 scraper、collector、preflight、controlled write、odds、training 入口；本次只读，执行/修改都可能触网或写库。
- `src/**`：包含 parser、fetcher、route selector、API client、harvester strategy、feature selector；改动会改变 runtime behavior。
- `tests/**`：本次任务明确禁止修改；测试可以提供线索，但不能替代 DATA-L1A 报告。
- DB / migration：`raw_match_data`、versioned schema、odds 表均涉及写入和迁移；本次无授权。
- Docker：本次禁止运行或修改 Docker，且无需容器。
- secrets / `.env`：本次不需要，不能读取或修改。
- scraper / collector：任何 live FotMob 或 OddsPortal 采集都不在本次范围。
- training / pipeline：字段边界未确认前不能训练或跑 pipeline。
- staging server：本次不连接 `192.168.10.4`、`xupeng-X556UB` 或 staging。

## 9. 对后续 DATA-L1B 的建议

建议下一步任务：

```text
DATA-L1B: FotMob Prematch Field Contract
```

目标：把 DATA-L1A 发现的字段和字段类别整理成正式字段合同，明确 `safe_prematch`、`unsafe_postmatch`、`unknown_timing`、`metadata_only`、`debug_or_raw_only`。未来 parser / feature / training / backtest 必须遵守这个字段合同。

建议产出文件可以是 `docs/data/fotmob_prematch_field_contract.md`。本次没有创建该文件，也没有启动 DATA-L1B。

## 10. 对旧文件清理的建议

现在不要直接删除旧脚本、旧测试、旧文档。DATA-L1A 之前，这些旧文件可能还保留数据源经验、失败方案、字段线索、历史入口信息。

建议未来单独做：

```text
CLEANUP-L1A: Repository File Usage Audit
```

本次没有启动 CLEANUP-L1A。

## 11. 本次明确不做事项

说明：以下指 DATA-L1A 审计工作本身。`git commit` 时仓库 hook 自动执行了 Gatekeeper 门禁；本报告不把该自动门禁视为 FotMob 审计、采集或训练。

- 没有改代码
- 没有改测试
- 没有改 CI
- 没有改 Docker
- 没有改 DB / migration
- 没有改 scraper / collector
- 没有运行 FotMob 采集
- 没有访问真实 FotMob 网络接口
- 没有改 parser
- 没有改 feature
- 没有改 training
- 没有碰 staging server
- 没有启动 L3I
- 没有启动 L4
- 没有做 legacy 删除 / 移动 / 重命名
- 没有做 CLEANUP-L1A
- 没有做 DATA-L1B

## 12. 下一步建议

1. 本 PR 合并前，观察 changed files 和 CI。
2. 本 PR 只应包含 `docs/_reports/data_l1a_fotmob_prematch_boundary_audit.md`。
3. 合并后，进入 DATA-L1B: FotMob Prematch Field Contract。
4. DATA-L1B 仍建议 docs-only。
5. 等 DATA-L1A / DATA-L1B 完成后，再考虑 CLEANUP-L1A。
6. 未授权前，不要改 scraper / parser / DB / Docker / training。
