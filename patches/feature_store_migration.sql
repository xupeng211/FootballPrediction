-- FeatureStore 表结构迁移
-- 创建时间: 2025-12-05
-- 目的: 支持 ML 特征工程的异步存储和查询

-- 创建特征存储主表
CREATE TABLE IF NOT EXISTS feature_store (
    match_id BIGINT NOT NULL,
    version VARCHAR(50) NOT NULL DEFAULT 'latest',
    features JSONB NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- 主键约束：比赛ID + 版本
    PRIMARY KEY (match_id, version),

    -- 版本检查约束
    CONSTRAINT valid_version CHECK (version ~ '^[a-zA-Z0-9_.-]+$')
);

-- 创建索引以优化查询性能
CREATE INDEX IF NOT EXISTS idx_featurestore_match_id ON feature_store(match_id);
CREATE INDEX IF NOT EXISTS idx_featurestore_version ON feature_store(version);
CREATE INDEX IF NOT EXISTS idx_featurestore_created_at ON feature_store(created_at);
CREATE INDEX IF NOT EXISTS idx_featurestore_updated_at ON feature_store(updated_at);
CREATE INDEX IF NOT EXISTS idx_featurestore_features_gin ON feature_store USING GIN(features);

-- 创建特征版本管理表
CREATE TABLE IF NOT EXISTS feature_versions (
    version VARCHAR(50) NOT NULL PRIMARY KEY,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    feature_schema JSONB,
    CONSTRAINT valid_version_name CHECK (version ~ '^[a-zA-Z0-9_.-]+$')
);

-- 创建特征访问日志表（用于监控和调试）
CREATE TABLE IF NOT EXISTS feature_access_log (
    id BIGSERIAL PRIMARY KEY,
    match_id BIGINT NOT NULL,
    version VARCHAR(50) NOT NULL,
    operation VARCHAR(20) NOT NULL, -- 'read', 'write', 'delete'
    access_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id VARCHAR(100),
    session_id VARCHAR(100),
    execution_time_ms INTEGER,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,

    -- 外键约束
    FOREIGN KEY (match_id, version) REFERENCES feature_store(match_id, version) ON DELETE CASCADE
);

-- 创建索引优化日志查询
CREATE INDEX IF NOT EXISTS idx_feature_log_match_id ON feature_access_log(match_id);
CREATE INDEX IF NOT EXISTS idx_feature_log_access_time ON feature_access_log(access_time);
CREATE INDEX IF NOT EXISTS idx_feature_log_operation ON feature_access_log(operation);

-- 插入默认版本记录
INSERT INTO feature_versions (version, description)
VALUES
    ('latest', '最新版本的特征数据'),
    ('v1.0', '初始版本的特征定义')
ON CONFLICT (version) DO NOTHING;

-- 创建特征存储统计视图
CREATE OR REPLACE VIEW feature_stats AS
SELECT
    COUNT(DISTINCT fs.match_id) as total_matches,
    COUNT(*) as total_feature_records,
    COUNT(DISTINCT fs.version) as total_versions,
    MAX(fs.created_at) as latest_timestamp,
    MIN(fs.created_at) as earliest_timestamp,
    AVG(EXTRACT(EPOCH FROM (fs.updated_at - fs.created_at))) as avg_update_delay_seconds,
    pg_size_pretty(pg_total_relation_size('feature_store')) as storage_size
FROM feature_store fs;

-- 创建特征访问统计视图
CREATE OR REPLACE VIEW feature_access_stats AS
SELECT
    operation,
    COUNT(*) as total_operations,
    AVG(execution_time_ms) as avg_execution_time_ms,
    MAX(execution_time_ms) as max_execution_time_ms,
    COUNT(*) FILTER (WHERE success = true) as successful_operations,
    COUNT(*) FILTER (WHERE success = false) as failed_operations,
    DATE_TRUNC('hour', access_time) as hour_bucket
FROM feature_access_log
GROUP BY operation, DATE_TRUNC('hour', access_time)
ORDER BY hour_bucket DESC, operation;

-- 创建用于监控的函数
CREATE OR REPLACE FUNCTION get_feature_store_health()
RETURNS JSONB AS $$
DECLARE
    result JSONB;
    total_records BIGINT;
    latest_access TIMESTAMPTZ;
    error_rate DECIMAL;
BEGIN
    -- 获取基础统计
    SELECT COUNT(*) INTO total_records FROM feature_store;

    -- 获取最新访问时间
    SELECT MAX(access_time) INTO latest_access
    FROM feature_access_log
    WHERE access_time > NOW() - INTERVAL '1 hour';

    -- 计算错误率（过去24小时）
    SELECT
        CASE
            WHEN COUNT(*) = 0 THEN 0
            ELSE (COUNT(*) FILTER (WHERE success = false)::DECIMAL / COUNT(*)) * 100
        END INTO error_rate
    FROM feature_access_log
    WHERE access_time > NOW() - INTERVAL '24 hours';

    -- 构建健康状态JSON
    result := jsonb_build_object(
        'status', CASE
            WHEN total_records = 0 THEN 'no_data'
            WHEN latest_access IS NULL THEN 'unknown'
            WHEN error_rate > 10.0 THEN 'degraded'
            ELSE 'healthy'
        END,
        'total_records', total_records,
        'latest_access', EXTRACT(EPOCH FROM (NOW() - latest_access)) WHEN latest_access IS NOT NULL ELSE NULL,
        'error_rate_24h', error_rate,
        'check_time', NOW()
    );

    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- 创建自动更新 updated_at 触发器
CREATE OR REPLACE FUNCTION update_feature_store_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 应用触发器
CREATE TRIGGER trigger_feature_store_updated_at
    BEFORE UPDATE ON feature_store
    FOR EACH ROW
    EXECUTE FUNCTION update_feature_store_updated_at();

-- 创建定期清理日志的函数（保留30天）
CREATE OR REPLACE FUNCTION cleanup_feature_access_logs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM feature_access_log
    WHERE access_time < NOW() - INTERVAL '30 days';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- 设置表的注释
COMMENT ON TABLE feature_store IS '足球预测特征存储主表，存储比赛相关的所有特征数据';
COMMENT ON TABLE feature_versions IS '特征版本管理表，记录不同版本的特征定义';
COMMENT ON TABLE feature_access_log IS '特征访问日志表，用于监控和调试';
COMMENT ON VIEW feature_stats IS '特征存储统计视图，提供快速的健康检查信息';

-- 创建用户权限（如果需要）
-- GRANT SELECT, INSERT, UPDATE, DELETE ON feature_store TO football_prediction_user;
-- GRANT SELECT, INSERT ON feature_versions TO football_prediction_user;
-- GRANT SELECT, INSERT ON feature_access_log TO football_prediction_user;
-- GRANT SELECT ON feature_stats TO football_prediction_user;
-- GRANT EXECUTE ON FUNCTION get_feature_store_health() TO football_prediction_user;