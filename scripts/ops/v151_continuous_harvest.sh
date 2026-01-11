#!/bin/bash
# V151.3 持续收割执行脚本
# 用途: 持续运行并发收割器，直到采集率突破 60%
# 日期: 2026-01-11

set -e

# 配置参数
WORKERS=3
BATCH_SIZE=200
TARGET_RATE=60

echo "=========================================="
echo "🚀 V151.3 持续收割启动"
echo "=========================================="
echo "配置: ${WORKERS} Workers × ${BATCH_SIZE} 场/批"
echo "目标: 采集率 > ${TARGET_RATE}%"
echo ""

# 激活虚拟环境（如果使用）
# source venv/bin/activate

# ===================================================================
# 检查当前采集率
# ===================================================================
check_collection_rate() {
    psql -U football_user -d football_db -t -c "
        SELECT
            ROUND(
                100.0 * COUNT(DISTINCT CASE WHEN l2_raw_json IS NOT NULL THEN fotmob_id END) /
                NULLIF(COUNT(DISTINCT fotmob_id), 0),
                2
            ) as rate
        FROM matches_mapping
        WHERE oddsportal_url IS NOT NULL
    " 2>/dev/null | tr -d ' '
}

CURRENT_RATE=$(check_collection_rate)
echo "📊 当前采集率: ${CURRENT_RATE}%"
echo ""

# ===================================================================
# 持续收割循环
# ===================================================================
ROUND=1
while true; do
    echo "=========================================="
    echo "🔄 第 ${ROUND} 轮收割开始"
    echo "=========================================="
    echo ""

    # 运行并发收割器
    python scripts/ops/harvest_pinnacle_concurrent.py \
        --workers ${WORKERS} \
        --limit ${BATCH_SIZE} \
        --delay-min 20 \
        --delay-max 40

    HARVEST_EXIT=$?
    echo ""

    # 检查采集率
    NEW_RATE=$(check_collection_rate)
    echo "📊 当前采集率: ${NEW_RATE}% (本轮之前: ${CURRENT_RATE}%)"

    # 检查是否达到目标
    if (( $(echo "$NEW_RATE >= $TARGET_RATE" | bc -l) )); then
        echo ""
        echo "=========================================="
        echo "🎉 恭喜！采集率已达到目标！"
        echo "=========================================="
        echo "目标: ${TARGET_RATE}%"
        echo "实际: ${NEW_RATE}%"
        echo "轮数: ${ROUND}"
        echo ""
        break
    fi

    CURRENT_RATE=$NEW_RATE
    ROUND=$((ROUND + 1))

    # 如果收割器异常退出，等待 5 分钟后重试
    if [ $HARVEST_EXIT -ne 0 ]; then
        echo ""
        echo "⚠️ 收割器异常退出 (退出码: ${HARVEST_EXIT})"
        echo "⏳ 等待 5 分钟后重试..."
        echo ""
        sleep 300
    else
        echo ""
        echo "⏳ 等待 2 分钟后继续下一轮..."
        echo ""
        sleep 120
    fi
done

echo "✅ 持续收割任务完成！"
echo ""
echo "📝 建议后续步骤:"
echo "  1. 检查 logs/harvest_pinnacle_concurrent.log 查看详细统计"
echo "  2. 检查 logs/concurrent_harvest_report.json 查看最终报告"
echo "  3. 运行数据质量检查: python scripts/ops/check_db_consistency.py"
echo ""
