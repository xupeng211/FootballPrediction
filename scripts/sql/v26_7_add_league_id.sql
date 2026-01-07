-- ============================================================================
-- V26.7 Schema Migration: 添加 league_id 列（双重标识支持）
--
-- 目的：实现 "数字索引优先" 原则，同时保留 league_name 可读性
--
-- 架构原则：
-- 1. league_id (INT) - 数字索引，用于高性能 JOIN 和聚合查询
-- 2. league_name (VARCHAR) - 可读性标识，用于展示和报表
--
-- 作者：高级数据库架构师
-- 日期：2026-01-07
-- ============================================================================

\echo '================================================================================'
\echo 'V26.7 Schema Migration: 添加 league_id 列'
\echo '================================================================================'
\timing on

-- ============================================================================
-- Step 1: 备份当前数据（安全第一）
-- ============================================================================
\echo ''
\echo '>>> Step 1: 数据备份 <<<'
\echo ''

-- 创建备份表
DROP TABLE IF EXISTS matches_backup_v26_7;
CREATE TABLE matches_backup_v26_7 AS
SELECT * FROM matches;

\echo '✅ 备份完成: matches_backup_v26_7'
SELECT COUNT(*) as backup_count FROM matches_backup_v26_7;

-- ============================================================================
-- Step 2: 添加 league_id 列
-- ============================================================================
\echo ''
\echo '>>> Step 2: 添加 league_id 列 <<<'
\echo ''

-- 检查列是否已存在
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'matches' AND column_name = 'league_id'
    ) THEN
        RAISE NOTICE 'league_id 列已存在，跳过添加';
    ELSE
        ALTER TABLE matches ADD COLUMN league_id INTEGER;
        RAISE NOTICE 'league_id 列添加成功';
    END IF;
END $$;

-- 添加注释
COMMENT ON COLUMN matches.league_id IS '联赛数字 ID（FotMob league_id），用于高性能索引和 JOIN';

-- ============================================================================
-- Step 3: 创建索引（加速查询）
-- ============================================================================
\echo ''
\echo '>>> Step 3: 创建索引 <<<'
\echo ''

-- 删除旧索引（如果存在）
DROP INDEX IF EXISTS idx_matches_league_id;
DROP INDEX IF EXISTS idx_matches_league_name;
DROP INDEX IF EXISTS idx_matches_league_combo;

-- 创建 league_id 索引（主索引）
CREATE INDEX idx_matches_league_id ON matches(league_id)
WHERE league_id IS NOT NULL;

-- 创建 league_name 索引（辅助索引）
CREATE INDEX idx_matches_league_name ON matches(league_name)
WHERE league_name IS NOT NULL;

-- 创建复合索引（league_id + season）
CREATE INDEX idx_matches_league_season ON matches(league_id, season)
WHERE league_id IS NOT NULL;

\echo '✅ 索引创建完成';

-- 显示索引信息
\echo ''
\echo '当前 matches 表索引:'
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'matches'
ORDER BY indexname;

-- ============================================================================
-- Step 4: 验证表结构
-- ============================================================================
\echo ''
\echo '>>> Step 4: 验证表结构 <<<'
\echo '

-- 显示新增列
\d matches

\echo ''
\echo '================================================================================'
\echo 'V26.7 Schema Migration 完成！'
\echo '下一步：运行 v26_7_history_alignment.sql 填充 league_id 数据'
\echo '================================================================================'
\timing off
