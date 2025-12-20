-- 添加核能特征列到match_features_training表
-- 顶级量化博彩分析 - "核能榨取"计划

ALTER TABLE match_features_training
ADD COLUMN IF NOT EXISTS home_first_sub_minute INTEGER DEFAULT NULL,
ADD COLUMN IF NOT EXISTS away_first_sub_minute INTEGER DEFAULT NULL,

ADD COLUMN IF NOT EXISTS home_sub_performance_delta REAL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS away_sub_performance_delta REAL DEFAULT NULL,

ADD COLUMN IF NOT EXISTS formation_changed BOOLEAN DEFAULT NULL,

ADD COLUMN IF NOT EXISTS home_avg_shot_distance REAL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS away_avg_shot_distance REAL DEFAULT NULL,

ADD COLUMN IF NOT EXISTS home_header_shot_count INTEGER DEFAULT NULL,
ADD COLUMN IF NOT EXISTS away_header_shot_count INTEGER DEFAULT NULL,

ADD COLUMN IF NOT EXISTS home_big_chances_ratio REAL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS away_big_chances_ratio REAL DEFAULT NULL,

ADD COLUMN IF NOT EXISTS momentum_swings INTEGER DEFAULT NULL,

ADD COLUMN IF NOT EXISTS home_defensive_density_final15 INTEGER DEFAULT NULL,
ADD COLUMN IF NOT EXISTS away_defensive_density_final15 INTEGER DEFAULT NULL;

-- 更新特征质量检查视图以包含核能特征
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

    -- 核能特征质量
    (CASE WHEN home_first_sub_minute IS NOT NULL AND away_first_sub_minute IS NOT NULL THEN 1 ELSE 0 END) as has_coaching_subs,
    (CASE WHEN formation_changed IS NOT NULL THEN 1 ELSE 0 END) as has_formation_changes,
    (CASE WHEN home_avg_shot_distance IS NOT NULL AND away_avg_shot_distance IS NOT NULL THEN 1 ELSE 0 END) as has_shot_distances,
    (CASE WHEN home_header_shot_count IS NOT NULL AND away_header_shot_count IS NOT NULL THEN 1 ELSE 0 END) as has_header_shots,
    (CASE WHEN home_big_chances_ratio IS NOT NULL AND away_big_chances_ratio IS NOT NULL THEN 1 ELSE 0 END) as has_big_chances_ratio,
    (CASE WHEN momentum_swings IS NOT NULL THEN 1 ELSE 0 END) as has_momentum_swings,
    (CASE WHEN home_defensive_density_final15 IS NOT NULL AND away_defensive_density_final15 IS NOT NULL THEN 1 ELSE 0 END) as has_defensive_density,

    extracted_at
FROM match_features_training
ORDER BY extracted_at DESC;

-- 更新注释
COMMENT ON COLUMN match_features_training.home_first_sub_minute IS '主队第一次换人分钟数';
COMMENT ON COLUMN match_features_training.away_first_sub_minute IS '客队第一次换人分钟数';
COMMENT ON COLUMN match_features_training.home_sub_performance_delta IS '主队替补球员平均评分与被换下球员评分差值';
COMMENT ON COLUMN match_features_training.away_sub_performance_delta IS '客队替补球员平均评分与被换下球员评分差值';
COMMENT ON COLUMN match_features_training.formation_changed IS '比赛中是否发生过阵型切换';
COMMENT ON COLUMN match_features_training.home_avg_shot_distance IS '主队所有射门平均距离(米)';
COMMENT ON COLUMN match_features_training.away_avg_shot_distance IS '客队所有射门平均距离(米)';
COMMENT ON COLUMN match_features_training.home_header_shot_count IS '主队头球射门次数';
COMMENT ON COLUMN match_features_training.away_header_shot_count IS '客队头球射门次数';
COMMENT ON COLUMN match_features_training.home_big_chances_ratio IS '主队xG与大机会的比例';
COMMENT ON COLUMN match_features_training.away_big_chances_ratio IS '客队xG与大机会的比例';
COMMENT ON COLUMN match_features_training.momentum_swings IS '统治力曲线正负值切换次数';
COMMENT ON COLUMN match_features_training.home_defensive_density_final15 IS '主队最后15分钟防守动作总数';
COMMENT ON COLUMN match_features_training.away_defensive_density_final15 IS '客队最后15分钟防守动作总数';