"""
特征服务 API

提供特征查询相关的 FastAPI 端点：
- /features/{match_id} -> 返回比赛特征
- /teams/{team_id}/features -> 返回球队特征
- 支持在线和离线特征查询
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_async_session
from ..database.models.match import Match
from ..database.models.team import Team
from ..features.entities import MatchEntity
from ..features.feature_calculator import FeatureCalculator
from ..features.feature_store import FootballFeatureStore
from ..utils.response import APIResponse

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/features", tags=["features"])

# 初始化特征存储和计算器（加入错误处理）
try:
    feature_store = FootballFeatureStore()
    feature_calculator = FeatureCalculator()
    logger.info("特征存储和计算器初始化成功")
except Exception as e:
    logger.error(f"特征存储初始化失败: {e}")
    feature_store: Optional[FootballFeatureStore] = None
    feature_calculator: Optional[FeatureCalculator] = None


# 健康检查端点（必须在 /{match_id} 之前定义）
@router.get("/health", summary="特征服务健康检查")
async def features_health_check():
    """
    特征服务健康检查

    检查各个组件的可用性
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "feature_store": feature_store is not None,
            "feature_calculator": feature_calculator is not None,
        },
    }

    # 检查特征存储连接
    if feature_store:
        try:
            # 这里可以添加特征存储的连接测试
            health_status["components"]["feature_store_connection"] = True
        except Exception as e:
            logger.warning(f"特征存储连接检查失败: {e}")
            health_status["components"]["feature_store_connection"] = False
            health_status["status"] = "degraded"

    if not all(health_status["components"].values()):
        health_status["status"] = "unhealthy"
        return health_status

    return health_status


