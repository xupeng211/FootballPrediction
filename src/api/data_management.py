"""
数据管理API路由
Data Management API Router

提供数据管理相关的API端点：
- 比赛数据管理
- 球队数据管理
- 联赛数据管理
- 赔率数据管理

Provides data management API endpoints:
- Match data management
- Team data management
- League data management
- Odds data management
"""

from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["数据管理"])


@router.get("/matches")
async def get_matches_list(limit: int = 20, offset: int = 0) -> dict[str, Any]:
    """
    获取比赛列表
    Get matches list

    Args:
        limit: 返回数量限制
        offset: 偏移量

    Returns:
        比赛列表信息
    """
    try:
        from src.services.data import get_data_service

        data_service = get_data_service()
        matches_data = data_service.get_matches_list(limit=limit, offset=offset)

        return matches_data

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"获取比赛列表失败: {str(e)}"
        ) from e


@router.get("/matches/{match_id}")
async def get_match_by_id(match_id: int) -> dict[str, Any]:
    """
    根据ID获取比赛信息
    Get match information by ID

    Args:
        match_id: 比赛ID

    Returns:
        比赛信息
    """
    try:
        from src.services.data import get_data_service

        data_service = get_data_service()
        match_data = data_service.get_match_by_id(match_id)

        if match_data is None:
            raise HTTPException(status_code=404, detail=f"比赛ID {match_id} 不存在")

        return match_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"获取比赛信息失败: {str(e)}"
        ) from e


@router.get("/teams")
async def get_teams_list(limit: int = 20, offset: int = 0) -> dict[str, Any]:
    """
    获取球队列表
    Get teams list

    Args:
        limit: 返回数量限制
        offset: 偏移量

    Returns:
        球队列表信息
    """
    try:
        from src.services.data import get_data_service

        data_service = get_data_service()
        teams_data = data_service.get_teams_list(limit=limit, offset=offset)

        return teams_data

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"获取球队列表失败: {str(e)}"
        ) from e


@router.get("/teams/{team_id}")
async def get_team_by_id(team_id: int) -> dict[str, Any]:
    """
    根据ID获取球队信息
    Get team information by ID

    Args:
        team_id: 球队ID

    Returns:
        球队信息
    """
    try:
        from src.services.data import get_data_service

        data_service = get_data_service()
        team_data = data_service.get_team_by_id(team_id)

        if team_data is None:
            raise HTTPException(status_code=404, detail=f"球队ID {team_id} 不存在")

        return team_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"获取球队信息失败: {str(e)}"
        ) from e


@router.get("/leagues")
async def get_leagues_list(limit: int = 20, offset: int = 0) -> dict[str, Any]:
    """
    获取联赛列表
    Get leagues list

    Args:
        limit: 返回数量限制
        offset: 偏移量

    Returns:
        联赛列表信息
    """
    try:
        from src.services.data import get_data_service

        data_service = get_data_service()
        leagues_data = data_service.get_leagues_list(limit=limit, offset=offset)

        return leagues_data

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"获取联赛列表失败: {str(e)}"
        ) from e


@router.get("/odds")
async def get_odds_data(match_id: int | None = None) -> dict[str, Any]:
    """
    获取赔率数据
    Get odds data

    Args:
        match_id: 可选的比赛ID过滤

    Returns:
        赔率数据
    """
    try:
        from src.services.data import get_data_service

        data_service = get_data_service()
        odds_data = data_service.get_odds_data(match_id=match_id)

        return odds_data

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"获取赔率数据失败: {str(e)}"
        ) from e
