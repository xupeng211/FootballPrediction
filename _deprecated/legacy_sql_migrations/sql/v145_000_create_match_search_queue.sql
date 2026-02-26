-- ============================================================================
-- [Genesis.ReLink] V145.000: Create match_search_queue Table
-- ============================================================================
--
-- Purpose: 队列表用于 URL 发现系统的任务管理
-- Author: Genesis.ReLink Team
-- Date: 2026-02-01
--
-- Features:
-- - 状态机: PENDING -> SEARCHING -> SUCCESS/FAILED
-- - 自动重试机制 (retry_count, max_retries)
-- - Checkpoint/resume 支持
-- ============================================================================

-- 创建表
CREATE TABLE IF NOT EXISTS match_search_queue (
    match_id VARCHAR(50) PRIMARY KEY,
    home_team VARCHAR(255) NOT NULL,
    away_team VARCHAR(255) NOT NULL,
    league_name VARCHAR(255),
    match_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    discovered_url TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    last_error TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_match_search_queue_status ON match_search_queue(status);
CREATE INDEX IF NOT EXISTS idx_match_search_queue_updated_at ON match_search_queue(updated_at);
CREATE INDEX IF NOT EXISTS idx_match_search_queue_date ON match_search_queue(match_date DESC);

-- 添加注释
COMMENT ON TABLE match_search_queue IS 'URL 发现任务队列 - 用于 OddsPortal URL 自动发现';

-- ============================================================================
-- 数据注入: 将缺失映射的比赛加入队列
-- ============================================================================

-- 注入 1: 从 matches 表中选择有 L2 数据但缺失 matches_mapping 的比赛
INSERT INTO match_search_queue (
    match_id, home_team, away_team, league_name, match_date, status, retry_count
)
SELECT DISTINCT
    m.match_id, m.home_team, m.away_team, m.league_name,
    m.match_date::DATE, 'PENDING', 0
FROM matches m
LEFT JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
WHERE m.l2_raw_json IS NOT NULL AND mm.fotmob_id IS NULL
ON CONFLICT (match_id) DO NOTHING;

-- 注入 2: 从 matches_mapping 表中选择 oddsportal_url 为空的记录
INSERT INTO match_search_queue (
    match_id, home_team, away_team, league_name, match_date, status, retry_count
)
SELECT
    mm.fotmob_id, mm.home_team, mm.away_team, mm.league_name,
    mm.match_date::DATE, 'PENDING', 0
FROM matches_mapping mm
WHERE mm.oddsportal_url IS NULL
   OR mm.oddsportal_url = ''
   OR mm.oddsportal_url LIKE '%fotmob%'
ON CONFLICT (match_id) DO NOTHING;

-- ============================================================================
-- 状态报告
-- ============================================================================

SELECT
    '[Genesis.ReLink] Queue Status Report' as report,
    (SELECT COUNT(*) FROM match_search_queue) as total_queued,
    (SELECT COUNT(*) FROM match_search_queue WHERE status = 'PENDING') as pending,
    (SELECT COUNT(*) FROM match_search_queue WHERE status = 'SEARCHING') as searching,
    (SELECT COUNT(*) FROM match_search_queue WHERE status = 'SUCCESS') as success,
    (SELECT COUNT(*) FROM match_search_queue WHERE status = 'FAILED') as failed,
    (SELECT COUNT(DISTINCT m.match_id)
     FROM matches m
     LEFT JOIN matches_mapping mm ON m.match_id = mm.fotmob_id
     WHERE m.l2_raw_json IS NOT NULL AND mm.fotmob_id IS NULL
    ) as gaps_in_matches,
    (SELECT COUNT(*)
     FROM matches_mapping
     WHERE oddsportal_url IS NULL OR oddsportal_url = '' OR oddsportal_url LIKE '%fotmob%'
    ) as gaps_in_mapping;
