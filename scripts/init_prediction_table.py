#!/usr/bin/env python3
"""
预测表初始化脚本
创建 match_predictions 表用于存储预测结果

功能:
1. 创建 match_predictions 表
2. 设置外键约束
3. 创建必要的索引
4. 插入测试数据(可选)

作者: Full Stack Automation Engineer
创建时间: 2025-01-10
版本: 1.0.0 - Phase 4 Daily Automation
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import logging

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.async_manager import get_db_session, initialize_database
from sqlalchemy import text, Index
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_predictions_table():
    """创建预测结果表"""

    # SQL创建表语句
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS match_predictions (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        match_id INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,

        -- 预测结果
        prediction VARCHAR(10) NOT NULL CHECK (prediction IN ('Home', 'Draw', 'Away')),
        confidence DECIMAL(5,4) NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
        probabilities JSONB NOT NULL,  -- {"Home": 0.55, "Draw": 0.25, "Away": 0.20}

        -- 模型信息
        model_version VARCHAR(50) NOT NULL DEFAULT 'v1.0.0',
        feature_count INTEGER NOT NULL DEFAULT 0,
        missing_features INTEGER NOT NULL DEFAULT 0,

        -- 元数据
        processing_time_ms DECIMAL(10,3),  -- 处理时间(毫秒)
        prediction_source VARCHAR(50) NOT NULL DEFAULT 'daily_automation',  -- 预测来源

        -- 时间戳
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """

    # 创建索引
    create_indexes_sql = [
        # 匹配ID索引 (用于查找特定比赛的预测)
        "CREATE INDEX IF NOT EXISTS idx_match_predictions_match_id ON match_predictions(match_id);",

        # 创建时间索引 (用于按时间范围查询)
        "CREATE INDEX IF NOT EXISTS idx_match_predictions_created_at ON match_predictions(created_at);",

        # 模型版本索引 (用于按模型版本查询)
        "CREATE INDEX IF NOT EXISTS idx_match_predictions_model_version ON match_predictions(model_version);",

        # 预测结果索引 (用于统计分析)
        "CREATE INDEX IF NOT EXISTS idx_match_predictions_prediction ON match_predictions(prediction);",

        # 复合索引: 比赛时间 + 创建时间 (用于查找特定日期的预测)
        """CREATE INDEX IF NOT EXISTS idx_match_predictions_match_created
           ON match_predictions(match_id, created_at DESC);""",

        # 置信度索引 (用于查找高置信度预测)
        "CREATE INDEX IF NOT EXISTS idx_match_predictions_confidence ON match_predictions(confidence DESC);",
    ]

    # 触发器: 自动更新 updated_at 字段 (拆分为单独语句)
    create_trigger_sqls = [
        """
        CREATE OR REPLACE FUNCTION update_match_predictions_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
        """,
        """
        DROP TRIGGER IF EXISTS trigger_update_match_predictions_updated_at ON match_predictions;
        """,
        """
        CREATE TRIGGER trigger_update_match_predictions_updated_at
            BEFORE UPDATE ON match_predictions
            FOR EACH ROW
            EXECUTE FUNCTION update_match_predictions_updated_at();
        """
    ]

    try:
        async with get_db_session() as session:
            # 1. 创建表
            logger.info("🔨 创建 match_predictions 表...")
            await session.execute(text(create_table_sql))

            # 2. 创建索引
            logger.info("📊 创建索引...")
            for index_sql in create_indexes_sql:
                await session.execute(text(index_sql))

            # 3. 创建触发器
            logger.info("⚡ 创建更新时间触发器...")
            for trigger_sql in create_trigger_sqls:
                await session.execute(text(trigger_sql))

            # 4. 提交所有更改
            await session.commit()

            logger.info("✅ match_predictions 表创建成功!")

            # 5. 验证表结构
            await verify_table_structure(session)

            return True

    except Exception as e:
        logger.error(f"❌ 创建表失败: {e}")
        await session.rollback()
        return False


