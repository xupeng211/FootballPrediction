-- ============================================================================
-- V35.4 数据清洗 SQL 脚本 - 修正存量脏数据
-- ============================================================================
-- 用途: 修复数据库中 league_id 与 league_name 不匹配的存量数据
-- 执行: docker compose exec -T db psql -U football_user -d football_prediction_dev -f deploy/sql/fix_league_metadata_v35.4.sql
-- 日期: 2025-12-28
-- Phase: Root Cause Fix - League Metadata Correction
-- ============================================================================

-- 步骤 1: 创建 League ID 映射表
-- ----------------------------------------------------------------------------
CREATE TEMP TABLE league_id_mapping (
    league_id INT PRIMARY KEY,
    correct_name VARCHAR(100) NOT NULL
);

-- 插入正确的 FotMob League ID 映射
INSERT INTO league_id_mapping (league_id, correct_name) VALUES
    (47, 'Premier League'),
    (55, 'La Liga'),
    (54, 'Bundesliga'),
    (61, 'Ligue 1'),
    (135, 'Serie A'),
    (42, 'Champions League');

-- 步骤 2: 显示修正前的数据分布
-- ----------------------------------------------------------------------------
\echo '===== 修正前的数据分布 ====='
SELECT 
    league_id,
    league_name,
    COUNT(*) as match_count
FROM matches
GROUP BY league_id, league_name
ORDER BY league_id;

-- 步骤 3: 修正 league_name（基于 league_id）
-- ----------------------------------------------------------------------------
\echo '===== 开始修正 league_name ====='
UPDATE matches m
SET league_name = mapping.correct_name,
    updated_at = NOW()
FROM league_id_mapping mapping
WHERE m.league_id = mapping.league_id
  AND m.league_name != mapping.correct_name;

-- 步骤 4: 显示修正后的数据分布
-- ----------------------------------------------------------------------------
\echo '===== 修正后的数据分布 ====='
SELECT 
    league_id,
    league_name,
    COUNT(*) as match_count
FROM matches
GROUP BY league_id, league_name
ORDER BY league_id;

-- 步骤 5: 验证修正结果
-- ----------------------------------------------------------------------------
\echo '===== 修正结果验证 ====='
SELECT
    league_id,
    league_name,
    COUNT(*) as match_count,
    MIN(match_date) as earliest_match,
    MAX(match_date) as latest_match
FROM matches
GROUP BY league_id, league_name
ORDER BY league_id;

-- 清理临时表
DROP TABLE league_id_mapping;

\echo '===== 清理完成 ====='
