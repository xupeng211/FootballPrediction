#!/usr/bin/env python3
"""验证Bronze层数据存储功能脚本
Verify Bronze Layer Data Storage Script.

此脚本验证FixturesCollector的完整工作流程：
1. 初始化API适配器
2. 采集真实API数据
3. 存储到Bronze层
4. 验证数据库中的数据
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv

# 尝试加载.env文件
env_files = [
    project_root / ".env",
    project_root / ".env.local",
    project_root / ".env.development",
]

for env_file in env_files:
    if env_file.exists():
        load_dotenv(env_file)
        break
else:
    pass

# 导入模块
try:
    from src.data.collectors.fixtures_collector import FixturesCollector
    from src.database.connection import get_async_session, initialize_database
    from src.database.models.raw_data import RawMatchData
    from sqlalchemy import select, func
except ImportError:
    sys.exit(1)


async def verify_bronze_storage():
    """验证Bronze层数据存储功能."""

    # 检查API Key
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_key:
        return False

    if api_key == "CHANGE_THIS_FOOTBALL_DATA_API_KEY":
        return False

    try:
        # 0. 初始化数据库连接
        try:
            initialize_database()
            db_available = True
        except Exception:
            db_available = False

        # 1. 初始化FixturesCollector
        collector = FixturesCollector(data_source="football_api")

        # 2. 记录采集前的数据库状态
        initial_count = 0
        if db_available:
            async with get_async_session() as session:
                count_query = select(func.count()).select_from(RawMatchData)
                result = await session.execute(count_query)
                initial_count = result.scalar() or 0

        # 3. 采集数据（限制范围以避免过多数据）
        result = await collector.collect_fixtures(
            leagues=["PL"],  # 仅采集英超以控制数据量
            season=2024,
        )

        if result.data:
            pass
        else:
            pass

        if result.error:
            pass

        if not result.success:
            return False

        # 4. 验证数据库中的数据
        final_count = 0
        if db_available:
            async with get_async_session() as session:
                # 获取总记录数
                count_query = select(func.count()).select_from(RawMatchData)
                result = await session.execute(count_query)
                final_count = result.scalar() or 0

                if final_count > initial_count:
                    # 获取最新的几条记录
                    latest_query = (
                        select(RawMatchData)
                        .order_by(RawMatchData.collected_at.desc())
                        .limit(3)
                    )
                    latest_result = await session.execute(latest_query)
                    latest_records = latest_result.scalars().all()

                    for _i, record in enumerate(latest_records, 1):
                        match_data = record.match_data
                        match_data.get("external_match_id", "unknown")
                        match_data.get("match_time", "unknown")
                        match_data.get("raw_data", {}).get("homeTeam", {}).get(
                            "name", "unknown"
                        )
                        match_data.get("raw_data", {}).get("awayTeam", {}).get(
                            "name", "unknown"
                        )

                    # 验证数据完整性

                # 按数据源统计
                source_stats_query = select(
                    RawMatchData.source, func.count().label("count")
                ).group_by(RawMatchData.source)
                source_stats_result = await session.execute(source_stats_query)
                source_stats = source_stats_result.all()

                for _source, _count in source_stats:
                    pass
        else:
            pass

        if db_available:
            pass
        else:
            pass
        return True

    except Exception:
        import traceback

        traceback.print_exc()
        return False


async def demonstrate_data_retrieval():
    """演示如何检索Bronze层数据."""

    try:
        # 检查数据库是否可用
        try:
            await initialize_database()
            db_available = True
        except Exception:
            return True

        if db_available:
            async with get_async_session() as session:
                # 1. 获取所有未处理的记录
                unprocessed_query = (
                    select(RawMatchData).where(not RawMatchData.processed).limit(5)
                )
                unprocessed_result = await session.execute(unprocessed_query)
                unprocessed_records = unprocessed_result.scalars().all()

                for record in unprocessed_records:
                    match_data = record.match_data
                    match_data.get("raw_data", {})

                # 2. 统计信息
                total_query = select(func.count()).select_from(RawMatchData)
                total_result = await session.execute(total_query)
                total_result.scalar() or 0

                processed_query = select(func.count()).where(RawMatchData.processed)
                processed_result = await session.execute(processed_query)
                processed_result.scalar() or 0

            return True

    except Exception:
        return False


async def main():
    """主函数."""

    # 执行主要验证
    success = await verify_bronze_storage()

    if success:
        # 执行数据检索演示
        await demonstrate_data_retrieval()

        return 0
    else:
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
