#!/usr/bin/env python3
"""
FBref 全域采集启动器 (异步版本)
首席数据架构师专用工具

Purpose: 执行"全域轰炸" - 采集FBref上所有可用比赛
使用asyncio异步并发采集，避免多进程pickle问题
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.collectors.fbref_collector import FBrefCollector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("total_coverage_async.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class AsyncTotalCoverageLauncher:
    """异步全域采集启动器"""

    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.stats = {
            "total_leagues": 0,
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "total_matches": 0,
            "start_time": None,
            "end_time": None,
        }

    async def collect_single_league(self, league_info: Tuple[str, Dict]) -> Dict:
        """
        异步采集单个联赛数据
        """
        name, data = league_info
        url = data["url"]
        category = data["category"]
        tier = data["tier"]

        async with self.semaphore:
            result = {
                "league_name": name,
                "category": category,
                "tier": tier,
                "status": "failed",
                "matches_collected": 0,
                "seasons_collected": [],
                "error": None,
            }

            try:
                # 创建新的采集器实例
                collector = FBrefCollector()

                # 获取需要采集的赛季
                current_year = datetime.now().year
                seasons = [
                    f"{current_year - 1}-{current_year}",
                    f"{current_year - 2}-{current_year - 1}",
                    f"{current_year - 3}-{current_year - 2}",
                ]

                total_matches = 0
                successful_seasons = 0

                # 采集每个赛季的数据
                for season in seasons:
                    try:
                        # 采集赛季数据
                        data_df = await collector.get_season_schedule(url, season)

                        if not data_df.empty:
                            # 清洗数据
                            cleaned_data = collector._clean_schedule_data(data_df)
                            completed_matches = collector._filter_completed_matches(
                                cleaned_data
                            )

                            match_count = len(completed_matches)
                            total_matches += match_count

                            if match_count > 0:
                                successful_seasons += 1
                                result["seasons_collected"].append(season)

                        # 避免被封，添加延迟
                        await asyncio.sleep(3)

                    except Exception as e:
                        logger.warning(f"⚠️ 赛季 {season} 采集失败: {e}")
                        continue

                result["matches_collected"] = total_matches

                if total_matches > 0:
                    result["status"] = "success"
                    self.stats["successful"] += 1
                    logger.info(
                        f"✅ {name}: {total_matches} 场比赛 ({successful_seasons}/3 赛季)"
                    )
                else:
                    result["error"] = "No matches collected"
                    self.stats["failed"] += 1

            except Exception as e:
                logger.error(f"❌ {name} 采集失败: {e}")
                result["error"] = str(e)
                self.stats["failed"] += 1

            finally:
                self.stats["processed"] += 1
                progress = (self.stats["processed"] / self.stats["total_leagues"]) * 100
                logger.info(
                    f"📊 进度: {self.stats['processed']}/{self.stats['total_leagues']} ({progress:.1f}%) - {name}"
                )

            return result

    async def run_async_collection(self, leagues: Dict[str, Dict]) -> Dict:
        """异步并行采集所有联赛数据"""
        logger.info(f"\n🚀 启动异步采集 (最大并发数: {self.max_concurrent})")

        self.stats["start_time"] = datetime.now()

        # 创建所有任务
        tasks = [
            self.collect_single_league((name, data)) for name, data in leagues.items()
        ]

        # 并发执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)

        self.stats["end_time"] = datetime.now()

        # 处理结果
        successful_results = []
        failed_results = []

        for result in results:
            if isinstance(result, Exception):
                failed_results.append(
                    {"league_name": "Unknown", "status": "error", "error": str(result)}
                )
                self.stats["failed"] += 1
            elif result.get("status") == "success":
                successful_results.append(result)
                self.stats["total_matches"] += result["matches_collected"]
            else:
                failed_results.append(result)

        return {
            "successful": successful_results,
            "failed": failed_results,
            "total_matches": self.stats["total_matches"],
        }

    def get_leagues_data(self) -> Dict[str, Dict]:
        """获取联赛数据"""
        logger.info("📋 加载联赛数据...")

        collector = FBrefCollector()
        leagues_data = collector.load_leagues_from_db()
        self.stats["total_leagues"] = len(leagues_data)

        # 只选择主要联赛进行测试
        # 五大联赛 + 主要杯赛
        priority_leagues = {}
        priority_keywords = [
            "Premier League",
            "La Liga",
            "Serie A",
            "Bundesliga",
            "Ligue 1",
            "Champions League",
            "Europa League",
            "Copa",
            "FA Cup",
            "DFB-Pokal",
            "EFL",
            "MLS",
            "Liga MX",
            "Serie A",
            "Eredivisie",
        ]

        for name, data in leagues_data.items():
            if any(keyword in name for keyword in priority_keywords):
                priority_leagues[name] = data

        logger.info(f"✅ 加载 {len(leagues_data)} 个联赛")
        logger.info(f"🎯 优先采集 {len(priority_leagues)} 个主要联赛")

        return priority_leagues

    def print_final_report(self, results: Dict):
        """打印最终报告"""
        duration = self.stats["end_time"] - self.stats["start_time"]
        duration_minutes = duration.total_seconds() / 60

        logger.info("\n" + "=" * 80)
        logger.info("🎉 异步全域采集完成!")
        logger.info("=" * 80)

        logger.info(f"\n📊 采集统计:")
        logger.info(f"  总联赛数: {self.stats['total_leagues']}")
        logger.info(f"  成功联赛: {self.stats['successful']}")
        logger.info(f"  失败联赛: {self.stats['failed']}")
        logger.info(f"  总比赛数: {results['total_matches']:,}")
        logger.info(f"  采集时长: {duration_minutes:.1f} 分钟")
        logger.info(
            f"  平均速度: {results['total_matches']/max(duration_minutes, 0.1):.1f} 场/分钟"
        )

        # 成功的联赛统计
        if results["successful"]:
            logger.info(f"\n✅ 成功联赛 (Top 10):")
            sorted_successful = sorted(
                results["successful"],
                key=lambda x: x["matches_collected"],
                reverse=True,
            )

            for i, league in enumerate(sorted_successful[:10], 1):
                seasons = ", ".join(league["seasons_collected"])
                logger.info(
                    f"  {i:2d}. {league['league_name']:40s} {league['matches_collected']:4d} 场 ({seasons})"
                )

        # 失败的联赛
        if results["failed"]:
            logger.info(f"\n❌ 失败联赛:")
            for league in results["failed"][:10]:  # 只显示前10个
                error = league["error"][:50] if league["error"] else "Unknown error"
                logger.info(f"  • {league['league_name']:40s} {error}")

        logger.info("=" * 80)

    async def run(self):
        """运行完整的异步全域采集流程"""
        logger.info("🏁 FBref 异步全域采集启动")
        logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        # 获取联赛数据
        leagues = self.get_leagues_data()

        # 异步并行采集
        results = await self.run_async_collection(leagues)

        # 打印报告
        self.print_final_report(results)

        return results["total_matches"] > 0


async def main():
    """主函数"""
    launcher = AsyncTotalCoverageLauncher(max_concurrent=3)
    success = await launcher.run()

    if success:
        logger.info("\n✅ 异步全域采集成功完成!")
        return 0
    else:
        logger.error("\n❌ 异步全域采集失败!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
