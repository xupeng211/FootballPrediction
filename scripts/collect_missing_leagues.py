#!/usr/bin/env python3
"""
缺失联赛专用采集器
目标: 采集9个缺失的联赛
"""

import asyncio
import json
import logging
import random
import sys
from datetime import datetime
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.collectors.fbref_collector_stealth import StealthFBrefCollector

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/missing_leagues_collection.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


# 缺失的联赛数据
MISSING_LEAGUES = [
    (
        "Europa-Conference-League",
        "UEFA Europa Conference League",
        "https://fbref.com/en/comps/871/schedule/Europa-Conference-League-Scores-and-Fixtures",
    ),
    (
        "Super-Cup",
        "UEFA Super Cup",
        "https://fbref.com/en/comps/245/schedule/Super-Cup-Scores-and-Fixtures",
    ),
    (
        "CAF-Champions-League",
        "CAF Champions League",
        "https://fbref.com/en/comps/79/schedule/CAF-Champions-League-Scores-and-Fixtures",
    ),
    (
        "Euros",
        "UEFA European Championship",
        "https://fbref.com/en/comps/676/schedule/Euros-Scores-and-Fixtures",
    ),
    (
        "Asian-Cup",
        "AFC Asian Cup",
        "https://fbref.com/en/comps/471/schedule/Asian-Cup-Scores-and-Fixtures",
    ),
    (
        "NWSL",
        "NWSL",
        "https://fbref.com/en/comps/102/schedule/NWSL-Scores-and-Fixtures",
    ),
    (
        "Division-1-Feminine",
        "Division 1 Féminine",
        "https://fbref.com/en/comps/169/schedule/Division-1-Feminine-Scores-and-Fixtures",
    ),
    (
        "FIFA-Womens-World-Cup",
        "FIFA Women's World Cup",
        "https://fbref.com/en/comps/106/schedule/FIFA-Womens-World-Cup-Scores-and-Fixtures",
    ),
    (
        "Womens-Euros",
        "UEFA Women's European Championship",
        "https://fbref.com/en/comps/133/schedule/Womens-Euros-Scores-and-Fixtures",
    ),
]


class MissingLeaguesCollector:
    """缺失联赛采集器"""

    def __init__(self):
        self.progress_file = "logs/missing_leagues_progress.json"
        self.completed_leagues = set()

        # 创建必要的目录
        Path("logs").mkdir(exist_ok=True)
        Path("data/fbref").mkdir(parents=True, exist_ok=True)

        # 加载进度
        self._load_progress()

        # FBref收集器
        self.collector = StealthFBrefCollector()

    def _load_progress(self):
        """加载进度"""
        try:
            if Path(self.progress_file).exists():
                with open(self.progress_file, "r") as f:
                    data = json.load(f)
                    self.completed_leagues = set(data.get("completed_leagues", []))
                logger.info(f"加载进度：已完成 {len(self.completed_leagues)} 个联赛")
        except Exception as e:
            logger.warning(f"加载进度失败：{e}")

    def _save_progress(self):
        """保存进度"""
        try:
            progress_data = {
                "completed_leagues": list(self.completed_leagues),
                "last_update": datetime.now().isoformat(),
            }
            with open(self.progress_file, "w") as f:
                json.dump(progress_data, f, indent=2)
        except Exception as e:
            logger.error(f"保存进度失败：{e}")

    async def _collect_single_league(
        self, league_id: str, league_name: str, league_url: str
    ) -> bool:
        """采集单个联赛"""
        try:
            logger.info(f"🔄 开始采集联赛: {league_name} ({league_id})")

            # 使用隐身模式采集赛程数据
            schedule_data = await self.collector.get_season_schedule_stealth(
                league_url, None
            )

            if schedule_data is not None and not schedule_data.empty:
                matches_count = len(schedule_data)
                logger.info(f"✅ 联赛采集完成: {matches_count} 场比赛")

                # 显示数据列信息
                logger.info(f"📋 数据列：{list(schedule_data.columns)}")

                # 保存到CSV文件
                output_file = f"data/fbref/{league_id}_all_seasons_matches.csv"
                schedule_data.to_csv(output_file, index=False)
                logger.info(f"💾 数据已保存到：{output_file}")

                self.completed_leagues.add(league_id)
                self._save_progress()
                return True
            else:
                raise Exception("未采集到任何比赛数据")

        except Exception as e:
            logger.error(f"❌ 联赛采集失败: {league_name} ({league_id}) - {e}")
            return False

    async def run(self):
        """执行采集"""
        logger.info(f"🚀 开始缺失联赛采集，目标: {len(MISSING_LEAGUES)} 个联赛")

        for i, (league_id, league_name, league_url) in enumerate(MISSING_LEAGUES):
            # 跳过已完成的联赛
            if league_id in self.completed_leagues:
                logger.info(f"⏭️ 跳过已完成联赛: {league_name}")
                continue

            progress_percent = (
                len(self.completed_leagues) / len(MISSING_LEAGUES)
            ) * 100
            logger.info(
                f"📊 进度: {len(self.completed_leagues)}/{len(MISSING_LEAGUES)} ({progress_percent:.1f}%)"
            )

            # 采集联赛
            success = await self._collect_single_league(
                league_id, league_name, league_url
            )

            # 联赛间休眠15-30秒
            if i < len(MISSING_LEAGUES) - 1:
                wait_time = random.randint(15, 30)
                logger.info(f"⏱️ 休眠 {wait_time} 秒...")
                await asyncio.sleep(wait_time)

        # 最终统计
        logger.info("🎉 缺失联赛采集任务完成！")
        logger.info(f"✅ 成功采集: {len(self.completed_leagues)} 个联赛")
        logger.info(
            f"❌ 失败联赛: {len(MISSING_LEAGUES) - len(self.completed_leagues)} 个联赛"
        )


async def main():
    """主函数"""
    collector = MissingLeaguesCollector()
    await collector.run()


if __name__ == "__main__":
    asyncio.run(main())
