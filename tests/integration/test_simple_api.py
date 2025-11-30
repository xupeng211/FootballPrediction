from typing import Optional

#!/usr/bin/env python3
"""

简单的Football-Data.org API测试
"""

import pytest

import asyncio
import logging
import os

import aiohttp
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()


@pytest.mark.asyncio
async def test_basic_api():
    """测试基本的API连接"""
    api_key = os.getenv("FOOTBALL_DATA_API_KEY")
    if not api_key:
        logger.debug("❌ 未找到API密钥")
        return

    headers = {"X-Auth-Token": api_key}
    base_url = "https://api.football-data.org/v4"

    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            # 测试1: 获取可用的比赛列表
            logger.debug("🔧 测试获取比赛列表...")
            url = f"{base_url}/matches"

            params = {"limit": 10}

            async with session.get(url, params=params) as response:
                logger.debug(f"状态码: {response.status}")

                if response.status == 200:
                    data = await response.json()
                    matches = data.get("matches", [])
                    logger.debug(f"✅ 获取到 {len(matches)} 场比赛")

                    # 显示前3场比赛
                    for i, match in enumerate(matches[:3], 1):
                        home_team = match.get("homeTeam", {}).get("name", "Unknown")
                        away_team = match.get("awayTeam", {}).get("name", "Unknown")
                        competition = match.get("competition", {}).get(
                            "name", "Unknown"
                        )
                        utc_date = match.get("utcDate", "Unknown")

                        logger.debug(f"  {i}. {home_team} vs {away_team}")
                        logger.debug(f"     联赛: {competition}")
                        logger.debug(f"     时间: {utc_date}")
                        logger.debug()

                else:
                    error_text = await response.text()
                    logger.debug(f"❌ API请求失败: {response.status}")
                    logger.error(f"错误详情: {error_text}")

            # 测试2: 获取可用比赛
            logger.debug("\n🏆 测试获取可用比赛...")
            url = f"{base_url}/competitions"

            async with session.get(url) as response:
                logger.debug(f"状态码: {response.status}")

                if response.status == 200:
                    data = await response.json()
                    competitions = data.get("competitions", [])
                    logger.debug(f"✅ 获取到 {len(competitions)} 个比赛")

                    # 显示前5个比赛
                    for i, comp in enumerate(competitions[:5], 1):
                        name = comp.get("name", "Unknown")
                        code = comp.get("code", "Unknown")
                        area = comp.get("area", {}).get("name", "Unknown")

                        logger.debug(f"  {i}. {name} ({code}) - {area}")

                else:
                    error_text = await response.text()
                    logger.debug(f"❌ API请求失败: {response.status}")
                    logger.error(f"错误详情: {error_text}")

        except Exception:
            logger.debug(f"❌ 测试失败: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_basic_api())
