#!/usr/bin/env python3
"""
快速球队插入测试 - 绕过所有可能的网络问题
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import text
from src.database.base import get_async_db
from src.database.models.team import Team


async def quick_team_test():
    """快速插入测试球队"""

    # 测试球队数据
    test_teams = [
        (100, "Test Team 100", "TT100"),
        (101, "Test Team 101", "TT101"),
        (102, "Test Team 102", "TT102"),
        (103, "Test Team 103", "TT103"),
        (104, "Test Team 104", "TT104"),
    ]

    print("🚀 开始快速球队插入测试...")

    async for db in get_async_db():
        try:
            # 只插入最基础的字段
            for team_id, name, short_name in test_teams:
                stmt = (
                    insert(Team)
                    .values(
                        id=team_id,
                        name=name,
                        short_name=short_name,
                        country="Test",  # 必填字段
                        # 跳过所有其他字段
                    )
                    .on_conflict_do_nothing(index_elements=["id"])
                )

                try:
                    result = await db.execute(stmt)
                    if result.rowcount > 0:
                        print(f"✅ 成功插入球队: {team_id} - {name}")
                    else:
                        print(f"ℹ️ 球队已存在: {team_id}")
                except Exception:
                    print(f"❌ 球队 {team_id} 插入失败: {e}")

            await db.commit()

            # 验证结果
            count_result = await db.execute(text("SELECT COUNT(*) FROM teams"))
            total_count = count_result.scalar()

            print(f"🎯 测试完成！球队总数: {total_count}")

        except Exception:
            print(f"❌ 数据库操作失败: {e}")
            await db.rollback()
        break


if __name__ == "__main__":
    asyncio.run(quick_team_test())
