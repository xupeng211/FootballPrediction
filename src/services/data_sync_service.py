"""
数据同步服务
Data Sync Service for Football-Data.org API
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update, delete

from src.collectors.match_collector import MatchCollector
from src.models.external.match import ExternalMatch
from src.cache.redis_manager import RedisManager

logger = logging.getLogger(__name__)


class DataSyncService:
    """数据同步服务"""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv('DATABASE_URL', 'postgresql+asyncpg://postgres:enhanced_db_password_2024@localhost:5433/football_prediction_staging')
        self.redis_manager = RedisManager()
        self.engine = None
        self.async_session = None
        self.collector = MatchCollector()

    async def initialize(self):
        """初始化数据库连接"""
        try:
            # 创建异步数据库引擎
            self.engine = create_async_engine(
                self.database_url,
                echo=False,
                pool_size=10,
                max_overflow=20
            )

            # 创建会话工厂
            self.async_session = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            logger.info("Database connection initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise

    async def close(self):
        """关闭数据库连接"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        await self.collector.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.collector.__aexit__(exc_type, exc_val, exc_tb)
        await self.close()

    async def sync_all_data(self) -> Dict[str, Any]:
        """
        同步所有数据

        Returns:
            同步结果统计
        """
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'sync_results': {
                'upcoming_matches': {'success': 0, 'failed': 0, 'total': 0},
                'recent_matches': {'success': 0, 'failed': 0, 'total': 0},
                'total_processed': 0
            },
            'errors': []
        }

        try:
            logger.info("Starting full data synchronization")

            # 同步即将开始的比赛
            upcoming_result = await self.sync_upcoming_matches()
            results['sync_results']['upcoming_matches'] = upcoming_result

            # 同步最近的比赛结果
            recent_result = await self.sync_recent_matches()
            results['sync_results']['recent_matches'] = recent_result

            # 计算总处理数
            results['sync_results']['total_processed'] = (
                upcoming_result['success'] + recent_result['success']
            )

            logger.info(f"Data synchronization completed. Processed {results['sync_results']['total_processed']} matches")

        except Exception as e:
            error_msg = f"Failed to sync all data: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)

        return results

    async def sync_upcoming_matches(self, days_ahead: int = 7) -> Dict[str, int]:
        """
        同步即将开始的比赛

        Args:
            days_ahead: 未来天数

        Returns:
            同步结果统计
        """
        result = {'success': 0, 'failed': 0, 'total': 0}

        try:
            logger.info(f"Syncing upcoming matches for next {days_ahead} days")

            # 从API获取即将开始的比赛
            upcoming_matches = await self.collector.collect_upcoming_matches(days_ahead)
            result['total'] = len(upcoming_matches)

            if not upcoming_matches:
                logger.info("No upcoming matches found")
                return result

            # 处理每个比赛
            async with self.async_session() as session:
                for match_data in upcoming_matches:
                    try:
                        await self._process_match(session, match_data)
                        result['success'] += 1
                    except Exception as e:
                        logger.error(f"Failed to process upcoming match {match_data.get('id')}: {e}")
                        result['failed'] += 1

                await session.commit()

            logger.info(f"Upcoming matches sync completed: {result['success']}/{result['total']} successful")

        except Exception as e:
            logger.error(f"Failed to sync upcoming matches: {e}")
            result['failed'] = result['total']

        return result

    async def sync_recent_matches(self, days_back: int = 7) -> Dict[str, int]:
        """
        同步最近的比赛结果

        Args:
            days_back: 过去天数

        Returns:
            同步结果统计
        """
        result = {'success': 0, 'failed': 0, 'total': 0}

        try:
            logger.info(f"Syncing recent matches from last {days_back} days")

            # 从API获取最近的比赛
            recent_matches = await self.collector.collect_recent_matches(days_back)
            result['total'] = len(recent_matches)

            if not recent_matches:
                logger.info("No recent matches found")
                return result

            # 处理每个比赛
            async with self.async_session() as session:
                for match_data in recent_matches:
                    try:
                        await self._process_match(session, match_data)
                        result['success'] += 1
                    except Exception as e:
                        logger.error(f"Failed to process recent match {match_data.get('id')}: {e}")
                        result['failed'] += 1

                await session.commit()

            logger.info(f"Recent matches sync completed: {result['success']}/{result['total']} successful")

        except Exception as e:
            logger.error(f"Failed to sync recent matches: {e}")
            result['failed'] = result['total']

        return result

    async def _process_match(self, session: AsyncSession, match_data: Dict[str, Any]) -> ExternalMatch:
        """
        处理单个比赛数据

        Args:
            session: 数据库会话
            match_data: 比赛数据

        Returns:
            处理后的比赛模型
        """
        external_id = str(match_data.get('id'))

        # 检查是否已存在
        stmt = select(ExternalMatch).where(ExternalMatch.external_id == external_id)
        existing_match = await session.execute(stmt)
        match_record = existing_match.scalar_one_or_none()

        if match_record:
            # 更新现有记录
            success = match_record.update_from_api_data(match_data)
            if success:
                logger.debug(f"Updated existing match: {external_id}")
            else:
                logger.warning(f"Failed to update match: {external_id}")
        else:
            # 创建新记录
            match_record = ExternalMatch.from_api_data(match_data)
            session.add(match_record)
            logger.debug(f"Created new match: {external_id}")

        return match_record

    async def get_matches_by_status(self, status: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        根据状态获取比赛

        Args:
            status: 比赛状态
            limit: 限制数量

        Returns:
            比赛列表
        """
        cache_key = f"matches:status:{status}:limit:{limit}"

        # 尝试从缓存获取
        cached_data = await self.redis_manager.get(cache_key)
        if cached_data:
            logger.info(f"Cache hit for {cache_key}")
            return cached_data

        try:
            async with self.async_session() as session:
                stmt = (
                    select(ExternalMatch)
                    .where(ExternalMatch.status == status)
                    .where(ExternalMatch.is_active)
                    .order_by(ExternalMatch.match_date.desc())
                    .limit(limit)
                )

                result = await session.execute(stmt)
                matches = result.scalars().all()

                # 转换为字典列表
                match_dicts = [match.to_dict() for match in matches]

                # 缓存结果（30分钟）
                await self.redis_manager.set(
                    cache_key,
                    match_dicts,
                    expire=1800
                )

                return match_dicts

        except Exception as e:
            logger.error(f"Failed to get matches by status {status}: {e}")
            return []

    async def get_upcoming_matches(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取即将开始的比赛

        Args:
            limit: 限制数量

        Returns:
            即将开始的比赛列表
        """
        cache_key = f"matches:upcoming:limit:{limit}"

        # 尝试从缓存获取
        cached_data = await self.redis_manager.get(cache_key)
        if cached_data:
            return cached_data

        try:
            async with self.async_session() as session:
                stmt = (
                    select(ExternalMatch)
                    .where(ExternalMatch.status.in_(['scheduled', 'timed']))
                    .where(ExternalMatch.is_active)
                    .where(ExternalMatch.match_date >= datetime.utcnow())
                    .order_by(ExternalMatch.match_date.asc())
                    .limit(limit)
                )

                result = await session.execute(stmt)
                matches = result.scalars().all()

                match_dicts = [match.to_dict() for match in matches]

                # 缓存结果（15分钟）
                await self.redis_manager.set(
                    cache_key,
                    match_dicts,
                    expire=900
                )

                return match_dicts

        except Exception as e:
            logger.error(f"Failed to get upcoming matches: {e}")
            return []

    async def get_recent_finished_matches(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取最近已结束的比赛

        Args:
            limit: 限制数量

        Returns:
            最近结束的比赛列表
        """
        cache_key = f"matches:recent_finished:limit:{limit}"

        # 尝试从缓存获取
        cached_data = await self.redis_manager.get(cache_key)
        if cached_data:
            return cached_data

        try:
            async with self.async_session() as session:
                stmt = (
                    select(ExternalMatch)
                    .where(ExternalMatch.status == 'finished')
                    .where(ExternalMatch.is_active)
                    .order_by(ExternalMatch.match_date.desc())
                    .limit(limit)
                )

                result = await session.execute(stmt)
                matches = result.scalars().all()

                match_dicts = [match.to_dict() for match in matches]

                # 缓存结果（30分钟）
                await self.redis_manager.set(
                    cache_key,
                    match_dicts,
                    expire=1800
                )

                return match_dicts

        except Exception as e:
            logger.error(f"Failed to get recent finished matches: {e}")
            return []

    async def cleanup_old_matches(self, days_to_keep: int = 30) -> int:
        """
        清理旧的比赛数据

        Args:
            days_to_keep: 保留天数

        Returns:
            清理的记录数
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

            async with self.async_session() as session:
                stmt = (
                    delete(ExternalMatch)
                    .where(ExternalMatch.match_date < cutoff_date)
                    .where(ExternalMatch.status == 'finished')
                )

                result = await session.execute(stmt)
                deleted_count = result.rowcount
                await session.commit()

                logger.info(f"Cleaned up {deleted_count} old matches")
                return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old matches: {e}")
            return 0

    async def get_sync_statistics(self) -> Dict[str, Any]:
        """
        获取同步统计信息

        Returns:
            统计信息
        """
        try:
            async with self.async_session() as session:
                # 统计各种状态的比赛数量
                stats = {}

                for status in ['scheduled', 'live', 'finished', 'postponed', 'cancelled']:
                    stmt = select(ExternalMatch).where(ExternalMatch.status == status)
                    result = await session.execute(stmt)
                    count = len(result.scalars().all())
                    stats[f'{status}_count'] = count

                # 获取最新的同步时间
                stmt = (
                    select(ExternalMatch)
                    .order_by(ExternalMatch.updated_at.desc())
                    .limit(1)
                )
                result = await session.execute(stmt)
                latest_match = result.scalar_one_or_none()

                if latest_match:
                    stats['last_sync_time'] = latest_match.updated_at.isoformat()
                else:
                    stats['last_sync_time'] = None

                stats['total_matches'] = sum(stats[k] for k in stats.keys() if k.endswith('_count'))

                return stats

        except Exception as e:
            logger.error(f"Failed to get sync statistics: {e}")
            return {'error': str(e)}