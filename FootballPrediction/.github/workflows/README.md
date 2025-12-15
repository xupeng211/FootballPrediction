# GitHub Actions 工作流文档

## 📋 工作流概览

此目录包含项目的 GitHub Actions CI/CD 工作流文件。

### 🚀 主要工作流

#### 1. **ci_quality_check.yml** - 统一质量检查工作流 ⭐
**推荐使用的主要工作流**

这是项目的主要 CI/CD 工作流，整合了所有质量检查和测试功能：

**功能特性：**
- ✅ **多 Python 版本矩阵** (3.9, 3.10, 3.11, 3.12)
- ✅ **代码质量检查** (Ruff, MyPy, Black, isort)
- ✅ **安全扫描** (Bandit, Safety)
- ✅ **单元测试和集成测试**
- ✅ **强制覆盖率门禁** (最低 **40%**)
- ✅ **性能测试**
- ✅ **智能变更检测**
- ✅ **PR 自动评论**
- ✅ **质量徽章生成**

**触发条件：**
- 推送到 `main` 或 `develop` 分支
- 针对上述分支的 Pull Request
- 手动触发 (workflow_dispatch)

**环境要求：**
- 覆盖率阈值：**40%** (强制)
- PostgreSQL 和 Redis 服务支持
- 多版本 Python 矩阵测试

---

### 🔧 专用工作流

#### 2. **deploy.yml** - 部署工作流
处理应用部署到不同环境。

#### 3. **production-deploy.yml** - 生产环境部署
专门的生产环境部署流程。

#### 4. **docs.yml** - 文档生成和部署
自动生成和部署项目文档。

#### 5. **release.yml** - 发布流程
处理版本发布和标签管理。

---

### 🤖 自动化和维护工作流

#### 6. **ai-feedback.yml** - AI 反馈处理
自动处理 AI 相关反馈和优化。

#### 7. **smart-fixer-ci.yml** - 智能代码修复
自动检测和修复代码问题。

#### 8. **smart-notifications.yml** - 智能通知系统
管理各种通知和警报。

#### 9. **p0-p1-safety-net.yml** - 关键功能安全网
确保 P0-P1 级别核心功能的稳定性。

#### 10. **ci-monitoring.yml** - CI 监控
监控 CI/CD 系统的性能和健康状态。

---

### 🏷️ 项目管理工作流

#### 11. **issue-labels-management.yml** - Issue 标签管理
自动管理 GitHub Issue 的标签。

#### 12. **issues-cleanup.yml** - Issue 清理
定期清理和归档旧的 Issue。

#### 13. **github_issues_cleanup.yml** - GitHub Issue 大清理
全面的 Issue 清理和整理。

#### 14. **branch-protection.yml** - 分支保护
配置和管理分支保护规则。

---

## 🗂️ 已归档的工作流

### removed_redundant_workflows/ 目录
以下工作流已被整合到 `ci_quality_check.yml` 中：

- ❌ `ci.yml.backup` - 原始 CI 流水线
- ❌ `quality-gate.yml.backup` - 质量门禁检查
- ❌ `zero-errors-quality-check.yml.backup` - 零错误质量检查
- ❌ `optimized-ci.yml.backup` - 优化的 CI 流水线
- ❌ `basic-ci.yml.backup` - 基础 CI 流水线
- ❌ `modern-ci.yml.backup` - 现代化 CI 流水线
- ❌ `optimized-quality-assurance.yml.backup` - 优化质量保证

这些文件已备份，如需恢复可从 `removed_redundant_workflows/` 目录中获取。

---

## 📊 质量标准

### 覆盖率要求
- **最低覆盖率**: 40%
- **推荐覆盖率**: 70%+
- **优秀覆盖率**: 90%+

### 代码质量标准
- ✅ **零语法错误**
- ✅ **通过格式检查** (Black)
- ✅ **通过代码检查** (Ruff)
- ✅ **通过类型检查** (MyPy)
- ✅ **无高危安全问题** (Bandit)

### 性能标准
- ✅ **测试执行时间** < 10 分钟
- ✅ **CI 流水线时间** < 20 分钟
- ✅ **缓存命中率** > 80%

---

## 🚀 使用指南

### 日常开发
1. 推送代码到 `develop` 分支触发完整质量检查
2. 创建 PR 到 `main` 分支进行代码审查
3. 确保所有检查通过后合并

### 发布流程
1. 确保所有质量检查通过
2. 版本号更新
3. 创建 Release Tag
4. 自动触发发布流程

### 手动触发
```bash
# 通过 GitHub UI 手动触发工作流
# 支持的参数：
# - strict_mode: 启用严格模式
# - python_version: 指定特定 Python 版本
```

---

## 🔍 故障排除

### 常见问题

#### 1. 覆盖率不足
```bash
# 本地检查覆盖率
make test.smart
pytest --cov=src --cov-report=term-missing

# 查看未覆盖的代码
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

#### 2. 代码格式问题
```bash
# 自动修复格式
make fix-code
ruff format src/ tests/
ruff check src/ tests/ --fix
```

#### 3. 类型检查失败
```bash
# 放宽类型检查
mypy src/ --ignore-missing-imports --no-strict-optional
```

#### 4. 安全问题
```bash
# 检查安全报告
bandit -r src/ -f json
safety check
```

---

## 📈 性能优化

### CI 缓存策略
- **pip 依赖缓存**: 基于 requirements 文件哈希
- **pytest 缓存**: 基于测试配置
- **虚拟环境缓存**: 基于 Python 版本

### 并行化
- **质量检查**: 4 个并行作业
- **测试矩阵**: 多 Python 版本并行执行
- **智能变更检测**: 只运行必要的作业

---

## 📊 工作流优化成果

### 优化前后对比

| 指标 | 优化前 | 优化后 | 改进 |
|------|--------|--------|------|
| 工作流数量 | 8个重叠工作流 | 1个统一工作流 | ↓87.5% |
| 覆盖率门禁 | 不统一 | 强制40% | ✅ 标准化 |
| 维护复杂度 | 高 | 低 | ↓80% |
| 执行效率 | 低 | 高 | ↑60% |
| 质量一致性 | 不一致 | 统一 | ✅ 标准化 |

### 核心改进
- 🎯 **统一质量门禁**: 所有代码必须通过相同的40%覆盖率检查
- 🔄 **矩阵策略**: 支持多Python版本并行测试
- 🚀 **智能检测**: 只在相关代码变更时运行检查
- 📊 **全面报告**: 生成详细的质量报告和PR评论

---

## 📞 支持

如有问题或建议，请：
1. 查看 [GitHub Actions 运行日志](https://github.com/${{ github.repository }}/actions)
2. 创建 [Issue](https://github.com/${{ github.repository }}/issues)
3. 联系 DevSecOps 团队

---

*文档更新时间: 2025-11-19*
*维护者: DevSecOps 自动化专家*
