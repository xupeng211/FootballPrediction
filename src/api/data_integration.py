"""
数据集成API端点
提供数据收集和管理的API接口
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.cache.redis_manager import RedisManager, get_redis_manager
from src.collectors.data_sources import data_source_manager
from src.collectors.enhanced_fixtures_collector import EnhancedFixturesCollector
from src.core.logging_system import get_logger
from src.database.connection import get_async_session
from src.database.models.match import Match
from src.database.models.team import Team

from .schemas.data import (
    DataCollectionRequest,
    DataCollectionResponse,
    DataSourceStatusResponse,
    MatchResponse,
    TeamResponse,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/data", tags=["data-integration"])


@router.post("/collect/matches", response_model=DataCollectionResponse)
async def collect_matches(
    request: DataCollectionRequest,
    background_tasks: BackgroundTasks,
    db_session: AsyncSession = Depends(get_async_session),
    redis_client: RedisManager = Depends(get_redis_manager),
):
    """
    收集比赛数据
    """
    try:
        collector = EnhancedFixturesCollector(db_session, redis_client)

        if request.collection_type == "all":
            # 收集所有比赛
            fixtures = await collector.collect_all_fixtures(
                days_ahead=request.days_ahead,
                force_refresh=request.force_refresh,
                preferred_source=request.data_source,
            )
        elif request.collection_type == "team" and request.team_name:
            # 收集指定球队的比赛
            fixtures = await collector.collect_team_fixtures(
                team_name=request.team_name,
                days_ahead=request.days_ahead,
                force_refresh=request.force_refresh,
                preferred_source=request.data_source,
            )
        elif request.collection_type == "league" and request.league_name:
            # 收集指定联赛的比赛
            fixtures = await collector.collect_league_fixtures(
                league_name=request.league_name,
                days_ahead=request.days_ahead,
                force_refresh=request.force_refresh,
                preferred_source=request.data_source,
            )
        else:
            raise HTTPException(status_code=400, detail="无效的收集参数")
        return DataCollectionResponse(
            success=True,
            message=f"成功收集 {len(fixtures)} 场比赛",
            collected_count=len(fixtures),
            data_source=request.data_source,
            collection_type=request.collection_type,
        )

    except Exception as e:
        logger.error(f"收集比赛数据失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"收集比赛数据失败: {str(e)}"
        ) from e  # TODO: B904 exception chaining


@router.post("/collect/teams", response_model=DataCollectionResponse)
async def collect_teams(
    request: DataCollectionRequest,
    background_tasks: BackgroundTasks,
    db_session: AsyncSession = Depends(get_async_session),
    redis_client: RedisManager = Depends(get_redis_manager),
):
    """
    收集球队数据
    """
    try:
        collector = EnhancedFixturesCollector(db_session, redis_client)

        teams = await collector.collect_teams(
            league_name=getattr(request, "league_name", None),
            force_refresh=request.force_refresh,
            preferred_source=request.data_source,
        )

        return DataCollectionResponse(
            success=True,
            message=f"成功收集 {len(teams)} 支球队信息",
            collected_count=len(teams),
            data_source=request.data_source,
            collection_type="teams",
        )

    except Exception as e:
        logger.error(f"收集球队数据失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"收集球队数据失败: {str(e)}"
        ) from e


@router.post("/collect/all", response_model=DataCollectionResponse)
async def collect_all_data(
    background_tasks: BackgroundTasks,
    db_session: AsyncSession = Depends(get_async_session),
    redis_client: RedisManager = Depends(get_redis_manager),
    days_ahead: int = 30,
    force_refresh: bool = False,
    data_source: str = "mock",
):
    """
    收集所有数据（比赛和球队）
    """
    try:
        collector = EnhancedFixturesCollector(db_session, redis_client)

        # 收集球队数据
        teams = await collector.collect_teams(
            force_refresh=force_refresh, preferred_source=data_source
        )

        # 收集比赛数据
        fixtures = await collector.collect_all_fixtures(
            days_ahead=days_ahead,
            force_refresh=force_refresh,
            preferred_source=data_source,
        )

        total_count = len(teams) + len(fixtures)

        return DataCollectionResponse(
            success=True,
            message=f"成功收集 {len(teams)} 支球队和 {len(fixtures)} 场比赛",
            collected_count=total_count,
            data_source=data_source,
            collection_type="all",
        )

    except Exception as e:
        logger.error(f"收集所有数据失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"收集所有数据失败: {str(e)}"
        ) from e  # TODO: B904 exception chaining


@router.get("/sources/status", response_model=DataSourceStatusResponse)
async def get_data_source_status(
    db_session: AsyncSession = Depends(get_async_session),
    redis_client: RedisManager = Depends(get_redis_manager),
):
    """
    获取数据源状态
    """
    try:
        collector = EnhancedFixturesCollector(db_session, redis_client)
        status = await collector.get_data_source_status()

        # 添加数据库统计信息
        match_count_query = select(Match).where(
            Match.match_date >= datetime.now() - timedelta(days=30)
        )
        recent_matches_count = len(
            await db_session.execute(match_count_query).scalars().all()
        )

        team_count_query = select(Team)
        total_teams_count = len(
            await db_session.execute(team_count_query).scalars().all()
        )

        return DataSourceStatusResponse(
            available_sources=status["available_sources"],
            primary_source=status["primary_source"],
            database_matches=recent_matches_count,
            database_teams=total_teams_count,
            last_update=status["last_update"],
            is_healthy=len(status["available_sources"]) > 0,
        )

    except Exception as e:
        logger.error(f"获取数据源状态失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取数据源状态失败: {str(e)}"
        ) from e


@router.get("/matches", response_model=list[MatchResponse])
async def get_matches(
    league: str | None = None,
    team: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db_session: AsyncSession = Depends(get_async_session),
):
    """
    获取比赛列表
    """
    try:
        query = select(Match)

        # 添加过滤条件
        if league:
            query = query.where(Match.league.ilike(f"%{league}%"))
        if team:
            query = query.where(
                (Match.home_team.ilike(f"%{team}%"))
                | (Match.away_team.ilike(f"%{team}%"))
            )
        if status:
            query = query.where(Match.status == status)

        # 添加排序和分页
        query = query.order_by(Match.match_date).offset(offset).limit(limit)

        matches = await db_session.execute(query).scalars().all()

        return [
            MatchResponse(
                id=match.id,
                home_team=match.home_team,
                away_team=match.away_team,
                match_date=match.match_date,
                league=match.league,
                status=match.status,
                home_score=match.home_score,
                away_score=match.away_score,
                venue=match.venue,
            )
            for match in matches
        ]

    except Exception as e:
        logger.error(f"获取比赛列表失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取比赛列表失败: {str(e)}"
        ) from e  # TODO: B904 exception chaining


@router.get("/teams", response_model=list[TeamResponse])
async def get_teams(
    league: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db_session: AsyncSession = Depends(get_async_session),
):
    """
    获取球队列表
    """
    try:
        query = select(Team)

        # 添加过滤条件
        if league:
            # 这里可以根据实际需要添加联赛过滤逻辑
            pass

        # 添加排序和分页
        query = query.order_by(Team.name).offset(offset).limit(limit)

        teams = await db_session.execute(query).scalars().all()

        return [
            TeamResponse(
                id=team.id,
                name=team.name,
                short_name=team.short_name,
                venue=team.venue,
                website=team.website,
            )
            for team in teams
        ]

    except Exception as e:
        logger.error(f"获取球队列表失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取球队列表失败: {str(e)}"
        ) from e


@router.get("/stats", response_model=dict[str, Any])
async def get_data_stats(
    db_session: AsyncSession = Depends(get_async_session),
    redis_client: RedisManager = Depends(get_redis_manager),
):
    """
    获取数据统计信息
    """
    try:
        stats = {}

        # 比赛统计
        total_matches_query = select(Match)
        total_matches = len(
            await db_session.execute(total_matches_query).scalars().all()
        )
        stats["total_matches"] = total_matches

        # 按状态分组统计
        upcoming_matches_query = select(Match).where(Match.status == "upcoming")
        upcoming_matches = len(
            await db_session.execute(upcoming_matches_query).scalars().all()
        )
        stats["upcoming_matches"] = upcoming_matches

        live_matches_query = select(Match).where(Match.status == "live")
        live_matches = len(await db_session.execute(live_matches_query).scalars().all())
        stats["live_matches"] = live_matches

        finished_matches_query = select(Match).where(Match.status == "finished")
        finished_matches = len(
            await db_session.execute(finished_matches_query).scalars().all()
        )
        stats["finished_matches"] = finished_matches

        # 球队统计
        total_teams_query = select(Team)
        total_teams = len(await db_session.execute(total_teams_query).scalars().all())
        stats["total_teams"] = total_teams

        # 联赛统计
        league_stats_query = select(Match.league).distinct()
        leagues = await db_session.execute(league_stats_query).scalars().all()
        stats["total_leagues"] = len(leagues)

        # 数据源状态
        collector = EnhancedFixturesCollector(db_session, redis_client)
        source_status = await collector.get_data_source_status()
        stats["data_source"] = source_status

        stats["last_updated"] = datetime.now().isoformat()

        return stats

    except Exception as e:
        logger.error(f"获取数据统计失败: {e}")
        raise HTTPException(
            status_code=500, detail=f"获取数据统计失败: {str(e)}"
        ) from e  # TODO: B904 exception chaining


@router.post("/test-data-source")
async def test_data_source(
    data_source: str = "mock",
    db_session: AsyncSession = Depends(get_async_session),
    redis_client: RedisManager = Depends(get_redis_manager),
):
    """
    测试数据源连接
    """
    try:
        adapter = data_source_manager.get_adapter(data_source)
        if not adapter:
            raise HTTPException(status_code=404, detail=f"数据源 {data_source} 不可用")
        # 测试获取少量数据
        matches = await adapter.get_matches()
        teams = await adapter.get_teams()

        return {
            "success": True,
            "data_source": data_source,
            "test_matches": len(matches),
            "test_teams": len(teams),
            "message": f"数据源 {data_source} 测试成功",
        }

    except Exception as e:
        logger.error(f"测试数据源失败: {e}")
        return {
            "success": False,
            "data_source": data_source,
            "error": str(e),
            "message": f"数据源 {data_source} 测试失败",
        }
