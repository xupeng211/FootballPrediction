
-- ============================================================
-- V51.2: team_name_mapping 表结构
-- ============================================================
-- 用途: 存储 FotMob 与 OddsPortal 球队名称映射关系
-- ============================================================

CREATE TABLE IF NOT EXISTS team_name_mapping (
    -- 主键
    id SERIAL PRIMARY KEY,

    -- FotMob 信息
    fotmob_name VARCHAR(200) NOT NULL,
    fotmob_league VARCHAR(100),

    -- OddsPortal 信息
    oddsportal_name VARCHAR(200) NOT NULL,
    oddsportal_league VARCHAR(100),

    -- 映射质量
    confidence_score FLOAT CHECK (confidence_score BETWEEN 0 AND 100),
    needs_review BOOLEAN DEFAULT FALSE,
    mapping_status VARCHAR(20) DEFAULT 'pending',  -- pending, approved, rejected

    -- 审计字段
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP WITH TIME ZONE,

    -- 元数据
    notes TEXT,

    -- 约束
    CONSTRAINT unique_fotmob_name UNIQUE (fotmob_name)
);

-- 索引
CREATE INDEX idx_team_mapping_fotmob ON team_name_mapping(fotmob_name);
CREATE INDEX idx_team_mapping_oddsportal ON team_name_mapping(oddsportal_name);
CREATE INDEX idx_team_mapping_status ON team_name_mapping(mapping_status, needs_review);
CREATE INDEX idx_team_mapping_confidence ON team_name_mapping(confidence_score);

-- 触发器: 自动更新 updated_at
CREATE OR REPLACE FUNCTION update_team_mapping_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_team_mapping_updated_at
    BEFORE UPDATE ON team_name_mapping
    FOR EACH ROW
    EXECUTE FUNCTION update_team_mapping_updated_at();

-- 注释
COMMENT ON TABLE team_name_mapping IS 'V51.2: FotMob 与 OddsPortal 球队名称映射表';
COMMENT ON COLUMN team_name_mapping.confidence_score IS '模糊匹配置信度 (0-100), 低于90需要人工审核';
COMMENT ON COLUMN team_name_mapping.needs_review IS '是否需要人工审核';
COMMENT ON COLUMN team_name_mapping.mapping_status IS '映射状态: pending=待审核, approved=已批准, rejected=已拒绝';
