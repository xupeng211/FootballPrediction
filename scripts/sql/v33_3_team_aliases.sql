-- ============================================================================
-- V33.3 Team Alias System - 队名别名系统
-- ============================================================================
-- Purpose: 实现自进化队名匹配，摆脱硬编码字典
--
-- 核心功能：
-- 1. 存储队名别名映射（URL slug → 标准队名）
-- 2. 支持多种别名类型（昵称、缩写、模糊匹配）
-- 3. 跟踪使用情况，优化热数据
-- 4. 联赛上下文支持（同 slug 不同联赛）
--
-- Author: 高级数据治理专家
-- Date: 2026-01-11
-- Version: V33.3 (Data Governance)
-- ============================================================================

-- 创建队名别名表
CREATE TABLE IF NOT EXISTS team_aliases (
    -- 主键
    id SERIAL PRIMARY KEY,

    -- 别名信息
    alias_slug VARCHAR(255) NOT NULL,
    canonical_name VARCHAR(255) NOT NULL,

    -- 上下文信息
    league_name VARCHAR(255),
    alias_type VARCHAR(50) DEFAULT 'fuzzy',

    -- 置信度和统计
    confidence FLOAT DEFAULT 0.7,
    usage_count INTEGER DEFAULT 0,

    -- 时间戳
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_used_at TIMESTAMP,

    -- 唯一约束：同一联赛下 alias_slug 唯一
    CONSTRAINT unique_alias_per_league UNIQUE (alias_slug, league_name)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_team_aliases_slug ON team_aliases(alias_slug);
CREATE INDEX IF NOT EXISTS idx_team_aliases_canonical ON team_aliases(canonical_name);
CREATE INDEX IF NOT EXISTS idx_team_aliases_league ON team_aliases(league_name);
CREATE INDEX IF NOT EXISTS idx_team_aliases_type ON team_aliases(alias_type);

-- 添加注释
COMMENT ON TABLE team_aliases IS '队名别名映射表，支持自进化匹配';
COMMENT ON COLUMN team_aliases.alias_slug IS 'URL slug 别名（如 wolves, ath-bilbao）';
COMMENT ON COLUMN team_aliases.canonical_name IS '标准队名（如 Wolverhampton Wanderers）';
COMMENT ON COLUMN team_aliases.league_name IS '联赛上下文（可选，用于区分同 slug 不同联赛）';
COMMENT ON COLUMN team_aliases.alias_type IS '别名类型: manual(手工), nickname(昵称), abbreviation(缩写), fuzzy(模糊匹配)';
COMMENT ON COLUMN team_aliases.confidence IS '匹配置信度 (0-1)';
COMMENT ON COLUMN team_aliases.usage_count IS '使用次数统计';
COMMENT ON COLUMN team_aliases.last_used_at IS '最后使用时间（用于缓存预热）';

-- ============================================================================
-- 初始化常见别名（英超 + 西甲）
-- ============================================================================

-- 英超昵称
INSERT INTO team_aliases (alias_slug, canonical_name, league_name, alias_type, confidence) VALUES
    ('wolves', 'Wolverhampton Wanderers', 'Premier League', 'nickname', 1.0),
    ('west-ham', 'West Ham United', 'Premier League', 'nickname', 1.0),
    ('tottenham', 'Tottenham Hotspur', 'Premier League', 'nickname', 1.0),
    ('luton', 'Luton Town', 'Premier League', 'nickname', 1.0),
    ('newcastle-utd', 'Newcastle United', 'Premier League', 'abbreviation', 1.0),
    ('sheffield-utd', 'Sheffield United', 'Premier League', 'abbreviation', 1.0),
    ('brighton', 'Brighton & Hove Albion', 'Premier League', 'nickname', 0.9)
ON CONFLICT (alias_slug, league_name) DO NOTHING;

-- 西甲缩写和昵称
INSERT INTO team_aliases (alias_slug, canonical_name, league_name, alias_type, confidence) VALUES
    ('ath-bilbao', 'Athletic Club', 'La Liga', 'abbreviation', 1.0),
    ('atl-madrid', 'Atletico Madrid', 'La Liga', 'abbreviation', 1.0),
    ('betis', 'Real Betis', 'La Liga', 'nickname', 1.0),
    ('valladolid', 'Real Valladolid', 'La Liga', 'nickname', 0.9),
    ('real-sociedad', 'Real Sociedad', 'La Liga', 'manual', 1.0),
    ('real-madrid', 'Real Madrid', 'La Liga', 'manual', 1.0)
ON CONFLICT (alias_slug, league_name) DO NOTHING;

-- 创建更新触发器
CREATE OR REPLACE FUNCTION update_team_aliases_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_team_aliases_updated_at
    BEFORE UPDATE ON team_aliases
    FOR EACH ROW
    EXECUTE FUNCTION update_team_aliases_updated_at();

-- ============================================================================
-- 辅助视图：队名匹配统计
-- ============================================================================

CREATE OR REPLACE VIEW v_team_aliases_stats AS
SELECT
    league_name,
    alias_type,
    COUNT(*) as total_aliases,
    COUNT(*) FILTER (WHERE last_used_at IS NOT NULL) as used_aliases,
    AVG(usage_count) as avg_usage_count,
    MAX(last_used_at) as most_recent_use
FROM team_aliases
GROUP BY league_name, alias_type
ORDER BY league_name, alias_type;

COMMENT ON VIEW v_team_aliases_stats IS '队名别名统计视图';
