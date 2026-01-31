-- ==============================================================================
-- V150.33 数据完整性核查 SQL 脚本
-- ==============================================================================
-- 用途: 核查 1,390 条短 ID 的完整性
-- 版本: V150.33
-- 最后更新: 2026-01-09
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. 核查总记录数
-- ------------------------------------------------------------------------------
SELECT
    'total_records' AS metric,
    COUNT(*) AS value,
    'matches_mapping 表总记录数' AS description
FROM matches_mapping
UNION ALL
SELECT
    'with_l2_data',
    COUNT(*) FILTER (WHERE l2_raw_json IS NOT NULL),
    '包含 l2_raw_json 数据的记录数'
FROM matches_mapping
UNION ALL
SELECT
    'with_oddsportal_data',
    COUNT(*) FILTER (WHERE l2_raw_json -> 'oddsportal' IS NOT NULL),
    '包含 oddsportal 快照的记录数'
FROM matches_mapping
UNION ALL
SELECT
    'oddsportal_coverage',
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE l2_raw_json -> 'oddsportal' IS NOT NULL) /
        NULLIF(COUNT(*), 0),
        2
    ),
    'OddsPortal 数据覆盖率 (%)'
FROM matches_mapping;

-- ------------------------------------------------------------------------------
-- 2. 检查预期的 1,390 条记录是否存在
-- ------------------------------------------------------------------------------
-- 方法 A: 如果你有预期的 match_id 列表，创建临时表并检查
-- CREATE TEMP TABLE expected_match_ids (short_id VARCHAR(50) PRIMARY KEY);
-- INSERT INTO expected_match_ids VALUES
--     ('nsbKWw0O'),
--     ('KfIcpcUN'),
--     ('GziuczET');
--     -- ... 添加所有 1,390 个 ID

-- SELECT
--     'expected_vs_actual' AS check_type,
--     (SELECT COUNT(*) FROM expected_match_ids) AS expected_count,
--     (SELECT COUNT(*) FROM matches_mapping WHERE short_id IN (SELECT short_id FROM expected_match_ids)) AS actual_count,
--     (SELECT COUNT(*) FROM expected_match_ids) -
--         (SELECT COUNT(*) FROM matches_mapping WHERE short_id IN (SELECT short_id FROM expected_match_ids)) AS missing_count;

-- 方法 B: 快速检查最近导入的记录
SELECT
    'recent_imports' AS check_type,
    COUNT(*) AS count,
    MIN(created_at) AS earliest,
    MAX(created_at) AS latest
FROM matches_mapping
WHERE l2_raw_json -> 'oddsportal' IS NOT NULL
  AND created_at > NOW() - INTERVAL '7 days';

-- ------------------------------------------------------------------------------
-- 3. 核查数据质量 - 检查必需字段
-- ------------------------------------------------------------------------------
SELECT
    'data_quality_check' AS check_type,
    COUNT(*) FILTER (
        WHERE l2_raw_json -> 'oddsportal' -> 'snapshot' IS NOT NULL
    ) AS with_snapshot,
    COUNT(*) FILTER (
        WHERE l2_raw_json -> 'oddsportal' -> 'metadata' IS NOT NULL
    ) AS with_metadata,
    COUNT(*) FILTER (
        WHERE l2_raw_json -> 'oddsportal' -> 'metadata' ->> 'scraper_version' = 'V150.33'
    ) AS with_v150_33_version
FROM matches_mapping
WHERE l2_raw_json -> 'oddsportal' IS NOT NULL;

