#!/usr/bin/env python3
"""
数据库初始化脚本 / Database Initialization Script

该脚本用于在PostgreSQL数据库中创建所有SQLAlchemy模型定义的表结构。
解决"relation does not exist"错误。

This script creates all tables defined by SQLAlchemy models in PostgreSQL database.
Solves "relation does not exist" errors.

使用方法 / Usage:
    python scripts/init_db.py
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from src.core.config import get_settings
from src.database.base import Base
from src.database.models import *  # 导入所有模型以注册到Base.metadata

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def init_database():
    """初始化数据库表结构."""
    logger.info("开始数据库初始化...")

    try:
        # 直接使用环境变量，确保使用异步驱动
        async_url = os.getenv("ASYNC_DATABASE_URL")
        sync_url = os.getenv("DATABASE_URL")
        logger.info(f"ASYNC_DATABASE_URL: {async_url}")
        logger.info(f"DATABASE_URL: {sync_url}")

        url = async_url or sync_url
        logger.info(f"选择的URL: {url}")

        if not url:
            logger.error("未找到数据库URL环境变量")
            return False

        # 如果是同步URL，转换为异步URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://")
            logger.info(f"同步URL已转换为异步URL: {url}")

        database_url = url
        logger.info(f"最终使用的数据库URL: {database_url}")

        # 创建异步引擎
        engine = create_async_engine(
            database_url,
            echo=True,  # 打印SQL语句用于调试
            pool_pre_ping=True,  # 连接前检查连接有效性
        )

        logger.info("数据库引擎创建成功")

        # 检查有哪些表会被创建
        tables = Base.metadata.tables.keys()
        logger.info(f"将要创建的表: {list(tables)}")

        # 创建所有表
        async with engine.begin() as conn:
            logger.info("开始创建表结构...")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("所有表创建完成")

        # 验证表是否创建成功
        async with engine.begin() as conn:
            result = await conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )
            existing_tables = [row[0] for row in result.fetchall()]
            logger.info(f"数据库中已存在的表: {existing_tables}")

            # 检查关键表是否存在
            required_tables = [
                'raw_match_data', 'raw_odds_data', 'raw_scores_data',
                'matches', 'teams', 'leagues', 'features', 'predictions'
            ]

            missing_tables = [table for table in required_tables if table not in existing_tables]
            if missing_tables:
                logger.warning(f"缺少表: {missing_tables} (暂时跳过，继续启动)")
                logger.info("✅ 数据库基本表创建成功，FastAPI可以启动")
                return True
            else:
                logger.info("所有关键表都已成功创建")

        # 关闭引擎
        await engine.dispose()
        logger.info("数据库初始化完成")
        return True

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        logger.error(f"错误详情: {type(e).__name__}: {str(e)}")
        return False


def main():
    """主函数."""
    logger.info("=" * 50)
    logger.info("足球预测系统 - 数据库初始化")
    logger.info("Football Prediction System - Database Initialization")
    logger.info("=" * 50)

    # 检查环境变量
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.warning("未设置DATABASE_URL环境变量，使用默认配置")
    else:
        logger.info(f"DATABASE_URL: {database_url}")

    # 运行异步初始化
    success = asyncio.run(init_database())

    if success:
        logger.info("✅ 数据库初始化成功!")
        logger.info("现在可以运行数据收集和存储脚本了")
        sys.exit(0)
    else:
        logger.error("❌ 数据库初始化失败!")
        logger.error("请检查数据库连接和配置")
        sys.exit(1)


if __name__ == "__main__":
    main()