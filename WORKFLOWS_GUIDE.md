# 🔄 GitHub Actions 工作流功能指南

> 本项目共有 **6 个 GitHub Actions 工作流**，覆盖 CI/CD、MLOps、部署、问题跟踪、项目同步和维护等全生命周期

**最后更新**: 2025-10-07

---

## 📋 工作流概览

| 工作流 | 文件名 | 触发方式 | 主要功能 | 状态 |
|--------|--------|----------|----------|------|
| 🔧 **CI 持续集成** | `ci-pipeline.yml` | Push/PR | 代码质量检查、测试、覆盖率 | ✅ 活跃 |
| 🤖 **MLOps 机器学习** | `mlops-pipeline.yml` | 定时/手动/Push | 模型训练、监控、反馈循环 | ✅ 活跃 |
| 🚀 **部署流水线** | `deploy-pipeline.yml` | CI完成后/手动 | 多环境部署、回滚 | ✅ 活跃 |
| 🐛 **问题跟踪** | `issue-tracking-pipeline.yml` | CI失败/手动 | 自动创建 Issue、问题分类 | ✅ 活跃 |
| 🔄 **项目同步** | `project-sync-pipeline.yml` | PR关闭/手动 | Kanban 同步、PR 状态更新 | ✅ 活跃 |
| 🧹 **项目维护** | `project-maintenance-pipeline.yml` | 定时/手动 | 文档更新、清理、统计 | ✅ 活跃 |

---

## 1️⃣ CI 持续集成流水线

**文件**: `.github/workflows/ci-pipeline.yml`
**名称**: CI 持续集成流水线

### 🎯 功能概述

完整的代码质量保证和测试流程，确保每次提交的代码质量。

### 🔔 触发条件

```yaml
# 分支推送
push:
  branches: [main, develop, hotfix/**]

# Pull Request
pull_request:
  branches: [main, develop]
```

### 🏗️ 工作流阶段

#### 阶段 1: 基础检查 (Basic Checks)

- ✅ 检查相关文件是否有变更
- ✅ 智能跳过无关提交（性能优化）
- ⚡ 快速失败机制

#### 阶段 2: 代码质量检查 (Quality Check)

- ✅ **Ruff 代码检查** - 快速 linting
- ✅ **Mypy 类型检查** - 静态类型验证
- ✅ **依赖一致性检查** - 验证 lock 文件

```bash
# 执行的命令
ruff check src/ tests/ --output-format=github
mypy src/ --ignore-missing-imports
make verify-deps
```

#### 阶段 3: 模拟测试覆盖率 (Mocked Coverage)

- ✅ 单元测试（无外部依赖）
- ✅ 覆盖率报告生成
- ✅ 覆盖率阈值验证（80%）
- ✅ 上传到 Codecov

#### 阶段 4: 集成测试 (Integration Tests)

- 🐳 启动测试服务（PostgreSQL + Redis）
- ✅ 数据库集成测试
- ✅ Redis 缓存测试
- ✅ API 端到端测试

#### 阶段 5: 安全扫描 (Security Scan)

- 🔒 依赖漏洞扫描 (pip-audit)
- 🔒 代码安全扫描 (bandit)
- 📊 生成安全报告

### 📊 输出产物

- ✅ 测试报告 (JUnit XML)
- ✅ 覆盖率报告 (HTML + XML)
- ✅ 安全扫描报告
- ✅ 代码质量报告

---

## 2️⃣ MLOps 机器学习流水线

**文件**: `.github/workflows/mlops-pipeline.yml`
**名称**: MLOps 机器学习流水线

### 🎯 功能概述

自动化的机器学习运维流程，包括模型训练、监控、反馈循环和自动重训练。

### 🔔 触发条件

```yaml
# 定时执行（每日早上 8:00 UTC，北京时间 16:00）
schedule:
  - cron: '0 8 * * *'

# 手动触发
workflow_dispatch:
  inputs:
    task: [all, feedback-update, performance-report, retrain-check, model-monitor, cleanup]
    days_back: '30'
    force_retrain: false

# 模型代码变更
push:
  branches: [main]
  paths:
    - 'src/models/**'
    - 'scripts/**'
```

### 🏗️ 工作流阶段

#### 阶段 1: 反馈更新 (Feedback Update)

