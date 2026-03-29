# Recon 模块说明

> 版本: `V11.0`
>
> 目标: 让 `ReconNavigator` 只负责浏览器流程调度，让 `ReconEngine` 只负责业务编排，其余能力全部下沉到可独立测试、可独立替换的服务。

## 1. 模块边界

### 1.1 顶层编排器

- `ReconNavigator.js`
  负责浏览器生命周期、导航、协议抓取入口、熔断保护、服务装配。
- `ReconEngine.js`
  负责待处理任务装配、候选源选择、匹配结果汇总、批量持久化和运行级日志。

### 1.2 Navigator 下沉服务

- `services/ReconBrowserContext.js`
  负责 Playwright `launch/newContext/newPage/close`、consent 处理、页面预热和滚动唤醒。
- `services/ReconNetworkMonitor.js`
  负责 `response` 拦截、协议响应解包、解密、分页 API 抓取和候选去重。
- `services/ReconDomScraper.js`
  负责 results 页 DOM 行提取、分页发现、current season DOM fallback。
- `services/ReconStateProber.js`
  负责 `pageOutrightsVar` / 页面脚本状态提取、current season archive 修复、联赛页回探。

### 1.3 Engine 下沉服务

- `services/ReconMirrorManager.js`
  负责赛季镜像与复合键索引。
- `services/ReconMatchEvaluator.js`
  负责队名相似度、日期置信度、主客反转判定、最佳候选选择。
- `services/ReconTaskPlanner.js`
  负责 target 装配、pending 队列筛选、source 评估与 fallback 路由。

### 1.4 Repository 1+3 结构

- `../services/FixtureRepository.js`
  作为对外唯一仓储门面，负责连接池、重试、状态更新入口和子服务装配。
- `../services/recon/MatchIdentityResolver.js`
  负责 L1/L2 热路径上的实时身份对齐。入库前按 `season + data_source + external_id(raw_match_id)` 查找 canonical winner，命中则复用既有 `match_id`，阻断重复实体继续扩散。
- `../services/recon/ReconSchemaJanitor.js`
  负责 mapping schema 对齐、`season/hash` 唯一索引固化、历史脏数据自愈。
- `../services/recon/ReconMappingStore.js`
  负责 mapping 写入、批量保存、hash 冲突审计和事务内重绑。
- `../services/recon/ReconConflictArbiter.js`
  负责队名/日期打分、冲突胜者选择和错误映射仲裁。
- `../services/recon/MatchCanonicalJanitor.js`
  只负责离线 canonical 审计与两阶段收敛：先按 `raw_match_id` 收敛逻辑实体，再按 active `external_id` 固化唯一索引，避免线上热路径承担批量修复职责。

## 2. 运行流程

1. `recon_scanner.js` 初始化 `FixtureRepository`、`ReconScanner`、`ReconEngine`。
2. `ReconEngine.runReconMatrix()` 通过 `ReconTaskPlanner` 选择联赛和 pending matches。
3. `ReconTaskPlanner.selectCandidateSource()` 调用 `ReconNavigator.fetchFullSeasonArchive()` 或 `protocolArchiveExtract()`。
4. `ReconNavigator` 通过 `ReconBrowserContext` 驱动页面，通过 `ReconNetworkMonitor` / `ReconDomScraper` / `ReconStateProber` 收集候选。
5. `ReconMirrorManager` 构建赛季镜像，`ReconMatchEvaluator` 给每场待对齐比赛计算最佳候选。
6. `ReconEngine._persistReconBatches()` 调用 `FixtureRepository`，由 Repository 薄壳把写入委托给 `ReconMappingStore`，必要时经 `ReconConflictArbiter` 仲裁并由 `ReconSchemaJanitor` 保证 schema/索引健康。
7. 每个批次最终落库 `RECON_LINKED` / `RECON_MISMATCH`，并带 `recon_run_id` 日志收口。

