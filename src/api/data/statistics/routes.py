"""
统计数据路由
Statistics Data Routes
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, or_
from sqlalchemy.orm import selectinload

from src.api.dependencies import get_current_user
from src.database.connection import get_async_session
from src.database.models import Match, Team, League, Odds, MatchStatus
from src.core.logging_system import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/overview")
async def get_data_statistics(
    current_user: Dict = Depends(get_current_user),
):
    """
    获取数据统计概览

    Args:
        current_user: 当前用户

    Returns:
        Dict: 统计概览
    """
    try:
        async with get_async_session() as session:
            # 统计比赛数量
            total_matches = await session.scalar(select(func.count(Match.id)))
            scheduled_matches = await session.scalar(
                select(func.count(Match.id)).where(
                    Match.match_status == MatchStatus.SCHEDULED
                )
            )
            live_matches = await session.scalar(
                select(func.count(Match.id)).where(
                    Match.match_status == MatchStatus.IN_PROGRESS
                )
            )
            finished_matches = await session.scalar(
                select(func.count(Match.id)).where(
                    Match.match_status == MatchStatus.FINISHED
                )
            )

            # 统计球队数量
            total_teams = await session.scalar(select(func.count(Team.id)))
            active_teams = await session.scalar(
                select(func.count(Team.id)).where(Team.is_active.is_(True))
            )

            # 统计联赛数量
            total_leagues = await session.scalar(select(func.count(League.id)))
            active_leagues = await session.scalar(
                select(func.count(League.id)).where(League.is_active.is_(True))
            )

            # 统计赔率数量
            total_odds = await session.scalar(select(func.count(Odds.id)))

            # 最近7天的活动
            seven_days_ago = datetime.now() - timedelta(days=7)
            recent_matches = await session.scalar(
                select(func.count(Match.id)).where(Match.match_time >= seven_days_ago)
            )

            return {
                "matches": {
                    "total": total_matches,
                    "scheduled": scheduled_matches,
                    "live": live_matches,
                    "finished": finished_matches,
                    "recent_7_days": recent_matches,
                },
                "teams": {
                    "total": total_teams,
                    "active": active_teams,
                },
                "leagues": {
                    "total": total_leagues,
                    "active": active_leagues,
                },
                "odds": {
                    "total": total_odds,
                },
                "last_updated": datetime.now().isoformat(),
            }

    except Exception as e:
        logger.error(f"获取数据统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取数据统计失败")


@router.get("/search")
async def search_data(
    q: str = Query(..., description="搜索关键词", min_length=2),
    type: Optional[str] = Query(None, description="搜索类型: matches, teams, leagues"),
    limit: int = Query(20, description="返回数量限制", ge=1, le=100),
    current_user: Dict = Depends(get_current_user),
):
    """
    搜索数据

    Args:
        q: 搜索关键词
        type: 搜索类型
        limit: 返回数量限制
        current_user: 当前用户

    Returns:
        Dict: 搜索结果
    """
    try:
        results = {
            "matches": [],
            "teams": [],
            "leagues": [],
        }

        async with get_async_session() as session:
            # 搜索比赛
            if type is None or type == "matches":
                match_query = (
                    select(Match)
                    .options(
                        selectinload(Match.home_team),
                        selectinload(Match.away_team),
                        selectinload(Match.league),
                    )
                    .join(Team, Match.home_team_id == Team.id)
                    .where(
                        or_(
                            Team.team_name.ilike(f"%{q}%"),
                            Match.venue.ilike(f"%{q}%"),
                        )
                    )
                    .limit(limit)
                )

                match_result = await session.execute(match_query)
                matches = match_result.scalars().all()

                for match in matches:
                    results["matches"].append(
                        {
                            "id": match.id,
                            "home_team": match.home_team.team_name,
                            "away_team": match.away_team.team_name,
                            "league": match.league.league_name,
                            "match_time": match.match_time.isoformat(),
                            "status": match.match_status.value,
                        }
                    )

            # 搜索球队
            if type is None or type == "teams":
                team_query = (
                    select(Team)
                    .where(
                        or_(
                            Team.team_name.ilike(f"%{q}%"),
                            Team.team_name_short.ilike(f"%{q}%"),
                            Team.country.ilike(f"%{q}%"),
                        )
                    )
                    .limit(limit)
                )

                team_result = await session.execute(team_query)
                teams = team_result.scalars().all()

                for team in teams:
                    results["teams"].append(
                        {
                            "id": team.id,
                            "name": team.team_name,
                            "country": team.country,
                            "is_active": team.is_active,
                        }
                    )

            # 搜索联赛
            if type is None or type == "leagues":
                league_query = (
                    select(League)
                    .where(
                        or_(
                            League.league_name.ilike(f"%{q}%"),
                            League.country.ilike(f"%{q}%"),
                            League.season.ilike(f"%{q}%"),
                        )
                    )
                    .limit(limit)
                )

                league_result = await session.execute(league_query)
                leagues = league_result.scalars().all()

                for league in leagues:
                    results["leagues"].append(
                        {
                            "id": league.id,
                            "name": league.league_name,
                            "country": league.country,
                            "season": league.season,
                            "is_active": league.is_active,
                        }
                    )

        return results

    except Exception as e:
        logger.error(f"搜索数据失败: {e}")
        raise HTTPException(status_code=500, detail="搜索数据失败")