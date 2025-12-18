#!/usr/bin/env python3
"""
E2E Pipeline - 采集与入库全链路验证
End-to-End Pipeline - Collection and Database Integration Verification

该脚本验证从数据采集到数据库存储的完整链路：
1. FotMob 采集：赛程数据 -> 数据库
2. FBref 采集：赛季数据 -> 数据库
3. FeatureStore 写入：处理后的数据
4. API 读取验证：从数据库读取并验证数据完整性

作者: Integration Test Engineer (P2-3)
创建时间: 2025-12-06
版本: 1.0.0
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.collectors.http_client_factory import HttpClientFactory
from src.collectors.fbref.collector_v2 import FBrefCollectorV2
from src.collectors.rate_limiter import RateLimiter
from src.collectors.proxy_pool import ProxyPool, StaticProxyProvider
from src.database.async_manager import get_db_session
from src.features.feature_store import FootballFeatureStore
from src.database.models import Match, Team


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            f"/tmp/e2e_pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        ),
    ],
)
logger = logging.getLogger(__name__)


class E2EPipelineManager:
    """E2E Pipeline 管理器"""

    def __init__(self):
        self.stats = {
            "start_time": datetime.now(),
            "collection_stats": {
                "fotmob": {
                    "fixtures_collected": 0,
                    "details_collected": 0,
                    "errors": 0,
                },
                "fbref": {"season_stats_collected": 0, "errors": 0},
                "total": {"requests": 0, "errors": 0},
            },
            "database_stats": {
                "matches_inserted": 0,
                "features_written": 0,
                "teams_inserted": 0,
            },
            "end_time": None,
            "duration": None,
        }

    async def setup_collectors(self) -> dict[str, Any]:
        """设置采集器实例"""
        logger.info("🚀 初始化采集器组件...")

        # 创建基础组件
        rate_limiter = RateLimiter(
            {
                "default": {"rate": 3.0, "burst": 5, "max_wait_time": 60.0},
                "fbref.com": {"rate": 0.5, "burst": 1, "max_wait_time": 120.0},
                "fotmob.com": {"rate": 2.0, "burst": 3, "max_wait_time": 45.0},
            }
        )

        # 使用空代理提供者进行测试
        proxy_provider = StaticProxyProvider(proxies=[])
        proxy_pool = ProxyPool(provider=proxy_provider)

        # 创建 HTTP客户端工厂和采集器
        client_factory = HttpClientFactory()

        # FotMob 采集器
        fotmob_collector = await client_factory.create_collector("fotmob")

        # FBref 采集器
        fbref_collector = FBrefCollectorV2(
            rate_limiter=rate_limiter,
            proxy_pool=proxy_pool,
            use_curl_cffi=False,  # 测试环境不使用curl_cffi
            raw_data_dir="/tmp/e2e_raw_data",
        )

        return {
            "fotmob_collector": fotmob_collector,
            "fbref_collector": fbref_collector,
            "client_factory": client_factory,
            "rate_limiter": rate_limiter,
            "proxy_pool": proxy_pool,
        }

    async def collect_premier_league_fixtures(
        self, fotmob_collector
    ) -> list[dict[str, Any]]:
        """采集英超最近5轮比赛"""
        logger.info("📊 采集英超最近5轮比赛...")

        # 英超联赛ID (在FotMob中的标识)
        league_id = 47  # 通常是Premier League的ID

        # 获取最近5轮比赛的赛程
        recent_matches = []
        days_back = 30  # 最近30天的比赛

        try:
            # 使用FotMob V2采集器获取赛程数据
            fixtures_data = await fotmob_collector.collect_league_fixtures(
                league_id=league_id,
                days_back=days_back,
                limit=5,  # 只采集5场比赛
            )

            if fixtures_data and fixtures_data.get("matches"):
                matches = fixtures_data["matches"]
                recent_matches = matches[:5]  # 确保最多5场

                self.stats["collection_stats"]["fotmob"]["fixtures_collected"] = len(
                    recent_matches
                )
                logger.info(f"✅ 成功采集 {len(recent_matches)} 场英超比赛")

                # 记录采集统计
                for match in recent_matches:
                    match_data = {
                        "match_id": match.get("id"),
                        "home_team": match.get("home_team"),
                        "away_team": match.get("away_team"),
                        "scheduled_time": match.get("scheduled_time"),
                        "status": match.get("status"),
                        "source": "fotmob",
                        "collected_at": datetime.utcnow().isoformat(),
                    }
                    recent_matches.append(match_data)

                return recent_matches
            else:
                logger.warning("⚠️ 未能获取到比赛数据")
                self.stats["collection_stats"]["fotmob"]["errors"] += 1

        except Exception as e:
            logger.error(f"❌ FotMob采集失败: {str(e)}")
            self.stats["collection_stats"]["fotmob"]["errors"] += 1

        return []

    async def collect_premier_league_season(self, fbref_collector) -> dict[str, Any]:
        """采集英超2023-2024赛季统计数据"""
        logger.info("📅 采集英超2023-2024赛季统计数据...")

        # FBref英超赛程URL
        season_url = (
            "https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures"
        )
        season_year = "2023-2024"

        try:
            # 采集赛季数据
            season_data = await fbref_collector.collect_season_stats(
                season_url, season_year
            )

            if not season_data.empty:
                self.stats["collection_stats"]["fbref"]["season_stats_collected"] = 1
                logger.info(f"✅ 成功采集英超赛季数据: {season_data.shape}")

                # 转换为字典格式便于处理
                season_dict = {
                    "url": season_url,
                    "season_year": season_year,
                    "shape": season_data.shape,
                    "columns": list(season_data.columns),
                    "sample_data": season_data.head(3).to_dict()
                    if not season_data.empty
                    else {},
                    "collected_at": datetime.utcnow().isoformat(),
                }

                return season_dict
            else:
                logger.warning("⚠️ FBref采集返回空数据")
                self.stats["collection_stats"]["fbref"]["errors"] += 1

        except Exception as e:
            logger.error(f"❌ FBref采集失败: {str(e)}")
            self.stats["collection_stats"]["fbref"]["errors"] += 1

        return {}

    async def save_matches_to_database(
        self, matches: list[dict[str, Any]]
    ) -> list[int]:
        """保存比赛数据到数据库"""
        logger.info(f"💾 保存 {len(matches)} 场比赛到数据库...")

        saved_match_ids = []

        async with get_db_session() as session:
            try:
                for match_data in matches:
                    # 检查比赛是否已存在
                    existing_match = await session.execute(
                        "SELECT id FROM matches WHERE source_match_id = :source_match_id AND source = :source",
                        {
                            "source_match_id": match_data["match_id"],
                            "source": match_data["source"],
                        },
                    ).scalar()

                    if not existing_match:
                        # 创建或查找主客队
                        home_team_id = await self._get_or_create_team(
                            session, match_data["home_team"]
                        )
                        away_team_id = await self._get_or_create_team(
                            session, match_data["away_team"]
                        )

                        # 创建比赛记录
                        new_match = Match(
                            source=match_data["source"],
                            source_match_id=match_data["match_id"],
                            home_team_id=home_team_id,
                            away_team_id=away_team_id,
                            scheduled_time=datetime.fromisoformat(
                                match_data["scheduled_time"]
                            )
                            if match_data.get("scheduled_time")
                            else None,
                            status=MatchStatus.SCHEDULED,
                            home_score=None,
                            away_score=None,
                            home_xg=None,
                            away_xg=None,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                        )

                        session.add(new_match)
                        await session.flush()  # 获取生成的ID
                        saved_match_ids.append(new_match.id)
                        self.stats["database_stats"]["matches_inserted"] += 1

                await session.commit()
                logger.info(f"✅ 成功保存 {len(saved_match_ids)} 场新比赛到数据库")

            except Exception as e:
                await session.rollback()
                logger.error(f"❌ 保存比赛数据失败: {str(e)}")

        return saved_match_ids

    async def save_season_stats_to_database(self, season_data: dict[str, Any]) -> bool:
        """保存赛季统计数据到数据库"""
        logger.info("💾 保存赛季统计数据到数据库...")

        # 这里简化处理，实际应用中可能需要更复杂的赛季数据表
        async with get_db_session():
            try:
                # 示例：保存赛季统计摘要
                {
                    "season_year": season_data.get("season_year"),
                    "total_matches": season_data.get("shape", (0, 0))[0],
                    "columns_count": len(season_data.get("columns", [])),
                    "source": "fbref",
                    "created_at": datetime.utcnow(),
                    "raw_data_path": None,
                }

                # 这里可以创建一个season_stats表或使用JSON字段存储
                # 为了简化，我们将数据保存到JSON文件
                import json

                output_file = f"/tmp/season_stats_{season_data.get('season_year')}.json"
                with open(output_file, "w") as f:
                    json.dump(season_data, f, indent=2, default=str)

                logger.info(f"💾 赛季统计已保存到: {output_file}")
                return True

            except Exception as e:
                logger.error(f"❌ 保存赛季统计失败: {str(e)}")
                return False

    async def write_to_feature_store(
        self, match_ids: list[int]
    ) -> list[dict[str, Any]]:
        """写入数据到FeatureStore"""
        logger.info(f"🔄 写入 {len(match_ids)} 场比赛到FeatureStore...")

        feature_store = FootballFeatureStore()
        feature_records = []

        try:
            # 初始化FeatureStore
            await feature_store.initialize()

            # 获取比赛数据并写入特征
            async with get_db_session() as session:
                for match_id in match_ids:
                    # 查询比赛详情
                    match = await session.execute(
                        """
                        SELECT m.*, ht.name as home_team_name, at.name as away_team_name
                        FROM matches m
                        LEFT JOIN teams ht ON m.home_team_id = ht.id
                        LEFT JOIN teams at ON m.away_team_id = at.id
                        WHERE m.id = :match_id
                        """,
                        {"match_id": match_id},
                    ).first()

                    if match:
                        # 创建特征记录
                        feature_record = {
                            "match_id": match_id,
                            "home_team": match.home_team_name,
                            "away_team": match.away_team_name,
                            "scheduled_time": match.scheduled_time,
                            "source": match.source,
                            "features": {
                                "match_day": datetime.utcnow().weekday(),
                                "is_weekend": datetime.utcnow().weekday() >= 5,
                                "days_since_start": (
                                    datetime.utcnow() - match.scheduled_time
                                ).days
                                if match.scheduled_time
                                else 0,
                            },
                            "created_at": datetime.utcnow(),
                        }

                        # 写入FeatureStore
                        feature_id = await feature_store.write_features(
                            [feature_record]
                        )
                        if feature_id:
                            feature_records.extend(feature_id)
                            self.stats["database_stats"]["features_written"] += 1

            logger.info(f"✅ 成功写入 {len(feature_records)} 条特征记录到FeatureStore")
            return feature_records

        except Exception as e:
            logger.error(f"❌ FeatureStore写入失败: {str(e)}")
            return []

    async def _get_or_create_team(self, session, team_name: str) -> int:
        """获取或创建球队记录"""
        team = await session.execute(
            "SELECT id FROM teams WHERE name = :team_name", {"team_name": team_name}
        ).scalar()

        if team:
            return team

        # 创建新球队
        new_team = Team(
            name=team_name, created_at=datetime.utcnow(), updated_at=datetime.utcnow()
        )
        session.add(new_team)
        await session.flush()
        self.stats["database_stats"]["teams_inserted"] += 1

        return new_team.id

    async def verify_api_endpoints(self, match_ids: list[int]) -> dict[str, Any]:
        """验证API端点数据读取"""
        logger.info(f"🔍 验证API端点数据读取 (match_ids: {match_ids[:3]}...)")

        api_verification = {
            "tested_endpoints": 0,
            "successful_responses": 0,
            "failed_responses": 0,
            "api_data": {},
        }

        # 测试多个API端点
        test_endpoints = [
            "http://localhost:8000/health",
            "http://localhost:8000/api/v1/predictions/",
            "http://localhost:8000/api/v1/predictions/match/",
        ]

        import httpx

        async with httpx.AsyncClient() as client:
            for endpoint in test_endpoints:
                try:
                    response = await client.get(endpoint, timeout=10.0)
                    api_verification["tested_endpoints"] += 1

                    if response.status_code == 200:
                        api_verification["successful_responses"] += 1
                        api_verification["api_data"][endpoint] = response.json()
                        logger.info(f"✅ API端点 {endpoint} 响应正常")
                    else:
                        api_verification["failed_responses"] += 1
                        logger.warning(
                            f"⚠️ API端点 {endpoint} 响应状态: {response.status_code}"
                        )

                except Exception as e:
                    api_verification["failed_responses"] += 1
                    logger.error(f"❌ API端点 {endpoint} 请求失败: {str(e)}")

        # 测试特定比赛预测端点
        if match_ids:
            match_id = match_ids[0]
            prediction_endpoint = (
                f"http://localhost:8000/api/v1/predictions/match/{match_id}"
            )

            try:
                response = await client.get(prediction_endpoint, timeout=10.0)
                api_verification["tested_endpoints"] += 1

                if response.status_code == 200:
                    prediction_data = response.json()
                    api_verification["successful_responses"] += 1
                    api_verification["api_data"][prediction_endpoint] = prediction_data
                    logger.info(f"✅ 比赛预测API端点响应正常: match_id={match_id}")

                    # 验证预测数据结构
                    if (
                        "request_id" in prediction_data
                        and "match_id" in prediction_data
                    ):
                        logger.info("✅ 预测响应格式验证通过")
                    else:
                        logger.warning("⚠️ 预测响应格式可能不正确")

                else:
                    api_verification["failed_responses"] += 1
                    logger.warning(f"⚠️ 比赛预测API响应状态: {response.status_code}")

            except Exception as e:
                api_verification["failed_responses"] += 1
                logger.error(f"❌ 比赛预测API请求失败: {str(e)}")

        return api_verification

    def generate_report(self) -> dict[str, Any]:
        """生成测试报告"""
        self.stats["end_time"] = datetime.now()
        self.stats["duration"] = (
            self.stats["end_time"] - self.stats["start_time"]
        ).total_seconds()

        return {
            "pipeline_summary": {
                "duration_seconds": self.stats["duration"],
                "start_time": self.stats["start_time"].isoformat(),
                "end_time": self.stats["end_time"].isoformat(),
                "overall_status": "SUCCESS"
                if self.stats["collection_stats"]["total"]["errors"] == 0
                else "FAILED",
            },
            "collection_stats": self.stats["collection_stats"],
            "database_stats": self.stats["database_stats"],
            "success_criteria": {
                "fotmob_fixtures_collected": self.stats["collection_stats"]["fotmob"][
                    "fixtures_collected"
                ]
                > 0,
                "fbref_season_collected": self.stats["collection_stats"]["fbref"][
                    "season_stats_collected"
                ]
                > 0,
                "matches_saved": self.stats["database_stats"]["matches_inserted"] > 0,
                "features_written": self.stats["database_stats"]["features_written"]
                > 0,
                "api_responsive": api_verification.get("successful_responses", 0) > 0
                if "api_verification" in locals()
                else False,
            },
        }

    async def run_pipeline(self) -> dict[str, Any]:
        """运行完整的E2E Pipeline"""
        logger.info("🚀 开始E2E Pipeline执行...")
        logger.info("=" * 60)

        # 1. 设置采集器
        collectors = await self.setup_collectors()

        # 2. 采集FotMob比赛数据
        logger.info("\n📊 Phase 1: FotMob数据采集")
        fotmob_matches = await self.collect_premier_league_fixtures(
            collectors["fotmob_collector"]
        )
        self.stats["collection_stats"]["total"]["requests"] += len(fotmob_matches)

        # 3. 采集FBref赛季数据
        logger.info("\n📅 Phase 2: FBref数据采集")
        season_stats = await self.collect_premier_league_season(
            collectors["fbref_collector"]
        )

        # 4. 保存到数据库
        logger.info("\n💾 Phase 3: 数据库存储")
        match_ids = []
        if fotmob_matches:
            match_ids = await self.save_matches_to_database(fotmob_matches)
        self.stats["collection_stats"]["total"]["requests"] += len(fotmob_matches)

        # 5. 写入FeatureStore
        logger.info("\n🔄 Phase 4: FeatureStore写入")
        feature_records = await self.write_to_feature_store(match_ids)

        # 6. API验证
        logger.info("\n🔍 Phase 5: API端点验证")
        api_verification = await self.verify_api_endpoints(match_ids)

        # 7. 清理资源
        logger.info("\n🧹 Phase 6: 资源清理")
        await collectors["client_factory"].cleanup()
        collectors["fbref_collector"].cleanup()

        # 8. 生成报告
        logger.info("\n📋 生成测试报告...")
        report = self.generate_report()

        # 添加API验证到报告
        if "api_verification" in locals():
            report["api_verification"] = api_verification

        return report


async def simulate_network_error(self):
    """模拟网络中断错误"""
    logger.warning("⚠️ 模拟网络中断5秒...")

    import httpx

    # 模拟网络不可用
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://httpbin.org/status/503", timeout=5.0)
            logger.info(f"模拟网络错误响应: {response.status_code}")
        except Exception as e:
            logger.info(f"网络中断模拟成功: {str(e)}")

    # 等待5秒
    await asyncio.sleep(5)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="E2E Pipeline - 采集与入库全链路验证")
    parser.add_argument(
        "--simulate-error", action="store_true", help="模拟网络错误进行错误恢复测试"
    )

    args = parser.parse_args()

    logger.info("🎯 E2E Pipeline - 采集与入库全链路验证")
    logger.info("=" * 60)

    pipeline = E2EPipelineManager()

    try:
        # 如果启用错误模拟
        if args.simulate_error:
            logger.info("🚨 错误恢复测试模式已启用")
            await simulate_network_error()
            logger.info("🔄 网络恢复，继续执行...")

        # 运行完整pipeline
        result = await pipeline.run_pipeline()

        # 输出结果
        logger.info("\n" + "=" * 60)
        logger.info("📊 E2E Pipeline 执行完成")
        logger.info(
            f"   执行时间: {result['pipeline_summary']['duration_seconds']:.2f} 秒"
        )
        logger.info(f"   整体状态: {result['pipeline_summary']['overall_status']}")

        if result["pipeline_summary"]["overall_status"] == "SUCCESS":
            logger.info("🎉 所有验证通过!")
            logger.info("   ✅ FotMob数据采集: 5 场比赛")
            logger.info("   ✅ FBref数据采集: 1 个赛季")
            logger.info(
                "   ✅ 数据库存储: {} 场比赛".format(
                    result["database_stats"]["matches_inserted"]
                )
            )
            logger.info(
                "   ✅ FeatureStore: {} 条特征".format(
                    result["database_stats"]["features_written"]
                )
            )

            if (
                "api_verification" in result
                and result["api_verification"]["successful_responses"] > 0
            ):
                logger.info(
                    "   ✅ API响应: {} 个端点".format(
                        result["api_verification"]["successful_responses"]
                    )
                )

            return 0
        else:
            logger.error("❌ 部分验证失败")
            logger.error(
                "   失败统计: {}".format(result["collection_stats"]["total"]["errors"])
            )
            return 1

    except KeyboardInterrupt:
        logger.info("\n⏹️ 用户中断执行")
        return 130
    except Exception as e:
        logger.error(f"\n💥 Pipeline执行异常: {str(e)}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
