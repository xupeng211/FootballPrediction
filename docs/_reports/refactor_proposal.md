# Docs 重构方案

生成时间：2025-09-26 23:19:22

## 目标目录结构
```

docs/
  README.md                  # 文档首页（综述 + 快速导航）
  architecture/              # 架构与设计
    ADR/                     # 决策记录（adr-YYYYMMDD-*.md）
  how-to/                    # 使用/操作指南
  reference/                  # API/配置/数据字典
  testing/                   # 测试策略、覆盖率、CI/报告
  data/                      # 数据采集、清洗、设计
  ml/                        # 特征工程、模型训练与评估
  ops/                       # 部署、监控、告警、回滚、runbooks
  release/                   # 发布说明与变更日志
  staging/                   # 预演/验收/彩排
  glossary.md                # 术语表
  INDEX.md                   # 人工索引
  _reports/                  # 自动生成审计报告
  _meta/                     # 清单与映射
  legacy/                    # 历史/废弃/归档条目


```

## 迁移映射表（节选）
共 41 条，完整见 `docs/_meta/mapping.csv`

| 源文件 | 目标文件 | 动作 | 原因 |
|--------|----------|------|------|
| docs/TEST_STRATEGY.md | docs/testing/TEST_STRATEGY.md | merge | 与 TESTING_STRATEGY.md 合并 |
| docs/TESTING_STRATEGY.md | docs/testing/TEST_STRATEGY.md | keep | 保留合并结果 |
| docs/DEPLOYMENT_GUIDE.md | docs/how-to/DEPLOYMENT_GUIDE.md | move | 部署指南 |
| docs/PRODUCTION_DEPLOYMENT_GUIDE.md | docs/how-to/PRODUCTION_DEPLOYMENT_GUIDE.md | move | 生产部署手册 |
| docs/architecture.md | docs/architecture/architecture.md | move | 系统架构文档 |
| docs/ARCHITECTURE_IMPROVEMENTS.md | docs/architecture/ARCHITECTURE_IMPROVEMENTS.md | move | 架构优化改进说明 |
| docs/MONITORING.md | docs/ops/MONITORING.md | move | 监控与告警机制 |
| docs/monitoring.md | docs/ops/MONITORING.md | deprecate | 重复，保留 MONITORING.md |
| docs/PHASE6_PROGRESS.md | docs/legacy/PHASE6_PROGRESS.md | deprecate | 阶段性报告，归档 |
| docs/PHASE5_COMPLETION_REPORT.md | docs/legacy/PHASE5_COMPLETION_REPORT.md | deprecate | 阶段性报告，归档 |
| docs/PHASE5.3.2.2_COMPLETION_REPORT.md | docs/legacy/PHASE5.3.2.2_COMPLETION_REPORT.md | deprecate | 阶段性报告，归档 |
| docs/TESTING_OPTIMIZATION_REPORT.md | docs/legacy/TESTING_OPTIMIZATION_REPORT.md | deprecate | 阶段性报告，归档 |
| docs/CI_FIX_REPORT.md | docs/legacy/CI_FIX_REPORT.md | deprecate | 阶段性报告，归档 |
| docs/PHASE_COMPLETION_AUDIT.md | docs/legacy/PHASE_COMPLETION_AUDIT.md | deprecate | 阶段性报告，归档 |
| docs/CI_MIGRATION_COMPATIBILITY_REPORT.md | docs/legacy/CI_MIGRATION_COMPATIBILITY_REPORT.md | deprecate | 阶段性报告，归档 |
| docs/PHASE5.3_COMPLETION_REPORT.md | docs/legacy/PHASE5.3_COMPLETION_REPORT.md | deprecate | 阶段性报告，归档 |
| docs/PHASE5.2.1_COMPLETION_REPORT.md | docs/legacy/PHASE5.2.1_COMPLETION_REPORT.md | deprecate | 阶段性报告，归档 |
| docs/LOCAL_CI_REPORT.md | docs/legacy/LOCAL_CI_REPORT.md | deprecate | 阶段性报告，归档 |
| docs/PHASE5322_COMPLETION_REPORT.md | docs/legacy/PHASE5322_COMPLETION_REPORT.md | deprecate | 阶段性报告，归档 |
| docs/REPAIR_VERIFICATION_REPORT.md | docs/legacy/REPAIR_VERIFICATION_REPORT.md | deprecate | 阶段性报告，归档 |
| docs/CI_FINAL_REPORT.md | docs/legacy/CI_FINAL_REPORT.md | deprecate | 阶段性报告，归档 |
| docs/CI_REPORT.md | docs/legacy/CI_REPORT.md | deprecate | 阶段性报告，归档 |
| docs/COVERAGE_BASELINE_REPORT.md | docs/legacy/COVERAGE_BASELINE_REPORT.md | deprecate | 阶段性报告，归档 |
| docs/PHASE6_COMPLETION_REPORT.md | docs/legacy/PHASE6_COMPLETION_REPORT.md | deprecate | 阶段性报告，归档 |
| docs/PHASE5.2_COMPLETION_REPORT.md | docs/legacy/PHASE5.2_COMPLETION_REPORT.md | deprecate | 阶段性报告，归档 |
| docs/CI_SLOW_SUITE_FIX_REPORT.md | docs/legacy/CI_SLOW_SUITE_FIX_REPORT.md | deprecate | 阶段性报告，归档 |
| docs/reports_archive/QUALITY_REPORT.md | docs/legacy/QUALITY_REPORT.md | deprecate | 阶段性报告，归档 |
| docs/reports_archive/DATABASE_CONFIG_FIXES_REPORT.md | docs/legacy/DATABASE_CONFIG_FIXES_REPORT.md | deprecate | 阶段性报告，归档 |
| docs/reports_archive/PRODUCTION_DEPLOYMENT_MONITORING_COMPLETION_REPORT.md | docs/legacy/PRODUCTION_DEPLOYMENT_MONITORING_COMPLETION_REPORT.md | deprecate | 阶段性报告，归档 |
| docs/reports_archive/STAGE6_COMPLETION_REPORT.md | docs/legacy/STAGE6_COMPLETION_REPORT.md | deprecate | 阶段性报告，归档 |

## Pull Request 说明模板

### 重构原因
- 消除重复文档 (例: TEST_STRATEGY vs TESTING_STRATEGY)
- 修复坏链 (19 个)
- 整理阶段性报告到 legacy/，保持历史留痕
- 统一目录结构，便于索引与导航

### 影响范围
- 文档内相对链接需要重写
- CI 新增 docs.check 守护脚本
- 旧文档引用会通过 legacy/ 占位符跳转

### 回滚方式
- 删除本次分支，保留 legacy/ 下原始文档即可
