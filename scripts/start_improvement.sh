#!/bin/bash

# 代码可维护性改进启动脚本
# 立即开始 Phase 1 的改进工作

set -e

echo "🚀 启动代码可维护性改进计划..."
echo "=========================================="

# 1. 执行 Phase 1 紧急修复
echo ""
echo "📋 执行 Phase 1: 紧急修复"
echo "------------------------"
python scripts/maintainability_quick_start.py

echo ""
echo "✅ Phase 1 完成！"

# 2. 运行测试检查
echo ""
echo "🧪 运行快速测试检查"
echo "----------------------"
if command -v make &> /dev/null; then
    make test-quick
else
    python -m pytest tests/unit/test_*quick*.py -v
fi

# 3. 检查覆盖率
echo ""
echo "📊 检查测试覆盖率"
echo "-------------------"
if command -v make &> /dev/null; then
    make coverage-local
else
    python -m pytest --cov=src --cov-report=term-missing tests/unit/test_*quick*.py
fi

# 4. 生成每日报告
echo ""
echo "📈 生成改进报告"
echo "-----------------"
python scripts/daily_maintainability_check.py

echo ""
echo "=========================================="
echo "🎯 下一步行动建议："
echo "1. 查看 MAINTAINABILITY_IMPROVEMENT_BOARD.md 了解完整计划"
echo "2. 运行 'python scripts/daily_maintainability_check.py' 每日跟踪进度"
echo "3. 开始重构高复杂度函数（audit_service.py）"
echo "4. 持续添加测试以提升覆盖率"
echo ""
echo "💡 快速命令："
echo "  • 运行所有测试: make test"
echo "  • 检查覆盖率: make coverage"
echo "  • 修复类型错误: make type-check"
echo "  • 运行 lint: make lint"
echo ""
