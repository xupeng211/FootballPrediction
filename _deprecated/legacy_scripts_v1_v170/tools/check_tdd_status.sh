#!/bin/bash
###############################################################################
# V37.6 TDD Status Check - 生产线全景视图
#
# 用途：查看全链路自动化系统运行状态 + 生产线指标
#
# Author: SRE Team
# Version: V37.6 Production Line Dashboard (Bad Debt Rate Monitoring)
# Date: 2026-01-12
###############################################################################

echo "══════════════════════════════════════════════════════════════════"
echo "🏭 V37.6 生产线全景视图"
echo "══════════════════════════════════════════════════════════════════"
echo ""

# ============================================================================
# 1. EventBus 状态 (V37.4 Event-Driven Architecture)
# ============================================================================
echo "🚀 [1/10] EventBus 状态 (V37.4 Event-Driven):"
if ps aux | grep -v grep | grep "src.services.event_bus" > /dev/null; then
    EVENTBUS_PID=$(cat logs/eventbus.pid 2>/dev/null || echo "未知")
    echo "   ✅ 运行中 (PID: $EVENTBUS_PID)"
    echo "   监听频道: matches_insert → odds_updated"
    echo "   日志: logs/eventbus_v37.log"
    echo "   最近日志:"
    tail -3 logs/eventbus_v37.log 2>/dev/null | grep -v "^$" | head -3 | sed 's/^/     /'
else
    echo "   ❌ 未运行"
    echo "   启动: ./scripts/ops/start_eventbus.sh"
fi
echo ""

# ============================================================================
# 2. 生产线指标 - A → B (matches_insert → URL mapping)
# ============================================================================
echo "📊 [2/10] 生产线指标: A → B (Layer B URL Mapping)"

