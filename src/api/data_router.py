"""
数据API端点（向后兼容）
Data API Endpoints (Backward Compatible)

Provides complete data management API endpoints, including:
- 比赛数据查询
- 球队数据查询
- 联赛数据查询
- 比分和赔率数据
- 数据统计和分析
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/data", tags=["data"])
logger = logging.getLogger(__name__)

# ============================================================================
# Pydantic Models
# ============================================================================


class LeagueInfo(BaseModel):
    """联赛信息"""

    id: int
    name: str
    country: str
    logo_url: Optional[str] = None
    season: Optional[str] = None


class TeamInfo(BaseModel):
    """球队信息"""

    id: int
    name: str
    short_name: Optional[str] = None
    logo_url: Optional[str] = None
    country: Optional[str] = None
    league_id: Optional[int] = None


class MatchInfo(BaseModel):
    """比赛信息"""

    id: int
    home_team_id: int
    away_team_id: int
    home_team_name: str
    away_team_name: str
    league_id: int
    league_name: str
    match_date: datetime
    status: str = Field(..., description="pending|live|finished|cancelled")
    home_score: Optional[int] = None
    away_score: Optional[int] = None


class OddsInfo(BaseModel):
    """赔率信息"""

    id: int
    match_id: int
    bookmaker: str
    home_win: float = Field(..., gt=1.0, description="主队获胜赔率")
    draw: float = Field(..., gt=1.0, description="平局赔率")
    away_win: float = Field(..., gt=1.0, description="客队获胜赔率")
    updated_at: datetime


class MatchStatistics(BaseModel):
    """比赛统计"""

    match_id: int
    possession_home: Optional[float] = None
    possession_away: Optional[float] = None
    shots_home: Optional[int] = None
    shots_away: Optional[int] = None
    shots_on_target_home: Optional[int] = None
    shots_on_target_away: Optional[int] = None
    corners_home: Optional[int] = None
    corners_away: Optional[int] = None


class TeamStatistics(BaseModel):
    """球队统计"""

    team_id: int
    matches_played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    points: int


# ============================================================================
# API Endpoints - Leagues
# ============================================================================


@router.get("/leagues", response_model=List[LeagueInfo])
async def get_leagues(
    country: Optional[str] = Query(None, description="国家筛选"),
    season: Optional[str] = Query(None, description="赛季"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
):
    """
    获取联赛列表

    支持按国家和赛季筛选联赛。
    """
    logger.info(f"获取联赛列表: country={country}, season={season}")

    try:
        # TODO: 从数据库获取实际数据
        leagues = [
            LeagueInfo(
                id=i,
                name=f"League {i}",
                country=country or f"Country{i}",
                season=season or "2024-25",
            )
            for i in range(1, min(limit + 1, 11))
        ]

        logger.info(f"成功获取 {len(leagues)} 个联赛")
        return leagues

    except Exception as e:
        logger.error(f"获取联赛失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取联赛失败: {str(e)}")


@router.get("/leagues/{league_id}", response_model=LeagueInfo)
async def get_league(league_id: int):
    """获取单个联赛详情"""
    logger.info(f"获取联赛 {league_id} 详情")

    try:
        # TODO: 从数据库获取
        league = LeagueInfo(
            id=league_id,
            name=f"League {league_id}",
            country="Example Country",
            season="2024-25",
        )
        return league
    except Exception as e:
        logger.error(f"获取联赛失败: {e}")
        raise HTTPException(status_code=404, detail="联赛不存在")


# ============================================================================
# API Endpoints - Teams
# ============================================================================


@router.get("/teams", response_model=List[TeamInfo])
async def get_teams(
    league_id: Optional[int] = Query(None, description="联赛ID"),
    country: Optional[str] = Query(None, description="国家"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    获取球队列表

    支持按联赛、国家筛选，或通过关键词搜索球队。
    """
    logger.info(f"获取球队列表: league_id={league_id}, search={search}")

    try:
        # TODO: 从数据库获取
        _teams = [
            TeamInfo(
                id=i,
                name=f"Team {i}",
                short_name=f"T{i}",
                country=country or "Country",
                league_id=league_id,
            )
            for i in range(1, min(limit + 1, 11))
        ]

        logger.info(f"成功获取 {len(_teams)} 支球队")
        return _teams

    except Exception as e:
        logger.error(f"获取球队失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取球队失败: {str(e)}")


@router.get("/teams/{team_id}", response_model=TeamInfo)
async def get_team(team_id: int):
    """获取单个球队详情"""
    logger.info(f"获取球队 {team_id} 详情")

    try:
        team = TeamInfo(
            id=team_id,
            name=f"Team {team_id}",
            short_name=f"T{team_id}",
            country="Example Country",
        )
        return team
    except Exception as e:
        logger.error(f"获取球队失败: {e}")
        raise HTTPException(status_code=404, detail="球队不存在")


