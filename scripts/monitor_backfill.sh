#!/bin/bash
echo "=== URL补全和L2转化实时监控 ==="
echo "开始时间: $(date)"
echo ""

while true; do
    echo "$(date "+%H:%M:%S") 检查进度..."

    # URL补全进度
    url_count=$(docker-compose exec -T db psql -U postgres -d football_prediction -tA -c "
        SELECT COUNT(*) FROM matches WHERE match_metadata->>'match_report_url' IS NOT NULL;
    ")

    # L2转化进度
    complete_count=$(docker-compose exec -T db psql -U postgres -d football_prediction -tA -c "
        SELECT COUNT(*) FROM matches WHERE data_completeness = 'complete';
    ")

    # 待处理记录数
    pending_count=$(docker-compose exec -T db psql -U postgres -d football_prediction -tA -c "
        SELECT COUNT(*) FROM matches
        WHERE data_completeness = 'partial'
          AND match_metadata->>'match_report_url' IS NULL;
    ")

    printf "📊 URL补全: %7d | 🔄 L2转化: %7d | ⏳ 待处理: %7d\n" \
        "$url_count" "$complete_count" "$pending_count"

    # 检查补全程序是否还在运行
    if docker-compose exec -T app pgrep -f backfill_urls.py > /dev/null; then
        echo "🔄 URL补全程序: 运行中"
    else
        echo "⚠️  URL补全程序: 已停止"
    fi

    echo "---"
    sleep 30
done
