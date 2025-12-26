#!/bin/bash
# ============================================
# V32.0 进度哨所 - Full Blood Data Progress Monitor
# ============================================
# 功能: 监控 L2 数据采集进度和特征提取状态
# ============================================

echo "============================================"
echo "V32.0 进度哨所 - Full Blood Data Monitor"
echo "============================================"
echo ""

# 查询数据库中的数据统计
echo "📊 数据库统计:"
echo ""

# 使用 docker-compose exec 查询数据库
docker-compose exec -T db psql -U football_user -d football_db -c "
SELECT
    (SELECT COUNT(*) FROM matches) as total_matches,
    (SELECT COUNT(*) FROM matches WHERE l2_raw_json IS NOT NULL) as l2_collected,
    (SELECT COUNT(*) FROM matches WHERE player_stats IS NOT NULL) as features_extracted,
    (SELECT COUNT(*) FROM matches WHERE actual_result IS NOT NULL) as results_available;
" 2>/dev/null

echo ""
echo "📈 特征维度检查:"
echo ""

# 检查 match_features_training 表
docker-compose exec -T db psql -U football_user -d football_db -c "
SELECT
    COUNT(*) as training_records,
    COUNT(DISTINCT external_id) as unique_matches
FROM match_features_training;
" 2>/dev/null

echo ""
echo "🎯 高维特征提取条件检查:"
echo ""

# 检查具备 3000+ 维度提取条件的比赛
docker-compose exec -T db psql -U football_user -d football_db -c "
SELECT
    COUNT(*) as matches_with_full_data
FROM matches
WHERE l2_raw_json IS NOT NULL
  AND player_stats IS NOT NULL
  AND actual_result IS NOT NULL;
" 2>/dev/null

echo ""
echo "⏱️  采集时间范围:"
echo ""

docker-compose exec -T db psql -U football_user -d football_db -c "
SELECT
    MIN(match_time) as earliest_match,
    MAX(match_time) as latest_match,
    COUNT(*) as total_matches
FROM matches
WHERE l2_raw_json IS NOT NULL;
" 2>/dev/null

echo ""
echo "============================================"
echo "V32.0 进度哨所报告完成"
echo "============================================"