@router.get("/teams/{team_id}/statistics", response_model=TeamStatistics)
async def get_team_statistics(
    team_id: int, season: Optional[str] = Query(None, description="赛季")
):
    """获取球队统计数据"""
    logger.info(f"获取球队 {team_id} 统计")

    try:
        stats = TeamStatistics(
            team_id=team_id,
            matches_played=30,
            wins=18,
            draws=6,
            losses=6,
            goals_for=55,
            goals_against=28,
            points=60,
        )
        return stats
    except Exception as e:
        logger.error(f"获取球队统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取统计失败")


# ============================================================================
# API Endpoints - Matches
# ============================================================================


@router.get("/matches", response_model=List[MatchInfo])
async def get_matches(
    league_id: Optional[int] = Query(None, description="联赛ID"),
    team_id: Optional[int] = Query(None, description="球队ID"),
    date_from: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    status: Optional[str] = Query(None, description="比赛状态"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    获取比赛列表

    支持按联赛、球队、日期范围、状态筛选比赛。
    """
    logger.info(f"获取比赛列表: league_id={league_id}, team_id={team_id}")

    try:
        # TODO: 从数据库获取
        _matches = [
            MatchInfo(
                id=i,
                home_team_id=i * 2,
                away_team_id=i * 2 + 1,
                home_team_name=f"Home Team {i}",
                away_team_name=f"Away Team {i}",
                league_id=league_id or 1,
                league_name=f"League {league_id or 1}",
                match_date=datetime.utcnow() + timedelta(days=i),
                status="pending",
            )
            for i in range(1, min(limit + 1, 11))
        ]

        logger.info(f"成功获取 {len(_matches)} 场比赛")
        return _matches

    except Exception as e:
        logger.error(f"获取比赛失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取比赛失败: {str(e)}")


@router.get("/matches/{match_id}", response_model=MatchInfo)
async def get_match(match_id: int):
    """获取单场比赛详情"""
    logger.info(f"获取比赛 {match_id} 详情")

    try:
        match = MatchInfo(
            id=match_id,
            home_team_id=1,
            away_team_id=2,
            home_team_name="Home Team",
            away_team_name="Away Team",
            league_id=1,
            league_name="Example League",
            match_date=datetime.utcnow() + timedelta(days=1),
            status="pending",
        )
        return match
    except Exception as e:
        logger.error(f"获取比赛失败: {e}")
        raise HTTPException(status_code=404, detail="比赛不存在")


@router.get("/matches/{match_id}/statistics", response_model=MatchStatistics)
async def get_match_statistics(match_id: int):
    """获取比赛统计数据"""
    logger.info(f"获取比赛 {match_id} 统计")

    try:
        stats = MatchStatistics(
            match_id=match_id,
            possession_home=55.5,
            possession_away=44.5,
            shots_home=15,
            shots_away=10,
            shots_on_target_home=6,
            shots_on_target_away=4,
            corners_home=8,
            corners_away=5,
        )
        return stats
    except Exception as e:
        logger.error(f"获取比赛统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取统计失败")


# ============================================================================
# API Endpoints - Odds
# ============================================================================


@router.get("/odds", response_model=List[OddsInfo])
async def get_odds(
    match_id: Optional[int] = Query(None, description="比赛ID"),
    bookmaker: Optional[str] = Query(None, description="博彩公司"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    获取赔率数据

    支持按比赛和博彩公司筛选赔率。
    """
    logger.info(f"获取赔率数据: match_id={match_id}, bookmaker={bookmaker}")

    try:
        odds = [
            OddsInfo(
                id=i,
                match_id=match_id or i,
                bookmaker=bookmaker or f"Bookmaker{i}",
                home_win=1.85 + i * 0.1,
                draw=3.20,
                away_win=4.50 - i * 0.1,
                updated_at=datetime.utcnow(),
            )
            for i in range(1, min(limit + 1, 6))
        ]

        logger.info(f"成功获取 {len(odds)} 条赔率数据")
        return odds

    except Exception as e:
        logger.error(f"获取赔率失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取赔率失败: {str(e)}")


@router.get("/odds/{match_id}", response_model=List[OddsInfo])
async def get_match_odds(match_id: int):
    """获取指定比赛的所有赔率"""
    logger.info(f"获取比赛 {match_id} 的赔率")

    try:
        odds = [
            OddsInfo(
                id=i,
                match_id=match_id,
                bookmaker=f"Bookmaker{i}",
                home_win=1.85 + i * 0.05,
                draw=3.20,
                away_win=4.50 - i * 0.05,
                updated_at=datetime.utcnow(),
            )
            for i in range(1, 4)
        ]
        return odds
    except Exception as e:
        logger.error(f"获取赔率失败: {e}")
        raise HTTPException(status_code=500, detail="获取赔率失败")


# 导出所有必要的符号以保持兼容性
__all__ = [
    "router",
    "TeamInfo",
    "LeagueInfo",
    "MatchInfo",
    "OddsInfo",
]
