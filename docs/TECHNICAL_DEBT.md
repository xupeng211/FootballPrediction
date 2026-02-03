# Technical Debt - [Genesis.ProductionFreeze]

本文档汇总项目中所有待完成的技术债务项。

## 优先级分类

| 优先级 | 说明 |
|--------|------|
| **P0 - Critical** | 影响生产功能的重大缺失 |
| **P1 - High** | 重要功能缺失，影响开发效率 |
| **P2 - Medium** | 改进型优化，不影响核心功能 |
| **P3 - Low** | 代码风格或文档完善 |

---

## P0 - Critical (影响生产功能)

### 1. OddsPortalEngine 实现
**文件**: `src/infrastructure/merger/GoldenDataMerger.py:480`
**TODO**: `# TODO: [Genesis.SmokeTest] Create OddsPortalEngine`
**状态**: L3 数据采集暂不可用
**影响**: 无法通过 GoldenDataMerger 完成 L3 赔率数据采集
**解决方案**:
- 创建 `src/infrastructure/engines/match_engine/oddsportal/oddsportal_engine.py`
- 继承 `BaseHarvestEngine` 并实现 `harvest_match()` 方法
- 集成 NetworkShield 代理管理
- 临时方案: 使用 QuantHarvester.js 进行 L3 采集

**预估工作量**: 4-6 小时

---

## P1 - High (重要功能缺失)

### 2. crawler_service.py NetworkShield 重构
**文件**: `src/services/crawler_service.py:40`
**TODO**: `# TODO: [Genesis.SmokeTest] Replace with NetworkGuardian`
**状态**: 使用已归档的 ProxyHealthChecker
**影响**: 功能正常但依赖遗留代码
**解决方案**:
- 替换 `ProxyHealthChecker` 为 `NetworkGuardian`
- 更新代理获取逻辑: `get_next_healthy_proxy(session_id)`
- 更新失败上报逻辑: `mark_proxy_failed(port, reason)`

**预估工作量**: 2-3 小时

---

### 3. self_healing.py NetworkShield 重构
**文件**: `src/core/self_healing.py:35`
**TODO**: `# TODO: [Genesis.SmokeTest] Replace with NetworkGuardian`
**状态**: 使用已归档的 ProxyManager
**影响**: 功能正常但依赖遗留代码
**解决方案**:
- 替换 `ProxyManager` 为 `NetworkGuardian`
- 更新 API 调用以匹配 NetworkGuardian 接口
- 移除 `get_proxy_manager()` 单例模式

**预估工作量**: 2-3 小时

---

## P2 - Medium (改进型优化)

### 4. 代码质量优化
**影响范围**: `src/api/models/`, `src/infrastructure/`
**问题**:
- RUF002: Docstring 包含全角标点符号
- COM812: 缺少尾部逗号
- TRY300: 可优化 try/except 结构

**解决方案**:
```bash
ruff check src/ --select=RUF002,COM812,TRY300 --fix
```

**预估工作量**: 30 分钟

---

## P3 - Low (文档完善)

### 5. API 文档完善
**状态**: 大部分公共方法缺少 Google Style Docstring
**文件**:
- `src/infrastructure/engines/match_engine/base/base_harvest_engine.py`
- `src/infrastructure/engines/match_engine/shared/network_guardian.py`
- `src/infrastructure/engines/match_engine/fotmob/fotmob_engine.py`
- `src/infrastructure/merger/GoldenDataMerger.py`

**解决方案**:
- 为所有公共方法添加 Google Style Docstring
- 包含 Args, Returns, Raises, Examples

**预估工作量**: 2-3 小时

---

## 已解决项 (Resolved)

### ✅ 1. Import 路径修复
**日期**: 2026-02-03
**文件**: 6 个文件
**解决**:
- `src.utils.semantic_matcher`: 修复 LevenshteinMatcher 导入
- `src.collectors.market_data_engine`: 修复 prometheus_metrics 导入
- `src.api.services.harvester_service`: 修复 circuit_breaker 导入
- `src.infrastructure.engines.match_engine.base`: 修复 shared 导入路径

### ✅ 2. 遗留代码归档
**日期**: 2026-02-03
**归档位置**: `archive/legacy/src/`
**归档数量**: 23 个文件 + 3 个目录
**脚本**: `scripts/ops/genesis_cleanup.sh`

### ✅ 3. 数据库表创建
**日期**: 2026-02-03
**表**: `metrics_multi_source_data`
**脚本**: `scripts/sql/v55_0_multi_source_metrics.sql`

---

## 下一步计划

1. **Week 1**: 完成 OddsPortalEngine 实现 (P0)
2. **Week 2**: 完成 crawler_service.py 和 self_healing.py 重构 (P1)
3. **Week 3**: 代码质量优化和文档完善 (P2-P3)

---

**最后更新**: 2026-02-03
**负责人**: [Genesis.ProductionFreeze]
