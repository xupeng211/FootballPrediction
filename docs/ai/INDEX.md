# AI开发工具文档索引

## 📚 文档总览

本文档集合为AI编程工具提供完整的工具使用指南，确保工具能够高效、正确地处理各种开发任务。

## 📖 文档列表

### 1. [README.md](./README.md)
**文档介绍和导航**
- 文档结构说明
- 快速开始指南
- 核心原则和最佳实践

### 2. [TOOLS_REFERENCE_GUIDE.md](./TOOLS_REFERENCE_GUIDE.md)
**完整的工具参考指南**
- 所有工具的详细说明
- 使用场景和时机
- 示例命令和最佳实践
- ⭐ **最全面的文档**

### 3. [DECISION_TREE_FOR_TOOLS.md](./DECISION_TREE_FOR_TOOLS.md)
**问题解决决策树**
- 按错误类型分类的解决方案
- 任务导向的流程图
- 快速问题定位
- ⭐ **解决问题时必看**

### 4. [QUICK_TOOL_CHEAT_SHEET.md](./QUICK_TOOL_CHEAT_SHEET.md)
**一页纸速查表**
- 最常用命令
- 紧急情况处理
- 快速参考
- ⭐ **日常开发必备**

## 🎯 如何使用这些文档

### 🔰 首次接触项目
1. 阅读 [README.md](./README.md) 了解文档结构
2. 查看 [TOOLS_REFERENCE_GUIDE.md](./TOOLS_REFERENCE_GUIDE.md#核心命令) 的核心命令
3. 运行 `make context` 了解项目状态

### 🛠️ 开发过程中
- 日常开发：保存认知 [QUICK_TOOL_CHEAT_SHEET.md](./QUICK_TOOL_CHEAT_SHEET.md)
- 遇到问题：查阅 [DECISION_TREE_FOR_TOOLS.md](./DECISION_TREE_FOR_TOOLS.md#遇到错误)
- 深入了解：查看 [TOOLS_REFERENCE_GUIDE.md](./TOOLS_REFERENCE_GUIDE.md)

### 🚨 紧急情况
1. 查看 [QUICK_TOOL_CHEAT_SHEET.md](./QUICK_TOOL_CHEAT_SHEET.md#-救急命令)
2. 按照 [DECISION_TREE_FOR_TOOLS.md](./DECISION_TREE_FOR_TOOLS.md#-紧急情况) 操作

## 📋 核心工具清单

| 工具类型 | 主要命令 | 详见 |
|---------|----------|------|
| 项目管理 | `make context` | [TOOLS_REFERENCE_GUIDE.md#核心命令](./TOOLS_REFERENCE_GUIDE.md#核心命令) |
| 测试 | `make test-quick` | [TOOLS_REFERENCE_GUIDE.md#测试覆盖率工具](./TOOLS_REFERENCE_GUIDE.md#测试覆盖率工具) |
| 提交检查 | `make prepush` | [TOOLS_REFERENCE_GUIDE.md#核心命令](./TOOLS_REFERENCE_GUIDE.md#核心命令) |
| 环境管理 | `source scripts/setup_pythonpath.sh` | [TOOLS_REFERENCE_GUIDE.md#环境管理工具](./TOOLS_REFERENCE_GUIDE.md#环境管理工具) |
| 依赖解决 | `venv_clean` 环境 | [TOOLS_REFERENCE_GUIDE.md#依赖管理工具](./TOOLS_REFERENCE_GUIDE.md#依赖管理工具) |
| 覆盖率查看 | `python scripts/quick_coverage_view.py` | [TOOLS_REFERENCE_GUIDE.md#测试覆盖率工具](./TOOLS_REFERENCE_GUIDE.md#测试覆盖率工具) |

## 🔄 文档更新记录

- **2025-10-03**: 创建初始版本
  - TOOLS_REFERENCE_GUIDE.md - 完整工具指南
  - DECISION_TREE_FOR_TOOLS.md - 决策树
  - QUICK_TOOL_CHEAT_SHEET.md - 速查表
  - README.md - 文档介绍
  - INDEX.md - 本索引

## 💡 使用技巧

### 1. 文档间的关系
- README.md → 其他文档的入口
- TOOLS_REFERENCE_GUIDE.md → 完整参考
- DECISION_TREE_FOR_TOOLS.md → 问题解决
- QUICK_TOOL_CHEAT_SHEET.md → 快速查阅

### 2. 搜索技巧
- 查找特定工具：在文档中搜索工具名或文件名
- 查找解决方案：在决策树中搜索错误类型
- 查找命令：在速查表中搜索命令

### 3. 最佳实践
1. 开始任务前：先看TOOLS_REFERENCE_GUIDE了解工具
2. 遇到问题时：使用决策树快速定位
3. 日常开发时：使用速查表提高效率
4. 完成任务后：更新相关知识到文档

## 📝 反馈和改进

如果发现文档：
- 有错误或不清楚的地方
- 缺少某些工具的说明
- 需要添加更多使用场景

请在项目中创建issue或pull request来改进文档。

---

**重要提醒：这些文档是AI编程工具的"使用说明书"，正确使用可以大大提高开发效率！**