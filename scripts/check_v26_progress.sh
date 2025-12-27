#!/bin/bash
# V26.0 进度监控脚本

echo "================================================================"
echo "📊 V26.0 进度监控"
echo "================================================================"
echo "当前时间: $(date '+%H:%M:%S')"
echo ""

echo "📡 L2 原始数据状态:"
docker-compose exec -T db psql -U football_user -d football_prediction_dev -c "
SELECT 'L2 raw_match_data' as source, COUNT(*) as count FROM raw_match_data;
" 2>/dev/null || echo "  (无法连接)"

echo ""
echo "🔬 L3 特征提取状态:"
docker-compose exec -T db psql -U football_user -d football_prediction_dev -c "
SELECT feature_version, COUNT(*) as count
FROM match_features_training
GROUP BY feature_version
ORDER BY feature_version;
" 2>/dev/null || echo "  (无法连接)"

echo ""
echo "================================================================"
