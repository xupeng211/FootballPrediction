-- ============================================================================
-- V150.2.2 L3 数据库迁移脚本
-- ============================================================================
-- 功能：为 matches 表添加 L3 赔率数据存储字段
-- 创建时间：2026-01-08
-- 作者：高级数据库管理员 (DBA)
-- ============================================================================

-- 开始事务
BEGIN;

-- 1. 添加 L3 赔率数据字段 (JSONB)
ALTER TABLE matches
  ADD COLUMN IF NOT EXISTS l3_odds_data JSONB;

-- 2. 添加 L3 提取状态字段
ALTER TABLE matches
  ADD COLUMN IF NOT EXISTS l3_extraction_status VARCHAR(20);

-- 3. 添加 L3 提取时间字段
ALTER TABLE matches
  ADD COLUMN IF NOT EXISTS l3_extracted_at TIMESTAMP;

-- 4. 添加 L3 数据不匹配标志
ALTER TABLE matches
  ADD COLUMN IF NOT EXISTS l3_data_mismatch BOOLEAN DEFAULT FALSE;

-- 5. 创建索引加速查询
CREATE INDEX IF NOT EXISTS idx_matches_l3_extraction_status
  ON matches(l3_extraction_status)
  WHERE l3_extraction_status IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_matches_l3_extracted_at
  ON matches(l3_extracted_at DESC)
  WHERE l3_extracted_at IS NOT NULL;

-- 6. 添加注释
COMMENT ON COLUMN matches.l3_odds_data IS 'V150.2.2 L3 赔率数据 (JSONB): 包含 opening_odds 和 closing_odds';
COMMENT ON COLUMN matches.l3_extraction_status IS 'V150.2.2 L3 提取状态: success/failed/null';
COMMENT ON COLUMN matches.l3_extracted_at IS 'V150.2.2 L3 数据提取时间戳';
COMMENT ON COLUMN matches.l3_data_mismatch IS 'V150.2.2 L3 数据是否不匹配 (比分验证失败)';

-- 提交事务
COMMIT;

-- 验证迁移结果
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'matches'
  AND column_name IN ('l3_odds_data', 'l3_extraction_status', 'l3_extracted_at', 'l3_data_mismatch')
ORDER BY ordinal_position;
