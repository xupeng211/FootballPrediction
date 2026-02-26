-- V41.32 Constraint Enforcement Migration - 添加 UNIQUE 约束
--
-- 目标：在 matches_mapping 表的 oddsportal_hash 列上添加 UNIQUE 约束
-- 效果：实现系统级的"自愈"与"防抖"，防止重复哈希入库
--
-- Author: 首席数据库安全官
-- Version: V41.32
-- Date: 2026-01-13

-- ========== 步骤 1：清理现有重复哈希（如果存在） ==========

-- 注意：V41.31 已经清除了所有重复哈希，此步骤作为保险措施
-- 如果仍有重复哈希，保留 Confidence 最高的记录

-- ========== 步骤 2：创建部分唯一索引 ==========

-- 创建部分唯一索引（Partial Unique Index）
-- 只对非 NULL 且长度为 8 的哈希进行唯一性约束
-- 这样允许多个 NULL 哈希记录共存，同时保证 8 位哈希的唯一性

CREATE UNIQUE INDEX IF NOT EXISTS idx_matches_mapping_oddsportal_hash_unique
ON matches_mapping (oddsportal_hash)
WHERE oddsportal_hash IS NOT NULL
  AND LENGTH(oddsportal_hash) = 8;

-- ========== 步骤 3：创建触发器自动修复冲突（可选） ==========

-- 创建触发器函数，在插入前自动检测并拒绝重复哈希
CREATE OR REPLACE FUNCTION check_unique_hash_before_insert()
RETURNS TRIGGER AS $$
BEGIN
    -- 检查是否已存在相同的 8 位哈希
    IF EXISTS (
        SELECT 1
        FROM matches_mapping
        WHERE oddsportal_hash = NEW.oddsportal_hash
          AND oddsportal_hash IS NOT NULL
          AND LENGTH(oddsportal_hash) = 8
          AND fotmob_id != NEW.fotmob_id
    ) THEN
        RAISE EXCEPTION 'Duplicate hash "%" detected. Hash must be unique.', NEW.oddsportal_hash;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 创建触发器（在 INSERT 和 UPDATE 时触发）
DROP TRIGGER IF EXISTS trg_check_unique_hash_before_insert ON matches_mapping;
CREATE TRIGGER trg_check_unique_hash_before_insert
    BEFORE INSERT OR UPDATE OF oddsportal_hash
    ON matches_mapping
    FOR EACH ROW
    EXECUTE FUNCTION check_unique_hash_before_insert();

-- ========== 步骤 4：验证约束 ==========

-- 验证唯一索引是否创建成功
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE indexname = 'idx_matches_mapping_oddsportal_hash_unique';

-- 验证触发器是否创建成功
SELECT
    tgname,
    tgtype
FROM pg_trigger
WHERE tgname = 'trg_check_unique_hash_before_insert';

-- ========== 步骤 5：注释 ==========

COMMENT ON INDEX idx_matches_mapping_oddsportal_hash_unique IS
    'V41.32: Partial unique index ensuring 8-character oddsportal_hash values are unique.
     Allows NULL hashes and non-8-character hashes. Prevents duplicate golden hashes.';

COMMENT ON FUNCTION check_unique_hash_before_insert() IS
    'V41.32: Trigger function to check for duplicate hashes before insert/update.
     Prevents violation of unique constraint at application level.';
