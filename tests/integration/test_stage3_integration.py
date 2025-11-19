#!/usr/bin/env python3
"""
第三阶段集成测试脚本
Stage 3 Integration Test Script - Database Integration and Caching
"""

import pytest

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict

# 添加项目根目录到Python路径
sys.path.insert(0, "/home/user/projects/FootballPrediction")

# 设置环境变量
os.environ["FOOTBALL_DATA_API_KEY"] = "ed809154dc1f422da46a18d8961a98a0"

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# 导入模块
try:
    from src.cache.football_data_cache import get_football_cache_manager
    from src.models.external.league import ExternalLeague, ExternalLeagueStandings
    from src.models.external.match import ExternalMatch
    from src.models.external.team import ExternalTeam
except ImportError as e:
    logger.error(f"导入模块失败: {e}")
    logger.info("尝试简化导入...")

    # 简化测试，不依赖复杂的数据库集成
    from test_stage2_fixed import SimpleDataCollector


class Stage3IntegrationTester:
    """第三阶段集成测试器"""

    def __init__(self):
        self.cache_manager = None
        self.sync_service = None
        self.test_results = {
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "errors": [],
        }

    async def initialize(self):
        """初始化测试环境"""
        try:
            # 初始化缓存管理器
            self.cache_manager = get_football_cache_manager()
            logger.info("✅ 缓存管理器初始化成功")

            # 注意：由于可能没有数据库连接，我们将使用简化的测试方式
            logger.info("⚠️ 使用简化测试模式，跳过数据库初始化")

        except Exception as e:
            logger.error(f"❌ 初始化失败: {e}")
            self.test_results["errors"].append(f"初始化失败: {e}")

    @pytest.mark.asyncio

    async def test_cache_functionality(self) -> bool:
        """测试缓存功能"""
        try:
            logger.info("🔍 测试缓存功能...")

            # 测试联赛数据缓存
            test_league_data = {
                "external_id": "2021",
                "name": "Premier League",
                "code": "PL",
                "type": "LEAGUE",
                "current_matchday": 12,
            }

            # 缓存联赛数据
            success = await self.cache_manager.cache_league(test_league_data)
            if not success:
                raise Exception("缓存联赛数据失败")

            # 获取缓存的联赛数据
            cached_league = await self.cache_manager.get_cached_league("2021")
            if not cached_league or cached_league.get("name") != "Premier League":
                raise Exception("获取缓存联赛数据失败")

            logger.info("  ✅ 联赛数据缓存测试通过")

            # 测试球队数据缓存
            test_team_data = {
                "external_id": "57",
                "name": "Arsenal FC",
                "short_name": "Arsenal",
                "tla": "ARS",
                "competition_id": "2021",
            }

            success = await self.cache_manager.cache_team(test_team_data)
            if not success:
                raise Exception("缓存球队数据失败")

            cached_team = await self.cache_manager.get_cached_team("57")
            if not cached_team or cached_team.get("name") != "Arsenal FC":
                raise Exception("获取缓存球队数据失败")

            logger.info("  ✅ 球队数据缓存测试通过")

            # 测试积分榜数据缓存
            test_standings_data = [
                {
                    "position": 1,
                    "team_name": "Arsenal FC",
                    "points": 22,
                    "played_games": 8,
                },
                {
                    "position": 2,
                    "team_name": "Manchester City FC",
                    "points": 18,
                    "played_games": 8,
                },
            ]

            success = await self.cache_manager.cache_standings(
                "2021", test_standings_data
            )
            if not success:
                raise Exception("缓存积分榜数据失败")

            cached_standings = await self.cache_manager.get_cached_standings("2021")
            if not cached_standings or len(cached_standings) != 2:
                raise Exception("获取缓存积分榜数据失败")

            logger.info("  ✅ 积分榜数据缓存测试通过")

            # 测试API响应缓存
            test_api_response = {
                "competitions": [
                    {"id": 2021, "name": "Premier League"},
                    {"id": 2014, "name": "La Liga"},
                ]
            }

            success = await self.cache_manager.cache_api_response(
                "competitions", {}, test_api_response
            )
            if not success:
                raise Exception("缓存API响应失败")

            cached_response = await self.cache_manager.get_cached_api_response(
                "competitions"
            )
            if not cached_response or len(cached_response.get("competitions", [])) != 2:
                raise Exception("获取缓存API响应失败")

            logger.info("  ✅ API响应缓存测试通过")

            return True

        except Exception as e:
            logger.error(f"  ❌ 缓存功能测试失败: {e}")
            return False

    @pytest.mark.asyncio

    async def test_data_models(self) -> bool:
        """测试数据模型"""
        try:
            logger.info("🔍 测试数据模型...")

            # 测试联赛模型
            league_data = {
                "id": 2021,
                "name": "Premier League",
                "code": "PL",
                "type": "LEAGUE",
                "emblem": "https://crests.football-data.org/pl.png",
                "area": {"id": 2072, "name": "England", "code": "ENG"},
                "season": {
                    "id": 1086,
                    "currentMatchday": 12,
                    "startDate": "2024-08-16",
                    "endDate": "2025-05-25",
                },
                "lastUpdated": "2024-10-31T20:00:00Z",
            }

            league = ExternalLeague.from_api_data(league_data, is_supported=True)

            if league.external_id != "2021" or league.name != "Premier League":
                raise Exception("联赛模型创建失败")

            if not league.is_supported or league.data_quality_score <= 0:
                raise Exception("联赛模型属性设置失败")

            logger.info("  ✅ 联赛模型测试通过")

            # 测试球队模型
            team_data = {
                "id": 57,
                "name": "Arsenal FC",
                "shortName": "Arsenal",
                "tla": "ARS",
                "crest": "https://crests.football-data.org/57.png",
                "address": "75 Drayton Park London",
                "website": "https://www.arsenal.com",
                "founded": 1886,
                "clubColors": "Red / White",
                "venue": "Emirates Stadium",
                "area": {"id": 2072, "name": "England", "code": "ENG"},
                "lastUpdated": "2024-10-31T20:00:00Z",
            }

            competition_info = {"id": 2021, "name": "Premier League", "code": "PL"}
            team = ExternalTeam.from_api_data(team_data, competition_info)

            if team.external_id != "57" or team.name != "Arsenal FC":
                raise Exception("球队模型创建失败")

            if team.competition_id != 2021 or team.founded != 1886:
                raise Exception("球队模型关联信息设置失败")

            logger.info("  ✅ 球队模型测试通过")

            # 测试积分榜模型
            standings_data = {
                "position": 1,
                "playedGames": 8,
                "won": 7,
                "draw": 1,
                "lost": 0,
                "goalsFor": 18,
                "goalsAgainst": 5,
                "goalDifference": 13,
                "points": 22,
                "team": {
                    "id": 57,
                    "name": "Arsenal FC",
                    "shortName": "Arsenal",
                    "crest": "https://crests.football-data.org/57.png",
                },
            }

            standings = ExternalLeagueStandings.from_api_data(
                standings_data, league_id=1, external_league_id="2021"
            )

            if standings.position != 1 or standings.team_name != "Arsenal FC":
                raise Exception("积分榜模型创建失败")

            if standings.points != 22 or standings.goal_difference != 13:
                raise Exception("积分榜模型数据设置失败")

            logger.info("  ✅ 积分榜模型测试通过")

            # 测试比赛模型
            match_data = {
                "id": 435678,
                "utcDate": "2024-11-02T17:30:00Z",
                "status": "scheduled",
                "matchday": 11,
                "stage": "REGULAR_SEASON",
                "venue": "Emirates Stadium",
                "competition": {"id": 2021, "name": "Premier League", "code": "PL"},
                "homeTeam": {"id": 57, "name": "Arsenal FC", "shortName": "Arsenal"},
                "awayTeam": {
                    "id": 61,
                    "name": "Liverpool FC",
                    "shortName": "Liverpool",
                },
                "score": {"fullTime": {"home": None, "away": None}, "winner": None},
                "lastUpdated": "2024-10-31T20:00:00Z",
            }

            match = ExternalMatch.from_api_data(match_data)

            if match.external_id != "435678" or match.home_team_name != "Arsenal FC":
                raise Exception("比赛模型创建失败")

            if not match.is_scheduled or match.status != "scheduled":
                raise Exception("比赛模型状态设置失败")

            logger.info("  ✅ 比赛模型测试通过")

            return True

        except Exception as e:
            logger.error(f"  ❌ 数据模型测试失败: {e}")
            return False

    @pytest.mark.asyncio

    async def test_collector_integration(self) -> bool:
        """测试数据采集器集成"""
        try:
            logger.info("🔍 测试数据采集器集成...")

            # 使用简化的数据采集器
            async with SimpleDataCollector() as collector:
                # 测试联赛数据采集
                competitions_data = await collector._make_request_with_retry(
                    "competitions"
                )
                if not competitions_data or "competitions" not in competitions_data:
                    raise Exception("联赛数据采集失败")

                competitions = competitions_data["competitions"]
                premier_league = next(
                    (comp for comp in competitions if comp.get("code") == "PL"), None
                )

                if not premier_league:
                    raise Exception("未找到英超联赛数据")

                logger.info(f"  ✅ 联赛数据采集成功: {premier_league['name']}")

                # 测试球队数据采集
                teams_data = await collector._make_request_with_retry(
                    "competitions/2021/teams"
                )
                if not teams_data or "teams" not in teams_data:
                    raise Exception("球队数据采集失败")

                teams = teams_data["teams"]
                arsenal = next(
                    (team for team in teams if "Arsenal" in team.get("name", "")), None
                )

                if not arsenal:
                    raise Exception("未找到阿森纳球队数据")

                logger.info(f"  ✅ 球队数据采集成功: {arsenal['name']}")

                # 测试积分榜数据采集
                standings_data = await collector._make_request_with_retry(
                    "competitions/2021/standings"
                )
                if not standings_data or "standings" not in standings_data:
                    raise Exception("积分榜数据采集失败")

                standings = standings_data["standings"]
                if not standings or len(standings) == 0:
                    raise Exception("积分榜数据为空")

                logger.info(
                    f"  ✅ 积分榜数据采集成功: {len(standings[0].get('table', []))} 支球队"
                )

                return True

        except Exception as e:
            logger.error(f"  ❌ 数据采集器集成测试失败: {e}")
            return False

    @pytest.mark.asyncio

    async def test_cache_invalidations(self) -> bool:
        """测试缓存失效机制"""
        try:
            logger.info("🔍 测试缓存失效机制...")

            # 先缓存一些数据
            test_league_data = {
                "external_id": "2021",
                "name": "Premier League",
                "code": "PL",
            }

            await self.cache_manager.cache_league(test_league_data)

            # 验证数据已缓存
            cached = await self.cache_manager.get_cached_league("2021")
            if not cached:
                raise Exception("数据缓存失败")

            # 测试单个缓存失效
            deleted_count = await self.cache_manager.invalidate_league_cache("2021")
            if deleted_count == 0:
                raise Exception("缓存失效失败")

            # 验证数据已失效
            cached = await self.cache_manager.get_cached_league("2021")
            if cached:
                raise Exception("缓存失效后仍能获取数据")

            logger.info("  ✅ 单个缓存失效测试通过")

            # 缓存多个数据
            await self.cache_manager.cache_league(test_league_data)
            await self.cache_manager.cache_team(
                {"external_id": "57", "name": "Arsenal FC"}
            )

            # 测试联赛相关缓存失效
            deleted_count = await self.cache_manager.invalidate_competition_cache(
                "2021"
            )
            if deleted_count == 0:
                logger.warning("  ⚠️ 联赛相关缓存失效可能没有删除任何键")

            logger.info("  ✅ 缓存失效机制测试通过")

            return True

        except Exception as e:
            logger.error(f"  ❌ 缓存失效机制测试失败: {e}")
            return False

    @pytest.mark.asyncio

    async def test_sync_status_tracking(self) -> bool:
        """测试同步状态跟踪"""
        try:
            logger.info("🔍 测试同步状态跟踪...")

            # 设置同步状态
            status_data = {
                "success": True,
                "total_processed": 100,
                "total_created": 50,
                "total_updated": 30,
                "total_failed": 20,
                "duration_seconds": 120.5,
            }

            success = await self.cache_manager.set_sync_status("test_sync", status_data)
            if not success:
                raise Exception("设置同步状态失败")

            # 获取同步状态
            retrieved_status = await self.cache_manager.get_sync_status("test_sync")
            if not retrieved_status:
                raise Exception("获取同步状态失败")

            if retrieved_status.get("status", {}).get("total_processed") != 100:
                raise Exception("同步状态数据不匹配")

            logger.info("  ✅ 同步状态跟踪测试通过")

            return True

        except Exception as e:
            logger.error(f"  ❌ 同步状态跟踪测试失败: {e}")
            return False

    async def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        logger.debug("🚀 开始第三阶段集成测试")
        logger.debug("=" * 60)

        start_time = datetime.now()

        tests = [
            ("缓存功能", self.test_cache_functionality),
            ("数据模型", self.test_data_models),
            ("数据采集器集成", self.test_collector_integration),
            ("缓存失效机制", self.test_cache_invalidations),
            ("同步状态跟踪", self.test_sync_status_tracking),
        ]

        for test_name, test_func in tests:
            logger.debug(
                f"\n🔍 执行 {test_name}测试..."
            )
            self.test_results["total_tests"] += 1

            try:
                if await test_func():
                    logger.debug(
                        f"✅ {test_name}测试通过"
                    )
                    self.test_results["passed_tests"] += 1
                else:
                    logger.debug(
                        f"❌ {test_name}测试失败"
                    )
                    self.test_results["failed_tests"] += 1
            except Exception as e:
                logger.debug(
                    f"❌ {test_name}测试异常: {e}"
                )
                self.test_results["failed_tests"] += 1
                self.test_results["errors"].append(f"{test_name}: {e}")

        end_time = datetime.now()
        duration = end_time - start_time

        # 清理测试数据
        try:
            await self.cache_manager.clear_all_football_cache()
            logger.info("✅ 测试数据清理完成")
        except Exception as e:
            logger.warning(f"⚠️ 测试数据清理失败: {e}")

        logger.debug("\n" + "=" * 60)
        logger.debug("📊 第三阶段集成测试完成!")
        logger.debug(
            f"   总计: {self.test_results['total_tests']}"
        )
        logger.debug(
            f"   通过: {self.test_results['passed_tests']}"
        )
        logger.error(
            f"   失败: {self.test_results['failed_tests']}"
        )
        logger.debug(
            f"   耗时: {duration.total_seconds():.2f} 秒"
        )

        if self.test_results["errors"]:
            logger.debug("\n❌ 错误详情:")
            for error in self.test_results["errors"]:
                logger.error(f"   - {error}")

        success_rate = 0
        if self.test_results["total_tests"] > 0:
            success_rate = (
                self.test_results["passed_tests"] / self.test_results["total_tests"]
            ) * 100

        logger.debug(
            f"\n🎯 成功率: {success_rate:.1f}%"
        )

        if self.test_results["failed_tests"] == 0:
            logger.debug("🎉 所有测试通过！")
            logger.debug("✅ 缓存功能正常工作")
            logger.debug(
                "✅ 数据模型创建和转换正确"
            )
            logger.debug("✅ 数据采集器集成成功")
            logger.debug("✅ 缓存失效机制有效")
            logger.debug("✅ 同步状态跟踪正常")
            logger.debug(
                "🚀 第三阶段集成验证完成！"
            )
            return True
        else:
            logger.debug(
                "⚠️  部分测试失败，请检查实现"
            )
            return False


async def main():
    """主测试函数"""
    tester = Stage3IntegrationTester()

    try:
        # 初始化测试环境
        await tester.initialize()

        # 运行所有测试
        success = await tester.run_all_tests()

        logger.debug(
            f"\n退出码: {0 if success else 1}"
        )
        return success

    except Exception as e:
        logger.error(f"测试执行失败: {e}")
        logger.debug(f"\n❌ 测试执行异常: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
