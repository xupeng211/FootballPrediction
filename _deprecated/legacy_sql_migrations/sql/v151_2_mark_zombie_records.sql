-- V151.2: 数据库"僵尸"识别与标记脚本
--
-- 功能:
-- 1. 将 retry_count >= 3 的记录标记为 abandoned
-- 2. 设置 mapping_method 为 'SEARCH_FAILED'
-- 3. 确保这些记录不会再被收割器处理
--
-- Author: 高级测试驱动架构师 (Staff SDET)
-- Date: 2026-01-11
-- Version: V151.2 (Deep Hardening Edition)

-- ==============================================================================
-- 步骤 1: 查看"僵尸"候选记录（重试 3 次以上）
-- ==============================================================================

SELECT
    retry_count,
    status,
    mapping_method,
    COUNT(*) as candidate_count
FROM matches_mapping
WHERE retry_count >= 3
GROUP BY retry_count, status, mapping_method
ORDER BY retry_count DESC;

-- ==============================================================================
-- 步骤 2: 标记"僵尸"记录
-- ==============================================================================

-- 将重试 3 次以上且仍为 pending/malformed 的记录标记为 abandoned
UPDATE matches_mapping
SET
    status = 'abandoned',
    mapping_method = 'SEARCH_FAILED',
    updated_at = NOW()
WHERE retry_count >= 3
  AND status IN ('pending', 'malformed');

-- ==============================================================================
-- 步骤 3: 验证标记结果
-- ==============================================================================

SELECT
    'abandoned' as status_group,
    COUNT(*) as count,
    COUNT(DISTINCT CASE WHEN mapping_method = 'SEARCH_FAILED' THEN fotmob_id END) as search_failed_count
FROM matches_mapping
WHERE status = 'abandoned'

UNION ALL

SELECT
    'pending_retry_ge_3' as status_group,
    COUNT(*) as count,
    0 as search_failed_count
FROM matches_mapping
WHERE status = 'pending' AND retry_count >= 3

UNION ALL

SELECT
    'total_records' as status_group,
    COUNT(*) as count,
    0 as search_failed_count
FROM matches_mapping;

-- ==============================================================================
-- 步骤 4: 创建索引以提高查询性能（可选）
-- ==============================================================================

-- 创建 retry_count 索引（如果不存在）
CREATE INDEX IF NOT EXISTS idx_matches_mapping_retry_count
ON matches_mapping(retry_count)
WHERE retry_count > 0;

-- 创建 abandoned 状态索引
CREATE INDEX IF NOT EXISTS idx_matches_mapping_abandoned
ON matches_mapping(status)
WHERE status = 'abandoned';

-- ==============================================================================
-- 说明
-- ==============================================================================

-- 标记为 abandoned 的记录将不会被收割器处理，避免无限重试。
-- mapping_method = 'SEARCH_FAILED' 表示这些记录在哈希搜索阶段失败。
-- 如需重新处理这些记录，可以手动将 status 改回 pending 并重置 retry_count。
