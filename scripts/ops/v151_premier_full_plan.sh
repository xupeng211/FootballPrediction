#!/bin/bash
# ╔════════════════════════════════════════════════════════════╗
# ║     FootballPrediction - 英超全量补齐计划执行脚本             ║
# ║     版本: V151.3                                               ║
# ║     日期: 2026-01-11                                          ║
# ╚════════════════════════════════════════════════════════════╝

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 配置参数
WORKERS=3
BATCH_SIZE=200
TARGET_RATE=60

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     🏴󠁧󠁢󠁥󠁮󠁧󠁿  英超全量补齐计划 - V151.3                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# ===================================================================
# 0. 环境检查
# ===================================================================
echo -e "${YELLOW}[阶段 0] 环境检查${NC}"
echo "----------------------------"

# 检查数据库
docker-compose exec -T db pg_isready -U football_user -d football_db > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 数据库服务正常${NC}"
else
    echo -e "${RED}❌ 数据库服务未启动${NC}"
    echo "   请运行: make up"
    exit 1
fi

# 检查代理
echo -n "检查代理 (7890-7892): "
for port in 7890 7891 7892; do
    if timeout 2 curl -x http://172.25.16.1:$port -s https://api.ipify.org > /dev/null 2>&1; then
        echo -n ":${port}✓"
    else
        echo -e "${RED} :${port}✗${NC}"
    fi
done
echo ""

# 检查日志目录
mkdir -p logs
echo -e "${GREEN}✅ 日志目录就绪${NC}"
echo ""

# ===================================================================
# 1. 显示当前状态
# ===================================================================
echo -e "${BLUE}[阶段 1] 当前数据状态${NC}"
echo "----------------------------"
docker-compose exec -T db psql -U football_user -d football_db -c "
SELECT
    'matches 表英超' as 项目,
    COUNT(*) as 数量
FROM matches
WHERE league_name = 'Premier League'
UNION ALL
SELECT
    '待获取哈希 URL',
    COUNT(*)
FROM matches_mapping
WHERE league_name = 'Premier League' AND oddsportal_url IS NULL
UNION ALL
SELECT
    '待采集 (有 URL)',
    COUNT(*)
FROM matches_mapping
WHERE league_name = 'Premier League' AND oddsportal_url IS NOT NULL AND l2_raw_json IS NULL
UNION ALL
SELECT
    '已完成采集',
    COUNT(*)
FROM matches_mapping
WHERE league_name = 'Premier League' AND l2_raw_json IS NOT NULL;
" 2>&1 | grep -v "level=warning"
echo ""

# ===================================================================
# 2. 哈希狩猎阶段 (分批处理 1,868 场)
# ===================================================================
echo -e "${YELLOW}[阶段 2] 哈希狩猎阶段 (1,868 场)${NC}"
echo "----------------------------"
echo "策略: 分 10 批，每批 187 场"
echo ""

