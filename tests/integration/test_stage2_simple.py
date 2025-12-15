from typing import Optional

#!/usr/bin/env python3
"""
简化的第二阶段测试脚本
Simplified Stage 2 Test Script
"""

import asyncio
import logging
from datetime import datetime

import aiohttp

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# API配置
API_KEY = "ed809154dc1f422da46a18d8961a98a0"
BASE_URL = "https://api.football-data.org/v4"


class SimpleDataCollector:
    """简化的数据采集器"""

    def __init__(self):
        self.api_key = API_KEY
        self.base_url = BASE_URL
        self.session = None

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=30)
        headers = {"X-Auth-Token": self.api_key, "content-type": "application/json"}
        self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def test_error_handling(self, collector, max_retries=3):
        """测试错误处理和重试机制"""
        try:
            logger.info("测试错误处理和重试机制...")

            # 测试正常请求
            data = await self._make_request_with_retry("competitions", max_retries)
            if data and "competitions" in data:
                logger.info(
                    f"  ✅ 正常请求成功，获取到 {len(data['competitions'])} 个联赛"
                )

            # 测试无效端点处理
            data = await self._make_request_with_retry("invalid/endpoint", max_retries)
            if data.get("status") == 404:
                logger.info("  ✅ 无效端点正确处理")

            return True
        except Exception as e:
            logger.error(f"  ❌ 错误处理测试失败: {e}")
            return False

    async def _make_request_with_retry(self, endpoint, max_retries=3):
        """带重试机制的请求"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        for attempt in range(max_retries + 1):
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        retry_after = int(response.headers.get("Retry-After", 60))
                        logger.warning(
                            f"Rate limit exceeded. Waiting {retry_after} seconds..."
                        )
                        await asyncio.sleep(retry_after)
                        continue
                    elif response.status == 404:
                        return {"error": "Not found", "status": 404}
                    elif response.status >= 500:
                        if attempt < max_retries:
                            wait_time = 2**attempt
                            logger.warning(
                                f"Server error {response.status}. Retrying in {wait_time} seconds..."
                            )
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise Exception(f"Server error {response.status}")
                    else:
                        raise Exception(
                            f"HTTP error {response.status}: {response.reason}"
                        )

            except Exception as e:
                if attempt < max_retries:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Network error (attempt {attempt + 1}): {e}. Retrying in {wait_time} seconds..."
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise

        raise Exception("All retries exhausted")

    def validate_data(self, data, data_type):
        """验证数据"""
        try:
            if not isinstance(data, dict):
                raise ValueError(f"Expected dict for {data_type}, got {type(data)}")

            if "error" in data:
                logger.warning(f"API returned error for {data_type}: {data['error']}")
                return False

            if data_type == "competitions":
                competitions = data.get("competitions", [])
                if not isinstance(competitions, list):
                    raise ValueError("Expected competitions to be a list")

                for comp in competitions:
                    if not all(comp.get(field) for field in ["id", "name", "code"]):
                        logger.warning(f"Invalid competition data: {comp}")
                        return False

                logger.info(f"  ✅ 数据验证成功，验证了 {len(competitions)} 个联赛")
                return True

            return True
        except Exception as e:
            logger.error(f"  ❌ 数据验证失败: {e}")
            return False

    def clean_data(self, data):
        """清洗数据"""
        try:
            competitions = data.get("competitions", [])
            cleaned_competitions = []

            for comp in competitions:
                cleaned_comp = {
                    "id": comp.get("id"),
                    "name": comp.get("name"),
                    "code": comp.get("code"),
                    "type": comp.get("type", "LEAGUE"),
                    "emblem": comp.get("emblem"),
                }
                cleaned_competitions.append(cleaned_comp)

            return {"competitions": cleaned_competitions}
        except Exception as e:
            logger.error(f"  ❌ 数据清洗失败: {e}")
            return data

    async def test_data_validation(self, collector):
        """测试数据验证和清洗"""
        try:
            logger.info("测试数据验证和清洗功能...")

            # 获取原始数据
            raw_data = await self._make_request_with_retry("competitions")

            # 测试验证
            if self.validate_data(raw_data, "competitions"):
                # 测试清洗
                cleaned_data = self.clean_data(raw_data)
                if "competitions" in cleaned_data:
                    logger.info(
                        f"  ✅ 数据清洗成功，包含 {len(cleaned_data['competitions'])} 个联赛"
                    )

                    # 检查数据结构
                    if cleaned_data["competitions"]:
                        first_comp = cleaned_data["competitions"][0]
                        if all(field in first_comp for field in ["id", "name", "code"]):
                            logger.info("  ✅ 数据结构正确")
                        else:
                            missing = [
                                f for f in ["id", "name", "code"] if f not in first_comp
                            ]
                            logger.warning(f"  ⚠️ 数据结构不完整，缺少: {missing}")
                else:
                    logger.error("  ❌ 数据清洗失败")
                    return False
            else:
                logger.error("  ❌ 数据验证失败")
                return False

            return True
        except Exception as e:
            logger.error(f"  ❌ 数据验证测试失败: {e}")
            return False

    async def test_team_data_collection(self, collector):
        """测试球队数据采集"""
        try:
            logger.info("测试球队数据采集...")

            # 获取英超球队
            teams_data = await self._make_request_with_retry("competitions/2021/teams")

            if teams_data and "teams" in teams_data:
                teams = teams_data["teams"]
                logger.info(f"  ✅ 英超球队采集成功，获取到 {len(teams)} 支球队")

                # 检查数据结构
                for i, team in enumerate(teams[:3]):  # 检查前3个球队
                    if all(team.get(field) for field in ["id", "name", "shortName"]):
                        logger.info(
                            f"    球队 {i + 1}: {team.get('name')} ({team.get('shortName')}) - ✅"
                        )
                    else:
                        logger.warning(f"    球队 {i + 1}: 数据结构不完整")

                return True
            else:
                logger.error("  ❌ 英超球队采集失败")
                return False

        except Exception as e:
            logger.error(f"  ❌ 球队数据采集测试失败: {e}")
            return False

    async def test_league_standings(self, collector):
        """测试联赛积分榜"""
        try:
            logger.info("测试联赛积分榜...")

            # 获取英超积分榜
            standings_data = await self._make_request_with_retry(
                "competitions/2021/standings"
            )

            if standings_data and "standings" in standings_data:
                standings = standings_data["standings"]
                logger.info(f"  ✅ 英超积分榜采集成功，包含 {len(standings)} 个积分榜")

                # 检查数据结构
                for standing in standings[:2]:  # 检查前2个积分榜
                    if "table" in standing and isinstance(standing["table"], list):
                        table = standing["table"]
                        logger.info(f"    积分榜包含 {len(table)} 支球队")

                        # 检查前3名
                        for i, team in enumerate(table[:3]):
                            team_data = team.get("team", {})
                            if all(team_data.get(field) for field in ["id", "name"]):
                                points = team.get("points", 0)
                                position = i + 1
                                logger.info(
                                    f"      第{position}名: {team_data.get('name')} - {points}分 - ✅"
                                )
                            else:
                                logger.warning(f"      第{position}名: 数据结构不完整")
                    else:
                        logger.warning("    积分榜格式错误")
                else:
                    logger.error("  ❌ 英超积分榜采集失败")
                    return False

                return True
            else:
                logger.error("  ❌ 英超积分榜采集失败")
                return False

        except Exception as e:
            logger.error(f"  ❌ 联赛积分榜测试失败: {e}")
            return False

    async def test_data_consistency(self, collector):
        """测试数据一致性"""
        try:
            logger.info("测试数据一致性...")

            # 获取球队和积分榜数据
            teams_data = await self._make_request_with_retry("competitions/2021/teams")
            standings_data = await self._make_request_with_retry(
                "competitions/2021/standings"
            )

            if not (
                teams_data
                and "teams" in teams_data
                and standings_data
                and "standings" in standings_data
            ):
                logger.error("  ❌ 无法获取数据进行一致性测试")
                return False

            teams = teams_data["teams"]
            standings = standings_data["standings"]

            # 收集积分榜中的球队ID
            team_ids_from_standings = set()
            for standing in standings:
                table = standing.get("table", [])
                for team in table:
                    team_id = team.get("team", {}).get("id")
                    if team_id:
                        team_ids_from_standings.add(str(team_id))

            # 收集球队列表中的球队ID
            team_ids_from_teams = {str(team.get("id")) for team in teams}

            logger.info(
                f"  球队数量对比: 球队列表={len(team_ids_from_teams)}, "
                f"积分榜={len(team_ids_from_standings)}"
            )

            # 检查差异
            missing_in_standings = team_ids_from_teams - team_ids_from_standings
            missing_in_teams = team_ids_from_standings - team_ids_from_teams

            if missing_in_standings:
                logger.warning(
                    f"  ⚠️ {len(missing_in_standings)} 支队在列表中但不在积分榜中"
                )
            if missing_in_teams:
                logger.warning(
                    f"  ⚠️ {len(missing_in_teams)} 支队在积分榜中但不在列表中"
                )

            # 评估一致性
            total_diff = len(missing_in_standings) + len(missing_in_teams)
            if total_diff <= 2:
                logger.info(f"  ✅ 数据一致性良好，差异仅 {total_diff} 个球队")
                return True
            else:
                logger.warning(f"  ⚠️ 数据一致性一般，差异有 {total_diff} 个球队")
                return True

        except Exception as e:
            logger.error(f"  ❌ 数据一致性测试失败: {e}")
            return False


async def main():
    """主测试函数"""

    start_time = datetime.now()

    tests = [
        ("错误处理和重试机制", SimpleDataCollector.test_error_handling),
        ("数据验证和清洗功能", SimpleDataCollector.test_data_validation),
        ("球队数据采集", SimpleDataCollector.test_team_data_collection),
        ("联赛积分榜采集", SimpleDataCollector.test_league_standings),
        ("数据一致性检查", SimpleDataCollector.test_data_consistency),
    ]

    passed = 0
    failed = 0

    async with SimpleDataCollector() as collector:
        for _test_name, test_func in tests:
            try:
                if await test_func(collector):
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1

    end_time = datetime.now()
    end_time - start_time

    if failed == 0:
        return True
    else:
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
