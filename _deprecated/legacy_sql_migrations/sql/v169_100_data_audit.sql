-- V169.100 Data Quality Audit SQL
-- =================================
--
-- [Genesis.DataAudit] 10场验证收割数据质检
--
-- 审计项:
-- 1. 完整性 - 10场比赛是否均已入库
-- 2. 轨迹深度 - bet365 平均变盘点数量
-- 3. 结构校验 - 时间戳对齐验证
-- 4. 成功率对比 - 日志 vs 数据库
--
-- @version V169.100
-- @since 2026-02-03

-- ============================================================================
-- 1. 完整性审计 - 确认 10 场比赛是否均已入库
-- ============================================================================

-- 1.1 统计 Entity_bet365 记录数
SELECT
    'Entity_bet365' as source_name,
    COUNT(*) as record_count,
    COUNT(DISTINCT match_id) as unique_matches
FROM metrics_multi_source_data
WHERE source_name = 'Entity_bet365'
  AND match_id IN (
      -- 从日志中提取的 10 场比赛 ID
      4830586, 4829452, 4830567, 4507132, 4534843,
      4534839, 4829247, 4534842, 4534840, 4534841
  );

-- 1.2 列出每场比赛的入库状态
SELECT
    m.match_id,
    m.home_team,
    m.away_team,
    m.match_date,
    COUNT(msd.match_id) as bet365_records,
    CASE
        WHEN COUNT(msd.match_id) > 0 THEN '✅ IN_DB'
        ELSE '❌ MISSING'
    END as status
FROM matches m
LEFT JOIN metrics_multi_source_data msd
    ON msd.match_id = m.match_id
    AND msd.source_name = 'Entity_bet365'
WHERE m.match_id IN (
    4830586, 4829452, 4830567, 4507132, 4534843,
    4534839, 4829247, 4534842, 4534840, 4534841
)
GROUP BY m.match_id, m.home_team, m.away_team, m.match_date
ORDER BY m.match_date DESC;

-- ============================================================================
-- 2. 轨迹深度统计 - bet365 变盘点数量
-- ============================================================================

-- 2.1 每场比赛的变盘点数量
SELECT
    match_id,
    source_name,
    jsonb_array_length(odds_history) as curve_points,
    init_h as opening_home,
    final_h as closing_home
FROM metrics_multi_source_data
WHERE source_name = 'Entity_bet365'
  AND match_id IN (
      4830586, 4829452, 4830567, 4507132, 4534843,
      4534839, 4829247, 4534842, 4534840, 4534841
  )
ORDER BY match_id;

-- 2.2 统计摘要
SELECT
    COUNT(*) as total_records,
    AVG(jsonb_array_length(odds_history)) as avg_curve_points,
    MIN(jsonb_array_length(odds_history)) as min_curve_points,
    MAX(jsonb_array_length(odds_history)) as max_curve_points,
    STDDEV(jsonb_array_length(odds_history)) as stddev_curve_points
FROM metrics_multi_source_data
WHERE source_name = 'Entity_bet365'
  AND match_id IN (
      4830586, 4829452, 4830567, 4507132, 4534843,
      4534839, 4829247, 4534842, 4534840, 4534841
  );

-- ============================================================================
-- 3. 结构校验 - 时间戳对齐验证 (随机抽取 1 场)
-- ============================================================================

-- 3.1 抽取 match_id = 4830586，展示首尾时间戳
SELECT
    match_id,
    source_name,
    -- 首个时间戳
    odds_history->0->>'t' as first_timestamp,
    odds_history->0->>'iso' as first_iso,
    -- 末尾时间戳
    odds_history->(jsonb_array_length(odds_history)-1)->>'t' as last_timestamp,
    odds_history->(jsonb_array_length(odds_history)-1)->>'iso' as last_iso,
    -- 年份校验
    EXTRACT(YEAR FROM TO_TIMESTAMP((odds_history->0->>'t')::bigint)) as detected_year,
    CASE
        WHEN EXTRACT(YEAR FROM TO_TIMESTAMP((odds_history->0->>'t')::bigint)) BETWEEN 2024 AND 2026
        THEN '✅ YEAR_ALIGNED'
        ELSE '❌ YEAR_MISMATCH'
    END as year_validation
FROM metrics_multi_source_data
WHERE match_id = 4830586
  AND source_name = 'Entity_bet365';

-- 3.2 展开首尾数据点完整结构
SELECT
    match_id,
    jsonb_pretty(odds_history->0) as first_point_structure,
    jsonb_pretty(odds_history->(jsonb_array_length(odds_history)-1)) as last_point_structure
FROM metrics_multi_source_data
WHERE match_id = 4830586
  AND source_name = 'Entity_bet365'
LIMIT 1;

-- ============================================================================
-- 4. 数据完整性高级审计
-- ============================================================================

-- 4.1 检查是否有空值或异常值
SELECT
    COUNT(*) FILTER (WHERE init_h IS NULL) as null_opening,
    COUNT(*) FILTER (WHERE final_h IS NULL) as null_closing,
    COUNT(*) FILTER (WHERE odds_history IS NULL) as null_history,
    COUNT(*) FILTER (WHERE jsonb_array_length(odds_history) = 0) as empty_history,
    COUNT(*) FILTER (WHERE market_payout IS NULL) as null_payout,
    COUNT(*) FILTER (WHERE is_valid = false) as invalid_records
FROM metrics_multi_source_data
WHERE source_name = 'Entity_bet365'
  AND match_id IN (
      4830586, 4829452, 4830567, 4507132, 4534843,
      4534839, 4829247, 4534842, 4534840, 4534841
  );

-- 4.2 检查主键冲突
SELECT
    match_id,
    source_name,
    COUNT(*) as duplicate_count
FROM metrics_multi_source_data
WHERE match_id IN (
    4830586, 4829452, 4830567, 4507132, 4534843,
    4534839, 4829247, 4534842, 4534840, 4534841
)
GROUP BY match_id, source_name
HAVING COUNT(*) > 1;

-- 4.3 检查最近数据插入时间
SELECT
    MAX(data_timestamp) as last_insert,
    MIN(data_timestamp) as first_insert,
    MAX(data_timestamp) - MIN(data_timestamp) as insert_span
FROM metrics_multi_source_data
WHERE source_name = 'Entity_bet365'
  AND match_id IN (
      4830586, 4829452, 4830567, 4507132, 4534843,
      4534839, 4829247, 4534842, 4534840, 4534841
  );
