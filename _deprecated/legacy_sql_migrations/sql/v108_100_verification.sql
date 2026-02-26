-- V108.100 数据对账验证脚本
-- ===================================
-- 用途: 在执行 V108.100 测试后，运行此 SQL 验证数据是否正确入库

-- 1. 检查测试样本的实体映射情况
SELECT
    '=== STEP 1: ENTITY MAPPING VERIFICATION ===' as section;

SELECT
    em.entity_id,
    em.source_id as match_id,
    em.source_url,
    em.is_active
FROM entities_mapping em
WHERE em.source_id IN (
    '4222388', '3610136', '4193865', '4230651', '4221737',
    '3900964', '4205633', '4193769', '4230662', '4230806'
)
ORDER BY em.source_id;

-- 2. 检查每场比赛的数据记录数
SELECT
    '=== STEP 2: RECORD COUNT PER MATCH ===' as section;

SELECT
    em.source_id as match_id,
    m.home_team,
    m.away_team,
    COUNT(tmr.id) as total_records,
    COUNT(DISTINCT tmr.metric_type) as distinct_dimensions,
    COUNT(DISTINCT tmr.provider_name) as distinct_providers
FROM entities_mapping em
LEFT JOIN matches m ON em.source_id = m.match_id
LEFT JOIN temporal_metric_records tmr ON tmr.entity_id = em.entity_id
WHERE em.source_id IN (
    '4222388', '3610136', '4193865', '4230651', '4221737',
    '3900964', '4205633', '4193769', '4230662', '4230806'
)
GROUP BY em.source_id, m.home_team, m.away_team
ORDER BY em.source_id;

-- 3. 检查 opening_odds 字段完整性
SELECT
    '=== STEP 3: OPENING ODDS INTEGRITY ===' as section;

SELECT
    em.source_id as match_id,
    m.home_team,
    m.away_team,
    COUNT(*) as total_records,
    COUNT(*) FILTER (WHERE tmr.raw_data::text ~ '"opening_odds":[0-9]') as has_real_opening_odds,
    COUNT(*) FILTER (WHERE tmr.raw_data::text ~ '"opening_odds":null') as null_opening_odds,
    COUNT(*) FILTER (WHERE tmr.raw_data::text ~ '"opening_source":"current-fallback"') as current_fallback,
    ROUND(100.0 * COUNT(*) FILTER (WHERE tmr.raw_data::text ~ '"opening_odds":[0-9]') / NULLIF(COUNT(*), 0), 2) as real_opening_percentage
FROM entities_mapping em
LEFT JOIN matches m ON em.source_id = m.match_id
LEFT JOIN temporal_metric_records tmr ON tmr.entity_id = em.entity_id
WHERE em.source_id IN (
    '4222388', '3610136', '4193865', '4230651', '4221737',
    '3900964', '4205633', '4193769', '4230662', '4230806'
)
GROUP BY em.source_id, m.home_team, m.away_team
ORDER BY em.source_id;

-- 4. 检查 history 数组结构
SELECT
    '=== STEP 4: HISTORY ARRAY VERIFICATION ===' as section;

SELECT
    em.source_id as match_id,
    m.home_team,
    m.away_team,
    COUNT(*) FILTER (WHERE tmr.raw_data::text ~ '"history":\[') as has_history_array,
    COUNT(*) FILTER (WHERE tmr.raw_data::text ~ '"history":\[') FILTER (
        tmr.raw_data::text ~ '\{[^}]*"time"[^}]*\}'::text
    ) as history_with_time_data,
    jsonb_array_length(tmr.raw_data->'history') as history_length
FROM entities_mapping em
LEFT JOIN matches m ON em.source_id = m.match_id
LEFT JOIN temporal_metric_records tmr ON tmr.entity_id = em.entity_id
WHERE em.source_id IN (
    '4222388', '3610136', '4193865', '4230651', '4221737',
    '3900964', '4205633', '4193769', '4230662', '4230806'
)
  AND tmr.raw_data::text ~ '"history":\['
LIMIT 5;

-- 5. 检查三轴完整性 (Home/Draw/Away)
SELECT
    '=== STEP 5: THREE-AXIS COMPLETENESS (1X2) ===' as section;

