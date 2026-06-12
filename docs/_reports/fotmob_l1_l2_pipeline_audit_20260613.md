# FotMob L1/L2 Pipeline Contract Audit - 2026-06-13

- lifecycle: phase-artifact
- scope: read-only audit only
- note: 超过 120 行的原因是本次必须同时覆盖 10 个指定问题、并行实现分叉和证据索引，已压缩为最小证据集

## 1. Scope / 本次边界

本次只做只读调查，目标是看清楚 FotMob 的 L1 发现层和 L2 detail raw retention 层现在分别在哪里、靠什么衔接、有没有真正形成正式闭环。

本次没有做这些事：
- 没有抓新数据
- 没有访问 FotMob live detail
- 没有运行 live scraper
- 没有写数据库
- 没有改 runtime 代码
- 没有改 parser / test / schema / migration
- 没有做 feature / model / prediction

## 2. Current Conclusion / 当前结论

- L1 存在，而且不是空壳。核心在 `src/infrastructure/services/DiscoveryService.js`，既能发现 league/season fixtures，也能把标准化结果写进 `matches`。
- L2 也存在，而且不止一条路。当前实际可验证的 retained raw 路线是 `raw_match_data + data_version=fotmob_live_v1`；另外仓库里还并行存在 `fotmob_html_hyd_v1/pageprops_v2` 的 phase-gated 路线，以及一套更长线的 `football_match_targets -> fotmob_raw_match_payloads` 设计。
- 现在没有一个“当前正式、通用、自动”的 L1 -> L2 闭环。L1 能产出，L2 也能写 raw，但中间缺统一 handoff。
- 当前最大的断点不是“不会抓”，而是“谁来接棒、用哪张表/哪个状态字段接棒、按什么任务池推进”没有一个被当前实现统一下来。

## 3. L1 Discovery / Schedule 层现状

相关代码和文档：
- `src/infrastructure/services/DiscoveryService.js`
- `src/infrastructure/services/DiscoveryParser.js`
- `src/infrastructure/services/DiscoveryDataValidator.js`
- `src/infrastructure/services/DiscoveryAttributeMapper.js`
- `src/infrastructure/services/L1ConfigManager.js`
- `src/infrastructure/services/FixtureRepository.js`
- `scripts/ops/seed_fixtures.js`
- `scripts/ops/l1_discovery_safe_preview.js`
- `docs/architecture/L1_DATA_CONTRACT.md`
- `tests/unit/DiscoveryService.discoverCandidates.test.js`

入口和职责：
- `DiscoveryService.discover()` 是 L1 正式发现入口，走 `_scanLeague()` -> `_fetchFixtures()` -> `fixtureRepository.persist(...)`，会写 `matches`。证据：`src/infrastructure/services/DiscoveryService.js:291-327,653-713`。
- `DiscoveryService.discoverCandidates()` 是安全候选预览入口，只做 fetch/parse/normalize，不调用 `persist`，不写 DB。证据：`src/infrastructure/services/DiscoveryService.js:357-440`。
- `L1ConfigManager.buildLeagueApiUrl()` 说明 L1 当前确实按 `leagueId + season` 去拿 FotMob 联赛赛程。证据：`src/infrastructure/services/L1ConfigManager.js:118-121`。
- `DiscoveryAttributeMapper.mapMatch()` 说明 L1 当前标准输出已经覆盖 `match_id`、`external_id`、`league_name`、`season`、`home_team`、`away_team`、`match_date`、`status`、`is_finished`、`data_source`。证据：`src/infrastructure/services/DiscoveryAttributeMapper.js:93-129`。

L1 当前能拿到什么：
- 能发现 league / season fixtures。证据：`DiscoveryService._fetchFixtures()` 直接构造 `https://www.fotmob.com/api/data/leagues?id=...&season=...`，并带网页 fallback。见 `src/infrastructure/services/DiscoveryService.js:769-835`。
- 能做按日期过滤后的候选输出。证据：`discoverCandidates()` 的 `date` 必填，最终候选经过 `_filterCandidatesByDate()`。见 `src/infrastructure/services/DiscoveryService.js:401-416,622-629`。

L1 输出写到哪里：
- 正式 discover 路线写 `matches`。证据：`FixtureRepository._persistBatch()` 向 `matches` 做 `INSERT ... ON CONFLICT (match_id) DO UPDATE`。见 `src/infrastructure/services/FixtureRepository.js:489-535`。
- 预览路线只返回内存中的候选对象，不写表。证据：`discoverCandidates()` 的 `safety_summary` 明确 `wrote_db=false`、`called_persist=false`。见 `src/infrastructure/services/DiscoveryService.js:575-619`。

