# 🧭 测试改进机制指南 (Test Improvement Guide)

## 1. 背景

本项目的测试套件存在结构性问题，因此引入了 Kanban + CI Hook + 周报三层机制来持续优化。

**初始问题**：
- 整体覆盖率：66%（低于目标 80%）
- 自动生成测试占比：67%（质量较低）
- 44 个文件存在大量 ImportError 跳过
- 关键模块（ai/, scheduler/, services/）缺乏测试

**目标**：
- 保持测试覆盖率稳步提升
- 保证每次提交的质量
- 形成透明的改进闭环
- 建立可持续的测试文化

## 2. Kanban 看板

### 2.1 文件位置
```
docs/_reports/TEST_OPTIMIZATION_KANBAN.md
```

### 2.2 功能结构
Kanban 看板分为三个阶段，跟踪测试优化任务：

- **Phase 1**: 短期修复（语法错误、清理、配置）
- **Phase 2**: 结构优化（关键模块测试、目录重组）
- **Phase 3**: 长期质量建设（覆盖率门控、性能测试、自动化）

### 2.3 使用方法

#### 任务状态管理
1. **TODO**: 待办任务，新发现的问题立即添加到对应 Phase
2. **In Progress**: 正在执行的任务，从 TODO 移动过来
3. **Done**: 已完成的任务，必须：
   - 打上 ✅ 标记
   - 写上完成日期（格式：`✅ 2025-01-01`）

#### 状态流转规则
```
TODO → In Progress → Done
```

#### 任务更新要求
- 每次 AI 工具或开发者执行任务时，**必须**更新 Kanban 状态
- 新发现的问题，**必须**立即添加到对应 Phase 的 TODO
- 任务完成后，**必须**移动到 Done 并标记完成

## 3. CI Hook 守护

### 3.1 本地 pre-commit hook

#### 文件路径
```
.git/hooks/pre-commit
```

#### 功能
- 阻止未更新 Kanban 文件的提交
- 提供清晰的错误提示（中文）
- 确保本地开发规范

#### 启用方法
```bash
make setup-hooks
```

#### 错误示例
```bash
❌ 提交被阻止: 未更新 docs/_reports/TEST_OPTIMIZATION_KANBAN.md
👉 请在提交前更新 Kanban 文件，保持任务进度一致
```

### 3.2 GitHub Actions 守护

#### 文件路径
```
.github/workflows/kanban-check.yml
```

#### 核心功能
- 每次 push/PR 检查 Kanban 是否更新
- 多层缓存优化：
  - 缓存 `.git/hooks` 目录（避免重复 chmod）
  - 缓存 Kanban 文件 hash（内容变化时重新验证）
- 彩色日志输出（✅/❌ 状态提示）
- 智能跳过逻辑（缓存命中时跳过检查）

#### 缓存策略
```yaml
# 多路径缓存
path: |
  .git/hooks
  docs/_reports/TEST_OPTIMIZATION_KANBAN.md
key: kanban-check-${{ hashFiles('.git/hooks/*', 'docs/_reports/TEST_OPTIMIZATION_KANBAN.md') }}
```

#### 输出示例
```bash
⚡ Cache hit: true (hooks & Kanban 文件已缓存)
✅ 📋 Kanban 未变，跳过检查
📋 缓存命中，无需重复验证
```

### 3.3 检查失败报告

#### 文件路径
```
docs/_reports/KANBAN_CHECK_REPORT.md
```

#### 生成时机
在 CI 检查失败时**自动生成**

#### 报告内容
```markdown
# 📋 Kanban 文件检查报告

**生成时间**: 2025-01-01 12:00:00 UTC
**CI 运行编号**: 123456
**提交 SHA**: abcdef1234567890

## 🚨 检查结果
- 状态: ❌ 失败
- 原因: Kanban 文件未更新

## 📂 文件路径
- docs/_reports/TEST_OPTIMIZATION_KANBAN.md

## 📌 提示
👉 每次提交必须同步更新 Kanban 文件，以保持任务进度与代码一致。
```

#### 失败原因分类
- `Kanban 文件缺失`：看板文件不存在
- `Kanban 文件未更新`：提交未包含看板变更

## 4. 周报机制

### 4.1 定时任务配置

#### 文件路径
```
.github/workflows/kanban-history.yml
```

#### 触发方式
- **定时执行**：每周一 02:00 UTC
- **手动触发**：支持 GitHub Actions 手动运行

### 4.2 功能流程

