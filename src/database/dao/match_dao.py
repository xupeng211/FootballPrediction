"""
比赛数据访问对象
Match Data Access Object

提供比赛数据的数据库访问接口，包含基础CRUD和业务特定查询方法。
"""

import logging
from datetime import datetime, timedelta
from typing import , Optional,  Any

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .base_dao import BaseDAO
from .schemas import MatchCreate, MatchUpdate
from .exceptions import (
    RecordNotFoundError,
    ValidationError,
    DatabaseConnectionError,
)

# 导入Match模型
from src.database.models.match import Match

logger = logging.getLogger(__name__)


class MatchDAO(BaseDAO):
    """
    比赛数据访问对象

    继承BaseDAO提供基础的CRUD操作，并添加比赛特定的业务查询方法。
    """

    @property
    def primary_key_field(self) -> str:
        """获取主键字段名"""
        return "id"

    # ==================== 基础CRUD方法重写 ====================

    async def get_by_teams(
        self,
        home_team: str,
        away_team: str,
        match_time: Optional[datetime] = None
    ) -> Optional[Any]:
        """
        根据主客队获取比赛

        Args:
            home_team: 主队名称
            away_team: 客队名称
            match_time: 可选的比赛时间限制

        Returns:
            Optional[Match]: 找到的比赛记录

        Raises:
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            query = select(self.model).where(
                and_(
                    self.model.home_team_name == home_team,
                    self.model.away_team_name == away_team
                )
            )

            # 如果提供了比赛时间，添加时间过滤
            if match_time:
                # 查找比赛时间前后1小时内的比赛
                time_range = timedelta(hours=1)
                query = query.where(
                    and_(
                        self.model.match_time >= match_time - time_range,
                        self.model.match_time <= match_time + time_range
                    )
                )

            result = await self.session.execute(query)
            record = result.scalar_one_or_none()

            if record:
                logger.debug(f"找到比赛: {home_team} vs {away_team}")
            else:
                logger.debug(f"未找到比赛: {home_team} vs {away_team}")

            return record

        except Exception as e:
            logger.error(f"根据主客队获取比赛失败: {home_team} vs {away_team}")
            raise DatabaseConnectionError(f"根据主客队获取比赛失败: {e}")

    # ==================== 业务特定方法 ====================

    async def get_upcoming_matches(
        self,
        hours: int = 24,
        limit: int = 100,
        league_id: Optional[int] = None
    ) -> list[Any]:
        """
        获取未来N小时内的比赛

        Args:
            hours: 未来小时数，默认24小时
            limit: 返回记录数限制，默认100
            league_id: 可选的联赛ID过滤

        Returns:
            list[Match]: 即将开始的比赛列表

        Raises:
            DatabaseConnectionError: 数据库连接错误
            ValidationError: 参数验证错误
        """
        try:
            # 参数验证
            if hours <= 0:
                raise ValidationError("Match", {"hours": "hours必须大于0"})
            if limit <= 0:
                raise ValidationError("Match", {"limit": "limit必须大于0"})

            # 计算时间范围
            now = datetime.utcnow()
            end_time = now + timedelta(hours=hours)

            logger.debug(f"查询未来{hours}小时内的比赛: {now} 到 {end_time}")

            # 构建查询
            query = select(self.model).where(
                and_(
                    self.model.match_time >= now,
                    self.model.match_time <= end_time,
                    self.model.status.in_(['scheduled', 'postponed'])  # 只包含未开始的比赛
                )
            ).order_by(self.model.match_time.asc()).limit(limit)

            # 添加联赛过滤
            if league_id:
                query = query.where(self.model.league_id == league_id)

            result = await self.session.execute(query)
            matches = result.scalars().all()

            logger.info(f"找到{len(matches)}场未来{hours}小时内的比赛")
            return list(matches)

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"获取未来{hours}小时内的比赛失败: {e}")
            raise DatabaseConnectionError(f"获取即将开始的比赛失败: {e}")

    async def get_matches_by_league(
        self,
        league_id: int,
        *,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> list[Any]:
        """
        根据联赛获取比赛列表

        Args:
            league_id: 联赛ID
            skip: 跳过记录数
            limit: 返回记录数限制
            status: 可选的比赛状态过滤
            start_date: 可选的开始日期
            end_date: 可选的结束日期

        Returns:
            list[Match]: 联赛比赛列表

        Raises:
            DatabaseConnectionError: 数据库连接错误
            ValidationError: 参数验证错误
        """
        try:
            # 参数验证
            if skip < 0:
                raise ValidationError("Match", {"skip": "skip不能为负数"})
            if limit <= 0:
                raise ValidationError("Match", {"limit": "limit必须大于0"})

            logger.debug(f"查询联赛{league_id}的比赛: skip={skip}, limit={limit}")

            # 构建基础查询
            query = select(self.model).where(self.model.league_id == league_id)

            # 添加状态过滤
            if status:
                query = query.where(self.model.status == status)

            # 添加日期范围过滤
            if start_date:
                query = query.where(self.model.match_time >= start_date)
            if end_date:
                query = query.where(self.model.match_time <= end_date)

            # 排序和分页
            query = query.order_by(self.model.match_time.desc()).offset(skip).limit(limit)

            result = await self.session.execute(query)
            matches = result.scalars().all()

            logger.info(f"找到联赛{league_id}的{len(matches)}场比赛")
            return list(matches)

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"获取联赛{league_id}的比赛失败: {e}")
            raise DatabaseConnectionError(f"获取联赛比赛失败: {e}")

    async def get_live_matches(self) -> list[Any]:
        """
        获取正在进行的比赛

        Returns:
            list[Match]: 正在进行的比赛列表

        Raises:
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            query = select(self.model).where(
                self.model.status == 'live'
            ).order_by(self.model.match_time.asc())

            result = await self.session.execute(query)
            matches = result.scalars().all()

            logger.debug(f"找到{len(matches)}场正在进行的比赛")
            return list(matches)

        except Exception as e:
            logger.error(f"获取正在进行的比赛失败: {e}")
            raise DatabaseConnectionError(f"获取正在进行比赛失败: {e}")

    async def get_finished_matches(
        self,
        *,
        days: int = 7,
        league_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> list[Any]:
        """
        获取最近已完成的比赛

        Args:
            days: 最近天数，默认7天
            league_id: 可选的联赛ID过滤
            skip: 跳过记录数
            limit: 返回记录数限制

        Returns:
            list[Match]: 已完成的比赛列表

        Raises:
            DatabaseConnectionError: 数据库连接错误
            ValidationError: 参数验证错误
        """
        try:
            # 参数验证
            if days <= 0:
                raise ValidationError("Match", {"days": "days必须大于0"})

            # 计算时间范围
            now = datetime.utcnow()
            start_time = now - timedelta(days=days)

            # 构建查询
            query = select(self.model).where(
                and_(
                    self.model.match_time >= start_time,
                    self.model.match_time <= now,
                    self.model.status == 'finished'
                )
            ).order_by(self.model.match_time.desc()).offset(skip).limit(limit)

            # 添加联赛过滤
            if league_id:
                query = query.where(self.model.league_id == league_id)

            result = await self.session.execute(query)
            matches = result.scalars().all()

            logger.info(f"找到最近{days}天内{len(matches)}场已完成的比赛")
            return list(matches)

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"获取最近已完成的比赛失败: {e}")
            raise DatabaseConnectionError(f"获取已完成比赛失败: {e}")

    async def search_matches(
        self,
        *,
        keyword: str,
        league_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50
    ) -> list[Any]:
        """
        搜索比赛（按球队名称）

        Args:
            keyword: 搜索关键词
            league_id: 可选的联赛ID过滤
            skip: 跳过记录数
            limit: 返回记录数限制

        Returns:
            list[Match]: 匹配的比赛列表

        Raises:
            DatabaseConnectionError: 数据库连接错误
            ValidationError: 参数验证错误
        """
        try:
            # 参数验证
            if not keyword or len(keyword.strip()) < 2:
                raise ValidationError("Match", {"keyword": "搜索关键词至少需要2个字符"})

            keyword = keyword.strip()

            # 构建搜索查询
            query = select(self.model).where(
                or_(
                    self.model.home_team_name.ilike(f"%{keyword}%"),
                    self.model.away_team_name.ilike(f"%{keyword}%")
                )
            )

            # 添加联赛过滤
            if league_id:
                query = query.where(self.model.league_id == league_id)

            # 排序和分页
            query = query.order_by(self.model.match_time.desc()).offset(skip).limit(limit)

            result = await self.session.execute(query)
            matches = result.scalars().all()

            logger.info(f"搜索关键词'{keyword}'找到{len(matches)}场比赛")
            return list(matches)

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"搜索比赛失败: {keyword}")
            raise DatabaseConnectionError(f"搜索比赛失败: {e}")

    # ==================== 统计方法 ====================

    async def get_match_count_by_status(
        self,
        league_id: Optional[int] = None
    ) -> dict[str, int]:
        """
        按状态统计比赛数量

        Args:
            league_id: 可选的联赛ID过滤

        Returns:
            dict[str, int]: 各状态的比赛数量

        Raises:
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            query = select(
                self.model.status,
                func.count(self.model.id)
            ).group_by(self.model.status)

            # 添加联赛过滤
            if league_id:
                query = query.where(self.model.league_id == league_id)

            result = await self.session.execute(query)
            rows = result.all()

            # 转换为字典
            status_counts = dict(rows)

            logger.debug(f"联赛{league_id or '全部'}比赛状态统计: {status_counts}")
            return status_counts

        except Exception as e:
            logger.error(f"获取比赛状态统计失败: {e}")
            raise DatabaseConnectionError(f"获取比赛状态统计失败: {e}")

    async def update_match_status(
        self,
        match_id: int,
        new_status: str
    ) -> bool:
        """
        更新比赛状态

        Args:
            match_id: 比赛ID
            new_status: 新状态

        Returns:
            bool: 是否更新成功

        Raises:
            RecordNotFoundError: 比赛不存在
            ValidationError: 状态无效
            DatabaseConnectionError: 数据库连接错误
        """
        try:
            # 验证状态
            allowed_statuses = ['scheduled', 'live', 'finished', 'postponed', 'cancelled']
            if new_status not in allowed_statuses:
                raise ValidationError("Match", {
                    "status": f"状态必须是以下之一: {allowed_statuses}"
                })

            # 检查比赛是否存在
            match = await self.get(match_id)
            if not match:
                raise RecordNotFoundError("Match", match_id)

            # 更新状态
            match.status = new_status
            match.updated_at = datetime.utcnow()

            logger.info(f"比赛{match_id}状态已更新为: {new_status}")
            return True

        except (ValidationError, RecordNotFoundError):
            raise
        except Exception as e:
            logger.error(f"更新比赛{match_id}状态失败: {e}")
            raise DatabaseConnectionError(f"更新比赛状态失败: {e}")


# 导出MatchDAO
__all__ = ['MatchDAO']
