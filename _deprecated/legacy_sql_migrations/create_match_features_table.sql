-- 创建机器学习特征表
-- 用于存储从L2数据中提取的特征

DROP TABLE IF EXISTS match_features_training;

CREATE TABLE match_features_training (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(50) NOT NULL UNIQUE,

    -- 比赛基本信息
    match_time TIMESTAMP WITH TIME ZONE NOT NULL,
    home_team VARCHAR(100) NOT NULL,
    away_team VARCHAR(100) NOT NULL,
    final_score VARCHAR(20),
    home_goals INTEGER,
    away_goals INTEGER,

    -- === 基础统计特征 ===

    -- 控球率
    home_possession REAL,
    away_possession REAL,

    -- 射正数
    home_shots_on_target INTEGER,
    away_shots_on_target INTEGER,

    -- 角球
    home_corners INTEGER,
    away_corners INTEGER,

    -- 总射门数
    home_total_shots INTEGER,
    away_total_shots INTEGER,

    -- 传球成功率
    home_pass_accuracy REAL,
    away_pass_accuracy REAL,

    -- === 深度统计 (xG) ===

    -- 预期进球
    home_xg REAL,
    away_xg REAL,

    -- === 阵容强度特征 ===

    -- 球队评分
    home_team_rating REAL,
    away_team_rating REAL,

    -- 首发球员平均评分
    home_avg_starting_rating REAL,
    away_avg_starting_rating REAL,

    -- 阵型
    home_formation VARCHAR(10),
    away_formation VARCHAR(10),

    -- === 地理环境特征 ===

    -- 观众人数
    attendance INTEGER,

    -- 裁判
    referee VARCHAR(100),

    -- 场地
    venue_name VARCHAR(200),

    -- === 元数据 ===

    raw_data_source VARCHAR(50) DEFAULT 'fotmob',
    feature_extraction_version VARCHAR(20) DEFAULT '1.0',

    -- 数据质量标记
    possession_quality BOOLEAN DEFAULT TRUE,
    xg_quality BOOLEAN DEFAULT TRUE,
    rating_quality BOOLEAN DEFAULT TRUE,
    attendance_quality BOOLEAN DEFAULT TRUE,

    -- 时间戳
    extracted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- 外键约束
    FOREIGN KEY (external_id) REFERENCES matches(external_id) ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX idx_match_features_external_id ON match_features_training(external_id);
CREATE INDEX idx_match_features_match_time ON match_features_training(match_time);
CREATE INDEX idx_match_features_teams ON match_features_training(home_team, away_team);
CREATE INDEX idx_match_features_extraction_date ON match_features_training(extracted_at);

-- 创建视图：特征完整性检查
CREATE VIEW v_feature_quality_check AS
SELECT
    external_id,
    home_team,
    away_team,
    match_time,
    (CASE WHEN home_possession IS NOT NULL AND away_possession IS NOT NULL THEN 1 ELSE 0 END) as has_possession,
    (CASE WHEN home_shots_on_target IS NOT NULL AND away_shots_on_target IS NOT NULL THEN 1 ELSE 0 END) as has_shots_on_target,
    (CASE WHEN home_corners IS NOT NULL AND away_corners IS NOT NULL THEN 1 ELSE 0 END) as has_corners,
    (CASE WHEN home_xg IS NOT NULL AND away_xg IS NOT NULL THEN 1 ELSE 0 END) as has_xg,
    (CASE WHEN home_team_rating IS NOT NULL AND away_team_rating IS NOT NULL THEN 1 ELSE 0 END) as has_team_rating,
    (CASE WHEN home_avg_starting_rating IS NOT NULL AND away_avg_starting_rating IS NOT NULL THEN 1 ELSE 0 END) as has_player_rating,
    (CASE WHEN attendance IS NOT NULL THEN 1 ELSE 0 END) as has_attendance,
    (CASE WHEN referee IS NOT NULL THEN 1 ELSE 0 END) as has_referee,
    extracted_at
FROM match_features_training
ORDER BY extracted_at DESC;

-- 添加注释
COMMENT ON TABLE match_features_training IS '机器学习训练特征表 - 从FotMob L2数据提取';
COMMENT ON COLUMN match_features_training.home_possession IS '主队控球率 (%)';
COMMENT ON COLUMN match_features_training.away_possession IS '客队控球率 (%)';
COMMENT ON COLUMN match_features_training.home_xg IS '主队预期进球 (xG)';
COMMENT ON COLUMN match_features_training.away_xg IS '客队预期进球 (xG)';
COMMENT ON COLUMN match_features_training.home_avg_starting_rating IS '主队首发球员平均评分';
COMMENT ON COLUMN match_features_training.away_avg_starting_rating IS '客队首发球员平均评分';
COMMENT ON COLUMN match_features_training.attendance IS '观众人数';
COMMENT ON COLUMN match_features_training.referee IS '主裁判姓名';
COMMENT ON COLUMN match_features_training.venue_name IS '比赛场地名称';