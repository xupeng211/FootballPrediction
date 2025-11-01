#!/bin/bash

# 每日质量检查提醒
# 用于提醒开发者每天进行质量检查

echo "🌅 每日质量检查提醒 - $(date '+%Y-%m-%d %H:%M')"
echo "============================================"
echo ""

# 1. 显示当前状态
echo "📊 当前项目状态"
echo "----------------"
RUN_SCRIPT="./scripts/quick-health-check.sh"
if [ -f "$RUN_SCRIPT" ]; then
    bash "$RUN_SCRIPT"
else
    echo "⚠️  快速健康检查脚本不存在"
fi
echo ""

# 2. 今日建议任务
echo "🎯 今日建议任务"
echo "----------------"
WEEKDAY=$(date +%u)
case $WEEKDAY in
    1)  # 周一
        echo "📅 周一任务："
        echo "  - 运行完整测试: make test-quick"
        echo "  - 检查覆盖率: make coverage-local"
        echo "  - 修复 5-10 个 lint 错误"
        echo "  - 设定本周质量目标"
        ;;
    2)  # 周二
        echo "📅 周二任务："
        echo "  - 运行覆盖率: make coverage-local"
        echo "  - 修复关键模块的 lint 错误"
        echo "  - 为新功能添加测试"
        ;;
    3)  # 周三
        echo "📅 周三任务："
        echo "  - 运行测试: make test-quick"
        echo "  - 检查依赖安全性: make safety-check"
        echo "  - 清理未提交的更改"
        ;;
    4)  # 周四
        echo "📅 周四任务："
        echo "  - 运行完整检查: make prepush"
        echo "  - 准备提交的代码"
        echo "  - 记录本周改进"
        ;;
    5)  # 周五
        echo "📅 周五任务："
        echo "  - 最终检查: make ci"
        echo "  - 提交本周改进"
        echo "  - 查看质量仪表板: ./scripts/quality-dashboard.sh"
        echo "  - 庆祝小胜利！🎉"
        ;;
    6|7)  # 周末
        echo "📅 周末任务："
        echo "  - 休息或进行实验性开发"
        echo "  - 学习新技术"
        echo "  - 为下周做计划"
        ;;
esac
echo ""

# 3. 快速命令参考
echo "⚡ 快速命令"
echo "------------"
echo "健康检查:    ./scripts/quick-health-check.sh"
echo "质量仪表板:  ./scripts/quality-dashboard.sh"
echo "快速测试:    make test-quick"
echo "本地覆盖率:  make coverage-local"
echo "修复lint:    ruff check --fix src/"
echo "完整检查:    make prepush"
echo ""

# 4. 激励语句
echo "💪 今日激励"
echo "------------"
QUOTES=(
    "代码质量是团队协作的基础。"
    "小步快跑，持续改进。"
    "今天的努力是为了明天的轻松。"
    "让每次提交都让项目变得更好。"
    "保持简单，持续前进。"
)
QUOTE_INDEX=$((RANDOM % ${#QUOTES[@]}))
echo "${QUOTES[$QUOTE_INDEX]}"
echo ""

echo "✨ 祝你编码愉快！"