- 📊 更新预测结果和真实结果对比
- 📈 生成准确率趋势
- 💾 保存到数据库

```bash
# 执行的任务
make feedback-update
```

#### 阶段 2: 性能报告 (Performance Report)

- 📊 生成模型性能报告
- 📈 可视化准确率趋势
- 📉 分析性能下降原因

```bash
# 执行的任务
make performance-report
```

#### 阶段 3: 重训练检查 (Retrain Check)

- 🔍 检查模型性能是否下降
- 🎯 准确率阈值验证
- 🚨 触发重训练决策

```bash
# 执行的任务
make retrain-check
```

#### 阶段 4: 模型监控 (Model Monitor)

- 🏥 模型健康检查
- 📊 性能指标收集
- 🚨 异常告警

```bash
# 执行的任务
make model-monitor
```

#### 阶段 5: 数据清理 (Cleanup)

- 🧹 清理过期预测数据
- 🗄️ 归档历史数据
- 💾 优化存储空间

### 📊 输出产物

- 📈 性能报告 (`reports/generated/model_performance_*.md`)
- 🔄 重训练报告 (`models/retrain_reports/`)
- 📊 监控指标 (MLflow)

### 🔧 使用示例

```bash
# 手动触发完整 MLOps 流程
gh workflow run mlops-pipeline.yml -f task=all

# 仅更新反馈数据
gh workflow run mlops-pipeline.yml -f task=feedback-update

# 强制重训练评估
gh workflow run mlops-pipeline.yml -f task=retrain-check -f force_retrain=true
```

---

## 3️⃣ 部署流水线

**文件**: `.github/workflows/deploy-pipeline.yml`
**名称**: 部署流水线

### 🎯 功能概述

自动化多环境部署，支持 Staging 和 Production 环境，包含回滚机制。

### 🔔 触发条件

```yaml
# CI 完成后自动部署
workflow_run:
  workflows: ["CI 持续集成流水线"]
  types: [completed]
  branches: [main, develop]

# 手动部署
workflow_dispatch:
  inputs:
    environment: [staging, production]
```

### 🏗️ 工作流阶段

#### 阶段 1: 确定环境 (Determine Environment)

- 🎯 根据分支和输入确定部署环境
- ✅ main → staging
- ✅ 手动选择 → staging/production

#### 阶段 2: 准备部署 (Prepare Deployment)

- 🔐 验证必需的 secrets
- 🏷️ 生成 Git SHA 标签
- ✅ 健康检查

**必需的 Secrets**:

```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
DATABASE_URL
REDIS_URL
SECRET_KEY
```

#### 阶段 3: 构建 Docker 镜像 (Build Docker Image)

- 🐳 多阶段 Docker 构建
- 🏷️ 使用 Git SHA 标签
- 📦 推送到 GitHub Container Registry

```bash
# 构建命令
docker build --target production \
  --tag ghcr.io/${{ github.repository }}:${{ github.sha }} \
  --tag ghcr.io/${{ github.repository }}:latest
```

#### 阶段 4: 部署到 Staging (Deploy to Staging)

- 🚀 部署到 Staging 环境
- ✅ 运行冒烟测试
- 📊 验证健康检查

#### 阶段 5: 部署到 Production (Deploy to Production)

- 🔒 需要手动审批
- 🚀 蓝绿部署
- 🔄 自动回滚机制

#### 阶段 6: 健康检查 (Health Check)

- 🏥 验证服务健康
- 📊 检查关键指标
- 🚨 失败时自动回滚

### 📊 部署策略

| 环境 | 分支 | 审批 | 回滚 |
|------|------|------|------|
| **Staging** | main/develop | 自动 | 自动 |
| **Production** | main | 手动 | 自动 |

### 🔧 使用示例

```bash
# 部署到 Staging
gh workflow run deploy-pipeline.yml -f environment=staging

# 部署到 Production（需要审批）
gh workflow run deploy-pipeline.yml -f environment=production

# 回滚到指定版本
make rollback TAG=abc1234
```

---

## 4️⃣ 问题跟踪流水线

**文件**: `.github/workflows/issue-tracking-pipeline.yml`
**名称**: 问题跟踪流水线

### 🎯 功能概述

自动化问题管理，CI 失败时自动创建 Issue，并进行智能分类。

### 🔔 触发条件

