#!/usr/bin/env python3
"""
FBref历史数据回填任务
运营总监部署版本

Operations Director: 生产级数据管道部署
Purpose: 过去3个赛季全量数据回填
"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.collectors.fbref_collector import FBrefCollector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def run_historical_backfill():
    """执行历史数据回填"""
    start_time = time.time()
    logger.info("🚀 FBref历史数据回填任务启动")
    logger.info("=" * 80)

    collector = FBrefCollector()

    # 配置目标联赛和赛季
    target_leagues = {
        "Premier League": "https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures",
        "La Liga": "https://fbref.com/en/comps/12/schedule/La-Liga-Scores-and-Fixtures",
        "Serie A": "https://fbref.com/en/comps/11/schedule/Serie-A-Scores-and-Fixtures",
        "Bundesliga": "https://fbref.com/en/comps/20/schedule/Bundesliga-Scores-and-Fixtures",
        "Ligue 1": "https://fbref.com/en/comps/13/schedule/Ligue-1-Scores-and-Fixtures",
    }

    seasons = ["2022-2023", "2023-2024", "2024-2025"]  # 过去3个赛季

    total_matches = 0
    successful_leagues = 0

    logger.info("📊 目标数据范围:")
    logger.info(f"   联赛数量: {len(target_leagues)} 个")
    logger.info(f"   赛季范围: {len(seasons)} 个 ({', '.join(seasons)})")
    logger.info(f"   总任务数: {len(target_leagues) * len(seasons)} 个联赛-赛季组合")
    logger.info("")

    for league_name, league_url in target_leagues.items():
        logger.info(f"🏆 处理联赛: {league_name}")
        league_success = False

        for season in seasons:
            task_start = time.time()
            logger.info(f"   📅 赛季: {season}")

            try:
                # 使用隐身模式采集
                data = await collector.get_season_schedule(league_url, season)

                if not data.empty:
                    # 清洗数据
                    cleaned_data = collector._clean_schedule_data(data)
                    completed_matches = collector._filter_completed_matches(
                        cleaned_data
                    )

                    match_count = len(completed_matches)
                    total_matches += match_count

                    task_time = time.time() - task_start
                    logger.info(
                        f"   ✅ 成功: {match_count} 场比赛 (耗时 {task_time:.1f}s)"
                    )

                    # 检查xG数据质量
                    if (
                        "xg_home" in completed_matches.columns
                        and "xg_away" in completed_matches.columns
                    ):
                        xg_valid = (
                            completed_matches[["xg_home", "xg_away"]]
                            .notna()
                            .all(axis=1)
                            .sum()
                        )
                        logger.info(
                            f"   📈 xG数据质量: {xg_valid}/{match_count} ({xg_valid/match_count*100:.1f}%)"
                        )

                    league_success = True

                else:
                    logger.error(f"   ❌ 失败: 未获取到数据")

                # 赛季间延迟 (避免反爬检测)
                if season != seasons[-1]:
                    delay = collector._get_random_delay(15.0, 45.0)
                    logger.info(f"   ⏳ 延迟 {delay:.1f}s...")
                    await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"   ❌ 异常: {e}")

        if league_success:
            successful_leagues += 1
            logger.info(f"🎉 联赛 {league_name} 完成")
        else:
            logger.error(f"💥 联赛 {league_name} 失败")

        # 联赛间延迟 (更重要，避免IP封锁)
        if league_name != list(target_leagues.keys())[-1]:
            delay = collector._get_random_delay(60.0, 180.0)  # 1-3分钟
            logger.info(f"🔄 联赛间延迟 {delay:.1f}s...")
            await asyncio.sleep(delay)

    # 任务总结
    total_time = time.time() - start_time
    hours = total_time / 3600

    logger.info("")
    logger.info("=" * 80)
    logger.info("🎉 FBref历史数据回填任务完成!")
    logger.info("=" * 80)
    logger.info(f"📊 最终统计:")
    logger.info(f"   成功联赛: {successful_leagues}/{len(target_leagues)}")
    logger.info(f"   总比赛数: {total_matches:,}")
    logger.info(f"   总耗时: {total_time/60:.1f} 分钟 ({hours:.2f} 小时)")
    logger.info(f"   平均每场: {total_time/max(1, total_matches):.2f} 秒")

    if total_matches > 0:
        logger.info(f"📈 数据采集速率: {total_matches/hours:.0f} 场/小时")
        logger.info("✅ 数据已准备好导入ML管道")

        # 计算数据完整性
        expected_matches = (
            len(target_leagues) * len(seasons) * 380
        )  # 估算每赛季380场比赛
        completeness = (total_matches / expected_matches) * 100
        logger.info(f"📊 数据完整性: {completeness:.1f}% (预期 {expected_matches} 场)")

    logger.info("=" * 80)

    return total_matches > 0


async def main():
    """主函数"""
    logger.info("🏭 FBref数据工厂 - 历史回填模式")
    logger.info(f"🕐 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        success = await run_historical_backfill()

        if success:
            logger.info("🎯 任务成功: 数据采集完成，可以开始模型训练")
            sys.exit(0)
        else:
            logger.error("💥 任务失败: 未采集到有效数据")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.warning("⚠️ 任务被用户中断")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 任务异常: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
