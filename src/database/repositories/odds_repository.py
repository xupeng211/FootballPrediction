"""
Titan007 赔率数据仓库 - 双表架构 (Latest + History)
Titan007 Odds Data Repository - Dual Table Architecture (Latest + History).

实施"最新快照 + 历史记录"双表策略的Repository：
- Latest表：存储每个公司每场比赛的最新赔率（支持upsert）
- History表：存储所有赔率变动历史（支持insert+去重）
- 智能去重：相同赔率数据不重复记录到History表

这个设计解决了变盘数据覆盖问题，确保历史数据的完整性。
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple

from sqlalchemy import select, and_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.async_manager import get_db_session
from src.database.models.titan import (
    TitanBookmaker,
    TitanEuroOddsLatest,
    TitanEuroOddsHistory,
    TitanAsianOddsLatest,
    TitanAsianOddsHistory,
    TitanOverUnderOddsLatest,
    TitanOverUnderOddsHistory,
)
from src.schemas.titan import (
    EuroOddsRecord,
    AsianHandicapRecord,
    OverUnderRecord,
)

logger = logging.getLogger(__name__)


class TitanOddsRepository:
    """
    Titan007 赔率数据仓库 - 双表架构

    职责:
    - 管理 Titan 博彩公司数据
    - 双写策略：Latest表upsert + History表insert
    - 智能去重：避免History表重复记录相同赔率
    - 提供完整的变盘历史追踪能力
    - 支持高性能的赔率查询和统计
    """

    def __init__(self):
        """初始化仓库"""
        self.logger = logger

    # ========================================
    # 博彩公司管理
    # ========================================

    async def upsert_bookmaker(
        self, company_id: int, company_name: str, **kwargs
    ) -> TitanBookmaker:
        """
        更新或插入博彩公司信息

        Args:
            company_id: Titan公司ID
            company_name: 公司名称
            **kwargs: 其他字段（display_name, country, is_active）

        Returns:
            TitanBookmaker: 博彩公司模型实例
        """
        data = {
            "company_id": company_id,
            "company_name": company_name,
            "display_name": kwargs.get("display_name"),
            "country": kwargs.get("country"),
            "is_active": kwargs.get("is_active", True),
            "updated_at": datetime.utcnow(),
        }

        async with get_db_session() as session:
            # 使用 PostgreSQL 的 ON CONFLICT DO UPDATE 语法
            stmt = (
                insert(TitanBookmaker)
                .values(data)
                .on_conflict_do_update(index_elements=["company_id"], set_=data)
                .returning(TitanBookmaker)
            )

            result = await session.execute(stmt)
            await session.commit()

            bookmaker = result.scalar_one()
            self.logger.debug(f"✅ 博彩公司 upsert 成功: {bookmaker}")
            return bookmaker

    async def get_bookmaker_by_company_id(
        self, company_id: int
    ) -> Optional[TitanBookmaker]:
        """根据 Titan 公司 ID 获取博彩公司"""
        async with get_db_session() as session:
            stmt = select(TitanBookmaker).where(TitanBookmaker.company_id == company_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_bookmaker_by_name(
        self, company_name: str
    ) -> Optional[TitanBookmaker]:
        """根据公司名称获取博彩公司"""
        async with get_db_session() as session:
            stmt = select(TitanBookmaker).where(
                TitanBookmaker.company_name == company_name
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    # ========================================
    # 欧赔数据管理
    # ========================================

    async def upsert_euro_odds(
        self, dto: EuroOddsRecord
    ) -> Tuple[TitanEuroOddsLatest, Optional[TitanEuroOddsHistory]]:
        """
        双写策略：更新或插入欧赔数据（Latest表 + History表）

        流程：
        1. 确保博彩公司存在
        2. Upsert 到 Latest表（更新最新赔率）
        3. 智能去重检查，判断是否需要插入History表
        4. 如需插入，则向History表插入历史记录

        Args:
            dto: 欧赔数据传输对象

        Returns:
            Tuple[TitanEuroOddsLatest, Optional[TitanEuroOddsHistory]]:
            (最新记录, 历史记录[如果插入了的话])
        """
        # 首先确保博彩公司存在
        bookmaker = await self.upsert_bookmaker(
            company_id=dto.companyid,
            company_name=dto.companyname,
        )

        # 准备欧赔数据
        api_update_time = (
            datetime.fromisoformat(dto.utime.replace("Z", "+00:00"))
            if dto.utime
            else datetime.utcnow()
        )
        data = {
            "match_id": dto.matchid,
            "bookmaker_id": bookmaker.id,
            "home_odds": dto.homeodds,
            "draw_odds": dto.drawodds,
            "away_odds": dto.awayodds,
            "home_open": dto.homeopen,
            "draw_open": dto.drawopen,
            "away_open": dto.awayopen,
            "update_time": api_update_time,
            "is_live": getattr(dto, "is_live", False),
            "confidence_score": getattr(dto, "confidence_score", None),
            "raw_data": getattr(dto, "raw_data", None),
            "updated_at": datetime.utcnow(),
        }

        async with get_db_session() as session:
            # 步骤1: Upsert 到 Latest表
            latest_stmt = (
                insert(TitanEuroOddsLatest)
                .values(data)
                .on_conflict_do_update(
                    index_elements=["match_id", "bookmaker_id"], set_=data
                )
                .returning(TitanEuroOddsLatest)
            )

            latest_result = await session.execute(latest_stmt)
            latest_odds = latest_result.scalar_one()
            self.logger.debug(f"✅ 欧赔 Latest 表 upsert 成功: {latest_odds}")

            # 步骤2: 智能去重检查 - 判断是否需要插入History表
            need_history_insert = await self._should_insert_euro_history(
                session=session,
                match_id=dto.matchid,
                bookmaker_id=bookmaker.id,
                home_odds=dto.homeodds,
                draw_odds=dto.drawodds,
                away_odds=dto.awayodds,
                update_time=api_update_time,
            )

            history_odds = None
            if need_history_insert:
                # 步骤3: 插入到History表
                history_data = data.copy()
                # 移除 Latest表特有的 updated_at 字段
                history_data.pop("updated_at", None)

                history_stmt = (
                    insert(TitanEuroOddsHistory)
                    .values(history_data)
                    .on_conflict_do_nothing(
                        index_elements=["match_id", "bookmaker_id", "update_time"]
                    )
                    .returning(TitanEuroOddsHistory)
                )

                history_result = await session.execute(history_stmt)
                history_odds = history_result.scalar_one_or_none()

                if history_odds:
                    self.logger.debug(f"✅ 欧赔 History 表插入成功: {history_odds}")
                else:
                    self.logger.debug(
                        f"⏭️ 欧赔 History 表跳过（重复数据）: match={dto.matchid}, company={dto.companyname}"
                    )

            await session.commit()
            return latest_odds, history_odds

    async def _should_insert_euro_history(
        self,
        session: AsyncSession,
        match_id: str,
        bookmaker_id: int,
        home_odds: float,
        draw_odds: float,
        away_odds: float,
        update_time: datetime,
    ) -> bool:
        """
        智能去重检查：判断是否需要插入欧赔历史记录

        去重逻辑：
        1. 查询最近一条历史记录
        2. 如果赔率完全相同且时间戳相同，则跳过插入
        3. 否则需要插入新的历史记录

        Args:
            session: 数据库会话
            match_id: 比赛ID
            bookmaker_id: 博彩公司ID
            home_odds: 主胜赔率
            draw_odds: 平局赔率
            away_odds: 客胜赔率
            update_time: 更新时间

        Returns:
            bool: 是否需要插入历史记录
        """
        # 查询最近一条历史记录
        stmt = (
            select(TitanEuroOddsHistory)
            .where(
                and_(
                    TitanEuroOddsHistory.match_id == match_id,
                    TitanEuroOddsHistory.bookmaker_id == bookmaker_id,
                )
            )
            .order_by(
                TitanEuroOddsHistory.update_time.desc(),
                TitanEuroOddsHistory.created_at.desc(),
            )
            .limit(1)
        )

        result = await session.execute(stmt)
        latest_history = result.scalar_one_or_none()

        # 如果没有历史记录，需要插入
        if not latest_history:
            return True

        # 如果赔率或时间戳有任何变化，需要插入
        if (
            latest_history.home_odds != home_odds
            or latest_history.draw_odds != draw_odds
            or latest_history.away_odds != away_odds
            or latest_history.update_time != update_time
        ):
            return True

        # 赔率和时间戳完全相同，跳过插入
        return False

    async def get_euro_odds_latest(
        self, match_id: str, company_id: int
    ) -> Optional[TitanEuroOddsLatest]:
        """获取指定比赛的最新欧赔数据"""
        async with get_db_session() as session:
            # 首先获取 bookmaker_id
            bookmaker = await self.get_bookmaker_by_company_id(company_id)
            if not bookmaker:
                return None

            stmt = select(TitanEuroOddsLatest).where(
                and_(
                    TitanEuroOddsLatest.match_id == match_id,
                    TitanEuroOddsLatest.bookmaker_id == bookmaker.id,
                )
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_euro_odds_history(
        self, match_id: str, company_id: int, limit: int = 50
    ) -> List[TitanEuroOddsHistory]:
        """获取指定比赛的欧赔历史数据（按时间倒序）"""
        async with get_db_session() as session:
            bookmaker = await self.get_bookmaker_by_company_id(company_id)
            if not bookmaker:
                return []

            stmt = (
                select(TitanEuroOddsHistory)
                .where(
                    and_(
                        TitanEuroOddsHistory.match_id == match_id,
                        TitanEuroOddsHistory.bookmaker_id == bookmaker.id,
                    )
                )
                .order_by(TitanEuroOddsHistory.update_time.desc())
                .limit(limit)
            )

            result = await session.execute(stmt)
            return result.scalars().all()

    # 兼容性方法：保持向后兼容
    async def get_euro_odds(
        self, match_id: str, company_id: int
    ) -> Optional[TitanEuroOddsLatest]:
        """获取指定比赛的欧赔数据（兼容性方法，重定向到最新数据）"""
        return await self.get_euro_odds_latest(match_id, company_id)

    # ========================================
    # 亚盘数据管理
    # ========================================

    async def upsert_asian_odds(
        self, dto: AsianHandicapRecord
    ) -> Tuple[TitanAsianOddsLatest, Optional[TitanAsianOddsHistory]]:
        """
        双写策略：更新或插入亚盘数据（Latest表 + History表）

        Args:
            dto: 亚盘数据传输对象

        Returns:
            Tuple[TitanAsianOddsLatest, Optional[TitanAsianOddsHistory]]:
            (最新记录, 历史记录[如果插入了的话])
        """
        # 确保博彩公司存在
        bookmaker = await self.upsert_bookmaker(
            company_id=dto.companyid,
            company_name=dto.companyname,
        )

        # 准备亚盘数据
        api_update_time = (
            datetime.fromisoformat(dto.utime.replace("Z", "+00:00"))
            if dto.utime
            else datetime.utcnow()
        )
        data = {
            "match_id": dto.matchid,
            "bookmaker_id": bookmaker.id,
            "upper_odds": dto.upperodds,
            "lower_odds": dto.lowerodds,
            "handicap": dto.handicap,
            "upper_open": dto.upperopen,
            "lower_open": dto.loweropen,
            "handicap_open": dto.handicapopen,
            "update_time": api_update_time,
            "is_live": getattr(dto, "is_live", False),
            "confidence_score": getattr(dto, "confidence_score", None),
            "raw_data": getattr(dto, "raw_data", None),
            "updated_at": datetime.utcnow(),
        }

        async with get_db_session() as session:
            # 步骤1: Upsert 到 Latest表
            latest_stmt = (
                insert(TitanAsianOddsLatest)
                .values(data)
                .on_conflict_do_update(
                    index_elements=["match_id", "bookmaker_id"], set_=data
                )
                .returning(TitanAsianOddsLatest)
            )

            latest_result = await session.execute(latest_stmt)
            latest_odds = latest_result.scalar_one()
            self.logger.debug(f"✅ 亚盘 Latest 表 upsert 成功: {latest_odds}")

            # 步骤2: 智能去重检查
            need_history_insert = await self._should_insert_asian_history(
                session=session,
                match_id=dto.matchid,
                bookmaker_id=bookmaker.id,
                upper_odds=dto.upperodds,
                lower_odds=dto.lowerodds,
                handicap=dto.handicap,
                update_time=api_update_time,
            )

            history_odds = None
            if need_history_insert:
                # 步骤3: 插入到History表
                history_data = data.copy()
                history_data.pop("updated_at", None)

                history_stmt = (
                    insert(TitanAsianOddsHistory)
                    .values(history_data)
                    .on_conflict_do_nothing(
                        index_elements=["match_id", "bookmaker_id", "update_time"]
                    )
                    .returning(TitanAsianOddsHistory)
                )

                history_result = await session.execute(history_stmt)
                history_odds = history_result.scalar_one_or_none()

                if history_odds:
                    self.logger.debug(f"✅ 亚盘 History 表插入成功: {history_odds}")
                else:
                    self.logger.debug(
                        f"⏭️ 亚盘 History 表跳过（重复数据）: match={dto.matchid}, company={dto.companyname}"
                    )

            await session.commit()
            return latest_odds, history_odds

    async def _should_insert_asian_history(
        self,
        session: AsyncSession,
        match_id: str,
        bookmaker_id: int,
        upper_odds: float,
        lower_odds: float,
        handicap: str,
        update_time: datetime,
    ) -> bool:
        """智能去重检查：判断是否需要插入亚盘历史记录"""
        stmt = (
            select(TitanAsianOddsHistory)
            .where(
                and_(
                    TitanAsianOddsHistory.match_id == match_id,
                    TitanAsianOddsHistory.bookmaker_id == bookmaker_id,
                )
            )
            .order_by(
                TitanAsianOddsHistory.update_time.desc(),
                TitanAsianOddsHistory.created_at.desc(),
            )
            .limit(1)
        )

        result = await session.execute(stmt)
        latest_history = result.scalar_one_or_none()

        if not latest_history:
            return True

        if (
            latest_history.upper_odds != upper_odds
            or latest_history.lower_odds != lower_odds
            or latest_history.handicap != handicap
            or latest_history.update_time != update_time
        ):
            return True

        return False

    async def get_asian_odds_latest(
        self, match_id: str, company_id: int
    ) -> Optional[TitanAsianOddsLatest]:
        """获取指定比赛的最新亚盘数据"""
        async with get_db_session() as session:
            bookmaker = await self.get_bookmaker_by_company_id(company_id)
            if not bookmaker:
                return None

            stmt = select(TitanAsianOddsLatest).where(
                and_(
                    TitanAsianOddsLatest.match_id == match_id,
                    TitanAsianOddsLatest.bookmaker_id == bookmaker.id,
                )
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_asian_odds_history(
        self, match_id: str, company_id: int, limit: int = 50
    ) -> List[TitanAsianOddsHistory]:
        """获取指定比赛的亚盘历史数据（按时间倒序）"""
        async with get_db_session() as session:
            bookmaker = await self.get_bookmaker_by_company_id(company_id)
            if not bookmaker:
                return []

            stmt = (
                select(TitanAsianOddsHistory)
                .where(
                    and_(
                        TitanAsianOddsHistory.match_id == match_id,
                        TitanAsianOddsHistory.bookmaker_id == bookmaker.id,
                    )
                )
                .order_by(TitanAsianOddsHistory.update_time.desc())
                .limit(limit)
            )

            result = await session.execute(stmt)
            return result.scalars().all()

    # 兼容性方法
    async def get_asian_odds(
        self, match_id: str, company_id: int
    ) -> Optional[TitanAsianOddsLatest]:
        """获取指定比赛的亚盘数据（兼容性方法）"""
        return await self.get_asian_odds_latest(match_id, company_id)

    # ========================================
    # 大小球数据管理
    # ========================================

    async def upsert_overunder_odds(
        self, dto: OverUnderRecord
    ) -> Tuple[TitanOverUnderOddsLatest, Optional[TitanOverUnderOddsHistory]]:
        """
        双写策略：更新或插入大小球数据（Latest表 + History表）

        Args:
            dto: 大小球数据传输对象

        Returns:
            Tuple[TitanOverUnderOddsLatest, Optional[TitanOverUnderOddsHistory]]:
            (最新记录, 历史记录[如果插入了的话])
        """
        # 确保博彩公司存在
        bookmaker = await self.upsert_bookmaker(
            company_id=dto.companyid,
            company_name=dto.companyname,
        )

        # 准备大小球数据
        api_update_time = (
            datetime.fromisoformat(dto.utime.replace("Z", "+00:00"))
            if dto.utime
            else datetime.utcnow()
        )
        data = {
            "match_id": dto.matchid,
            "bookmaker_id": bookmaker.id,
            "over_odds": dto.overodds,
            "under_odds": dto.underodds,
            "overunder": dto.handicap,  # OverUnderRecord 中使用 handicap 字段
            "over_open": dto.overopen,
            "under_open": dto.underopen,
            "overunder_open": dto.handicapopen,
            "update_time": api_update_time,
            "is_live": getattr(dto, "is_live", False),
            "confidence_score": getattr(dto, "confidence_score", None),
            "raw_data": getattr(dto, "raw_data", None),
            "updated_at": datetime.utcnow(),
        }

        async with get_db_session() as session:
            # 步骤1: Upsert 到 Latest表
            latest_stmt = (
                insert(TitanOverUnderOddsLatest)
                .values(data)
                .on_conflict_do_update(
                    index_elements=["match_id", "bookmaker_id"], set_=data
                )
                .returning(TitanOverUnderOddsLatest)
            )

            latest_result = await session.execute(latest_stmt)
            latest_odds = latest_result.scalar_one()
            self.logger.debug(f"✅ 大小球 Latest 表 upsert 成功: {latest_odds}")

            # 步骤2: 智能去重检查
            need_history_insert = await self._should_insert_overunder_history(
                session=session,
                match_id=dto.matchid,
                bookmaker_id=bookmaker.id,
                over_odds=dto.overodds,
                under_odds=dto.underodds,
                overunder=dto.handicap,
                update_time=api_update_time,
            )

            history_odds = None
            if need_history_insert:
                # 步骤3: 插入到History表
                history_data = data.copy()
                history_data.pop("updated_at", None)

                history_stmt = (
                    insert(TitanOverUnderOddsHistory)
                    .values(history_data)
                    .on_conflict_do_nothing(
                        index_elements=["match_id", "bookmaker_id", "update_time"]
                    )
                    .returning(TitanOverUnderOddsHistory)
                )

                history_result = await session.execute(history_stmt)
                history_odds = history_result.scalar_one_or_none()

                if history_odds:
                    self.logger.debug(f"✅ 大小球 History 表插入成功: {history_odds}")
                else:
                    self.logger.debug(
                        f"⏭️ 大小球 History 表跳过（重复数据）: match={dto.matchid}, company={dto.companyname}"
                    )

            await session.commit()
            return latest_odds, history_odds

    async def _should_insert_overunder_history(
        self,
        session: AsyncSession,
        match_id: str,
        bookmaker_id: int,
        over_odds: float,
        under_odds: float,
        overunder: str,
        update_time: datetime,
    ) -> bool:
        """智能去重检查：判断是否需要插入大小球历史记录"""
        stmt = (
            select(TitanOverUnderOddsHistory)
            .where(
                and_(
                    TitanOverUnderOddsHistory.match_id == match_id,
                    TitanOverUnderOddsHistory.bookmaker_id == bookmaker_id,
                )
            )
            .order_by(
                TitanOverUnderOddsHistory.update_time.desc(),
                TitanOverUnderOddsHistory.created_at.desc(),
            )
            .limit(1)
        )

        result = await session.execute(stmt)
        latest_history = result.scalar_one_or_none()

        if not latest_history:
            return True

        if (
            latest_history.over_odds != over_odds
            or latest_history.under_odds != under_odds
            or latest_history.overunder != overunder
            or latest_history.update_time != update_time
        ):
            return True

        return False

    async def get_overunder_odds_latest(
        self, match_id: str, company_id: int
    ) -> Optional[TitanOverUnderOddsLatest]:
        """获取指定比赛的最新大小球数据"""
        async with get_db_session() as session:
            bookmaker = await self.get_bookmaker_by_company_id(company_id)
            if not bookmaker:
                return None

            stmt = select(TitanOverUnderOddsLatest).where(
                and_(
                    TitanOverUnderOddsLatest.match_id == match_id,
                    TitanOverUnderOddsLatest.bookmaker_id == bookmaker.id,
                )
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_overunder_odds_history(
        self, match_id: str, company_id: int, limit: int = 50
    ) -> List[TitanOverUnderOddsHistory]:
        """获取指定比赛的大小球历史数据（按时间倒序）"""
        async with get_db_session() as session:
            bookmaker = await self.get_bookmaker_by_company_id(company_id)
            if not bookmaker:
                return []

            stmt = (
                select(TitanOverUnderOddsHistory)
                .where(
                    and_(
                        TitanOverUnderOddsHistory.match_id == match_id,
                        TitanOverUnderOddsHistory.bookmaker_id == bookmaker.id,
                    )
                )
                .order_by(TitanOverUnderOddsHistory.update_time.desc())
                .limit(limit)
            )

            result = await session.execute(stmt)
            return result.scalars().all()

    # 兼容性方法
    async def get_overunder_odds(
        self, match_id: str, company_id: int
    ) -> Optional[TitanOverUnderOddsLatest]:
        """获取指定比赛的大小球数据（兼容性方法）"""
        return await self.get_overunder_odds_latest(match_id, company_id)

    # ========================================
    # 批量操作
    # ========================================

    async def batch_upsert_euro_odds(
        self, dtos: List[EuroOddsRecord]
    ) -> Tuple[List[TitanEuroOddsLatest], List[TitanEuroOddsHistory]]:
        """
        批量双写策略：更新或插入欧赔数据（Latest表 + History表）

        Args:
            dtos: 欧赔数据传输对象列表

        Returns:
            Tuple[List[TitanEuroOddsLatest], List[TitanEuroOddsHistory]]:
            (最新记录列表, 历史记录列表)
        """
        latest_results = []
        history_results = []

        for dto in dtos:
            try:
                latest, history = await self.upsert_euro_odds(dto)
                latest_results.append(latest)
                if history:
                    history_results.append(history)
            except Exception as e:
                self.logger.error(
                    f"❌ 批量双写欧赔失败: {dto.matchid}-{dto.companyid}, 错误: {e}"
                )
                # 继续处理其他记录

        return latest_results, history_results

    async def batch_upsert_asian_odds(
        self, dtos: List[AsianHandicapRecord]
    ) -> Tuple[List[TitanAsianOddsLatest], List[TitanAsianOddsHistory]]:
        """批量双写策略：更新或插入亚盘数据"""
        latest_results = []
        history_results = []

        for dto in dtos:
            try:
                latest, history = await self.upsert_asian_odds(dto)
                latest_results.append(latest)
                if history:
                    history_results.append(history)
            except Exception as e:
                self.logger.error(
                    f"❌ 批量双写亚盘失败: {dto.matchid}-{dto.companyid}, 错误: {e}"
                )

        return latest_results, history_results

    async def batch_upsert_overunder_odds(
        self, dtos: List[OverUnderRecord]
    ) -> Tuple[List[TitanOverUnderOddsLatest], List[TitanOverUnderOddsHistory]]:
        """批量双写策略：更新或插入大小球数据"""
        latest_results = []
        history_results = []

        for dto in dtos:
            try:
                latest, history = await self.upsert_overunder_odds(dto)
                latest_results.append(latest)
                if history:
                    history_results.append(history)
            except Exception as e:
                self.logger.error(
                    f"❌ 批量双写大小球失败: {dto.matchid}-{dto.companyid}, 错误: {e}"
                )

        return latest_results, history_results

    # ========================================
    # 统计和查询
    # ========================================

    async def count_odds_by_match(self, match_id: str) -> Dict[str, int]:
        """统计指定比赛的赔率数量"""
        async with get_db_session() as session:
            euro_count = await session.scalar(
                select(TitanEuroOdds).where(TitanEuroOdds.match_id == match_id).count()
            )
            asian_count = await session.scalar(
                select(TitanAsianOdds)
                .where(TitanAsianOdds.match_id == match_id)
                .count()
            )
            overunder_count = await session.scalar(
                select(TitanOverUnderOdds)
                .where(TitanOverUnderOdds.match_id == match_id)
                .count()
            )

            return {
                "euro": euro_count or 0,
                "asian": asian_count or 0,
                "overunder": overunder_count or 0,
                "total": (euro_count or 0)
                + (asian_count or 0)
                + (overunder_count or 0),
            }

    async def get_recent_odds(self, hours: int = 24) -> Dict[str, List]:
        """获取最近的赔率数据"""
        async with get_db_session() as session:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)

            euro_results = await session.execute(
                select(TitanEuroOdds)
                .where(TitanEuroOdds.update_time >= cutoff_time)
                .order_by(TitanEuroOdds.update_time.desc())
                .limit(100)
            )

            asian_results = await session.execute(
                select(TitanAsianOdds)
                .where(TitanAsianOdds.update_time >= cutoff_time)
                .order_by(TitanAsianOdds.update_time.desc())
                .limit(100)
            )

            overunder_results = await session.execute(
                select(TitanOverUnderOdds)
                .where(TitanOverUnderOdds.update_time >= cutoff_time)
                .order_by(TitanOverUnderOdds.update_time.desc())
                .limit(100)
            )

            return {
                "euro": euro_results.scalars().all(),
                "asian": asian_results.scalars().all(),
                "overunder": overunder_results.scalars().all(),
            }


# 导出
__all__ = [
    "TitanOddsRepository",
]
