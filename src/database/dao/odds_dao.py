"""
赔率数据访问对象
Odds Data Access Object

提供赔率数据的数据库访问接口，包含基础CRUD和业务特定查询方法。
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from decimal import Decimal

from sqlalchemy import select, and_, or_, func, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .base_dao import BaseDAO
from .schemas import (
    OddsCreate,
    OddsUpdate,
    OddsHistoryCreate,
    MarketAnalysisCreate,
)
from .exceptions import (
    RecordNotFoundError,
    ValidationError,
    DatabaseConnectionError,
)

# 导入Odds相关模型
from src.database.models.odds import Odds, OddsHistory, MarketAnalysis

logger = logging.getLogger(__name__)


class OddsDAO(BaseDAO):
    """
    赔率数据访问对象

    继承BaseDAO提供基础的CRUD操作，并添加赔率特定的业务查询方法。
    """

    @property
    def primary_key_field(self) -> str:
        """获取主键字段名"""
        return "id"

    # ==================== 基础CRUD方法重写 ====================

    async def get_by_match_and_bookmaker(
        self,
        match_id: int,
        bookmaker: str
    ) -> Optional[Odds]:
        """
        根据比赛ID和博彩公司获取赔率

        Args:
            match_id: 比赛ID
            bookmaker: 博彩公司名称

        Returns:
            Optional[Odds]: 找到的赔率记录

        Raises:
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            query = select(self.model).where(
                and_(
                    self.model.match_id == match_id,
                    self.model.bookmaker == bookmaker,
                    self.model.is_active
                )
            ).order_by(desc(self.model.created_at))

            result = await self.session.execute(query)
            record = result.scalar_one_or_none()

            if record:
                logger.debug(f"找到赔率: match_id={match_id}, bookmaker={bookmaker}")
            else:
                logger.debug(f"未找到赔率: match_id={match_id}, bookmaker={bookmaker}")

            return record

        except Exception as e:
            logger.error(f"根据比赛和博彩公司获取赔率失败: match_id={match_id}, bookmaker={bookmaker}")
            raise DatabaseConnectionError(f"根据比赛和博彩公司获取赔率失败: {e}")

    # ==================== 业务特定方法 ====================

    async def get_latest_odds_by_bookmaker(
        self,
        match_id: int,
        bookmaker: str
    ) -> Optional[Odds]:
        """
        获取指定博彩公司的最新赔率

        Args:
            match_id: 比赛ID
            bookmaker: 博彩公司名称

        Returns:
            Optional[Odds]: 最新的赔率记录

        Raises:
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            query = select(self.model).where(
                and_(
                    self.model.match_id == match_id,
                    self.model.bookmaker == bookmaker,
                    self.model.is_active
                )
            ).order_by(desc(self.model.last_updated)).limit(1)

            result = await self.session.execute(query)
            record = result.scalar_one_or_none()

            if record:
                logger.debug(f"获取最新赔率成功: match_id={match_id}, bookmaker={bookmaker}, last_updated={record.last_updated}")

            return record

        except Exception as e:
            logger.error(f"获取最新赔率失败: match_id={match_id}, bookmaker={bookmaker}")
            raise DatabaseConnectionError(f"获取最新赔率失败: {e}")

    async def get_all_odds_by_match(
        self,
        match_id: int,
        *,
        active_only: bool = True,
        live_only: bool = False
    ) -> list[Odds]:
        """
        获取比赛的所有赔率

        Args:
            match_id: 比赛ID
            active_only: 是否只获取活跃赔率
            live_only: 是否只获取实时赔率

        Returns:
            List[Odds]: 赔率列表

        Raises:
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            query = select(self.model).where(self.model.match_id == match_id)

            if active_only:
                query = query.where(self.model.is_active)

            if live_only:
                query = query.where(self.model.live_odds)

            query = query.order_by(
                self.model.bookmaker.asc(),
                desc(self.model.last_updated)
            )

            result = await self.session.execute(query)
            odds_list = result.scalars().all()

            logger.info(f"获取比赛{match_id}的赔率: 找到{len(odds_list)}条记录")
            return list(odds_list)

        except Exception as e:
            logger.error(f"获取比赛赔率失败: match_id={match_id}")
            raise DatabaseConnectionError(f"获取比赛赔率失败: {e}")

    async def get_best_odds_by_match(
        self,
        match_id: int,
        bet_type: str = "home_win"
    ) -> Optional[Odds]:
        """
        获取比赛的最优赔率

        Args:
            match_id: 比赛ID
            bet_type: 投注类型 ('home_win', 'draw', 'away_win')

        Returns:
            Optional[Odds]: 最优赔率记录

        Raises:
            ValidationError: 投注类型无效
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            # 验证投注类型
            valid_types = ['home_win', 'draw', 'away_win', 'over_under', 'asian_handicap']
            if bet_type not in valid_types:
                raise ValidationError("Odds", {"bet_type": f"投注类型必须是以下之一: {valid_types}"})

            # 构建查询
            query = select(self.model).where(
                and_(
                    self.model.match_id == match_id,
                    self.model.is_active,
                    getattr(self.model, bet_type).isnot(None)
                )
            ).order_by(getattr(self.model, bet_type).asc()).limit(1)

            result = await self.session.execute(query)
            best_odds = result.scalar_one_or_none()

            if best_odds:
                logger.info(f"找到最优赔率: match_id={match_id}, bet_type={bet_type}, odds={getattr(best_odds, bet_type)}")

            return best_odds

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"获取最优赔率失败: match_id={match_id}, bet_type={bet_type}")
            raise DatabaseConnectionError(f"获取最优赔率失败: {e}")

    async def get_live_odds(
        self,
        *,
        limit: int = 100,
        match_ids: Optional[list[int]] = None
    ) -> list[Odds]:
        """
        获取实时赔率

        Args:
            limit: 返回记录数限制
            match_ids: 可选的比赛ID列表

        Returns:
            List[Odds]: 实时赔率列表

        Raises:
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            query = select(self.model).where(
                and_(
                    self.model.live_odds,
                    self.model.is_active
                )
            )

            if match_ids:
                query = query.where(self.model.match_id.in_(match_ids))

            query = query.order_by(desc(self.model.last_updated)).limit(limit)

            result = await self.session.execute(query)
            live_odds = result.scalars().all()

            logger.info(f"获取实时赔率: 找到{len(live_odds)}条记录")
            return list(live_odds)

        except Exception as e:
            logger.error("获取实时赔率失败")
            raise DatabaseConnectionError(f"获取实时赔率失败: {e}")

    async def get_odds_by_confidence_threshold(
        self,
        min_confidence: float = 0.7,
        *,
        limit: int = 50
    ) -> list[Odds]:
        """
        根据置信度阈值获取赔率

        Args:
            min_confidence: 最低置信度 (0-1)
            limit: 返回记录数限制

        Returns:
            List[Odds]: 高置信度赔率列表

        Raises:
            ValidationError: 置信度参数无效
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            if not 0 <= min_confidence <= 1:
                raise ValidationError("Odds", {"min_confidence": "置信度必须在0-1之间"})

            query = select(self.model).where(
                and_(
                    self.model.confidence_score >= min_confidence,
                    self.model.is_active
                )
            ).order_by(desc(self.model.confidence_score)).limit(limit)

            result = await self.session.execute(query)
            high_confidence_odds = result.scalars().all()

            logger.info(f"获取高置信度赔率(>={min_confidence}): 找到{len(high_confidence_odds)}条记录")
            return list(high_confidence_odds)

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"获取高置信度赔率失败: min_confidence={min_confidence}")
            raise DatabaseConnectionError(f"获取高置信度赔率失败: {e}")

    async def search_odds_by_bookmaker(
        self,
        bookmaker_keyword: str,
        *,
        limit: int = 50
    ) -> list[Odds]:
        """
        根据博彩公司关键词搜索赔率

        Args:
            bookmaker_keyword: 博彩公司关键词
            limit: 返回记录数限制

        Returns:
            List[Odds]: 匹配的赔率列表

        Raises:
            ValidationError: 关键词无效
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            if not bookmaker_keyword or len(bookmaker_keyword.strip()) < 2:
                raise ValidationError("Odds", {"bookmaker_keyword": "博彩公司关键词至少需要2个字符"})

            keyword = bookmaker_keyword.strip()

            query = select(self.model).where(
                and_(
                    self.model.bookmaker.ilike(f"%{keyword}%"),
                    self.model.is_active
                )
            ).order_by(desc(self.model.last_updated)).limit(limit)

            result = await self.session.execute(query)
            search_results = result.scalars().all()

            logger.info(f"搜索博彩公司'{keyword}'的赔率: 找到{len(search_results)}条记录")
            return list(search_results)

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"搜索博彩公司赔率失败: {bookmaker_keyword}")
            raise DatabaseConnectionError(f"搜索博彩公司赔率失败: {e}")

    # ==================== 统计方法 ====================

    async def get_odds_count_by_bookmaker(self) -> dict[str, int]:
        """
        按博彩公司统计赔率数量

        Returns:
            Dict[str, int]: 各博彩公司的赔率数量

        Raises:
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            query = select(
                self.model.bookmaker,
                func.count(self.model.id)
            ).where(
                self.model.is_active
            ).group_by(self.model.bookmaker)

            result = await self.session.execute(query)
            rows = result.all()

            # 转换为字典
            bookmaker_counts = dict(rows)

            logger.debug(f"博彩公司赔率统计: {bookmaker_counts}")
            return bookmaker_counts

        except Exception as e:
            logger.error("获取博彩公司赔率统计失败")
            raise DatabaseConnectionError(f"获取博彩公司赔率统计失败: {e}")

    async def get_live_odds_count(self) -> int:
        """
        统计实时赔率数量

        Returns:
            int: 实时赔率数量

        Raises:
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            query = select(func.count(self.model.id)).where(
                and_(
                    self.model.live_odds,
                    self.model.is_active
                )
            )

            result = await self.session.execute(query)
            count = result.scalar()

            logger.debug(f"实时赔率数量: {count}")
            return count

        except Exception as e:
            logger.error("统计实时赔率数量失败")
            raise DatabaseConnectionError(f"统计实时赔率数量失败: {e}")

    # ==================== 质量控制方法 ====================

    async def update_odds_quality_score(
        self,
        odds_id: int,
        quality_score: float
    ) -> bool:
        """
        更新赔率质量分数

        Args:
            odds_id: 赔率ID
            quality_score: 质量分数 (0-1)

        Returns:
            bool: 是否更新成功

        Raises:
            RecordNotFoundError: 赔率不存在
            ValidationError: 质量分数无效
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            # 验证质量分数
            if not 0 <= quality_score <= 1:
                raise ValidationError("Odds", {"quality_score": "质量分数必须在0-1之间"})

            # 检查赔率是否存在
            odds = await self.get(odds_id)
            if not odds:
                raise RecordNotFoundError("Odds", odds_id)

            # 更新质量分数
            odds.data_quality_score = quality_score
            odds.updated_at = datetime.utcnow()

            logger.info(f"赔率{odds_id}质量分数已更新为: {quality_score}")
            return True

        except (ValidationError, RecordNotFoundError):
            raise
        except Exception as e:
            logger.error(f"更新赔率{odds_id}质量分数失败: {e}")
            raise DatabaseConnectionError(f"更新赔率质量分数失败: {e}")

    async def deactivate_old_odds(
        self,
        hours: int = 24,
        bookmaker: Optional[str] = None
    ) -> int:
        """
        停用旧的赔率记录

        Args:
            hours: 超过多少小时的赔率被视为旧数据
            bookmaker: 可选的博彩公司过滤

        Returns:
            int: 停用的记录数量

        Raises:
            ValidationError: 小时数无效
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            if hours <= 0:
                raise ValidationError("Odds", {"hours": "小时数必须大于0"})

            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            # 构建更新查询
            update_stmt = (
                self.model.__table__.update()
                .where(self.model.last_updated < cutoff_time)
                .where(self.model.is_active)
                .values(is_active=False, updated_at=datetime.utcnow())
            )

            if bookmaker:
                update_stmt = update_stmt.where(self.model.bookmaker == bookmaker)

            result = await self.session.execute(update_stmt)
            deactivated_count = result.rowcount

            logger.info(f"停用{hours}小时前的旧赔率记录: {deactivated_count}条")
            return deactivated_count

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"停用旧赔率记录失败: hours={hours}")
            raise DatabaseConnectionError(f"停用旧赔率记录失败: {e}")


# 导出OddsDAO
__all__ = ['OddsDAO']
