-- ============================================================================
-- V6.6 L2 原始数据存储层硬化 (Hardened L2 Raw Storage)
-- ============================================================================
-- 目标: 为 raw_match_data 表添加 V6.5 级别的工业级约束
-- 影响: L2b 原始数据收割组件 (ProductionHarvester + FotMobStrategy)
-- 日期: 2026-03-19
-- ============================================================================

-- ============================================================================
-- Step 1: 添加 data_version 字段 (与 L1 matches 表保持一致)
-- ============================================================================

ALTER TABLE raw_match_data
ADD COLUMN IF NOT EXISTS data_version VARCHAR(20) DEFAULT 'V26.1';

-- 为现有数据设置默认版本
UPDATE raw_match_data
SET data_version = 'V26.1'
WHERE data_version IS NULL;

-- ============================================================================
-- Step 2: 添加 external_id 字段 (便于追溯 FotMob 源数据)
-- ============================================================================

ALTER TABLE raw_match_data
ADD COLUMN IF NOT EXISTS external_id VARCHAR(50);

-- ============================================================================
-- Step 3: 添加 JSONB 数据校验约束
-- ============================================================================

-- 确保 raw_data 字段不为空且是有效的 JSONB
ALTER TABLE raw_match_data
ADD CONSTRAINT raw_data_not_empty
CHECK (raw_data IS NOT NULL AND raw_data <> '{}'::jsonb);

-- 确保 raw_data 包含关键字段 (FotMob 详情页标准字段)
ALTER TABLE raw_match_data
ADD CONSTRAINT raw_data_has_match_id
CHECK (raw_data ? 'matchId' OR raw_data ? 'general' OR raw_data ? 'header');

-- ============================================================================
-- Step 4: 添加时间戳约束
-- ============================================================================

-- 确保 collected_at 不为空
ALTER TABLE raw_match_data
ADD CONSTRAINT collected_at_not_null
CHECK (collected_at IS NOT NULL);

-- ============================================================================
-- Step 5: 添加 match_id 格式校验 (与 L1 保持一致)
-- ============================================================================

-- match_id 格式: {league_id}_{season_tag}_{external_id}
-- 示例: 47_20232024_4193450
ALTER TABLE raw_match_data
ADD CONSTRAINT match_id_format
CHECK (match_id ~ '^\d+_\d{8}_\d+$');

-- ============================================================================
-- Step 6: 创建索引优化
-- ============================================================================

-- 复合索引: 版本 + 采集时间 (用于快速查询最新数据)
CREATE INDEX IF NOT EXISTS idx_raw_data_version_collected
ON raw_match_data(data_version, collected_at DESC);

-- 索引: external_id (用于关联 FotMob API)
CREATE INDEX IF NOT EXISTS idx_raw_data_external_id
ON raw_match_data(external_id);

-- GIN 索引: raw_data 内容全文检索
CREATE INDEX IF NOT EXISTS idx_raw_data_gin
ON raw_match_data USING GIN(raw_data);

-- ============================================================================
-- Step 7: 创建自动更新时间戳触发器
-- ============================================================================

-- 创建触发器函数
CREATE OR REPLACE FUNCTION update_raw_data_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.collected_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 挂载触发器
DROP TRIGGER IF EXISTS trg_update_raw_data_timestamp ON raw_match_data;
CREATE TRIGGER trg_update_raw_data_timestamp
    BEFORE UPDATE ON raw_match_data
    FOR EACH ROW
    EXECUTE FUNCTION update_raw_data_timestamp();

-- ============================================================================
-- Step 8: 添加表注释
-- ============================================================================

COMMENT ON TABLE raw_match_data IS 'L2 原始数据存储层 - V6.6 硬化版本 (工业级约束)';
COMMENT ON COLUMN raw_match_data.data_version IS '数据版本 (与 L1 matches 表保持一致)';
COMMENT ON COLUMN raw_match_data.external_id IS 'FotMob 外部 ID';
COMMENT ON COLUMN raw_match_data.raw_data IS 'FotMob Match Details API 原始 JSONB 数据';
COMMENT ON COLUMN raw_match_data.collected_at IS '数据采集时间戳';

-- ============================================================================
-- 验证: 检查约束是否创建成功
-- ============================================================================

\echo 'V6.6 L2 硬化迁移完成!'
\echo '检查约束列表:'
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'raw_match_data'::regclass
AND contype = 'c';