# 查询最近 1 小时的 A→B 转换情况
RESULT_AB=$(docker-compose exec -T db psql -U football_user -d football_db -t -c "
WITH recent_matches AS (
    SELECT match_id, league_name, match_date,
           EXTRACT(EPOCH FROM (NOW() - match_date)) as seconds_ago
    FROM matches
    WHERE match_date >= NOW() - INTERVAL '1 hour'
),
mapped_matches AS (
    SELECT m.match_id,
           mm.oddsportal_url IS NOT NULL as has_url,
           EXTRACT(EPOCH FROM (NOW() - m.match_date)) as seconds_to_map
    FROM recent_matches m
    LEFT JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
)
SELECT
    COUNT(*) as total_a,
    COUNT(CASE WHEN has_url THEN 1 END) as success_b,
    ROUND(100.0 * COUNT(CASE WHEN has_url THEN 1 END) / COUNT(*), 2) as success_rate,
    ROUND(AVG(CASE WHEN has_url THEN seconds_to_map END), 2) as avg_seconds
FROM mapped_matches;
" 2>/dev/null)

if [ -n "$RESULT_AB" ]; then
    TOTAL_A=$(echo "$RESULT_AB" | head -1 | awk '{print $1}')
    SUCCESS_B=$(echo "$RESULT_AB" | head -1 | awk '{print $2}')
    SUCCESS_RATE=$(echo "$RESULT_AB" | head -1 | awk '{print $3}')
    AVG_SECONDS=$(echo "$RESULT_AB" | head -1 | awk '{print $4}')

    echo "   总输入 (A): $TOTAL_A 场"
    echo "   成功输出 (B): $SUCCESS_B 场"
    echo "   成功率: ${SUCCESS_RATE}%"
    echo "   平均耗时: ${AVG_SECONDS}s"

    # 准入红线判定
    if (( $(echo "$SUCCESS_RATE >= 80.0" | bc -l) )); then
        echo "   ✅ A→B 流水线正常"
    else
        echo "   ⚠️  A→B 成功率低于 80% (准入红线)"
    fi
else
    echo "   ⚠️  查询失败或无数据"
fi
echo ""

# ============================================================================
# 3. 生产线指标 - B → C (URL found → Odds harvested)
# ============================================================================
echo "📊 [3/10] 生产线指标: B → C (Layer C Odds Harvest)"

RESULT_BC=$(docker-compose exec -T db psql -U football_user -d football_db -t -c "
WITH urls_found AS (
    SELECT fotmob_id, match_date, oddsportal_url
    FROM matches_mapping
    WHERE oddsportal_url IS NOT NULL
      AND match_date >= NOW() - INTERVAL '1 hour'
),
odds_harvested AS (
    SELECT mm.fotmob_id,
           m.l3_odds_data IS NOT NULL as has_odds,
           EXTRACT(EPOCH FROM (NOW() - mm.match_date)) as seconds_to_harvest
    FROM urls_found mm
    LEFT JOIN matches m ON mm.fotmob_id = m.match_id
)
SELECT
    COUNT(*) as total_b,
    COUNT(CASE WHEN has_odds THEN 1 END) as success_c,
    ROUND(100.0 * COUNT(CASE WHEN has_odds THEN 1 END) / COUNT(*), 2) as success_rate,
    ROUND(AVG(CASE WHEN has_odds THEN seconds_to_harvest END), 2) as avg_seconds
FROM odds_harvested;
" 2>/dev/null)

if [ -n "$RESULT_BC" ]; then
    TOTAL_B=$(echo "$RESULT_BC" | head -1 | awk '{print $1}')
    SUCCESS_C=$(echo "$RESULT_BC" | head -1 | awk '{print $2}')
    SUCCESS_RATE=$(echo "$RESULT_BC" | head -1 | awk '{print $3}')
    AVG_SECONDS=$(echo "$RESULT_BC" | head -1 | awk '{print $4}')

    echo "   总输入 (B): $TOTAL_B 场"
    echo "   成功输出 (C): $SUCCESS_C 场"
    echo "   成功率: ${SUCCESS_RATE}%"
    echo "   平均耗时: ${AVG_SECONDS}s"

    if (( $(echo "$SUCCESS_RATE >= 70.0" | bc -l) )); then
        echo "   ✅ B→C 流水线正常"
    else
        echo "   ⚠️  B→C 成功率低于 70% (准入红线)"
    fi
else
    echo "   ⚠️  查询失败或无数据"
fi
echo ""

# ============================================================================
# 4. 生产线指标 - C → D (l3_odds_data → Features extracted)
# ============================================================================
echo "📊 [4/10] 生产线指标: C → D (Layer D Feature Extraction)"

RESULT_CD=$(docker-compose exec -T db psql -U football_user -d football_db -t -c "
WITH odds_harvested AS (
    SELECT match_id, l3_odds_data, match_date
    FROM matches
    WHERE l3_odds_data IS NOT NULL
      AND match_date >= NOW() - INTERVAL '1 hour'
),
features_extracted AS (
    SELECT m.match_id,
           mf.payout_ratio IS NOT NULL as has_features,
           EXTRACT(EPOCH FROM (NOW() - m.match_date)) as seconds_to_extract
    FROM odds_harvested m
    LEFT JOIN match_features mf ON m.match_id = mf.match_id
)
SELECT
    COUNT(*) as total_c,
    COUNT(CASE WHEN has_features THEN 1 END) as success_d,
    ROUND(100.0 * COUNT(CASE WHEN has_features THEN 1 END) / COUNT(*), 2) as success_rate,
    ROUND(AVG(CASE WHEN has_features THEN seconds_to_extract END), 2) as avg_seconds
FROM features_extracted;
" 2>/dev/null)

if [ -n "$RESULT_CD" ]; then
    TOTAL_C=$(echo "$RESULT_CD" | head -1 | awk '{print $1}')
    SUCCESS_D=$(echo "$RESULT_CD" | head -1 | awk '{print $2}')
    SUCCESS_RATE=$(echo "$RESULT_CD" | head -1 | awk '{print $3}')
    AVG_SECONDS=$(echo "$RESULT_CD" | head -1 | awk '{print $4}')

    echo "   总输入 (C): $TOTAL_C 场"
    echo "   成功输出 (D): $SUCCESS_D 场"
    echo "   成功率: ${SUCCESS_RATE}%"
    echo "   平均耗时: ${AVG_SECONDS}s"

    if (( $(echo "$SUCCESS_RATE >= 90.0" | bc -l) )); then
        echo "   ✅ C→D 流水线正常"
    else
        echo "   ⚠️  C→D 成功率低于 90% (准入红线)"
    fi
else
    echo "   ⚠️  查询失败或无数据"
fi
echo ""

# ============================================================================
# 5. 全链路 A → D 端到端指标
# ============================================================================
echo "📊 [5/10] 全链路 A → D 端到端指标:"

RESULT_AD=$(docker-compose exec -T db psql -U football_user -d football_db -t -c "
WITH input_a AS (
    SELECT match_id
    FROM matches
    WHERE match_date >= NOW() - INTERVAL '1 hour'
),
output_d AS (
    SELECT m.match_id
    FROM input_a m
    JOIN match_features mf ON m.match_id = mf.match_id
    WHERE mf.payout_ratio IS NOT NULL
)
SELECT
    (SELECT COUNT(*) FROM input_a) as total_a,
    (SELECT COUNT(*) FROM output_d) as total_d,
    ROUND(100.0 * (SELECT COUNT(*) FROM output_d) / NULLIF((SELECT COUNT(*) FROM input_a), 0), 2) as e2e_rate;
" 2>/dev/null)

if [ -n "$RESULT_AD" ]; then
    TOTAL_A=$(echo "$RESULT_AD" | head -1 | awk '{print $1}')
    TOTAL_D=$(echo "$RESULT_AD" | head -1 | awk '{print $2}')
    E2E_RATE=$(echo "$RESULT_AD" | head -1 | awk '{print $3}')

    echo "   输入 (A): $TOTAL_A 场"
    echo "   输出 (D): $TOTAL_D 场"
    echo "   端到端成功率: ${E2E_RATE}%"

    # Boss 准入红线
    if (( $(echo "$E2E_RATE >= 50.0" | bc -l) )); then
        echo "   ✅ 全链路自动化 PASSED (Boss 准入红线)"
    else
        echo "   ❌ 全链路自动化 FAILED (低于 Boss 准入红线 50%)"
        echo "   🚨 禁止进入无人值守状态！"
    fi
else
    echo "   ⚠️  查询失败或无数据"
fi
echo ""

# ============================================================================
# 6. 8 Workers 状态 (进程安全阀)
# ============================================================================
echo "⚙️  [6/10] 8 Workers 状态 (进程安全阀):"
WORKER_COUNT=$(ps aux | grep -v grep | grep "harvest_pinnacle_concurrent.py" | wc -l)
echo "   当前活跃进程: $WORKER_COUNT 个"
echo "   进程安全阀限制: 8 个"
if [ "$WORKER_COUNT" -le 8 ]; then
    echo "   ✅ 进程数量在安全范围内"
else
    echo "   ❌ 进程数量超出安全阀！"
fi
echo ""

# ============================================================================
# 7. 失败特征记录
# ============================================================================
echo "📋 [7/10] 失败特征记录:"
if [ -f "logs/failed_features.json" ]; then
    FAILED_COUNT=$(jq '. | length' logs/failed_features.json 2>/dev/null || echo "0")
    echo "   记录数: $FAILED_COUNT"
    if [ "$FAILED_COUNT" -gt 0 ]; then
        echo "   ⚠️  最近失败:"
        jq -r '.[-1] | "   - Match: \(.match_id), Reason: \(.reason)"' logs/failed_features.json 2>/dev/null
    else
        echo "   ✅ 无失败记录"
    fi
else
    echo "   ✅ 文件不存在（无失败）"
fi
echo ""

# ============================================================================
# 9. V37.6 坏账率指标 (Bad Debt Rate)
# ============================================================================
echo "📊 [9/10] V37.6 坏账率指标 (Has Odds but No Feature):"
docker-compose exec -T db psql -U football_user -d football_db -t -c "
SELECT
    COUNT(*) as total_with_odds,
    COUNT(CASE WHEN mf.payout_ratio IS NULL OR mf.payout_ratio = 0 THEN 1 END) as bad_debt,
    COUNT(CASE WHEN mf.payout_ratio IS NOT NULL AND mf.payout_ratio > 0 THEN 1 END) as good_debt,
    ROUND(100.0 * COUNT(CASE WHEN mf.payout_ratio IS NOT NULL AND mf.payout_ratio > 0 THEN 1 END) / COUNT(*), 2) as success_rate
FROM matches m
LEFT JOIN match_features mf ON m.match_id = mf.match_id
WHERE m.l3_odds_data IS NOT NULL;
" 2>/dev/null | sed 's/^/   /'

# 准入红线判定
BAD_DEBT_RATE=$(docker-compose exec -T db psql -U football_user -d football_db -t -c "
SELECT ROUND(100.0 * COUNT(CASE WHEN mf.payout_ratio IS NULL OR mf.payout_ratio = 0 THEN 1 END) / COUNT(*), 2)
FROM matches m
LEFT JOIN match_features mf ON m.match_id = mf.match_id
WHERE m.l3_odds_data IS NOT NULL;
" 2>/dev/null | xargs)

if [ -n "$BAD_DEBT_RATE" ]; then
    # 转换为数字比较
    BAD_RATE_NUM=$(echo "$BAD_DEBT_RATE" | tr -d ' ')
    if (( $(echo "$BAD_RATE_NUM <= 5.0" | bc -l) )); then
        echo "   ✅ 坏账率: ${BAD_DEBT_RATE}% (准入红线: <= 5%)"
    else
        echo "   ❌ 坏账率: ${BAD_DEBT_RATE}% (超过准入红线 5%)"
        echo "   🚨 禁止启动 8 Workers 全量收集！"
    fi
fi

echo ""

# ============================================================================
# 10. payout_ratio 总体指标
# ============================================================================
echo "📊 [10/10] payout_ratio 总体指标:"
docker-compose exec -T db psql -U football_user -d football_db -t -c "
SELECT
    COUNT(*) as total,
    COUNT(payout_ratio) as with_payout,
    ROUND(100.0 * COUNT(payout_ratio) / COUNT(*), 2) as percentage
FROM match_features;
" 2>/dev/null | sed 's/^/   /'

echo ""
echo "══════════════════════════════════════════════════════════════════"
echo "💡 快捷命令:"
echo "   查看 EventBus 日志: tail -f logs/eventbus_v37.log"
echo "   查看同步日志:     tail -f logs/auto_sync_v2_nohup.log"
echo "   停止 EventBus:    kill \$(cat logs/eventbus.pid)"
echo "   重启 EventBus:    ./scripts/ops/start_eventbus.sh"
echo ""
echo "🎯 准入红线:"
echo "   A→B 成功率 >= 80%"
echo "   B→C 成功率 >= 70%"
echo "   C→D 成功率 >= 90%"
echo "   全链路 A→D >= 50% (Boss 准入红线)"
echo "══════════════════════════════════════════════════════════════════"
