"""
球队数据路由
Team Data Routes
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import select, and_, or_

from src.api.dependencies import get_current_user
from src.api.data.models.common import TeamInfo
from src.database.connection import get_async_session
from src.database.models import Team
from src.core.logging_system import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/", response_model=List[TeamInfo])
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
            return [_convert_team_to_info(team) for team in teams]

    except Exception as e:
        logger.error(f"获取球队列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取球队列表失败")


@router.get("/{team_id}", response_model=TeamInfo)
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
        async with get_async_session() as session:
            query = select(Team).where(Team.id == team_id)
            result = await session.execute(query)
            team = result.scalar_one_or_none()

            if not team:
                raise HTTPException(status_code=404, detail="球队不存在")

            return _convert_team_to_info(team)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取球队 {team_id} 详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取球队详情失败")


def _convert_team_to_info(team: Team) -> TeamInfo:
    """转换Team对象为TeamInfo"""
    return TeamInfo(
        id=team.id,
        name=team.team_name,
        country=team.country,
        founded_year=team.founded_year,
        stadium=team.stadium,
        logo_url=team.logo_url,
        is_active=team.is_active,
    )