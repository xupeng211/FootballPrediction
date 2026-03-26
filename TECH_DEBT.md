# 技术债台账 (Tech Debt Register)

本文档登记已确认、可量化、且已获发布决策接受的工程技术债。

---

## [治理完成] `AbstractHarvester.js` 上帝类拆解

- 状态: **已治理 (2026-03-26)**
- 影响范围: `src/infrastructure/harvesters/base/AbstractHarvester.js`
- 治理成果: 
  - 文件规模从 1026 行压缩至 **571 行** (瘦身 44%)
  - 成功剥离 `HarvesterRetryPolicy`, `HarvesterContextPool`, `HarvesterTelemetry` 三大核心组件
  - 维持了向下兼容性，子类无需修改调用链
- 遗留工作: V12.0 计划进一步剥离 `HarvesterExecutionEngine` 以实现最终 300 行目标。

---

## [治理完成] `OddsPortalHarvester.js` 巨兽肢解

- 状态: **已治理 (2026-03-26)**
- 影响范围: `src/infrastructure/harvesters/OddsPortalHarvester.js`
- 治理成果:
  - 文件规模从 1856 行压缩至 **1184 行**
  - 100% 剥离解析逻辑至 `OddsPortalParser.js`
  - URL 构建与解析逻辑迁移至 `OddsPortalURLParser`
- 遗漏风险: 无。

---

## [治理完成] 全链路硬编码清除 (Phase 1)

- 状态: **已治理 (2026-03-26)**
- 治理范围: `Normalizer.js`, `FixtureRepository.js`, `ReconEngine.js` 等
- 治理成果:
  - 拔除了 `TEAM_NAME_MAPPINGS` 内联字典
  - 抽离了仓储层 SQL 模板至 `recon_config.json`
  - JS 侧核心 URL 已全部收口至配置中心
- 余额统计: `src/` 中仅余少量 Python 辅助类存在 URL 硬编码。

---

## [RESOLVED][P1] `AbstractHarvester.js` 上帝类膨胀

- 状态: **已治理并归档 (2026-03-26)**
- 说明: 该 P1 债务已由上文“`AbstractHarvester.js` 上帝类拆解”完成治理，本条仅保留为历史映射，避免发布追踪失联。