-- ------------------------------------------------------------------------------
-- 4. 检查数据完整性 - 赔率快照结构
-- ------------------------------------------------------------------------------
SELECT
    'snapshot_structure_check' AS check_type,
    COUNT(*) FILTER (
        WHERE l2_raw_json -> 'oddsportal' -> 'snapshot' -> 'home' IS NOT NULL
    ) AS with_home_odds,
    COUNT(*) FILTER (
        WHERE l2_raw_json -> 'oddsportal' -> 'snapshot' -> 'draw' IS NOT NULL
    ) AS with_draw_odds,
    COUNT(*) FILTER (
        WHERE l2_raw_json -> 'oddsportal' -> 'snapshot' -> 'away' IS NOT NULL
    ) AS with_away_odds,
    COUNT(*) FILTER (
        WHERE jsonb_array_length(l2_raw_json -> 'oddsportal' -> 'snapshot' -> 'home') > 0
    ) AS with_home_records,
    COUNT(*) FILTER (
        WHERE jsonb_array_length(l2_raw_json -> 'oddsportal' -> 'snapshot' -> 'draw') > 0
    ) AS with_draw_records,
    COUNT(*) FILTER (
        WHERE jsonb_array_length(l2_raw_json -> 'oddsportal' -> 'snapshot' -> 'away') > 0
    ) AS with_away_records
FROM matches_mapping
WHERE l2_raw_json -> 'oddsportal' IS NOT NULL;

-- ------------------------------------------------------------------------------
-- 5. 统计赔率记录数量分布
-- ------------------------------------------------------------------------------
SELECT
    'records_distribution' AS check_type,
    COUNT(*) AS match_count,
    jsonb_array_length(l2_raw_json -> 'oddsportal' -> 'snapshot' -> 'home') AS home_records,
    jsonb_array_length(l2_raw_json -> 'oddsportal' -> 'snapshot' -> 'draw') AS draw_records,
    jsonb_array_length(l2_raw_json -> 'oddsportal' -> 'snapshot' -> 'away') AS away_records
FROM matches_mapping
WHERE l2_raw_json -> 'oddsportal' -> 'snapshot' IS NOT NULL
GROUP BY
    jsonb_array_length(l2_raw_json -> 'oddsportal' -> 'snapshot' -> 'home'),
    jsonb_array_length(l2_raw_json -> 'oddsportal' -> 'snapshot' -> 'draw'),
    jsonb_array_length(l2_raw_json -> 'oddsportal' -> 'snapshot' -> 'away')
ORDER BY match_count DESC
LIMIT 20;

-- ------------------------------------------------------------------------------
-- 6. 检查采集时间范围
-- ------------------------------------------------------------------------------
SELECT
    'extraction_time_range' AS check_type,
    MIN(l2_raw_json -> 'oddsportal' -> 'metadata' ->> 'extraction_time') AS earliest_extraction,
    MAX(l2_raw_json -> 'oddsportal' -> 'metadata' ->> 'extraction_time') AS latest_extraction,
    COUNT(*) AS total_records
FROM matches_mapping
WHERE l2_raw_json -> 'oddsportal' -> 'metadata' ->> 'extraction_time' IS NOT NULL;

-- ------------------------------------------------------------------------------
-- 7. 检查代理使用分布
-- ------------------------------------------------------------------------------
SELECT
    'proxy_distribution' AS check_type,
    l2_raw_json -> 'oddsportal' -> 'metadata' ->> 'proxy' AS proxy,
    COUNT(*) AS usage_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS percentage
FROM matches_mapping
WHERE l2_raw_json -> 'oddsportal' -> 'metadata' ->> 'proxy' IS NOT NULL
GROUP BY l2_raw_json -> 'oddsportal' -> 'metadata' ->> 'proxy'
ORDER BY usage_count DESC;

-- ------------------------------------------------------------------------------
-- 8. 查找数据质量问题
-- ------------------------------------------------------------------------------
-- 8a. 查找缺少必需字段的记录
SELECT
    'missing_fields' AS check_type,
    short_id,
    CASE
        WHEN l2_raw_json -> 'oddsportal' -> 'snapshot' IS NULL THEN 'missing_snapshot'
        WHEN l2_raw_json -> 'oddsportal' -> 'metadata' IS NULL THEN 'missing_metadata'
        WHEN l2_raw_json -> 'oddsportal' -> 'metadata' ->> 'scraper_version' IS NULL THEN 'missing_version'
        ELSE 'unknown'
    END AS issue_type
