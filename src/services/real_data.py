"""真实数据库服务模块
Real Database Service Module.

提供基于SQLAlchemy的真实数据库查询服务，替换Mock数据。
Provides real database query service based on SQLAlchemy, replacing Mock data.
"""

import logging
from typing import Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.database.models.team import Team
from src.database.models.league import League
from src.database.models.match import Match

logger = logging.getLogger(__name__)


class RealDataService:
    """真实数据服务类 - 基于SQLAlchemy的数据库查询."""

    def __init__(self, session: AsyncSession):
        """
        初始化真实数据服务.

        Args:
            session: 异步数据库会话
        """
        self.session = session
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def get_teams_list(self, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        """
        获取球队列表 - 从真实数据库查询
        Get teams list - query from real database.

        Args:
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            球队列表数据，包含分页信息
        """
        try:
            self.logger.info(f"Querying teams from database: limit={limit}, offset={offset}")

            # 查询球队总数
            count_query = select(Team)
            count_result = await self.session.execute(count_query)
            total_teams = len(count_result.scalars().all())

            # 分页查询球队数据
            query = select(Team).offset(offset).limit(limit)
            result = await self.session.execute(query)
            teams = result.scalars().all()

            # 转换为API响应格式
            teams_data = []
            for team in teams:
                team_dict = {
                    "id": team.id,
                    "name": team.name,
                    "short_name": team.short_name,
                    "country": team.country,
                    "founded": team.founded_year,
                    "stadium": team.venue,
                    "website": team.website,
                    "created_at": team.created_at.isoformat() if team.created_at else None,
                    "updated_at": team.updated_at.isoformat() if team.updated_at else None,
                }
                teams_data.append(team_dict)

            self.logger.info(f"Successfully retrieved {len(teams_data)} teams from database")

            return {
                "teams": teams_data,
                "total": total_teams,
                "limit": limit,
                "offset": offset,
            }

        except Exception as e:
            self.logger.error(f"Error querying teams from database: {e}")
            raise e

    async def get_team_by_id(self, team_id: int) -> Optional[dict[str, Any]]:
        """
        根据ID获取球队信息 - 从真实数据库查询
        Get team information by ID - query from real database.

        Args:
            team_id: 球队ID

        Returns:
            球队信息或None
        """
        try:
            self.logger.info(f"Querying team {team_id} from database")

            query = select(Team).where(Team.id == team_id)
            result = await self.session.execute(query)
            team = result.scalar_one_or_none()

            if not team:
                self.logger.warning(f"Team {team_id} not found in database")
                return None

            team_dict = {
                "id": team.id,
                "name": team.name,
                "short_name": team.short_name,
                "country": team.country,
                "founded": team.founded_year,
                "stadium": team.venue,
                "website": team.website,
                "created_at": team.created_at.isoformat() if team.created_at else None,
                "updated_at": team.updated_at.isoformat() if team.updated_at else None,
            }

            self.logger.info(f"Successfully retrieved team {team_id} from database")
            return team_dict

        except Exception as e:
            self.logger.error(f"Error querying team {team_id} from database: {e}")
            raise e

    async def get_matches_list(self, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        """
        获取比赛列表 - 从真实数据库查询
        Get matches list - query from real database.

        Args:
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            比赛列表数据，包含分页信息
        """
        try:
            self.logger.info(f"Querying matches from database: limit={limit}, offset={offset}")

            # 查询比赛总数
            count_query = select(Match)
            count_result = await self.session.execute(count_query)
            total_matches = len(count_result.scalars().all())

            # 关联查询比赛、主队、客队和联赛
            query = (
                select(Match)
                .options(
                    selectinload(Match).joinedload(Match.home_team),
                    selectinload(Match).joinedload(Match.away_team),
                )
                .offset(offset)
                .limit(limit)
            )
            result = await self.session.execute(query)
            matches = result.scalars().all()

            # 转换为API响应格式
            matches_data = []
            for match in matches:
                match_dict = {
                    "id": match.id,
                    "home_team_id": match.home_team_id,
                    "away_team_id": match.away_team_id,
                    "home_score": match.home_score,
                    "away_score": match.away_score,
                    "status": match.status,
                    "match_date": match.match_date.isoformat() if match.match_date else None,
                    "venue": match.venue,
                    "league_id": match.league_id,
                    "season": match.season,
                    "created_at": match.created_at.isoformat() if match.created_at else None,
                    "updated_at": match.updated_at.isoformat() if match.updated_at else None,
                }
                matches_data.append(match_dict)

            self.logger.info(f"Successfully retrieved {len(matches_data)} matches from database")

            return {
                "matches": matches_data,
                "total": total_matches,
                "limit": limit,
                "offset": offset,
            }

        except Exception as e:
            self.logger.error(f"Error querying matches from database: {e}")
            raise e

    async def get_match_by_id(self, match_id: int) -> Optional[dict[str, Any]]:
        """
        根据ID获取比赛信息 - 从真实数据库查询
        Get match information by ID - query from real database.

        Args:
            match_id: 比赛ID

        Returns:
            比赛信息或None
        """
        try:
            self.logger.info(f"Querying match {match_id} from database")

            query = (
                select(Match)
                .options(
                    selectinload(Match).joinedload(Match.home_team),
                    selectinload(Match).joinedload(Match.away_team),
                )
                .where(Match.id == match_id)
            )
            result = await self.session.execute(query)
            match = result.scalar_one_or_none()

            if not match:
                self.logger.warning(f"Match {match_id} not found in database")
                return None

            match_dict = {
                "id": match.id,
                "home_team_id": match.home_team_id,
                "away_team_id": match.away_team_id,
                "home_score": match.home_score,
                "away_score": match.away_score,
                "status": match.status,
                "match_date": match.match_date.isoformat() if match.match_date else None,
                "venue": match.venue,
                "league_id": match.league_id,
                "season": match.season,
                "created_at": match.created_at.isoformat() if match.created_at else None,
                "updated_at": match.updated_at.isoformat() if match.updated_at else None,
            }

            self.logger.info(f"Successfully retrieved match {match_id} from database")
            return match_dict

        except Exception as e:
            self.logger.error(f"Error querying match {match_id} from database: {e}")
            raise e


def get_real_data_service(session: AsyncSession) -> RealDataService:
    """
    获取真实数据服务实例
    Get real data service instance.

    Args:
        session: 异步数据库会话

    Returns:
        RealDataService实例
    """
    return RealDataService(session)