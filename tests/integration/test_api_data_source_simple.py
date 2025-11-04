#!/usr/bin/env python3
"""
简单的数据源API测试脚本（不依赖数据库）
"""

import asyncio
import sys

from dotenv import load_dotenv

load_dotenv()

# 添加项目根目录到Python路径
sys.path.insert(0, "/home/user/projects/FootballPrediction")

from src.collectors.data_sources import data_source_manager


async def test_data_source_api():
    """测试数据源API功能"""
    logger.debug("🔧 测试数据源API功能...")  # TODO: Add logger import if needed

    try:
        # 检查可用数据源
        available_sources = data_source_manager.get_available_sources()
        logger.debug(f"✅ 可用数据源: {available_sources}")  # TODO: Add logger import if needed

        # 测试Football-Data.org适配器
        logger.debug("\n📊 测试Football-Data.org适配器...")  # TODO: Add logger import if needed
        adapter = data_source_manager.get_adapter("football_data_org")
        if not adapter:
            logger.debug("❌ Football-Data.org适配器不可用")  # TODO: Add logger import if needed
            return False

        logger.debug("✅ Football-Data.org适配器可用")  # TODO: Add logger import if needed

        # 测试获取比赛数据
        from datetime import datetime, timedelta

        date_from = datetime.now()
        date_to = date_from + timedelta(days=7)

        matches = await adapter.get_matches(date_from=date_from, date_to=date_to)
        logger.debug(f"✅ 成功获取 {len(matches)} 场比赛")  # TODO: Add logger import if needed

        # 测试获取球队数据
        teams = await adapter.get_teams()
        logger.debug(f"✅ 成功获取 {len(teams)} 支球队")  # TODO: Add logger import if needed

        # 构造API响应格式
        response = {
            "success": True,
            "data_source": "football_data_org",
            "test_matches": len(matches),
            "test_teams": len(teams),
            "message": "数据源 football_data_org 测试成功",
            "available_sources": available_sources,
            "timestamp": datetime.now().isoformat(),
        }

        logger.debug("\n🎉 数据源测试成功！")  # TODO: Add logger import if needed
        logger.debug("📋 测试结果:")  # TODO: Add logger import if needed
        logger.debug(f"   数据源: {response['data_source']}")  # TODO: Add logger import if needed
        logger.debug(f"   测试比赛数: {response['test_matches']}")  # TODO: Add logger import if needed
        logger.debug(f"   测试球队数: {response['test_teams']}")  # TODO: Add logger import if needed
        logger.debug(f"   可用数据源: {response['available_sources']}")  # TODO: Add logger import if needed

        # 显示前3场比赛示例
        if matches:
            logger.debug("\n📊 前3场比赛示例:")  # TODO: Add logger import if needed
            for i, match in enumerate(matches[:3], 1):
                logger.debug(f"  {i}. {match.home_team} vs {match.away_team}")  # TODO: Add logger import if needed
                logger.debug(f"     联赛: {match.league}")  # TODO: Add logger import if needed
                logger.debug(f"     时间: {match.match_date}")  # TODO: Add logger import if needed
                logger.debug(f"     状态: {match.status}")  # TODO: Add logger import if needed

        return True

    except Exception as e:
        logger.debug(f"❌ 数据源测试失败: {e}")  # TODO: Add logger import if needed
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_data_source_api())
    if success:
        logger.debug("\n✅ 数据源API功能验证成功！")  # TODO: Add logger import if needed
        logger.debug("📝 状态:")  # TODO: Add logger import if needed
        logger.debug("   ✅ Football-Data.org API连接正常")  # TODO: Add logger import if needed
        logger.debug("   ✅ 可以获取真实比赛数据")  # TODO: Add logger import if needed
        logger.debug("   ✅ 数据适配器工作正常")  # TODO: Add logger import if needed
        logger.debug("\n🚀 准备集成到完整API端点！")  # TODO: Add logger import if needed
    else:
        logger.debug("\n❌ 数据源API功能验证失败！")  # TODO: Add logger import if needed
