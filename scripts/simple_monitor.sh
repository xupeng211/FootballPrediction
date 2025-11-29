#!/bin/bash
# 简单监控脚本 - 实时查看数据增长

echo "🔍 回填进度监控 - $(date)"
echo "================================"

# 数据库记录数
current_count=$(docker-compose exec db psql -U postgres -d football_prediction -t -c "SELECT COUNT(*) FROM matches;" 2>/dev/null | tr -d ' ')
echo "📊 当前总记录数: $current_count"

# 最近1小时增长
recent_growth=$(docker-compose exec db psql -U postgres -d football_prediction -t -c "SELECT COUNT(*) FROM matches WHERE created_at > NOW() - INTERVAL '1 hour';" 2>/dev/null | tr -d ' ')
echo "📈 最近1小时新增: $recent_growth"

# 检查容器日志中的回填活动
echo "📋 容器日志中的回填活动:"
docker-compose logs --tail=5 app | grep -i "backfill\|数据\|比赛" || echo "  未找到相关日志"

echo ""
echo "💡 提示: 每5分钟运行一次此脚本查看进度"
echo "================================"
