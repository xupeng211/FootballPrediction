"""
足球预测系统 - 数据访问对象模块
Data Access Object Module for Football Prediction System

提供统一的数据访问接口，解耦业务逻辑与数据库操作。
Provides unified data access interfaces, decoupling business logic from database operations.

此模块旨在解决以下循环依赖问题：
This module aims to solve the following circular dependency issues:
1. src/database <-> src/models
2. src/services <-> src/database
3. src/models <-> src/database/models

通过引入数据访问对象模式，将数据库操作封装在独立的DAO层中，
业务层通过DAO接口访问数据，避免直接依赖数据库模型。

By introducing the Data Access Object pattern, database operations are encapsulated
in an independent DAO layer. Business layers access data through DAO interfaces,
avoiding direct dependency on database models.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.database.connection import DatabaseManager
from src.database.models import (
    AuditLog,
    DataCollectionLog,
    Features,
    League,
    Match,
    Odds,
    Predictions,
    RawMatchData,
    RawOddsData,
    RawScoresData,
    Team,
)


class BaseDAO:
    """基础数据访问对象"""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager


class MatchDAO(BaseDAO):
    """比赛数据访问对象"""

    async def get_match_by_id(self, match_id: int) -> Optional[Match]:
        """根据ID获取比赛信息"""
        async with self.db_manager.get_async_session() as session:
            result = await session.execute(select(Match).where(Match.id == match_id))
            return result.scalar_one_or_none()

    async def get_matches_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Match]:
        """根据日期范围获取比赛"""
        async with self.db_manager.get_async_session() as session:
            result = await session.execute(
                select(Match)
                .where(Match.match_time >= start_date)
                .where(Match.match_time <= end_date)
                .order_by(Match.match_time)
            )
            return list(result.scalars().all())


class PredictionDAO(BaseDAO):
    """预测数据访问对象"""

    async def create_prediction(self, prediction_data: Dict[str, Any]) -> Predictions:
        """创建预测记录"""
        async with self.db_manager.get_async_session() as session:
            prediction = Predictions(**prediction_data)
            session.add(prediction)
            await session.commit()
            await session.refresh(prediction)
            return prediction

    async def get_prediction_by_match_id(self, match_id: int) -> Optional[Predictions]:
        """根据比赛ID获取预测结果"""
        async with self.db_manager.get_async_session() as session:
            result = await session.execute(
                select(Predictions).where(Predictions.match_id == match_id)
            )
            return result.scalar_one_or_none()

    async def update_prediction_result(
        self, match_id: int, actual_result: str, is_correct: Optional[bool] = None
    ) -> bool:
        """更新预测结果验证信息"""
        async with self.db_manager.get_async_session() as session:
            try:
                # 首先获取预测记录以确定是否正确
                pred_result = await session.execute(
                    select(Predictions).where(Predictions.match_id == match_id)
                )
                prediction = pred_result.scalar_one_or_none()

                if not prediction:
                    return False

                # 如果没有提供is_correct，则根据预测结果和实际结果比较
                if is_correct is None:
                    is_correct = prediction.predicted_result == actual_result

                result = await session.execute(
                    update(Predictions)
                    .where(Predictions.match_id == match_id)
                    .values(
                        actual_result=actual_result,
                        is_correct=is_correct,
                        verified_at=datetime.now(),
                    )
                )
                await session.commit()
                return result.rowcount > 0
            except Exception:
                await session.rollback()
                raise


class DataCollectionDAO(BaseDAO):
    """数据采集访问对象"""

    async def create_data_collection_log(
        self, log_data: Dict[str, Any]
    ) -> DataCollectionLog:
        """创建数据采集日志"""
        async with self.db_manager.get_async_session() as session:
            log = DataCollectionLog(**log_data)
            session.add(log)
            await session.commit()
            await session.refresh(log)
            return log


# 导出所有DAO类
__all__ = ["BaseDAO", "MatchDAO", "PredictionDAO", "DataCollectionDAO"]
