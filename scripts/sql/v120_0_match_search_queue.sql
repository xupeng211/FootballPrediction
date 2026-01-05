-- ============================================================================
-- V120.0 Phase 2: Match Search Queue Table
-- ============================================================================
-- Purpose: 任务队列管理系统 - 支持断点续传的搜索发现流程
--
-- State Machine:
--   PENDING -> SEARCHING -> SUCCESS / FAILED
--   FAILED -> PENDING (retry until max_retries)
--
-- Dependencies: matches 表 (外键)
-- ============================================================================

-- 创建任务队列表
CREATE TABLE IF NOT EXISTS match_search_queue (
    -- 主键
    match_id VARCHAR(50) PRIMARY KEY,

    -- 状态机 (PENDING, SEARCHING, SUCCESS, FAILED)
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',

    -- 搜索结果
    discovered_url TEXT,

    -- 重试机制
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 5,

    -- 错误追踪
    last_error TEXT,

    -- 时间戳
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- 外键约束
    CONSTRAINT fk_match
        FOREIGN KEY (match_id)
        REFERENCES matches(match_id)
        ON DELETE CASCADE
);

-- 创建索引 - 优化查询性能
CREATE INDEX IF NOT EXISTS idx_search_queue_status
    ON match_search_queue(status);

CREATE INDEX IF NOT EXISTS idx_search_queue_updated_at
    ON match_search_queue(updated_at DESC);

-- 创建索引 - 优化批量获取待处理任务
CREATE INDEX IF NOT EXISTS idx_search_queue_pending
    ON match_search_queue(status, updated_at)
    WHERE status IN ('PENDING', 'FAILED');

-- 添加注释
COMMENT ON TABLE match_search_queue IS 'V120.0: Phase 2 搜索任务队列 - 支持断点续传';

COMMENT ON COLUMN match_search_queue.status IS '任务状态: PENDING=待处理, SEARCHING=搜索中, SUCCESS=成功, FAILED=失败';
COMMENT ON COLUMN match_search_queue.retry_count IS '当前重试次数';
COMMENT ON COLUMN match_search_queue.max_retries IS '最大重试次数 (默认5)';
COMMENT ON COLUMN match_search_queue.discovered_url IS '发现的 OddsPortal URL';
COMMENT ON COLUMN match_search_queue.last_error IS '最后一次失败原因';
