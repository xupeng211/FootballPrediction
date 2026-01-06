-- ============================================================================
-- V26.3 Schema Migration: Matches Table Architecture Fix
-- ============================================================================
-- Purpose: 修复 matches 表架构问题
-- Author: Senior Database Engineer
-- Date: 2026-01-06
--
-- Changes:
--   1. 重命名 l2_raw_json → l2_extracted_features (反映真实用途)
--   2. 新增 l2_raw_json 字段用于存储真正的原始 FotMob JSON
--   3. 新增 collection_status 字段用于追踪采集状态
--   4. 新增 last_error 字段用于存储错误信息
--   5. 新增 updated_at 字段用于追踪记录更新时间
-- ============================================================================

-- ============================================================================
-- Step 1: 重命名现有字段
-- ============================================================================

-- 重命名 l2_raw_json → l2_extracted_features
-- 说明: 该字段实际存储的是已提取的特征字典，而非原始 JSON
ALTER TABLE matches
    RENAME COLUMN l2_raw_json TO l2_extracted_features;

-- 更新字段注释
COMMENT ON COLUMN matches.l2_extracted_features IS
    'V26.2 提取后的特征字典 (由 V25ProductionExtractor 输出)';

-- 更新 l2_data_version 字段注释
COMMENT ON COLUMN matches.l2_data_version IS
    '特征提取器版本 (V25.1, V26.2, etc.)';

-- ============================================================================
-- Step 2: 新增原始数据存储字段
-- ============================================================================

-- 新增 l2_raw_json 字段用于存储真正的原始 FotMob API JSON 响应
ALTER TABLE matches
    ADD COLUMN l2_raw_json JSONB;

COMMENT ON COLUMN matches.l2_raw_json IS
    'FotMob L2 API 原始 JSON 响应 (未经处理)';

-- 为新字段创建 GIN 索引以支持高效 JSON 查询
CREATE INDEX idx_matches_l2_raw_json_gin ON matches USING GIN (l2_raw_json);

-- ============================================================================
-- Step 3: 新增采集状态追踪字段
-- ============================================================================

-- 新增 collection_status 字段
ALTER TABLE matches
    ADD COLUMN collection_status VARCHAR(20)
    DEFAULT 'PENDING'
    NOT NULL;

COMMENT ON COLUMN matches.collection_status IS
    '数据采集状态: PENDING, IN_PROGRESS, SUCCESS, PARTIAL, FAILED';

-- 新增 last_error 字段
ALTER TABLE matches
    ADD COLUMN last_error TEXT;

COMMENT ON COLUMN matches.last_error IS
    '最后一次采集/提取错误信息';

-- 新增 collected_at 字段用于记录成功采集时间
ALTER TABLE matches
    ADD COLUMN collected_at TIMESTAMP WITH TIME ZONE;

COMMENT ON COLUMN matches.collected_at IS
    '数据成功采集时间 (collection_status = SUCCESS 时设置)';

-- 新增 extracted_at 字段用于记录特征提取时间
ALTER TABLE matches
    ADD COLUMN extracted_at TIMESTAMP WITH TIME ZONE;

COMMENT ON COLUMN matches.extracted_at IS
    '特征提取完成时间';

-- ============================================================================
-- Step 4: 新增/更新时间戳字段
-- ============================================================================

-- 如果 updated_at 不存在则新增，如果存在则更新注释
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'matches'
        AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE matches ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE;
    END IF;
END $$;

COMMENT ON COLUMN matches.updated_at IS
    '记录最后更新时间';

-- 创建 updated_at 索引
CREATE INDEX IF NOT EXISTS idx_matches_updated_at ON matches(updated_at DESC);

-- ============================================================================
-- Step 5: 创建状态查询索引
-- ============================================================================

-- 为 collection_status 创建索引以快速查询失败记录
CREATE INDEX idx_matches_collection_status ON matches(collection_status);

-- 为 last_error 创建全文索引用于错误搜索
CREATE INDEX idx_matches_last_error_trgm ON matches USING GIN (last_error gin_trgm_ops);

-- ============================================================================
-- Step 6: 数据迁移 - 从 l2_extracted_features 恢复状态
-- ============================================================================

-- 根据特征数量推断 collection_status
-- 特征数量 >= 3000 → SUCCESS
-- 特征数量 >= 1000 → PARTIAL
-- 特征数量 < 1000 → FAILED (可能的 NO_META)
UPDATE matches
SET
    collection_status = CASE
        WHEN JSONB_ARRAY_LENGTH(l2_extracted_features) >= 3000 THEN 'SUCCESS'
        WHEN JSONB_ARRAY_LENGTH(l2_extracted_features) >= 1000 THEN 'PARTIAL'
        ELSE 'FAILED'
    END,
    last_error = CASE
        WHEN JSONB_ARRAY_LENGTH(l2_extracted_features) < 1000
        THEN 'Insufficient features extracted (possible NO_META error)'
        ELSE NULL
    END,
    collected_at = CASE
        WHEN JSONB_ARRAY_LENGTH(l2_extracted_features) >= 1000 THEN collection_date
        ELSE NULL
    END,
    extracted_at = collection_date
