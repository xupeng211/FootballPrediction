-- V169.200 Harvest Inventory SQL
-- ================================
--
-- [Genesis.HarvestInventory] 8500场全量收割结果盘点
--
-- @version V169.200
-- @since 2026-02-03

-- ============================================================================
-- 1. 宏观产出统计 (Macro Stats)
-- ============================================================================

-- 1.1 入库总量 - 过去 6 小时内新增的记录
SELECT
    '入库总量' as metric,
    COUNT(*) as total_records,
    COUNT(DISTINCT match_id) as unique_matches
FROM metrics_multi_source_data
WHERE data_timestamp > NOW() - INTERVAL '6 hours';

-- 1.2 数据源分布
SELECT
    source_name,
    COUNT(*) as record_count,
    COUNT(DISTINCT match_id) as unique_matches,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM metrics_multi_source_data
WHERE data_timestamp > NOW() - INTERVAL '6 hours'
GROUP BY source_name
ORDER BY record_count DESC;

-- 1.3 时间分布 - 每小时入库量
SELECT
    DATE_TRUNC('hour', data_timestamp) as hour_bucket,
    COUNT(*) as records_per_hour,
    COUNT(DISTINCT match_id) as matches_per_hour
FROM metrics_multi_source_data
WHERE data_timestamp > NOW() - INTERVAL '6 hours'
GROUP BY DATE_TRUNC('hour', data_timestamp)
ORDER BY hour_bucket;

-- ============================================================================
-- 2. 数据质量审计 (Quality Deep-Dive)
-- ============================================================================

-- 2.1 胜平负完整性检查
SELECT
    COUNT(*) FILTER (WHERE init_h IS NULL) as null_opening_home,
    COUNT(*) FILTER (WHERE init_d IS NULL) as null_opening_draw,
    COUNT(*) FILTER (WHERE init_a IS NULL) as null_opening_away,
    COUNT(*) FILTER (WHERE final_h IS NULL) as null_closing_home,
    COUNT(*) FILTER (WHERE final_d IS NULL) as null_closing_draw,
    COUNT(*) FILTER (WHERE final_a IS NULL) as null_closing_away,
    COUNT(*) as total_records
FROM metrics_multi_source_data
WHERE data_timestamp > NOW() - INTERVAL '6 hours';

-- 2.2 轨迹点统计
SELECT
    AVG(jsonb_array_length(odds_history)) as avg_curve_points,
    MIN(jsonb_array_length(odds_history)) as min_curve_points,
    MAX(jsonb_array_length(odds_history)) as max_curve_points,
    STDDEV(jsonb_array_length(odds_history)) as stddev_curve_points,
    COUNT(*) FILTER (WHERE jsonb_array_length(odds_history) = 0) as zero_curve_records,
    COUNT(*) FILTER (WHERE jsonb_array_length(odds_history) >= 10) as rich_curve_records
FROM metrics_multi_source_data
WHERE data_timestamp > NOW() - INTERVAL '6 hours'
  AND source_name = 'Entity_bet365';

-- 2.3 时间跨度验证
SELECT
    source_name,
    TO_TIMESTAMP(MIN((odds_history->0->>'t')::bigint)) as earliest_timestamp,
    TO_TIMESTAMP(MAX((odds_history->(jsonb_array_length(odds_history)-1)->>'t')::bigint)) as latest_timestamp,
    EXTRACT(EPOCH FROM (TO_TIMESTAMP(MAX((odds_history->(jsonb_array_length(odds_history)-1)->>'t')::bigint)) -
                          TO_TIMESTAMP(MIN((odds_history->0->>'t')::bigint)))) / 86400 as span_days,
    COUNT(*) as record_count
FROM metrics_multi_source_data
WHERE data_timestamp > NOW() - INTERVAL '6 hours'
  AND source_name = 'Entity_bet365'
  AND jsonb_array_length(odds_history) > 0
GROUP BY source_name;

-- 2.4 年份分布验证 (检查 SyncTimestamp 稳定性)
SELECT
    EXTRACT(YEAR FROM TO_TIMESTAMP((odds_history->0->>'t')::bigint)) as detected_year,
    COUNT(*) as record_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM metrics_multi_source_data
WHERE data_timestamp > NOW() - INTERVAL '6 hours'
  AND source_name = 'Entity_bet365'
  AND jsonb_array_length(odds_history) > 0
GROUP BY EXTRACT(YEAR FROM TO_TIMESTAMP((odds_history->0->>'t')::bigint))
ORDER BY detected_year;

-- ============================================================================
-- 3. 新增比赛详情采样
-- ============================================================================

-- 3.1 随机采样 10 场新增比赛的详情
SELECT
    m.match_id,
    m.home_team,
    m.away_team,
    m.match_date,
    msd.source_name,
    jsonb_array_length(msd.odds_history) as curve_points,
    msd.init_h as opening_home,
    msd.final_h as closing_home,
    msd.data_timestamp
FROM matches m
INNER JOIN metrics_multi_source_data msd ON msd.match_id = m.match_id
WHERE msd.data_timestamp > NOW() - INTERVAL '6 hours'
  AND msd.source_name = 'Entity_bet365'
ORDER BY msd.data_timestamp DESC
LIMIT 10;

-- 3.2 检查是否有重复记录（同一比赛同一来源）
SELECT
    match_id,
    source_name,
    COUNT(*) as duplicate_count,
    ARRAY_AGG(data_timestamp ORDER BY data_timestamp) as insert_times
FROM metrics_multi_source_data
WHERE data_timestamp > NOW() - INTERVAL '6 hours'
GROUP BY match_id, source_name
HAVING COUNT(*) > 1;
