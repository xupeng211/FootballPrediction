-- V41.105: 添加 technical_features 字段到 matches 表
-- 作者：首席架构师 & 数据科学家 (V41.105)
-- 日期：2026-01-16
-- 描述：为 152 维技术特征（xG 细分、进攻三区传球等）添加专用存储空间

-- 检查字段是否已存在
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'matches'
        AND column_name = 'technical_features'
    ) THEN
        -- 添加 technical_features 字段（JSONB 类型）
        ALTER TABLE matches
        ADD COLUMN technical_features JSONB DEFAULT '{}'::jsonb;

        -- 添加注释
        COMMENT ON COLUMN matches.technical_features IS 'V41.105: 152维技术特征 (xG细分、进攻三区传球、对抗成功率等) - 来自 FotMob API /matchDetails 端点';

        -- 创建 GIN 索引（加速 JSONB 查询）
        CREATE INDEX IF NOT EXISTS idx_matches_technical_features
        ON matches USING GIN (technical_features);

        RAISE NOTICE '✅ technical_features 字段已成功添加';
    ELSE
        RAISE NOTICE '⚠️  technical_features 字段已存在，跳过添加';
    END IF;
END $$;

-- 验证字段添加
SELECT
    column_name,
    data_type,
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'matches'
AND column_name = 'technical_features';

-- 显示索引信息
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'matches'
AND indexname LIKE '%technical_features%';