## 2.1 Repo-Service 协作图

```text
recon_scanner
  -> ReconEngine
    -> FixtureRepository
      -> MatchIdentityResolver
           -> canonical match_id lookup by season + source_provider + raw_match_id
      -> ReconSchemaJanitor
           -> dedupeMappings / repairLinkedStatusesWithoutMapping
      -> ReconMappingStore
           -> ReconConflictArbiter
           -> matches_oddsportal_mapping / matches
      -> MatchCanonicalJanitor
           -> Phase 1: raw_match_id consolidation
           -> Phase 2: active external_id consolidation
           -> idx_matches_season_source_external_active_unique
```

## 2.2 为什么要两阶段收敛

2025/2026 赛季暴露出的根因不是 OddsPortal hash 真碰撞，而是同一个 FotMob `raw_match_id` 被写成了多个本地 `match_id`，并且部分实体的 `external_id`、`match_date`、主客方向已经漂移。单靠 `matches(home, away, date)` 无法稳定识别这类病灶。

- Phase 1: `raw_match_id` 收敛
  直接以 `raw_match_data.general.matchId` 为锚点，把指向同一原始赛事的本地实体先合成一个 canonical winner。这一步解决“同一真实比赛被写成多个本地 ID”的根病。
- Phase 2: `external_id` 收敛
  在 Phase 1 之后，再对 active `external_id` 做二次收敛并固化唯一索引，清掉历史上已经漂移到主表 `external_id` 的残留重复。

顺序不能反过来：

- 如果先固化 `external_id` 唯一索引，Phase 1 在修正 winner 的 `external_id` 时会被历史脏数据卡住。
- 如果只做 Phase 1，不做 Phase 2，历史上已经写进 `matches.external_id` 的重复实体仍会继续制造冲突窗口。

这也是当前架构把 `MatchIdentityResolver` 和 `MatchCanonicalJanitor` 分开的原因：

- 热路径只负责“阻止新增污染”
- 离线路径只负责“收敛历史污染”

## 3. 配置入口

Recon 运行时参数统一从 [config/recon_config.json](/home/xupeng/projects/FootballPrediction/config/recon_config.json) 读取，重点包括：

- `repository.retry`
  仓储重试次数、退避间隔、最大恢复窗口。
- `repository.conflict_arbiter`
  hash 冲突仲裁的同场阈值与时间窗口。
- `matching`
  置信度阈值、主客判定阈值、日期权重。
- `recon_runtime.engine`
  batch size、并发、批量日志频率、协议超时。
- `recon_runtime.navigator`
  浏览器导航、熔断器、archive 抓取等待。
- `recon_runtime.browser_context`
  launch 参数、viewport、consent 策略。
- `recon_runtime.network_monitor`
  API pattern、script wrapper pattern、fetch timeout。
- `recon_runtime.dom_scraper`
  CSS selector、分页规则、滚动步长。
- `recon_runtime.state_prober`
  current season 页面探测超时与等待。

## 4. 运维约束

- `ReconHealthServer` 必须注册数据库 readiness，不允许只报 liveness。
- `ReconEngine` 的批量写入日志必须带 `recon_run_id`、`batch_type`、`batch_index`、`total_batches`。
- `RECON_MISMATCH` 更新必须满足双重条件：
  当前状态仍是 `harvested`，且同赛季还不存在 mapping。
- 退出路径必须保证 `browser.close()`、`guardian.stop()`、`dbPool.end()` 最终都会执行。

## 5. 继续扩展时的边界要求

- 新的 DOM selector、滚动参数、匹配阈值，不准写回 service 文件，必须进入 `recon_config.json`。
- 新增联赛适配优先改配置，不先改 `ReconNavigator` / `ReconEngine`。
- 如果需要新增抓取策略，先判断是“页面调度问题”还是“候选匹配问题”，不要再次把职责揉回顶层编排器。
