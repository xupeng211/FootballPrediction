# 📚 项目文档总索引

本目录作为项目的文档总入口，帮助开发者快速导航到不同类别的文档。
文档分为六个主要部分：**质量保证系统**、**测试策略**、**智能报告与追踪**、**AI 驱动改进**、**开发规范与 CI/CD**、**架构与运维**。

---

## 🎯 质量保证系统
- [项目质量仪表板](./_reports/TEST_COVERAGE_KANBAN.md) - 综合质量监控与追踪系统
- [质量快照生成](./_reports/QUALITY_SNAPSHOT.json) - 自动化质量数据聚合
- [AI缺陷修复追踪](./_reports/BUGFIX_TODO.md) - 智能缺陷发现与修复生命周期管理
- [覆盖率进展报告](./_reports/COVERAGE_PROGRESS.md) - 测试覆盖率提升历史与分析

---

## 🧪 测试相关文档
- [测试策略主文档](testing/TESTING_STRATEGY.md) - 项目的核心测试策略
- [测试附录索引](testing/README.md) - 包含详细的测试附录文档索引（工具、方法、案例）
- [测试框架说明](../tests/README.md) - 分层测试架构与最佳实践

---

## 📊 智能报告与追踪
- [质量系统访问指南](./_reports/REPORTS_ACCESS_GUIDE.md) - 🆕 统一报告系统使用说明
- [覆盖率修复计划](./_reports/COVERAGE_FIX_PLAN.md) - 提升覆盖率的阶段性目标与执行方案
- [持续修复报告](./_reports/CONTINUOUS_FIX_REPORT_latest.md) - AI驱动修复效果统计
- [Bug 自动修复闭环流程图](./BUGFIX_CYCLE_OVERVIEW.md) - 展示自动化 Bug 修复循环机制
- [报告索引](./_reports/README.md) - 汇总所有报告型文档的索引

---

## 🤖 AI 驱动改进
- [AI 集成改进风险评估](./AI_INTEGRATION_RISKS.md) - 解释为什么必须采用分阶段策略来引入 AI 改进
- [AI 集成改进实施计划](./AI_IMPROVEMENT_PLAN.md) - 分阶段列出具体的执行目标和任务
- [自动化测试生成器](../scripts/generate_tests.py) - 基于覆盖率的智能测试生成工具
- [质量快照生成器](../scripts/generate_quality_snapshot.py) - 🆕 统一质量数据收集脚本

---

## ⚙️ 开发规范与 CI/CD
- [Staging 环境验证](./STAGING_VALIDATION.md) - 上线前的全链路验证步骤
- [监控与告警配置](./MONITORING_SETUP.md) - Prometheus/Grafana 等监控体系设置
- [部署彩排演练流程](./STAGING_DEPLOYMENT_REHEARSAL.md) - 上线前的彩排部署演练流程
- [CI/CD 守护机制说明](./CI_GUARDIAN.md) - 防止低质量代码进入主分支的机制

---

## 🏗️ 架构与运维
- [architecture/](architecture/) 架构与设计
- [how-to/](how-to/) 使用指南
- [reference/](reference/) API 与配置参考
- [data/](data/) 数据采集与设计
- [ml/](ml/) 特征工程与模型
- [ops/](ops/) 部署与运维
- [release/](release/) 发布与变更
- [staging/](staging/) 上线前预演
- [reference/glossary.md](reference/glossary.md) 术语表

---

## 📌 使用说明
- 所有文档均采用 Markdown 编写，支持 GitHub / VS Code 渲染
- 质量系统支持自动化生成和更新，相关脚本位于 `scripts/` 目录
- 更新文档时请保持索引同步，避免遗漏
- 质量数据可通过 `make quality-dashboard` 命令统一查看

### 🚀 快速导航
- **新用户**: 查看 [README.md](../README.md) 快速开始
- **质量状态**: 查看 [质量仪表板](./_reports/TEST_COVERAGE_KANBAN.md)
- **开发者**: 查看 [开发规范](./AI_IMPROVEMENT_PLAN.md) 和 [测试策略](testing/TESTING_STRATEGY.md)
- **运维人员**: 查看 [部署指南](ops/) 和 [监控配置](./MONITORING_SETUP.md)

---

*最后更新: 2025-09-28 | 🤖 AI质量系统升级完成*