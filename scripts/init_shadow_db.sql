-- 影子测试数据库初始化脚本
-- 创建影子模式专用表结构

-- 创建影子预测结果表
CREATE TABLE IF NOT EXISTS realtime_predictions (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(100) NOT NULL,
    home_team VARCHAR(100) NOT NULL,
    away_team VARCHAR(100) NOT NULL,
    league_id INTEGER,
    prediction_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- AI预测结果
    ai_prediction VARCHAR(20) NOT NULL,  -- HOME_WIN, DRAW, AWAY_WIN
    ai_probabilities JSONB NOT NULL,    -- {"HOME_WIN": 0.65, "DRAW": 0.22, "AWAY_WIN": 0.13}
    ai_confidence FLOAT NOT NULL,       -- 0.0 to 1.0

    -- 真实赔率数据
    home_odds FLOAT,
    draw_odds FLOAT,
    away_odds FLOAT,
    odds_timestamp TIMESTAMP WITH TIME ZONE,

    -- Kelly公式建议
    kelly_fraction FLOAT,               -- 0.0 to 1.0
    recommended_stake DECIMAL(10,2),    -- 建议投注金额
    expected_value DECIMAL(5,4),        -- 期望值

    -- 影子模式标记
    is_shadow_mode BOOLEAN DEFAULT TRUE,
    test_batch_id VARCHAR(50),          -- 测试批次ID

    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建比赛结果表 (用于后续对账)
CREATE TABLE IF NOT EXISTS match_results (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(100) UNIQUE NOT NULL,
    home_team VARCHAR(100) NOT NULL,
    away_team VARCHAR(100) NOT NULL,
    league_id INTEGER,

    -- 实际比赛结果
    final_home_score INTEGER,
    final_away_score INTEGER,
    actual_result VARCHAR(20),         -- HOME_WIN, DRAW, AWAY_WIN

    -- 比赛时间
    match_start_time TIMESTAMP WITH TIME ZONE,
    match_end_time TIMESTAMP WITH TIME ZONE,

    -- 影子模式关联
    prediction_id INTEGER REFERENCES realtime_predictions(id),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建性能监控表
CREATE TABLE IF NOT EXISTS shadow_performance_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- 预测性能
    total_predictions INTEGER DEFAULT 0,
    successful_predictions INTEGER DEFAULT 0,
    failed_predictions INTEGER DEFAULT 0,
    success_rate FLOAT GENERATED ALWAYS AS (
        CASE
            WHEN total_predictions > 0 THEN
                CAST(successful_predictions AS FLOAT) / total_predictions
            ELSE 0
        END
    ) STORED,

    -- Kelly统计
    kelly_recommendations INTEGER DEFAULT 0,
    total_recommended_stake DECIMAL(10,2) DEFAULT 0,

    -- 系统性能
    avg_prediction_time_ms FLOAT,
    memory_usage_mb FLOAT,
    cpu_usage_percent FLOAT,

    -- 数据质量
    data_collection_errors INTEGER DEFAULT 0,
    fotmob_api_calls INTEGER DEFAULT 0,

    -- 环境信息
    test_batch_id VARCHAR(50),
    environment VARCHAR(20) DEFAULT 'shadow_test'
);

-- 创建索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_realtime_predictions_match_id ON realtime_predictions(match_id);
CREATE INDEX IF NOT EXISTS idx_realtime_predictions_prediction_time ON realtime_predictions(prediction_time);
CREATE INDEX IF NOT EXISTS idx_realtime_predictions_test_batch ON realtime_predictions(test_batch_id);
CREATE INDEX IF NOT EXISTS idx_match_results_match_id ON match_results(match_id);
CREATE INDEX IF NOT EXISTS idx_shadow_performance_timestamp ON shadow_performance_logs(timestamp);

-- 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_realtime_predictions_updated_at
    BEFORE UPDATE ON realtime_predictions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_match_results_updated_at
    BEFORE UPDATE ON match_results
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 插入初始性能记录
INSERT INTO shadow_performance_logs (
    test_batch_id,
    total_predictions,
    successful_predictions,
    environment
) VALUES (
    CONCAT('shadow_batch_', EXTRACT(EPOCH FROM NOW())::BIGINT),
    0,
    0,
    'shadow_test'
);

-- 创建视图用于监控
CREATE OR REPLACE VIEW shadow_test_summary AS
SELECT
    COUNT(*) as total_predictions,
    COUNT(CASE WHEN ai_confidence >= 0.6 THEN 1 END) as high_confidence_predictions,
    AVG(ai_confidence) as avg_confidence,
    COUNT(CASE WHEN kelly_fraction > 0 THEN 1 END) as kelly_recommendations,
    SUM(COALESCE(recommended_stake, 0)) as total_recommended_stake,
    MAX(prediction_time) as last_prediction_time,
    MIN(prediction_time) as first_prediction_time
FROM realtime_predictions
WHERE is_shadow_mode = TRUE;

-- 授权
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO football_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO football_user;

COMMIT;