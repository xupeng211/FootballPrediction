# CI/CD 清理集成说明

本文档说明如何在 CI/CD 流水线中集成项目清理任务。

## 📋 集成概述

我们在以下两个 GitHub Actions 工作流中集成了自动清理功能：

### 1. **主 CI 流水线** (`ci.yml`)

**触发时机**: 每次 push 或 pull request 到 `main` 或 `develop` 分支

**清理步骤**: 在测试完成后、上传构建产物前执行

```yaml
- name: Clean temporary files before upload
  if: always()
  run: |
    # Keep only necessary artifacts, clean temporary files
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    rm -f *_SUMMARY.md *_REPORT*.md 2>/dev/null || true
    echo "✅ Temporary files cleaned, keeping test artifacts"
```

**作用**:
- 清理 Python 缓存文件 (`__pycache__/`, `*.pyc`)
- 删除临时报告文件 (`*_SUMMARY.md`, `*_REPORT*.md`)
- 保留必要的测试产物 (`htmlcov/`, `coverage.xml`, `bandit-report.json`)
- 减少上传的构建产物大小

**优势**:
- ✅ 减少 GitHub Actions 存储空间占用
- ✅ 加快构建产物上传速度
- ✅ 保持工作区整洁
- ✅ 不影响测试结果和覆盖率报告

---

### 2. **项目维护流水线** (`项目维护流水线.yml`)

**触发时机**:
- 定时任务: 每周一凌晨 2:00 (UTC)
- 手动触发: 通过 GitHub Actions 界面

**清理步骤**: 作为维护任务的一部分

```yaml
- name: Clean project temporary files
  run: |
    # Use Makefile clean-temp command
    make clean-temp || true

    # Additional cleanup for CI-specific files
    find . -type f -name "*.log" -mtime +30 -delete 2>/dev/null || true
    find logs/ -type f -mtime +90 -delete 2>/dev/null || true

    echo "📊 Cleanup Summary:"
    echo "- Removed temporary report files"
    echo "- Cleaned Python cache files"
    echo "- Removed old log files (>30 days)"
```

**作用**:
- 执行 `make clean-temp` 命令进行标准清理
- 删除超过 30 天的日志文件
- 删除超过 90 天的 logs 目录下的文件
- 提供清理摘要报告

**优势**:
- ✅ 定期自动清理，无需手动干预
- ✅ 防止项目中积累过多临时文件
- ✅ 维护项目健康和整洁
- ✅ 与 Makefile 命令保持一致

---

## 🚀 使用方法

### 自动执行（推荐）

清理任务会在以下情况自动执行：

1. **每次 CI 运行**:
   - 推送代码到 `main` 或 `develop` 分支
   - 创建或更新 Pull Request

2. **每周定期维护**:
   - 每周一凌晨 2:00 UTC 自动运行
   - 包含完整的项目清理和维护任务

### 手动触发

可以通过 GitHub Actions 界面手动触发维护流水线：

1. 访问 GitHub 仓库的 **Actions** 标签页
2. 选择 **项目维护流水线** workflow
3. 点击 **Run workflow** 按钮
4. 选择清理任务类型：
   - `all`: 运行所有维护任务
   - `cleanup`: 仅运行清理任务
   - `docs`: 仅更新文档
   - `stats`: 仅生成统计
   - `archive`: 仅归档报告

### 本地测试

在推送前，可以本地测试清理命令：

```bash
# 测试清理命令
make clean-temp

# 查看帮助信息
make help | grep Clean
```

---

## 📊 清理内容详细列表

### CI 流水线清理内容

| 项目 | 模式 | 说明 |
|------|------|------|
| Python 缓存目录 | `__pycache__/` | 递归删除所有缓存目录 |
| Python 字节码 | `*.pyc` | 删除所有编译缓存文件 |
| 临时 Summary | `*_SUMMARY.md` | 删除临时摘要文档 |
| 临时 Report | `*_REPORT*.md` | 删除临时报告文档 |

### 维护流水线清理内容

| 项目 | 规则 | 说明 |
|------|------|------|
| 覆盖率报告 | `htmlcov/`, `htmlcov_60_plus/` | 删除 HTML 覆盖率报告 |
| 覆盖率数据 | `coverage.xml`, `coverage.json` | 删除覆盖率数据文件 |
| 安全扫描报告 | `bandit_report.json` | 删除安全扫描结果 |
| Python 缓存 | 所有 `__pycache__/` 和 `*.pyc` | 全面清理 |
| 旧日志文件 | 超过 30 天的 `*.log` | 删除过期日志 |
| logs 目录 | 超过 90 天的文件 | 清理旧日志 |

