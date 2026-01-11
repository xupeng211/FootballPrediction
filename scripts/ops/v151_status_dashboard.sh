#!/bin/bash
# V151.3 → V32.1 采集状态仪表盘
# 用途: 实时查看采集进度和统计数据 + 数据库连接监控
# 日期: 2026-01-11

echo "╔════════════════════════════════════════════════════════════╗"
echo "║        V32.1 采集状态仪表盘 (含数据库连接监控)               ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 激活虚拟环境（如果使用）
# source venv/bin/activate

# ===================================================================
# 1. 整体采集率
# ===================================================================
echo "📊 整体采集率"
echo "----------------------------"
psql -U football_user -d football_db -c "
SELECT
    COUNT(DISTINCT fotmob_id) as total_matches,
    COUNT(DISTINCT CASE WHEN l2_raw_json IS NOT NULL THEN fotmob_id END) as harvested,
    ROUND(
        100.0 * COUNT(DISTINCT CASE WHEN l2_raw_json IS NOT NULL THEN fotmob_id END) /
        NULLIF(COUNT(DISTINCT fotmob_id), 0),
        2
    ) as collection_rate
FROM matches_mapping
WHERE oddsportal_url IS NOT NULL
" 2>/dev/null

echo ""

# ===================================================================
# 2. 按联赛统计
# ===================================================================
echo "📊 按联赛统计"
echo "----------------------------"
psql -U football_user -d football_db -c "
SELECT
    league_name,
    COUNT(DISTINCT fotmob_id) as total,
    COUNT(DISTINCT CASE WHEN l2_raw_json IS NOT NULL THEN fotmob_id END) as harvested,
    ROUND(
        100.0 * COUNT(DISTINCT CASE WHEN l2_raw_json IS NOT NULL THEN fotmob_id END) /
        NULLIF(COUNT(DISTINCT fotmob_id), 0),
        2
    ) as rate_pct
FROM matches_mapping
WHERE oddsportal_url IS NOT NULL
GROUP BY league_name
ORDER BY harvested DESC
LIMIT 10
" 2>/dev/null

echo ""

# ===================================================================
# 3. 按状态统计
# ===================================================================
echo "📊 按状态统计"
echo "----------------------------"
psql -U football_user -d football_db -c "
SELECT
    status,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) as percentage
FROM matches_mapping
WHERE oddsportal_url IS NOT NULL
GROUP BY status
ORDER BY status
" 2>/dev/null

echo ""

# ===================================================================
# 4. 待采集数量
# ===================================================================
echo "📊 待采集队列"
echo "----------------------------"
psql -U football_user -d football_db -c "
SELECT
    COUNT(*) as pending_count,
    COUNT(CASE WHEN status = 'pending' THEN 1 END) as ready_to_harvest
FROM matches_mapping
WHERE oddsportal_url IS NOT NULL
  AND l2_raw_json IS NULL
" 2>/dev/null

echo ""

# ===================================================================
# 5. 数据库连接监控 (V32.1)
# ===================================================================
echo "📊 数据库连接监控 (V32.1)"
echo "----------------------------"
psql -U football_user -d football_db -c "
SELECT
    COUNT(*) as total_connections,
    COUNT(CASE WHEN state = 'active' THEN 1 END) as active_connections,
    COUNT(CASE WHEN state = 'idle' THEN 1 END) as idle_connections,
    COUNT(CASE WHEN state = 'idle in transaction' THEN 1 END) as idle_in_transaction
FROM pg_stat_activity
WHERE datname = 'football_db'
" 2>/dev/null

echo ""
echo "当前连接详情 (最近 10 条):"
psql -U football_user -d football_db -c "
SELECT
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query_start,
    state_change
FROM pg_stat_activity
WHERE datname = 'football_db'
ORDER BY state_change DESC
LIMIT 10
" 2>/dev/null

echo ""

# ===================================================================
# 6. 漏斗审计 (Data Funnel Audit) - V33.0
# ===================================================================
echo "📊 漏斗审计 (V33.0)"
echo "----------------------------"

# 6.1 Unmatched Teams 记录数
echo "🔴 无法匹配队名记录:"
if [ -f "logs/unmatched_teams.json" ]; then
    UNMATCHED_COUNT=$(python3 -c "import json; data=json.load(open('logs/unmatched_teams.json')); print(len(data) if isinstance(data, list) else 0)" 2>/dev/null || echo "0")
    echo "   unmatched_teams.json 记录数: ${UNMATCHED_COUNT}"

    # 按联赛统计
    python3 -c "
import json
try:
    with open('logs/unmatched_teams.json', 'r') as f:
        data = json.load(f)
    if isinstance(data, list):
        leagues = {}
        for item in data:
            league = item.get('league_name', 'Unknown')
            leagues[league] = leagues.get(league, 0) + 1
        print('   按联赛分布:')
        for league, count in sorted(leagues.items(), key=lambda x: -x[1])[:5]:
            print(f'     - {league}: {count}')
except:
    pass
" 2>/dev/null
else
    echo "   unmatched_teams.json 不存在"
fi

echo ""

# 6.2 Abandoned 记录百分比
echo "🟠 已放弃记录 (Abandoned) 比例:"
psql -U football_user -d football_db -c "
SELECT
    COUNT(*) FILTER (WHERE retry_count >= 3) as abandoned_count,
    COUNT(*) as total_count,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE retry_count >= 3) /
        NULLIF(COUNT(*), 0),
        2
    ) as abandoned_pct
FROM matches_mapping
WHERE oddsportal_url IS NOT NULL
" 2>/dev/null

echo ""

# ===================================================================
# 7. 哈希缓存状态
# ===================================================================
echo "📊 哈希缓存状态"
echo "----------------------------"
if [ -f "logs/hash_hunt_cache.json" ]; then
    CACHE_COUNT=$(python3 -c "import json; print(len(json.load(open('logs/hash_hunt_cache.json')).get('records', [])))" 2>/dev/null || echo "0")
    echo "待同步缓存记录: ${CACHE_COUNT}"
else
    echo "缓存文件不存在"
fi

echo ""

# ===================================================================
# 8. 最近活动
# ===================================================================
echo "📊 最近活动 (最近 5 条)"
echo "----------------------------"
psql -U football_user -d football_db -c "
SELECT
    league_name,
    status,
    updated_at
FROM matches_mapping
WHERE oddsportal_url IS NOT NULL
ORDER BY updated_at DESC
LIMIT 5
" 2>/dev/null

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "💡 快速操作:"
echo "  - 运行哈希狩猎: python scripts/ops/hunt_league_hashes.py --limit 100"
echo "  - 运行并发收割: python scripts/ops/harvest_pinnacle_concurrent.py --workers 3"
echo "  - 查看完整日志: tail -f logs/harvest_pinnacle_concurrent.log"
echo "═══════════════════════════════════════════════════════════"
echo ""
