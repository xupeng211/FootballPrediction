# AI 开发工作流规则

## 🤖 Claude Code 工作流交互规则

本文档定义了 Claude Code 与项目工作流系统交互的具体规则。

## 📋 必须执行的工作流交互

### 1. 代码提交前

```yaml
Claude Code 必须执行：
  - make prepush
  - 或 ./ci-verify.sh

触发条件：
  - 每次代码提交前
  - 修改重要文件后
  - 创建PR前
```

### 2. 理解CI失败

```yaml
当CI失败时：
  1. 查看 GitHub Actions 中的 Issue Tracker 工作流
  2. 阅读自动创建的 Issue
  3. Issue 包含：
     - 失败的具体步骤
     - 错误日志链接
     - 修复建议
  4. 修复后：
     - 推送新代码
     - CI自动重新运行
     - Issue自动关闭
```

### 3. MLOps交互

```yaml
当收到MLOps Issue时：
  1. Issue类型说明：
     - "模型性能下降" → 检查数据质量
     - "数据质量问题" → 检查数据源
     - "需要重训练" → 可手动触发MLOps
  2. 手动触发MLOps：
     - GitHub Actions → MLOps → Run workflow
     - 选择相应任务
```

## 🔄 工作流触发时机

### 自动触发（无需Claude操作）

- `CI Pipeline` - push到main/develop/hotfix/**
- `Deploy` - CI成功后自动
- `MLOps` - 每日8:00 UTC
- `Project Sync` - PR关闭时
- `Project Maintenance` - 每周一凌晨
- `Issue Tracker` - CI/MLOps失败时

### 手动触发（Claude可操作）

```yaml
可以手动触发的情况：
  1. MLOps - 需要立即检查模型
  2. Issue Tracker - 需要手动创建Issue
  3. Project Sync - 需要同步看板
  4. Project Maintenance - 需要紧急维护
```

## 📝 Claude Code 开发检查清单

### 修改代码后

- [ ] 运行 `make prepush`
- [ ] 检查是否通过所有测试
- [ ] 确认代码覆盖率不低于80%
- [ ] 检查格式化和类型检查
- [ ] 提交代码

### 提交后

- [ ] 查看GitHub Actions状态
- [ ] 如有失败，查看Issue Tracker
- [ ] 修复问题（如有）
- [ ] 确认Issue自动关闭

### 处理Issue

- [ ] 阅读Issue详情
- [ ] 理解失败原因
- [ ] 修复代码
- [ ] 推送修复
- [ ] 验证自动关闭

## 🎯 常见场景处理指南

### 场景1：添加新功能

```yaml
步骤：
  1. 理解需求
  2. 编写代码
  3. 编写测试
  4. make prepush
  5. git提交（触发CI）
  6. CI成功后自动部署
  7. PR合并后看板自动更新
```

### 场景2：修复Bug

```yaml
步骤：
  1. 查看Issue Tracker的Issue
  2. 复现问题
  3. 修复代码
  4. 添加回归测试
  5. make prepush
  6. 提交修复
  7. Issue自动关闭
```

### 场景3：模型优化

```yaml
步骤：
  1. MLOps自动检测
  2. 需要优化时自动重训练
  3. 新模型通过CI部署
  4. Claude只需：
     - 监控性能报告
     - 处理异常Issue
```

### 场景4：紧急修复

```yaml
步骤：
  1. 快速修复代码
  2. make prepush
  3. 推送到hotfix分支
  4. CI自动运行
  5. 成功后自动部署
```

## ⚠️ 禁止行为

### Claude Code 不应该

- ❌ 跳过 `make prepush` 直接提交
- ❌ 手动关闭 CI 失败的 Issue
- ❌ 修改生产环境配置
- ❌ 禁用或跳过工作流
- ❌ 直接修改 `.github/workflows/`（除非明确需要）

### 应该做

- ✅ 始终运行本地检查
- ✅ 阅读并理解工作流反馈
- ✅ 及时处理自动创建的 Issue
- ✅ 利用工作流自动化特性
- ✅ 保持与工作流同步

## 📊 工作流性能考虑

### 优化建议

1. **减少不必要的提交**
   - 多个小改动合并为一个提交
   - 使用有意义的提交信息

2. **利用缓存**
   - 工作流自动缓存依赖
   - 避免重复安装

3. **并行执行**
   - 独立任务并行运行
   - 减少总执行时间

## 🔧 故障排除

### CI Pipeline失败

```bash
# 本地调试
make test
make lint
make type-check

# 完整检查
./ci-verify.sh
```

### MLOps问题

```bash
# 手动触发MLOps
GitHub Actions → MLOps → Run workflow
选择：retrain-check 或 model-monitor
```

### Deploy问题

- 检查CI是否成功
- 查看Deploy工作流日志
- 必要时手动触发

## 📞 获取帮助

### 工作流文档

- `docs/ai/CLAUDE_WORKFLOW_GUIDE.md` - Claude专用指南
- `.github/workflows/README.md` - 完整工作流文档
- `CLAUDE.md` - 项目开发指南

### 命令帮助

- `make help` - 查看所有命令
- `make context` - 加载项目上下文

## 💡 核心理念

1. **信任自动化** - 工作流是助手，不是障碍
2. **快速反馈** - 失败是反馈，不是错误
3. **持续改进** - 利用每次失败优化代码
4. **保持同步** - 与工作流保持一致

---

*本文档确保 Claude Code 能够正确理解并有效使用项目的工作流系统。*
