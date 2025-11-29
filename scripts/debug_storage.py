#!/usr/bin/env python3
"""
入库调试脚本 - 诊断为什么比赛数据没有保存到数据库
Database Reliability Engineer 紧急诊断工具
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

async def main():
    print("🔍 开始入库诊断...")
    print("=" * 50)

    try:
        # 导入必要的模块
        from src.database.dependencies import get_async_db
        from src.database.models.match import Match
        from src.domain.models.data import MatchData
        from src.database.repositories.match_repository import MatchRepository
        from src.core.config import get_settings

        print("✅ 1. 模块导入成功")

        # 获取数据库连接
        settings = get_settings()
        db_generator = get_async_db()
        db = await db_generator.__anext__()

        print("✅ 2. 数据库连接成功")

        # 创建仓库
        match_repo = MatchRepository(db)

        print("✅ 3. MatchRepository 创建成功")

        # 构造测试数据
        test_match = MatchData(
            external_id="debug-test-123",
            home_team_id=1,
            away_team_id=2,
            home_score=2,
            away_score=1,
            match_date=datetime(2022, 1, 1, 15, 0),
            status="FINISHED",
            competition_id=39,
            season="2022",
            round_number=None
        )

        print(f"✅ 4. 测试数据构造成功: {test_match.external_id}")

        # 尝试保存
        print("\n🚨 开始保存测试...")
        try:
            saved_match = await match_repo.save_match(test_match)
            print(f"✅ 5. 保存成功! 保存的ID: {saved_match.id}")

            # 立即查询验证
            print("\n🔍 验证保存结果...")
            from sqlalchemy import select
            stmt = select(Match).where(Match.external_id == "debug-test-123")
            result = await db.execute(stmt)
            found_match = result.scalar_one_or_none()

            if found_match:
                print(f"✅ 6. 验证成功! 数据库中的记录: ID={found_match.id}, external_id={found_match.external_id}")
            else:
                print("❌ 6. 验证失败! 保存后查询不到记录")

        except Exception as save_error:
            print(f"❌ 5. 保存失败! 错误: {type(save_error).__name__}: {save_error}")
            import traceback
            print("详细错误信息:")
            traceback.print_exc()

            # 检查是否有事务问题
            print("\n🔍 检查事务状态...")
            print(f"事务是否活跃: {db.is_active}")

    except Exception as import_error:
        print(f"❌ 导入/初始化失败: {type(import_error).__name__}: {import_error}")
        import traceback
        print("详细错误信息:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())