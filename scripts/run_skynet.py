#!/usr/bin/env python3
"""
天网计划 - Step 4: 启动全球数据采集
Project Skynet - Step 4: Global Data Collection Launcher

执行完整的天网计划：构建索引 → 批量采集豪门球队历史数据
"""

import asyncio
import sys
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import json

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.index_competitions import WorldCompetitionsIndexer
from scripts.index_elite_teams import EliteTeamsIndexer
from src.data.collectors.fbref_team_history_collector import TeamHistoryOmniScraper, get_global_scraper
from sqlalchemy import create_engine, text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/skynet_launcher.log"),
        logging.StreamHandler()
    ],
)
logger = logging.getLogger(__name__)


class SkynetLauncher:
    """天网计划启动器"""

    def __init__(self):
        self.engine = create_engine("postgresql://postgres@db:5432/football_prediction")
        self.scraper = get_global_scraper()

        # 采集配置
        self.config = {
            'max_concurrent_teams': 3,  # 最大并发球队数
            'delay_between_teams': 15,  # 球队间延迟（秒）
            'delay_after_error': 30,    # 错误后延迟（秒）
            'retry_attempts': 3,        # 重试次数
        }

        # 统计信息
        self.stats = {
            'start_time': None,
            'end_time': None,
            'total_teams': 0,
            'processed_teams': 0,
            'successful_teams': 0,
            'failed_teams': 0,
            'total_matches': 0,
            'total_new_leagues': 0,
            'errors': []
        }

    async def step1_build_competitions_index(self) -> bool:
        """Step 1: 构建世界赛事索引"""
        logger.info("\n" + "="*80)
        logger.info("🌍 Step 1: 构建世界赛事索引")
        logger.info("="*80)

        try:
            indexer = WorldCompetitionsIndexer()
            success = await indexer.run()

            if success:
                logger.info("✅ Step 1 完成: 世界赛事索引构建成功")
                return True
            else:
                logger.error("❌ Step 1 失败: 世界赛事索引构建失败")
                return False

        except Exception as e:
            logger.error(f"❌ Step 1 执行异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def step2_build_teams_index(self) -> bool:
        """Step 2: 构建豪门球队索引"""
        logger.info("\n" + "="*80)
        logger.info("⚽ Step 2: 构建豪门球队索引")
        logger.info("="*80)

        try:
            indexer = EliteTeamsIndexer()
            success = await indexer.run()

            if success:
                logger.info("✅ Step 2 完成: 豪门球队索引构建成功")
                return True
            else:
                logger.error("❌ Step 2 失败: 豪门球队索引构建失败")
                return False

        except Exception as e:
            logger.error(f"❌ Step 2 执行异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_target_teams(self) -> List[Dict]:
        """获取目标采集球队列表"""
        logger.info("\n📋 获取目标采集球队列表...")

        try:
            with self.engine.connect() as conn:
                # 获取五大联赛球队，按国家分组
                teams = conn.execute(text("""
                    SELECT id, name, country, fbref_url, fbref_external_id
                    FROM teams
                    WHERE country IN ('England', 'Spain', 'Germany', 'Italy', 'France')
                    AND fbref_url IS NOT NULL
                    ORDER BY country, name
                """)).fetchall()

                team_list = []
                for team in teams:
                    team_info = {
                        'id': team.id,
                        'name': team.name,
                        'country': team.country,
                        'fbref_url': team.fbref_url,
                        'fbref_id': team.fbref_external_id
                    }
                    team_list.append(team_info)

                # 按国家分组统计
                countries = {}
                for team in team_list:
                    country = team['country']
                    if country not in countries:
                        countries[country] = []
                    countries[country].append(team)

                logger.info(f"\n📊 目标球队统计:")
                for country, teams in countries.items():
                    logger.info(f"  {country}: {len(teams)} 支球队")

                self.stats['total_teams'] = len(team_list)
                return team_list

        except Exception as e:
            logger.error(f"❌ 获取目标球队失败: {e}")
            return []

    async def step3_batch_scrape_teams(self, teams: List[Dict]) -> bool:
        """Step 3: 批量采集球队历史数据"""
        logger.info("\n" + "="*80)
        logger.info("🚀 Step 3: 批量采集球队历史数据")
        logger.info(f"目标: {len(teams)} 支球队")
        logger.info("="*80)

        # 创建信号量限制并发数
        semaphore = asyncio.Semaphore(self.config['max_concurrent_teams'])

        async def scrape_single_team(team: Dict) -> Dict:
            """采集单个球队数据"""
            async with semaphore:
                team_name = team['name']
                fbref_url = team['fbref_url']

                logger.info(f"\n🎯 开始采集: {team_name} ({team['country']})")
                logger.info(f"URL: {fbref_url}")

                try:
                    # 采集球队数据
                    stats = await self.scraper.scrape_team_history(team_name, fbref_url)

                    # 更新全局统计
                    self.stats['processed_teams'] += 1
                    self.stats['total_matches'] += stats['saved_matches']
                    self.stats['total_new_leagues'] += stats['new_leagues']

                    if stats['saved_matches'] > 0:
                        self.stats['successful_teams'] += 1
                        logger.info(f"  ✅ 成功: {stats['saved_matches']} 场比赛, {stats['new_leagues']} 新联赛")
                    else:
                        self.stats['failed_teams'] += 1
                        logger.warning(f"  ⚠️ 未获取到数据")

                    return {
                        'team': team_name,
                        'status': 'success',
                        'matches': stats['saved_matches'],
                        'leagues': stats['new_leagues']
                    }

                except Exception as e:
                    self.stats['processed_teams'] += 1
                    self.stats['failed_teams'] += 1
                    error_msg = f"采集失败 {team_name}: {e}"

                    logger.error(f"  ❌ {error_msg}")
                    self.stats['errors'].append(error_msg)

                    return {
                        'team': team_name,
                        'status': 'error',
                        'error': str(e)
                    }

                finally:
                    # 采集完成后等待，避免请求过快
                    logger.info(f"  ⏳ 等待 {self.config['delay_between_teams']} 秒...")
                    await asyncio.sleep(self.config['delay_between_teams'])

        # 并发采集
        logger.info(f"\n🚀 开始并发采集 (最大 {self.config['max_concurrent_teams']} 个线程)")

        results = await asyncio.gather(
            *[scrape_single_team(team) for team in teams],
            return_exceptions=True
        )

        # 处理结果
        success_count = sum(1 for r in results if isinstance(r, dict) and r.get('status') == 'success')
        error_count = len(results) - success_count

        logger.info(f"\n✅ Step 3 完成:")
        logger.info(f"  成功球队: {success_count}/{len(teams)}")
        logger.info(f"  失败球队: {error_count}")
        logger.info(f"  总比赛数: {self.stats['total_matches']}")
        logger.info(f"  新增联赛: {self.stats['total_new_leagues']}")

        return success_count > 0

    async def run_full_skynet(self) -> bool:
        """执行完整的天网计划"""
        logger.info("🌍" * 80)
        logger.info("🚀 天网计划 (Project Skynet) 启动")
        logger.info("目标: 构建全球足球数据洪流")
        logger.info("🌍" * 80)

        self.stats['start_time'] = datetime.now()

        try:
            # Step 1: 构建赛事索引
            if not await self.step1_build_competitions_index():
                logger.error("❌ 天网计划终止: Step 1 失败")
                return False

            # Step 2: 构建球队索引
            if not await self.step2_build_teams_index():
                logger.error("❌ 天网计划终止: Step 2 失败")
                return False

            # Step 3: 获取目标球队
            teams = self.get_target_teams()
            if not teams:
                logger.error("❌ 天网计划终止: 未找到目标球队")
                return False

            logger.info(f"\n🎯 准备采集 {len(teams)} 支豪门球队")

            # Step 4: 批量采集
            if not await self.step3_batch_scrape_teams(teams):
                logger.error("❌ 天网计划终止: Step 3 失败")
                return False

            # 完成
            self.stats['end_time'] = datetime.now()
            duration = self.stats['end_time'] - self.stats['start_time']

            self.print_final_report(duration)
            return True

        except KeyboardInterrupt:
            logger.warning("\n🛑 用户中断天网计划")
            return False
        except Exception as e:
            logger.error(f"❌ 天网计划执行失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def print_final_report(self, duration):
        """打印最终报告"""
        logger.info("\n" + "="*80)
        logger.info("🎉 天网计划执行完成！")
        logger.info("="*80)

        logger.info(f"\n⏱️ 执行时间: {duration.total_seconds()/3600:.2f} 小时")
        logger.info(f"📊 总计球队: {self.stats['total_teams']}")
        logger.info(f"✅ 成功球队: {self.stats['successful_teams']}")
        logger.info(f"❌ 失败球队: {self.stats['failed_teams']}")
        logger.info(f"⚽ 总比赛数: {self.stats['total_matches']}")
        logger.info(f"🏆 新增联赛: {self.stats['total_new_leagues']}")

        # 成功率
        if self.stats['total_teams'] > 0:
            success_rate = (self.stats['successful_teams'] / self.stats['total_teams']) * 100
            logger.info(f"📈 成功率: {success_rate:.1f}%")

        # 平均每队比赛数
        if self.stats['successful_teams'] > 0:
            avg_matches = self.stats['total_matches'] / self.stats['successful_teams']
            logger.info(f"📊 平均每队比赛数: {avg_matches:.1f}")

        if self.stats['errors']:
            logger.info(f"\n❌ 错误列表 (前10个):")
            for i, error in enumerate(self.stats['errors'][:10]):
                logger.info(f"  {i+1}. {error}")

        # 数据库最终统计
        try:
            with self.engine.connect() as conn:
                # 统计比赛数据
                match_stats = conn.execute(text("""
                    SELECT
                        COUNT(*) as total_matches,
                        COUNT(DISTINCT league_id) as total_leagues,
                        COUNT(DISTINCT home_team_id) + COUNT(DISTINCT away_team_id) as total_teams
                    FROM matches
                    WHERE data_source = 'fbref'
                """)).fetchone()

                logger.info(f"\n📋 数据库最终统计 (FBref数据):")
                logger.info(f"  比赛总数: {match_stats.total_matches}")
                logger.info(f"  联赛总数: {match_stats.total_leagues}")
                logger.info(f"  球队总数: {match_stats.total_teams}")

                # 按赛季统计
                season_stats = conn.execute(text("""
                    SELECT season, COUNT(*) as match_count
                    FROM matches
                    WHERE data_source = 'fbref'
                    GROUP BY season
                    ORDER BY season DESC
                """)).fetchall()

                logger.info(f"\n📅 按赛季统计:")
                for row in season_stats:
                    logger.info(f"  {row.season}: {row.match_count} 场比赛")

        except Exception as e:
            logger.error(f"数据库统计失败: {e}")

        logger.info("="*80)
        logger.info("🌍 数据洪流已就绪，AI训练可以使用真实数据了！")
        logger.info("="*80)


async def main():
    """主函数"""
    # 确保日志目录
    Path("logs").mkdir(exist_ok=True)

    try:
        launcher = SkynetLauncher()
        success = await launcher.run_full_skynet()

        return 0 if success else 1

    except Exception as e:
        logger.error(f"❌ 启动器执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
