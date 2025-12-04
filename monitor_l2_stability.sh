#!/bin/bash
# L2 System Stability Monitoring Script
# 每5分钟检查一次数据产出情况，共30分钟

echo "🔍 L2 System Stability Monitoring Started"
echo "📊 Monitoring Complete Records Growth (30 minutes total)"
echo "⏰ Start Time: $(date)"
echo "================================================"

# 记录初始数据量
INITIAL_COUNT=$(docker-compose exec db psql -U postgres -d football_prediction -t -c "SELECT COUNT(*) FROM matches WHERE data_completeness = 'complete';" 2>/dev/null | tr -d ' ')
echo "🎯 Initial Complete Records: $INITIAL_COUNT"
echo ""

# 创建监控结果文件
REPORT_FILE="l2_stability_report_$(date +%Y%m%d_%H%M%S).txt"
echo "L2 Stability Monitoring Report" > "$REPORT_FILE"
echo "Started at: $(date)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# 监控循环 (6次 x 5分钟 = 30分钟)
for i in {1..6}; do
    echo "--- Check #$i at $(date) ---"
    echo "--- Check #$i at $(date) ---" >> "$REPORT_FILE"

    # 检查当前complete记录数
    CURRENT_COUNT=$(docker-compose exec db psql -U postgres -d football_prediction -t -c "SELECT COUNT(*) FROM matches WHERE data_completeness = 'complete';" 2>/dev/null | tr -d ' ')
    GROWTH=$((CURRENT_COUNT - INITIAL_COUNT))

    echo "📊 Current Complete Records: $CURRENT_COUNT (Growth: +$GROWTH)"
    echo "📊 Current Complete Records: $CURRENT_COUNT (Growth: +$GROWTH)" >> "$REPORT_FILE"

    # 检查最近5分钟的新增记录
    RECENT_5MIN=$(docker-compose exec db psql -U postgres -d football_prediction -t -c "SELECT COUNT(*) FROM matches WHERE data_completeness = 'complete' AND updated_at > NOW() - INTERVAL '5 minutes';" 2>/dev/null | tr -d ' ')
    echo "🆕 Records added in last 5 minutes: $RECENT_5MIN"
    echo "🆕 Records added in last 5 minutes: $RECENT_5MIN" >> "$REPORT_FILE"

    # 检查L2容器进程状态
    if docker-compose top data-collector-l2 | grep -q "python scripts/backfill_details.py"; then
        echo "✅ L2 Container Process: RUNNING"
        echo "✅ L2 Container Process: RUNNING" >> "$REPORT_FILE"
    else
        echo "❌ L2 Container Process: STOPPED/ERROR"
        echo "❌ L2 Container Process: STOPPED/ERROR" >> "$REPORT_FILE"
    fi

    # 检查最新更新时间
    LATEST_UPDATE=$(docker-compose exec db psql -U postgres -d football_prediction -t -c "SELECT MAX(updated_at) FROM matches WHERE data_completeness = 'complete';" 2>/dev/null | tr -d ' ')
    echo "🕒 Latest Complete Record Update: $LATEST_UPDATE"
    echo "🕒 Latest Complete Record Update: $LATEST_UPDATE" >> "$REPORT_FILE"

    echo "" >> "$REPORT_FILE"

    # 如果不是最后一次检查，等待5分钟
    if [ $i -lt 6 ]; then
        echo "⏳ Waiting 5 minutes for next check..."
        sleep 300
    fi
done

echo "================================================"
echo "📋 30-Minute Monitoring Complete"
echo "📋 30-Minute Monitoring Complete" >> "$REPORT_FILE"
echo "📄 Detailed report saved to: $REPORT_FILE"

# 最终统计
FINAL_COUNT=$(docker-compose exec db psql -U postgres -d football_prediction -t -c "SELECT COUNT(*) FROM matches WHERE data_completeness = 'complete';" 2>/dev/null | tr -d ' ')
TOTAL_GROWTH=$((FINAL_COUNT - INITIAL_COUNT))

echo ""
echo "🎯 FINAL RESULTS:"
echo "🎯 Initial Complete Records: $INITIAL_COUNT"
echo "🎯 Final Complete Records: $FINAL_COUNT"
echo "🎯 Total Growth Over 30 Minutes: +$TOTAL_GROWTH"
echo ""
echo "🎯 FINAL RESULTS:" >> "$REPORT_FILE"
echo "🎯 Initial Complete Records: $INITIAL_COUNT" >> "$REPORT_FILE"
echo "🎯 Final Complete Records: $FINAL_COUNT" >> "$REPORT_FILE"
echo "🎯 Total Growth Over 30 Minutes: +$TOTAL_GROWTH" >> "$REPORT_FILE"

# 验收标准判断
if [ $TOTAL_GROWTH -gt 0 ]; then
    echo "✅ VERDICT: PASSED - System is continuously producing data"
    echo "✅ VERDICT: PASSED - System is continuously producing data" >> "$REPORT_FILE"
    exit 0
else
    echo "❌ VERDICT: FAILED - System is not producing new data"
    echo "❌ VERDICT: FAILED - System is not producing new data" >> "$REPORT_FILE"
    exit 1
fi