---

## 🔧 配置说明

### 调整清理策略

如果需要调整清理策略，可以修改以下文件：

1. **Makefile** (`clean-temp` 目标):
   ```makefile
   clean-temp: ## Clean: Remove temporary reports and generated files
       @echo "$(YELLOW)Cleaning temporary files...$(RESET)" && \
       rm -rf htmlcov/ htmlcov_60_plus/ coverage.xml coverage.json && \
       rm -f *_SUMMARY.md *_REPORT*.md bandit_report.json && \
       find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
       find . -type f -name "*.pyc" -delete && \
       echo "$(GREEN)✅ Temporary files cleanup completed$(RESET)"
   ```

2. **CI workflow** (`.github/workflows/ci.yml`):
   - 修改 "Clean temporary files before upload" 步骤

3. **维护 workflow** (`.github/workflows/项目维护流水线.yml`):
   - 修改 "Clean project temporary files" 步骤

### 调整定时任务频率

修改 `项目维护流水线.yml` 中的 cron 表达式：

```yaml
schedule:
  - cron: '0 2 * * 1'  # 每周一凌晨 2 点 UTC
```

常用 cron 表达式：
- `0 2 * * 1`: 每周一凌晨 2:00
- `0 2 * * *`: 每天凌晨 2:00
- `0 2 1 * *`: 每月 1 号凌晨 2:00
- `0 2 1 */3 *`: 每季度第一天凌晨 2:00

---

## 📈 监控和验证

### 查看清理执行结果

1. **查看 CI 运行日志**:
   - 进入 GitHub Actions 标签页
   - 选择对应的 workflow run
   - 查看 "Clean temporary files before upload" 步骤的日志

2. **查看维护报告**:
   - 每周维护完成后会自动创建 Issue
   - Issue 标题: "📋 Weekly Maintenance Report"
   - 标签: `maintenance`, `weekly-report`

### 验证清理效果

```bash
# 本地验证
make clean-temp

# 检查工作区状态
git status

# 查看目录大小变化
du -sh .
```

---

## 🛡️ 安全考虑

### 保护的文件

以下文件/目录**不会被清理**：

- ✅ 源代码 (`src/`, `tests/`)
- ✅ 配置文件 (`.env`, `*.yml`, `*.toml`)
- ✅ 文档 (`docs/`, `*.md`)
- ✅ Git 仓库 (`.git/`)
- ✅ 虚拟环境 (`.venv/`, `venv/`)
- ✅ CI 必需的构建产物 (`htmlcov/`, `coverage.xml` 在上传前)

### 失败处理

所有清理命令都使用了失败容错机制：

```bash
make clean-temp || true          # Makefile 命令失败不中断流程
rm -f ... 2>/dev/null || true   # 文件不存在不报错
```

---

## 💡 最佳实践

### 开发阶段

1. 每天工作结束前执行 `make clean-temp`
2. 提交代码前检查是否包含临时文件
3. 使用 `.gitignore` 防止临时文件被提交

### CI/CD 阶段

1. 在上传构建产物前清理不必要的文件
2. 保留测试报告和覆盖率数据
3. 定期清理 GitHub Actions 的旧运行记录

### 维护阶段

1. 每周自动运行维护流水线
2. 定期检查维护报告 Issue
3. 根据项目实际情况调整清理策略

---

## 📝 变更历史

| 日期 | 版本 | 变更内容 |
|------|------|----------|
| 2025-10-04 | 1.0 | 初始版本 - 集成清理任务到 CI/CD |

---

## 🔗 相关资源

- [Makefile 文档](../../Makefile)
- [主 CI 流水线](./ci.yml)
- [项目维护流水线](./项目维护流水线.yml)
- [项目维护指南](../../docs/PROJECT_MAINTENANCE_GUIDE.md)

---

## 🤝 贡献

如果你有改进建议，欢迎：

1. 提交 Issue 讨论
2. 创建 Pull Request
3. 更新本文档

---

**最后更新**: 2025-10-04
**维护者**: DevOps Team
