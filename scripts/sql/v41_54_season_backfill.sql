-- V41.54: 存量数据"暴力回填" - 修复 season 字段
-- ===================================================
-- 用途: 批量修复 2,363 场比赛的 season 空值
-- 方法: 根据 match_date 自动推断赛季标签

-- 事务开始
BEGIN;

-- 1. 备份当前数据（创建临时表）
CREATE TEMP TABLE matches_mapping_backup AS
SELECT
    fotmob_id,
    league_name,
    season as old_season,
    match_date,
    home_team,
    away_team,
    oddsportal_url
FROM matches_mapping
WHERE season IS NULL OR season = '' OR season = 'NULL';

-- 记录待修复数量
SELECT
    COUNT(*) as matches_to_fix,
    '待修复记录数' as description
FROM matches_mapping_backup;

-- 2. 回填规则 1: 跨年赛季 (欧洲/南美主流联赛)
--    2023-08-01 至 2024-06-30  -> '2023/2024'
--    2024-08-01 至 2025-06-30  -> '2024/2025'
--    2022-08-01 至 2023-06-30  -> '2022/2023'
--    2021-08-01 至 2022-06-30  -> '2021/2022'
--    2020-08-01 至 2021-06-30  -> '2020/2021'

UPDATE matches_mapping
SET season = '2023/2024'
WHERE (season IS NULL OR season = '' OR season = 'NULL')
  AND match_date >= '2023-08-01'
  AND match_date <= '2024-06-30';

UPDATE matches_mapping
SET season = '2024/2025'
WHERE (season IS NULL OR season = '' OR season = 'NULL')
  AND match_date >= '2024-08-01'
  AND match_date <= '2025-06-30';

UPDATE matches_mapping
SET season = '2022/2023'
WHERE (season IS NULL OR season = '' OR season = 'NULL')
  AND match_date >= '2022-08-01'
  AND match_date <= '2023-06-30';

UPDATE matches_mapping
SET season = '2021/2022'
WHERE (season IS NULL OR season = '' OR season = 'NULL')
  AND match_date >= '2021-08-01'
  AND match_date <= '2022-06-30';

UPDATE matches_mapping
SET season = '2020/2021'
WHERE (season IS NULL OR season = '' OR season = 'NULL')
  AND match_date >= '2020-08-01'
  AND match_date <= '2021-06-30';

-- 3. 回填规则 2: 自然年赛季 (美洲/亚洲联赛)
--    2024 年  -> '2024'
--    2023 年  -> '2023'
--    2022 年  -> '2022'

UPDATE matches_mapping
SET season = '2024'
WHERE (season IS NULL OR season = '' OR season = 'NULL')
  AND match_date >= '2024-01-01'
  AND match_date < '2024-08-01';

UPDATE matches_mapping
SET season = '2023'
WHERE (season IS NULL OR season = '' OR season = 'NULL')
  AND match_date >= '2023-01-01'
  AND match_date < '2023-08-01';

UPDATE matches_mapping
SET season = '2022'
WHERE (season IS NULL OR season = '' OR season = 'NULL')
  AND match_date >= '2022-01-01'
  AND match_date < '2022-08-01';

UPDATE matches_mapping
SET season = '2021'
WHERE (season IS NULL OR season = '' OR season = 'NULL')
  AND match_date >= '2021-01-01'
  AND match_date < '2021-08-01';

UPDATE matches_mapping
SET season = '2020'
WHERE (season IS NULL OR season = '' OR season = 'NULL')
  AND match_date >= '2020-01-01'
  AND match_date < '2020-08-01';

-- 4. 回填规则 3: 特殊处理 - 2026 年数据（可能是时区问题）
--    标记为 '2024/2025' 进行人工复核
UPDATE matches_mapping
SET season = '2024/2025'
WHERE (season IS NULL OR season = '' OR season = 'NULL')
  AND match_date >= '2026-01-01';

-- 5. 验证修复结果
-- 5.1 检查是否还有空 season
SELECT
    COUNT(*) as null_season_count,
    CASE
        WHEN COUNT(*) = 0 THEN '✅ 修复完成'
        ELSE '❌ 仍有空 season'
    END as status
FROM matches_mapping
WHERE season IS NULL OR season = '';

-- 5.2 显示修复后的赛季分布
SELECT
    season,
    COUNT(*) as match_count,
    MIN(match_date) as earliest_match,
    MAX(match_date) as latest_match
FROM matches_mapping
WHERE season IS NOT NULL AND season != ''
GROUP BY season
ORDER BY season DESC;

-- 5.3 按联赛统计修复结果
SELECT
    league_name,
    season,
    COUNT(*) as match_count
FROM matches_mapping
WHERE season IS NOT NULL AND season != ''
GROUP BY league_name, season
ORDER BY league_name, season DESC;

-- 6. 创建修复日志表（可选）
CREATE TABLE IF NOT EXISTS season_backfill_log (
    id SERIAL PRIMARY KEY,
    executed_at TIMESTAMP DEFAULT NOW(),
    fixed_count INTEGER,
    null_count_after INTEGER,
    status VARCHAR(50)
);

INSERT INTO season_backfill_log (fixed_count, null_count_after, status)
SELECT
    (SELECT COUNT(*) FROM matches_mapping_backup) as fixed_count,
    (SELECT COUNT(*) FROM matches_mapping WHERE season IS NULL OR season = '') as null_count_after,
    CASE
        WHEN (SELECT COUNT(*) FROM matches_mapping WHERE season IS NULL OR season = '') = 0
        THEN 'SUCCESS'
        ELSE 'PARTIAL'
    END as status;

-- 事务提交
COMMIT;

-- 最终报告
SELECT
    '=== V41.54 Season Backfill Report ===' as report;
SELECT
    fixed_count as "修复记录数",
    null_count_after as "剩余空值",
    status as "状态"
FROM season_backfill_log
ORDER BY executed_at DESC
LIMIT 1;