L1 是否覆盖 league / season / fixtures / status / score / external_id：
- `league / season / external_id / home / away / match_date / status`：有，见 `DiscoveryAttributeMapper.js:115-129`。
- `score`：L1 写 `matches` 时保留 `home_score` / `away_score` 字段，但候选预览对象本身不带 score。见 `FixtureRepository.js:503-529` 与 `DiscoveryService.js:632-646`。

## 4. L2 Detail Raw Retention 层现状

当前能看到 3 组相关实现。

第一组：当前已落地并被 #1485/#1486/#1502 用过的 retained raw 路线
- `scripts/ops/single_live_fotmob_raw_ingest_smoke.js`
- `scripts/ops/n3_live_fotmob_raw_retain.js`
- `src/infrastructure/services/FotMobRawDetailFetcher.js`
- `docs/_reports/fotmob_retain_more_raw_sample_20260612.md`
- `docs/_reports/fotmob_retain_50_raw_parser_validation_20260613.md`

这组路线的特点：
- 实际写入目标是 `raw_match_data`，而且 #1502 证明写的是 `data_version=fotmob_live_v1`。证据：`docs/_reports/fotmob_retain_50_raw_parser_validation_20260613.md:13-21,46-57`。
- 输入不是自动从 L1 调度来的，而是显式 target 输入：`--match-id --external-id --home-team --away-team`，或者从候选 config 读入。证据：`scripts/ops/single_live_fotmob_raw_ingest_smoke.js:37-71,161-179`；`scripts/ops/n3_live_fotmob_raw_retain.js:24-45,115-130`。
- `n3_live_fotmob_raw_retain.js` 默认 `dataVersion='fotmob_live_v1'`，并且写 `raw_match_data` 用的是 `(match_id, data_version)` 冲突键。证据：`scripts/ops/n3_live_fotmob_raw_retain.js:70-79,115-118`。
- 这条线依赖 `matches` 已经存在对应 `match_id`，否则不自动 seed。证据：`docs/_reports/fotmob_retain_more_raw_sample_20260612.md:30-31`，以及单场 retained 工具的 FK guard 说明 `Seed it first` 路线。`scripts/ops/single_live_fotmob_raw_ingest_smoke.js:25-35`。

第二组：phase-gated 的 detail preview / controlled write 路线
- `scripts/ops/l2_raw_detail_preview.js`
- `scripts/ops/l2_raw_match_data_write.js`
- `src/infrastructure/services/FotMobRawDetailFetcher.js`
- `src/infrastructure/services/FotMobDetailRouteSelector.js`

这组路线的特点：
- `FotMobRawDetailFetcher` 是明确定义好的 detail fetcher，但它每次调用都要吃 `externalId`，可选带 `matchId/homeTeam/awayTeam/matchDate`，自己不从 L1 拉任务。证据：`src/infrastructure/services/FotMobRawDetailFetcher.js:4-9,73-123`。
- `l2_raw_match_data_write.js` 是 exact-scope、单目标、强授权写入脚本，不是通用调度器。默认 target 还是硬编码单场 `53_20252026_4830746`，默认 `dataVersion='fotmob_html_hyd_v1'`。证据：`scripts/ops/l2_raw_match_data_write.js:10-21`。

第三组：legacy backlog / pipeline_status 路线
- `src/infrastructure/services/MarathonService.js`
- `scripts/ops/backfill_historical_raw_match_data.js`
- `database/migrations/V12.2__add_matches_pipeline_status.sql`

这组路线的特点：
- 会从 `matches LEFT JOIN raw_match_data` 找 pending 项，再写 raw，并回写 `matches.pipeline_status='harvested'`。证据：`MarathonService.js:665-703`，`backfill_historical_raw_match_data.js:545-596`。
- 这说明仓库历史上确实有“L1 产出 matches，L2 扫 pending”这套思路。
- 但它不是当前 `fotmob_live_v1` retained raw 扩容使用的主路径，而且它还保留 `ON CONFLICT (match_id)` 这种旧写法。证据：`MarathonService.js:633-643`，`backfill_historical_raw_match_data.js:563-579`。

当前 L2 写到哪里：
- 当前 retained raw 样本写到 `raw_match_data`。证据：`docs/_reports/fotmob_retain_more_raw_sample_20260612.md:20-23,42-43`；`docs/_reports/fotmob_retain_50_raw_parser_validation_20260613.md:18-22,34-45`。
- 仓库还存在另一张长期设计表 `fotmob_raw_match_payloads`，但它属于另一套长线 raw JSON 设计，不是 #1502 这次 58 条 retained raw 的落点。证据：`database/migrations/V26.5__create_fotmob_raw_match_payloads.sql:1-59`。

## 5. L1 -> L2 Contract / 协作契约