@router.get(
    "/{match_id}",
    summary="获取比赛特征",
    description="获取指定比赛的所有特征，包括球队近期表现、历史对战、赔率等",
)
async def get_match_features(
    match_id: int,
    include_raw: bool = Query(default=False, description="是否包含原始特征数据"),
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """
    获取比赛特征 (改进版)

    Args:
        match_id: 比赛ID
        include_raw: 是否包含原始特征计算数据
        session: 数据库会话

    Returns:
        APIResponse: 包含比赛特征的响应
    """
    logger.info(f"开始获取比赛 {match_id} 的特征数据")

    # 1. 参数验证
    if match_id <= 0:
        logger.warning(f"无效的比赛ID: {match_id}")
        raise HTTPException(status_code=400, detail="比赛ID必须大于0")

    # 2. 服务可用性检查
    if feature_store is None:
        logger.error("特征存储服务不可用")
        raise HTTPException(
            status_code=503, detail="特征存储服务暂时不可用，请稍后重试"
        )

    try:
        # 3. 数据库查询（增强错误处理）
        logger.debug(f"查询比赛 {match_id} 的基础信息")

        try:
            match_query = select(Match).where(Match.id == match_id)
            match_result = await session.execute(match_query)
            match = match_result.scalar_one_or_none()

            if not match:
                logger.warning(f"比赛 {match_id} 不存在")
                raise HTTPException(status_code=404, detail=f"比赛 {match_id} 不存在")

            logger.debug(
                f"成功获取比赛信息: {match.home_team_id} vs {match.away_team_id}"
            )

        except SQLAlchemyError as db_error:
            logger.error(f"数据库查询失败 (match_id={match_id}): {db_error}")
            raise HTTPException(status_code=500, detail="数据库查询失败，请稍后重试")

        # 4. 构造比赛实体（防御性编程）
        try:
            match_entity = MatchEntity(
                match_id=int(int(match.id)),
                home_team_id=int(match.home_team_id),
                away_team_id=int(match.away_team_id),
                league_id=int(match.league_id),
                match_time=match.match_time,
                season=match.season or "2024-25",
            )
            logger.debug("比赛实体构造成功")
        except Exception as entity_error:
            logger.error(f"构造比赛实体失败: {entity_error}")
            raise HTTPException(status_code=500, detail="处理比赛数据时发生错误")

        # 5. 获取特征数据（优雅降级）
        features_error = None
        try:
            logger.debug(f"从特征存储获取特征 (match_id={match_id})")
            features = await feature_store.get_match_features_for_prediction(
                match_id=match_id,
                home_team_id=match.home_team_id,
                away_team_id=match.away_team_id,
            )

            if features:
                logger.info(f"成功获取 {len(features)} 组特征数据")
            else:
                logger.warning(f"比赛 {match_id} 暂无特征数据")
                features = {}

        except Exception as feature_error:
            logger.error(f"获取特征数据失败: {feature_error}")
            features_error = str(feature_error)
            features = {}

        # 6. 构造响应数据
        response_data = {
            "match_info": {
                "match_id": int(match.id),
                "home_team_id": match.home_team_id,
                "away_team_id": match.away_team_id,
                "league_id": match.league_id,
                "match_time": (
                    match.match_time.isoformat() if match.match_time else None
                ),
                "season": match.season,
                "match_status": match.match_status,
            },
            "features": features or {},
        }

        # 添加特征获取状态
        if features_error:
            response_data[
                "features_warning"
            ] = f"特征数据获取部分失败: {features_error}"

        # 7. 处理原始特征请求（可选）
        if include_raw and feature_calculator:
            try:
                logger.debug("计算原始特征数据")
                all_features = await feature_calculator.calculate_all_match_features(
                    match_entity
                )
                response_data["raw_features"] = all_features.to_dict()
                logger.debug("原始特征计算完成")
            except Exception as raw_error:
                logger.error(f"计算原始特征失败: {raw_error}")
                response_data["raw_features_error"] = {"error": str(raw_error)}

        # 8. 成功响应
        message = f"成功获取比赛 {match_id} 的特征"
        if not features:
            message += "（特征数据部分缺失）"

        logger.info(f"比赛 {match_id} 特征获取完成")
        return APIResponse.success(data=response_data, message=message)
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as unexpected_error:
        # 捕获所有未预期的错误
        logger.exception(
            f"获取比赛特征时发生未预期错误 (match_id={match_id}): {unexpected_error}"
        )
        raise HTTPException(
            status_code=500, detail=f"获取比赛特征失败: {str(unexpected_error)}"
        )


@router.get(
    "/teams/{team_id}",
    summary="获取球队特征",
    description="获取指定球队的特征，包括近期表现、统计数据等",
)
async def get_team_features(
    team_id: int,
    calculation_date: Optional[datetime] = Query(
        None, description="特征计算日期，默认为当前时间"
    ),
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """
    获取球队特征

    Args:
        team_id: 球队ID
        calculation_date: 特征计算日期
        session: 数据库会话

    Returns:
        APIResponse: 包含球队特征的响应
    """
    # 查询球队信息
    team_query = select(Team).where(Team.id == team_id)
    team_result = await session.execute(team_query)
    team = team_result.scalar_one_or_none()

    if not team:
        raise HTTPException(status_code=404, detail=f"球队 {team_id} 不存在")

    if calculation_date is None:
        calculation_date = datetime.now()

    # 从特征存储获取球队特征
    team_features = await feature_store.get_online_features(
        feature_refs=[
            "team_recent_performance:recent_5_wins",
            "team_recent_performance:recent_5_draws",
            "team_recent_performance:recent_5_losses",
            "team_recent_performance:recent_5_goals_for",
            "team_recent_performance:recent_5_goals_against",
            "team_recent_performance:recent_5_points",
            "team_recent_performance:recent_5_home_wins",
            "team_recent_performance:recent_5_away_wins",
        ],
        entity_rows=[{"team_id": team_id}],
    )

    response_data = {
        "team_info": {
            "team_id": team.id,
            "team_name": team.name,
            "league_id": int(team.league_id),
            "founded_year": team.founded_year,
            "venue": getattr(team, "venue", None),
        },
        "calculation_date": calculation_date.isoformat(),
        "features": (
            team_features.to_dict("records")[0] if not team_features.empty else {}
        ),
    }

    return APIResponse.success(
        data=response_data, message=f"成功获取球队 {team.name} 的特征"
    )


@router.post(
    "/calculate/{match_id}",
    summary="计算比赛特征",
    description="实时计算指定比赛的所有特征并存储到特征存储",
)
async def calculate_match_features(
    match_id: int,
    force_recalculate: bool = Query(default=False, description="是否强制重新计算"),
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """
    计算比赛特征

    Args:
        match_id: 比赛ID
        force_recalculate: 是否强制重新计算
        session: 数据库会话

    Returns:
        APIResponse: 计算结果
    """
    # 查询比赛信息
    match_query = select(Match).where(Match.id == match_id)
    match_result = await session.execute(match_query)
    match = match_result.scalar_one_or_none()

    if not match:
        raise HTTPException(status_code=404, detail=f"比赛 {match_id} 不存在")

    # 创建比赛实体
    match_entity = MatchEntity(
        match_id=int(match.id),
        home_team_id=int(match.home_team_id),
        away_team_id=int(match.away_team_id),
        league_id=int(match.league_id),
        match_time=match.match_time,
        season=match.season or "2024-25",
    )

    # 计算并存储特征
    success = await feature_store.calculate_and_store_match_features(match_entity)

    # 计算并存储球队特征
    home_team_success = await feature_store.calculate_and_store_team_features(
        match.home_team_id, match.match_time
    )
    away_team_success = await feature_store.calculate_and_store_team_features(
        match.away_team_id, match.match_time
    )

    return APIResponse.success(
        data={
            "match_id": match_id,
            "match_features_stored": success,
            "home_team_features_stored": home_team_success,
            "away_team_features_stored": away_team_success,
            "calculation_time": datetime.now().isoformat(),
        },
        message="特征计算完成",
    )


@router.get(
    "/calculate/teams/{team_id}",
    summary="计算球队特征",
    description="实时计算指定球队的特征并存储到特征存储",
)
async def calculate_team_features(
    team_id: int,
    calculation_date: Optional[datetime] = Query(
        default=None, description="特征计算日期"
    ),
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """
    计算球队特征

    Args:
        team_id: 球队ID
        calculation_date: 特征计算日期
        session: 数据库会话

    Returns:
        APIResponse: 计算结果
    """
    # 查询球队信息
    team_query = select(Team).where(Team.id == team_id)
    team_result = await session.execute(team_query)
    team = team_result.scalar_one_or_none()

    if not team:
        raise HTTPException(status_code=404, detail=f"球队 {team_id} 不存在")

    if calculation_date is None:
        calculation_date = datetime.now()

    # 计算并存储特征
    success = await feature_store.calculate_and_store_team_features(
        team_id, calculation_date
    )

    return APIResponse.success(
        data={
            "team_id": team_id,
            "features_stored": success,
            "calculation_date": calculation_date.isoformat(),
        },
        message=f"球队 {team.name} 特征计算完成",
    )


@router.post(
    "/batch/calculate",
    summary="批量计算特征",
    description="批量计算指定时间范围内的特征",
)
async def batch_calculate_features(
    start_date: datetime = Query(..., description="开始日期"),
    end_date: datetime = Query(..., description="结束日期"),
) -> Dict[str, Any]:
    """
    批量计算特征

    Args:
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        APIResponse: 批量计算结果
    """
    if start_date >= end_date:
        raise HTTPException(status_code=400, detail="开始日期必须早于结束日期")

    if (end_date - start_date).days > 30:
        raise HTTPException(status_code=400, detail="时间范围不能超过30天")

    # 执行批量计算
    stats = await feature_store.batch_calculate_features(start_date, end_date)

    return APIResponse.success(
        data={
            "date_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "statistics": stats,
            "completion_time": datetime.now().isoformat(),
        },
        message="批量特征计算完成",
    )


@router.get(
    "/historical/{match_id}",
    summary="获取历史特征",
    description="获取比赛的历史特征数据，用于模型训练",
)
async def get_historical_features(
    match_id: int,
    feature_refs: List[str] = Query(..., description="特征引用列表"),
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """
    获取历史特征

    Args:
        match_id: 比赛ID
        feature_refs: 特征引用列表
        session: 数据库会话

    Returns:
        APIResponse: 历史特征数据
    """
    # 查询比赛信息
    match_query = select(Match).where(Match.id == match_id)
    match_result = await session.execute(match_query)
    match = match_result.scalar_one_or_none()

    if not match:
        raise HTTPException(status_code=404, detail=f"比赛 {match_id} 不存在")

    # 创建实体DataFrame
    entity_df = pd.DataFrame(
        [
            {
                "match_id": match_id,
                "team_id": match.home_team_id,
                "event_timestamp": match.match_time,
            },
            {
                "match_id": match_id,
                "team_id": match.away_team_id,
                "event_timestamp": match.match_time,
            },
        ]
    )

    # 获取历史特征
    historical_features = await feature_store.get_historical_features(
        entity_df=entity_df, feature_refs=feature_refs, full_feature_names=True
    )

    return APIResponse.success(
        data={
            "feature_refs": feature_refs,
            "features": historical_features.to_dict("records"),
            "feature_count": len(historical_features.columns),
            "record_count": len(historical_features),
        },
        message="成功获取历史特征数据",
    )
