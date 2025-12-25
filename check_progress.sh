#!/bin/bash
# ============================================
# V20.8 收割机监控脚本
# ============================================
# 用途: 检查收割进度、最新入库记录、维度分布
# 使用: ./check_progress.sh
# ============================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  V20.8 焦土收割机 - 进度监控仪表板${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# 1. 服务状态检查
echo -e "${BLUE}📡 [1] 服务状态${NC}"
echo "-------------------------------------------"
SERVICE_STATUS=$(docker-compose ps v20_8_harvester --format json 2>/dev/null || echo '{"State":"not found"}')
if echo "$SERVICE_STATUS" | grep -q "Up\|running"; then
    echo -e "  ${GREEN}✓${NC} 收割机服务: ${GREEN}运行中${NC}"
    CONTAINER_NAME=$(docker-compose ps v20_8_harvester --format "{{.Name}}" 2>/dev/null)
    echo "  容器名称: $CONTAINER_NAME"
else
    echo -e "  ${RED}✗${NC} 收割机服务: ${RED}未运行${NC}"
fi
echo ""

# 2. 最近 5 场入库记录
echo -e "${BLUE}💾 [2] 最近 5 场入库记录${NC}"
echo "-------------------------------------------"
docker-compose exec -T db psql -U football_user -d football_db -c "
SELECT
    match_id,
    league_id,
    season_id,
    home_team,
    away_team,
    (meta_data->>'extraction_version') as version,
    (meta_data->>'feature_count') as dimensions,
    CASE
        WHEN updated_at > NOW() - INTERVAL '5 minutes' THEN '← 刚刚'
        WHEN updated_at > NOW() - INTERVAL '1 hour' THEN '← 1小时内'
        ELSE ''
    END as recency
FROM match_features_training
ORDER BY updated_at DESC
LIMIT 5;
" 2>/dev/null || echo "查询失败"
echo ""

# 3. 赛季分布统计
echo -e "${BLUE}📊 [3] 赛季分布统计${NC}"
echo "-------------------------------------------"
docker-compose exec -T db psql -U football_user -d football_db -c "
SELECT
    season_id,
    COUNT(*) as match_count,
    COUNT(CASE WHEN league_id = 47 THEN 1 END) as premier_league,
    COUNT(CASE WHEN league_id = 87 THEN 1 END) as laliga,
    COUNT(CASE WHEN league_id = 55 THEN 1 END) as serie_a,
    COUNT(CASE WHEN league_id = 53 THEN 1 END) as bundesliga,
    COUNT(CASE WHEN league_id = 54 THEN 1 END) as ligue_1
FROM match_features_training
WHERE season_id IS NOT NULL
GROUP BY season_id
ORDER BY season_id;
" 2>/dev/null || echo "查询失败"
echo ""

# 4. 维度达标率
echo -e "${BLUE}🎯 [4] 维度达标率 (目标: ≥881)${NC}"
echo "-------------------------------------------"
docker-compose exec -T db psql -U football_user -d football_db -c "
SELECT
    CASE
        WHEN (meta_data->>'feature_count')::int >= 881 THEN '达标'
        ELSE '未达标'
    END as status,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as percentage
FROM match_features_training
WHERE meta_data->>'feature_count' IS NOT NULL
GROUP BY
    CASE
        WHEN (meta_data->>'feature_count')::int >= 881 THEN '达标'
        ELSE '未达标'
    END
ORDER BY status DESC;
" 2>/dev/null || echo "查询失败"
echo ""

# 5. NULL 标签检查
echo -e "${BLUE}🚨 [5] NULL 标签检查${NC}"
echo "-------------------------------------------"
NULL_COUNT=$(docker-compose exec -T db psql -U football_user -d football_db -t -c "
SELECT COUNT(*) FROM match_features_training
WHERE league_id IS NULL OR season_id IS NULL OR season_id = '';
" 2>/dev/null | tr -d ' ')

if [ -n "$NULL_COUNT" ] && [ "$NULL_COUNT" -eq 0 ]; then
    echo -e "  ${GREEN}✓${NC} 无 NULL 标签记录"
else
    echo -e "  ${YELLOW}⚠${NC} 发现 ${NULL_COUNT:-?} 条 NULL 标签记录"
fi
echo ""

# 6. 最近日志 (可选)
echo -e "${BLUE}📋 [6] 收割机最近日志 (最后10行)${NC}"
echo "-------------------------------------------"
docker-compose logs v20_8_harvester --tail 10 2>/dev/null | grep -E "INFO|ERROR|完成|收割" || echo "无可用日志"
echo ""

echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}监控完成 - 按 Ctrl+C 退出${NC}"
echo -e "${CYAN}============================================${NC}"
