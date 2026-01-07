-- ============================================================================
-- V26.7 历史数据对齐：利用反向字典补齐 league_id
--
-- 目的：将已有的 7000+ 场比赛的 league_name 映射为对应的 league_id
--
-- 映射规则（基于 LEAGUE_ID_TO_NAME）：
--   47  -> Premier League
--   87  -> La Liga
--   94  -> Serie A
--   118 -> Bundesliga
--   126 -> Ligue 1
--   53  -> Ligue 1 (备用 ID)
--
-- 作者：高级数据库架构师
-- 日期：2026-01-07
-- ============================================================================

\echo '================================================================================'
\echo 'V26.7 历史数据对齐：补齐 league_id'
\echo '================================================================================'
\timing on

-- ============================================================================
-- Step 1: 当前数据诊断
-- ============================================================================
\echo ''
\echo '>>> Step 1: 当前数据诊断 <<<'
\echo ''

-- 统计各联赛的记录数
\echo '按 league_name 分组统计:'
SELECT
    league_name,
    COUNT(*) as match_count,
    COUNT(league_id) as has_league_id,
    COUNT(*) - COUNT(league_id) as missing_league_id
FROM matches
GROUP BY league_name
ORDER BY match_count DESC;

-- ============================================================================
-- Step 2: 利用反向字典填充 league_id
-- ============================================================================
\echo ''
\echo '>>> Step 2: 填充 league_id <<<'
\echo ''

-- 批量更新 league_id（基于 league_name）
UPDATE matches
SET league_id = CASE league_name
    WHEN 'Premier League' THEN 47
    WHEN 'La Liga' THEN 87
    WHEN 'Serie A' THEN 94
    WHEN 'Bundesliga' THEN 118
    WHEN 'Ligue 1' THEN 126
    WHEN 'Eredivisie' THEN 53
    WHEN 'Championship' THEN 48
    -- 其他联赛保持 NULL
    ELSE NULL
END
WHERE league_id IS NULL
  AND league_name IN (
      'Premier League', 'La Liga', 'Serie A', 'Bundesliga',
      'Ligue 1', 'Eredivisie', 'Championship'
  );

\echo '✅ league_id 填充完成';

-- ============================================================================
-- Step 3: 验证填充结果
-- ============================================================================
\echo ''
\echo '>>> Step 3: 验证填充结果 <<<'
\echo '

-- 显示填充后的统计
\echo '填充后各联赛的 league_id 分布:'
SELECT
    league_name,
    league_id,
    COUNT(*) as match_count,
    COUNT(DISTINCT season) as seasons
FROM matches
WHERE league_id IS NOT NULL
GROUP BY league_name, league_id
ORDER BY match_count DESC;

\echo ''
\echo '按 league_id 分组统计:'
SELECT
    league_id,
    STRING_AGG(DISTINCT league_name, ', ') as league_names,
    COUNT(*) as total_matches
FROM matches
WHERE league_id IS NOT NULL
GROUP BY league_id
ORDER BY league_id;

-- ============================================================================
-- Step 4: 检查未匹配的数据
-- ============================================================================
\echo ''
\echo '>>> Step 4: 检查未匹配的数据 <<<'
\echo '

\echo '缺少 league_id 的联赛（需要人工处理）:'
SELECT
    league_name,
    COUNT(*) as match_count
FROM matches
WHERE league_id IS NULL
GROUP BY league_name
ORDER BY match_count DESC;

-- ============================================================================
-- Step 5: 随机抽样验证
-- ============================================================================
\echo ''
\echo '>>> Step 5: 随机抽样验证 <<<'
\echo '

\echo '英超随机 5 场验证（应同时有 league_id=47 和 league_name）:'
SELECT
    match_id,
    home_team,
    away_team,
    league_id,
    league_name,
    home_score,
    away_score
FROM matches
WHERE league_name = 'Premier League'
  AND league_id = 47
ORDER BY RANDOM()
LIMIT 5;

\echo ''
\echo '西甲随机 5 场验证（应同时有 league_id=87 和 league_name）:'
SELECT
    match_id,
    home_team,
    away_team,
    league_id,
    league_name,
    home_score,
    away_score
FROM matches
WHERE league_name = 'La Liga'
  AND league_id = 87
ORDER BY RANDOM()
LIMIT 5;

\echo ''
\echo '================================================================================'
\echo 'V26.7 历史数据对齐完成！'
\echo '================================================================================'
\timing off

-- ============================================================================
-- 完成报告
-- ============================================================================
\echo ''
\echo '📊 最终统计:'
SELECT
    COUNT(*) as total_matches,
    COUNT(league_id) as has_league_id,
    COUNT(*) - COUNT(league_id) as missing_league_id,
    ROUND(100.0 * COUNT(league_id) / COUNT(*), 2) as coverage_percentage
FROM matches;
