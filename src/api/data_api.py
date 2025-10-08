"""
数据API端点
Data API Endpoints

提供完整的数据管理API接口，包括：
- 比赛数据查询
- 球队数据查询
- 联赛数据查询
- 比分和赔率数据
- 数据统计和分析

Provides complete data management API endpoints, including:
- Match data queries
- Team data queries
- League data queries
- Scores and odds data
- Data statistics and analysis
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel

from src.api.dependencies import get_current_user
from src.database.connection import get_async_session
from src.database.models import Match, League, Odds, MatchStatus
from src.core.logging_system import get_logger
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

logger = get_logger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/v1/data", tags=["data"])


# Pydantic模型
class TeamInfo(BaseModel):
    """球队信息模型"""

    id: int
    name: str
    country: Optional[str]
    founded_year: Optional[int]
    stadium: Optional[str]
    logo_url: Optional[str]
    is_active: bool


class LeagueInfo(BaseModel):
    """联赛信息模型"""

    id: int
    name: str
    country: str
    season: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    is_active: bool


class MatchInfo(BaseModel):
    """比赛信息模型"""

    id: int
    home_team: TeamInfo
    away_team: TeamInfo
    league: LeagueInfo
    match_time: datetime
    match_status: str
    venue: Optional[str]
    home_score: Optional[int]
    away_score: Optional[int]
    home_half_score: Optional[int]
    away_half_score: Optional[int]


class OddsInfo(BaseModel):
    """赔率信息模型"""

    match_id: int
    bookmaker: str
    market_type: str
    home_win_odds: Optional[float]
    draw_odds: Optional[float]
    away_win_odds: Optional[float]
    over_line: Optional[float]
    over_odds: Optional[float]
    under_odds: Optional[float]
    created_at: datetime


# API端点实现
@router.get("/matches", response_model=List[MatchInfo])
async def get_matches(
    league_id: Optional[int] = Query(None, description="联赛ID"),
    team_id: Optional[int] = Query(None, description="球队ID"),
    status: Optional[str] = Query(None, description="比赛状态"),
    start_date: Optional[datetime] = Query(None, description="开始日期"),
    end_date: Optional[datetime] = Query(None, description="结束日期"),
    limit: int = Query(50, description="返回数量限制", ge=1, le=1000),
    offset: int = Query(0, description="偏移量", ge=0),
    current_user: Dict = Depends(get_current_user),
):
    """
    获取比赛列表

    Args:
        league_id: 联赛ID
        team_id: 球队ID
        status: 比赛状态
        start_date: 开始日期
        end_date: 结束日期
        limit: 返回数量限制
        offset: 偏移量
        current_user: 当前用户

    Returns:
        List[MatchInfo]: 比赛列表
    """
    try:
        async with get_async_session() as session:
            # 构建查询
            query = select(Match).options(
                selectinload(Match.home_team),
                selectinload(Match.away_team),
                selectinload(Match.league),
            )

            # 应用过滤条件
            filters = []
            if league_id:
                filters.append(Match.league_id == league_id)
            if team_id:
                filters.append(
                    or_(
                        Match.home_team_id == team_id,
                        Match.away_team_id == team_id,
                    )
                )
            if status:
                try:
                    match_status = MatchStatus(status)
                    filters.append(Match.match_status == match_status)
                except ValueError:
                    raise HTTPException(
                        status_code=400, detail=f"无效的比赛状态: {status}"
                    )
            if start_date:
                filters.append(Match.match_time >= start_date)
            if end_date:
                filters.append(Match.match_time <= end_date)

            if filters:
                query = query.where(and_(*filters))

            # 排序和分页
            query = query.order_by(Match.match_time.desc()).offset(offset).limit(limit)

            result = await session.execute(query)
            matches = result.scalars().all()

            # 转换为响应模型
            match_list = []
            for match in matches:
                match_info = MatchInfo(
                    id=match.id,
                    home_team=TeamInfo(
                        id=match.home_team.id,
                        name=match.home_team.team_name,
                        country=match.home_team.country,
                        founded_year=match.home_team.founded_year,
                        stadium=match.home_team.stadium,
                        logo_url=match.home_team.logo_url,
                        is_active=match.home_team.is_active,
                    ),
                    away_team=TeamInfo(
                        id=match.away_team.id,
                        name=match.away_team.team_name,
                        country=match.away_team.country,
                        founded_year=match.away_team.founded_year,
                        stadium=match.away_team.stadium,
                        logo_url=match.away_team.logo_url,
                        is_active=match.away_team.is_active,
                    ),
                    league=LeagueInfo(
                        id=match.league.id,
                        name=match.league.league_name,
                        country=match.league.country,
                        season=match.league.season,
                        start_date=match.league.start_date,
                        end_date=match.league.end_date,
                        is_active=match.league.is_active,
                    ),
                    match_time=match.match_time,
                    match_status=match.match_status.value,
                    venue=match.venue,
                    home_score=match.home_score,
                    away_score=match.away_score,
                    home_half_score=match.home_half_score,
                    away_half_score=match.away_half_score,
                )
                match_list.append(match_info)

            return match_list

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取比赛列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取比赛列表失败")


@router.get("/matches/{match_id}", response_model=MatchInfo)
async def get_match_details(
    match_id: int = Path(..., description="比赛ID", gt=0),
    current_user: Dict = Depends(get_current_user),
):
    """
    获取比赛详情

    Args:
        match_id: 比赛ID
        current_user: 当前用户

    Returns:
        MatchInfo: 比赛详情
    """
    try:
        async with get_async_session() as session:
            query = (
                select(Match)
                .options(
                    selectinload(Match.home_team),
                    selectinload(Match.away_team),
                    selectinload(Match.league),
                )
                .where(Match.id == match_id)
            )

            result = await session.execute(query)
            match = result.scalar_one_or_none()

            if not match:
                raise HTTPException(status_code=404, detail="比赛不存在")

            return MatchInfo(
                id=match.id,
                home_team=TeamInfo(
                    id=match.home_team.id,
                    name=match.home_team.team_name,
                    country=match.home_team.country,
                    founded_year=match.home_team.founded_year,
                    stadium=match.home_team.stadium,
                    logo_url=match.home_team.logo_url,
                    is_active=match.home_team.is_active,
                ),
                away_team=TeamInfo(
                    id=match.away_team.id,
                    name=match.away_team.team_name,
                    country=match.away_team.country,
                    founded_year=match.away_team.founded_year,
                    stadium=match.away_team.stadium,
                    logo_url=match.away_team.logo_url,
                    is_active=match.away_team.is_active,
                ),
                league=LeagueInfo(
                    id=match.league.id,
                    name=match.league.league_name,
                    country=match.league.country,
                    season=match.league.season,
                    start_date=match.league.start_date,
                    end_date=match.league.end_date,
                    is_active=match.league.is_active,
                ),
                match_time=match.match_time,
                match_status=match.match_status.value,
                venue=match.venue,
                home_score=match.home_score,
                away_score=match.away_score,
                home_half_score=match.home_half_score,
                away_half_score=match.away_half_score,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取比赛 {match_id} 详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取比赛详情失败")


@router.get("/teams", response_model=List[TeamInfo])
async def get_teams(
    country: Optional[str] = Query(None, description="国家"),
    is_active: Optional[bool] = Query(None, description="是否活跃"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    limit: int = Query(100, description="返回数量限制", ge=1, le=1000),
    offset: int = Query(0, description="偏移量", ge=0),
    current_user: Dict = Depends(get_current_user),
):
    """
    获取球队列表

    Args:
        country: 国家
        is_active: 是否活跃
        search: 搜索关键词
        limit: 返回数量限制
        offset: 偏移量
        current_user: 当前用户

    Returns:
        List[TeamInfo]: 球队列表
    """
    try:
        from src.database.models import Team

        async with get_async_session() as session:
            query = select(Team)

            # 应用过滤条件
            filters = []
            if country:
                filters.append(Team.country.ilike(f"%{country}%"))
            if is_active is not None:
                filters.append(Team.is_active == is_active)
            if search:
                filters.append(
                    or_(
                        Team.team_name.ilike(f"%{search}%"),
                        Team.team_name_short.ilike(f"%{search}%"),
                    )
                )

            if filters:
                query = query.where(and_(*filters))

            # 排序和分页
            query = query.order_by(Team.team_name).offset(offset).limit(limit)

            result = await session.execute(query)
            teams = result.scalars().all()

            # 转换为响应模型
            team_list = []
            for team in teams:
                team_info = TeamInfo(
                    id=team.id,
                    name=team.team_name,
                    country=team.country,
                    founded_year=team.founded_year,
                    stadium=team.stadium,
                    logo_url=team.logo_url,
                    is_active=team.is_active,
                )
                team_list.append(team_info)

            return team_list

    except Exception as e:
        logger.error(f"获取球队列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取球队列表失败")


@router.get("/teams/{team_id}", response_model=TeamInfo)
async def get_team_details(
    team_id: int = Path(..., description="球队ID", gt=0),
    current_user: Dict = Depends(get_current_user),
):
    """
    获取球队详情

    Args:
        team_id: 球队ID
        current_user: 当前用户

    Returns:
        TeamInfo: 球队详情
    """
    try:
        from src.database.models import Team

        async with get_async_session() as session:
            query = select(Team).where(Team.id == team_id)
            result = await session.execute(query)
            team = result.scalar_one_or_none()

            if not team:
                raise HTTPException(status_code=404, detail="球队不存在")

            return TeamInfo(
                id=team.id,
                name=team.team_name,
                country=team.country,
                founded_year=team.founded_year,
                stadium=team.stadium,
                logo_url=team.logo_url,
                is_active=team.is_active,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取球队 {team_id} 详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取球队详情失败")


@router.get("/leagues", response_model=List[LeagueInfo])
async def get_leagues(
    country: Optional[str] = Query(None, description="国家"),
    season: Optional[str] = Query(None, description="赛季"),
    is_active: Optional[bool] = Query(None, description="是否活跃"),
    limit: int = Query(50, description="返回数量限制", ge=1, le=1000),
    offset: int = Query(0, description="偏移量", ge=0),
    current_user: Dict = Depends(get_current_user),
):
    """
    获取联赛列表

    Args:
        country: 国家
        season: 赛季
        is_active: 是否活跃
        limit: 返回数量限制
        offset: 偏移量
        current_user: 当前用户

    Returns:
        List[LeagueInfo]: 联赛列表
    """
    try:
        async with get_async_session() as session:
            query = select(League)

            # 应用过滤条件
            filters = []
            if country:
                filters.append(League.country.ilike(f"%{country}%"))
            if season:
                filters.append(League.season == season)
            if is_active is not None:
                filters.append(League.is_active == is_active)

            if filters:
                query = query.where(and_(*filters))

            # 排序和分页
            query = query.order_by(League.league_name).offset(offset).limit(limit)

            result = await session.execute(query)
            leagues = result.scalars().all()

            # 转换为响应模型
            league_list = []
            for league in leagues:
                league_info = LeagueInfo(
                    id=league.id,
                    name=league.league_name,
                    country=league.country,
                    season=league.season,
                    start_date=league.start_date,
                    end_date=league.end_date,
                    is_active=league.is_active,
                )
                league_list.append(league_info)

            return league_list

    except Exception as e:
        logger.error(f"获取联赛列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取联赛列表失败")


@router.get("/matches/{match_id}/odds", response_model=List[OddsInfo])
async def get_match_odds(
    match_id: int = Path(..., description="比赛ID", gt=0),
    bookmaker: Optional[str] = Query(None, description="博彩公司"),
    market_type: Optional[str] = Query(None, description="市场类型"),
    limit: int = Query(50, description="返回数量限制", ge=1, le=1000),
    current_user: Dict = Depends(get_current_user),
):
    """
    获取比赛赔率

    Args:
        match_id: 比赛ID
        bookmaker: 博彩公司
        market_type: 市场类型
        limit: 返回数量限制
        current_user: 当前用户

    Returns:
        List[OddsInfo]: 赔率列表
    """
    try:
        async with get_async_session() as session:
            query = select(Odds).where(Odds.match_id == match_id)

            # 应用过滤条件
            if bookmaker:
                query = query.where(Odds.bookmaker.ilike(f"%{bookmaker}%"))
            if market_type:
                query = query.where(Odds.market_type == market_type)

            # 排序和分页
            query = query.order_by(Odds.created_at.desc()).limit(limit)

            result = await session.execute(query)
            odds_list = result.scalars().all()

            # 转换为响应模型
            odds_response = []
            for odds in odds_list:
                odds_info = OddsInfo(
                    match_id=odds.match_id,
                    bookmaker=odds.bookmaker,
                    market_type=odds.market_type.value,
                    home_win_odds=odds.home_win_odds,
                    draw_odds=odds.draw_odds,
                    away_win_odds=odds.away_win_odds,
                    over_line=odds.over_line,
                    over_odds=odds.over_odds,
                    under_odds=odds.under_odds,
                    created_at=odds.created_at,
                )
                odds_response.append(odds_info)

            return odds_response

    except Exception as e:
        logger.error(f"获取比赛 {match_id} 赔率失败: {e}")
        raise HTTPException(status_code=500, detail="获取赔率失败")


@router.get("/statistics/overview")
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
            from src.database.models import Team

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
                from src.database.models import Team

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
                from src.database.models import Team

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
                            "founded_year": team.founded_year,
                            "stadium": team.stadium,
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
                        }
                    )

        return {
            "query": q,
            "results": results,
            "total": len(results["matches"])
            + len(results["teams"])
            + len(results["leagues"]),
        }

    except Exception as e:
        logger.error(f"搜索数据失败: {e}")
        raise HTTPException(status_code=500, detail="搜索数据失败")
