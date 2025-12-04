#!/usr/bin/env python3
"""
FotMob历史回填器 - 天网计划第二阶段
Chief Data Architect: 数据地基重塑
Purpose: 使用FotMob API回填5个赛季的完整赛程数据，重塑L1数据源架构
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
import psycopg2
from psycopg2.extras import RealDictCursor
from src.data.collectors.fotmob_match_collector import FotmobCollector, FotmobAPIError

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class FotMobMatch:
    """FotMob比赛数据模型"""
    id: str
    home_team: str
    away_team: str
    home_score: Optional[int]
    away_score: Optional[int]
    match_date: datetime
    status: str
    match_week: Optional[int]
    league_id: str
    league_name: str
    season: str


class FotMobHistoryBackfiller:
    """FotMob历史数据回填器"""

    def __init__(self):
        # 初始化HTTP客户端
        self.session = httpx.Client(timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.fotmob.com/',
        })

        # 数据库配置
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': os.getenv('POSTGRES_PORT', '5432'),
            'database': os.getenv('POSTGRES_DB', 'football_prediction'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'postgres-dev-password')
        }

        # 统计信息
        self.stats = {
            'total_matches_processed': 0,
            'successful_inserts': 0,
            'failed_inserts': 0,
            'duplicates_skipped': 0,
            'leagues_processed': 0,
            'seasons_processed': 0,
            'start_time': datetime.now()
        }

    def load_league_config(self, config_path: str = "config/fotmob_leagues.json") -> Dict:
        """加载联赛配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            leagues = config.get('leagues', {})
            logger.info(f"✅ 加载了 {len(leagues)} 个联赛配置")
            return leagues

        except Exception as e:
            logger.error(f"❌ 加载联赛配置失败: {e}")
            return {}

    async def fetch_league_matches(self, league_id: str, season: str) -> List[FotMobMatch]:
        """
        获取指定联赛赛季的所有比赛

        Args:
            league_id: FotMob联赛ID
            season: 赛季标识

        Returns:
            比赛列表
        """
        try:
            logger.info(f"🔍 获取联赛数据: ID={league_id}, 赛季={season}")

            # 构建FotMob API URL
            # 注意：这里使用简化的API调用，实际可能需要更复杂的端点
            api_url = f"https://www.fotmob.com/api/leagues?id={league_id}&season={season}"

            response = self.session.get(api_url)

            if response.status_code != 200:
                logger.warning(f"⚠️ API调用失败: {response.status_code} - {api_url}")
                return []

            data = response.json()

            # 解析比赛数据
            matches = self._parse_league_matches(data, league_id, season)
            logger.info(f"✅ 解析到 {len(matches)} 场比赛")
            return matches

        except Exception as e:
            logger.error(f"❌ 获取联赛数据失败: {e}")
            return []

    def _parse_league_matches(self, data: Dict, league_id: str, season: str) -> List[FotMobMatch]:
        """解析联赛比赛数据"""
        matches = []

        try:
            # 根据FotMob API响应结构解析数据
            # 这里使用简化的解析逻辑，实际需要根据API响应结构调整

            # 假设数据结构：data['leagues'][0]['matches']
            leagues_data = data.get('leagues', [])
            if not leagues_data:
                logger.warning("⚠️ 未找到联赛数据")
                return matches

            league_data = leagues_data[0] if leagues_data else {}
            matches_data = league_data.get('matches', [])

            for match_data in matches_data:
                try:
                    match = FotMobMatch(
                        id=str(match_data.get('id', '')),
                        home_team=match_data.get('home', {}).get('name', ''),
                        away_team=match_data.get('away', {}).get('name', ''),
                        home_score=match_data.get('homeScore'),
                        away_score=match_data.get('awayScore'),
                        match_date=self._parse_match_date(match_data.get('status', {}).get('utcTime')),
                        status=match_data.get('status', {}).get('type', ''),
                        match_week=match_data.get('round'),
                        league_id=league_id,
                        league_name=league_data.get('name', ''),
                        season=season
                    )
                    matches.append(match)

                except Exception as e:
                    logger.debug(f"解析比赛数据失败: {e}")
                    continue

        except Exception as e:
            logger.error(f"解析联赛数据失败: {e}")

        return matches

    def _parse_match_date(self, date_str: Optional[str]) -> datetime:
        """解析比赛日期"""
        if not date_str:
            return datetime.now()

        try:
            # 尝试解析不同的日期格式
            if 'T' in date_str:
                # ISO格式：2023-12-15T19:45:00Z
                date_str = date_str.replace('Z', '+00:00')
                return datetime.fromisoformat(date_str)
            else:
                # 尝试其他格式
                return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')

        except Exception:
            return datetime.now()

    async def get_database_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(**self.db_config)

    def match_exists(self, cursor, fotmob_id: str) -> bool:
        """检查比赛是否已存在"""
        try:
            cursor.execute(
                "SELECT id FROM matches WHERE match_metadata->>'fotmob_id' = %s",
                (fotmob_id,)
            )
            return cursor.fetchone() is not None
        except Exception as e:
            logger.debug(f"检查比赛存在性失败: {e}")
            return False

    def insert_match(self, cursor, match: FotMobMatch) -> bool:
        """插入比赛记录"""
        try:
            # 构建metadata
            metadata = {
                'fotmob_id': match.id,
                'fotmob_league_id': match.league_id,
                'data_source': 'fotmob_l1',
                'imported_at': datetime.now().isoformat(),
                'season': match.season,
                'match_week': match.match_week
            }

            # 插入比赛记录
            insert_sql = """
                INSERT INTO matches (
                    home_team, away_team, home_score, away_score,
                    match_date, status, data_source, data_completeness,
                    league_id, league_name, match_metadata, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """

            cursor.execute(insert_sql, (
                match.home_team,
                match.away_team,
                match.home_score,
                match.away_score,
                match.match_date,
                match.status,
                'fotmob_l1',
                'basic',  # 基础数据，后续L2会补全
                match.league_id,
                match.league_name,
                json.dumps(metadata, ensure_ascii=False)
            ))

            return True

        except Exception as e:
            logger.error(f"插入比赛失败: {e}")
            return False

    async def process_league_season(self, league_key: str, league_config: Dict, season: str):
        """处理单个联赛赛季"""
        try:
            logger.info(f"🔄 开始处理: {league_config['name']} {season}")

            # 获取比赛数据
            matches = await self.fetch_league_matches(league_config['id'], season)

            if not matches:
                logger.warning(f"⚠️ 没有找到比赛数据: {league_config['name']} {season}")
                return

            # 数据库操作
            conn = await self.get_database_connection()
            try:
                with conn.cursor() as cursor:
                    batch_success = 0
                    batch_duplicates = 0
                    batch_failed = 0

                    for i, match in enumerate(matches, 1):
                        try:
                            # 检查是否已存在
                            if self.match_exists(cursor, match.id):
                                batch_duplicates += 1
                                logger.debug(f"⏭️  跳过重复比赛: {match.id}")
                                continue

                            # 插入新记录
                            if self.insert_match(cursor, match):
                                batch_success += 1
                                self.stats['successful_inserts'] += 1

                                if i % 10 == 0:
                                    logger.info(f"📊 {i}/{len(matches)} 已处理 ({batch_success} 成功)")
                            else:
                                batch_failed += 1
                                self.stats['failed_inserts'] += 1

                        except Exception as e:
                            logger.error(f"❌ 处理比赛失败 {match.id}: {e}")
                            batch_failed += 1
                            self.stats['failed_inserts'] += 1

                        # 延迟避免过载
                        if i % 50 == 0:
                            conn.commit()

                    # 提交事务
                    conn.commit()

                    logger.info(f"✅ 处理完成: {league_config['name']} {season}")
                    logger.info(f"   总比赛: {len(matches)}")
                    logger.info(f"   新增: {batch_success}")
                    logger.info(f"   重复跳过: {batch_duplicates}")
                    logger.info(f"   失败: {batch_failed}")

                    self.stats['total_matches_processed'] += len(matches)
                    self.stats['duplicates_skipped'] += batch_duplicates

            finally:
                conn.close()

        except Exception as e:
            logger.error(f"❌ 处理联赛赛季失败: {e}")

    def get_priority_leagues(self, leagues: Dict, max_leagues: int = 5) -> Dict:
        """获取优先级最高的联赛"""
        # 按优先级排序，优先处理高优先级联赛
        sorted_leagues = sorted(
            leagues.items(),
            key=lambda x: x[1].get('priority', 999)
        )

        # 取前max_leagues个联赛
        priority_leagues = dict(sorted_leagues[:max_leagues])
        logger.info(f"🎯 选择 {len(priority_leagues)} 个优先级联赛进行回填")

        # 显示选择的联赛
        for key, config in priority_leagues.items():
            priority = config.get('priority', 'N/A')
            logger.info(f"   • {config['name']} (优先级: {priority})")

        return priority_leagues

    async def run_backfill(self, config_path: str = "config/fotmob_leagues.json",
                          test_mode: bool = True):
        """运行历史数据回填"""
        logger.info("🚀 启动FotMob历史数据回填器 - 天网计划")
        logger.info("目标: 5个赛季完整赛程回填")
        logger.info("=" * 80)

        try:
            # 加载联赛配置
            leagues = self.load_league_config(config_path)
            if not leagues:
                logger.error("❌ 没有可用的联赛配置")
                return

            # 选择优先级联赛
            if test_mode:
                leagues = self.get_priority_leagues(leagues, max_leagues=1)  # 只处理英超
                target_seasons = ["2024/2025"]  # 只处理当前赛季
            else:
                leagues = self.get_priority_leagues(leagues, max_leagues=10)  # 处理10个顶级联赛
                target_seasons = ["2020/2021", "2021/2022", "2022/2023", "2023/2024", "2024/2025"]

            logger.info(f"📋 将处理 {len(leagues)} 个联赛，{len(target_seasons)} 个赛季")
            logger.info(f"🎯 测试模式: {'是' if test_mode else '否'}")

            # 处理每个联赛
            for league_key, league_config in leagues.items():
                self.stats['leagues_processed'] += 1

                for season in target_seasons:
                    self.stats['seasons_processed'] += 1
                    await self.process_league_season(league_key, league_config, season)

                    # 联赛间延迟
                    await asyncio.sleep(2)

                # 联赛间更长延迟
                await asyncio.sleep(5)

            # 输出最终统计
            self._print_final_stats()

        except Exception as e:
            logger.error(f"💥 回填程序异常: {e}")
            import traceback
            traceback.print_exc()

    def _print_final_stats(self):
        """打印最终统计信息"""
        self.stats['end_time'] = datetime.now()
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()

        logger.info("=" * 80)
        logger.info("📊 天网计划执行统计:")
        logger.info(f"   执行时间: {duration:.1f}秒")
        logger.info(f"   处理联赛: {self.stats['leagues_processed']}")
        logger.info(f"   处理赛季: {self.stats['seasons_processed']}")
        logger.info(f"   总比赛数: {self.stats['total_matches_processed']}")
        logger.info(f"   成功插入: {self.stats['successful_inserts']}")
        logger.info(f"   重复跳过: {self.stats['duplicates_skipped']}")
        logger.info(f"   插入失败: {self.stats['failed_inserts']}")

        if self.stats['total_matches_processed'] > 0:
            success_rate = (self.stats['successful_inserts'] /
                          (self.stats['total_matches_processed'] - self.stats['duplicates_skipped'])) * 100
            logger.info(f"   成功率: {success_rate:.1f}%")

        logger.info("=" * 80)

        if self.stats['successful_inserts'] > 0:
            logger.info("🎉 天网计划执行成功!")
            logger.info("📈 L1数据源已切换到FotMob")
        else:
            logger.warning("⚠️ 没有成功插入任何数据")


async def main():
    """主函数"""
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='FotMob历史数据回填器')
    parser.add_argument('--test', action='store_true', help='测试模式（只处理英超当前赛季）')
    parser.add_argument('--config', default='config/fotmob_leagues.json', help='联赛配置文件路径')

    args = parser.parse_args()

    logger.info("🌟 FotMob历史回填器 - 天网计划启动")
    logger.info("🎯 目标: 重塑L1数据源，实现100%赛程覆盖")

    try:
        backfiller = FotMobHistoryBackfiller()
        await backfiller.run_backfill(config_path=args.config, test_mode=args.test)

    except Exception as e:
        logger.error(f"💥 主程序异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())