```yaml
# CI 失败时
workflow_run:
  workflows: ["CI Pipeline"]
  types: [completed]

# MLOps 检测到问题
workflow_run:
  workflows: ["MLOps"]
  types: [completed]

# 手动创建
workflow_dispatch:
  inputs:
    issue_type: [bug, enhancement, task, question]
    title: "Issue title"
    description: "Issue description"
```

### 🏗️ 工作流功能

#### 功能 1: 跟踪 CI 失败 (Track CI Failures)

- 🔍 分析 CI 失败原因
- 📝 自动创建详细 Issue
- 🏷️ 自动添加标签

**创建的 Issue 包含**:

- ❌ 失败的 Job 名称
- ❌ 失败的 Step 名称
- 🔗 运行日志链接
- 📝 失败日志摘要
- 🏷️ 标签: `ci-failure`, `auto-created`

#### 功能 2: 跟踪 MLOps 问题 (Track MLOps Issues)

- 📉 模型性能下降告警
- 🔍 数据质量问题
- 🚨 重训练失败通知

#### 功能 3: 智能问题分类 (Issue Classification)

- 🤖 自动分类问题类型
- 🏷️ 添加相关标签
- 👤 自动分配负责人

#### 功能 4: 重复问题检测 (Duplicate Detection)

- 🔍 检查是否有相似 Issue
- 🔗 关联重复 Issue
- 📊 更新现有 Issue

### 📊 Issue 分类

| 类型 | 标签 | 优先级 | 自动分配 |
|------|------|--------|----------|
| CI 失败 | `ci-failure`, `bug` | High | CI 维护者 |
| 模型性能下降 | `mlops`, `performance` | High | ML 工程师 |
| 测试失败 | `test-failure` | Medium | QA 团队 |
| 依赖问题 | `dependencies` | Low | DevOps |

---

## 5️⃣ 项目同步流水线

**文件**: `.github/workflows/project-sync-pipeline.yml`
**名称**: 项目同步流水线

### 🎯 功能概述

保持项目看板、PR 状态和文档同步，确保项目管理的一致性。

### 🔔 触发条件

```yaml
# PR 关闭时
pull_request:
  types: [closed]

# 手动触发
workflow_dispatch:
  inputs:
    task: [kanban, pr-update, issue-sync]
```

### 🏗️ 工作流功能

#### 功能 1: Kanban 同步 (Kanban Synchronization)

- 📊 PR 关闭时更新看板状态
- ✅ 完成的任务移到 Done 列
- 🔄 同步 Issue 状态

```bash
# 执行的脚本
python scripts/kanban_audit.py \
  --repo ${{ github.repository }} \
  --pr-number $PR_NUMBER \
  --update-kanban
```

#### 功能 2: PR 状态更新 (PR Status Update)

- 📝 更新 PR 描述
- ✅ 检查 PR 完成度
- 🏷️ 更新标签

#### 功能 3: Issue 同步 (Issue Sync)

- 🔄 双向同步 Issue 状态
- 📊 更新看板
- 🔗 关联相关 Issue

### 📊 Kanban 列

```
📋 Backlog → 🚀 To Do → 🏗️ In Progress → ✅ Done
```

---

## 6️⃣ 项目维护流水线

**文件**: `.github/workflows/project-maintenance-pipeline.yml`
**名称**: 项目维护流水线

### 🎯 功能概述

定期维护项目，更新文档、清理数据、生成统计报告。

### 🔔 触发条件

```yaml
# 定时执行（每周一凌晨 2 点 UTC）
schedule:
  - cron: "0 2 * * 1"

# 手动触发
workflow_dispatch:
  inputs:
    task: [all, docs, cleanup, stats, archive]
```

### 🏗️ 工作流功能

#### 功能 1: 文档更新 (Update Documentation)

- 📚 生成 API 文档
- 📊 更新 README 统计
- 👥 更新贡献者列表
- 📝 生成 CHANGELOG

```bash
# 执行的脚本
python scripts/generate_api_docs.py
python scripts/update_readme_stats.py
python scripts/update_contributors.py
python scripts/generate_changelog.py --days 7
```

#### 功能 2: 数据清理 (Cleanup)

- 🧹 清理旧日志文件
- 🗄️ 归档测试报告
- 💾 优化存储空间
- 🔄 清理 Docker 缓存

