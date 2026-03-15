-- ============================================================================
-- TITAN V6.0 P0 Fortification - Backfill Progress Tracking
-- 任务: TITAN-V6.0-FORTIFY-P0
-- 
-- 目标: 创建 backfill_progress 表用于持久化回填进度
-- 功能: 断点续传、状态追踪、失败重试管理
-- ============================================================================

-- 创建回填进度表
CREATE TABLE IF NOT EXISTS backfill_progress (
    -- 主键: 比赛ID
    match_id VARCHAR(50) PRIMARY KEY,
    
    -- 回填状态
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- 可选值: pending (等待处理), processing (处理中), success (成功), failed (失败), skipped (跳过)
    
    -- 重试计数
    retry_count INTEGER NOT NULL DEFAULT 0,
    
    -- 最后错误信息
    last_error TEXT,
    
    -- 代理端口记录 (用于调试)
    proxy_port INTEGER,
    
    -- URL 哈希
    oddsportal_hash VARCHAR(100),
    
    -- 原始比赛信息 (冗余存储,避免JOIN)
    match_info JSONB,
    
    -- 批次ID (用于分批处理)
    batch_id VARCHAR(50),
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- 处理耗时 (毫秒)
    processing_time_ms INTEGER
);

-- 添加注释
COMMENT ON TABLE backfill_progress IS '回填进度追踪表 (V6.0 P0 加固)';
COMMENT ON COLUMN backfill_progress.match_id IS '比赛唯一标识';
COMMENT ON COLUMN backfill_progress.status IS '处理状态: pending/processing/success/failed/skipped';
COMMENT ON COLUMN backfill_progress.retry_count IS '重试次数 (最大3次)';
COMMENT ON COLUMN backfill_progress.last_error IS '最后一次错误信息';
COMMENT ON COLUMN backfill_progress.proxy_port IS '使用的代理端口';
COMMENT ON COLUMN backfill_progress.oddsportal_hash IS 'OddsPortal URL哈希';
COMMENT ON COLUMN backfill_progress.batch_id IS '批次标识,用于分批处理';

-- 创建索引优化查询
-- 按状态查询 (用于获取待处理任务)
CREATE INDEX IF NOT EXISTS idx_backfill_status 
ON backfill_progress(status);

-- 按状态和重试次数查询 (用于断点续传)
CREATE INDEX IF NOT EXISTS idx_backfill_resume 
ON backfill_progress(status, retry_count) 
WHERE status IN ('pending', 'failed') AND retry_count < 3;

-- 按批次查询
CREATE INDEX IF NOT EXISTS idx_backfill_batch 
ON backfill_progress(batch_id);

-- 按更新时间查询 (用于清理旧数据)
CREATE INDEX IF NOT EXISTS idx_backfill_updated 
ON backfill_progress(updated_at);

-- 创建更新时间自动更新触发器
CREATE OR REPLACE FUNCTION update_backfill_progress_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_backfill_progress_updated 
ON backfill_progress;

CREATE TRIGGER trigger_backfill_progress_updated
    BEFORE UPDATE ON backfill_progress
    FOR EACH ROW
    EXECUTE FUNCTION update_backfill_progress_timestamp();

-- 验证表结构
DO $$
DECLARE
    v_count INT;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM information_schema.tables 
    WHERE table_name = 'backfill_progress';
    
    IF v_count = 1 THEN
        RAISE NOTICE '✅ backfill_progress 表创建成功';
    ELSE
        RAISE EXCEPTION '❌ backfill_progress 表创建失败';
    END IF;
END $$;

-- 显示表结构
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'backfill_progress'
ORDER BY ordinal_position;
