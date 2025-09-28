# 🔄 CI/CD 持续 Bug 修复循环工作流

本文档说明如何在项目的 CI/CD pipeline 中使用每日自动运行的持续 Bug 修复循环。

## 📋 概述

已配置的 GitHub Actions 工作流会自动运行 AI 增强的持续 Bug 修复循环，帮助保持代码质量。

## ⏰ 调度配置

### 自动执行
- **时间**: 每天凌晨 2:00 UTC (北京时间 10:00)
- **频率**: 每日执行
- **循环次数**: 3 次
- **超时**: 60 分钟

### 手动触发
工作流支持手动触发，可以自定义循环次数：
```bash
# 使用默认 3 次循环
gh workflow run continuous_bugfix.yml

# 自定义循环次数
gh workflow run continuous_bugfix.yml -f max_iterations=5
```

## 🚀 工作流详情

### 文件位置
`.github/workflows/continuous_bugfix.yml`

### 执行步骤
1. **环境设置** - Python 3.11 + 依赖缓存
2. **依赖安装** - `make install` + `make env-check`
3. **项目上下文** - `make context`
4. **持续循环** - `python scripts/continuous_bugfix.py --max-iterations 3`
5. **报告上传** - 所有报告和日志作为 artifacts
6. **总结生成** - GitHub Actions 步骤摘要

## 📊 输出产物

### 报告 Artifacts
- **bugfix-reports**: 包含核心报告文件（14天保留）
  - `CONTINUOUS_FIX_REPORT_*.md` - 循环执行记录
  - `BUGFIX_TODO.md` - AI 修复建议
  - `TEST_QUALITY_REPORT.md` - 测试质量报告

### 日志 Artifacts
- **bugfix-logs-${run_number}**: 包含执行日志（7天保留）
  - `logs/` - 应用日志
  - `pytest_failures.log` - 测试失败日志
  - `coverage.json` - 覆盖率数据

### 长期归档分支
- **bugfix-reports 分支**: 永久保存所有报告文件
  - 报告文件会被复制到分支根目录
  - 支持历史追踪和长期存储
  - 使用 `[skip ci]` 避免递归触发

### 保留策略
- **短期 Artifacts**: 14天（报告）/ 7天（日志）
- **长期归档**: 永久（archive branch）

## 🔧 本地测试

在提交到 CI 前，可以本地测试工作流：

```bash
# 运行单个循环
python scripts/continuous_bugfix.py --max-iterations 1

# 使用便捷脚本
./scripts/run_continuous_loop.sh 3

# 完整 CI 模拟
./ci-verify.sh
```

## 📈 监控和维护

### 查看执行历史
```bash
gh run list --workflow=continuous_bugfix.yml
```

### 下载 Artifacts
```bash
# 下载最新的报告
gh run download --workflow=continuous_bugfix.yml --name="bugfix-reports"

# 下载最新的日志
gh run download --workflow=continuous_bugfix.yml --name="bugfix-logs-*"

# 查看归档分支
git checkout bugfix-reports
git log --oneline -10
```

### 监控关键指标
工作流会自动在 GitHub Actions 摘要中显示：
- 最新 BUGFIX_TODO 内容
- 连续循环执行摘要
- 高优先级修复建议警告

## ⚠️ 注意事项

1. **非阻塞执行**: 工作流配置为 `continue-on-error: true`，确保即使部分失败也能完成
2. **资源限制**: 60 分钟超时防止长时间运行
3. **存储成本**: Artifacts 有保留期限，重要报告需要及时下载
4. **安全考虑**: 工作流只读执行，不会自动推送代码修改

## 🎯 最佳实践

### 开发者流程
1. **每日检查**: 查看自动生成的 BUGFIX_TODO 报告
2. **定期审查**: 下载并分析连续执行报告
3. **手动触发**: 在重要变更后手动触发工作流
4. **反馈优化**: 基于执行结果优化测试和修复策略

### CI/CD 集成
- 与现有的 CI 流程并行运行
- 不影响正常的 PR 检查和合并流程
- 提供额外的质量保证层

## 🔗 相关链接

- [GitHub Actions 文档](https://docs.github.com/en/actions)
- [AI 增强修复系统](../src/ai/README.md)
- [持续修复脚本](../scripts/continuous_bugfix.py)

---
*此文档由 CI/CD 工作流自动生成*