**清理规则**:

- 日志文件: 保留 30 天
- 测试报告: 保留 90 天
- 覆盖率报告: 保留 180 天

#### 功能 3: 统计报告 (Statistics)

- 📊 生成项目统计
- 📈 代码增长趋势
- 👥 贡献者活跃度
- 🧪 测试覆盖率历史

**生成的报告**:

```
docs/_reports/
├── weekly_stats.md
├── code_quality_trends.md
└── contributor_activity.md
```

#### 功能 4: 归档 (Archive)

- 📦 归档旧分支
- 🗄️ 归档关闭的 Issue
- 📚 归档文档版本

---

## 🔧 工作流管理

### 查看工作流状态

```bash
# 列出所有工作流
gh workflow list

# 查看特定工作流运行
gh run list --workflow=ci-pipeline.yml

# 查看运行详情
gh run view <run-id>
```

### 手动触发工作流

```bash
# CI 流水线
gh workflow run ci-pipeline.yml

# MLOps 流水线（完整）
gh workflow run mlops-pipeline.yml -f task=all -f days_back=30

# 部署到 Staging
gh workflow run deploy-pipeline.yml -f environment=staging

# 项目维护（仅文档更新）
gh workflow run project-maintenance-pipeline.yml -f task=docs
```

### 查看工作流日志

```bash
# 查看最新运行日志
gh run view --log

# 下载日志
gh run download <run-id>
```

---

## 📊 工作流统计

### 执行频率

| 工作流 | 自动执行 | 平均时长 | 成功率 |
|--------|----------|----------|--------|
| CI | 每次 Push/PR | ~5-8 分钟 | 95%+ |
| MLOps | 每天 1 次 | ~15-20 分钟 | 90%+ |
| 部署 | CI 完成后 | ~10-15 分钟 | 98%+ |
| 问题跟踪 | CI/MLOps 失败时 | ~1-2 分钟 | 99%+ |
| 项目同步 | PR 关闭时 | ~2-3 分钟 | 98%+ |
| 项目维护 | 每周 1 次 | ~5-10 分钟 | 95%+ |

---

## 🚨 常见问题

### Q1: CI 流水线失败了怎么办？

**A**:

1. 查看失败的 Job 和 Step
2. 检查自动创建的 Issue
3. 本地运行 `make prepush` 复现问题
4. 修复后重新提交

### Q2: 如何跳过 CI 检查？

**A**:

```bash
# 在提交信息中添加 [skip ci]
git commit -m "docs: update README [skip ci]"
```

**⚠️ 注意**: 仅用于文档更新等非代码变更

### Q3: 如何回滚部署？

**A**:

```bash
# 方式1: 使用 Makefile
make rollback TAG=<git-sha>

# 方式2: 手动触发部署流水线
gh workflow run deploy-pipeline.yml -f environment=production
```

### Q4: MLOps 流水线如何手动触发重训练？

**A**:

```bash
gh workflow run mlops-pipeline.yml \
  -f task=retrain-check \
  -f force_retrain=true
```

---

## 🎯 最佳实践

### 1. 提交代码前

```bash
# 本地运行完整验证
make prepush

# 或运行本地 CI 模拟
./ci-verify.sh
```

### 2. 部署到生产环境

1. ✅ 确保 CI 通过
2. ✅ 在 Staging 测试
3. ✅ 检查 MLOps 报告
4. ✅ 手动触发 Production 部署
5. ✅ 监控健康检查

### 3. 处理 CI 失败

1. 📧 查看邮件通知
2. 🔍 检查自动创建的 Issue
3. 💻 本地复现问题
4. 🔧 修复并验证
5. 📤 重新提交

---

## 📚 相关文档

- 📖 **CI/CD 配置**: `.github/workflows/`
- 📖 **Makefile 命令**: 运行 `make help`
- 📖 **优化指南**: `OPTIMIZATION_QUICKSTART.md`
- 📖 **项目说明**: `README.md`

---

## 🔄 更新日志

| 日期 | 变更 |
|------|------|
| 2025-10-07 | 🎉 创建工作流功能指南 |
| 2025-10-07 | ✅ 重命名工作流为英文 |

---

**维护者**: DevOps Team
**更新频率**: 每次工作流变更后更新
**反馈**: 通过 Issue 提交建议
