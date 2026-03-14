-- ============================================================================
-- TITAN V6.0 Data Convergence Migration
-- 任务: TITAN-V6.0-DATA-CONVERGENCE
-- 
-- 目标: 在 l3_features 表中新增 market_sentiment JSONB 字段
-- 用于存储熔炼后的市场情绪特征
-- ============================================================================

-- 新增 market_sentiment 字段
ALTER TABLE l3_features
ADD COLUMN IF NOT EXISTS market_sentiment JSONB DEFAULT NULL;

-- 添加注释
COMMENT ON COLUMN l3_features.market_sentiment IS 
'市场情绪特征 (V6.0) - 包含赔率效率、市场偏见、庄家共识等8维特征';

-- 创建 GIN 索引以支持 JSONB 查询
CREATE INDEX IF NOT EXISTS idx_l3_features_market_sentiment 
ON l3_features USING GIN (market_sentiment);

-- 创建部分索引: 仅对包含 market_sentiment 的记录
CREATE INDEX IF NOT EXISTS idx_l3_features_has_market_sentiment 
ON l3_features (match_id) 
WHERE market_sentiment IS NOT NULL;

-- 验证迁移结果
DO $$
DECLARE
    v_count INT;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM information_schema.columns 
    WHERE table_name = 'l3_features' 
    AND column_name = 'market_sentiment';
    
    IF v_count = 1 THEN
        RAISE NOTICE '✅ market_sentiment 字段添加成功';
    ELSE
        RAISE EXCEPTION '❌ market_sentiment 字段添加失败';
    END IF;
END $$;

-- 显示当前表结构
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'l3_features'
ORDER BY ordinal_position;
