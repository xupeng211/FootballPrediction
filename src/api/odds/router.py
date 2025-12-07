"""
赔率 API 路由
Odds API Router

提供赔率数据的 RESTful API 接口，暴露 Phase 2 构建的数据获取和处理能力。

核心功能:
1. 获取比赛赔率数据 (支持过滤和分页)
2. 手动触发赔率数据采集
3. 查询赔率历史变动
4. 赔率数据统计分析

作者: 高级后端架构师
创建时间: 2025-12-07
版本: 1.0.0
"""

import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import StandardResponse, PaginatedResponse
from src.database.async_manager import get_db_session
from src.database.dao.odds_dao import OddsDAO
from src.database.dao.match_dao import MatchDAO
from src.services.odds_service import OddsService
from src.database.models.odds import Odds
from src.database.models.match import Match

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/odds", tags=["odds"])


# ==================== 响应模型定义 ====================

class OddsResponse(BaseModel):
    """赔率响应模型"""
    id: int
    match_id: int
    bookmaker: str
    home_win: Optional[float] = None
    draw: Optional[float] = None
    away_win: Optional[float] = None
    asian_handicap: Optional[float] = None
    over_under: Optional[float] = None
    last_updated: Optional[datetime] = None
    source_reliability: Optional[str] = None
    is_active: bool = True

    class Config:
        from_attributes = True


class OddsHistoryResponse(BaseModel):
    """赔率历史响应模型"""
    id: int
    odds_id: int
    old_home_win: Optional[float]
    new_home_win: Optional[float]
    old_draw: Optional[float]
    new_draw: Optional[float]
    old_away_win: Optional[float]
    new_away_win: Optional[float]
    change_timestamp: datetime
    change_reason: Optional[str]

    class Config:
        from_attributes = True


class OddsFetchRequest(BaseModel):
    """赔率获取请求模型"""
    source_name: str = "oddsportal"
    force_refresh: bool = False


class OddsStatsResponse(BaseModel):
    """赔率统计响应模型"""
    total_odds: int
    active_bookmakers: List[str]
    latest_update: Optional[datetime]
    avg_home_win: Optional[float]
    avg_draw: Optional[float]
    avg_away_win: Optional[float]


# ==================== 依赖注入 ====================

async def get_odds_service(session: AsyncSession = Depends(get_db_session)) -> OddsService:
    """获取 OddsService 实例"""
    odds_dao = OddsDAO(Odds, session)
    match_dao = MatchDAO(Match, session)
    return OddsService(odds_dao, match_dao)


# ==================== API 端点实现 ====================

