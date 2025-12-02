#!/usr/bin/env python3
"""
FBref数据采集调度器
长期稳定的增量更新策略

Anti-Bot Security Researcher: 反爬虫对抗专家
Purpose: 生产环境调度配置
"""

import asyncio
import logging
import sys
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.collectors.fbref_collector_stealth import StealthFBrefCollector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class FBrefScheduler:
    """FBref数据采集调度器"""

    def __init__(self):
        self.collector = StealthFBrefCollector()

        # 当前赛季配置（根据年份动态调整）
        current_year = datetime.now().year
        current_month = datetime.now().month

        if current_month >= 8:  # 8月新赛季开始
            self.current_season = f"{current_year}-{current_year+1}"
            self.previous_season = f"{current_year-1}-{current_year}"
        else:  # 仍在上赛季
            self.current_season = f"{current_year-1}-{current_year}"
            self.previous_season = f"{current_year-2}-{current_year-1}"

        # 联赛配置
        self.leagues = self.collector.get_available_leagues()

    def get_optimal_schedule_times(self) -> List[Dict[str, any]]:
        """
        获取最优调度时间配置

        策略：
        1. 周一：更新周末比赛结果
        2. 周四：更新周中比赛结果
        3. 周日：检查即将进行的比赛
        4. 随机时间分散请求
        """

        schedules = []

        # 周一 06:00 UTC (欧洲比赛结束后)
        schedules.append(
            {
                "name": "weekend_results_update",
                "day": "monday",
                "hour": 6,
                "minute": random.randint(0, 30),
                "description": "更新周末比赛结果和xG数据",
                "seasons": [self.current_season],  # 只更新当前赛季
                "leagues": ["Premier League", "La Liga", "Bundesliga"],  # 优先主要联赛
            }
        )

        # 周四 06:00 UTC (周中比赛结束后)
        schedules.append(
            {
                "name": "midweek_results_update",
                "day": "thursday",
                "hour": 6,
                "minute": random.randint(15, 45),
                "description": "更新周中比赛结果",
                "seasons": [self.current_season],
                "leagues": [
                    "Premier League",
                    "La Liga",
                    "Serie A",
                    "Bundesliga",
                    "Ligue 1",
                ],
            }
        )

        # 周日 12:00 UTC (比赛前检查)
        schedules.append(
            {
                "name": "upcoming_matches_check",
                "day": "sunday",
                "hour": 12,
                "minute": random.randint(0, 30),
                "description": "检查即将进行的比赛",
                "seasons": [self.current_season],
                "leagues": ["Premier League", "La Liga"],  # 重点检查
            }
        )

        # 每月1号进行历史数据补全
        schedules.append(
            {
                "name": "historical_data_sync",
                "day": "1",  # 每月1号
                "hour": 3,  # 凌晨3点，低流量时段
                "minute": random.randint(0, 59),
                "description": "历史数据增量同步",
                "seasons": [self.previous_season],  # 只同步上赛季
                "leagues": ["Premier League"],  # 优先英超
            }
        )

        return schedules

    def generate_crontab_config(self) -> str:
        """生成Crontab配置"""
        schedules = self.get_optimal_schedule_times()

        crontab_content = """# FBref数据采集调度配置
# 由反爬虫对抗专家设计的生产级调度策略
# 所有时间均为UTC

"""

        for schedule in schedules:
            if schedule["day"] in [
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
                "friday",
                "saturday",
                "sunday",
            ]:
                day_map = {
                    "monday": 1,
                    "tuesday": 2,
                    "wednesday": 3,
                    "thursday": 4,
                    "friday": 5,
                    "saturday": 6,
                    "sunday": 0,
                }
                cron_day = day_map[schedule["day"]]
            else:  # 每月1号
                cron_day = 1

            minute = schedule["minute"]
            hour = schedule["hour"]

            # 构建crontab行
            crontab_line = f"{minute} {hour} {cron_day} * *"

            # Python命令
            python_cmd = f"cd {Path(__file__).parent.parent} && python3 -c "

            # 动态Python代码
            python_code = f"""
import asyncio
import sys
sys.path.insert(0, '{Path(__file__).parent.parent}')

from src.data.collectors.fbref_collector_stealth import StealthFBrefCollector

async def run_schedule():
    collector = StealthFBrefCollector()

    leagues = {schedule['leagues']}
    seasons = {schedule['seasons']}

    for league_name, league_url in collector.get_available_leagues().items():
        if league_name in leagues:
            print(f"📅 处理联赛: {{league_name}}")

            for season in seasons:
                data = await collector.get_season_schedule_stealth(league_url, season)
                print(f"✅ {{league_name}} {{season}}: {{len(data)}} 场比赛")

asyncio.run(run_schedule())
"""

            crontab_content += f"{crontab_line} {python_cmd}'{python_code}'\n"
            crontab_content += f"# {schedule['description']}\n\n"

        return crontab_content

    async def test_schedule(self):
        """测试调度逻辑"""
        logger.info("🧪 测试FBref调度逻辑")

        # 获取当前赛季信息
        logger.info(f"📅 当前赛季: {self.current_season}")
        logger.info(f"📅 上个赛季: {self.previous_season}")

        # 测试单次采集
        test_league = "Premier League"
        test_season = "2023-2024"  # 使用历史数据测试

        logger.info(f"🧪 测试采集: {test_league} {test_season}")

        try:
            data = await self.collector.get_season_schedule_stealth(
                self.leagues[test_league], test_season
            )

            if not data.empty:
                cleaned = self.collector._clean_schedule_data(data)
                completed = self.collector._filter_completed_matches(cleaned_data)

                logger.info(f"✅ 测试成功: {len(completed)} 场已完成比赛")

                # 显示示例数据
                if "xg_home" in completed.columns and "xg_away" in completed.columns:
                    sample = completed[
                        ["home", "away", "xg_home", "xg_away", "score"]
                    ].head(3)
                    logger.info("📊 数据示例:")
                    print(sample.to_string(index=False))

                return True
            else:
                logger.error("❌ 测试失败: 未获取到数据")
                return False

        except Exception as e:
            logger.error(f"❌ 测试异常: {e}")
            return False

    def save_crontab_config(self, filename: str = "fbref_crontab.txt"):
        """保存Crontab配置到文件"""
        crontab_content = self.generate_crontab_config()

        with open(filename, "w", encoding="utf-8") as f:
            f.write(crontab_content)

        logger.info(f"💾 Crontab配置已保存到: {filename}")

        # 显示配置内容
        logger.info("📋 Crontab配置预览:")
        print(crontab_content)


