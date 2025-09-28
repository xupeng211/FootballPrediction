#!/bin/bash

# AI 增强的持续 Bug 修复循环启动脚本
# 使用方法: ./run_continuous_loop.sh [max_iterations]

set -e

# 设置默认值
MAX_ITERATIONS=${1:-5}  # 默认5轮循环
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "🚀 启动 AI 增强的持续 Bug 修复循环"
echo "📊 最大循环次数: $MAX_ITERATIONS"
echo "📁 项目根目录: $PROJECT_ROOT"
echo "⏰ 开始时间: $(date)"
echo ""

# 设置环境变量
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# 运行持续循环
echo "🔄 开始持续 Bug 修复循环..."
python scripts/continuous_bugfix.py --max-iterations "$MAX_ITERATIONS"

echo ""
echo "✅ 持续 Bug 修复循环完成"
echo "⏰ 结束时间: $(date)"
echo "📋 报告位置: docs/_reports/"

# 显示生成的报告
echo ""
echo "📊 生成的报告:"
ls -la docs/_reports/ | grep -E "(CONTINUOUS|BUGFIX_TODO|PHASE)" | tail -10