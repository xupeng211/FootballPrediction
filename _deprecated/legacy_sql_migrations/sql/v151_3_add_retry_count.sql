-- V151.3 数据库迁移 - 添加重试计数和放弃状态
--
-- 功能: 防止永久无数据记录无限重试
--
-- Author: 高级数据运维架构师
-- Version: V151.3 (Infinite Loop Protection)
-- Date: 2026-01-11

-- ==============================================================================
-- 第一步: 添加 retry_count 字段
-- ==============================================================================

ALTER TABLE matches_mapping
ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;

-- 添加注释
COMMENT ON COLUMN matches_mapping.retry_count IS 'V151.3: 重试次数计数器，超过3次将标记为 abandoned';

-- ==============================================================================
-- 第二步: 扩展 mapping_status 枚举类型
-- ==============================================================================

-- PostgreSQL 不支持直接修改枚举类型，需要重建
-- 先添加新状态 'abandoned' (在 'malformed' 之后)
DO $$BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_enum WHERE enumlabel = 'abandoned'
        AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'mapping_status')
    ) THEN
        ALTER TYPE mapping_status ADD VALUE 'abandoned' AFTER 'malformed';
    END IF;
END$$;

-- ==============================================================================
-- 第三步: 为现有 malformed 记录初始化 retry_count
-- ==============================================================================

-- 统计当前需要初始化的记录数
SELECT
    '当前 malformed 记录数' as description,
    COUNT(*) as count
FROM matches_mapping
WHERE status = 'malformed';

-- 初始化 retry_count（基于 updated_at 推断）
-- 如果更新时间在 1 小时前，假设已重试过 1 次
UPDATE matches_mapping
SET retry_count = CASE
    WHEN updated_at < NOW() - INTERVAL '3 hours' THEN 3  -- 超过3小时，视为已重试3次
    WHEN updated_at < NOW() - INTERVAL '2 hours' THEN 2
    WHEN updated_at < NOW() - INTERVAL '1 hour' THEN 1
    ELSE 0  -- 1小时内的记录，视为首次失败
END
WHERE status = 'malformed'
  AND retry_count = 0;  -- 只更新未初始化的

-- ==============================================================================
-- 第四步: 标记超重试记录为 abandoned
-- ==============================================================================

-- 将 retry_count >= 3 的记录标记为 abandoned
UPDATE matches_mapping
SET status = 'abandoned',
    updated_at = NOW()
WHERE status = 'malformed'
  AND retry_count >= 3;

-- 显示 abandoned 统计
SELECT
    '已标记为 abandoned 的记录' as description,
    COUNT(*) as count
FROM matches_mapping
WHERE status = 'abandoned';

-- ==============================================================================
-- 第五步: 验证结果
-- ==============================================================================

-- 查看 status 分布
SELECT
    status,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) as percentage
FROM matches_mapping
WHERE oddsportal_url IS NOT NULL
GROUP BY status
ORDER BY status;

-- 查看 retry_count 分布
SELECT
    retry_count,
    COUNT(*) as count
FROM matches_mapping
WHERE status IN ('pending', 'malformed', 'harvested', 'abandoned')
GROUP BY retry_count
ORDER BY retry_count;

-- ==============================================================================
-- 后续步骤:
-- ==============================================================================
-- 1. 修改 harvest_pinnacle_odds.py 的 SQL 查询，添加 retry_count 限制
-- 2. 更新保存逻辑，失败时增加 retry_count
-- 3. 超过 3 次重试后，自动标记为 'abandoned'
