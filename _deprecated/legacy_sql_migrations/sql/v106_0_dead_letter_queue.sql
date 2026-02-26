-- V106.0 Dead Letter Queue Table
-- ============================================
-- 用于跟踪和管理失败的提取任务

-- 创建失败市场数据表
CREATE TABLE IF NOT EXISTS failed_market_data (
    id BIGSERIAL PRIMARY KEY,
    match_id VARCHAR(255) NOT NULL,
    vendor VARCHAR(100) NOT NULL,
    source_name VARCHAR(50) NOT NULL,
    failure_reason TEXT NOT NULL,
    retry_count INTEGER DEFAULT 0,
    max_retry_count INTEGER DEFAULT 3,
    last_retry_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    status VARCHAR(20) DEFAULT 'pending', -- pending, retrying, recovered, abandoned

    -- 约束
    CONSTRAINT failed_market_data_match_vendor_unique UNIQUE (match_id, vendor, source_name)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_failed_market_data_match_id ON failed_market_data(match_id);
CREATE INDEX IF NOT EXISTS idx_failed_market_data_vendor ON failed_market_data(vendor);
CREATE INDEX IF NOT EXISTS idx_failed_market_data_status ON failed_market_data(status);
CREATE INDEX IF NOT EXISTS idx_failed_market_data_created_at ON failed_market_data(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_failed_market_data_retry_count ON failed_market_data(retry_count);

-- 创建复合索引（用于重试查询）
CREATE INDEX IF NOT EXISTS idx_failed_market_data_retry_candidates
    ON failed_market_data(status, retry_count)
    WHERE retry_count < max_retry_count;

-- 添加注释
COMMENT ON TABLE failed_market_data IS '死信队列 - 跟踪失败的提取任务';
COMMENT ON COLUMN failed_market_data.status IS '状态: pending=待处理, retrying=重试中, recovered=已恢复, abandoned=已放弃';
COMMENT ON COLUMN failed_market_data.metadata IS '额外的元数据（JSON格式）';

-- 创建触发器：自动更新 updated_at
CREATE OR REPLACE FUNCTION update_failed_market_data_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_failed_market_data_updated_at
    BEFORE UPDATE ON failed_market_data
    FOR EACH ROW
    EXECUTE FUNCTION update_failed_market_data_updated_at();

-- ============================================================================
-- V106.0 数据库视图 - 失败统计
-- ============================================================================

CREATE OR REPLACE VIEW v_failed_market_data_stats AS
SELECT
    vendor,
    source_name,
    status,
    COUNT(*) as total_count,
    COUNT(DISTINCT match_id) as unique_matches,
    AVG(retry_count) as avg_retry_count,
    MAX(retry_count) as max_retry_count,
    MIN(created_at) as first_failure,
    MAX(created_at) as last_failure
FROM failed_market_data
GROUP BY vendor, source_name, status
ORDER BY total_count DESC;

COMMENT ON VIEW v_failed_market_data_stats IS '失败市场数据统计视图';

-- ============================================================================
-- V106.0 辅助函数
-- ============================================================================

-- 获取可重试的记录
CREATE OR REPLACE FUNCTION get_retry_candidates(p_max_retry_count INTEGER DEFAULT 3)
RETURNS TABLE (
    id BIGINT,
    match_id VARCHAR(255),
    vendor VARCHAR(100),
    source_name VARCHAR(50),
    failure_reason TEXT,
    retry_count INTEGER,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        fmd.id,
        fmd.match_id,
        fmd.vendor,
        fmd.source_name,
        fmd.failure_reason,
        fmd.retry_count,
        fmd.metadata
    FROM failed_market_data fmd
    WHERE fmd.status IN ('pending', 'retrying')
      AND fmd.retry_count < p_max_retry_count
      AND fmd.retry_count < fmd.max_retry_count
    ORDER BY fmd.created_at ASC
    LIMIT 100;
END;
$$ LANGUAGE plpgsql;

-- 标记记录为重试中
CREATE OR REPLACE FUNCTION mark_retrying(p_record_id BIGINT)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE failed_market_data
    SET status = 'retrying',
        retry_count = retry_count + 1,
        last_retry_at = CURRENT_TIMESTAMP
    WHERE id = p_record_id
      AND status IN ('pending', 'retrying');

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- 标记记录为已恢复
CREATE OR REPLACE FUNCTION mark_recovered(p_record_id BIGINT)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE failed_market_data
    SET status = 'recovered'
    WHERE id = p_record_id;

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- 标记记录为已放弃
CREATE OR REPLACE FUNCTION mark_abandoned(p_record_id BIGINT)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE failed_market_data
    SET status = 'abandoned'
    WHERE id = p_record_id
      AND retry_count >= max_retry_count;

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_retry_candidates IS '获取可重试的失败记录';
COMMENT ON FUNCTION mark_retrying IS '标记记录为重试中';
COMMENT ON FUNCTION mark_recovered IS '标记记录为已恢复';
COMMENT ON FUNCTION mark_abandoned IS '标记记录为已放弃';

-- ============================================================================
-- V106.0 审计触发器
-- ============================================================================

-- 自动插入失败记录的触发器
CREATE OR REPLACE FUNCTION auto_insert_failed_market_data()
RETURNS TRIGGER AS $$
BEGIN
    -- 当 metrics_multi_source_data 插入验证失败的数据时
    -- 自动将失败记录插入到 failed_market_data
    IF (NEW.is_valid = FALSE) THEN
        INSERT INTO failed_market_data (
            match_id,
            vendor,
            source_name,
            failure_reason,
            metadata,
            status
        ) VALUES (
            NEW.match_id,
            COALESCE(NEW.vendor_id::text, 'unknown'),
            NEW.source_name,
            COALESCE(NEW.validation_error, 'Validation failed'),
            jsonb_build_object(
                'integrity_score', NEW.integrity_score,
                'data_timestamp', NEW.data_timestamp
            ),
            'pending'
        )
        ON CONFLICT (match_id, vendor, source_name)
        DO UPDATE SET
            failure_reason = EXCLUDED.failure_reason,
            retry_count = failed_market_data.retry_count + 1,
            updated_at = CURRENT_TIMESTAMP;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 注意：此触发器需要根据实际情况手动启用
-- CREATE TRIGGER trigger_auto_insert_failed_market_data
--     AFTER INSERT ON metrics_multi_source_data
--     FOR EACH ROW
--     WHEN (NEW.is_valid = FALSE)
--     EXECUTE FUNCTION auto_insert_failed_market_data();
