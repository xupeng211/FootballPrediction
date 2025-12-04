#!/usr/bin/env python3
"""
FotMob智能回填引擎 - 生产级数据收割机
Chief Architect: 工业级历史数据回填系统
Purpose: 高并发、智能化的历史数据回填，支持多个赛季批量处理
"""

import asyncio
import logging
import sys
import time
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.data.collectors.fotmob_universal_collector import FotMobUniversalCollector
from src.database.definitions import get_async_session
from src.database.models.league import League
from src.database.models.match import Match

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class BackfillConfig:
    """回填配置"""
    seasons: List[str]
    max_concurrent_leagues: int = 10
    max_concurrent_requests: int = 20
    batch_size: int = 100
    rate_limit_delay: float = 0.2
    retry_attempts: int = 3
    dry_run: bool = False
    skip_existing: bool = True


@dataclass
class BackfillStats:
    """回填统计"""
    start_time: float
    leagues_processed: int = 0
    seasons_processed: int = 0
    matches_found: int = 0
    matches_inserted: int = 0
    matches_updated: int = 0
    duplicates_skipped: int = 0
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []

    @property
    def elapsed_time(self) -> float:
        return time.time() - self.start_time

    @property
    def processing_rate(self) -> float:
        return self.matches_found / max(self.elapsed_time, 1)

    def to_dict(self) -> Dict:
        return {
            'elapsed_time': f"{self.elapsed_time:.2f}s",
            'leagues_processed': self.leagues_processed,
            'seasons_processed': self.seasons_processed,
            'matches_found': self.matches_found,
            'matches_inserted': self.matches_inserted,
            'matches_updated': self.matches_updated,
            'duplicates_skipped': self.duplicates_skipped,
            'processing_rate': f"{self.processing_rate:.1f} matches/sec",
            'error_count': len(self.errors)
        }


