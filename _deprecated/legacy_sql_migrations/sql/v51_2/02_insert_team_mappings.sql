-- ============================================================
-- V51.2: 球队名称映射数据
-- 生成时间: 2025-12-31T20:52:30.427994
-- 总计: 116 条映射
-- =============================================================

-- 插入映射数据
INSERT INTO team_name_mapping (
    fotmob_name, fotmob_league,
    oddsportal_name, oddsportal_league,
    confidence_score, needs_review, mapping_status
) VALUES
    ('Augsburg', 'Bundesliga', 'Augsburg', NULL, 100.0, False, 'approved'),
    ('Bayer Leverkusen', 'Bundesliga', 'Leverkusen', NULL, 90.0, False, 'approved'),
    ('Bayern München', 'Bundesliga', 'Bayern Munich', NULL, 81.5, True, 'pending'),
    ('Bochum', 'Bundesliga', 'Bochum', NULL, 100.0, False, 'approved'),
    ('Borussia Dortmund', 'Bundesliga', 'B. Dortmund', NULL, 85.5, True, 'pending'),
    ('Borussia Mönchengladbach', 'Bundesliga', 'B. Monchengladbach', NULL, 76.2, True, 'pending'),
    ('Eintracht Frankfurt', 'Bundesliga', 'Eintracht Frankfurt', NULL, 100.0, False, 'approved'),
    ('FC Heidenheim', 'Bundesliga', 'Heidenheim', NULL, 95.0, False, 'approved'),
    ('Freiburg', 'Bundesliga', 'Freiburg', NULL, 100.0, False, 'approved'),
    ('Hoffenheim', 'Bundesliga', 'Hoffenheim', NULL, 100.0, False, 'approved'),
    ('Mainz 05', 'Bundesliga', 'Mainz', NULL, 90.0, False, 'approved'),
    ('RB Leipzig', 'Bundesliga', 'RB Leipzig', NULL, 100.0, False, 'approved'),
    ('St. Pauli', 'Bundesliga', 'St. Pauli', NULL, 100.0, False, 'approved'),
    ('Union Berlin', 'Bundesliga', 'Union Berlin', NULL, 100.0, False, 'approved'),
    ('VfB Stuttgart', 'Bundesliga', 'Stuttgart', NULL, 95.0, False, 'approved'),
    ('Werder Bremen', 'Bundesliga', 'Werder Bremen', NULL, 100.0, False, 'approved'),
    ('Wolfsburg', 'Bundesliga', 'Wolfsburg', NULL, 100.0, False, 'approved'),
    ('Atletico Madrid', 'La Liga', 'Atl. Madrid', NULL, 76.9, True, 'pending'),
    ('Barcelona', 'La Liga', 'Barcelona', NULL, 100.0, False, 'approved'),
    ('Celta Vigo', 'La Liga', 'Celta Vigo', NULL, 100.0, False, 'approved'),
    ('Deportivo Alaves', 'La Liga', 'Alaves', NULL, 90.0, False, 'approved'),
    ('Getafe', 'La Liga', 'Getafe', NULL, 100.0, False, 'approved'),
    ('Girona', 'La Liga', 'Girona', NULL, 100.0, False, 'approved'),
    ('Las Palmas', 'La Liga', 'Las Palmas', NULL, 100.0, False, 'approved'),
    ('Leganes', 'La Liga', 'Lens', NULL, 72.7, True, 'pending'),
    ('Mallorca', 'La Liga', 'Mallorca', NULL, 100.0, False, 'approved'),
    ('Osasuna', 'La Liga', 'Osasuna', NULL, 100.0, False, 'approved'),
    ('Rayo Vallecano', 'La Liga', 'Rayo Vallecano', NULL, 100.0, False, 'approved'),
    ('Real Betis', 'La Liga', 'Betis', NULL, 90.0, False, 'approved'),
    ('Real Madrid', 'La Liga', 'Real Madrid', NULL, 100.0, False, 'approved'),
    ('Real Sociedad', 'La Liga', 'Real Sociedad', NULL, 100.0, False, 'approved'),
    ('Real Valladolid', 'La Liga', 'Valladolid', NULL, 90.0, False, 'approved'),
    ('Sevilla', 'La Liga', 'Sevilla', NULL, 100.0, False, 'approved'),
    ('Valencia', 'La Liga', 'Valencia', NULL, 100.0, False, 'approved'),
    ('Villarreal', 'La Liga', 'Villarreal', NULL, 100.0, False, 'approved'),
    ('Angers', 'Ligue 1', 'Angers', NULL, 100.0, False, 'approved'),
    ('Auxerre', 'Ligue 1', 'Auxerre', NULL, 100.0, False, 'approved'),
    ('Brest', 'Ligue 1', 'Brest', NULL, 100.0, False, 'approved'),
    ('Le Havre', 'Ligue 1', 'Le Havre', NULL, 100.0, False, 'approved'),
    ('Lens', 'Ligue 1', 'Lens', NULL, 100.0, False, 'approved'),
    ('Lille', 'Ligue 1', 'Lille', NULL, 100.0, False, 'approved'),
    ('Lorient', 'Ligue 1', 'Lorient', NULL, 100.0, False, 'approved'),
    ('Lyon', 'Ligue 1', 'Lyon', NULL, 100.0, False, 'approved'),
    ('Marseille', 'Ligue 1', 'Marseille', NULL, 100.0, False, 'approved'),
    ('Metz', 'Ligue 1', 'Metz', NULL, 100.0, False, 'approved'),
    ('Monaco', 'Ligue 1', 'Monaco', NULL, 100.0, False, 'approved'),
    ('Montpellier', 'Ligue 1', 'Montpellier', NULL, 100.0, False, 'approved'),
    ('Nantes', 'Ligue 1', 'Nantes', NULL, 100.0, False, 'approved'),
    ('Nice', 'Ligue 1', 'Nice', NULL, 100.0, False, 'approved'),
    ('Reims', 'Ligue 1', 'Reims', NULL, 100.0, False, 'approved'),
    ('Rennes', 'Ligue 1', 'Rennes', NULL, 100.0, False, 'approved'),
    ('Saint-Etienne', 'Ligue 1', 'Rennes', NULL, 72.0, True, 'pending'),
    ('Strasbourg', 'Ligue 1', 'Strasbourg', NULL, 100.0, False, 'approved'),
    ('Toulouse', 'Ligue 1', 'Toulouse', NULL, 100.0, False, 'approved'),
    ('AFC Bournemouth', 'Premier League', 'Bournemouth', NULL, 95.0, False, 'approved'),
    ('Arsenal', 'Premier League', 'Arsenal', NULL, 100.0, False, 'approved'),
    ('Aston Villa', 'Premier League', 'Aston Villa', NULL, 100.0, False, 'approved'),
    ('Brentford', 'Premier League', 'Brentford', NULL, 100.0, False, 'approved'),
    ('Brighton & Hove Albion', 'Premier League', 'Brighton', NULL, 90.0, False, 'approved'),
    ('Chelsea', 'Premier League', 'Chelsea', NULL, 100.0, False, 'approved'),
    ('Crystal Palace', 'Premier League', 'Crystal Palace', NULL, 100.0, False, 'approved'),
    ('Everton', 'Premier League', 'Everton', NULL, 100.0, False, 'approved'),
    ('Fulham', 'Premier League', 'Fulham', NULL, 100.0, False, 'approved'),
    ('Ipswich Town', 'Premier League', 'Ipswich', NULL, 90.0, False, 'approved'),
    ('Leeds United', 'Premier League', 'Man United', NULL, 71.2, True, 'pending'),
    ('Leicester City', 'Premier League', 'Leicester', NULL, 90.0, False, 'approved'),
    ('Liverpool', 'Premier League', 'Liverpool', NULL, 100.0, False, 'approved'),
    ('Manchester City', 'Premier League', 'Man City', NULL, 85.5, True, 'pending'),
    ('Manchester United', 'Premier League', 'Man United', NULL, 85.5, True, 'pending'),
    ('Newcastle United', 'Premier League', 'Newcastle', NULL, 90.0, False, 'approved'),
    ('Norwich City', 'Premier League', 'Man City', NULL, 85.5, True, 'pending'),
    ('Nottingham Forest', 'Premier League', 'Nottingham Forest', NULL, 100.0, False, 'approved'),
    ('Sheffield United', 'Premier League', 'Man United', NULL, 85.5, True, 'pending'),
    ('Southampton', 'Premier League', 'Southampton', NULL, 100.0, False, 'approved'),
    ('Tottenham Hotspur', 'Premier League', 'Tottenham', NULL, 90.0, False, 'approved'),
    ('West Bromwich Albion', 'Premier League', 'West Ham', NULL, 85.5, True, 'pending'),
    ('West Ham United', 'Premier League', 'West Ham', NULL, 90.0, False, 'approved'),
    ('Wolverhampton Wanderers', 'Premier League', 'Wolves', NULL, 81.8, True, 'pending'),
    ('Atalanta', 'Serie A', 'Atalanta', NULL, 100.0, False, 'approved'),
    ('Bologna', 'Serie A', 'Bologna', NULL, 100.0, False, 'approved'),
    ('Cagliari', 'Serie A', 'Cagliari', NULL, 100.0, False, 'approved'),
    ('Como', 'Serie A', 'Como', NULL, 100.0, False, 'approved'),
    ('Empoli', 'Serie A', 'Empoli', NULL, 100.0, False, 'approved'),
    ('Fiorentina', 'Serie A', 'Fiorentina', NULL, 100.0, False, 'approved'),
    ('Genoa', 'Serie A', 'Genoa', NULL, 100.0, False, 'approved'),
    ('Hellas Verona', 'Serie A', 'Verona', NULL, 90.0, False, 'approved'),
    ('Inter', 'Serie A', 'Inter', NULL, 100.0, False, 'approved'),
    ('Juventus', 'Serie A', 'Juventus', NULL, 100.0, False, 'approved'),
    ('Lazio', 'Serie A', 'Lazio', NULL, 100.0, False, 'approved'),
    ('Lecce', 'Serie A', 'Lecce', NULL, 100.0, False, 'approved'),
    ('Milan', 'Serie A', 'Milan', NULL, 100.0, False, 'approved'),
    ('Monza', 'Serie A', 'Monza', NULL, 100.0, False, 'approved'),
    ('Napoli', 'Serie A', 'Napoli', NULL, 100.0, False, 'approved'),
    ('Parma', 'Serie A', 'Parma', NULL, 100.0, False, 'approved'),
    ('Roma', 'Serie A', 'Roma', NULL, 100.0, False, 'approved'),
    ('Torino', 'Serie A', 'Torino', NULL, 100.0, False, 'approved'),
    ('Udinese', 'Serie A', 'Udinese', NULL, 100.0, False, 'approved'),
    ('Venezia', 'Serie A', 'Venezia', NULL, 100.0, False, 'approved'),
    ('AFC Bournemouth', '英超', 'Bournemouth', NULL, 95.0, False, 'approved'),
    ('Arsenal', '英超', 'Arsenal', NULL, 100.0, False, 'approved'),
    ('Aston Villa', '英超', 'Aston Villa', NULL, 100.0, False, 'approved'),
    ('Brentford', '英超', 'Brentford', NULL, 100.0, False, 'approved'),
    ('Brighton & Hove Albion', '英超', 'Brighton', NULL, 90.0, False, 'approved'),
    ('Chelsea', '英超', 'Chelsea', NULL, 100.0, False, 'approved'),
    ('Crystal Palace', '英超', 'Crystal Palace', NULL, 100.0, False, 'approved'),
    ('Everton', '英超', 'Everton', NULL, 100.0, False, 'approved'),
    ('Fulham', '英超', 'Fulham', NULL, 100.0, False, 'approved'),
    ('Leeds United', '英超', 'Man United', NULL, 71.2, True, 'pending'),
    ('Liverpool', '英超', 'Liverpool', NULL, 100.0, False, 'approved'),
    ('Manchester City', '英超', 'Man City', NULL, 85.5, True, 'pending'),
    ('Manchester United', '英超', 'Man United', NULL, 85.5, True, 'pending'),
    ('Newcastle United', '英超', 'Newcastle', NULL, 90.0, False, 'approved'),
    ('Nottingham Forest', '英超', 'Nottingham Forest', NULL, 100.0, False, 'approved'),
    ('Tottenham Hotspur', '英超', 'Tottenham', NULL, 90.0, False, 'approved'),
    ('West Ham United', '英超', 'West Ham', NULL, 90.0, False, 'approved'),
    ('Wolverhampton Wanderers', '英超', 'Wolves', NULL, 81.8, True, 'pending');

-- ============================================================
-- 人工审核查询
-- ============================================================

-- 1. 查看所有需要审核的映射
SELECT
    id, fotmob_name, oddsportal_name, confidence_score, mapping_status
FROM team_name_mapping
WHERE needs_review = TRUE
ORDER BY confidence_score DESC;

-- 2. 按联赛统计映射情况
SELECT
    fotmob_league,
    COUNT(*) as total_mappings,
    SUM(CASE WHEN needs_review THEN 1 ELSE 0 END) as needs_review_count,
    AVG(confidence_score) as avg_confidence
FROM team_name_mapping
GROUP BY fotmob_league
ORDER BY needs_review_count DESC;

-- 3. 批准映射 (示例)
-- UPDATE team_name_mapping SET mapping_status = 'approved', needs_review = FALSE WHERE id = ?;
