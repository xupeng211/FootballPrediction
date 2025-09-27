# 📚 项目文档总索引

本目录作为项目的文档总入口，帮助开发者快速导航到不同类别的文档。
文档分为三个主要部分：**测试策略**、**问题报告与修复闭环**、**AI 改进计划**。

---

## 🧪 测试相关文档
- [测试策略主文档](testing/TESTING_STRATEGY.md) - 项目的核心测试策略
- [测试附录索引](testing/README.md) - 包含详细的测试附录文档索引（工具、方法、案例）

---

## 📊 报告与修复机制
- [测试覆盖率看板](./_reports/TEST_COVERAGE_KANBAN.md) - 展示覆盖率任务进展
- [Bugfix TODO 列表](./_reports/BUGFIX_TODO.md) - 自动记录测试失败和低覆盖率点
- [Bug 自动修复闭环流程图](./BUGFIX_CYCLE_OVERVIEW.md) - 展示自动化 Bug 修复循环机制
- [报告索引](./_reports/README.md) - 汇总所有报告型文档的索引

---

## 🤖 AI 集成改进
- [AI 集成改进风险评估](./AI_INTEGRATION_RISKS.md) - 解释为什么必须采用分阶段策略来引入 AI 改进
- [AI 集成改进实施计划](./AI_IMPROVEMENT_PLAN.md) - 分阶段列出具体的执行目标和任务

---

## 📌 使用说明
- 所有文档均采用 Markdown 编写，支持 GitHub / VS Code 渲染。
- 更新文档时请保持索引同步，避免遗漏。

---

## 📁 完整文档结构
- [architecture/](architecture/) 架构与设计
- [how-to/](how-to/) 使用指南
- [reference/](reference/) API 与配置参考
- [testing/](testing/) 测试策略与报告
- [data/](data/) 数据采集与设计
- [ml/](ml/) 特征工程与模型
- [ops/](ops/) 部署与运维
- [release/](release/) 发布与变更
- [staging/](staging/) 上线前预演
- [reference/glossary.md](reference/glossary.md) 术语表

---

*最后更新: 2025-09-27*