def main():
    """主函数"""
    logger.info("🚀 FBref调度器配置")

    scheduler = FBrefScheduler()

    # 显示调度策略
    logger.info("=" * 60)
    logger.info("📅 调度策略概览")
    logger.info("=" * 60)

    schedules = scheduler.get_optimal_schedule_times()
    for schedule in schedules:
        logger.info(f"📋 {schedule['name']}:")
        logger.info(
            f"   时间: {schedule['day']} {schedule['hour']:02d}:{schedule['minute']:02d} UTC"
        )
        logger.info(f"   描述: {schedule['description']}")
        logger.info(f"   赛季: {schedule['seasons']}")
        logger.info(f"   联赛: {schedule['leagues']}")
        logger.info("")

    # 生成和保存Crontab配置
    logger.info("🔧 生成Crontab配置...")
    scheduler.save_crontab_config()

    # 可选：测试调度逻辑
    test_schedule = input("\n🧪 是否测试调度逻辑? (y/n): ").lower().strip()
    if test_schedule == "y":
        logger.info("🧪 开始测试调度逻辑...")

        async def run_test():
            success = await scheduler.test_schedule()
            if success:
                logger.info("🎉 调度逻辑测试成功!")
            else:
                logger.error("❌ 调度逻辑测试失败!")

        asyncio.run(run_test())

    logger.info("✅ FBref调度器配置完成")


if __name__ == "__main__":
    main()
