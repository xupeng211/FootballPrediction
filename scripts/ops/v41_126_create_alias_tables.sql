-- V41.126 "工业化适配" - 别名库自动注浆系统
-- 创建 alias_teams 表，支持队名跨平台映射

-- FotMob 队伍别名表
CREATE TABLE IF NOT EXISTS alias_teams (
    id SERIAL PRIMARY KEY,
    fotmob_team_id VARCHAR(50) NOT NULL,
    fotmob_team_name VARCHAR(255) NOT NULL,
    oddsportal_team_name VARCHAR(255),
    oddsportal_team_path VARCHAR(500),
    
    -- 置信度追踪
    confidence FLOAT DEFAULT 0.95,
    alignment_count INTEGER DEFAULT 1,
    last_aligned_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    
    -- 元数据
    league_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    
    -- 唯一约束
    UNIQUE(fotmob_team_id, oddsportal_team_name)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_alias_teams_fotmob_id ON alias_teams(fotmob_team_id);
CREATE INDEX IF NOT EXISTS idx_alias_teams_op_name ON alias_teams(oddsportal_team_name);
CREATE INDEX IF NOT EXISTS idx_alias_teams_confidence ON alias_teams(confidence DESC);
CREATE INDEX IF NOT EXISTS idx_alias_teams_last_aligned ON alias_teams(last_aligned_at DESC);

-- 注释
COMMENT ON TABLE alias_teams IS 'V41.126: 队伍别名映射表 - 支持 FotMob ↔ OddsPortal 自动对齐';
COMMENT ON COLUMN alias_teams.fotmob_team_id IS 'FotMob 队伍 ID（如 9774）';
COMMENT ON COLUMN alias_teams.oddsportal_team_name IS 'OddsPortal 队伍名称（如 Liverpool）';
COMMENT ON COLUMN alias_teams.confidence IS '对齐置信度 (0.0-1.0)，默认 0.95';
COMMENT ON COLUMN alias_teams.alignment_count IS '成功对齐次数，用于递增置信度';

-- OddsPortal 比赛映射表（存储已对齐的比赛）
CREATE TABLE IF NOT EXISTS aligned_matches (
    id SERIAL PRIMARY KEY,
    fotmob_match_id VARCHAR(50) NOT NULL UNIQUE,
    oddsportal_match_id VARCHAR(50) NOT NULL UNIQUE,
    
    -- 对齐元数据
    alignment_score FLOAT NOT NULL,
    alignment_confidence VARCHAR(20),  -- HIGH/MEDIUM/LOW
    aligned_at TIMESTAMP DEFAULT NOW(),
    
    -- 比赛信息
    home_team VARCHAR(255),
    away_team VARCHAR(255),
    match_time TIMESTAMP,
    league_name VARCHAR(255),
    
    FOREIGN KEY (fotmob_match_id) REFERENCES matches(match_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_aligned_matches_score ON aligned_matches(alignment_score DESC);
CREATE INDEX IF NOT EXISTS idx_aligned_matches_time ON aligned_matches(aligned_at DESC);

COMMENT ON TABLE aligned_matches IS 'V41.126: 已对齐比赛表 - 追踪 FotMob ↔ OddsPortal 对齐关系';
