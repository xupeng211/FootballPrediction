-- ==============================================================================
-- V150.34 数据库迁移脚本 - 添加 l2_raw_json 字段
-- ==============================================================================
-- 用途: 为 matches_mapping 表添加 l2_raw_json JSONB 字段和索引
-- 版本: V150.34
-- 最后更新: 2026-01-09
-- ==============================================================================

-- 步骤 1: 添加 l2_raw_json 列
ALTER TABLE matches_mapping
ADD COLUMN IF NOT EXISTS l2_raw_json JSONB;

-- 步骤 2: 添加注释
COMMENT ON COLUMN matches_mapping.l2_raw_json IS 'OddsPortal 采集的原始 JSON 数据';

-- 步骤 3: 创建 GIN 索引用于 JSONB 查询优化
CREATE INDEX IF NOT EXISTS idx_l2_raw_json
ON matches_mapping
USING GIN (l2_raw_json);

-- 步骤 4: 验证迁移结果
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'matches_mapping'
  AND column_name = 'l2_raw_json';

-- 预期输出:
-- column_name   | data_type | is_nullable
-- --------------+-----------+-------------
-- l2_raw_json  | jsonb     | YES
