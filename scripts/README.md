# Scripts 目录说明

本目录包含项目的所有自动化脚本，按功能分类组织。

## 📁 目录结构

```
scripts/
├── ci/              # CI/CD 自动化
├── testing/         # 测试与覆盖率
├── quality/         # 代码质量检查
├── dependency/      # 依赖管理
├── deployment/      # 部署与运维
├── ml/              # 机器学习相关
├── analysis/        # 分析工具
├── fix_tools/       # 代码修复工具
├── security/        # 安全相关
├── db-init/         # 数据库初始化
├── archive/         # 已归档的脚本
└── README.md        # 本文件
```

## 🎯 快速索引

### CI/CD 自动化 (`ci/`)

- `guardian.py` - CI 质量保障守护者，自动监控和防御
- `monitor.py` - GitHub Actions 实时监控
- `issue_analyzer.py` - CI 失败原因分析器
- `auto_updater.py` - 自动更新 CI 配置
- `defense_validator.py` - 防御机制验证器

### 测试与覆盖率 (`testing/`)

- `run_with_report.py` - 运行测试并生成报告
- `coverage_tracker.py` - 覆盖率追踪器
- `run_full_coverage.py` - 完整覆盖率运行
- `validate_coverage.py` - 覆盖率一致性验证
- `build_framework.py` - 测试框架构建器

### 质量检查 (`quality/`)

- `checker.py` - 代码质量检查器
- `docs_guard.py` - 文档守护者
- `collect_trends.py` - 质量趋势收集
- `context_loader.py` - 项目上下文加载器

### 依赖管理 (`dependency/`)

- `analyze.py` - 依赖分析器
- `check.py` - 依赖检查器
- `lock.py` - 依赖锁定工具
- `audit.py` - 依赖审计
- `resolve_conflicts.py` - 依赖冲突解决

### 部署与运维 (`deployment/`)

- `env_checker.py` - 环境检查器
- `setup_project.py` - 项目设置脚本
- `e2e_verification.py` - 端到端验证
- `prepare_test_db.py` - 测试数据库准备
- `backup.sh` / `restore.sh` - 数据备份/恢复
- `deploy.sh` - 部署脚本

### 机器学习 (`ml/`)

- `retrain_pipeline.py` - ML 重训练管道
- `run_pipeline.py` - ML 流程运行器
- `update_predictions.py` - 预测结果更新

### 分析工具 (`analysis/`)

- `health_check.py` - 综合健康检查
- `analyze_coverage.py` - 覆盖率分析
- `kanban.py` - Kanban 看板工具
- `sync_issues.py` - Issues 同步工具

### 代码修复工具 (`fix_tools/`)

- `fix_syntax.py` - 语法错误修复（整合）
- `fix_imports.py` - 导入错误修复（整合）
- `fix_linting.py` - Linting 错误修复（整合）

## 🚀 常用命令

### CI/CD

```bash
# 监控 CI 状态
python scripts/ci/monitor.py

# 运行 CI Guardian
python scripts/ci/guardian.py
```

### 测试

```bash
# 运行测试并生成报告
python scripts/testing/run_with_report.py

# 追踪覆盖率
python scripts/testing/coverage_tracker.py
```

### 质量检查

```bash
# 代码质量检查
python scripts/quality/checker.py

# 文档守护
python scripts/quality/docs_guard.py
```

### 部署

```bash
# 检查环境
python scripts/deployment/env_checker.py

# 端到端验证
python scripts/deployment/e2e_verification.py
```

## 📝 开发规范

### 新增脚本

1. **确定分类**：将脚本放入对应的功能目录
2. **命名规范**：使用动词开头，清晰描述功能
3. **添加文档**：必须包含 docstring 说明用途、参数、示例
4. **避免重复**：检查是否已有类似功能的脚本

### 脚本模板

```python
#!/usr/bin/env python3
"""
脚本名称 - 简短描述

详细说明脚本的用途、功能和使用场景。

用法：
    python scripts/category/script_name.py [options]

示例：
    python scripts/ci/monitor.py --watch

作者：Your Name
日期：YYYY-MM-DD
"""
```

### 维护建议

1. **定期清理**：每季度检查一次，删除 6 个月未使用的脚本
2. **更新文档**：脚本修改后及时更新文档
3. **版本控制**：重要脚本使用版本号标记
4. **测试脚本**：关键脚本应该有对应的测试

## 📚 相关文档

- [完整分析报告](SCRIPTS_ANALYSIS_REPORT.md)
- [开发工作流程](../docs/DEVELOPMENT_WORKFLOW.md)
- [CI/CD 指南](../docs/testing/CI_GUARDIAN_GUIDE.md)
- [质量改进计划](../docs/QUALITY_IMPROVEMENT_PLAN.md)

## 🔄 最近更新

- 2025-10-05: 完成 scripts/ 目录重组，减少 55% 的脚本数量
- 2025-10-05: 整合重复的语法/导入/linting 修复脚本
- 2025-10-05: 归档临时和一次性使用的脚本

## ❓ 常见问题

### Q: 找不到某个脚本了？

A: 查看 [SCRIPTS_ANALYSIS_REPORT.md](SCRIPTS_ANALYSIS_REPORT.md) 中的脚本映射表

### Q: 需要临时脚本怎么办？

A: 在 `archive/` 目录中查找，或查看 Git 历史

### Q: 如何执行归档的脚本？

A: 不建议执行归档脚本，它们可能已过时。如需要功能，使用对应的新脚本

### Q: 脚本路径变更后 Makefile 不工作了？

A: 执行 `make help` 查看更新后的命令，或查看重组日志

## 📧 联系方式

如有问题或建议，请：

- 提交 Issue: [GitHub Issues](https://github.com/xupeng211/FootballPrediction/issues)
- 查看文档: `docs/` 目录
- 运行帮助: `python scripts/category/script.py --help`
