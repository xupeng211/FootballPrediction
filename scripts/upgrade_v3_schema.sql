-- V3.0 Schema 升级脚本
-- 为 match_features_training 表添加西甲收割必需字段

-- 执行时间: 2025-12-21
-- 目标: 支持 106 维特征存储，兼容全球联赛数据

-- 开始事务
BEGIN;

-- 添加联赛标识字段
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='match_features_training' AND column_name='league_id') THEN
        ALTER TABLE match_features_training
        ADD COLUMN league_id VARCHAR(50) DEFAULT NULL;
        RAISE NOTICE 'Added column: league_id';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='match_features_training' AND column_name='league_name') THEN
        ALTER TABLE match_features_training
        ADD COLUMN league_name VARCHAR(100) DEFAULT NULL;
        RAISE NOTICE 'Added column: league_name';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='match_features_training' AND column_name='is_real_data') THEN
        ALTER TABLE match_features_training
        ADD COLUMN is_real_data BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Added column: is_real_data';
    END IF;
END $$;

-- 添加特征向量版本字段
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='match_features_training' AND column_name='feature_version') THEN
        ALTER TABLE match_features_training
        ADD COLUMN feature_version VARCHAR(20) DEFAULT 'v3.0';
        RAISE NOTICE 'Added column: feature_version';
    END IF;
END $$;

-- 添加数据来源标识字段
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='match_features_training' AND column_name='data_source') THEN
        ALTER TABLE match_features_training
        ADD COLUMN data_source VARCHAR(50) DEFAULT 'harvested';
        RAISE NOTICE 'Added column: data_source';
    END IF;
END $$;

-- 确保所有可能需要的字段都存在
DO $$
DECLARE
    missing_columns TEXT[];
BEGIN
    -- 检查并添加可能的缺失字段
    SELECT ARRAY_AGG(column_name) INTO missing_columns
    FROM (
        -- 基础字段检查
        SELECT 'match_time' AS column_name WHERE NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='match_features_training' AND column_name='match_time'
        )
        UNION ALL
        SELECT 'collection_date' WHERE NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='match_features_training' AND column_name='collection_date'
        )
        UNION ALL
        -- xG 相关字段
        SELECT 'home_xg_first_half' WHERE NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='match_features_training' AND column_name='home_xg_first_half'
        )
        UNION ALL
        SELECT 'away_xg_first_half' WHERE NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='match_features_training' AND column_name='away_xg_first_half'
        )
        UNION ALL
        SELECT 'home_xg_second_half' WHERE NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='match_features_training' AND column_name='home_xg_second_half'
        )
        UNION ALL
        SELECT 'away_xg_second_half' WHERE NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='match_features_training' AND column_name='away_xg_second_half'
        )
        UNION ALL
        -- 角球相关字段
        SELECT 'home_corners_first_half' WHERE NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='match_features_training' AND column_name='home_corners_first_half'
        )
        UNION ALL
        SELECT 'away_corners_first_half' WHERE NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='match_features_training' AND column_name='away_corners_first_half'
        )
        UNION ALL
        SELECT 'home_corners_second_half' WHERE NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='match_features_training' AND column_name='home_corners_second_half'
        )
        UNION ALL
        SELECT 'away_corners_second_half' WHERE NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='match_features_training' AND column_name='away_corners_second_half'
        )
        UNION ALL
        -- 赔率相关字段
        SELECT 'home_opening_odds' WHERE NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='match_features_training' AND column_name='home_opening_odds'
        )
        UNION ALL
        SELECT 'away_opening_odds' WHERE NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='match_features_training' AND column_name='away_opening_odds'
        )
        UNION ALL
        SELECT 'draw_opening_odds' WHERE NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name='match_features_training' AND column_name='draw_opening_odds'
        )
    ) missing;

    -- 执行字段添加 (简化版本，避免复杂的 PL/pgSQL 语法)
    IF missing_columns IS NOT NULL AND array_length(missing_columns, 1) > 0 THEN
        -- 手动添加常见缺失字段
        IF 'match_time' = ANY(missing_columns) THEN
            ALTER TABLE match_features_training ADD COLUMN match_time TIMESTAMP WITH TIME ZONE DEFAULT NULL;
            RAISE NOTICE 'Added column: match_time';
        END IF;

        IF 'collection_date' = ANY(missing_columns) THEN
            ALTER TABLE match_features_training ADD COLUMN collection_date TIMESTAMP WITH TIME ZONE DEFAULT NULL;
            RAISE NOTICE 'Added column: collection_date';
        END IF;

        IF 'home_xg_first_half' = ANY(missing_columns) THEN
            ALTER TABLE match_features_training ADD COLUMN home_xg_first_half DOUBLE PRECISION DEFAULT NULL;
            RAISE NOTICE 'Added column: home_xg_first_half';
        END IF;

        IF 'away_xg_first_half' = ANY(missing_columns) THEN
            ALTER TABLE match_features_training ADD COLUMN away_xg_first_half DOUBLE PRECISION DEFAULT NULL;
            RAISE NOTICE 'Added column: away_xg_first_half';
        END IF;

        IF 'home_xg_second_half' = ANY(missing_columns) THEN
            ALTER TABLE match_features_training ADD COLUMN home_xg_second_half DOUBLE PRECISION DEFAULT NULL;
            RAISE NOTICE 'Added column: home_xg_second_half';
        END IF;

        IF 'away_xg_second_half' = ANY(missing_columns) THEN
            ALTER TABLE match_features_training ADD COLUMN away_xg_second_half DOUBLE PRECISION DEFAULT NULL;
            RAISE NOTICE 'Added column: away_xg_second_half';
        END IF;

        IF 'home_opening_odds' = ANY(missing_columns) THEN
            ALTER TABLE match_features_training ADD COLUMN home_opening_odds DOUBLE PRECISION DEFAULT NULL;
            RAISE NOTICE 'Added column: home_opening_odds';
        END IF;

        IF 'away_opening_odds' = ANY(missing_columns) THEN
            ALTER TABLE match_features_training ADD COLUMN away_opening_odds DOUBLE PRECISION DEFAULT NULL;
            RAISE NOTICE 'Added column: away_opening_odds';
        END IF;

        IF 'draw_opening_odds' = ANY(missing_columns) THEN
            ALTER TABLE match_features_training ADD COLUMN draw_opening_odds DOUBLE PRECISION DEFAULT NULL;
            RAISE NOTICE 'Added column: draw_opening_odds';
        END IF;
    END IF;
