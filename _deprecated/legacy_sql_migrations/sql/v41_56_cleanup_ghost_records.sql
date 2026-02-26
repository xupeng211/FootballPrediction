-- V41.56: 清理幽灵记录和修复哈希错位
-- =====================================================
-- 用途: 清理 V40 DOM 收割器生成的 389 条 OP_ 幽灵记录
--       修复 3 处已知的哈希错位
-- 执行: docker-compose exec -T db psql -U football_user -d football_db -f scripts/sql/v41_56_cleanup_ghost_records.sql
-- =====================================================

BEGIN;

-- =====================================================
-- 1. 清理 OP_ 幽灵记录 (389 条)
-- =====================================================

-- 1.1 备份待删除记录（安全起见）
CREATE TEMP TABLE IF NOT EXISTS matches_mapping_op_backup AS
SELECT * FROM matches_mapping
WHERE fotmob_id ~ '^OP_';

-- 1.2 记录备份数量
DO $$
DECLARE
    backup_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO backup_count FROM matches_mapping_op_backup;
    RAISE NOTICE 'V41.56: 备份了 % 条 OP_ 幽灵记录', backup_count;
END $$;

-- 1.3 删除 OP_ 幽灵记录
DELETE FROM matches_mapping
WHERE fotmob_id ~ '^OP_';

-- 1.4 验证删除结果
DO $$
DECLARE
    remaining_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO remaining_count FROM matches_mapping WHERE fotmob_id ~ '^OP_';
    IF remaining_count > 0 THEN
        RAISE NOTICE '⚠️  V41.56: 仍有 % 条 OP_ 记录未删除', remaining_count;
    ELSE
        RAISE NOTICE '✅ V41.56: 所有 OP_ 幽灵记录已清理';
    END IF;
END $$;

-- =====================================================
-- 2. 修复哈希错位记录 (3 条)
-- =====================================================

-- 2.1 修复 Villarreal vs Real Madrid (fotmob_id: 4507032)
-- 问题: DB season=2024/2025, URL season=2023/2024
UPDATE matches_mapping
SET oddsportal_url = NULL,
    oddsportal_hash = NULL,
    updated_at = NOW()
WHERE fotmob_id = '4507032'
  AND oddsportal_url LIKE '%-2023-2024/%';

-- 2.2 修复 Milan vs Cagliari (fotmob_id: 4535314)
-- 问题: DB season=2024/2025, URL season=2023/2024
UPDATE matches_mapping
SET oddsportal_url = NULL,
    oddsportal_hash = NULL,
    updated_at = NOW()
WHERE fotmob_id = '4535314'
  AND oddsportal_url LIKE '%-2023-2024/%';

-- 2.3 修复 Metz vs Saint-Etienne (fotmob_id: 3625941)
-- 问题: DB season=2021/2022, URL season=2023/2024
UPDATE matches_mapping
SET oddsportal_url = NULL,
    oddsportal_hash = NULL,
    updated_at = NOW()
WHERE fotmob_id = '3625941'
  AND oddsportal_url LIKE '%-2023-2024/%';

-- 2.4 验证修复结果
DO $$
DECLARE
    fixed_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO fixed_count
    FROM matches_mapping
    WHERE fotmob_id IN ('4507032', '4535314', '3625941')
      AND oddsportal_url IS NULL;

    RAISE NOTICE '✅ V41.56: 修复了 % 条哈希错位记录', fixed_count;
END $$;

-- =====================================================
-- 3. 批量检查所有潜在错位记录（报告）
-- =====================================================

-- 3.1 查找所有 URL 赛季与数据库赛季不一致的记录
SELECT
    mm.fotmob_id,
    mm.league_name,
    mm.season as db_season,
    REPLACE(SUBSTRING(mm.oddsportal_url FROM '[0-9]{4}-[0-9]{4}'), '-', '/') as url_season,
    mm.oddsportal_url,
    m.match_date,
    CASE
        WHEN mm.oddsportal_url ~ '[0-9]{4}-[0-9]{4}' THEN
            REPLACE(SUBSTRING(mm.oddsportal_url FROM '[0-9]{4}-[0-9]{4}'), '-', '/') != mm.season
        ELSE FALSE
    END as is_misaligned
FROM matches_mapping mm
JOIN matches m ON mm.fotmob_id = m.match_id::text
WHERE mm.oddsportal_url ~ '[0-9]{4}-[0-9]{4}'
ORDER BY is_misaligned DESC, mm.league_name, mm.season;

-- =====================================================
-- 4. 最终统计
-- =====================================================

-- 4.1 显示清理后的统计
SELECT
    '=== V41.56 清理后统计 ===' as report;

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

COMMIT;

-- =====================================================
-- 执行结果验证
-- =====================================================

-- 预期结果:
-- 1. 删除 389 条 OP_ 幽灵记录
-- 2. 修复 3 条哈希错位记录
-- 3. 剩余 0 条 OP_ 记录
-- 4. 数据质量提升
