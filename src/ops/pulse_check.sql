-- ============================================
-- V20.8 数据质量心跳检测 SQL
-- ============================================
--
-- 功能: 每 10 分钟运行一次，检测数据质量
--
-- 检测项目:
-- 1. 最近 5 场比赛的 home_DF_total_interceptions 是否为 0
-- 2. 当前平均特征维度是否严格等于 881
-- 3. 数据完整性检查（NULL 值检测）
--
-- 作者: SRE Lead
-- 日期: 2025-12-25
-- 版本: V20.8
-- ============================================

\echo '========================================'
\echo 'V20.8 数据质量心跳检测'
\echo '检测时间: ' `date`
\echo '========================================'
\echo ''

-- ==================== 1. 特征维度检查 ====================
\echo '【1】特征维度检查 (881 维标准)'
\echo '----------------------------------------'

SELECT
    COUNT(*) as total_matches,
    ROUND(AVG(feature_count), 2) as avg_features,
    MIN(feature_count) as min_features,
    MAX(feature_count) as max_features,
    COUNT(*) FILTER (WHERE feature_count = 881) as exact_881_count,
    COUNT(*) FILTER (WHERE feature_count < 881) as below_881_count,
    COUNT(*) FILTER (WHERE feature_count > 881) as above_881_count
FROM (
    SELECT
        match_id,
        jsonb_array_length(enriched_features) as feature_count
    FROM match_features_training
    WHERE enriched_features IS NOT NULL
    ORDER BY updated_at DESC
    LIMIT 5
) recent_matches;

\echo ''

-- ==================== 2. 深度球员聚合检查 ====================
\echo '【2】深度球员聚合检查 (interceptions 应 > 0)'
\echo '----------------------------------------'

SELECT
    match_id,
    home_team,
    away_team,
    updated_at,
    COALESCE(
        (enriched_features->>'home_DF_total_interceptions')::numeric,
        -1
    ) as home_df_interceptions,
    COALESCE(
        (enriched_features->>'away_DF_total_interceptions')::numeric,
        -1
    ) as away_df_interceptions,
    CASE
        WHEN COALESCE((enriched_features->>'home_DF_total_interceptions')::numeric, 0) = 0
        THEN '⚠️ WARNING: DF interceptions = 0'
        ELSE '✓ OK'
    END as status
FROM match_features_training
WHERE enriched_features IS NOT NULL
ORDER BY updated_at DESC
LIMIT 5;

\echo ''

-- ==================== 3. 数据完整性检查 ====================
\echo '【3】数据完整性检查 (NULL 值检测)'
\echo '----------------------------------------'

SELECT
    COUNT(*) as total_matches,
    COUNT(*) FILTER (WHERE enriched_features IS NULL) as null_features_count,
    COUNT(*) FILTER (WHERE meta_data IS NULL) as null_metadata_count,
    COUNT(*) FILTER (WHERE status != 'completed') as not_completed_count,
    ROUND(100.0 * COUNT(*) FILTER (WHERE enriched_features IS NULL) / COUNT(*), 2) as null_percentage
FROM match_features_training;

\echo ''

-- ==================== 4. 提取版本分布 ====================
\echo '【4】提取版本分布'
\echo '----------------------------------------'

SELECT
    COALESCE((meta_data->>'extraction_version')::text, 'V0.0') as extraction_version,
    COUNT(*) as match_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM match_features_training
GROUP BY (meta_data->>'extraction_version')::text
ORDER BY extraction_version DESC;

\echo ''

-- ==================== 5. 最近 5 场比赛详情 ====================
\echo '【5】最近 5 场比赛详情'
\echo '----------------------------------------'

SELECT
    m.match_id,
    m.home_team,
    m.away_team,
    (m.meta_data->>'extraction_version')::text as version,
    (m.meta_data->>'feature_count')::int as features,
    m.status,
    m.updated_at
FROM match_features_training m
ORDER BY m.updated_at DESC
LIMIT 5;

\echo ''

-- ==================== 6. 维度死结警报 ====================
\echo '【6】维度死结警报'
\echo '----------------------------------------'

DO $$
DECLARE
    v_avg_features numeric;
    v_exact_881 int;
    v_alert_msg text;
BEGIN
    SELECT AVG(feature_count)
    INTO v_avg_features
    FROM (
        SELECT jsonb_array_length(enriched_features) as feature_count
        FROM match_features_training
        WHERE enriched_features IS NOT NULL
        ORDER BY updated_at DESC
        LIMIT 5
    ) recent_matches;

    SELECT COUNT(*)
    INTO v_exact_881
    FROM (
        SELECT jsonb_array_length(enriched_features) as feature_count
        FROM match_features_training
        WHERE enriched_features IS NOT NULL
        ORDER BY updated_at DESC
        LIMIT 5
    ) recent_matches
    WHERE feature_count = 881;

    IF v_exact_881 < 5 THEN
        RAISE NOTICE '🚨 ALERT: 维度死结检测 - 最近 5 场中有 % 场不等于 881 维！平均维度: %.2f', 5 - v_exact_881, v_avg_features;
    ELSE
        RAISE NOTICE '✅ PASS: 维度死结检测 - 所有 5 场比赛均为 881 维';
    END IF;
END $$;

\echo ''
\echo '========================================'
\echo '心跳检测完成'
\echo '========================================'
