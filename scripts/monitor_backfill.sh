#!/bin/bash
# 回填进度监控脚本 - 不会打断运行中的进程

echo "=== 数据回填进度监控 ==="
echo "时间: $(date)"
echo ""

# 1. 检查进程状态
echo "📊 进程状态:"
if docker-compose exec app bash -c 'ps aux | grep backfill_global.py | grep -v grep' > /dev/null 2>&1; then
    echo "  ✅ 回填进程正在运行"
    docker-compose exec app bash -c 'ps aux | grep backfill_global.py | grep -v grep'
else
    echo "  ❌ 未找到回填进程"
fi
echo ""

# 2. 检查数据库记录数变化
echo "📈 数据库增长情况:"
total_matches=$(docker-compose exec db psql -U postgres -d football_prediction -t -c "SELECT COUNT(*) FROM matches;")
echo "  总比赛记录数: $total_matches"

recent_matches=$(docker-compose exec db psql -U postgres -d football_prediction -t -c "SELECT COUNT(*) FROM matches WHERE created_at > NOW() - INTERVAL '1 hour';")
echo "  最近1小时新增: $recent_matches"

echo "  最近5分钟新增: $(docker-compose exec db psql -U postgres -d football_prediction -t -c "SELECT COUNT(*) FROM matches WHERE created_at > NOW() - INTERVAL '5 minutes';")"
echo ""

# 3. 检查数据日期范围
echo "📅 数据覆盖范围:"
date_range=$(docker-compose exec db psql -U postgres -d football_prediction -t -c "SELECT 
    MIN(date) as earliest_date,
    MAX(date) as latest_date,
    COUNT(DISTINCT date) as unique_dates
FROM matches;")
echo "  $date_range"

# 4. 检查日志最新内容
echo "📋 最近日志 (最后10行):"
if docker-compose exec app bash -c 'test -f logs/backfill_run.log' 2>/dev/null; then
    docker-compose exec app bash -c 'tail -10 logs/backfill_run.log'
else
    echo "  日志文件尚未创建"
fi
echo ""

echo "=== 监控完成 ==="
