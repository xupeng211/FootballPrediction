-- 添加深度特征列到match_features_training表
-- 机器学习深度特征扩展

ALTER TABLE match_features_training
ADD COLUMN IF NOT EXISTS home_big_chances_missed INTEGER DEFAULT NULL,
ADD COLUMN IF NOT EXISTS away_big_chances_missed INTEGER DEFAULT NULL,

ADD COLUMN IF NOT EXISTS home_shots_inside_box INTEGER DEFAULT NULL,
ADD COLUMN IF NOT EXISTS away_shots_inside_box INTEGER DEFAULT NULL,

ADD COLUMN IF NOT EXISTS home_expected_assists REAL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS away_expected_assists REAL DEFAULT NULL,

ADD COLUMN IF NOT EXISTS home_momentum_avg REAL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS away_momentum_avg REAL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS momentum_avg REAL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS momentum_std REAL DEFAULT NULL,

ADD COLUMN IF NOT EXISTS home_passes_final_third INTEGER DEFAULT NULL,
ADD COLUMN IF NOT EXISTS away_passes_final_third INTEGER DEFAULT NULL,

ADD COLUMN IF NOT EXISTS home_ground_duels_won_pct REAL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS away_ground_duels_won_pct REAL DEFAULT NULL,

ADD COLUMN IF NOT EXISTS home_aerial_duels_won_pct REAL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS away_aerial_duels_won_pct REAL DEFAULT NULL,

ADD COLUMN IF NOT EXISTS home_interceptions INTEGER DEFAULT NULL,
ADD COLUMN IF NOT EXISTS away_interceptions INTEGER DEFAULT NULL;

-- 更新特征质量检查视图
DROP VIEW IF EXISTS v_feature_quality_check;

CREATE VIEW v_feature_quality_check AS
SELECT
    external_id,
    home_team,
    away_team,
    match_time,

    -- 基础特征质量
    (CASE WHEN home_possession IS NOT NULL AND away_possession IS NOT NULL THEN 1 ELSE 0 END) as has_possession,
    (CASE WHEN home_shots_on_target IS NOT NULL AND away_shots_on_target IS NOT NULL THEN 1 ELSE 0 END) as has_shots_on_target,
    (CASE WHEN home_corners IS NOT NULL AND away_corners IS NOT NULL THEN 1 ELSE 0 END) as has_corners,
    (CASE WHEN home_xg IS NOT NULL AND away_xg IS NOT NULL THEN 1 ELSE 0 END) as has_xg,
    (CASE WHEN home_team_rating IS NOT NULL AND away_team_rating IS NOT NULL THEN 1 ELSE 0 END) as has_team_rating,
    (CASE WHEN home_avg_starting_rating IS NOT NULL AND away_avg_starting_rating IS NOT NULL THEN 1 ELSE 0 END) as has_player_rating,
    (CASE WHEN attendance IS NOT NULL THEN 1 ELSE 0 END) as has_attendance,
    (CASE WHEN referee IS NOT NULL THEN 1 ELSE 0 END) as has_referee,

    -- 深度特征质量
    (CASE WHEN home_big_chances_missed IS NOT NULL AND away_big_chances_missed IS NOT NULL THEN 1 ELSE 0 END) as has_big_chances_missed,
    (CASE WHEN home_shots_inside_box IS NOT NULL AND away_shots_inside_box IS NOT NULL THEN 1 ELSE 0 END) as has_shots_inside_box,
    (CASE WHEN home_expected_assists IS NOT NULL AND away_expected_assists IS NOT NULL THEN 1 ELSE 0 END) as has_expected_assists,
    (CASE WHEN momentum_avg IS NOT NULL AND momentum_std IS NOT NULL THEN 1 ELSE 0 END) as has_momentum,
    (CASE WHEN home_passes_final_third IS NOT NULL AND away_passes_final_third IS NOT NULL THEN 1 ELSE 0 END) as has_passes_final_third,
    (CASE WHEN home_ground_duels_won_pct IS NOT NULL AND away_ground_duels_won_pct IS NOT NULL THEN 1 ELSE 0 END) as has_ground_duels,
    (CASE WHEN home_aerial_duels_won_pct IS NOT NULL AND away_aerial_duels_won_pct IS NOT NULL THEN 1 ELSE 0 END) as has_aerial_duels,
    (CASE WHEN home_interceptions IS NOT NULL AND away_interceptions IS NOT NULL THEN 1 ELSE 0 END) as has_interceptions,

    extracted_at
FROM match_features_training
ORDER BY extracted_at DESC;

-- 更新注释
COMMENT ON COLUMN match_features_training.home_big_chances_missed IS '主队错失大好机会次数';
COMMENT ON COLUMN match_features_training.away_big_chances_missed IS '客队错失大好机会次数';
COMMENT ON COLUMN match_features_training.home_shots_inside_box IS '主队禁区内射门数';
COMMENT ON COLUMN match_features_training.away_shots_inside_box IS '客队禁区内射门数';
COMMENT ON COLUMN match_features_training.home_expected_assists IS '主队预期助攻(xA)';
COMMENT ON COLUMN match_features_training.away_expected_assists IS '客队预期助攻(xA)';
COMMENT ON COLUMN match_features_training.home_momentum_avg IS '主队momentum平均值';
COMMENT ON COLUMN match_features_training.away_momentum_avg IS '客队momentum平均值';
COMMENT ON COLUMN match_features_training.momentum_avg IS '全场momentum平均值';
COMMENT ON COLUMN match_features_training.momentum_std IS 'momentum波动率';
COMMENT ON COLUMN match_features_training.home_passes_final_third IS '主队进攻三区传球数';
COMMENT ON COLUMN match_features_training.away_passes_final_third IS '客队进攻三区传球数';
COMMENT ON COLUMN match_features_training.home_ground_duels_won_pct IS '主队地面对抗成功率(%)';
COMMENT ON COLUMN match_features_training.away_ground_duels_won_pct IS '客队地面对抗成功率(%)';
COMMENT ON COLUMN match_features_training.home_aerial_duels_won_pct IS '主队空中对抗成功率(%)';
COMMENT ON COLUMN match_features_training.away_aerial_duels_won_pct IS '客队空中对抗成功率(%)';
COMMENT ON COLUMN match_features_training.home_interceptions IS '主队总拦截次数';
COMMENT ON COLUMN match_features_training.away_interceptions IS '客队总拦截次数';