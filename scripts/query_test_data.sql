-- FotMob 冒烟测试数据查询脚本
-- 用于快速验证采集结果
-- Author: DBA
-- Date: 2025-12-05

-- 1. 检查冒烟测试结果表是否存在
\echo '🔍 检查冒烟测试结果表...'
SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name = 'smoke_test_results'
) AS table_exists;

-- 2. 统计测试数据
\echo ''
\echo '📊 测试数据统计...'
SELECT
    collection_type,
    COUNT(*) as total_records,
    COUNT(DISTINCT match_id) as unique_matches,
    MIN(created_at) as first_record,
    MAX(created_at) as last_record
FROM smoke_test_results
GROUP BY collection_type;

-- 3. 查看具体的比赛数据
\echo ''
\echo '⚽ 采集的比赛详情 (最近10条)...'
SELECT
    match_id,
    data->>'l1_data'->>'home'->'name' as home_team,
    data->>'l1_data'->>'away'->'name' as away_team,
    data->>'l1_data'->>'status'->>'reason'->'short' as status,
    data->>'l1_data'->>'league'->>'name' as league,
    CASE
        WHEN data->'l2_data' IS NOT NULL THEN '✅ Available'
        ELSE '❌ Missing'
    END as l2_status,
    created_at
FROM smoke_test_results
WHERE collection_type = 'smoke_test'
ORDER BY created_at DESC
LIMIT 10;

-- 4. 检查L2层数据质量
\echo ''
\echo '📈 L2层数据质量检查...'
SELECT
    match_id,
    (data->'l2_data'->'match_stats'->>'xg') IS NOT NULL as has_xg,
    (data->'l2_data'->'match_stats'->>'shots') IS NOT NULL as has_shots,
    (data->'l2_data'->'players') IS NOT NULL as has_players,
    (data->'l2_data'->'odds') IS NOT NULL as has_odds,
    jsonb_array_length(data->'l2_data'->'players') as player_count
FROM smoke_test_results
WHERE collection_type = 'smoke_test'
  AND data->'l2_data' IS NOT NULL
LIMIT 5;

-- 5. 数据完整性报告
\echo ''
\echo '✅ 数据完整性报告...'
SELECT
    '总比赛数' as metric,
    COUNT(DISTINCT match_id) as value
FROM smoke_test_results
WHERE collection_type = 'smoke_test'

UNION ALL

SELECT
    'L2数据成功数' as metric,
    COUNT(CASE WHEN data->'l2_data' IS NOT NULL THEN 1 END) as value
FROM smoke_test_results
WHERE collection_type = 'smoke_test'

UNION ALL

SELECT
    'L2成功率' as metric,
    ROUND(
        COUNT(CASE WHEN data->'l2_data' IS NOT NULL THEN 1 END) * 100.0 /
        NULLIF(COUNT(DISTINCT match_id), 0), 1
    ) || '%' as value
FROM smoke_test_results
WHERE collection_type = 'smoke_test'

UNION ALL

SELECT
    '平均响应时间(秒)' as metric,
    ROUND(
        AVG(
            EXTRACT(EPOCH FROM (
                (data->>'collected_at')::timestamp - created_at
            ))
        ), 2
    )::text as value
FROM smoke_test_results
WHERE collection_type = 'smoke_test';

-- 6. 按联赛分组统计
\echo ''
\echo '🏆 按联赛分组统计...'
SELECT
    data->>'l1_data'->'league'->'name' as league_name,
    COUNT(*) as match_count,
    COUNT(CASE WHEN data->'l2_data' IS NOT NULL THEN 1 END) as l2_success_count
FROM smoke_test_results
WHERE collection_type = 'smoke_test'
GROUP BY data->>'l1_data'->'league'->'name'
ORDER BY match_count DESC;

-- 7. 采样查看完整的JSON数据结构 (仅显示前200字符)
\echo ''
\echo '📋 数据结构示例 (仅显示部分)...'
SELECT
    match_id,
    LEFT(data::text, 200) || '...' as data_sample
FROM smoke_test_results
WHERE collection_type = 'smoke_test'
LIMIT 1;