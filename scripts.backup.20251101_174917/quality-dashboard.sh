#!/bin/bash

# 质量仪表板 - 显示项目健康状态

echo "🎯 足球预测系统 - 质量仪表板"
echo "================================"
echo "日期: $(date '+%Y-%m-%d %H:%M')"
echo ""

# 1. 测试覆盖率
echo "📊 测试覆盖率"
echo "-----------"
if [ -f "coverage.json" ]; then
    COV=$(python -c "import json; print(json.load(open('coverage.json'))['totals']['percent_covered'])" 2>/dev/null || echo "N/A")
    # 根据覆盖率显示不同颜色
    if (( $(echo "$COV >= 30" | bc -l) )); then
        echo "当前: ${COV}% ✅ (达到目标)"
    elif (( $(echo "$COV >= 20" | bc -l) )); then
        echo "当前: ${COV}% 🟡 (接近目标)"
    elif (( $(echo "$COV >= 15" | bc -l) )); then
        echo "当前: ${COV}% 🔴 (需要改进)"
    else
        echo "当前: ${COV}% ❌ (严重不足)"
    fi
    echo "目标: 30% (CI门槛)"
    echo "最低: 15% (本地门槛)"
else
    echo "未运行覆盖率测试"
fi
echo ""

# 2. 代码质量
echo "🔍 代码质量"
echo "----------"
LINT_COUNT=$(ruff check src/ --quiet 2>/dev/null | wc -l)
echo "Lint错误: $LINT_COUNT 个"
if [ $LINT_COUNT -lt 50 ]; then
    echo "状态: ✅ 优秀"
elif [ $LINT_COUNT -lt 100 ]; then
    echo "状态: 🟡 良好"
elif [ $LINT_COUNT -lt 200 ]; then
    echo "状态: 🔴 需要改进"
else
    echo "状态: ❌ 严重"
fi
echo ""

# 3. 测试状态
echo "🧪 测试状态"
echo "----------"
# 运行一个快速测试看测试基础设施是否正常
if pytest tests/unit/test_config.py -q 2>/dev/null >/dev/null; then
    echo "基础设施: ✅ 正常"
else
    echo "基础设施: ❌ 有问题"
fi
echo ""

# 4. 最近提交质量
echo "📝 最近提交"
echo "------------"
LAST_COMMIT=$(git log -1 --pretty=format:"%h %s" 2>/dev/null)
echo "最新: $LAST_COMMIT"
COMMIT_COUNT_TODAY=$(git log --since="midnight" --pretty=format:"%h" | wc -l)
echo "今日提交: $COMMIT_COUNT_TODAY 次"
echo ""

# 5. 改进建议
echo "💡 改进建议"
echo "----------"
if [ -n "$COV" ]; then
    if (( $(echo "$COV < 20" | bc -l) )); then
        echo "🎯 本周目标：覆盖率达到 20%"
        echo "   - 为新功能添加测试"
        echo "   - 修复失败的测试"
    fi
fi

if [ $LINT_COUNT -gt 100 ]; then
    echo "🔧 代码质量："
    echo "   - 每天修复 10 个 lint 错误"
    echo "   - 使用 'ruff check --fix' 自动修复"
fi

if [ $COMMIT_COUNT_TODAY -eq 0 ]; then
    echo "📅 建议：今天至少提交一次改进"
fi
echo ""

# 6. 快速命令
echo "⚡ 快速命令"
echo "----------"
echo "运行健康检查: ./scripts/quick-health-check.sh"
echo "运行完整测试: make test-quick"
echo "检查覆盖率: make coverage-local"
echo "修复lint错误: ruff check --fix src/"
echo ""
echo "🎉 持续改进，每一天都更好！"
