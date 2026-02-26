-- V151.2 数据库"复活" SQL - 英超缺失记录恢复
--
-- 功能: 从 matches 表中找出英超数据，但不在 matches_mapping 中的记录
--       将它们重新插入 matches_mapping，并设为 pending 状态
--
-- Author: 首席数据架构师 (Principal Data Architect)
-- Version: V151.2 (Auto-Alignment Engine)
-- Date: 2026-01-11
--
-- 准入红线: 禁止在不使用 matches 表作为底座的情况下进行任何"抢救"工作！
--          我们要的是两个数据源的绝对联动。

-- ==============================================================================
-- 第一步: 检查缺失情况（诊断用）
-- ==============================================================================

-- 检查英超在 matches 表中的总数
SELECT
    'matches 表中的英超记录' as description,
    COUNT(*) as count
FROM matches
WHERE league_name = 'Premier League';

-- 检查英超在 matches_mapping 中的数量
SELECT
    'matches_mapping 中的英超记录' as description,
    COUNT(DISTINCT m.match_id) as count
FROM matches m
INNER JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
WHERE m.league_name = 'Premier League';

-- 检查缺失数量
SELECT
    '英超缺失记录数量' as description,
    COUNT(*) as count
FROM matches m
WHERE m.league_name = 'Premier League'
  AND NOT EXISTS (
      SELECT 1 FROM matches_mapping mm
      WHERE mm.fotmob_id = m.match_id
  );

-- ==============================================================================
-- 第二步: 复活缺失的英超记录
-- ==============================================================================

-- 插入缺失的英超记录到 matches_mapping
INSERT INTO matches_mapping (
    fotmob_id,
    home_team,
    away_team,
    league_name,
    match_date,
    oddsportal_url,
    confidence,
    mapping_method,
    review_status,
    status
)
SELECT
    m.match_id as fotmob_id,
    m.home_team,
    m.away_team,
    m.league_name,
    m.match_date,
    NULL as oddsportal_url,  -- URL 将由 hunt_league_hashes.py 补充
    0.0 as confidence,  -- 初始置信度为 0，待搜索后更新
    'resurrected' as mapping_method,  -- 标记为"复活"记录
    'pending' as review_status,
    'pending' as status
FROM matches m
WHERE m.league_name = 'Premier League'
  AND NOT EXISTS (
      SELECT 1 FROM matches_mapping mm
      WHERE mm.fotmob_id = m.match_id
  )
ON CONFLICT (fotmob_id) DO NOTHING;  -- 避免重复插入

-- ==============================================================================
-- 第三步: 验证复活结果
-- ==============================================================================

-- 统计本次复活了多少条记录
SELECT
    '英超记录总数 (matches)' as description,
    COUNT(*) as count
FROM matches
WHERE league_name = 'Premier League'

UNION ALL

SELECT
    '英超记录总数 (matches_mapping)' as description,
    COUNT(DISTINCT fotmob_id) as count
FROM matches_mapping mm
WHERE mm.league_name = 'Premier League'

UNION ALL

SELECT
    '英超缺失记录数 (复活后)' as description,
    COUNT(*) as count
FROM matches m
WHERE m.league_name = 'Premier League'
  AND NOT EXISTS (
      SELECT 1 FROM matches_mapping mm
      WHERE mm.fotmob_id = m.match_id
  );

-- ==============================================================================
-- 第四步: 查看复活的记录样本（前 10 条）
-- ==============================================================================

SELECT
    mm.fotmob_id,
    mm.home_team,
    mm.away_team,
    mm.league_name,
    mm.match_date,
    mm.mapping_method,
    mm.status,
    mm.review_status
FROM matches_mapping mm
WHERE mm.league_name = 'Premier League'
  AND mm.mapping_method = 'resurrected'
ORDER BY mm.match_date DESC
LIMIT 10;

-- ==============================================================================
-- 第五步: 清理旧的 malformed 记录（可选）
-- ==============================================================================

-- 如果需要清理之前的 malformed 记录，可以运行以下语句
-- UPDATE matches_mapping
-- SET status = 'pending',
--     is_malformed = FALSE,
--     l2_raw_json = NULL,
--     updated_at = NOW()
-- WHERE status = 'malformed'
--   AND updated_at < NOW() - INTERVAL '7 days'
--   AND league_name = 'Premier League';

-- ==============================================================================
-- 执行后的后续步骤:
-- ==============================================================================
-- 1. 运行 python scripts/ops/hunt_league_hashes.py --premier 补充哈希 URL
-- 2. 运行 python scripts/ops/harvest_pinnacle_odds.py 开始采集
-- 3. 检查 logs/hunt_league_hashes.log 和 logs/harvest_pinnacle.log
