-- ============================================================================
-- V87.600 数据库约束修复脚本
-- ============================================================================
--
-- 功能: 为 temporal_metric_records 表建立优化的唯一约束以支持 UPSERT
--
-- 当前约束情况:
--   1. temporal_metric_records_entity_id_provider_name_metric_type_key
--      (entity_id, provider_name, metric_type, occurred_at)
--   2. idx_temporal_unique_record
--      (entity_id, provider_name, occurred_at, dimension, sequence)
--
-- 修复策略:
--   - 创建新的更精确的约束，覆盖所有关键维度
--   - 保留现有约束以避免破坏现有功能
--   - 使用 CONFLICT 处理策略
--
-- ============================================================================

-- ============================================================================
-- Step 1: 检查现有约束
-- ============================================================================

SELECT
    conname AS constraint_name,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conrelid = 'temporal_metric_records'::regclass
    AND contype = 'u'
ORDER BY conname;

-- ============================================================================
-- Step 2: 创建优化的唯一约束 (如果不存在)
-- ============================================================================

-- V87.600 核心约束 - 覆盖所有关键 UPSERT 维度
-- 包含 metric_type 以区分 Home/Draw/Away
-- 包含 dimension 以支持 single/aggregate 模式
-- 包含 sequence 以支持时序顺序

DO $$
BEGIN
    -- 检查约束是否已存在
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'temporal_metric_records'::regclass
            AND conname = 'v87_600_unique_metric_record'
    ) THEN
        -- 创建新约束
        ALTER TABLE temporal_metric_records
        ADD CONSTRAINT v87_600_unique_metric_record
        UNIQUE (entity_id, provider_name, metric_type, occurred_at, dimension, sequence);

        RAISE NOTICE 'Constraint v87_600_unique_metric_record created successfully';
    ELSE
        RAISE NOTICE 'Constraint v87_600_unique_metric_record already exists';
    END IF;
END $$;

-- ============================================================================
-- Step 3: 创建 UPSERT 友好的索引 (如果不存在)
-- ============================================================================

-- 这个索引优化了 UPSERT 查询性能
-- 同时支持按时间范围查询和去重

CREATE INDEX IF NOT EXISTS idx_v87_600_upsert_lookup
ON temporal_metric_records (entity_id, provider_name, occurred_at DESC, metric_type, dimension, sequence)
WHERE is_baseline = false;  -- 只索引非基线数据，提升索引效率

-- ============================================================================
-- Step 4: 验证约束创建
-- ============================================================================

SELECT
    conname AS constraint_name,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conrelid = 'temporal_metric_records'::regclass
    AND conname = 'v87_600_unique_metric_record';

-- ============================================================================
-- Step 5: 测试 UPSERT 操作 (验证约束工作正常)
-- ============================================================================

-- 测试数据 (使用虚拟 UUID)
-- 注意: 这个测试需要有效的 entity_id，实际使用时替换为真实 ID

-- INSERT 测试
/*
INSERT INTO temporal_metric_records (
    entity_id,
    provider_name,
    metric_type,
    value,
    occurred_at,
    dimension,
    sequence,
    payout
) VALUES (
    '00000000-0000-0000-0000-000000000001'::uuid,  -- 替换为真实 entity_id
    'Entity_P',
    'home_odd',
    1.85,
    '2024-01-26 10:00:00+00'::timestamptz,
    'single',
    0,
    0.95
)
ON CONFLICT (entity_id, provider_name, metric_type, occurred_at, dimension, sequence)
DO UPDATE SET
    value = EXCLUDED.value,
    payout = EXCLUDED.payout,
    updated_at = CURRENT_TIMESTAMP;
*/

-- ============================================================================
-- 完成信息
-- ============================================================================

SELECT 'V87.600 Database Constraint Fix Complete' AS status,
       'Ready for UPSERT operations' AS message;
