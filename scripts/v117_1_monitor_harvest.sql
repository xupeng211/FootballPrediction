-- ============================================================================
-- V117.1 Phase 1 收割进度实时监控 SQL
-- ============================================================================
-- 用途：实时监控 Entity_P 库存是否正在向 2,400 场大关迈进
-- 使用方法：在 PostgreSQL Shell 中执行
--   psql -h localhost -U football_user -d football_db -f scripts/v117_1_monitor_harvest.sql
-- ============================================================================

\echo ''
\echo '============================================================================'
\echo 'V117.1 Phase 1 收割进度 - 实时监控仪表盘'
\echo '============================================================================'
\echo ''

-- ----------------------------------------------------------------------------
-- 查询 1: Entity_P 总库存状态（核心指标）
-- ----------------------------------------------------------------------------
\echo '>>> Query 1: Entity_P 总库存状态'
\echo '--------------------------------------------------------------------'

SELECT
    'Entity_P 总库存' as metric_name,
    COUNT(*) as total_matches,
    COUNT(CASE WHEN final_h IS NOT NULL THEN 1 END) as has_final_odds,
    ROUND(100.0 * COUNT(CASE WHEN final_h IS NOT NULL THEN 1 END) / COUNT(*), 2) as coverage_percent
FROM metrics_multi_source_data
WHERE source_name = 'Entity_P';

\echo ''

-- ----------------------------------------------------------------------------
-- 查询 2: Phase 1 待收割队列状态
-- ----------------------------------------------------------------------------
\echo '>>> Query 2: Phase 1 待收割队列状态'
\echo '--------------------------------------------------------------------'

SELECT
    'Phase 1 待收割' as queue_status,
    COUNT(*) as pending_count,
    MIN(m.match_date) as earliest_match,
    MAX(m.match_date) as latest_match
FROM matches m
WHERE m.oddsportal_url IS NOT NULL
  AND m.oddsportal_url != ''
  AND m.oddsportal_url LIKE '%oddsportal.com%'
  AND m.is_finished = true
  AND NOT EXISTS (
      SELECT 1
      FROM metrics_multi_source_data msd
      WHERE msd.match_id = m.match_id
        AND msd.source_name = 'Entity_P'
        AND msd.final_h IS NOT NULL
  );

\echo ''

-- ----------------------------------------------------------------------------
-- 查询 3: 今日收割统计（过去 24 小时）
-- ----------------------------------------------------------------------------
\echo '>>> Query 3: 今日收割统计（过去 24 小时）'
\echo '--------------------------------------------------------------------'

SELECT
    DATE(extracted_at) as harvest_date,
    COUNT(*) as matches_harvested,
    COUNT(CASE WHEN source_name = 'Entity_P' THEN 1 END) as entity_p_count,
    COUNT(CASE WHEN source_name = 'Entity_W' THEN 1 END) as entity_w_count,
    COUNT(CASE WHEN source_name = 'Entity_B' THEN 1 END) as entity_b_count,
    COUNT(CASE WHEN source_name = 'Entity_L' THEN 1 END) as entity_l_count,
    COUNT(CASE WHEN source_name = 'Entity_AVG' THEN 1 END) as entity_avg_count
FROM metrics_multi_source_data
WHERE extracted_at >= CURRENT_DATE - INTERVAL '1 day'
GROUP BY DATE(extracted_at)
ORDER BY harvest_date DESC;

\echo ''

-- ----------------------------------------------------------------------------
-- 查询 4: Entity_P 捕获率趋势（最近 10 条入库记录）
-- ----------------------------------------------------------------------------
\echo '>>> Query 4: Entity_P 捕获率趋势（最近 10 条入库记录）'
\echo '--------------------------------------------------------------------'

SELECT
    extracted_at,
    match_id,
    integrity_score,
    CASE
        WHEN integrity_score BETWEEN 1.00 AND 1.08 THEN '✅ VALID'
        ELSE '⚠️ OUT_OF_RANGE'
    END as score_status,
    final_h, final_d, final_a
FROM metrics_multi_source_data
WHERE source_name = 'Entity_P'
  AND extracted_at >= CURRENT_DATE - INTERVAL '1 day'
