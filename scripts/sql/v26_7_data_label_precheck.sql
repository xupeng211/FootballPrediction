-- ============================================================================
-- V26.7 数据标签预检查脚本
-- 目的：在执行清洗前诊断数据问题
--
-- 使用方法：
--   docker exec football_prediction_db psql -U football_user -d football_prediction_dev -f scripts/sql/v26_7_data_label_precheck.sql
--
-- 此脚本不会修改任何数据，仅用于诊断
-- ============================================================================

\echo '================================================================================'
\echo 'V26.7 数据标签预检查报告'
\echo '================================================================================'
\echo ''

-- ============================================================================
-- 1. 整体数据概况
-- ============================================================================
\echo '>>> 1. 整体数据概况 <<<'
\echo ''
\echo '总记录数:'
SELECT COUNT(*) as total_matches FROM matches;

\echo ''
\echo '按赛季统计:'
SELECT
    season,
    COUNT(*) as count
FROM matches
GROUP BY season
ORDER BY season DESC;

\echo ''
\echo '按联赛统计（Top 15）:'
SELECT
    league_name,
    COUNT(*) as count
FROM matches
GROUP BY league_name
ORDER BY count DESC
LIMIT 15;

-- ============================================================================
-- 2. 数据质量问题诊断
-- ============================================================================
\echo ''
\echo '>>> 2. 数据质量问题诊断 <<<'
\echo ''

\echo 'Unknown League 标记的记录:'
SELECT
    match_id,
    home_team,
    away_team,
    league_name,
    season,
    created_at
FROM matches
WHERE league_name = 'Unknown League'
ORDER BY created_at DESC
LIMIT 10;

\echo ''
\echo '可能的错误标记（以色列球队被标记为其他联赛）:'
SELECT
    m.match_id,
    m.home_team,
    m.away_team,
    m.league_name as current_league,
    m.season,
    CASE
        WHEN m.league_name = 'Eredivisie' THEN '应改为: Israeli Premier League (以色列联赛被误标为荷甲)'
        WHEN m.league_name = 'Serie B' THEN '应改为: Israeli Premier League (以色列联赛被误标为意乙)'
        ELSE '需要人工确认'
    END as suggested_fix
FROM matches m
WHERE (m.home_team LIKE '%Maccabi%'
    OR m.home_team LIKE '%Hapoel%'
    OR m.home_team LIKE '%Beitar%'
    OR m.home_team LIKE '%Ironi%'
    OR m.home_team LIKE '%Bnei%'
    OR m.away_team LIKE '%Maccabi%'
    OR m.away_team LIKE '%Hapoel%'
    OR m.away_team LIKE '%Beitar%'
    OR m.away_team LIKE '%Ironi%'
    OR m.away_team LIKE '%Bnei%')
AND m.league_name NOT IN ('Premier League', 'La Liga', 'Serie A', 'Bundesliga', 'Ligue 1')
ORDER BY m.created_at DESC
LIMIT 20;

\echo ''
\echo '英超 24/25 赛季记录抽样（验证修复效果）:'
SELECT
    match_id,
    home_team,
    away_team,
    league_name,
    season,
    collection_status,
    created_at
FROM matches
WHERE season = '2425'
  AND league_name = 'Premier League'
ORDER BY created_at DESC
LIMIT 10;

-- ============================================================================
-- 3. 修复影响评估
-- ============================================================================
\echo ''
\echo '>>> 3. 修复影响评估 <<<'
\echo ''

\echo '将被修复的记录数量（以色列球队）:'
SELECT
    league_name as current_wrong_label,
    COUNT(*) as affected_count
FROM matches
WHERE (home_team LIKE '%Maccabi%'
    OR home_team LIKE '%Hapoel%'
    OR home_team LIKE '%Beitar%'
    OR home_team LIKE '%Ironi%'
    OR home_team LIKE '%Bnei%'
    OR away_team LIKE '%Maccabi%'
    OR away_team LIKE '%Hapoel%'
    OR away_team LIKE '%Beitar%'
    OR away_team LIKE '%Ironi%'
    OR away_team LIKE '%Bnei%')
AND league_name NOT IN ('Premier League', 'La Liga', 'Serie A', 'Bundesliga', 'Ligue 1')
GROUP BY league_name;

-- ============================================================================
-- 4. 推荐操作
-- ============================================================================
\echo ''
\echo '>>> 4. 推荐操作 <<<'
\echo ''

\echo '推荐修复操作清单:'
SELECT
    '修复以色列联赛标记' as operation,
    COUNT(*) as affected_records,
    'UPDATE matches SET league_name = ''Israeli Premier League'' WHERE ...' as sql_example
FROM matches
WHERE (home_team LIKE '%Maccabi%'
    OR home_team LIKE '%Hapoel%'
    OR home_team LIKE '%Beitar%'
    OR home_team LIKE '%Ironi%'
    OR home_team LIKE '%Bnei%'
    OR away_team LIKE '%Maccabi%'
    OR away_team LIKE '%Hapoel%'
    OR away_team LIKE '%Beitar%'
    OR away_team LIKE '%Ironi%'
    OR away_team LIKE '%Bnei%')
AND league_name IN ('Eredivisie', 'Serie B');

\echo ''
\echo '================================================================================'
\echo '预检查完成！请根据上述报告决定是否执行数据清洗。'
\echo '如需执行清洗，请运行: v26_7_data_label_cleanup.sql'
\echo '================================================================================'