#### 扫描阶段
- 查找所有 `KANBAN_CHECK_REPORT*.md` 文件
- 按时间倒序排列
- 提取关键信息：时间、CI编号、提交SHA、失败原因

#### 汇总生成
- 将所有报告合并到历史文件
- 按日期分组显示
- 自动添加分隔线

#### 自动提交
- 有变化时自动提交到主分支
- 标准化提交信息：`chore(report): update KANBAN_HISTORY.md (weekly summary)`
- 无变化时跳过提交

### 4.3 历史汇总格式

#### 文件路径
```
docs/_reports/KANBAN_HISTORY.md
```

#### 内容示例
```markdown
# 🗂️ Kanban 检查历史汇总

**最后更新**: 2025-01-08 02:00:00 UTC

## 2025-01-07
- 状态: ❌ 失败
- 原因: Kanban 文件未更新
- 提交 SHA: abc1234
- CI 运行编号: 987654

---

## 2025-01-05
- 状态: ❌ 失败
- 原因: Kanban 文件缺失
- 提交 SHA: def5678
- CI 运行编号: 123456
```

## 5. 开发者操作指南

### 5.1 标准工作流程

#### 1. 任务选择
```bash
# 1. 查看当前项目状态
make context

# 2. 阅读 Kanban 看板
cat docs/_reports/TEST_OPTIMIZATION_KANBAN.md

# 3. 选择 TODO 任务，标记为 In Progress
```

#### 2. 开发执行
- 执行选定的任务
- 确保代码质量（运行 `make prepush`）
- 测试通过后准备提交

#### 3. 状态更新
```bash
# 更新 Kanban 文件
# 将任务从 In Progress 移动到 Done
# 添加 ✅ 和完成日期
```

#### 4. 提交代码
```bash
# 启用 hooks（如果未启用）
make setup-hooks

# 提交代码
git add .
git commit -m "fix: 完成某测试优化任务"
git push
```

### 5.2 CI 失败处理

#### 1. 查看失败报告
```bash
# 查看自动生成的失败报告
cat docs/_reports/KANBAN_CHECK_REPORT.md
```

#### 2. 问题分析
- 确认失败原因（文件缺失 vs 未更新）
- 检查提交是否包含 Kanban 变更

#### 3. 修复流程
```bash
# 1. 更新 Kanban 文件
git add docs/_reports/TEST_OPTIMIZATION_KANBAN.md

# 2. 重新提交
git commit --amend --no-edit
git push
```

### 5.3 最佳实践

#### 任务管理
- **小批量**: 每次提交专注于 1-2 个任务
- **及时更新**: 完成任务立即更新 Kanban
- **清晰描述**: 任务描述要具体可执行

#### 质量保证
- **本地验证**: 提交前运行 `make prepush`
- **CI 监控**: 关注 CI 执行状态
- **快速响应**: CI 失败后立即修复

#### 团队协作
- **透明可见**: 所有任务进度公开可见
- **持续改进**: 定期回顾和优化流程
- **知识共享**: 新人需要熟悉这套机制

## 6. 长期目标

### 6.1 覆盖率目标
- **整体覆盖率**: ≥ 80%（当前 66%）
- **关键路径覆盖率**: 100%
- **单元测试覆盖率**: ≥ 85%
- **集成测试覆盖率**: ≥ 70%

### 6.2 质量目标
- **测试债务**: 定期清理，保持技术债务可控
- **自动化程度**: 减少手动测试，提高自动化覆盖率
- **测试稳定性**: 减少flaky测试，提高可靠性

### 6.3 透明度目标
- **进度可视化**: Kanban 看板实时反映进展
- **历史可追溯**: 周报记录历史趋势
- **问题可追踪**: 失败报告提供详细诊断信息

### 6.4 文化目标
- **质量意识**: 团队成员重视测试质量
- **持续改进**: 形成测试优化的良性循环
- **规范习惯**: 养成按流程操作的习惯

## 7. 维护和演进

### 7.1 定期回顾
- 每月回顾机制执行效果
- 收集团队反馈，优化流程
- 调整目标和优先级

### 7.2 工具改进
- 根据需要优化 CI 流程
- 增强报告的可读性和实用性
- 探索新的测试优化工具

### 7.3 文档更新
- 及时更新本指南
- 保持操作说明的准确性
- 添加新的最佳实践

---

**最后更新**: 2025-01-01

*本文档是测试改进机制的核心指南，请所有团队成员仔细阅读并遵循执行。如有疑问，请及时提出讨论。*