SELECT
    em.source_id as match_id,
    m.home_team,
    m.away_team,
    COUNT(*) FILTER (WHERE tmr.metric_type = 'home') as home_records,
    COUNT(*) FILTER (WHERE tmr.metric_type = 'draw') as draw_records,
    COUNT(*) FILTER (WHERE tmr.metric_type = 'away') as away_records,
    CASE
        WHEN COUNT(*) FILTER (WHERE tmr.metric_type = 'home') > 0
         AND COUNT(*) FILTER (WHERE tmr.metric_type = 'draw') > 0
         AND COUNT(*) FILTER (WHERE tmr.metric_type = 'away') > 0
        THEN '✓ FULL 1X2'
        ELSE '✗ INCOMPLETE'
    END as axis_completeness
FROM entities_mapping em
LEFT JOIN matches m ON em.source_id = m.match_id
LEFT JOIN temporal_metric_records tmr ON tmr.entity_id = em.entity_id
WHERE em.source_id IN (
    '4222388', '3610136', '4193865', '4230651', '4221737',
    '3900964', '4205633', '4193769', '4230662', '4230806'
)
GROUP BY em.source_id, m.home_team, m.away_team
ORDER BY em.source_id;

-- 6. 供应商识别统计
SELECT
    '=== STEP 6: PROVIDER IDENTIFICATION STATS ===' as section;

SELECT
    tmr.provider_name,
    COUNT(*) as record_count,
    COUNT(DISTINCT tmr.entity_id) as unique_matches
FROM temporal_metric_records tmr
WHERE tmr.entity_id IN (
    SELECT entity_id FROM entities_mapping WHERE source_id IN (
        '4222388', '3610136', '4193865', '4230651', '4221737',
        '3900964', '4205633', '4193769', '4230662', '4230806'
    )
)
GROUP BY tmr.provider_name
ORDER BY record_count DESC;

-- 7. 总体数据质量评分
SELECT
    '=== STEP 7: DATA QUALITY SCORE ===' as section;

SELECT
    COUNT(DISTINCT tmr.entity_id) as total_matches_with_data,
    COUNT(*) as total_records,
    COUNT(DISTINCT tmr.entity_id) FILTER (
        EXISTS (
            SELECT 1 FROM temporal_metric_records tmr2
            WHERE tmr2.entity_id = tmr.entity_id
              AND tmr2.metric_type = 'home'
        )
        AND EXISTS (
            SELECT 1 FROM temporal_metric_records tmr3
            WHERE tmr3.entity_id = tmr.entity_id
              AND tmr3.metric_type = 'draw'
        )
        AND EXISTS (
            SELECT 1 FROM temporal_metric_records tmr4
            WHERE tmr4.entity_id = tmr.entity_id
              AND tmr4.metric_type = 'away'
        )
    ) as matches_with_full_1x2,
    COUNT(*) FILTER (WHERE tmr.raw_data::text ~ '"opening_odds":[0-9]') as records_with_real_opening,
    COUNT(*) FILTER (WHERE tmr.raw_data::text ~ '"history":\[') as records_with_history,
    ROUND(100.0 * COUNT(DISTINCT tmr.entity_id) FILTER (
        EXISTS (
            SELECT 1 FROM temporal_metric_records tmr2
            WHERE tmr2.entity_id = tmr.entity_id
              AND tmr2.metric_type = 'home'
        )
        AND EXISTS (
            SELECT 1 FROM temporal_metric_records tmr3
            WHERE tmr3.entity_id = tmr.entity_id
              AND tmr3.metric_type = 'draw'
        )
        AND EXISTS (
            SELECT 1 FROM temporal_metric_records tmr4
            WHERE tmr4.entity_id = tmr.entity_id
              AND tmr4.metric_type = 'away'
        )
    ) / 10, 1) as quality_score_percentage
FROM temporal_metric_records tmr
WHERE tmr.entity_id IN (
    SELECT entity_id FROM entities_mapping WHERE source_id IN (
        '4222388', '3610136', '4193865', '4230651', '4221737',
        '3900964', '4205633', '4193769', '4230662', '4230806'
    )
);
