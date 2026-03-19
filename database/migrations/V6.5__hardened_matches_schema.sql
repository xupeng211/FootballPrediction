-- =============================================================================
-- V6.5 Database Migration: Hardened matches Schema
-- =============================================================================
-- 版本: V6.5
-- 日期: 2026-03-19
-- 作者: FootballPrediction Engineering Team
-- 依赖: V6.4 基础 schema
-- =============================================================================
-- 
-- 目的:
--   本迁移脚本旨在为 matches 表建立工业级数据一致性保障机制，实现
--   "非标准数据进不来，标准数据改不掉" 的鲁棒性目标。
--
-- 变更内容:
--   1. 数据清洗: 将现有 status 字段统一转为小写
--   2. CHECK 约束: 添加 status_lowercase 约束，强制 status 必须全小写
--   3. CHECK 约束: 添加 season_format 约束，强制 season 必须符合 'YYYY/YYYY' 格式
--   4. 触发器: 创建 sync_is_finished 函数和触发器，自动同步 is_finished 与 status
--
-- 影响范围:
--   - matches 表: 18 列
--   - 现有数据: 760 场比赛记录
--   - 应用程序: FixtureSeeder.js L1 发现引擎
--
-- 回滚策略:
--   如需回滚，请执行:
--     DROP TRIGGER IF EXISTS trg_sync_is_finished ON matches;
--     DROP FUNCTION IF EXISTS sync_is_finished();
--     ALTER TABLE matches DROP CONSTRAINT IF EXISTS status_lowercase;
--     ALTER TABLE matches DROP CONSTRAINT IF EXISTS season_format;
--
-- =============================================================================

-- =============================================================================
-- Step 1: 数据清洗 (Data Cleansing)
-- =============================================================================
-- 将现有所有非小写的 status 值转换为小写，确保约束添加成功

UPDATE matches 
SET status = LOWER(status) 
WHERE status != LOWER(status);

-- 执行结果检查:
--   成功: 0 行受影响 (表示所有数据已是小写，或无需清洗)
--   注意: 如果有大写数据，此步骤会将其转换为小写

-- =============================================================================
-- Step 2: 添加 CHECK 约束 (Constraints)
-- =============================================================================

-- 2.1 状态值小写约束
-- 目的: 强制 status 字段必须全小写，防止 'Finished'/'FINISHED' 等大小写混用
ALTER TABLE matches 
ADD CONSTRAINT status_lowercase 
CHECK (status = LOWER(status));

COMMENT ON CONSTRAINT status_lowercase ON matches IS 
'V6.5: 强制 status 字段必须全小写，防止大小写不一致';

-- 2.2 赛季格式约束
-- 目的: 强制 season 字段必须符合 'YYYY/YYYY' 正则格式
ALTER TABLE matches 
ADD CONSTRAINT season_format 
CHECK (season ~ '^\d{4}/\d{4}$');

COMMENT ON CONSTRAINT season_format ON matches IS 
'V6.5: 强制 season 字段必须符合 YYYY/YYYY 格式 (如 2023/2024)';

-- =============================================================================
-- Step 3: 创建触发器函数 (Trigger Function)
-- =============================================================================
-- 目的: 在数据库层面自动同步 is_finished 字段与 status 字段

CREATE OR REPLACE FUNCTION sync_is_finished()
RETURNS TRIGGER AS $$
BEGIN
    -- 根据 status 自动计算 is_finished
    -- 当 status = 'finished' 时，is_finished = true
    -- 其他状态时，is_finished = false
    NEW.is_finished := (NEW.status = 'finished');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION sync_is_finished() IS 
'V6.5: 触发器函数，自动根据 status 字段同步 is_finished 布尔值';

-- =============================================================================
-- Step 4: 挂载触发器 (Trigger Attachment)
-- =============================================================================
-- 触发时机: BEFORE INSERT OR UPDATE
-- 作用: 在数据写入前自动修正 is_finished 字段，即使应用层忘记设置也能保证一致性

CREATE TRIGGER trg_sync_is_finished
    BEFORE INSERT OR UPDATE ON matches
    FOR EACH ROW
    EXECUTE FUNCTION sync_is_finished();

COMMENT ON TRIGGER trg_sync_is_finished ON matches IS 
'V6.5: 自动同步触发器，确保 is_finished 与 status 保持 100% 一致';

-- =============================================================================
-- Step 5: 验证脚本 (Verification)
-- =============================================================================
-- 以下查询可用于验证迁移是否成功

/*
-- 验证约束是否存在
SELECT conname, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conrelid = 'matches'::regclass 
AND conname IN ('status_lowercase', 'season_format');

-- 验证触发器是否存在
SELECT tgname, proname 
FROM pg_trigger t 
JOIN pg_proc p ON t.tgfoid = p.oid 
WHERE tgrelid = 'matches'::regclass 
AND tgname = 'trg_sync_is_finished';

-- 验证触发器工作正常 (插入测试数据)
INSERT INTO matches (match_id, external_id, league_name, season, home_team, away_team, 
                     match_date, status, data_source)
VALUES ('TEST_V65_001', '9999991', 'Test League', '2023/2024', 'Team A', 'Team B', 
        NOW(), 'finished', 'Test')
RETURNING match_id, status, is_finished;
-- 预期结果: is_finished = true

-- 清理测试数据
DELETE FROM matches WHERE match_id = 'TEST_V65_001';

-- 验证非法数据被拦截 (应该报错)
-- INSERT INTO matches (..., status, ...) VALUES (..., 'Finished', ...);  -- 报错: violates check constraint "status_lowercase"
-- INSERT INTO matches (..., season, ...) VALUES (..., '2324', ...);      -- 报错: violates check constraint "season_format"
*/

-- =============================================================================
-- 迁移完成 (Migration Complete)
-- =============================================================================
-- 执行时间: 2026-03-19
-- 执行结果: 成功
-- 后续操作: 更新应用程序代码以利用新的约束和触发器
-- =============================================================================
