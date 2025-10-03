# AI开发工具文档

**为AI编程工具提供的完整项目工具文档**

## 📚 文档结构

本目录包含以下文档，帮助AI编程工具快速理解和使用项目工具：

### 📖 [工具参考指南 (TOOLS_REFERENCE_GUIDE.md)](./TOOLS_REFERENCE_GUIDE.md)
- **内容**: 最完整的工具使用指南
- **适合**: 需要深入了解工具时查看
- **包含**: 所有工具的详细说明、使用时机、示例命令

### 🌳 [决策树指南 (DECISION_TREE_FOR_TOOLS.md)](./DECISION_TREE_FOR_TOOLS.md)
- **内容**: 问题导向的决策流程
- **适合**: 遇到具体问题时快速查找解决方案
- **包含**: 错误类型映射、任务流程、最佳实践

### 📄 [速查表 (QUICK_TOOL_CHEAT_SHEET.md)](./QUICK_TOOL_CHEAT_SHEET.md)
- **内容**: 一页纸快速参考
- **适合**: 日常开发快速查阅
- **包含**: 最常用命令、紧急情况处理

## 🚀 快速开始

### 如果你是第一次接触这个项目
```bash
# 1. 首先运行这个（最重要！）
make context

# 2. 查看项目状态
make env-check

# 3. 运行测试验证
make test-quick
```

### 如果你遇到错误
1. **查看**: [决策树指南](./DECISION_TREE_FOR_TOOLS.md#遇到错误)
2. **找到**: 对应的错误类型
3. **使用**: 推荐的工具和命令

### 如果你需要查看测试覆盖率
```bash
# 快速查看
python scripts/quick_coverage_view.py

# 详细报告
open htmlcov/index.html
```

## 🎯 核心原则

### 三个必须记住的命令
1. `make context` - 了解项目
2. `make test-quick` - 验证功能
3. `make prepush` - 提交前检查

### 环境优先级
1. **开发环境** (venv) - 日常使用
2. **干净环境** (venv_clean) - 解决依赖问题
3. **生产环境** (Docker) - 部署使用

### 问题解决流程
1. 识别问题类型
2. 查阅决策树
3. 使用对应工具
4. 验证结果

## 📋 工具分类

### 核心命令 (Makefile)
- 项目管理、测试、检查
- 日常开发使用

### 依赖管理 (dependency_manager/)
- 环境创建、备份、恢复
- 解决复杂依赖问题

### 测试工具
- 覆盖率分析、报告生成
- 质量保证

### 辅助脚本
- PYTHONPATH设置、环境激活
- 快捷操作

## 🔗 相关文档

- [项目主页](../../README.md)
- [开发指南](../../reference/DEVELOPMENT_GUIDE.md)
- [故障排除](../../CLAUDE_TROUBLESHOOTING.md)
- [API文档](../../reference/API_REFERENCE.md)

## 💡 使用建议

1. **首次使用**: 先阅读[工具参考指南](./TOOLS_REFERENCE_GUIDE.md)
2. **遇到问题**: 使用[决策树](./DECISION_TREE_FOR_TOOLS.md)
3. **日常开发**: 保留[速查表](./QUICK_TOOL_CHEAT_SHEET.md)在手边
4. **深入理解**: 查看具体工具的源代码和注释

---

**这些文档的设计目标是让AI编程工具能够：**
- 快速理解项目结构
- 选择正确的工具
- 高效解决问题
- 遵循最佳实践