for round in {1..10}; do
    echo -e "${BLUE}🔄 第 ${round}/10 批哈希狩猎${NC}"
    python scripts/ops/hunt_league_hashes.py \
        --premier \
        --limit 187 \
        --delay-min 5 \
        --delay-max 10

    # 显示进度
    PENDING=$(docker-compose exec -T db psql -U football_user -d football_db -t -c "
        SELECT COUNT(*) FROM matches_mapping
        WHERE league_name = 'Premier League' AND oddsportal_url IS NULL
    " 2>&1 | grep -v "level=warning" | tr -d ' ')

    echo -e "${GREEN}  ✅ 完成 ${round}/10 批，剩余待获取: ${PENDING} 场${NC}"
    echo ""

    # 每 5 批同步一次缓存
    if [ $((round % 5)) -eq 0 ]; then
        echo -e "${YELLOW}  📦 同步缓存...${NC}"
        python scripts/ops/hunt_league_hashes.py --sync-cache
        echo ""
    fi
done

# 最终缓存同步
echo -e "${YELLOW}📦 最终缓存同步${NC}"
python scripts/ops/hunt_league_hashes.py --sync-cache
echo ""

# ===================================================================
# 3. 并发收割阶段
# ===================================================================
echo -e "${YELLOW}[阶段 3] 并发收割阶段${NC}"
echo "----------------------------"
echo "配置: ${WORKERS} Workers × ${BATCH_SIZE} 场/批"
echo "目标: 采集率 > ${TARGET_RATE}%"
echo ""

# 计算当前采集率
get_rate() {
    docker-compose exec -T db psql -U football_user -d football_db -t -c "
        SELECT ROUND(
            100.0 * COUNT(DISTINCT CASE WHEN l2_raw_json IS NOT NULL THEN fotmob_id END) /
            NULLIF(COUNT(DISTINCT fotmob_id), 0),
            2
        ) FROM matches_mapping
        WHERE league_name = 'Premier League'
    " 2>&1 | grep -v "level=warning" | tr -d ' '
}

CURRENT_RATE=$(get_rate)
echo -e "${BLUE}📊 当前采集率: ${CURRENT_RATE}%${NC}"
echo ""

# 持续收割直到达到目标
HARVEST_ROUND=1
while true; do
    echo -e "${BLUE}🔄 第 ${HARVEST_ROUND} 轮收割开始${NC}"

    # 运行并发收割器
    python scripts/ops/harvest_pinnacle_concurrent.py \
        --workers ${WORKERS} \
        --limit ${BATCH_SIZE} \
        --delay-min 20 \
        --delay-max 40

    HARVEST_EXIT=$?
    echo ""

    # 检查新的采集率
    NEW_RATE=$(get_rate)
    echo -e "${BLUE}📊 当前采集率: ${NEW_RATE}% (之前: ${CURRENT_RATE}%)${NC}"

    # 检查是否达到目标
    if (( $(echo "$NEW_RATE >= $TARGET_RATE" | bc -l) )); then
        echo ""
        echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║              🎉 恭喜！英超采集任务完成！                    ║${NC}"
        echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        echo -e "${GREEN}目标采集率: ${TARGET_RATE}%${NC}"
        echo -e "${GREEN}实际采集率: ${NEW_RATE}%${NC}"
        echo -e "${GREEN}收割轮数: ${HARVEST_ROUND}${NC}"
        echo ""
        break
    fi

    CURRENT_RATE=$NEW_RATE
    HARVEST_ROUND=$((HARVEST_ROUND + 1))

    # 如果收割器异常退出，等待 5 分钟后重试
    if [ $HARVEST_EXIT -ne 0 ]; then
        echo -e "${RED}⚠️ 收割器异常退出 (退出码: ${HARVEST_EXIT})${NC}"
        echo -e "${YELLOW}⏳ 等待 5 分钟后重试...${NC}"
        sleep 300
    else
        echo -e "${YELLOW}⏳ 等待 2 分钟后继续下一轮...${NC}"
        sleep 120
    fi
done

# ===================================================================
# 4. 最终报告
# ===================================================================
echo ""
echo -e "${BLUE}[阶段 4] 最终数据报告${NC}"
echo "----------------------------"
docker-compose exec -T db psql -U football_user -d football_db -c "
SELECT
    status as 状态,
    COUNT(*) as 数量,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) as 百分比
FROM matches_mapping
WHERE league_name = 'Premier League'
GROUP BY status
ORDER BY status
" 2>&1 | grep -v "level=warning"
echo ""

echo -e "${GREEN}✅ 英超全量补齐计划执行完成！${NC}"
echo ""
echo "📝 后续建议:"
echo "  1. 查看详细日志: tail -f logs/harvest_pinnacle_concurrent.log"
echo "  2. 查看战果报告: cat logs/concurrent_harvest_report.json"
echo "  3. 数据质量检查: python scripts/ops/check_db_consistency.py --league 'Premier League'"
echo ""
