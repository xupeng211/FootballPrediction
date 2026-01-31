-- V41.58: 全库哈希错位深度扫描与修复 (SQL版本)
-- =====================================================
-- 用途: 检测并修复所有 URL 赛季与 season 字段不匹配的记录
-- 执行: docker-compose exec -T db psql -U football_user -d football_db -f scripts/sql/v41_58_deep_season_scan.sql
-- =====================================================

BEGIN;

-- =====================================================
-- 1. 创建临时视图：检测所有错位记录
-- =====================================================

CREATE TEMP TABLE v41_58_misaligned_records AS
SELECT
    fotmob_id,
    league_name,
    season as db_season,
    -- 从 URL 提取赛季并转换格式: 2023-2024 -> 2023/2024
    REPLACE(SUBSTRING(oddsportal_url FROM '[0-9]{4}-[0-9]{4}'), '-', '/') as url_season,
    oddsportal_url
FROM matches_mapping
WHERE oddsportal_url ~ '[0-9]{4}-[0-9]{4}'  -- URL 中包含赛季
  AND fotmob_id ~ '^[0-9]+$'                 -- 只扫描纯数字 ID
  AND season != REPLACE(SUBSTRING(oddsportal_url FROM '[0-9]{4}-[0-9]{4}'), '-', '/');  -- 赛季不匹配

-- =====================================================
-- 2. 统计错位记录数量
-- =====================================================

DO $$
DECLARE
    misaligned_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO misaligned_count FROM v41_58_misaligned_records;

    RAISE NOTICE '=====================================================';
    RAISE NOTICE 'V41.58: 全库哈希错位深度扫描结果';
    RAISE NOTICE '=====================================================';
    RAISE NOTICE '发现错位记录数: %', misaligned_count;

    IF misaligned_count = 0 THEN
        RAISE NOTICE '✅ 恭喜！未发现任何赛季错位记录';
    ELSE
        RAISE NOTICE '⚠️  需要修复 % 条错位记录', misaligned_count;
    END IF;

    RAISE NOTICE '=====================================================';
END $$;

-- =====================================================
-- 3. 按联赛显示错位记录分布
-- =====================================================

SELECT
    '📋 错位记录按联赛分布:' as info;

SELECT
    league_name,
    COUNT(*) as misaligned_count
FROM v41_58_misaligned_records
GROUP BY league_name
ORDER BY misaligned_count DESC;

-- =====================================================
-- 4. 显示前 20 条错位记录详情
-- =====================================================

SELECT
    '🔍 错位记录详情（前 20 条）:' as info;

SELECT
    fotmob_id,
    league_name,
    db_season,
    url_season,
    LEFT(oddsportal_url, 60) as url_preview
FROM v41_58_misaligned_records
ORDER BY league_name, db_season
LIMIT 20;

-- =====================================================
-- 5. 执行修复：重置错位记录的 URL 和 Hash
-- =====================================================

DO $$
DECLARE
    fixed_count INTEGER;
BEGIN
    -- 先记录修复前的数量
    SELECT COUNT(*) INTO fixed_count FROM v41_58_misaligned_records;

    -- 执行修复
    UPDATE matches_mapping mm
    SET oddsportal_url = NULL,
        oddsportal_hash = NULL,
        updated_at = NOW()
    WHERE fotmob_id IN (
        SELECT fotmob_id FROM v41_58_misaligned_records
    );

    RAISE NOTICE '=====================================================';
    RAISE NOTICE '🔧 修复完成: % 条记录已重置', fixed_count;
    RAISE NOTICE '=====================================================';
END $$;

-- =====================================================
-- 6. 验证修复结果
-- =====================================================

DO $$
DECLARE
    remaining_count INTEGER;
BEGIN
    -- 重新创建临时视图检查是否还有错位
    CREATE TEMP TABLE IF NOT EXISTS v41_58_verify_misaligned AS
    SELECT fotmob_id
    FROM matches_mapping
    WHERE oddsportal_url ~ '[0-9]{4}-[0-9]{4}'
      AND fotmob_id ~ '^[0-9]+$'
      AND season != REPLACE(SUBSTRING(oddsportal_url FROM '[0-9]{4}-[0-9]{4}'), '-', '/');

    SELECT COUNT(*) INTO remaining_count FROM v41_58_verify_misaligned;

    RAISE NOTICE '🔍 验证结果:';
    IF remaining_count = 0 THEN
        RAISE NOTICE '✅ 验证通过: 所有错位记录已修复';
    ELSE
        RAISE NOTICE '⚠️  仍有 % 条错位记录', remaining_count;
    END IF;

    RAISE NOTICE '=====================================================';
END $$;

COMMIT;

-- =====================================================
-- 7. 清理后的统计报告
-- =====================================================

SELECT
    '📊 V41.58 物理清淤完成 - 数据质量报告' as final_report;

SELECT
    league_name,
    season,
    COUNT(*) as total_matches,
    COUNT(CASE WHEN oddsportal_url IS NOT NULL THEN 1 END) as with_hash,
    COUNT(*) - COUNT(CASE WHEN oddsportal_url IS NOT NULL THEN 1 END) as missing_hash,
    ROUND(100.0 * COUNT(CASE WHEN oddsportal_url IS NOT NULL THEN 1 END) / COUNT(*), 2) as coverage_pct
FROM matches_mapping
WHERE fotmob_id ~ '^[0-9]+$'  -- 只统计纯数字 ID
GROUP BY league_name, season
ORDER BY league_name, season DESC;
