#!/usr/bin/env python3
"""
英超专项采集器 - 精准打击行动
Premier League Specialist Collector - Precision Strike Operation

目标：专注采集英超2021-2024三个赛季约1000场比赛
确保模型训练所需的高质量数据
"""

import asyncio
import sys
import os
import time
import logging
from datetime import datetime
from pathlib import Path
# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.collectors.fbref_collector_stealth import StealthFBrefCollector
from scripts.fbref_database_saver import FBrefDatabaseSaver

logging.basicConfig(
    level=logging.INFO
    format="%(asctime)s - %(levelname)s - %(message)s"
    handlers=[
        logging.FileHandler("logs/premier_league_backfill.log")
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PremierLeagueBackfill:
    """英超专项采集器"""

    def __init__(self):
        # 英超配置
        self.premier_league_id = 2  # 数据库中英超联赛ID
        self.fbref_comp_id = 9  # FBref中英超competition ID

        # 赛季配置 - 精确的FBref URL
        self.seasons = {
            "2023-2024": {
                "url": "https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures"
                "season_id": "2023-2024"
            }
            "2022-2023": {
                "url": "https://fbref.com/en/comps/9/2022-2023/schedule/2022-2023-Premier-League-Scores-and-Fixtures"
                "season_id": "2022-2023"
            }
            "2021-2022": {
                "url": "https://fbref.com/en/comps/9/2021-2022/schedule/2021-2022-Premier-League-Scores-and-Fixtures"
                "season_id": "2021-2022"
            }
        }

        # 初始化组件
        self.collector = StealthFBrefCollector()
        self.saver = FBrefDatabaseSaver()

        # 统计信息
        self.stats = {
            "total_seasons": len(self.seasons)
            "completed_seasons": 0
            "total_matches": 0
            "successful_matches": 0
            "failed_seasons": []
            "start_time": datetime.now()
        }

        # 确保日志目录存在
        Path("logs").mkdir(exist_ok=True)

    async def collect_season(self, season_name: str, season_config: dict) -> bool:
        """
        采集单个赛季数据
        """
        url = season_config["url"]
        season_id = season_config["season_id"]

        logger.info(f"🏆 开始采集 {season_name} 赛季")
        logger.info(f"🔗 URL: {url}")

        try:
            # 智能延迟 - 避免反爬
            delay = 3 + (len(self.stats["failed_seasons"]) * 2)  # 失败越多，延迟越长
            logger.info(f"⏱️ 智能延迟 {delay} 秒...")
            await asyncio.sleep(delay)

            # 执行采集
            logger.info("📡 连接FBref服务器...")
            season_data = await self.collector.get_season_schedule_stealth(url)

            if season_data is None or season_data.empty:
                logger.error(f"❌ {season_name}: 无数据返回")
                self.stats["failed_seasons"].append(season_name)
                return False

            logger.info(f"📊 {season_name}: 原始数据 {len(season_data)} 条记录")

            # 转换DataFrame为字典列表
            try:
                season_data_dict = season_data.to_dict("records")
            except Exception as e:
                logger.error(f"❌ {season_name}: 数据转换失败 - {e}")
                self.stats["failed_seasons"].append(season_name)
                return False

            # 数据清洗和验证
            logger.info("🧹 数据清洗和验证...")
            cleaned_data = self._validate_and_clean_data(season_data_dict, season_name)

            if not cleaned_data:
                logger.error(f"❌ {season_name}: 清洗后无有效数据")
                self.stats["failed_seasons"].append(season_name)
                return False

            logger.info(f"✅ {season_name}: 有效数据 {len(cleaned_data)} 场比赛")

            # 数据入库
            logger.info("💾 开始数据入库...")
            success = await self._save_to_database(cleaned_data, season_name, season_id)

            if success:
                self.stats["completed_seasons"] += 1
                self.stats["total_matches"] += len(cleaned_data)
                self.stats["successful_matches"] += len(cleaned_data)

                logger.info(
                    f"🎉 {season_name}: 采集完成! {len(cleaned_data)} 场比赛已入库"
                )
                return True
            else:
                logger.error(f"❌ {season_name}: 数据入库失败")
                self.stats["failed_seasons"].append(season_name)
                return False

        except Exception as e:
            logger.error(f"❌ {season_name}: 采集异常 - {e}")
            self.stats["failed_seasons"].append(season_name)
            import traceback

            traceback.print_exc()
            return False

    def _validate_and_clean_data(
        self, data: list[dict], season_name: str
    ) -> list[dict]:
        """
        数据验证和清洗
        """
        if not data:
            return []

        cleaned_data = []

        for match in data:
            try:
                # 基本字段验证
                if not match.get("home_team") or not match.get("away_team"):
                    continue

                # 赛季标记
                match["season"] = season_name
                match["league_id"] = self.premier_league_id

                # 状态标记 - 只有已完成的比赛
                if match.get("status", "").lower() not in ["completed", "final"]:
                    logger.debug(
                        f"跳过未完成比赛: {match.get('home_team')} vs {match.get('away_team')}"
                    )
                    continue

                # 确保有比赛日期
                if not match.get("date"):
                    continue

                cleaned_data.append(match)

            except Exception as e:
                logger.warning(f"数据清洗异常，跳过记录: {e}")
                continue

        logger.info(f"🔍 {season_name}: {len(data)} → {len(cleaned_data)} 条有效记录")
        return cleaned_data

    async def _save_to_database(
        self, data: list[dict], season_name: str, season_id: str
    ) -> bool:
        """
        保存数据到数据库
        """
        try:
            # 使用现成的数据库保存器
            logger.info(f"💾 调用FBrefDatabaseSaver保存 {len(data)} 场比赛...")

            success_count = await self.saver.save_matches(data, self.premier_league_id)

            if success_count > 0:
                logger.info(
                    f"✅ {season_name}: 成功保存 {success_count}/{len(data)} 场比赛"
                )
                return True
            else:
                logger.error(f"❌ {season_name}: 没有比赛被成功保存")
                return False

        except Exception as e:
            logger.error(f"❌ {season_name}: 数据库保存异常 - {e}")
            import traceback

            traceback.print_exc()
            return False

    def print_final_report(self):
        """打印最终报告"""
        end_time = datetime.now()
        duration = end_time - self.stats["start_time"]

        logger.info("\n" + "=" * 80)
        logger.info("🎯 英超专项采集任务完成!")
        logger.info("=" * 80)

        logger.info("\n📊 采集统计:")
        logger.info(f"  目标赛季: {self.stats['total_seasons']} 个")
        logger.info(f"  成功赛季: {self.stats['completed_seasons']} 个")
        logger.info(f"  失败赛季: {len(self.stats['failed_seasons'])} 个")
        logger.info(f"  总比赛数: {self.stats['total_matches']}")
        logger.info(
            f"  成功率: {(self.stats['completed_seasons']/self.stats['total_seasons'])*100:.1f}%"
        )
        logger.info(f"  采集时长: {duration.total_seconds()/60:.1f} 分钟")

        if self.stats["failed_seasons"]:
            logger.info("\n❌ 失败赛季:")
            for season in self.stats["failed_seasons"]:
                logger.info(f"  - {season}")

        logger.info("\n🎯 模型训练数据准备情况:")
        expected_matches = 38 * 20 * 3  # 3赛季 * 20队 * 38场比赛
        actual_matches = self.stats["total_matches"]
        coverage = (
            (actual_matches / expected_matches) * 100 if expected_matches > 0 else 0
        )

        logger.info(f"  期望比赛: {expected_matches} 场")
        logger.info(f"  实际比赛: {actual_matches} 场")
        logger.info(f"  数据覆盖率: {coverage:.1f}%")

        if coverage >= 80:
            logger.info("  ✅ 数据充足，适合模型训练!")
        elif coverage >= 50:
            logger.info("  ⚠️ 数据基本够用，建议补充")
        else:
            logger.info("  ❌ 数据不足，需要进一步采集")

        logger.info("=" * 80)

    async def run_backfill(self):
        """执行回填任务"""
        logger.info("🚀 英超专项采集器启动")
        logger.info("目标: 采集3个赛季约1000场英超比赛")
        logger.info(
            f"开始时间: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}"
        )
        logger.info("=" * 80)

        # 按赛季顺序采集
        season_order = ["2023-2024", "2022-2023", "2021-2022"]

        for i, season_name in enumerate(season_order):
            if season_name not in self.seasons:
                logger.warning(f"⚠️ 跳过未配置的赛季: {season_name}")
                continue

            season_config = self.seasons[season_name]

            logger.info(
                f"\n📈 进度: {i+1}/{len(season_order)} ({((i+1)/len(season_order))*100:.1f}%)"
            )

            await self.collect_season(season_name, season_config)

            # 赛季间休息 - 避免被封
            if i < len(season_order) - 1:
                rest_time = 60  # 60秒休息
                logger.info(f"😴 赛季间休息 {rest_time} 秒...")
                await asyncio.sleep(rest_time)

        # 生成最终报告
        self.print_final_report()

        return self.stats["completed_seasons"] > 0


def main():
    """主函数"""
    try:
        # 确保日志目录
        Path("logs").mkdir(exist_ok=True)

        # 启动英超专项采集器
        backfill = PremierLeagueBackfill()
        success = asyncio.run(backfill.run_backfill())

        return 0 if success else 1

    except KeyboardInterrupt:
        logger.info("\n🛑 用户中断采集")
        return 130
    except Exception as e:
        logger.error(f"❌ 采集过程异常: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
