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
- `../services/recon/ReconSchemaJanitor.js`
  负责 mapping schema 对齐、`season/hash` 唯一索引固化、历史脏数据自愈。
- `../services/recon/ReconMappingStore.js`
  负责 mapping 写入、批量保存、hash 冲突审计和事务内重绑。
- `../services/recon/ReconConflictArbiter.js`
  负责队名/日期打分、冲突胜者选择和错误映射仲裁。

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
      -> ReconSchemaJanitor
           -> dedupeMappings / repairLinkedStatusesWithoutMapping
      -> ReconMappingStore
           -> ReconConflictArbiter
           -> matches_oddsportal_mapping / matches
```

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
