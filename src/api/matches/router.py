"""比赛API路由器
Matches API Router.

提供比赛相关的API路由，使用新的DAO层。
"""

import logging
from datetime import datetime, timedelta
from typing import Any, list, Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

# 导入DAO层
from src.database.dao.match_dao import MatchDAO
from src.database.models.match import Match
from src.database.async_manager import get_db_session

# 导入标准响应模型
from src.api.schemas import StandardResponse, PaginatedResponse

# 创建路由器
router = APIRouter(prefix="/matches", tags=["matches"])

logger = logging.getLogger(__name__)

# ============================================================================
# Pydantic Models
# ============================================================================

class MatchResponse(BaseModel):
    """比赛响应模型"""
    id: int = Field(..., description="比赛ID")
    home_team_id: int = Field(..., description="主队ID")
    away_team_id: int = Field(..., description="客队ID")
    home_team_name: str = Field(..., description="主队名称")
    away_team_name: str = Field(..., description="客队名称")
    league_id: Optional[int] = Field(None, description="联赛ID")
    match_time: datetime = Field(..., description="比赛时间")
    match_date: Optional[datetime] = Field(None, description="比赛日期")
    venue: Optional[str] = Field(None, description="比赛场地")
    status: str = Field(..., description="比赛状态")
    home_score: Optional[int] = Field(0, description="主队得分")
    away_score: Optional[int] = Field(0, description="客队得分")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    class Config:
        from_attributes = True

class UpcomingMatchesParams(BaseModel):
    """即将开始的比赛查询参数"""
    hours: int = Field(default=24, ge=1, le=168, description="未来小时数 (1-168)")
    limit: int = Field(default=50, ge=1, le=100, description="返回数量限制 (1-100)")
    league_id: Optional[int] = Field(None, description="联赛ID过滤")

# ============================================================================
# API Routes
# ============================================================================

@router.get("/upcoming", response_model=StandardResponse[list[MatchResponse]])
async def get_upcoming_matches(
    hours: int = Query(default=24, ge=1, le=168, description="未来小时数"),
    limit: int = Query(default=50, ge=1, le=100, description="返回数量限制"),
    league_id: Optional[int] = Query(default=None, description="联赛ID过滤"),
    session: AsyncSession = Depends(get_db_session)
) -> StandardResponse[list[MatchResponse]]:
    """
    获取即将开始的比赛列表

    使用新的DAO层进行数据库访问，展示统一数据访问层的集成。
    """
    try:
        # 初始化MatchDAO
        match_dao = MatchDAO(model=Match, session=session)

        # 调用DAO的业务方法
        upcoming_matches = await match_dao.get_upcoming_matches(
            hours=hours,
            limit=limit,
            league_id=league_id
        )

        # 转换为响应模型
        match_responses = [MatchResponse.model_validate(match) for match in upcoming_matches]

        logger.info(f"获取到{len(match_responses)}场即将开始的比赛")

        return StandardResponse(
            success=True,
            message=f"成功获取{len(match_responses)}场即将开始的比赛",
            data=match_responses
        )

    except Exception as e:
        logger.error(f"获取即将开始的比赛失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取比赛数据失败: {str(e)}")

@router.get("/live", response_model=StandardResponse[list[MatchResponse]])
async def get_live_matches(
    session: AsyncSession = Depends(get_db_session)
) -> StandardResponse[list[MatchResponse]]:
    """
    获取正在进行的比赛列表

    使用DAO层获取状态为'live'的比赛。
    """
    try:
        # 初始化MatchDAO
        match_dao = MatchDAO(model=Match, session=session)

        # 调用DAO的业务方法
        live_matches = await match_dao.get_live_matches()

        # 转换为响应模型
        match_responses = [MatchResponse.model_validate(match) for match in live_matches]

        logger.info(f"获取到{len(match_responses)}场正在进行的比赛")

        return StandardResponse(
            success=True,
            message=f"成功获取{len(match_responses)}场正在进行的比赛",
            data=match_responses
        )

    except Exception as e:
        logger.error(f"获取正在进行的比赛失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取比赛数据失败: {str(e)}")