class FotMobSmartBackfill:
    """FotMob智能回填引擎"""

    def __init__(self, config: BackfillConfig):
        self.config = config
        self.stats = BackfillStats(start_time=time.time())
        self.collector = None

    async def __aenter__(self):
        self.collector = FotMobUniversalCollector(
            max_concurrent=self.config.max_concurrent_requests,
            rate_limit_delay=self.config.rate_limit_delay,
            retry_attempts=self.config.retry_attempts
        )
        await self.collector.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.collector:
            await self.collector.__aexit__(exc_type, exc_val, exc_tb)

    async def run_backfill(self) -> Dict[str, any]:
        """执行完整的历史数据回填"""
        logger.info("🚀 FotMob智能回填引擎启动")
        logger.info("=" * 80)
        logger.info(f"📋 配置参数:")
        logger.info(f"   赛季: {self.config.seasons}")
        logger.info(f"   最大并发联赛: {self.config.max_concurrent_leagues}")
        logger.info(f"   批处理大小: {self.config.batch_size}")
        logger.info(f"   跳过已存在: {self.config.skip_existing}")
        logger.info(f"   模拟运行: {self.config.dry_run}")

        try:
            # 1. 获取有FotMob ID的联赛
            leagues = await self._get_active_leagues()
            if not leagues:
                raise ValueError("没有找到有FotMob ID的活跃联赛")

            logger.info(f"📊 找到 {len(leagues)} 个活跃联赛")

            # 2. 并发处理联赛和赛季
            await self._process_leagues_seasons(leagues)

            # 3. 生成报告
            report = self._generate_report()

            logger.info("=" * 80)
            logger.info("🎉 回填任务完成!")
            logger.info(f"📈 总处理效率: {self.stats.processing_rate:.1f} 比赛/秒")

            return report

        except Exception as e:
            error_msg = f"回填流程失败: {e}"
            logger.error(f"💥 {error_msg}")
            self.stats.errors.append(error_msg)
            return {'error': error_msg, 'stats': self.stats.to_dict()}

    async def _get_active_leagues(self) -> List[Dict[str, str]]:
        """获取有FotMob ID的活跃联赛"""
        try:
            async with get_async_session() as session:
                result = await session.execute(
                    select(League.id, League.name, League.fotmob_id)
                    .where(League.fotmob_id.isnot(None))
                    .where(League.is_active == True)
                    .order_by(League.name)
                )

                leagues = []
                for row in result:
                    leagues.append({
                        'id': row.id,
                        'name': row.name,
                        'fotmob_id': row.fotmob_id
                    })

                return leagues

        except Exception as e:
            logger.error(f"❌ 获取联赛失败: {e}")
            return []

    async def _process_leagues_seasons(self, leagues: List[Dict[str, str]]):
        """并发处理联赛和赛季"""
        logger.info(f"🔄 开始处理 {len(leagues)} 个联赛 x {len(self.config.seasons)} 个赛季")

        # 创建并发任务
        semaphore = asyncio.Semaphore(self.config.max_concurrent_leagues)

        async def process_league_season(league: Dict[str, str], season: str):
            async with semaphore:
                return await self._process_single_league_season(league, season)

        # 生成所有任务
        tasks = []
        for league in leagues:
            for season in self.config.seasons:
                task = process_league_season(league, season)
                tasks.append((league['name'], season, task))

        # 执行并发任务
        results = []
        for i, (league_name, season, task) in enumerate(tasks):
            try:
                result = await task
                results.append((league_name, season, result))
                self.stats.seasons_processed += 1

                # 进度报告
                if (i + 1) % 10 == 0:
                    progress = (i + 1) / len(tasks) * 100
                    logger.info(f"📊 进度: {progress:.1f}% ({i + 1}/{len(tasks)})")

            except Exception as e:
                error_msg = f"处理 {league_name} {season} 失败: {e}"
                logger.error(f"❌ {error_msg}")
                self.stats.errors.append(error_msg)
                results.append((league_name, season, {'error': str(e)}))

        # 统计成功处理的联赛
        successful_leagues = set()
        for league_name, season, result in results:
            if not result.get('error'):
                successful_leagues.add(league_name)

        self.stats.leagues_processed = len(successful_leagues)

    async def _process_single_league_season(
        self,
        league: Dict[str, str],
        season: str
    ) -> Dict[str, any]:
        """处理单个联赛的单个赛季"""
        league_name = league['name']
        fotmob_id = league['fotmob_id']

        try:
            logger.debug(f"🏆 处理 {league_name} {season}")

            # 使用采集器获取比赛数据
            matches = await self.collector.fetch_matches_by_league(fotmob_id, season)

            if not matches:
                logger.debug(f"⚠️ {league_name} {season} 没有比赛数据")
                return {'matches_found': 0, 'matches_processed': 0}

            self.stats.matches_found += len(matches)

            # 如果是模拟运行，只返回统计
            if self.config.dry_run:
                return {
                    'matches_found': len(matches),
                    'matches_processed': 0,
                    'status': 'dry_run'
                }

            # 批量处理比赛数据
            processed = await self._batch_upsert_matches(matches, league)

            return processed

        except Exception as e:
            error_msg = f"处理 {league_name} {season} 失败: {e}"
            logger.error(f"❌ {error_msg}")
            return {'error': error_msg}

    async def _batch_upsert_matches(
        self,
        matches: List[Dict],
        league: Dict[str, str]
    ) -> Dict[str, int]:
        """批量插入/更新比赛数据"""
        if not matches:
            return {'inserted': 0, 'updated': 0, 'skipped': 0}

        try:
            # 分批处理
            total_inserted = 0
            total_updated = 0
            total_skipped = 0

            for i in range(0, len(matches), self.config.batch_size):
                batch = matches[i:i + self.config.batch_size]
                result = await self._process_match_batch(batch, league)

                total_inserted += result['inserted']
                total_updated += result['updated']
                total_skipped += result['skipped']

                # 提交批次
                if not self.config.dry_run:
                    async with get_async_session() as session:
                        await session.commit()

                # 短暂延迟避免数据库过载
                await asyncio.sleep(0.01)

            # 更新全局统计
            self.stats.matches_inserted += total_inserted
            self.stats.matches_updated += total_updated
            self.stats.duplicates_skipped += total_skipped

            return {
                'inserted': total_inserted,
                'updated': total_updated,
                'skipped': total_skipped,
                'total': len(matches)
            }

        except Exception as e:
            logger.error(f"❌ 批量处理失败: {e}")
            return {'error': str(e), 'inserted': 0, 'updated': 0, 'skipped': 0}

    async def _process_match_batch(
        self,
        batch: List[Dict],
        league: Dict[str, str]
    ) -> Dict[str, int]:
        """处理单个批次的比赛"""
        if self.config.dry_run:
            return {'inserted': 0, 'updated': 0, 'skipped': len(batch)}

        try:
            async with get_async_session() as session:
                inserted = 0
                updated = 0
                skipped = 0

                for match_data in batch:
                    try:
                        # 检查是否已存在
                        if self.config.skip_existing:
                            existing = await session.execute(
                                select(Match).where(
                                    Match.fotmob_id == match_data['fotmob_id']
                                )
                            )
                            if existing.scalar_one_or_none():
                                skipped += 1
                                continue

                        # 准备比赛记录
                        match_record = await self._prepare_match_record(match_data, league)

                        # 使用UPSERT
                        stmt = pg_insert(Match).values(**match_record)
                        stmt = stmt.on_conflict('fotmob_id').do_update(
                            set_=match_record
                        )

                        await session.execute(stmt)

                        # 统计操作类型
                        result = await session.execute(
                            select(Match).where(
                                Match.fotmob_id == match_data['fotmob_id']
                            )
                        )
                        if result.scalar_one_or_none():
                            if skipped == 0:  # 如果不是跳过的，说明是新插入
                                inserted += 1
                            else:
                                updated += 1

                    except Exception as e:
                        logger.warning(f"⚠️ 处理比赛失败 {match_data.get('fotmob_id')}: {e}")
                        skipped += 1

                return {
                    'inserted': inserted,
                    'updated': updated,
                    'skipped': skipped
                }

        except Exception as e:
            logger.error(f"❌ 批次处理异常: {e}")
            return {'error': str(e), 'inserted': 0, 'updated': 0, 'skipped': 0}

    async def _prepare_match_record(
        self,
        match_data: Dict,
        league: Dict[str, str]
    ) -> Dict:
        """准备比赛记录"""
        return {
            'fotmob_id': match_data['fotmob_id'],
            'league_id': league['id'],
            'home_team_name': match_data['home_team_name'],
            'away_team_name': match_data['away_team_name'],
            'match_date': datetime.strptime(
                match_data['match_date'], '%Y-%m-%d'
            ).date(),
            'home_score': match_data.get('home_score'),
            'away_score': match_data.get('away_score'),
            'status': match_data['status'],
            'venue': match_data.get('venue', ''),
            'season': match_data['season'],
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

    def _generate_report(self) -> Dict[str, any]:
        """生成回填报告"""
        return {
            'summary': self.stats.to_dict(),
            'config': {
                'seasons': self.config.seasons,
                'max_concurrent_leagues': self.config.max_concurrent_leagues,
                'batch_size': self.config.batch_size,
                'dry_run': self.config.dry_run
            },
            'performance': {
                'total_time': f"{self.stats.elapsed_time:.2f}s",
                'avg_processing_rate': f"{self.stats.processing_rate:.1f} matches/sec",
                'leagues_per_season': self.stats.leagues_processed / max(len(self.config.seasons), 1)
            },
            'data_quality': {
                'total_matches_found': self.stats.matches_found,
                'successfully_processed': self.stats.matches_inserted + self.stats.matches_updated,
                'processing_success_rate': f"{(self.stats.matches_inserted + self.stats.matches_updated) / max(self.stats.matches_found, 1) * 100:.1f}%"
            }
        }


# 便捷函数
async def run_backfill(
    seasons: Optional[List[str]] = None,
    max_concurrent: int = 10,
    dry_run: bool = False
) -> Dict[str, any]:
    """
    运行FotMob历史数据回填

    Args:
        seasons: 要回填的赛季列表，默认为最近5个赛季
        max_concurrent: 最大并发数
        dry_run: 是否为模拟运行

    Returns:
        回填报告
    """
    # 默认配置：最近5个赛季
    if not seasons:
        current_year = datetime.now().year
        seasons = [f"{year}/{year+1}" for year in range(current_year - 5, current_year)]

    config = BackfillConfig(
        seasons=seasons,
        max_concurrent_leagues=max_concurrent,
        dry_run=dry_run,
        skip_existing=True,
        batch_size=50
    )

    async with FotMobSmartBackfill(config) as backfill:
        return await backfill.run_backfill()


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='FotMob智能回填引擎')
    parser.add_argument('--seasons', nargs='+', help='要回填的赛季 (如: 2023/2024 2022/2023)')
    parser.add_argument('--max-concurrent', type=int, default=10, help='最大并发数')
    parser.add_argument('--dry-run', action='store_true', help='模拟运行，不实际写入数据')
    parser.add_argument('--recent-years', type=int, default=5, help='回填最近N年的数据')

    args = parser.parse_args()

    # 确定赛季
    if args.seasons:
        seasons = args.seasons
    else:
        current_year = datetime.now().year
        seasons = [f"{year}/{year+1}" for year in range(current_year - args.recent_years, current_year)]

    logger.info("🌟 FotMob智能回填引擎")
    logger.info(f"📅 回填赛季: {seasons}")
    logger.info(f"🔧 并发数: {args.max_concurrent}")
    logger.info(f"🧪 模拟运行: {args.dry_run}")
    logger.info("=" * 80)

    try:
        # 运行回填
        report = await run_backfill(
            seasons=seasons,
            max_concurrent=args.max_concurrent,
            dry_run=args.dry_run
        )

        if 'error' in report:
            logger.error(f"❌ 回填失败: {report['error']}")
            sys.exit(1)
        else:
            logger.info("✅ 回填成功完成!")

            # 显示详细报告
            summary = report['summary']
            performance = report['performance']
            data_quality = report['data_quality']

            print("\n📊 回填报告:")
            print(f"   执行时间: {summary['elapsed_time']}")
            print(f"   处理联赛: {summary['leagues_processed']}")
            print(f"   处理赛季: {summary['seasons_processed']}")
            print(f"   发现比赛: {summary['matches_found']}")
            print(f"   插入比赛: {summary['matches_inserted']}")
            print(f"   更新比赛: {summary['matches_updated']}")
            print(f"   跳过重复: {summary['duplicates_skipped']}")
            print(f"   处理效率: {summary['processing_rate']}")
            print(f"   数据质量: {data_quality['processing_success_rate']}")

    except KeyboardInterrupt:
        logger.info("⏹️ 用户中断操作")
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 程序异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())