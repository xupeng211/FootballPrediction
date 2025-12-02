#!/usr/bin/env python3
"""
FBref 全域采集启动器 (Total Coverage Launcher)
首席数据架构师专用工具

Purpose: 执行"全域轰炸" - 采集FBref上所有可用比赛
采用多进程并发采集，覆盖当前赛季+过去2个赛季

Strategy:
1. 先刷新联赛列表 (discover_all_leagues.py)
2. 从数据库加载所有305个联赛
3. 使用ProcessPoolExecutor开启10个并发任务
4. 每个联赛采集3个赛季的数据
5. 总计约1000+场比赛
"""

import asyncio
import logging
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.collectors.fbref_collector import FBrefCollector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("total_coverage.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class TotalCoverageLauncher:
    """全域采集启动器"""

    def __init__(self, max_workers: int = 8):
        self.max_workers = max_workers
        self.collector = FBrefCollector()
        self.stats = {
            "total_leagues": 0,
            "processed": 0,
            "successful": 0,
            "failed": 0,
            "total_matches": 0,
            "start_time": None,
            "end_time": None,
        }

    def refresh_league_list(self) -> bool:
        """刷新联赛列表"""
        logger.info("🔄 刷新联赛列表...")

        try:
            from scripts.discover_all_leagues import FBrefLeagueDiscovery

            discovery = FBrefLeagueDiscovery()
            result = discovery.run_discovery()

            if "error" not in result:
                logger.info(
                    f"✅ 联赛列表已刷新，共 {result['statistics']['total_leagues']} 个联赛"
                )
                return True
            else:
                logger.error(f"❌ 联赛列表刷新失败: {result['error']}")
                return False
        except Exception as e:
            logger.error(f"❌ 联赛列表刷新异常: {e}")
            return False

    def get_all_leagues(self) -> Dict[str, Dict]:
        """获取所有联赛"""
        logger.info("📋 加载联赛列表...")

        try:
            leagues_data = self.collector.load_leagues_from_db()
            self.stats["total_leagues"] = len(leagues_data)

            logger.info(f"✅ 成功加载 {len(leagues_data)} 个联赛")

            # 按分类统计
            categories = {}
            for name, data in leagues_data.items():
                cat = data["category"]
                categories[cat] = categories.get(cat, 0) + 1

            logger.info("\n🏆 联赛分布:")
            for cat, count in sorted(
                categories.items(), key=lambda x: x[1], reverse=True
            ):
                logger.info(f"  {cat:40s}: {count:3d}")

            return leagues_data

        except Exception as e:
            logger.error(f"❌ 加载联赛列表失败: {e}")
            return {}

    def get_seasons_to_collect(self) -> List[str]:
        """获取需要采集的赛季列表"""
        current_year = datetime.now().year
        current_month = datetime.now().month

        # 确定当前赛季
        if current_month >= 8:  # 新赛季从8月开始
            current_season = f"{current_year}-{current_year + 1}"
            seasons = [
                f"{current_year}-{current_year + 1}",  # 当前赛季
                f"{current_year - 1}-{current_year}",  # 上赛季
                f"{current_year - 2}-{current_year - 1}",  # 前赛季
            ]
        else:
            # 当前是1-7月，当前赛季是上一年的赛季
            current_season = f"{current_year - 1}-{current_year}"
            seasons = [
                f"{current_year - 1}-{current_year}",  # 当前赛季
                f"{current_year - 2}-{current_year - 1}",  # 上赛季
                f"{current_year - 3}-{current_year - 2}",  # 前赛季
            ]

        logger.info(f"🗓️ 采集赛季: {', '.join(seasons)}")
        return seasons

    def collect_league_data(self, league_info: Tuple[str, Dict]) -> Dict:
        """
        采集单个联赛数据 (用于多进程)
        """
        name, data = league_info
        url = data["url"]
        category = data["category"]
        tier = data["tier"]

        # 收集联赛的基本信息
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
            # 创建新的采集器实例（多进程安全）
            collector = FBrefCollector()

            # 获取需要采集的赛季
            seasons = self.get_seasons_to_collect()

            total_matches = 0
            successful_seasons = 0

            # 采集每个赛季的数据
            for season in seasons:
                try:
                    # 采集赛季数据
                    data_df = asyncio.run(collector.get_season_schedule(url, season))

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

                        # 保存数据（如果需要）
                        # 这里可以添加数据库保存逻辑

                    # 避免被封，添加延迟
                    time.sleep(2)

                except Exception as e:
                    logger.warning(f"⚠️ 赛季 {season} 采集失败: {e}")
                    continue

            result["matches_collected"] = total_matches

            if total_matches > 0:
                result["status"] = "success"
                logger.info(
                    f"✅ {name}: {total_matches} 场比赛 ({successful_seasons}/3 赛季)"
                )
            else:
                result["error"] = "No matches collected"

        except Exception as e:
            logger.error(f"❌ {name} 采集失败: {e}")
            result["error"] = str(e)

        return result

    def run_parallel_collection(self, leagues: Dict[str, Dict]) -> Dict:
        """并行采集所有联赛数据"""
        logger.info(f"\n🚀 启动并行采集 (使用 {self.max_workers} 个进程)")

        self.stats["start_time"] = datetime.now()

        results = {"successful": [], "failed": [], "total_matches": 0}

        # 使用ProcessPoolExecutor进行多进程采集
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_league = {
                executor.submit(self.collect_league_data, (name, data)): name
                for name, data in leagues.items()
            }

            # 处理完成的任务
            for future in as_completed(future_to_league):
                league_name = future_to_league[future]
                self.stats["processed"] += 1

                try:
                    result = future.result()
                    results["total_matches"] += result["matches_collected"]

                    if result["status"] == "success":
                        results["successful"].append(result)
                        self.stats["successful"] += 1
                    else:
                        results["failed"].append(result)
                        self.stats["failed"] += 1

                    # 显示进度
                    progress = (
                        self.stats["processed"] / self.stats["total_leagues"]
                    ) * 100
                    logger.info(
                        f"📊 进度: {self.stats['processed']}/{self.stats['total_leagues']} ({progress:.1f}%) - {league_name}"
                    )

                except Exception as e:
                    logger.error(f"❌ {league_name} 处理异常: {e}")
                    results["failed"].append(
                        {"league_name": league_name, "status": "error", "error": str(e)}
                    )
                    self.stats["failed"] += 1

        self.stats["end_time"] = datetime.now()

        return results

    def print_final_report(self, results: Dict):
        """打印最终报告"""
        duration = self.stats["end_time"] - self.stats["start_time"]
        duration_minutes = duration.total_seconds() / 60

        logger.info("\n" + "=" * 80)
        logger.info("🎉 全域采集完成!")
        logger.info("=" * 80)

        logger.info(f"\n📊 采集统计:")
        logger.info(f"  总联赛数: {self.stats['total_leagues']}")
        logger.info(f"  成功联赛: {self.stats['successful']}")
        logger.info(f"  失败联赛: {self.stats['failed']}")
        logger.info(f"  总比赛数: {results['total_matches']:,}")
        logger.info(f"  采集时长: {duration_minutes:.1f} 分钟")
        logger.info(
            f"  平均速度: {results['total_matches']/duration_minutes:.1f} 场/分钟"
        )

        # 成功的联赛统计
        if results["successful"]:
            logger.info(f"\n✅ 成功联赛 (Top 20):")
            sorted_successful = sorted(
                results["successful"],
                key=lambda x: x["matches_collected"],
                reverse=True,
            )

            for i, league in enumerate(sorted_successful[:20], 1):
                seasons = ", ".join(league["seasons_collected"])
                logger.info(
                    f"  {i:2d}. {league['league_name']:40s} {league['matches_collected']:4d} 场 ({seasons})"
                )

        # 失败的联赛
        if results["failed"]:
            logger.info(f"\n❌ 失败联赛:")
            for league in results["failed"]:
                error = league["error"][:50] if league["error"] else "Unknown error"
                logger.info(f"  • {league['league_name']:40s} {error}")

        logger.info("=" * 80)

    def run(self):
        """运行完整的全域采集流程"""
        logger.info("🏁 FBref 全域采集启动")
        logger.info(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        # Step 1: 刷新联赛列表
        if not self.refresh_league_list():
            logger.error("❌ 联赛列表刷新失败，退出")
            return False

        # Step 2: 加载所有联赛
        leagues = self.get_all_leagues()
        if not leagues:
            logger.error("❌ 无联赛数据，退出")
            return False

        # Step 3: 并行采集
        results = self.run_parallel_collection(leagues)

        # Step 4: 打印报告
        self.print_final_report(results)

        return True


def main():
    """主函数"""
    launcher = TotalCoverageLauncher(max_workers=8)
    success = launcher.run()

    if success:
        logger.info("\n✅ 全域采集成功完成!")
        return 0
    else:
        logger.error("\n❌ 全域采集失败!")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