@router.get("/search", response_model=StandardResponse[list[MatchResponse]])
async def search_matches(
    keyword: str = Query(..., min_length=2, max_length=50, description="搜索关键词"),
    league_id: Optional[int] = Query(default=None, description="联赛ID过滤"),
    limit: int = Query(default=50, ge=1, le=100, description="返回数量限制"),
    session: AsyncSession = Depends(get_db_session)
) -> StandardResponse[list[MatchResponse]]:
    """
    搜索比赛

    根据球队名称搜索比赛，使用DAO层的搜索功能。
    """
    try:
        # 初始化MatchDAO
        match_dao = MatchDAO(model=Match, session=session)

        # 调用DAO的业务方法
        search_results = await match_dao.search_matches(
            keyword=keyword,
            league_id=league_id,
            limit=limit
        )

        # 转换为响应模型
        match_responses = [MatchResponse.model_validate(match) for match in search_results]

        logger.info(f"搜索关键词'{keyword}'找到{len(match_responses)}场比赛")

        return StandardResponse(
            success=True,
            message=f"搜索关键词'{keyword}'找到{len(match_responses)}场比赛",
            data=match_responses
        )

    except Exception as e:
        logger.error(f"搜索比赛失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索比赛失败: {str(e)}")

@router.get("/{match_id}", response_model=StandardResponse[MatchResponse])
async def get_match_by_id(
    match_id: int,
    session: AsyncSession = Depends(get_db_session)
) -> StandardResponse[MatchResponse]:
    """
    根据ID获取比赛详情

    使用DAO层的基础CRUD方法获取单个比赛。
    """
    try:
        # 初始化MatchDAO
        match_dao = MatchDAO(model=Match, session=session)

        # 调用DAO的基础方法
        match = await match_dao.get(match_id)

        if not match:
            raise HTTPException(status_code=404, detail=f"比赛ID {match_id} 不存在")

        # 转换为响应模型
        match_response = MatchResponse.model_validate(match)

        logger.info(f"获取比赛详情成功: ID={match_id}")

        return StandardResponse(
            success=True,
            message="成功获取比赛详情",
            data=match_response
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取比赛详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取比赛详情失败: {str(e)}")

@router.get("/", response_model=StandardResponse[list[MatchResponse]])
async def get_matches(
    league_id: Optional[int] = Query(default=None, description="联赛ID过滤"),
    status: Optional[str] = Query(default=None, description="比赛状态过滤"),
    skip: int = Query(default=0, ge=0, description="跳过数量"),
    limit: int = Query(default=50, ge=1, le=100, description="返回数量限制"),
    session: AsyncSession = Depends(get_db_session)
) -> StandardResponse[list[MatchResponse]]:
    """
    获取比赛列表

    使用DAO层的通用查询方法，支持多种过滤条件。
    """
    try:
        # 初始化MatchDAO
        match_dao = MatchDAO(model=Match, session=session)

        # 构建过滤条件
        filters = {}
        if league_id:
            filters['league_id'] = league_id
        if status:
            filters['status'] = status

        # 调用DAO的通用查询方法
        matches = await match_dao.get_multi(
            skip=skip,
            limit=limit,
            filters=filters,
            order_by="-match_time"  # 按时间降序
        )

        # 转换为响应模型
        match_responses = [MatchResponse.model_validate(match) for match in matches]

        logger.info(f"获取比赛列表成功: {len(match_responses)}条记录")

        return StandardResponse(
            success=True,
            message=f"成功获取{len(match_responses)}场比赛",
            data=match_responses
        )

    except Exception as e:
        logger.error(f"获取比赛列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取比赛列表失败: {str(e)}")
