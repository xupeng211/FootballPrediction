#!/usr/bin/env python3
"""
直接检查数据库中的赔率数据
"""

import asyncio
import sys
from pathlib import Path
import pandas as pd

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.async_manager import AsyncDatabaseManager
from sqlalchemy import text


async def check_database_odds():
    """检查数据库中的赔率数据"""
    print("🔍 直接检查数据库中的赔率数据")

    db_manager = AsyncDatabaseManager()

    # 手动创建数据库连接
    import os
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/football_prediction")
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            # 检查matches表结构 (所有列)
            print("\n📋 检查matches表结构:")
            query = """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'matches'
                ORDER BY column_name
            """
            result = await session.execute(text(query))
            all_columns = result.fetchall()

            # 查找所有列
            print("   所有列:")
            for col in all_columns:
                print(f"      {col.column_name}: {col.data_type}")

            # 查找赔率相关列
            odds_columns = [col for col in all_columns if 'odds' in col.column_name.lower()]

            if odds_columns:
                print("   发现赔率相关列:")
                for col in odds_columns:
                    print(f"      {col.column_name}: {col.data_type}")
            else:
                print("   ❌ 数据库中未发现赔率相关列")

            # 检查是否有任何非空的赔率数据
            print(f"\n📊 检查赔率数据覆盖率:")
            for col in odds_columns:
                if col.data_type == 'json':
                    query = f"""
                        SELECT COUNT(*) as total_count,
                               COUNT({col.column_name}) as non_null_count
                        FROM matches
                        WHERE {col.column_name} IS NOT NULL
                        AND {col.column_name}::text != 'null'
                        AND {col.column_name}::text != '{{}}'
                    """
                else:
                    query = f"""
                        SELECT COUNT(*) as total_count,
                               COUNT({col.column_name}) as non_null_count
                        FROM matches
                        WHERE {col.column_name} IS NOT NULL
                    """
                result = await session.execute(text(query))
                stats = result.fetchone()

                if stats and stats.non_null_count > 0:
                    print(f"   {col.column_name}: {stats.non_null_count} 非空记录")
                else:
                    print(f"   {col.column_name}: 无有效数据")

            # 检查样本数据 (包括JSON赔率)
            print(f"\n📋 检查样本数据 (前3条记录):")
            sample_query = """
                SELECT id, match_date, home_score, away_score,
                       odds, odds_snapshot_json
                FROM matches
                WHERE home_score IS NOT NULL
                ORDER BY match_date
                LIMIT 3
            """
            result = await session.execute(text(sample_query))
            samples = result.fetchall()

            if samples:
                print("   样本记录:")
                for sample in samples:
                    print(f"      ID: {sample.id}, 日期: {sample.match_date}")
                    print(f"      比分: {sample.home_score}-{sample.away_score}")
                    if sample.odds:
                        print(f"      赔率(JSON): {sample.odds}")
                    if sample.odds_snapshot_json:
                        print(f"      赔率快照: {sample.odds_snapshot_json}")
                    print()

    except Exception as e:
        print(f"❌ 数据库查询失败: {e}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_database_odds())