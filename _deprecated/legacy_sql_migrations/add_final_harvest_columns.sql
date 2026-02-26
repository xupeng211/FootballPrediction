-- 最终收割计划 - 扩展特征架构
-- 添加博彩市场预期和赛场突发事件特征
-- 目标: 突破80个特征大关

ALTER TABLE match_features_training
-- A. 赔率与市场预期特征 (8个字段)
ADD COLUMN IF NOT EXISTS home_opening_odds REAL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS draw_opening_odds REAL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS away_opening_odds REAL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS home_closing_odds REAL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS draw_closing_odds REAL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS away_closing_odds REAL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS home_implied_win_prob REAL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS odds_drift_home REAL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS odds_drift_away REAL DEFAULT NULL,

-- B. 事件流深度解析特征 (8个字段)
ADD COLUMN IF NOT EXISTS home_yellow_cards INTEGER DEFAULT NULL,
ADD COLUMN IF NOT EXISTS away_yellow_cards INTEGER DEFAULT NULL,
ADD COLUMN IF NOT EXISTS total_yellow_cards INTEGER DEFAULT NULL,
ADD COLUMN IF NOT EXISTS home_red_cards INTEGER DEFAULT NULL,
ADD COLUMN IF NOT EXISTS away_red_cards INTEGER DEFAULT NULL,
ADD COLUMN IF NOT EXISTS total_red_cards INTEGER DEFAULT NULL,
ADD COLUMN IF NOT EXISTS first_red_card_minute INTEGER DEFAULT NULL,
ADD COLUMN IF NOT EXISTS var_intervention_count INTEGER DEFAULT NULL,
ADD COLUMN IF NOT EXISTS injury_stoppage_time INTEGER DEFAULT NULL,

-- C. 效率与守门员特征 (4个字段)
ADD COLUMN IF NOT EXISTS home_finishing_efficiency REAL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS away_finishing_efficiency REAL DEFAULT NULL,
ADD COLUMN IF NOT EXISTS home_saves_count INTEGER DEFAULT NULL,
ADD COLUMN IF NOT EXISTS away_saves_count INTEGER DEFAULT NULL;

-- 更新特征质量检查视图以包含最终收割特征
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

    -- 最终收割特征质量
    (CASE WHEN home_opening_odds IS NOT NULL AND draw_opening_odds IS NOT NULL AND away_opening_odds IS NOT NULL THEN 1 ELSE 0 END) as has_opening_odds,
    (CASE WHEN home_closing_odds IS NOT NULL AND draw_closing_odds IS NOT NULL AND away_closing_odds IS NOT NULL THEN 1 ELSE 0 END) as has_closing_odds,
    (CASE WHEN home_implied_win_prob IS NOT NULL THEN 1 ELSE 0 END) as has_implied_prob,
    (CASE WHEN odds_drift_home IS NOT NULL AND odds_drift_away IS NOT NULL THEN 1 ELSE 0 END) as has_odds_drift,
    (CASE WHEN total_yellow_cards IS NOT NULL AND total_red_cards IS NOT NULL THEN 1 ELSE 0 END) as has_cards_data,
    (CASE WHEN var_intervention_count IS NOT NULL THEN 1 ELSE 0 END) as has_var_data,
    (CASE WHEN home_finishing_efficiency IS NOT NULL AND away_finishing_efficiency IS NOT NULL THEN 1 ELSE 0 END) as has_efficiency,
    (CASE WHEN home_saves_count IS NOT NULL AND away_saves_count IS NOT NULL THEN 1 ELSE 0 END) as has_saves,

    extracted_at
FROM match_features_training
ORDER BY extracted_at DESC;

-- 添加详细字段注释
-- A. 赔率与市场预期特征
COMMENT ON COLUMN match_features_training.home_opening_odds IS '主队初盘赔率';
COMMENT ON COLUMN match_features_training.draw_opening_odds IS '平局初盘赔率';
COMMENT ON COLUMN match_features_training.away_opening_odds IS '客队初盘赔率';
COMMENT ON COLUMN match_features_training.home_closing_odds IS '主队终盘赔率';
COMMENT ON COLUMN match_features_training.draw_closing_odds IS '平局终盘赔率';
COMMENT ON COLUMN match_features_training.away_closing_odds IS '客队终盘赔率';
COMMENT ON COLUMN match_features_training.home_implied_win_prob IS '主队隐含胜率(0-1)';
COMMENT ON COLUMN match_features_training.odds_drift_home IS '主队赔率变动幅度';
COMMENT ON COLUMN match_features_training.odds_drift_away IS '客队赔率变动幅度';

-- B. 事件流深度解析特征
COMMENT ON COLUMN match_features_training.home_yellow_cards IS '主队黄牌数';
COMMENT ON COLUMN match_features_training.away_yellow_cards IS '客队黄牌数';
COMMENT ON COLUMN match_features_training.total_yellow_cards IS '总黄牌数';
COMMENT ON COLUMN match_features_training.home_red_cards IS '主队红牌数';
COMMENT ON COLUMN match_features_training.away_red_cards IS '客队红牌数';
COMMENT ON COLUMN match_features_training.total_red_cards IS '总红牌数';
COMMENT ON COLUMN match_features_training.first_red_card_minute IS '首张红牌发生分钟数';
COMMENT ON COLUMN match_features_training.var_intervention_count IS 'VAR介入次数';
COMMENT ON COLUMN match_features_training.injury_stoppage_time IS '伤病中断时长(分钟)';

-- C. 效率与守门员特征
COMMENT ON COLUMN match_features_training.home_finishing_efficiency IS '主队射门效率(进球数/xG)';
COMMENT ON COLUMN match_features_training.away_finishing_efficiency IS '客队射门效率(进球数/xG)';
COMMENT ON COLUMN match_features_training.home_saves_count IS '主队门将扑救次数';
COMMENT ON COLUMN match_features_training.away_saves_count IS '客队门将扑救次数';