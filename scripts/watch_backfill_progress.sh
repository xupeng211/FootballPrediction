#!/bin/bash
# 数据回填进度监控脚本 - 不会打断运行中的进程
# 使用方法: ./watch_backfill_progress.sh

echo "🔍 数据回填实时监控"
echo "======================"
echo ""

# 1. 检查日志文件最新进度
echo "📋 最新回填进度:"
if docker-compose exec app bash -c 'test -f /app/backfill.log' 2>/dev/null; then
    echo "  最新日志:"
    docker-compose exec app bash -c 'tail -5 /app/backfill.log' | sed 's/^/    /'

    # 提取关键信息
    progress_line=$(docker-compose exec app bash -c 'tail -10 /app/backfill.log | grep -E "\[.*\].*处理.*" | tail -1')
    if [ ! -z "$progress_line" ]; then
        echo "  当前进度: $progress_line"
    fi
else
    echo "  ❌ 未找到回填日志文件"
fi
echo ""

# 2. 数据库增长情况
echo "📊 数据库统计:"
total_matches=$(docker-compose exec db psql -U postgres -d football_prediction -t -c "SELECT COUNT(*) FROM matches;" 2>/dev/null | tr -d ' ')
echo "  总比赛记录: $total_matches"

# 检查最近创建的记录
recent_count=$(docker-compose exec db psql -U postgres -d football_prediction -t -c "SELECT COUNT(*) FROM matches WHERE created_at > NOW() - INTERVAL '10 minutes';" 2>/dev/null | tr -d ' ')
echo "  最近10分钟新增: $recent_count"
echo ""

# 3. 检查进程状态（间接方式）
echo "⚡ 进程状态:"
log_activity=$(docker-compose exec app bash -c 'tail -1 /app/backfill.log 2>/dev/null | grep -E "[0-9]{4}-[0-9]{2}-[0-9]{2}" || echo ""')
if [ ! -z "$log_activity" ]; then
    echo "  ✅ 进程看起来正在运行 (日志活跃)"
else
    echo "  ⚠️ 无法确定进程状态"
fi
echo ""

echo "💡 使用提示:"
echo "  - 每5-10分钟运行此脚本查看进度"
echo "  - 回填预计需要19小时完成"
echo "  - 可运行 'docker-compose exec app tail -f /app/backfill.log' 实时查看日志"
echo "======================"