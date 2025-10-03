# 🤖 AI编程工具快速指南

**给AI编程工具的项目工具使用指南**

## ⚡ 30秒快速开始

```bash
# 1. 了解项目（最重要！）
make context

# 2. 检查环境
make env-check

# 3. 运行测试
make test-quick
```

## 📚 完整文档位置

所有AI工具相关文档都在 `docs/ai/` 目录：

- 📖 **[完整工具指南](docs/ai/TOOLS_REFERENCE_GUIDE.md)** - 所有工具的详细说明
- 🌳 **[问题决策树](docs/ai/DECISION_TREE_FOR_TOOLS.md)** - 遇到问题时查看
- 📄 **[速查表](docs/ai/QUICK_TOOL_CHEAT_SHEET.md)** - 一页纸快速参考

## 🚨 遇到错误怎么办？

| 错误类型 | 解决方案 |
|---------|----------|
| ImportError | `source scripts/setup_pythonpath.sh` |
| 依赖冲突 | 使用 `venv_clean` 环境 |
| 测试失败 | 查看具体错误信息 |
| 环境问题 | `make env-check` |

## 💡 必须记住的命令

```bash
make context          # 了解项目状态
make test-quick       # 快速测试
make prepush         # 提交前检查
```

## 🔧 环境管理

```bash
# 设置Python路径
source scripts/setup_pythonpath.sh

# 激活干净环境（解决依赖问题）
source activate_clean_env.sh

# 查看测试覆盖率
python scripts/quick_coverage_view.py
```

## 📋 更多资源

- [项目README](README.md)
- [开发指南](docs/reference/DEVELOPMENT_GUIDE.md)
- [故障排除](CLAUDE_TROUBLESHOOTING.md)

---
**记住：遇到问题先查看 `docs/ai/` 目录中的文档！**