FROM matches_mapping
WHERE l2_raw_json -> 'oddsportal' IS NOT NULL
  AND (
    l2_raw_json -> 'oddsportal' -> 'snapshot' IS NULL OR
    l2_raw_json -> 'oddsportal' -> 'metadata' IS NULL OR
    l2_raw_json -> 'oddsportal' -> 'metadata' ->> 'scraper_version' IS NULL
  )
LIMIT 10;

-- 8b. 查找空赔率数组的记录
SELECT
    'empty_odds_arrays' AS check_type,
    short_id,
    CASE
        WHEN jsonb_array_length(l2_raw_json -> 'oddsportal' -> 'snapshot' -> 'home') = 0 THEN 'empty_home'
        WHEN jsonb_array_length(l2_raw_json -> 'oddsportal' -> 'snapshot' -> 'draw') = 0 THEN 'empty_draw'
        WHEN jsonb_array_length(l2_raw_json -> 'oddsportal' -> 'snapshot' -> 'away') = 0 THEN 'empty_away'
        ELSE 'unknown'
    END AS issue_type
FROM matches_mapping
WHERE l2_raw_json -> 'oddsportal' -> 'snapshot' IS NOT NULL
  AND (
    jsonb_array_length(l2_raw_json -> 'oddsportal' -> 'snapshot' -> 'home') = 0 OR
    jsonb_array_length(l2_raw_json -> 'oddsportal' -> 'snapshot' -> 'draw') = 0 OR
    jsonb_array_length(l2_raw_json -> 'oddsportal' -> 'snapshot' -> 'away') = 0
  )
LIMIT 10;

-- ------------------------------------------------------------------------------
-- 9. 示例数据预览
-- ------------------------------------------------------------------------------
SELECT
    short_id,
    l2_raw_json -> 'oddsportal' -> 'metadata' ->> 'extraction_time' AS extraction_time,
    l2_raw_json -> 'oddsportal' -> 'metadata' ->> 'proxy' AS proxy,
    l2_raw_json -> 'oddsportal' -> 'metadata' ->> 'scraper_version' AS version,
    l2_raw_json -> 'oddsportal' -> 'metadata' -> 'stats' ->> 'total_records' AS total_records,
    created_at
FROM matches_mapping
WHERE l2_raw_json -> 'oddsportal' IS NOT NULL
ORDER BY created_at DESC
LIMIT 5;

-- ------------------------------------------------------------------------------
-- 10. 完整性汇总报告
-- ------------------------------------------------------------------------------
SELECT
    'integrity_summary' AS report_type,
    jsonb_build_object(
        'total_matches', COUNT(*),
        'with_oddsportal_data', COUNT(*) FILTER (WHERE l2_raw_json -> 'oddsportal' IS NOT NULL),
        'coverage_percentage', ROUND(
            100.0 * COUNT(*) FILTER (WHERE l2_raw_json -> 'oddsportal' IS NOT NULL) /
            NULLIF(COUNT(*), 0),
            2
        ),
        'avg_records_per_match', ROUND(
            AVG(
                jsonb_array_length(l2_raw_json -> 'oddsportal' -> 'snapshot' -> 'home') +
                jsonb_array_length(l2_raw_json -> 'oddsportal' -> 'snapshot' -> 'draw') +
                jsonb_array_length(l2_raw_json -> 'oddsportal' -> 'snapshot' -> 'away')
            ),
            2
        ),
        'unique_proxies', COUNT(DISTINCT l2_raw_json -> 'oddsportal' -> 'metadata' ->> 'proxy'),
        'v150_33_records', COUNT(*) FILTER (
            WHERE l2_raw_json -> 'oddsportal' -> 'metadata' ->> 'scraper_version' = 'V150.33'
        )
    ) AS summary
FROM matches_mapping;