ORDER BY extracted_at DESC
LIMIT 10;

\echo ''

-- ----------------------------------------------------------------------------
-- 查询 5: 各 Entity 库存对比
-- ----------------------------------------------------------------------------
\echo '>>> Query 5: 各 Entity 库存对比'
\echo '--------------------------------------------------------------------'

SELECT
    source_name as entity_name,
    COUNT(*) as total_records,
    COUNT(CASE WHEN final_h IS NOT NULL THEN 1 END) as has_final_odds,
    ROUND(AVG(integrity_score), 4) as avg_integrity_score,
    ROUND(100.0 * COUNT(CASE WHEN final_h IS NOT NULL THEN 1 END) / COUNT(*), 2) as data_completeness
FROM metrics_multi_source_data
WHERE source_name IN ('Entity_P', 'Entity_W', 'Entity_B', 'Entity_L', 'Entity_AVG')
GROUP BY source_name
ORDER BY COUNT(*) DESC;

\echo ''

-- ----------------------------------------------------------------------------
-- 查询 6: 完整性评分分布（Entity_P）
-- ----------------------------------------------------------------------------
\echo '>>> Query 6: 完整性评分分布（Entity_P）'
\echo '--------------------------------------------------------------------'

SELECT
    CASE
        WHEN integrity_score < 1.00 THEN '< 1.00 (Too Low)'
        WHEN integrity_score BETWEEN 1.00 AND 1.02 THEN '1.00 - 1.02 (Zero Juice)'
        WHEN integrity_score BETWEEN 1.02 AND 1.05 THEN '1.02 - 1.05 (Normal)'
        WHEN integrity_score BETWEEN 1.05 AND 1.08 THEN '1.05 - 1.08 (Normal)'
        ELSE '> 1.08 (Too High)'
    END as score_range,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM metrics_multi_source_data
WHERE source_name = 'Entity_P'
  AND integrity_score IS NOT NULL
GROUP BY score_range
ORDER BY
    CASE score_range
        WHEN '< 1.00 (Too Low)' THEN 1
        WHEN '1.00 - 1.02 (Zero Juice)' THEN 2
        WHEN '1.02 - 1.05 (Normal)' THEN 3
        WHEN '1.05 - 1.08 (Normal)' THEN 4
        ELSE 5
    END;

\echo ''

-- ----------------------------------------------------------------------------
-- 查询 7: V117.1 收割进度摘要
-- ----------------------------------------------------------------------------
\echo '>>> Query 7: V117.1 收割进度摘要'
\echo '--------------------------------------------------------------------'

WITH phase1_stats AS (
    SELECT
        COUNT(*) as total_pending,
        COUNT(CASE WHEN m.match_date >= CURRENT_DATE - INTERVAL '7 days' THEN 1 END) as recent_pending
    FROM matches m
    WHERE m.oddsportal_url IS NOT NULL
      AND m.oddsportal_url != ''
      AND m.oddsportal_url LIKE '%oddsportal.com%'
      AND m.is_finished = true
      AND NOT EXISTS (
          SELECT 1
          FROM metrics_multi_source_data msd
          WHERE msd.match_id = m.match_id
            AND msd.source_name = 'Entity_P'
            AND msd.final_h IS NOT NULL
      )
),
entity_p_stats AS (
    SELECT COUNT(*) as entity_p_total
    FROM metrics_multi_source_data
    WHERE source_name = 'Entity_P'
      AND final_h IS NOT NULL
)
SELECT
    'V117.1 收割进度' as summary_title,
    p.total_pending as phase1_pending,
    p.recent_pending as recent_7days_pending,
    e.entity_p_total as entity_p_inventory,
    CASE
        WHEN e.entity_p_total >= 2400 THEN '✅ TARGET_ACHIEVED'
        WHEN e.entity_p_total >= 2000 THEN '🟢 APPROACHING_TARGET'
        WHEN e.entity_p_total >= 1500 THEN '🟡 MAKING_PROGRESS'
        ELSE '🟠 EARLY_STAGE'
    END as progress_status
FROM phase1_stats p, entity_p_stats e;

\echo ''
\echo '============================================================================'
\echo 'V117.1 收割进度监控完成'
\echo '============================================================================'
\echo ''
