-- ML/DL 优化的 match_advanced_stats 表结构
-- PostgreSQL 混合存储：可索引列 + JSONB深度学习特征

-- 删除旧表（如果存在）
DROP TABLE IF EXISTS match_advanced_stats CASCADE;

-- 创建新的ML优化表
CREATE TABLE match_advanced_stats (
    -- 主键和基本标识
    match_id VARCHAR(100) PRIMARY KEY,

    -- === 可索引的核心业务指标 (用于快速筛选和查询) ===
    -- 期望进球 (Expected Goals) - ML模型核心特征
    home_xg DECIMAL(5,2) NOT NULL DEFAULT 0.0,
    away_xg DECIMAL(5,2) NOT NULL DEFAULT 0.0,

    -- 基础技术统计
    possession_home INTEGER NOT NULL DEFAULT 0,    -- 控球率(整数形式，如58表示58%)
    possession_away INTEGER NOT NULL DEFAULT 0,
    shots_home INTEGER NOT NULL DEFAULT 0,
    shots_away INTEGER NOT NULL DEFAULT 0,
    shots_on_target_home INTEGER NOT NULL DEFAULT 0,
    shots_on_target_away INTEGER NOT NULL DEFAULT 0,

    -- 犯规统计
    fouls_home INTEGER NOT NULL DEFAULT 0,
    fouls_away INTEGER NOT NULL DEFAULT 0,
    yellow_cards_home INTEGER NOT NULL DEFAULT 0,
    yellow_cards_away INTEGER NOT NULL DEFAULT 0,
    red_cards_home INTEGER NOT NULL DEFAULT 0,
    red_cards_away INTEGER NOT NULL DEFAULT 0,

    -- 定位球统计
    corners_home INTEGER NOT NULL DEFAULT 0,
    corners_away INTEGER NOT NULL DEFAULT 0,
    offsides_home INTEGER NOT NULL DEFAULT 0,
    offsides_away INTEGER NOT NULL DEFAULT 0,

    -- 比赛元数据 (可索引字符串)
    referee VARCHAR(200),
    stadium VARCHAR(200),
    attendance INTEGER,
    weather VARCHAR(100),
    match_day VARCHAR(50),
    round VARCHAR(100),
    competition_stage VARCHAR(100),

    -- === JSONB 深度学习特征存储 ===
    -- 完整射门数据 (包含坐标、xG、射门类型等深度学习特征)
    shot_map JSONB NOT NULL DEFAULT '[]',

    -- 全场压力指数时间序列 (用于momentum分析)
    momentum JSONB NOT NULL DEFAULT '{}',

    -- 完整阵容数据 (首发/替补 + 球员评分)
    lineups JSONB NOT NULL DEFAULT '{}',

    -- 详细的球员技术统计 (评分、传球、对抗等)
    player_stats JSONB NOT NULL DEFAULT '{}',

    -- 完整的比赛事件时间轴 (进球、换人、卡牌、VAR等)
    match_events JSONB NOT NULL DEFAULT '[]',

    -- 数据质量和来源
    data_quality_score DECIMAL(3,2) NOT NULL DEFAULT 0.5,
    source_reliability VARCHAR(20) NOT NULL DEFAULT 'medium',

    -- 时间戳
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- === 性能优化索引 ===
-- JSONB 数据索引 (支持深度学习模型查询)
CREATE INDEX idx_match_advanced_stats_shot_map ON match_advanced_stats USING GIN (shot_map);
CREATE INDEX idx_match_advanced_stats_momentum ON match_advanced_stats USING GIN (momentum);
CREATE INDEX idx_match_advanced_stats_lineups ON match_advanced_stats USING GIN (lineups);
CREATE INDEX idx_match_advanced_stats_player_stats ON match_advanced_stats USING GIN (player_stats);
CREATE INDEX idx_match_advanced_stats_match_events ON match_advanced_stats USING GIN (match_events);

-- 常用查询索引
CREATE INDEX idx_match_advanced_stats_referee ON match_advanced_stats(referee);
CREATE INDEX idx_match_advanced_stats_stadium ON match_advanced_stats(stadium);
CREATE INDEX idx_match_advanced_stats_attendance ON match_advanced_stats(attendance);
CREATE INDEX idx_match_advanced_stats_weather ON match_advanced_stats(weather);

-- ML模型查询优化索引
CREATE INDEX idx_match_advanced_stats_home_xg ON match_advanced_stats(home_xg);
CREATE INDEX idx_match_advanced_stats_away_xg ON match_advanced_stats(away_xg);
CREATE INDEX idx_match_advanced_stats_possession_home ON match_advanced_stats(possession_home);
CREATE INDEX idx_match_advanced_stats_possession_away ON match_advanced_stats(possession_away);
CREATE INDEX idx_match_advanced_stats_shots_total ON match_advanced_stats(shots_home + shots_away);
CREATE INDEX idx_match_advanced_stats_xg_total ON match_advanced_stats(home_xg + away_xg);

-- 复合索引 (常见查询组合)
CREATE INDEX idx_match_advanced_stats_xg_possession ON match_advanced_stats(home_xg, away_xg, possession_home, possession_away);

-- 时间戳索引
CREATE INDEX idx_match_advanced_stats_created_at ON match_advanced_stats(created_at);
CREATE INDEX idx_match_advanced_stats_updated_at ON match_advanced_stats(updated_at);

-- === 表注释和约束 ===
COMMENT ON TABLE match_advanced_stats IS 'ML/DL优化的比赛高阶统计数据表 - 混合存储设计：可索引列 + JSONB深度学习特征';
COMMENT ON COLUMN match_advanced_stats.shot_map IS 'JSONB: 完整射门数据，包含坐标(x,y)、xG值、射门类型、时间戳等深度学习特征';
COMMENT ON COLUMN match_advanced_stats.momentum IS 'JSONB: 全场压力指数时间序列数据，用于momentum分析';
COMMENT ON COLUMN match_advanced_stats.lineups IS 'JSONB: 完整阵容数据，包含首发/替补名单、球员评分、位置信息';
COMMENT ON COLUMN match_advanced_stats.player_stats IS 'JSONB: 详细球员技术统计，包含评分、传球、对抗、跑动等指标';
COMMENT ON COLUMN match_advanced_stats.match_events IS 'JSONB: 完整比赛事件时间轴，包含进球、换人、卡牌、VAR等所有事件';
COMMENT ON COLUMN match_advanced_stats.data_quality_score IS '数据质量评分(0-1)，用于模型训练数据筛选';
COMMENT ON COLUMN match_advanced_stats.source_reliability IS '数据来源可靠性: high/medium/low';

-- === JSONB 字段验证约束 (可选) ===
-- 确保JSONB字段包含基本必需的结构
ALTER TABLE match_advanced_stats ADD CONSTRAINT chk_shot_map_is_array
    CHECK (jsonb_typeof(shot_map) = 'array');

-- === 查询优化视图 ===
-- 为常用ML查询创建视图
CREATE VIEW match_features_for_ml AS
SELECT
    match_id,
    -- 基础数值特征
    home_xg,
    away_xg,
    home_xg - away_xg AS xg_difference,
    home_xg + away_xg AS total_xg,
    possession_home,
    possession_away,
    possession_home - possession_away AS possession_difference,
    shots_home,
    shots_away,
    shots_home - shots_away AS shots_difference,
    shots_on_target_home,
    shots_on_target_away,
    (shots_on_target_home::FLOAT / NULLIF(shots_home, 0)) * 100 AS shot_accuracy_home,
    (shots_on_target_away::FLOAT / NULLIF(shots_away, 0)) * 100 AS shot_accuracy_away,

    -- 球队强度指标
    (home_xg * 1.5 + possession_home * 0.5) AS home_strength_score,
    (away_xg * 1.5 + possession_away * 0.5) AS away_strength_score,

    -- 比赛统计指标
    fouls_home + fouls_away AS total_fouls,
    yellow_cards_home + yellow_cards_away + red_cards_home + red_cards_away AS total_cards,
    corners_home + corners_away AS total_corners,

    -- JSONB字段长度（用于特征选择）
    jsonb_array_length(shot_map) AS shot_count,
    jsonb_array_length(match_events) AS event_count,

    -- 元数据
    referee,
    stadium,
    attendance,
    data_quality_score,
    source_reliability,
    created_at,
    updated_at
FROM match_advanced_stats;

-- JSONB 特征提取函数示例
CREATE OR REPLACE FUNCTION extract_shot_features(match_data JSONB)
RETURNS JSONB AS $$
BEGIN
    RETURN jsonb_build_object(
        'total_shots', jsonb_array_length(match_data),
        'xg_total', (SELECT COALESCE(SUM((elem->>'expectedGoals')::NUMERIC), 0)
                    FROM jsonb_array_elements(match_data) AS elem),
        'avg_xg', (SELECT COALESCE(AVG((elem->>'expectedGoals')::NUMERIC), 0)
                 FROM jsonb_array_elements(match_data) AS elem),
        'shots_by_team', (
            SELECT jsonb_object_agg(
                CASE WHEN (elem->>'teamId')::TEXT IS NOT NULL
                     THEN 'team_' || (elem->>'teamId')::TEXT
                     ELSE 'unknown' END,
                COUNT(*)
            ) FROM jsonb_array_elements(match_data) AS elem
        )
    );
END;
$$ LANGUAGE plpgsql;

-- 插入示例数据（用于测试）
INSERT INTO match_advanced_stats (
    match_id, home_xg, away_xg, possession_home, possession_away,
    shots_home, shots_away, referee, stadium, attendance,
    shot_map, momentum, lineups, player_stats, match_events,
    data_quality_score, source_reliability
) VALUES (
    'test_match_001',
    2.15, 1.32, 58, 42,
    18, 14, 'Mike Dean', 'Old Trafford', 75000,
    '[
        {
            "id": 2840199951,
            "x": 81.7,
            "y": 39.5,
            "expectedGoals": 0.85,
            "shotType": "RightFoot",
            "isOnTarget": true,
            "minute": 16,
            "teamId": 8603
        },
        {
            "id": 2840199952,
            "x": 120.3,
            "y": 25.8,
            "expectedGoals": 0.12,
            "shotType": "LeftFoot",
            "isOnTarget": false,
            "minute": 23,
            "teamId": 5421
        }
    ]'::jsonb,
    '{"home": [45, 48, 52, 50, 55, 53, 51], "away": [55, 52, 48, 50, 47, 45, 48]}'::jsonb,
    '{
        "home": {
            "team_name": "Manchester United",
            "formation": "4-3-3",
            "players": [
                {"name": "Marcus Rashford", "position": "ST", "rating": 8.5}
            ]
        },
        "away": {
            "team_name": "Liverpool",
            "formation": "4-3-3",
            "players": [
                {"name": "Mohamed Salah", "position": "RW", "rating": 9.1}
            ]
        }
    }'::jsonb,
    '{
        "115591": {"name": "Marcus Rashford", "goals": 1, "assists": 1, "rating": 8.5}
    }'::jsonb,
    '[
        {
            "minute": 25,
            "type": "goal",
            "team_id": 8603,
            "player_id": 115591,
            "player_name": "Marcus Rashford"
        },
        {
            "minute": 67,
            "type": "yellow_card",
            "team_id": 5421,
            "player_id": 123456,
            "player_name": "Liverpool Player"
        }
    ]'::jsonb,
    0.95, 'high'
) ON CONFLICT (match_id) DO NOTHING;

-- 验证数据插入
SELECT
    match_id,
    jsonb_array_length(shot_map) as shot_count,
    jsonb_array_length(match_events) as event_count,
    shot_map->0->>'expectedGoals' as first_shot_xg,
    extract_shot_features(shot_map) as shot_features
FROM match_advanced_stats
WHERE match_id = 'test_match_001';