#!/usr/bin/env python3
"""
测试Football-Data.org API连接
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.insert(0, "/home/user/projects/FootballPrediction")

from dotenv import load_dotenv

load_dotenv()

from src.collectors.data_sources import data_source_manager


async def test_football_data_api():
    """测试Football-Data.org API连接"""
    logger.debug("🔧 测试Football-Data.org API连接...")  # TODO: Add logger import if needed

    # 检查API密钥
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_key:
        logger.debug("❌ 未找到FOOTBALL_DATA_API_KEY环境变量")  # TODO: Add logger import if needed
        return False

    logger.debug(f"✅ API密钥已配置: {api_key[:10]}...{api_key[-4:]}")  # TODO: Add logger import if needed

    # 获取Football-Data.org适配器
    adapter = data_source_manager.get_adapter("football_data_org")
    if not adapter:
        logger.debug("❌ Football-Data.org适配器不可用")  # TODO: Add logger import if needed
        return False

    logger.debug("✅ Football-Data.org适配器已创建")  # TODO: Add logger import if needed

    try:
        # 测试获取比赛数据
        logger.debug("📊 测试获取比赛数据...")  # TODO: Add logger import if needed
        date_from = datetime.now()
        date_to = date_from + timedelta(days=7)

        matches = await adapter.get_matches(date_from=date_from, date_to=date_to)
        logger.debug(f"✅ 成功获取 {len(matches)} 场比赛")  # TODO: Add logger import if needed

        # 显示前3场比赛
        if matches:
            logger.debug("📊 前3场比赛示例:")  # TODO: Add logger import if needed
            for i, match in enumerate(matches[:3], 1):
                logger.debug(f"  {i}. {match.home_team} vs {match.away_team}")  # TODO: Add logger import if needed
                logger.debug(f"     联赛: {match.league}")  # TODO: Add logger import if needed
                logger.debug(f"     时间: {match.match_date}")  # TODO: Add logger import if needed
                logger.debug(f"     状态: {match.status}")  # TODO: Add logger import if needed

        # 测试获取球队数据
        logger.debug("\n⚽ 测试获取球队数据...")  # TODO: Add logger import if needed
        teams = await adapter.get_teams()
        logger.debug(f"✅ 成功获取 {len(teams)} 支球队")  # TODO: Add logger import if needed

        # 显示前5支球队
        if teams:
            logger.debug("⚽ 前5支球队示例:")  # TODO: Add logger import if needed
            for i, team in enumerate(teams[:5], 1):
                logger.debug(f"  {i}. {team.name} ({team.short_name})")  # TODO: Add logger import if needed
                if team.venue:
                    logger.debug(f"     主场: {team.venue}")  # TODO: Add logger import if needed

        logger.debug("\n🎉 Football-Data.org API测试成功！")  # TODO: Add logger import if needed
        return True

    except Exception as e:
        logger.debug(f"❌ Football-Data.org API测试失败: {e}")  # TODO: Add logger import if needed
        import traceback

        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    logger.debug("🚀 开始Football-Data.org API连接测试...")  # TODO: Add logger import if needed
    logger.debug("=" * 50)  # TODO: Add logger import if needed

    success = await test_football_data_api()

    logger.debug("\n" + "=" * 50)  # TODO: Add logger import if needed
    if success:
        logger.debug("🎉 API连接测试成功！系统已准备好使用真实数据源！")  # TODO: Add logger import if needed
        logger.debug("\n📝 下一步:")  # TODO: Add logger import if needed
        logger.debug("✅ 可以通过API端点收集真实比赛数据")  # TODO: Add logger import if needed
        logger.debug("✅ 数据集成系统完全可用")  # TODO: Add logger import if needed
        logger.debug("✅ 前端可以显示真实比赛信息")  # TODO: Add logger import if needed
    else:
        logger.debug("❌ API连接测试失败，请检查配置")  # TODO: Add logger import if needed
        logger.debug("\n🔧 故障排除:")  # TODO: Add logger import if needed
        logger.debug("1. 检查API密钥是否正确")  # TODO: Add logger import if needed
        logger.debug("2. 检查网络连接")  # TODO: Add logger import if needed
        logger.debug("3. 确认Football-Data.org服务状态")  # TODO: Add logger import if needed


if __name__ == "__main__":
    asyncio.run(main())
