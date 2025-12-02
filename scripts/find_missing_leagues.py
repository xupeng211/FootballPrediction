#!/usr/bin/env python3
"""
查找缺失联赛脚本 - 数据治理工程师专用
对比CSV文件和原始采集目标，找出未完成的联赛
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Set

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_completed_leagues() -> Set[str]:
    """获取已完成的联赛ID"""
    csv_dir = Path("data/fbref")
    completed_leagues = set()

    if csv_dir.exists():
        for csv_file in csv_dir.glob("*.csv"):
            # 从文件名提取联赛ID: "Premier-League_all_seasons_matches.csv" -> "Premier-League"
            league_id = csv_file.stem.replace("_all_seasons_matches", "")
            completed_leagues.add(league_id)

    return completed_leagues


def get_all_target_leagues() -> List[tuple]:
    """获取所有目标联赛"""
    return [
        # Premier League and related competitions
        (
            "Premier-League",
            "Premier League",
            "https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures",
        ),
        (
            "Championship",
            "Championship",
            "https://fbref.com/en/comps/10/schedule/Championship-Scores-and-Fixtures",
        ),
        (
            "League-One",
            "League One",
            "https://fbref.com/en/comps/13/schedule/League-One-Scores-and-Fixtures",
        ),
        (
            "League-Two",
            "League Two",
            "https://fbref.com/en/comps/14/schedule/League-Two-Scores-and-Fixtures",
        ),
        (
            "National-League",
            "National League",
            "https://fbref.com/en/comps/34/schedule/National-League-Scores-and-Fixtures",
        ),
        # Major European Leagues
        (
            "La-Liga",
            "La Liga",
            "https://fbref.com/en/comps/12/schedule/La-Liga-Scores-and-Fixtures",
        ),
        (
            "Serie-A",
            "Serie A",
            "https://fbref.com/en/comps/11/schedule/Serie-A-Scores-and-Fixtures",
        ),
        (
            "Bundesliga",
            "Bundesliga",
            "https://fbref.com/en/comps/20/schedule/Bundesliga-Scores-and-Fixtures",
        ),
        (
            "Ligue-1",
            "Ligue 1",
            "https://fbref.com/en/comps/13/schedule/Ligue-1-Scores-and-Fixtures",
        ),
        # Major European Second Divisions
        (
            "Segunda-Division",
            "Segunda División",
            "https://fbref.com/en/comps/11/schedule/Segunda-Division-Scores-and-Fixtures",
        ),
        (
            "Serie-B",
            "Serie B",
            "https://fbref.com/en/comps/12/schedule/Serie-B-Scores-and-Fixtures",
        ),
        (
            "2-Bundesliga",
            "2. Bundesliga",
            "https://fbref.com/en/comps/33/schedule/2-Bundesliga-Scores-and-Fixtures",
        ),
        (
            "Ligue-2",
            "Ligue 2",
            "https://fbref.com/en/comps/17/schedule/Ligue-2-Scores-and-Fixtures",
        ),
        # UEFA Competitions
        (
            "Champions-League",
            "UEFA Champions League",
            "https://fbref.com/en/comps/8/schedule/Champions-League-Scores-and-Fixtures",
        ),
        (
            "Europa-League",
            "UEFA Europa League",
            "https://fbref.com/en/comps/19/schedule/Europa-League-Scores-and-Fixtures",
        ),
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
        # South American Competitions
        (
            "Libertadores",
            "Copa Libertadores",
            "https://fbref.com/en/comps/23/schedule/Copa-Libertadores-Scores-and-Fixtures",
        ),
        (
            "Sudamericana",
            "Copa Sudamericana",
            "https://fbref.com/en/comps/24/schedule/Copa-Sudamericana-Scores-and-Fixtures",
        ),
        # CONCACAF Competitions
        (
            "MLS",
            "MLS",
            "https://fbref.com/en/comps/22/schedule/MLS-Scores-and-Fixtures",
        ),
        (
            "Liga-MX",
            "Liga MX",
            "https://fbref.com/en/comps/32/schedule/Liga-MX-Scores-and-Fixtures",
        ),
        # Asian Competitions
        (
            "J1-League",
            "J1 League",
            "https://fbref.com/en/comps/25/schedule/J1-League-Scores-and-Fixtures",
        ),
        (
            "K-League-1",
            "K League 1",
            "https://fbref.com/en/comps/55/schedule/K-League-1-Scores-and-Fixtures",
        ),
        (
            "Chinese-Super-League",
            "Chinese Super League",
            "https://fbref.com/en/comps/32/schedule/Chinese-Super-League-Scores-and-Fixtures",
        ),
        # African Competitions
        (
            "CAF-Champions-League",
            "CAF Champions League",
            "https://fbref.com/en/comps/79/schedule/CAF-Champions-League-Scores-and-Fixtures",
        ),
        # International Competitions
        (
            "World-Cup",
            "FIFA World Cup",
            "https://fbref.com/en/comps/45/schedule/World-Cup-Scores-and-Fixtures",
        ),
        (
            "Copa-America",
            "Copa América",
            "https://fbref.com/en/comps/47/schedule/Copa-America-Scores-and-Fixtures",
        ),
        (
            "Euros",
            "UEFA European Championship",
            "https://fbref.com/en/comps/676/schedule/Euros-Scores-and-Fixtures",
        ),
        (
            "Africa-Cup-of-Nations",
            "Africa Cup of Nations",
            "https://fbref.com/en/comps/82/schedule/Africa-Cup-of-Nations-Scores-and-Fixtures",
        ),
        (
            "Asian-Cup",
            "AFC Asian Cup",
            "https://fbref.com/en/comps/471/schedule/Asian-Cup-Scores-and-Fixtures",
        ),
        (
            "Gold-Cup",
            "CONCACAF Gold Cup",
            "https://fbref.com/en/comps/49/schedule/Gold-Cup-Scores-and-Fixtures",
        ),
        # Youth International Competitions
        (
            "U20-World-Cup",
            "FIFA U-20 World Cup",
            "https://fbref.com/en/comps/48/schedule/U20-World-Cup-Scores-and-Fixtures",
        ),
        (
            "U17-World-Cup",
            "FIFA U-17 World Cup",
            "https://fbref.com/en/comps/44/schedule/U17-World-Cup-Scores-and-Fixtures",
        ),
        # Women's Competitions
        (
            "NWSL",
            "NWSL",
            "https://fbref.com/en/comps/102/schedule/NWSL-Scores-and-Fixtures",
        ),
        (
            "WSL",
            "Women's Super League",
            "https://fbref.com/en/comps/189/schedule/WSL-Scores-and-Fixtures",
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


def main():
    """主函数"""
    logger.info("🔍 查找缺失联赛...")

    completed = get_completed_leagues()
    all_targets = get_all_target_leagues()

    logger.info(f"✅ 已完成联赛数量: {len(completed)}")
    logger.info(f"📋 目标联赛总数: {len(all_targets)}")

    # 找出缺失的联赛
    missing_leagues = []
    for league_id, league_name, league_url in all_targets:
        if league_id not in completed:
            missing_leagues.append((league_id, league_name, league_url))

    logger.info(f"❌ 缺失联赛数量: {len(missing_leagues)}")

    if missing_leagues:
        logger.info("\n🚨 缺失联赛列表:")
        for i, (league_id, league_name, league_url) in enumerate(missing_leagues, 1):
            logger.info(f"  {i:2d}. {league_name:25s} ({league_id})")
            logger.info(f"      URL: {league_url}")

        # 生成专用的采集脚本
        generate_missing_leagues_script(missing_leagues)

        logger.info(f"\n💡 已生成专用采集脚本: scripts/collect_missing_leagues.py")
        logger.info("🔧 运行命令: python scripts/collect_missing_leagues.py")
    else:
        logger.info("\n🎉 所有联赛采集完成！")


def generate_missing_leagues_script(missing_leagues: List[tuple]):
    """生成缺失联赛的专用采集脚本"""
    script_content = f'''#!/usr/bin/env python3
"""
缺失联赛专用采集器
自动生成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
目标: 采集 {len(missing_leagues)} 个缺失的联赛
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
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/missing_leagues_collection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MissingLeaguesCollector:
    """缺失联赛采集器"""

    def __init__(self):
        self.progress_file = "logs/missing_leagues_progress.json"
        self.failed_log_file = "logs/missing_failed_leagues.log"
        self.completed_leagues: set = set()
        self.failed_leagues: list = []

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
                with open(self.progress_file, 'r') as f:
                    data = json.load(f)
                    self.completed_leagues = set(data.get('completed_leagues', []))
                    self.failed_leagues = data.get('failed_leagues', [])
                logger.info(f"加载进度：已完成 {len(self.completed_leagues)} 个联赛")
        except Exception as e:
            logger.warning(f"加载进度失败：{{e}}")

    def _save_progress(self):
        """保存进度"""
        try:
            progress_data = {{
                'completed_leagues': list(self.completed_leagues),
                'failed_leagues': self.failed_leagues,
                'last_update': datetime.now().isoformat()
            }}
            with open(self.progress_file, 'w') as f:
                json.dump(progress_data, f, indent=2)
        except Exception as e:
            logger.error(f"保存进度失败：{{e}}")

    async def _collect_single_league(self, league_id: str, league_name: str, league_url: str) -> bool:
        """采集单个联赛"""
        try:
            logger.info(f"🔄 开始采集联赛: {{league_name}} ({{league_id}})")

            # 使用隐身模式采集赛程数据
            schedule_data = await self.collector.get_season_schedule_stealth(league_url, None)

            if schedule_data is not None and not schedule_data.empty:
                matches_count = len(schedule_data)
                logger.info(f"✅ 联赛采集完成: {{matches_count}} 场比赛")

                # 保存到CSV文件
                output_file = f"data/fbref/{{league_id}}_all_seasons_matches.csv"
                schedule_data.to_csv(output_file, index=False)
                logger.info(f"💾 数据已保存到: {{output_file}}")

                self.completed_leagues.add(league_id)
                self._save_progress()
                return True
            else:
                raise Exception("未采集到任何比赛数据")

        except Exception as e:
            logger.error(f"❌ 联赛采集失败: {{league_name}} ({{league_id}}) - {{e}}")
            self.failed_leagues.append({{
                'league_id': league_id,
                'league_name': league_name,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }})
            self._save_progress()
            return False

    async def run(self):
        """执行采集"""
        logger.info(f"🚀 开始缺失联赛采集，目标: {len(missing_leagues)} 个联赛")

        missing_data = {missing_leagues}

        for i, (league_id, league_name, league_url) in enumerate(missing_data):
            # 跳过已完成的联赛
            if league_id in self.completed_leagues:
                logger.info(f"⏭️ 跳过已完成联赛: {{league_name}}")
                continue

            progress_percent = ((len(self.completed_leagues)) / len(missing_data)) * 100
            logger.info(f"📊 进度: {{len(self.completed_leagues)}}/{{len(missing_data)}} ({{progress_percent:.1f}}%)")

            # 采集联赛
            success = await self._collect_single_league(league_id, league_name, league_url)

            # 联赛间休眠15-30秒
            if i < len(missing_data) - 1:
                wait_time = random.randint(15, 30)
                logger.info(f"⏱️ 休眠 {{wait_time}} 秒...")
                await asyncio.sleep(wait_time)

        # 最终统计
        logger.info("🎉 缺失联赛采集任务完成！")
        logger.info(f"✅ 成功采集: {{len(self.completed_leagues)}} 个联赛")
        logger.info(f"❌ 失败联赛: {{len(self.failed_leagues)}} 个联赛")


async def main():
    """主函数"""
    collector = MissingLeaguesCollector()
    await collector.run()


if __name__ == "__main__":
    asyncio.run(main())
'''

    # 写入脚本文件
    with open("scripts/collect_missing_leagues.py", "w", encoding="utf-8") as f:
        f.write(script_content)

    # 添加执行权限
    Path("scripts/collect_missing_leagues.py").chmod(0o755)


if __name__ == "__main__":
    main()