WHERE l2_extracted_features IS NOT NULL;

-- ============================================================================
-- Step 7: 创建更新触发器
-- ============================================================================

-- 自动更新 updated_at 字段
CREATE OR REPLACE FUNCTION update_matches_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_matches_updated_at ON matches;
CREATE TRIGGER trigger_update_matches_updated_at
    BEFORE UPDATE ON matches
    FOR EACH ROW
    EXECUTE FUNCTION update_matches_updated_at();

-- ============================================================================
-- Step 8: 创建视图用于快速查询
-- ============================================================================

-- 创建失败记录视图
CREATE OR REPLACE VIEW v_failed_matches AS
SELECT
    match_id,
    external_id,
    league_name,
    season,
    home_team,
    away_team,
    match_date,
    collection_status,
    last_error,
    JSONB_ARRAY_LENGTH(l2_extracted_features) as feature_count,
    collected_at,
    extracted_at,
    updated_at
FROM matches
WHERE collection_status = 'FAILED'
ORDER BY updated_at DESC;

COMMENT ON VIEW v_failed_matches IS
    '数据采集/提取失败的记录视图 (用于 NO_META 诊断)';

-- 创建成功记录视图
CREATE OR REPLACE VIEW v_successful_matches AS
SELECT
    match_id,
    external_id,
    league_name,
    season,
    home_team,
    away_team,
    match_date,
    collection_status,
    JSONB_ARRAY_LENGTH(l2_extracted_features) as feature_count,
    l2_data_version,
    collected_at,
    extracted_at,
    updated_at
FROM matches
WHERE collection_status = 'SUCCESS'
ORDER BY collected_at DESC;

COMMENT ON VIEW v_successful_matches IS
    '成功采集的记录视图';

-- ============================================================================
-- Step 9: 授权
-- ============================================================================

-- 确保应用用户有权限
GRANT SELECT, INSERT, UPDATE ON matches TO football_user;
GRANT SELECT, UPDATE ON SEQUENCE matches_match_id_seq TO football_user;
GRANT SELECT ON v_failed_matches TO football_user;
GRANT SELECT ON v_successful_matches TO football_user;

-- ============================================================================
-- Step 10: 验证迁移
-- ============================================================================

-- 显示迁移结果
DO $$
DECLARE
    total_matches INT;
    status_counts TEXT;
BEGIN
    SELECT COUNT(*) INTO total_matches FROM matches;

    SELECT
        string_agg(collection_status || ': ' || COUNT, E'\n')
    INTO status_counts
    FROM (
        SELECT collection_status, COUNT(*)
        FROM matches
        GROUP BY collection_status
    ) t;

    RAISE NOTICE '=== V26.3 Schema Migration Complete ===';
    RAISE NOTICE 'Total matches: %', total_matches;
    RAISE NOTICE 'Status distribution: %', COALESCE(status_counts, 'N/A');
    RAISE NOTICE '==========================================';
END $$;

-- ============================================================================
-- Rollback Script (保存以备回滚)
-- ============================================================================
/*
-- 回滚步骤:
-- 1. DROP VIEW IF EXISTS v_failed_matches;
-- 2. DROP VIEW IF EXISTS v_successful_matches;
-- 3. DROP TRIGGER IF EXISTS trigger_update_matches_updated_at ON matches;
-- 4. DROP FUNCTION IF EXISTS update_matches_updated_at();
-- 5. DROP INDEX IF EXISTS idx_matches_collection_status;
-- 6. DROP INDEX IF EXISTS idx_matches_last_error_trgm;
-- 7. DROP INDEX IF EXISTS idx_matches_l2_raw_json_gin;
-- 8. DROP INDEX IF EXISTS idx_matches_updated_at;
-- 9. ALTER TABLE matches DROP COLUMN IF EXISTS updated_at;
-- 10. ALTER TABLE matches DROP COLUMN IF EXISTS extracted_at;
-- 11. ALTER TABLE matches DROP COLUMN IF EXISTS collected_at;
-- 12. ALTER TABLE matches DROP COLUMN IF EXISTS last_error;
-- 13. ALTER TABLE matches DROP COLUMN IF EXISTS collection_status;
-- 14. ALTER TABLE matches DROP COLUMN IF EXISTS l2_raw_json;
-- 15. ALTER TABLE matches RENAME COLUMN l2_extracted_features TO l2_raw_json;
*/
