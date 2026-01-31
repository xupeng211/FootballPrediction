-- ============================================================================
-- V32.1.2 Golden Training View (v_matches_clean)
-- ============================================================================
-- Purpose: 创建"黄金训练视图" - 过滤 malformed 数据，统一状态码
-- Author: 高级数据平台架构师 (Principal Architect)
-- Date: 2026-01-11
--
-- 核心功能:
-- 1. JOIN matches 和 matches_mapping 表
-- 2. 过滤 is_malformed = FALSE
-- 3. 只包含已收割数据 (status = 'harvested')
-- 4. 统一状态码映射: FT → MATCH_FINISHED
-- 5. 提供干净的训练数据集
--
-- 使用方法:
--   SELECT * FROM v_matches_clean WHERE league_name = 'Premier League';
-- ============================================================================

-- 删除旧视图（如果存在）
DROP VIEW IF EXISTS v_matches_clean CASCADE;

-- 创建黄金训练视图
CREATE VIEW v_matches_clean AS
SELECT
    -- 基础字段
    m.match_id,
    m.league_name,
    m.season,
    m.match_date,

    -- 队名信息（优先使用 matches 表，因为它是 FotMob 数据源）
    m.home_team,
    m.away_team,

    -- 比分数据
    m.home_score,
    m.away_score,
    m.actual_result,

    -- 统一状态码映射
    CASE
        WHEN m.status = 'FT' THEN 'MATCH_FINISHED'
        WHEN m.status = 'AW' THEN 'MATCH_AWARDED'  -- 异常终止
        WHEN m.status IN ('Scheduled', 'NS') THEN 'MATCH_SCHEDULED'
        WHEN m.status IN ('HT', 'ET') THEN 'MATCH_IN_PROGRESS'
        ELSE m.status
    END AS unified_status,

    -- 数据质量标记
    COALESCE(mm.is_malformed, FALSE) AS is_malformed,
    mm.status AS harvest_status,
    mm.confidence AS mapping_confidence,

    -- 采集元数据
    mm.oddsportal_url,
    mm.mapping_method,
    mm.created_at AS mapping_created_at,
    mm.updated_at AS mapping_updated_at,
    mm.retry_count,

    -- FotMob 原始数据（L2）
    m.l2_raw_json,
    m.l2_extracted_features,
    m.l2_data_version,

    -- 赔率数据（L3）
    m.l3_odds_data,
    m.l3_extraction_status,

    -- 数据版本
    m.data_version,
    m.data_source,

    -- 时间戳
    m.collected_at,
    m.extracted_at

FROM matches m

-- JOIN matches_mapping (通过 fotmob_id)
LEFT JOIN matches_mapping mm
    ON m.match_id = mm.fotmob_id

-- 过滤条件: 只包含干净数据
WHERE COALESCE(mm.is_malformed, FALSE) = FALSE  -- 排除 malformed 数据
  AND (
      mm.status IS NULL                          -- 没有 mapping 记录（纯 FotMob 数据）
      OR mm.status = 'harvested'                 -- 或已成功收割
  )
  AND m.home_score IS NOT NULL                  -- 必须有比分
  AND m.away_score IS NOT NULL
  AND m.status = 'FT'                           -- 只包含已完场比赛
  AND m.is_finished = TRUE;

-- 添加注释
COMMENT ON VIEW v_matches_clean IS '
黄金训练视图 - 提供干净的训练数据集

用途:
- 模型训练的数据源
- 数据质量分析
- 性能指标计算

过滤条件:
- is_malformed = FALSE
- status = harvested OR NULL (纯 FotMob 数据)
- match.status = FT (已完场)
- 有比分数据

状态码映射:
- FT → MATCH_FINISHED
- AW → MATCH_AWARDED
- HT/ET → MATCH_IN_PROGRESS
- Scheduled/NS → MATCH_SCHEDULED

版本: V32.1.2
更新: 2026-01-11
';

-- ============================================================================
-- 验证视图
-- ============================================================================

-- 检查视图记录数
SELECT 'v_matches_clean 记录数' as metric, COUNT(*) as count FROM v_matches_clean;

-- 按联赛统计
SELECT
    league_name,
    COUNT(*) as total_matches,
    COUNT(*) FILTER (WHERE oddsportal_url IS NOT NULL) as with_oddsportal,
    ROUND(100.0 * COUNT(*) FILTER (WHERE oddsportal_url IS NOT NULL) / COUNT(*), 2) as coverage_pct
FROM v_matches_clean
GROUP BY league_name
ORDER BY total_matches DESC
LIMIT 10;

-- 检查 malformed 数据泄漏（应该为 0）
SELECT 'Malformed 数据泄漏检查' as metric, COUNT(*) as count
FROM v_matches_clean
WHERE is_malformed = TRUE;
