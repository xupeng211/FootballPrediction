#!/bin/bash

# 快速健康检查脚本
# 在提交前运行，确保不破坏基本功能

set -e

echo "🔍 快速健康检查..."
echo "=================="

# 1. 基本语法检查（最快）
echo -n "✓ 语法检查："
python -m py_compile src/main.py 2>/dev/null && echo "通过" || echo "失败 - 请修复语法错误"

# 2. 导入检查
echo -n "✓ 导入检查："
python -c "import src.main" 2>/dev/null && echo "通过" || echo "失败 - 有导入错误"

# 3. 配置检查
echo -n "✓ 配置检查："
python -c "from src.core.config import get_settings; get_settings()" 2>/dev/null && echo "通过" || echo "失败 - 配置错误"

# 4. 快速测试（只运行最关键的）
echo -n "✓ 核心测试："
pytest tests/unit/test_config.py::test_get_settings -v 2>/dev/null >/dev/null && echo "通过" || echo "警告 - 测试失败"

# 5. 检查是否有明显的 lint 错误
echo -n "✓ Lint检查："
LINT_ERRORS=$(ruff check src/ --quiet 2>/dev/null | wc -l)
if [ $LINT_ERRORS -gt 200 ]; then
    echo "警告 - 有 $LINT_ERRORS 个错误，建议修复一些"
elif [ $LINT_ERRORS -gt 100 ]; then
    echo "注意 - 有 $LINT_ERRORS 个错误"
else
    echo "良好 - 只有 $LINT_ERRORS 个错误"
fi

echo ""
echo "📊 健康状态："

# 计算当前覆盖率
if [ -f "coverage.json" ]; then
    CURRENT_COV=$(python -c "import json; print(json.load(open('coverage.json'))['totals']['percent_covered'])" 2>/dev/null || echo "N/A")
    echo "- 当前覆盖率: ${CURRENT_COV}%"
else
    echo "- 当前覆盖率: 未测量"
fi

# 检查未提交的更改
UNCOMMITTED=$(git status --porcelain 2>/dev/null | wc -l)
echo "- 未提交文件: $UNCOMMITTED 个"

# 提供建议
echo ""
if [ $UNCOMMITTED -gt 10 ]; then
    echo "💡 建议：考虑分批提交更改"
fi

if [ $LINT_ERRORS -gt 150 ]; then
    echo "💡 建议：每天修复5-10个 lint 错误"
fi

echo ""
echo "✅ 快速检查完成！"
