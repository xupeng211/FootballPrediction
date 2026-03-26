# Project: Deep Clean 技术债清缴地图

> 分支: `refactor/tech-debt-liquidation`
> 审计日期: 2026-03-26
> 审计范围: `src/`, `tests/`

## 结论

- 活跃代码中超过 500 行的 `src/` 文件共有 69 个，`tests/` 文件共有 11 个。
- `src/` 中检测到 URL 硬编码 33 个文件、队名/联赛/博彩公司硬编码 32 个文件、SQL/Schema 硬编码 51 个文件。
- `tests/` 中检测到高脆弱测试 32 个文件，其中 28 个带外网或真实浏览器依赖，6 个带绝对路径依赖，6 个带文件系统/权限耦合。
- `AbstractHarvester.js` 仍是 P0 上帝类，应作为第一刀目标。

## P0: God Classes

重点对象:

- `src/infrastructure/harvesters/base/AbstractHarvester.js` 1026 行
- `src/infrastructure/harvesters/OddsPortalHarvester.js` 1856 行
- `src/infrastructure/harvesters/OddsPortalParser.js` 1230 行
- `src/infrastructure/harvesters/StealthNavigator.js` 1178 行
- `src/infrastructure/network/SessionManager.js` 861 行
- `src/infrastructure/recon/ReconStitcher.js` 743 行
- `src/infrastructure/recon/ReconParser.js` 671 行
- `src/ml/inference/predictor.py` 1293 行
- `src/database/schema_manager.py` 1210 行

## P1: Hard-coded Fragility

代表样本:

- `src/infrastructure/harvesters/OddsPortalHarvester.js`
  - 内嵌 `OUTPUT_DIR`, `SESSION_DIR`, `BASE_URL`, `LEAGUE_URLS`
- `src/utils/Normalizer.js`
  - 方法体内联 `TEAM_NAME_MAPPINGS`
- `src/infrastructure/recon/ReconEngine.js`
  - 运行时直接拼接 `resultsUrl`
- `src/infrastructure/services/FixtureRepository.js`
  - 仓储层直接拼接 SQL 与列名

治理建议:

- URL、目录、联赛 slug 全部收口到 `config/`
- 队名与博彩公司映射抽成 registry/data dictionary
- Schema 与表列名抽到常量层，降低迁移回归

## P1: Test Fragility

高风险样本:

- `tests/integration/Real_Data_Extraction.test.js`
  - 真实外网、真实数据库、真实代理
- `tests/integration/Golden_Injection_Verify.test.js`
  - 依赖 `/app/data/sessions/auth_gold.json`
- `tests/smoke_test.js`
  - 依赖 `/app/src/...`、真实浏览器、真实外网、`/app/data/debug`
- `tests/unit/RealWorld_Odds_Fetch.test.js`
  - 名义单测，实质使用真实 OddsPortal URL 与代理假设
- `tests/unit/StructuredLogger.test.js`
  - 对 `/app/logs/pipeline` 做固定断言

治理建议:

- live test 与 unit/integration test 分层
- 默认 CI 禁跑真实外网套件
- 禁止测试写死 `/app/...`
- 用临时目录工厂替代绝对路径和权限假设

## P2: Contract Mismatch

已确认样本:

- `src/infrastructure/harvesters/OddsPortalParser.js`
  - `deepParseOddsData()` 文档只写 `{ pinnacle, bet365 }`，实际还返回 `raw`, `_apiDecrypt`, `_apiExcavator`, `_version`
- `src/feature_engine/smelter/components/MarketSentimentExtractor.js`
  - `extract()` 文档未说明 `metadata` 与 fallback 返回结构
- `src/feature_engine/smelter/FeatureSmelter.js`
  - `run()` 文档未说明初始化前置条件
  - `close()` 文档写“关闭资源”，实际未显式释放池资源
- `src/utils/Normalizer.js`
  - `normalizeSeason()` 文档未强调“赛季必须连续”
- `src/infrastructure/harvesters/ProductionHarvester.js`
  - 文件头语义偏“生产主实现”，实际是兼容适配层

## `AbstractHarvester.js` 拆解方案

建议拆为 5 个职责块:

1. `HarvesterLifecycleService`
2. `HarvesterContextPool`
3. `HarvesterRetryPolicy`
4. `HarvesterExecutionEngine`
5. `HarvesterTelemetry`

建议拆解顺序:

1. 先抽 `HarvesterRetryPolicy`
2. 再抽 `HarvesterContextPool`
3. 再抽 `HarvesterTelemetry`
4. 最后收口生命周期与依赖注入

第一阶段目标:

- 将 `AbstractHarvester.js` 压到 700 行以内
- 保持子类 API 不变
- 为重试、Context 淘汰、优雅停机补契约测试