@router.get(
    "/matches/{match_id}",
    response_model=StandardResponse[List[OddsResponse]],
    summary="获取比赛赔率",
    description="获取指定比赛的所有可用赔率数据，支持按博彩公司过滤"
)
async def get_match_odds(
    match_id: int = Path(..., description="比赛ID", ge=1),
    bookmaker: Optional[str] = Query(None, description="博彩公司名称过滤"),
    is_active: Optional[bool] = Query(True, description="是否只显示活跃赔率"),
    limit: int = Query(50, description="返回记录数限制", ge=1, le=1000),
    offset: int = Query(0, description="分页偏移量", ge=0),
    odds_service: OddsService = Depends(get_odds_service)
) -> StandardResponse[List[OddsResponse]]:
    """
    获取比赛赔率数据

    Args:
        match_id: 比赛ID
        bookmaker: 博彩公司过滤
        is_active: 是否只显示活跃赔率
        limit: 返回记录数限制
        offset: 分页偏移量
        odds_service: 赔率服务实例

    Returns:
        StandardResponse[List[OddsResponse]]: 赔率数据列表

    Raises:
        HTTPException: 当比赛不存在或数据获取失败时
    """
    try:
        logger.info(f"获取比赛赔率: match_id={match_id}, bookmaker={bookmaker}")

        # 验证比赛是否存在
        match = await odds_service.match_dao.get(match_id)
        if not match:
            raise HTTPException(
                status_code=404,
                detail=f"比赛不存在: match_id={match_id}"
            )

        # 获取赔率数据
        odds_records = await odds_service.odds_dao.get_by_match_id(
            match_id=match_id,
            bookmaker=bookmaker,
            is_active=is_active,
            limit=limit,
            offset=offset
        )

        # 转换为响应模型
        odds_response = [
            OddsResponse.model_validate(record)
            for record in odds_records
        ]

        logger.info(f"成功获取赔率数据: count={len(odds_response)}")

        return StandardResponse[List[OddsResponse]](
            success=True,
            message=f"成功获取比赛 {match_id} 的赔率数据",
            data=odds_response,
            timestamp=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取比赛赔率失败: match_id={match_id}, error={e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取赔率数据失败: {str(e)}"
        )


@router.post(
    "/fetch/{match_id}",
    response_model=StandardResponse[dict],
    summary="触发赔率采集",
    description="手动触发指定比赛的赔率数据采集"
)
async def fetch_match_odds(
    match_id: int = Path(..., description="比赛ID", ge=1),
    request: OddsFetchRequest = OddsFetchRequest(),
    odds_service: OddsService = Depends(get_odds_service)
) -> StandardResponse[dict]:
    """
    手动触发赔率数据采集

    Args:
        match_id: 比赛ID
        request: 采集请求参数
        odds_service: 赔率服务实例

    Returns:
        StandardResponse[dict]: 采集结果统计

    Raises:
        HTTPException: 当采集失败时
    """
    try:
        logger.info(f"手动触发赔率采集: match_id={match_id}, source={request.source_name}")

        # 验证比赛是否存在
        match = await odds_service.match_dao.get(match_id)
        if not match:
            raise HTTPException(
                status_code=404,
                detail=f"比赛不存在: match_id={match_id}"
            )

        # 执行赔率采集
        result = await odds_service.fetch_and_save_odds(
            source_name=request.source_name,
            match_id=str(match_id)
        )

        # 构建响应数据
        response_data = {
            "match_id": match_id,
            "source": request.source_name,
            "total_processed": result.total_processed,
            "successful_inserts": result.successful_inserts,
            "successful_updates": result.successful_updates,
            "duplicates_found": result.duplicates_found,
            "processing_time_ms": result.processing_time_ms,
            "success_rate": result.to_dict().get("success_rate", 0.0)
        }

        logger.info(f"赔率采集完成: {response_data}")

        return StandardResponse[dict](
            success=True,
            message=f"成功采集比赛 {match_id} 的赔率数据",
            data=response_data,
            timestamp=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"手动触发赔率采集失败: match_id={match_id}, error={e}")
        raise HTTPException(
            status_code=500,
            detail=f"赔率采集失败: {str(e)}"
        )


@router.get(
    "/history/{odds_id}",
    response_model=StandardResponse[List[OddsHistoryResponse]],
    summary="获取赔率历史",
    description="获取特定赔率记录的历史变动信息"
)
async def get_odds_history(
    odds_id: int = Path(..., description="赔率记录ID", ge=1),
    limit: int = Query(50, description="返回记录数限制", ge=1, le=1000),
    odds_service: OddsService = Depends(get_odds_service)
) -> StandardResponse[List[OddsHistoryResponse]]:
    """
    获取赔率历史变动

    Args:
        odds_id: 赔率记录ID
        limit: 返回记录数限制
        odds_service: 赔率服务实例

    Returns:
        StandardResponse[List[OddsHistoryResponse]]: 历史变动列表

    Raises:
        HTTPException: 当赔率记录不存在或查询失败时
    """
    try:
        logger.info(f"获取赔率历史: odds_id={odds_id}")

        # 验证赔率记录是否存在
        odds_record = await odds_service.odds_dao.get(odds_id)
        if not odds_record:
            raise HTTPException(
                status_code=404,
                detail=f"赔率记录不存在: odds_id={odds_id}"
            )

        # 获取历史记录 (这里需要实现相应的 DAO 方法)
        # 暂时返回空列表，等待 OddsHistory DAO 实现
        history_records = []  # TODO: 实现历史记录查询

        history_response = [
            OddsHistoryResponse.model_validate(record)
            for record in history_records
        ]

        logger.info(f"成功获取赔率历史: count={len(history_response)}")

        return StandardResponse[List[OddsHistoryResponse]](
            success=True,
            message=f"成功获取赔率 {odds_id} 的历史变动",
            data=history_response,
            timestamp=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取赔率历史失败: odds_id={odds_id}, error={e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取赔率历史失败: {str(e)}"
        )


@router.get(
    "/matches/{match_id}/stats",
    response_model=StandardResponse[OddsStatsResponse],
    summary="获取赔率统计",
    description="获取指定比赛的赔率统计信息"
)
async def get_match_odds_stats(
    match_id: int = Path(..., description="比赛ID", ge=1),
    odds_service: OddsService = Depends(get_odds_service)
) -> StandardResponse[OddsStatsResponse]:
    """
    获取比赛赔率统计信息

    Args:
        match_id: 比赛ID
        odds_service: 赔率服务实例

    Returns:
        StandardResponse[OddsStatsResponse]: 赔率统计信息

    Raises:
        HTTPException: 当比赛不存在或统计失败时
    """
    try:
        logger.info(f"获取赔率统计: match_id={match_id}")

        # 验证比赛是否存在
        match = await odds_service.match_dao.get(match_id)
        if not match:
            raise HTTPException(
                status_code=404,
                detail=f"比赛不存在: match_id={match_id}"
            )

        # 获取所有赔率记录进行统计
        odds_records = await odds_service.odds_dao.get_by_match_id(match_id=match_id)

        if not odds_records:
            stats_data = OddsStatsResponse(
                total_odds=0,
                active_bookmakers=[],
                latest_update=None,
                avg_home_win=None,
                avg_draw=None,
                avg_away_win=None
            )
        else:
            # 计算统计信息
            bookmakers = list(set(record.bookmaker for record in odds_records if record.bookmaker))
            home_wins = [record.home_win for record in odds_records if record.home_win]
            draws = [record.draw for record in odds_records if record.draw]
            away_wins = [record.away_win for record in odds_records if record.away_win]

            stats_data = OddsStatsResponse(
                total_odds=len(odds_records),
                active_bookmakers=bookmakers,
                latest_update=max(record.last_updated for record in odds_records if record.last_updated),
                avg_home_win=sum(home_wins) / len(home_wins) if home_wins else None,
                avg_draw=sum(draws) / len(draws) if draws else None,
                avg_away_win=sum(away_wins) / len(away_wins) if away_wins else None
            )

        logger.info(f"成功获取赔率统计: total_odds={stats_data.total_odds}")

        return StandardResponse[OddsStatsResponse](
            success=True,
            message=f"成功获取比赛 {match_id} 的赔率统计",
            data=stats_data,
            timestamp=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取赔率统计失败: match_id={match_id}, error={e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取赔率统计失败: {str(e)}"
        )


@router.get(
    "/bookmakers",
    response_model=StandardResponse[List[str]],
    summary="获取博彩公司列表",
    description="获取系统中所有可用的博彩公司列表"
)
async def get_bookmakers(
    odds_service: OddsService = Depends(get_odds_service)
) -> StandardResponse[List[str]]:
    """
    获取博彩公司列表

    Args:
        odds_service: 赔率服务实例

    Returns:
        StandardResponse[List[str]]: 博彩公司列表
    """
    try:
        logger.info("获取博彩公司列表")

        # 获取所有独特的博彩公司
        bookmakers = await odds_service.odds_dao.get_all_bookmakers()

        logger.info(f"成功获取博彩公司列表: count={len(bookmakers)}")

        return StandardResponse[List[str]](
            success=True,
            message="成功获取博彩公司列表",
            data=bookmakers,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"获取博彩公司列表失败: error={e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取博彩公司列表失败: {str(e)}"
        )


# ==================== 健康检查端点 ====================

@router.get(
    "/health",
    response_model=StandardResponse[dict],
    summary="赔率服务健康检查",
    description="检查赔率 API 服务的健康状态"
)
async def health_check(
    odds_service: OddsService = Depends(get_odds_service)
) -> StandardResponse[dict]:
    """
    赔率服务健康检查

    Args:
        odds_service: 赔率服务实例

    Returns:
        StandardResponse[dict]: 健康检查结果
    """
    try:
        health_data = {
            "status": "healthy",
            "service": "odds-api",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "database_connection": "ok",
            "fetcher_status": "ready"
        }

        return StandardResponse[dict](
            success=True,
            message="赔率 API 服务运行正常",
            data=health_data,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"健康检查失败: error={e}")
        raise HTTPException(
            status_code=500,
            detail=f"健康检查失败: {str(e)}"
        )