-- 足球预测系统真实种子数据
-- Football Prediction System Real Seed Data
--
-- 作者: 全栈工程师
-- 目标: 打通数据库 -> API 的真实链路

-- 设置时区
SET TIME ZONE 'UTC';

-- ========================================
-- 1. 插入联赛数据 (Leagues)
-- ========================================
INSERT INTO leagues (name, country, is_active, created_at, updated_at) VALUES
('Premier League', 'England', true, NOW(), NOW()),
('La Liga', 'Spain', true, NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ========================================
-- 2. 插入球队数据 (Teams)
-- ========================================
INSERT INTO teams (name, short_name, country, founded_year, venue, created_at, updated_at) VALUES
('Manchester United', 'MU', 'England', 1878, 'Old Trafford', NOW(), NOW()),
('Liverpool', 'LIV', 'England', 1892, 'Anfield', NOW(), NOW()),
('Real Madrid', 'RMA', 'Spain', 1902, 'Santiago Bernabéu', NOW(), NOW()),
('Barcelona', 'BAR', 'Spain', 1899, 'Camp Nou', NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ========================================
-- 3. 插入比赛数据 (Matches)
-- ========================================
INSERT INTO matches (home_team_id, away_team_id, home_score, away_score, status, match_date, venue, league_id, season, created_at, updated_at) VALUES
-- Manchester United vs Liverpool (即将进行的比赛)
(1, 2, NULL, NULL, 'upcoming', NOW() + INTERVAL '2 days', 'Old Trafford', 1, '2024-2025', NOW(), NOW()),
-- Real Madrid vs Barcelona (已结束的比赛)
(3, 4, 2, 1, 'finished', NOW() - INTERVAL '1 day', 'Santiago Bernabéu', 2, '2024-2025', NOW(), NOW())
ON CONFLICT DO NOTHING;

-- ========================================
-- 4. 验证插入结果
-- ========================================
SELECT 'Leagues inserted:' as info, COUNT(*) as count FROM leagues;
SELECT 'Teams inserted:' as info, COUNT(*) as count FROM teams;
SELECT 'Matches inserted:' as info, COUNT(*) as count FROM matches;

-- 显示插入的详细数据
SELECT
    t.id, t.name, t.short_name, t.country, t.venue,
    l.name as league_name
FROM teams t
LEFT JOIN leagues l ON t.country = l.country
ORDER BY t.id;

SELECT
    m.id,
    t1.name as home_team,
    t2.name as away_team,
    m.home_score, m.away_score, m.status, m.match_date,
    l.name as league_name
FROM matches m
JOIN teams t1 ON m.home_team_id = t1.id
JOIN teams t2 ON m.away_team_id = t2.id
JOIN leagues l ON m.league_id = l.id
ORDER BY m.match_date;