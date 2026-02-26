-- ============================================================================
-- V120.0 Phase 4: Dead Letter Queue for Failed Validations
-- ============================================================================
-- Purpose: 死信队列 - 存储未通过数据契约验证的数据，供后续人工审查

CREATE TABLE IF NOT EXISTS metrics_dead_letter_queue (
    -- 主键
    id SERIAL PRIMARY KEY,

    -- 原始数据标识
    match_id VARCHAR(50) NOT NULL,
    source_name VARCHAR(50) NOT NULL,

    -- 提取的原始数据
    init_h NUMERIC(10, 2),
    init_d NUMERIC(10, 2),
    init_a NUMERIC(10, 2),
    final_h NUMERIC(10, 2),
    final_d NUMERIC(10, 2),
    final_a NUMERIC(10, 2),

    -- 验证信息
    integrity_score NUMERIC(10, 4),
    validation_error TEXT,

    -- 故障分类
    failure_category VARCHAR(50),  -- 'nan_values', 'out_of_range', 'identical', 'other'

    -- 重试信息
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    is_permanent_failure BOOLEAN DEFAULT FALSE,

    -- 时间戳
    failed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_retry_at TIMESTAMP,

    -- 外键约束 (仅 match_id)
    CONSTRAINT fk_match_dlq
        FOREIGN KEY (match_id)
        REFERENCES matches(match_id)
        ON DELETE CASCADE
);

-- 创建索引 - 优化查询和重试
CREATE INDEX IF NOT EXISTS idx_dlq_match_id
    ON metrics_dead_letter_queue(match_id);

CREATE INDEX IF NOT EXISTS idx_dlq_source_name
    ON metrics_dead_letter_queue(source_name);

CREATE INDEX IF NOT EXISTS idx_dlq_failure_category
    ON metrics_dead_letter_queue(failure_category);

CREATE INDEX IF NOT EXISTS idx_dlq_retry
    ON metrics_dead_letter_queue(is_permanent_failure, retry_count)
    WHERE is_permanent_failure = FALSE;

-- 创建索引 - 优化重试查询
CREATE INDEX IF NOT EXISTS idx_dlq_pending_retry
    ON metrics_dead_letter_queue(match_id, source_name)
    WHERE is_permanent_failure = FALSE AND retry_count < max_retries;

-- 添加注释
COMMENT ON TABLE metrics_dead_letter_queue IS 'V120.0: 死信队列 - 存储未通过数据契约验证的数据';

COMMENT ON COLUMN metrics_dead_letter_queue.failure_category IS '故障分类: nan_values, out_of_range, identical, other';
COMMENT ON COLUMN metrics_dead_letter_queue.is_permanent_failure IS '是否为永久失败 (超过最大重试次数)';
COMMENT ON COLUMN metrics_dead_letter_queue.retry_count IS '当前重试次数';
COMMENT ON COLUMN metrics_dead_letter_queue.max_retries IS '最大重试次数 (默认3)';
