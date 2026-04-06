-- ============================================================================
-- TITAN V6.0 - OddsPortal URL Mapping 表
-- ============================================================================
-- 用途: 存储 match_id 与 OddsPortal hash URL 的映射关系
-- 支持: 历史数据回填、断点续传、多赛季管理
-- ============================================================================

-- 创建 mapping 表
CREATE TABLE IF NOT EXISTS matches_oddsportal_mapping (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(255) NOT NULL REFERENCES matches(match_id) ON DELETE CASCADE,
    oddsportal_hash VARCHAR(8) NOT NULL,
    full_url TEXT NOT NULL,
    season VARCHAR(20) NOT NULL,  -- 例如: '2023-2024'
    league_name VARCHAR(100) NOT NULL,
    home_team VARCHAR(100) NOT NULL,
    away_team VARCHAR(100) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, harvested, failed, skipped
    match_confidence NUMERIC(6, 4),
    mapping_method VARCHAR(50),
    is_reversed BOOLEAN DEFAULT FALSE,
    candidate_name VARCHAR(255),
    is_evidence_only BOOLEAN DEFAULT FALSE,
    retry_count INTEGER DEFAULT 0,
    last_error TEXT,
    harvested_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- 唯一约束: 每场比赛每个赛季只能有一条记录
    UNIQUE(match_id, season),
    
    -- 索引优化
    CONSTRAINT valid_status CHECK (status IN ('pending', 'harvested', 'failed', 'skipped', 'processing')),
    CONSTRAINT valid_method CHECK (
        mapping_method IN (
            'exact',
            'fuzzy',
            'manual',
            'unknown',
            'hash_lock',
            'set_reconciliation',
            'recon_matrix',
            'protocol_extract',
            'dictionary',
            'semantic',
            'V5.5_HARVESTER',
            'v41_186_auto'
        )
    )
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_mapping_season ON matches_oddsportal_mapping(season);
CREATE INDEX IF NOT EXISTS idx_mapping_status ON matches_oddsportal_mapping(status);
CREATE INDEX IF NOT EXISTS idx_mapping_league ON matches_oddsportal_mapping(league_name);
CREATE INDEX IF NOT EXISTS idx_mapping_hash ON matches_oddsportal_mapping(oddsportal_hash);
CREATE INDEX IF NOT EXISTS idx_mapping_evidence_only ON matches_oddsportal_mapping(is_evidence_only);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mapping_season_hash_unique
    ON matches_oddsportal_mapping(season, oddsportal_hash);
CREATE INDEX IF NOT EXISTS idx_mapping_pending ON matches_oddsportal_mapping(status, retry_count) 
    WHERE status IN ('pending', 'failed') AND retry_count < 3;

-- 更新触发器: 自动更新 updated_at
CREATE OR REPLACE FUNCTION update_mapping_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_mapping_timestamp ON matches_oddsportal_mapping;
CREATE TRIGGER trigger_update_mapping_timestamp
    BEFORE UPDATE ON matches_oddsportal_mapping
    FOR EACH ROW
    EXECUTE FUNCTION update_mapping_updated_at();

-- 统计视图: 按赛季和联赛统计
CREATE OR REPLACE VIEW v_mapping_stats AS
SELECT 
    season,
    league_name,
    COUNT(*) as total_matches,
    COUNT(*) FILTER (WHERE status = 'pending') as pending,
    COUNT(*) FILTER (WHERE status = 'harvested') as harvested,
    COUNT(*) FILTER (WHERE status = 'failed') as failed,
    COUNT(*) FILTER (WHERE status = 'skipped') as skipped,
    COUNT(*) FILTER (WHERE status = 'processing') as processing,
    ROUND(COUNT(*) FILTER (WHERE status = 'harvested') * 100.0 / COUNT(*), 2) as harvest_rate
FROM matches_oddsportal_mapping
GROUP BY season, league_name
ORDER BY season DESC, league_name;

-- 使用说明:
-- 1. 查看映射表统计: SELECT * FROM v_mapping_stats;
-- 2. 获取待收割任务: SELECT * FROM matches_oddsportal_mapping WHERE status = 'pending' LIMIT 100;
-- 3. 标记收割成功: UPDATE matches_oddsportal_mapping SET status = 'harvested', harvested_at = NOW() WHERE match_id = 'xxx';
-- 4. 标记失败: UPDATE matches_oddsportal_mapping SET status = 'failed', retry_count = retry_count + 1, last_error = 'error msg' WHERE match_id = 'xxx';
