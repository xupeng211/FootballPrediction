#!/bin/bash
# 新开发者欢迎脚本
# 验证环境并提供重要提示

echo "🎉 欢迎加入 FootballPrediction 项目！"
echo "========================================"
echo ""

# 检查是否是新开发者
if [ ! -f ".developer_welcome_shown" ]; then
    echo "📋 检测到新开发者，请阅读以下重要信息："
    echo ""
    echo "⚠️  【重要】测试运行须知"
    echo "------------------------"
    echo "❌ 错误做法："
    echo "   pytest tests/unit/api/test_health.py --cov=src"
    echo "   这会导致覆盖率报告不准确！"
    echo ""
    echo "✅ 正确做法："
    echo "   make test-phase1    # Phase 1 测试"
    echo "   make coverage       # 覆盖率测试"
    echo "   make test-quick     # 快速测试"
    echo ""
    echo "📚 必读文档："
    echo "   - TEST_RUN_GUIDE.md        # 测试运行指南"
    echo "   - docs/QUICK_START_FOR_DEVELOPERS.md  # 开发者快速入门"
    echo "   - docs/TESTING_COMMANDS.md # 测试命令参考"
    echo ""
    echo "🧪 验证测试环境："
    echo "   make test-phase1"
    echo ""
    read -p "按回车键继续..."

    # 标记已经显示过欢迎信息
    touch .developer_welcome_shown
    echo ""
    echo "✅ 环境检查完成！开始开发吧 🚀"
fi

echo ""
echo "🔧 常用命令："
echo "-----------"
echo "make help          # 查看所有命令"
echo "make test-quick    # 快速测试"
echo "make prepush       # 提交前检查"
echo ""