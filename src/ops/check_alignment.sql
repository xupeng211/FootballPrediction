-- V20.5 数据一致性对账脚本
-- ===========================
-- 用于随时查看各赛季的平均特征数和对账状态
--
-- 使用方式:
--   docker-compose exec -T db psql -U football_user -d football_db -f src/ops/check_alignment.sql
--
-- DataOps: SRE Team
-- Date: 2025-12-24

\echo '=========================================================='
\echo 'V20.5 数据一致性对账报告'
\echo '生成时间: ' || clock_timestamp()
\echo '=========================================================='
\echo ''

-- 1. 各赛季特征维度统计
\echo '📊 各赛季特征维度统计'
\echo '──────────────────────────────────────────────────────────'
SELECT
    season_id AS "赛季",
    COUNT(*) AS "场次数",
    ROUND(AVG((enriched_features->'_meta'->>'feature_count')::int), 1) AS "平均特征数",
    MIN((enriched_features->'_meta'->>'feature_count')::int) AS "最小特征数",
    MAX((enriched_features->'_meta'->>'feature_count')::int) AS "最大特征数",
    CASE
        WHEN ROUND(AVG((enriched_features->'_meta'->>'feature_count')::int), 1) >= 600 THEN '🌟 全息模式'
        WHEN ROUND(AVG((enriched_features->'_meta'->>'feature_count')::int), 1) >= 250 THEN '⚠️  兼容模式'
        ELSE '❌ 异常'
    END AS "模式判定"
FROM match_features_training
WHERE enriched_features ? '_meta'
GROUP BY season_id
ORDER BY season_id;

\echo ''

-- 2. 特征维度分布（按赛季）
\echo '📈 特征维度分布明细'
\echo '──────────────────────────────────────────────────────────'
SELECT
    season_id AS "赛季",
    (enriched_features->'_meta'->>'feature_count')::int AS "特征数",
    COUNT(*) AS "场次数",
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY season_id), 1) AS "占比(%)"
FROM match_features_training
WHERE enriched_features ? '_meta'
GROUP BY season_id, (enriched_features->'_meta'->>'feature_count')::int
ORDER BY season_id, (enriched_features->'_meta'->>'feature_count')::int DESC;

\echo ''

-- 3. 全息模式比赛清单（600+ 维）
\echo '🌟 全息模式比赛清单 (600+ 维)'
\echo '──────────────────────────────────────────────────────────'
SELECT
    season_id AS "赛季",
    COUNT(*) AS "场次数",
    ROUND(AVG((enriched_features->'_meta'->>'feature_count')::int), 1) AS "平均特征数"
FROM match_features_training
WHERE enriched_features ? '_meta'
  AND (enriched_features->'_meta'->>'feature_count')::int >= 600
GROUP BY season_id
ORDER BY season_id;

\echo ''

-- 4. 兼容模式比赛清单（250-599 维）
\echo '⚠️  兼容模式比赛清单 (250-599 维)'
\echo '──────────────────────────────────────────────────────────'
SELECT
    season_id AS "赛季",
    COUNT(*) AS "场次数",
    ROUND(AVG((enriched_features->'_meta'->>'feature_count')::int), 1) AS "平均特征数"
FROM match_features_training
WHERE enriched_features ? '_meta'
  AND (enriched_features->'_meta'->>'feature_count')::int >= 250
  AND (enriched_features->'_meta'->>'feature_count')::int < 600
GROUP BY season_id
ORDER BY season_id;

\echo ''

-- 5. 数据完整性总览
\echo '🎯 数据完整性总览'
\echo '──────────────────────────────────────────────────────────'
SELECT
    COUNT(*) AS "总场次数",
    COUNT(CASE WHEN (enriched_features->'_meta'->>'feature_count')::int >= 600 THEN 1 END) AS "全息模式(600+)",
    COUNT(CASE WHEN (enriched_features->'_meta'->>'feature_count')::int >= 250 AND (enriched_features->'_meta'->>'feature_count')::int < 600 THEN 1 END) AS "兼容模式(250-599)",
    COUNT(CASE WHEN (enriched_features->'_meta'->>'feature_count')::int < 250 THEN 1 END) AS "异常(<250)",
    ROUND(AVG((enriched_features->'_meta'->>'feature_count')::int), 1) AS "整体平均特征数"
FROM match_features_training
WHERE enriched_features ? '_meta';

\echo ''
\echo '=========================================================='
\echo '对账完成'
\echo '=========================================================='
