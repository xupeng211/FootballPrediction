-- ============================================================================
-- V150.0 OddsPortal 数据对齐映射表
-- ============================================================================
-- 功能:
--   1. 存储 FotMob ↔ OddsPortal 比赛映射关系
--   2. 支持多级匹配方法 (ID表、Levenshtein、语义匹配)
--   3. 记录置信度和验证时间
--   4. 支持人工审核队列
--
-- Author: 高级数据架构师
-- Version: V150.0
-- Date: 2026-01-07
-- ============================================================================

-- 创建 matches_mapping 表
CREATE TABLE IF NOT EXISTS matches_mapping (
    -- 主键
    id SERIAL PRIMARY KEY,

    -- FotMob 标识符
    fotmob_id VARCHAR(50) NOT NULL UNIQUE,

    -- OddsPortal 标识符
    oddsportal_url VARCHAR(500),

    -- 映射元数据
    confidence FLOAT NOT NULL DEFAULT 0.0,
    mapping_method VARCHAR(50) NOT NULL,  -- 'id_table', 'levenshtein', 'semantic', 'manual'
    verified_at TIMESTAMP DEFAULT NOW(),

    -- 审核状态
    review_status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'approved', 'rejected'
    review_notes TEXT,

    -- 调试信息
    match_date TIMESTAMP,
    home_team VARCHAR(200),
    away_team VARCHAR(200),
    league_name VARCHAR(200),

    -- 时间戳
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- 约束
    CONSTRAINT confidence_range CHECK (confidence >= 0.0 AND confidence <= 1.0),
    CONSTRAINT valid_method CHECK (mapping_method IN ('id_table', 'levenshtein', 'semantic', 'manual')),
    CONSTRAINT valid_status CHECK (review_status IN ('pending', 'approved', 'rejected'))
);

-- 创建索引以优化查询性能
CREATE INDEX idx_fotmob_id ON matches_mapping(fotmob_id);
CREATE INDEX idx_oddsportal_url ON matches_mapping(oddsportal_url);
CREATE INDEX idx_confidence ON matches_mapping(confidence DESC);
CREATE INDEX idx_review_status ON matches_mapping(review_status);
CREATE INDEX idx_mapping_method ON matches_mapping(mapping_method);
CREATE INDEX idx_created_at ON matches_mapping(created_at DESC);

-- 创建复合索引用于常见查询
CREATE INDEX idx_method_confidence ON matches_mapping(mapping_method, confidence DESC);
CREATE INDEX idx_status_review ON matches_mapping(review_status, created_at);

-- 添加注释
COMMENT ON TABLE matches_mapping IS 'V150.0: FotMob ↔ OddsPortal 比赛映射表';
COMMENT ON COLUMN matches_mapping.fotmob_id IS 'FotMob 比赛唯一标识符';
COMMENT ON COLUMN matches_mapping.oddsportal_url IS 'OddsPortal 比赛页面 URL';
COMMENT ON COLUMN matches_mapping.confidence IS '匹配置信度 (0.0-1.0)';
COMMENT ON COLUMN matches_mapping.mapping_method IS '匹配方法: id_table(零歧义), levenshtein(编辑距离), semantic(语义), manual(人工)';
COMMENT ON COLUMN matches_mapping.review_status IS '审核状态: pending(待审核), approved(已批准), rejected(已拒绝)';
COMMENT ON COLUMN matches_mapping.review_notes IS '人工审核备注';

-- 创建触发器：自动更新 updated_at 字段
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_matches_mapping_updated_at
    BEFORE UPDATE ON matches_mapping
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 辅助视图
-- ============================================================================

-- 高置信度映射视图 (confidence >= 0.9)
CREATE OR REPLACE VIEW high_confidence_mappings AS
SELECT
    id,
    fotmob_id,
    oddsportal_url,
    confidence,
    mapping_method,
    home_team,
    away_team,
    match_date,
    created_at
FROM matches_mapping
WHERE confidence >= 0.9 AND review_status = 'approved'
ORDER BY confidence DESC, created_at DESC;

COMMENT ON VIEW high_confidence_mappings IS '高置信度映射视图 (confidence >= 0.9, 已审核)';

-- 待审核映射视图
CREATE OR REPLACE VIEW pending_review_mappings AS
SELECT
    id,
    fotmob_id,
    oddsportal_url,
    confidence,
    mapping_method,
    home_team,
    away_team,
    match_date,
    created_at
FROM matches_mapping
WHERE review_status = 'pending'
ORDER BY confidence DESC, created_at ASC;

COMMENT ON VIEW pending_review_mappings IS '待审核映射队列';

-- ============================================================================
-- 初始化数据（示例）
-- ============================================================================

-- 插入一些示例映射（用于测试）
INSERT INTO matches_mapping (
    fotmob_id,
    oddsportal_url,
    confidence,
    mapping_method,
    review_status,
    match_date,
    home_team,
    away_team,
    league_name
) VALUES
    (
        '1234567',
        'https://www.oddsportal.com/football/england/premier-league/arsenal-chelsea/',
        1.0,
        'id_table',
        'approved',
        '2024-11-01 15:00:00',
        'Arsenal',
        'Chelsea',
        'Premier League'
    ),
    (
        '1234568',
        'https://www.oddsportal.com/football/england/premier-league/manchester-city-bournemouth/',
        0.95,
        'levenshtein',
        'approved',
        '2024-11-01 17:30:00',
        'Manchester City',
        'Bournemouth',
        'Premier League'
    ),
    (
        '1234569',
        'https://www.oddsportal.com/football/england/premier-league/liverpool-aston-villa/',
        0.88,
        'semantic',
        'pending',
        '2024-11-01 20:00:00',
        'Liverpool',
        'Aston Villa',
        'Premier League'
    )
ON CONFLICT (fotmob_id) DO NOTHING;

-- ============================================================================
-- 验证
-- ============================================================================

-- 验证表创建
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname = 'public' AND tablename = 'matches_mapping') THEN
        RAISE NOTICE '✅ matches_mapping table created successfully';
    ELSE
        RAISE EXCEPTION '❌ matches_mapping table creation failed';
    END IF;

    IF EXISTS (SELECT FROM pg_views WHERE schemaname = 'public' AND viewname = 'high_confidence_mappings') THEN
        RAISE NOTICE '✅ high_confidence_mappings view created successfully';
    END IF;

    IF EXISTS (SELECT FROM pg_views WHERE schemaname = 'public' AND viewname = 'pending_review_mappings') THEN
        RAISE NOTICE '✅ pending_review_mappings view created successfully';
    END IF;
END $$;

-- 显示初始数据统计
SELECT
    'matches_mapping' AS table_name,
    COUNT(*) AS total_rows,
    COUNT(*) FILTER (WHERE review_status = 'approved') AS approved_count,
    COUNT(*) FILTER (WHERE review_status = 'pending') AS pending_count,
    AVG(confidence) AS avg_confidence
FROM matches_mapping;