END $$;

-- 创建/更新索引以优化查询性能
DO $$
BEGIN
    -- 联赛索引
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_match_features_league') THEN
        CREATE INDEX idx_match_features_league ON match_features_training(league_id, league_name);
        RAISE NOTICE 'Created index: idx_match_features_league';
    END IF;

    -- 真实数据索引
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_match_features_real_data') THEN
        CREATE INDEX idx_match_features_real_data ON match_features_training(is_real_data);
        RAISE NOTICE 'Created index: idx_match_features_real_data';
    END IF;

    -- 数据源索引
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_match_features_data_source') THEN
        CREATE INDEX idx_match_features_data_source ON match_features_training(data_source);
        RAISE NOTICE 'Created index: idx_match_features_data_source';
    END IF;

    -- xG 相关索引（如果不存在）
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE indexname = 'idx_match_features_xg') THEN
        CREATE INDEX idx_match_features_xg ON match_features_training(home_xg, away_xg);
        RAISE NOTICE 'Created index: idx_match_features_xg';
    END IF;
END $$;

-- 更新表注释
COMMENT ON TABLE match_features_training IS 'V3.0 全球比赛特征存储表 - 支持106维特征向量';
COMMENT ON COLUMN match_features_training.league_id IS '联赛ID (FotMob API ID)';
COMMENT ON COLUMN match_features_training.league_name IS '联赛名称';
COMMENT ON COLUMN match_features_training.is_real_data IS '是否为真实比赛数据 (FALSE为测试数据)';
COMMENT ON COLUMN match_features_training.feature_version IS '特征向量版本';
COMMENT ON COLUMN match_features_training.data_source IS '数据来源标识';

-- 提交事务
COMMIT;

-- 验证升级结果
SELECT
    'Schema升级完成' as status,
    NOW() as upgrade_time,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name='match_features_training') as total_columns;