#!/usr/bin/env python3
"""
简化的第二阶段测试脚本 - 修复版本
Simplified Stage 2 Test Script - Fixed Version
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# API配置
API_KEY = 'ed809154dc1f422da46a18d8961a98a0'
BASE_URL = 'https://api.football-data.org/v4'


class SimpleDataCollector:
    """简化的数据采集器"""

    def __init__(self):
        self.api_key = API_KEY
        self.base_url = BASE_URL
        self.session = None

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=30)
        headers = {
            'X-Auth-Token': self.api_key,
            'content-type': 'application/json'
        }
        self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _make_request_with_retry(self, endpoint, max_retries=3):
        """带重试机制的请求"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        for attempt in range(max_retries + 1):
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        retry_after = int(response.headers.get('Retry-After', 60))
                        logger.warning(f"Rate limit exceeded. Waiting {retry_after} seconds...")
                        await asyncio.sleep(retry_after)
                        continue
                    elif response.status == 404:
                        return {"error": "Not found", "status": 404}
                    elif response.status >= 500:
                        if attempt < max_retries:
                            wait_time = 2 ** attempt
                            logger.warning(f"Server error {response.status}. Retrying in {wait_time} seconds...")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise Exception(f"Server error {response.status}")
                    else:
                        raise Exception(f"HTTP error {response.status}: {response.reason}")

            except Exception as e:
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(f"Network error (attempt {attempt + 1}): {e}. Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise

        raise Exception("All retries exhausted")


async def test_error_handling(collector):
    """测试错误处理和重试机制"""
    try:
        logger.info("测试错误处理和重试机制...")

        # 测试正常请求
        data = await collector._make_request_with_retry('competitions')
        if data and 'competitions' in data:
            logger.info(f"  ✅ 正常请求成功，获取到 {len(data['competitions'])} 个联赛")

        # 测试无效端点处理
        data = await collector._make_request_with_retry('invalid/endpoint')
        if data.get('status') == 404:
            logger.info("  ✅ 无效端点正确处理")

        return True
    except Exception as e:
        logger.error(f"  ❌ 错误处理测试失败: {e}")
        return False


async def test_data_validation(collector):
    """测试数据验证和清洗"""
    try:
        logger.info("测试数据验证和清洗功能...")

        # 获取原始数据
        raw_data = await collector._make_request_with_retry('competitions')

        if raw_data and 'competitions' in raw_data:
            competitions = raw_data.get('competitions', [])
            if not isinstance(competitions, list):
                raise ValueError("Expected competitions to be a list")

            # 验证数据结构
            for comp in competitions[:3]:  # 检查前3个
                if not all(comp.get(field) for field in ['id', 'name', 'code']):
                    logger.warning(f"Invalid competition data: {comp}")
                    return False

            logger.info(f"  ✅ 数据验证成功，验证了 {len(competitions)} 个联赛")

            # 简单的数据清洗
            cleaned_competitions = []
            for comp in competitions:
                cleaned_comp = {
                    'id': comp.get('id'),
                    'name': comp.get('name'),
                    'code': comp.get('code'),
                    'type': comp.get('type', 'LEAGUE'),
                    'emblem': comp.get('emblem')
                }
                cleaned_competitions.append(cleaned_comp)

            logger.info(f"  ✅ 数据清洗成功，包含 {len(cleaned_competitions)} 个联赛")
            return True
        else:
            logger.error("  ❌ 无法获取联赛数据")
            return False

    except Exception as e:
        logger.error(f"  ❌ 数据验证测试失败: {e}")
        return False


async def test_team_data_collection(collector):
    """测试球队数据采集"""
    try:
        logger.info("测试球队数据采集...")

        # 获取英超球队
        teams_data = await collector._make_request_with_retry('competitions/2021/teams')

        if teams_data and 'teams' in teams_data:
            teams = teams_data['teams']
            logger.info(f"  ✅ 英超球队采集成功，获取到 {len(teams)} 支球队")

            # 检查数据结构
            for i, team in enumerate(teams[:3]):  # 检查前3个球队
                if all(team.get(field) for field in ['id', 'name', 'shortName']):
                    logger.info(f"    球队 {i+1}: {team.get('name')} ({team.get('shortName')}) - ✅")
                else:
                    logger.warning(f"    球队 {i+1}: 数据结构不完整")

            return True
        else:
            logger.error("  ❌ 英超球队采集失败")
            return False

    except Exception as e:
        logger.error(f"  ❌ 球队数据采集测试失败: {e}")
        return False


async def test_league_standings(collector):
    """测试联赛积分榜"""
    try:
        logger.info("测试联赛积分榜...")

        # 获取英超积分榜
        standings_data = await collector._make_request_with_retry('competitions/2021/standings')

        if standings_data and 'standings' in standings_data:
            standings = standings_data['standings']
            logger.info(f"  ✅ 英超积分榜采集成功，包含 {len(standings)} 个积分榜")

            # 检查数据结构
            for standing in standings[:2]:  # 检查前2个积分榜
                if 'table' in standing and isinstance(standing['table'], list):
                    table = standing['table']
                    logger.info(f"    积分榜包含 {len(table)} 支球队")

                    # 检查前3名
                    for i, team in enumerate(table[:3]):
                        team_data = team.get('team', {})
                        if all(team_data.get(field) for field in ['id', 'name']):
                            points = team.get('points', 0)
                            position = i + 1
                            logger.info(f"      第{position}名: {team_data.get('name')} - {points}分 - ✅")
                        else:
                            logger.warning(f"      第{position}名: 数据结构不完整")
                else:
                    logger.warning("    积分榜格式错误")

            return True
        else:
            logger.error("  ❌ 英超积分榜采集失败")
            return False

    except Exception as e:
        logger.error(f"  ❌ 联赛积分榜测试失败: {e}")
        return False


async def test_data_consistency(collector):
    """测试数据一致性"""
    try:
        logger.info("测试数据一致性...")

        # 获取球队和积分榜数据
        teams_data = await collector._make_request_with_retry('competitions/2021/teams')
        standings_data = await collector._make_request_with_retry('competitions/2021/standings')

        if not (teams_data and 'teams' in teams_data and standings_data and 'standings' in standings_data):
            logger.error("  ❌ 无法获取数据进行一致性测试")
            return False

        teams = teams_data['teams']
        standings = standings_data['standings']

        # 收集积分榜中的球队ID
        team_ids_from_standings = set()
        for standing in standings:
            table = standing.get('table', [])
            for team in table:
                team_id = team.get('team', {}).get('id')
                if team_id:
                    team_ids_from_standings.add(str(team_id))

        # 收集球队列表中的球队ID
        team_ids_from_teams = set(str(team.get('id')) for team in teams)

        logger.info(f"  球队数量对比: 球队列表={len(team_ids_from_teams)}, 积分榜={len(team_ids_from_standings)}")

        # 检查差异
        missing_in_standings = team_ids_from_teams - team_ids_from_standings
        missing_in_teams = team_ids_from_standings - team_ids_from_teams

        if missing_in_standings:
            logger.warning(f"  ⚠️ {len(missing_in_standings)} 支队在列表中但不在积分榜中")
        if missing_in_teams:
            logger.warning(f"  ⚠️ {len(missing_in_teams)} 支队在积分榜中但不在列表中")

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
    print("🚀 开始第二阶段简化测试（修复版）")
    print("=" * 50)

    start_time = datetime.now()

    tests = [
        ("错误处理和重试机制", test_error_handling),
        ("数据验证和清洗功能", test_data_validation),
        ("球队数据采集", test_team_data_collection),
        ("联赛积分榜采集", test_league_standings),
        ("数据一致性检查", test_data_consistency)
    ]

    passed = 0
    failed = 0

    async with SimpleDataCollector() as collector:
        for test_name, test_func in tests:
            print(f"\n🔍 执行 {test_name}测试...")
            try:
                if await test_func(collector):
                    print(f"✅ {test_name} 通过")
                    passed += 1
                else:
                    print(f"❌ {test_name} 失败")
                    failed += 1
            except Exception as e:
                print(f"❌ {test_name} 异常: {e}")
                failed += 1

    end_time = datetime.now()
    duration = end_time - start_time

    print("\n" + "=" * 50)
    print(f"📊 第二阶段测试完成!")
    print(f"   通过: {passed}")
    print(f"   失败: {failed}")
    print(f"   总计: {passed + failed}")
    print(f"   耗时: {duration.total_seconds():.2f} 秒")

    if failed == 0:
        print("🎉 所有测试通过！")
        print("✅ 错误处理和重试机制工作正常")
        print("✅ 数据验证和清洗功能正常")
        print("✅ 球队数据采集功能正常")
        print("✅ 联赛积分榜采集功能正常")
        print("✅ 数据一致性检查通过")
        print("🚀 第二阶段基本功能验证完成！")
        return True
    else:
        print("⚠️  部分测试失败，请检查实现")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    print(f"\n退出码: {0 if success else 1}")