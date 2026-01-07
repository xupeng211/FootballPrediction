-- ============================================================================
-- V26.7 数据标签清洗脚本
-- 目的：修复历史数据中错误的 league_name 标记
--
-- 使用方法：
--   docker exec football_prediction_db psql -U football_user -d football_prediction_dev -f scripts/sql/v26_7_data_label_cleanup.sql
--
-- 注意：执行前请先运行预检查脚本查看需要修复的记录数量
-- ============================================================================

\echo '================================================================================'
\echo 'V26.7 数据标签清洗脚本'
\echo '================================================================================'
\timing on

-- ============================================================================
-- Step 1: 诊断报告 - 显示当前数据问题
-- ============================================================================
\echo ''
\echo '>>> Step 1: 诊断报告 <<<'
\echo ''

-- 显示各联赛的记录数
\echo '当前各联赛记录统计:'
SELECT
    league_name,
    season,
    COUNT(*) as count
FROM matches
GROUP BY league_name, season
ORDER BY count DESC
LIMIT 20;

-- 显示可能的错误标记（通过队名推断）
\echo ''
\echo '可能的错误标记（以色列球队被标记为其他联赛）:'
SELECT
    match_id,
    home_team,
    away_team,
    league_name,
    season
FROM matches
WHERE (home_team LIKE '%Maccabi%'
    OR home_team LIKE '%Hapoel%'
    OR home_team LIKE '%Beitar%'
    OR home_team LIKE '%Ironi%'
    OR away_team LIKE '%Maccabi%'
    OR away_team LIKE '%Hapoel%'
    OR away_team LIKE '%Beitar%'
    OR away_team LIKE '%Ironi%')
AND league_name NOT IN ('Premier League', 'La Liga', 'Serie A', 'Bundesliga', 'Ligue 1', 'Serie B', 'Eredivisie')
ORDER BY created_at DESC
LIMIT 20;

-- ============================================================================
-- Step 2: 创建修复映射表
-- ============================================================================
\echo ''
\echo '>>> Step 2: 创建修复映射表 <<<'
\echo ''

DROP TABLE IF EXISTS league_name_fixes;
CREATE TEMP TABLE league_name_fixes (
    old_league_name VARCHAR(100),
    new_league_name VARCHAR(100),
    reason TEXT
);

-- 插入已知的修复规则
INSERT INTO league_name_fixes VALUES
    ('Eredivisie', 'Israeli Premier League', '以色列球队被误标为荷甲'),
    ('Serie B', 'Israeli Premier League', '以色列球队被误标为意乙'),
    ('Unknown League', 'Unknown League', '保留用于后续处理');

\echo '修复映射表已创建:'
SELECT * FROM league_name_fixes;

-- ============================================================================
-- Step 3: 执行修复
-- ============================================================================
\echo ''
\echo '>>> Step 3: 执行修复 <<<'
\echo ''

-- 显示即将修复的记录
\echo '即将修复的记录（预览）:'
SELECT
    m.match_id,
    m.home_team,
    m.away_team,
    m.league_name as old_league,
    f.new_league_name,
    f.reason
FROM matches m
JOIN league_name_fixes f ON m.league_name = f.old_league_name
WHERE m.home_team LIKE '%Maccabi%'
    OR m.home_team LIKE '%Hapoel%'
    OR m.home_team LIKE '%Beitar%'
    OR m.home_team LIKE '%Ironi%'
    OR m.away_team LIKE '%Maccabi%'
    OR m.away_team LIKE '%Hapoel%'
    OR m.away_team LIKE '%Beitar%'
    OR m.away_team LIKE '%Ironi%'
LIMIT 10;

-- 执行修复
\echo ''
\echo '正在执行修复...'

-- 修复以色列球队标记错误的记录
UPDATE matches m
SET league_name = 'Israeli Premier League',
    updated_at = NOW()
WHERE m.league_name IN ('Eredivisie', 'Serie B')
AND (
    m.home_team LIKE '%Maccabi%'
    OR m.home_team LIKE '%Hapoel%'
    OR m.home_team LIKE '%Beitar%'
    OR m.home_team LIKE '%Ironi%'
    OR m.away_team LIKE '%Maccabi%'
    OR m.away_team LIKE '%Hapoel%'
    OR m.away_team LIKE '%Beitar%'
    OR m.away_team LIKE '%Ironi%'
);

-- ============================================================================
-- Step 4: 验证修复结果
-- ============================================================================
\echo ''
\echo '>>> Step 4: 验证修复结果 <<<'
\echo ''

-- 显示修复后的统计
\echo '修复后各联赛记录统计:'
SELECT
    league_name,
    season,
    COUNT(*) as count
FROM matches
GROUP BY league_name, season
ORDER BY count DESC
LIMIT 20;

-- 显示修复后的以色列联赛记录
\echo ''
\echo '修复后的以色列联赛记录（前10条）:'
SELECT
    match_id,
    home_team,
    away_team,
    league_name,
    season,
    updated_at
FROM matches
WHERE league_name = 'Israeli Premier League'
ORDER BY updated_at DESC
LIMIT 10;

-- ============================================================================
-- Step 5: 清理临时表
-- ============================================================================
\echo ''
\echo '>>> Step 5: 清理临时表 <<<'
\echo ''
DROP TABLE IF EXISTS league_name_fixes;

-- ============================================================================
-- 完成报告
-- ============================================================================
\echo ''
\echo '================================================================================'
\echo 'V26.7 数据标签清洗完成！'
\echo '================================================================================'
\timing off