async def verify_table_structure(session):
    """验证表结构"""
    logger.info("🔍 验证表结构...")

    # 检查表是否存在
    check_table_sql = """
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_name = 'match_predictions'
    );
    """

    result = await session.execute(text(check_table_sql))
    table_exists = result.scalar()

    if not table_exists:
        raise Exception("表创建失败")

    # 检查列信息
    columns_sql = """
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name = 'match_predictions'
    ORDER BY ordinal_position;
    """

    result = await session.execute(text(columns_sql))
    columns = result.fetchall()

    logger.info("📋 表结构:")
    for col in columns:
        logger.info(f"   {col.column_name}: {col.data_type} "
                   f"(nullable: {col.is_nullable}, default: {col.column_default})")

    # 检查索引
    indexes_sql = """
    SELECT indexname, indexdef
    FROM pg_indexes
    WHERE tablename = 'match_predictions'
    ORDER BY indexname;
    """

    result = await session.execute(text(indexes_sql))
    indexes = result.fetchall()

    logger.info("📊 索引信息:")
    for idx in indexes:
        logger.info(f"   {idx.indexname}")

    # 检查外键约束
    constraints_sql = """
    SELECT constraint_name, constraint_type
    FROM information_schema.table_constraints
    WHERE table_name = 'match_predictions';
    """

    result = await session.execute(text(constraints_sql))
    constraints = result.fetchall()

    logger.info("🔗 约束信息:")
    for cons in constraints:
        logger.info(f"   {cons.constraint_name}: {cons.constraint_type}")


async def insert_sample_predictions():
    """插入示例预测数据 (可选)"""
    logger.info("🎯 插入示例预测数据...")

    # 首先检查是否有已完成的比赛
    find_matches_sql = """
    SELECT id, home_team_name, away_team_name, match_date
    FROM matches
    WHERE status = 'completed'
    AND home_score IS NOT NULL
    AND away_score IS NOT NULL
    LIMIT 5;
    """

    try:
        async with get_db_session() as session:
            result = await session.execute(text(find_matches_sql))
            matches = result.fetchall()

            if not matches:
                logger.info("⚠️ 没有找到已完成的比赛，跳过示例数据插入")
                return

            for match in matches:
                # 模拟预测结果
                sample_prediction = {
                    'match_id': str(match.id),
                    'prediction': 'Home',  # 假设主队获胜
                    'confidence': 0.65,
                    'probabilities': {"Home": 0.65, "Draw": 0.25, "Away": 0.10},
                    'model_version': 'v1.0.0',
                    'feature_count': 14,
                    'missing_features': 0,
                    'processing_time_ms': 150.5,
                    'prediction_source': 'sample_data'
                }

                insert_sql = """
                INSERT INTO match_predictions (
                    match_id, prediction, confidence, probabilities,
                    model_version, feature_count, missing_features,
                    processing_time_ms, prediction_source
                ) VALUES (
                    :match_id, :prediction, :confidence, :probabilities,
                    :model_version, :feature_count, :missing_features,
                    :processing_time_ms, :prediction_source
                );
                """

                await session.execute(text(insert_sql), sample_prediction)

            await session.commit()
            logger.info(f"✅ 成功插入 {len(matches)} 条示例预测数据")

    except Exception as e:
        logger.error(f"❌ 插入示例数据失败: {e}")
        await session.rollback()


async def main():
    """主函数"""
    logger.info("🚀 开始初始化预测表...")

    try:
        # 0. 初始化数据库管理器
        logger.info("🔧 初始化数据库管理器...")
        initialize_database()

        # 1. 创建表和索引
        success = await create_predictions_table()

        if not success:
            logger.error("❌ 预测表初始化失败")
            return False

        # 2. 可选: 插入示例数据
        # insert_sample_predictions()

        logger.info("🎉 预测表初始化完成!")
        return True

    except Exception as e:
        logger.error(f"❌ 初始化过程发生异常: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)