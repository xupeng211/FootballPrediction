#!/bin/bash
# L2全量回补脚本 - 战术统计数据回补

set -e  # 遇到错误立即退出

echo "🎯 [L2全量回补] 启动79维度战术数据回补..."
echo "目标: 为所有完赛场次补充完整的战术统计"
echo "预计耗时: 数小时 (取决于比赛数量)"
echo ""

# 确保在项目根目录
cd "$(dirname "$0")/.."

# 设置Python路径
export PYTHONPATH=$(pwd)

echo "🚀 开始L2全量回补..."

# 使用Python脚本执行L2回补，并捕获返回值
python scripts/backfill_l2_batch.py --batch-size 50 --delay 2

# 检查Python脚本的退出状态
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo "✅ L2全量回补完成！"
    echo "📊 79维度战术数据已同步到数据库"
    echo "🎯 状态: 成功"
else
    echo ""
    echo "❌ L2全量回补失败！"
    echo "🔍 退出码: $EXIT_CODE"
    echo "📊 请检查日志文件: l2_enhanced_collection.log"
    exit $EXIT_CODE
fi