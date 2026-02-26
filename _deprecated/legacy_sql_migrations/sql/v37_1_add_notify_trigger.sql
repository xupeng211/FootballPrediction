-- ============================================================================
-- V37.1: PostgreSQL NOTIFY/LISTEN 触发器
-- ============================================================================
-- 功能: 当 matches 表插入新数据时，自动发送 NOTIFY 信号
-- 目的: 实现"A驱动全自动闭环" - Layer B 自动化触发
--
-- 使用方法:
--   1. 执行本脚本创建触发器
--   2. 监听 'matches_insert' 频道
--   3. 插入测试数据验证信号
--
-- Author: 首席 SRE & 数据库架构师
-- Version: V37.1 Green Phase
-- Date: 2026-01-12
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Step 1: 创建 NOTIFY 函数
-- ----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION notify_match_insert()
RETURNS TRIGGER AS $$
DECLARE
    payload TEXT;
BEGIN
    -- 构造通知载荷 (JSON 格式)
    payload := json_build_object(
        'match_id', NEW.match_id,
        'league_name', NEW.league_name,
        'season', NEW.season,
        'home_team', NEW.home_team,
        'away_team', NEW.away_team,
        'match_date', EXTRACT(EPOCH FROM NEW.match_date),
        'timestamp', EXTRACT(EPOCH FROM NOW())
    )::TEXT;

    -- 发送 NOTIFY 信号到 'matches_insert' 频道
    PERFORM pg_notify('matches_insert', payload);

    -- 记录日志 (可选，用于调试)
    RAISE LOG 'V37.1 NOTIFY: matches_insert - match_id=%, payload=%', NEW.match_id, payload;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ----------------------------------------------------------------------------
-- Step 2: 创建触发器
-- ----------------------------------------------------------------------------

-- 先删除可能存在的旧触发器
DROP TRIGGER IF EXISTS trigger_match_insert_notify ON matches;

-- 创建新触发器
CREATE TRIGGER trigger_match_insert_notify
AFTER INSERT ON matches
FOR EACH ROW
EXECUTE FUNCTION notify_match_insert();


-- ----------------------------------------------------------------------------
-- Step 3: 验证安装
-- ----------------------------------------------------------------------------

-- 显示触发器信息
SELECT
    trigger_name,
    event_manipulation,
    event_object_table,
    action_statement
FROM information_schema.triggers
WHERE trigger_name = 'trigger_match_insert_notify';


-- ----------------------------------------------------------------------------
-- 使用示例: 手动监听测试
-- ----------------------------------------------------------------------------
-- 在 psql 中执行:
--
--   LISTEN matches_insert;
--   INSERT INTO matches (match_id, external_id, league_name, season, home_team, away_team)
--   VALUES ('test_notify_001', 'test_notify_001', 'La Liga', '2324', 'Test Home', 'Test Away');
--   -- 应该看到: Asynchronous notification 'matches_insert' with payload '{"match_id": "test_notify_001", ...}'
--
-- 或使用 Python 测试:
--   python scripts/ops/test_notify_listener.py
-- ----------------------------------------------------------------------------
