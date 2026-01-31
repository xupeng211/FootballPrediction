-- ============================================================================
-- V37.4 Layer D NOTIFY 触发器 - l3_odds_data UPDATE 事件
-- ============================================================================
-- 功能: 当 matches.l3_odds_data 字段被更新时，发送 NOTIFY 信号
-- 用途: EventBus 监听此信号，自动触发 Layer D 特征提取
--
-- Author: 首席系统架构师
-- Version: V37.4
-- Date: 2026-01-12
-- ============================================================================

-- 1. 创建 NOTIFY 触发函数
CREATE OR REPLACE FUNCTION notify_odds_updated()
RETURNS TRIGGER AS $$
DECLARE
    payload TEXT;
BEGIN
    -- 构建 JSON 载荷并转换为 TEXT (pg_notify 需要 TEXT 参数)
    payload = json_build_object(
        'match_id', NEW.match_id,
        'league_name', NEW.league_name,
        'has_odds', (NEW.l3_odds_data IS NOT NULL)
    )::TEXT;

    -- 发送 NOTIFY 信号到 'odds_updated' 频道
    PERFORM pg_notify('odds_updated', payload);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 2. 创建触发器 - 监听 l3_odds_data UPDATE
DROP TRIGGER IF EXISTS trigger_odds_updated ON matches;

CREATE TRIGGER trigger_odds_updated
    AFTER UPDATE OF l3_odds_data ON matches
    FOR EACH ROW
    WHEN (OLD.l3_odds_data IS DISTINCT FROM NEW.l3_odds_data AND NEW.l3_odds_data IS NOT NULL)
    EXECUTE FUNCTION notify_odds_updated();

-- 3. 验证安装
SELECT
    trigger_name,
    event_manipulation,
    event_object_table,
    action_statement
FROM information_schema.triggers
WHERE trigger_name = 'trigger_odds_updated';

-- 输出确认信息
DO $$
BEGIN
    RAISE NOTICE '======================================================================';
    RAISE NOTICE 'V37.4 Layer D NOTIFY 触发器安装完成';
    RAISE NOTICE '======================================================================';
    RAISE NOTICE '触发器名称: trigger_odds_updated';
    RAISE NOTICE '监听表: matches (l3_odds_data UPDATE)';
    RAISE NOTICE 'NOTIFY 频道: odds_updated';
    RAISE NOTICE '======================================================================';
END $$;