| 项目 | 当前状态 | 证据文件 | 风险 |
|---|---|---|---|
| L1 发现能力 | 已实现，可按 `league + season` 发现 fixtures | `src/infrastructure/services/DiscoveryService.js:291-327,769-835` `src/infrastructure/services/L1ConfigManager.js:118-121` | 能发现，不等于已自动接入 L2 |
| L1 标准输出字段 | 基本够用，已有 `match_id/external_id/season/home/away/match_date/status` | `src/infrastructure/services/DiscoveryAttributeMapper.js:115-129` `docs/architecture/L1_DATA_CONTRACT.md:119-151` | 字段够，不代表消费方已统一 |
| L1 正式落点 | 写 `matches` | `src/infrastructure/services/FixtureRepository.js:489-535` | `matches` 只是结果表，不等于任务池 |
| L2 最小输入 | 当前实际需要 `match_id + external_id`，保守场景还会带 `home_team/away_team/match_date` | `scripts/ops/single_live_fotmob_raw_ingest_smoke.js:39-63,161-179` `src/infrastructure/services/FotMobRawDetailFetcher.js:73-123` | 输入契约散在脚本里，没有统一 current-state 规范 |
| L2 当前输入来源 | 主要是显式 target / 候选 config / 已存在 `matches` 行，不是自动消费 L1 结果流 | `docs/_reports/fotmob_retain_more_raw_sample_20260612.md:28-33,66-68` | 依赖人工圈定范围，扩容方式不标准化 |
| L2 是否依赖 L1 输出 | 弱依赖。依赖 `matches` 里已有 `match_id/external_id` 和 FK 存在，但不是 L1 发现后自动触发 | `deploy/docker/init_db.sql:58-68` `docs/_reports/L1_CONTROLLED_MATCHES_SEED_COMMIT_EXECUTION_PREFLIGHT_PHASE5_08L1.md` | “有前置依赖”不等于“已经串起来” |
| 任务池 / queue | 当前没有一条被现行 retained raw 路线真正启用的统一任务池 | 当前 retained raw 证据在 `fotmob_retain_more_raw_sample_20260612.md`；并行设计在 `database/migrations/V26.6__create_football_calendar_target_registry.sql:83-119` | 现行实现与长线设计分叉，团队容易误判“已经有队列了” |
| 状态字段 | 有两套但没统一：旧的 `matches.pipeline_status`，新的 `football_match_targets.target_state/raw_json_status` | `database/migrations/V12.2__add_matches_pipeline_status.sql:4-40` `database/migrations/V26.6__create_football_calendar_target_registry.sql:83-119,248-251` | 双轨并存，当前 retained raw 没把二者统一成一套真状态机 |
| retry / failed / retained / parsed 状态 | 有零散表达，没有单一端到端状态机 | `matches.pipeline_status` 见 V12.2；`football_match_targets.target_state` 见 V26.6；parser 成功/失败目前只在报告里体现 `58/58` | 运行状态和治理状态分离，后续难调度、难审计 |
| 调度闭环 | 没有当前正式闭环 | `MarathonService.js:665-703` 代表旧 backlog 思路；`#1502` 报告代表当前 bounded retained raw 实操 | 现在更像“可手工推进的若干能力块”，不是正式流水线 |

重点判断：
- L1 输出字段从内容上看，已经足够驱动 L2。
- 真正缺的不是字段本身，而是“谁消费这些字段、在哪里排队、状态怎么推进、哪条路径算当前正式路径”。

## 6. #1502 的真实性质判断

明确判断：

- `#1502` 不是正式的通用 L1 -> L2 流水线接通。
- `#1502` 的真实性质是：基于已有 `matches` 行和候选 `external_id` 的 bounded L2 retained raw 扩容 + parser dry-run 验证。

理由：
- `#1502` 合并内容本身只有报告，没有新 runtime 代码。证据：`git show --stat af96f7d`。
- 报告明确写的是 `raw_match_data=yes`，`matches=no`，并且 candidate source 来自已有 `matches` / 非 retained 候选池。证据：`docs/_reports/fotmob_retain_50_raw_parser_validation_20260613.md:13-22,98-109`；`docs/_reports/fotmob_retain_more_raw_sample_20260612.md:28-33,66-74`。
- 所以它证明的是“L2 retained raw 扩容和 parser 样本验证可以做”，不是“正式 L1 discover 后自动把新 fixtures 推进到 L2”。

## 7. Missing Pieces / 缺口清单

P0: 没有一个被当前实现明确采纳的 L1 -> L2 handoff 契约
- 现在可选承载物至少有 `matches + pipeline_status`、`football_match_targets`、以及“人工圈定候选清单”三套。
- 不先定唯一真相，就谈不上正式闭环。

P0: 没有当前正式启用的 L2 任务池 / 状态机 / 消费器
- L1 发现完之后，谁把 `pending` 目标交给当前 retained raw 路线，没有统一实现。

