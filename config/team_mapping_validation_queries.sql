
-- 队名映射验证查询

-- 1. 查看所有已映射的球队
SELECT
    id,
    name,
    fbref_external_id,
    fotmob_external_id
FROM teams
WHERE fotmob_external_id IS NOT NULL OR fbref_external_id IS NOT NULL
ORDER BY name;

-- 2. 统计映射情况
SELECT
    COUNT(*) as total_teams,
    COUNT(fotmob_external_id) as has_fotmob_id,
    COUNT(fbref_external_id) as has_fbref_id,
    COUNT(*) - COUNT(fotmob_external_id) as missing_fotmob,
    COUNT(*) - COUNT(fbref_external_id) as missing_fbref
FROM teams;

-- 3. 测试跨数据源关联 (FBref ↔ FotMob)
SELECT
    t.name as team_name,
    m_fbref.home_score as fbref_score,
    m_fotmob.home_score as fotmob_score,
    m_fbref.match_date,
    m_fotmob.match_date
FROM teams t
JOIN matches m_fbref ON t.fbref_external_id = m_fbref.home_team_id
    AND m_fbref.data_source = 'fbref'
JOIN matches m_fotmob ON t.fotmob_external_id = m_fotmob.home_team_id
    AND m_fotmob.data_source = 'fotmob'
    AND DATE(m_fbref.match_date) = DATE(m_fotmob.match_date)
LIMIT 10;

-- 4. 查找未映射的FBref球队
SELECT DISTINCT
    t.name
FROM matches m
JOIN teams t ON m.home_team_id = t.id
WHERE m.data_source = 'fbref'
    AND t.fotmob_external_id IS NULL
ORDER BY t.name;

-- 5. 查找FotMob中有但FBref中没有的球队
SELECT DISTINCT
    team_name
FROM fotmob_matches
WHERE team_name NOT IN (
    SELECT name FROM teams WHERE fbref_external_id IS NOT NULL
)
ORDER BY team_name;
