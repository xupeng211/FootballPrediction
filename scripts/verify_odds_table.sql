-- 验证 odds 表结构和数据的 SQL 脚本
-- 使用方法: docker-compose exec db psql -U football_prediction -f scripts/verify_odds_table.sql

-- 检查 odds 表是否存在
SELECT
    table_name,
    table_schema
FROM information_schema.tables
WHERE table_name = 'odds' AND table_schema = 'public';

-- 显示 odds 表结构
\d odds

-- 检查 odds 表中的数据量
SELECT
    COUNT(*) as total_odds_records,
    COUNT(DISTINCT match_id) as unique_matches,
    COUNT(DISTINCT bookmaker) as unique_bookmakers,
    COUNT(DISTINCT provider) as unique_providers
FROM odds;

-- 显示 odds 表的示例数据
SELECT
    id,
    match_id,
    bookmaker,
    provider,
    home_win,
    draw,
    away_win,
    created_at,
    updated_at
FROM odds
ORDER BY created_at DESC
LIMIT 5;

-- 检查是否有比赛数据关联
SELECT
    m.id as match_id,
    m.home_team_name,
    m.away_team_name,
    o.bookmaker,
    o.provider,
    o.home_win,
    o.draw,
    o.away_win
FROM matches m
LEFT JOIN odds o ON m.id = o.match_id
ORDER BY m.match_date DESC
LIMIT 10;

-- 验证数据完整性（概率应该在0-1之间）
SELECT
    'home_win_data_quality' as metric,
    COUNT(*) as total_records,
    COUNT(CASE WHEN home_win >= 0 AND home_win <= 1 THEN 1 END) as valid_probabilities,
    ROUND(AVG(home_win), 4) as avg_probability,
    ROUND(MAX(home_win), 4) as max_probability,
    ROUND(MIN(home_win), 4) as min_probability
FROM odds
WHERE home_win IS NOT NULL

UNION ALL

SELECT
    'draw_data_quality' as metric,
    COUNT(*) as total_records,
    COUNT(CASE WHEN draw >= 0 AND draw <= 1 THEN 1 END) as valid_probabilities,
    ROUND(AVG(draw), 4) as avg_probability,
    ROUND(MAX(draw), 4) as max_probability,
    ROUND(MIN(draw), 4) as min_probability
FROM odds
WHERE draw IS NOT NULL

UNION ALL

SELECT
    'away_win_data_quality' as metric,
    COUNT(*) as total_records,
    COUNT(CASE WHEN away_win >= 0 AND away_win <= 1 THEN 1 END) as valid_probabilities,
    ROUND(AVG(away_win), 4) as avg_probability,
    ROUND(MAX(away_win), 4) as max_probability,
    ROUND(MIN(away_win), 4) as min_probability
FROM odds
WHERE away_win IS NOT NULL;