P0: 当前 retained raw 路线和长线 registry 设计没有接到一起
- `raw_match_data(fotmob_live_v1)` 是当前真样本。
- `football_match_targets -> fotmob_raw_match_payloads` 是并行长线设计。
- 这两套现在没有统一成一条 current path。

P1: current-state 文档落后于事实
- `docs/data/FOTMOB_RETAINED_RAW_STAGE_STATUS.md` 还写 4 条 retained raw，但 #1502 后事实是 58 条。
- `docs/data/FOTMOB_CURRENT_STATE.md` 也还是以旧 ADG 叙述为主。

P1: 历史 backlog 路线仍在，但和现行版本感知不一致
- 旧脚本还用 `ON CONFLICT (match_id)`，而新写法已经朝 `(match_id, data_version)` 走。
- 这意味着旧调度器不能直接代表当前 L2 正式实现。

P2: 文档层面已经描述过很多设计，但 current contract 没有收口
- 不是“没想过”，而是“想过多套，还没收敛成当前正式版”。

## 8. Minimal Next Step / 下一步最小建议

只建议一个最小下一步：

做一个单独的 design / contract PR，只定一件事：明确当前 FotMob 正式 L1 -> L2 handoff 到底以哪张表和哪组状态字段为准。

建议优先把下面这件事定死，不做抓数、不做 parser、不做 feature/model：
- 选定“当前正式承载物”只能二选一：`matches + pipeline_status`，或者 `football_match_targets + raw_json_status/target_state`。
- 同时写清楚：L1 产出后谁进入 pending、L2 消费谁、写完 raw 后谁改状态、parser 阶段以后再说。

## 9. Evidence / 证据索引

- `src/infrastructure/services/DiscoveryService.js`
  说明 L1 同时存在 discover 写库路径和 discoverCandidates 只读预览路径。
- `src/infrastructure/services/DiscoveryAttributeMapper.js`
  说明 L1 标准输出字段已经具备 `match_id/external_id/season/home/away/match_date/status`。
- `src/infrastructure/services/L1ConfigManager.js`
  说明 L1 当前是 league/season 维度拉 FotMob 赛程。
- `src/infrastructure/services/FixtureRepository.js`
  说明 L1 正式落点就是 `matches`。
- `src/infrastructure/services/FotMobRawDetailFetcher.js`
  说明 L2 detail fetcher 按 `externalId` 调用，不自己接任务池。
- `scripts/ops/single_live_fotmob_raw_ingest_smoke.js`
  说明当前 retained raw 单场工具输入是显式 target，不自动依赖 L1 调度。
- `scripts/ops/n3_live_fotmob_raw_retain.js`
  说明当前 N=3 retained raw 批量工具默认写 `fotmob_live_v1` 到 `raw_match_data`。
- `scripts/ops/l2_raw_match_data_write.js`
  说明 phase-gated L2 controlled write 是 exact-scope 单目标，不是通用闭环调度器。
- `database/migrations/V12.2__add_matches_pipeline_status.sql`
  说明历史上确实设计过 `matches.pipeline_status` 这套 L1/L2 状态字段。
- `src/infrastructure/services/MarathonService.js`
  说明历史上确实有从 `matches` 找 pending、再写 `raw_match_data` 的 backlog 思路。
- `scripts/ops/backfill_historical_raw_match_data.js`
  说明 legacy L2 consumer 依赖 `matches LEFT JOIN raw_match_data`。
- `database/migrations/V26.5__create_fotmob_raw_match_payloads.sql`
  说明仓库里还存在另一套长线 raw JSON 存储表。
- `database/migrations/V26.6__create_football_calendar_target_registry.sql`
  说明仓库里还存在另一套 target registry / 状态机设计。
- `docs/_reports/fotmob_retain_more_raw_sample_20260612.md`
  说明 `24` 条 retained raw 扩容来自已有 `matches` 候选，不是新 L1 闭环。
- `docs/_reports/fotmob_retain_50_raw_parser_validation_20260613.md`
  说明 `#1502` 实质是 `24 -> 58` retained raw 扩容加 parser dry-run，不是正式 L1 -> L2。
- `docs/data/FOTMOB_RETAINED_RAW_STAGE_STATUS.md`
  说明 current-state 文档已落后于最新 `58` 条现实。

## 10. Validation / 验证

本次只做了只读命令和提交前静态检查：

- `git fetch origin`
- `git checkout main`
- `git pull --ff-only origin main`
- `git checkout -b docs/fotmob-l1-l2-pipeline-audit`
- `git status --short --branch`
- `git branch --show-current`
- `git log --oneline -n 5`
- `git remote -v`
- `rg ...`
- `find ...`
- `nl -ba <file> | sed -n ...`
- `git diff --check`

本报告没有触发 network fetch、没有写 DB、没有改 runtime/test/schema。
