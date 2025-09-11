"""
特征服务 API

提供特征查询相关的 FastAPI 端点：
- /features/{match_id} → 返回比赛特征
- /teams/{team_id}/features → 返回球队特征
- 支持在线和离线特征查询
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_async_session
from ..database.models.match import Match
from ..database.models.team import Team
from ..features.entities import MatchEntity, TeamEntity
from ..features.feature_calculator import FeatureCalculator
from ..features.feature_store import FootballFeatureStore
from ..utils.response import APIResponse

router = APIRouter(prefix="/features", tags=["features"])

# 初始化特征存储和计算器
feature_store = FootballFeatureStore()
feature_calculator = FeatureCalculator()


@router.get(
    "/{match_id}",
    summary="获取比赛特征",
    description="获取指定比赛的所有特征，包括球队近期表现、历史对战、赔率等",
)
async def get_match_features(
    match_id: int,
    include_raw: bool = Query(False, description="是否包含原始特征数据"),
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """
    获取比赛特征

    Args:
        match_id: 比赛ID
        include_raw: 是否包含原始特征计算数据
        session: 数据库会话

    Returns:
        APIResponse: 包含比赛特征的响应
    """
    try:
        # 查询比赛信息
        match_query = select(Match).where(Match.id == match_id)
        match_result = await session.execute(match_query)
        match = match_result.scalar_one_or_none()

        if not match:
            raise HTTPException(status_code=404, detail=f"比赛 {match_id} 不存在")

        # 创建比赛实体
        match_entity = MatchEntity(
            match_id=match.id,
            home_team_id=match.home_team_id,
            away_team_id=match.away_team_id,
            league_id=match.league_id,
            match_time=match.match_time,
            season=match.season or "2024-25",
        )

        # 从特征存储获取特征
        features = await feature_store.get_match_features_for_prediction(
            match_id=match_id,
            home_team_id=match.home_team_id,
            away_team_id=match.away_team_id,
        )

        response_data = {
            "match_info": {
                "match_id": match.id,
                "home_team_id": match.home_team_id,
                "away_team_id": match.away_team_id,
                "league_id": match.league_id,
                "match_time": match.match_time.isoformat(),
                "season": match.season,
                "match_status": match.match_status,
            },
            "features": features or {},
        }

        # 如果需要原始特征数据，直接计算
        if include_raw:
            try:
                all_features = await feature_calculator.calculate_all_match_features(
                    match_entity
                )
                response_data["raw_features"] = all_features.to_dict()
            except Exception as e:
                response_data["raw_features_error"] = str(e)

        return APIResponse.success(data=response_data, message=f"成功获取比赛 {match_id} 的特征")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取比赛特征失败: {str(e)}")


@router.get(
    "/teams/{team_id}",
    summary="获取球队特征",
    description="获取指定球队的特征，包括近期表现、统计数据等",
)
async def get_team_features(
    team_id: int,
    calculation_date: Optional[datetime] = Query(None, description="特征计算日期，默认为当前时间"),
    include_raw: bool = Query(False, description="是否包含原始特征数据"),
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """
    获取球队特征

    Args:
        team_id: 球队ID
        calculation_date: 特征计算日期
        include_raw: 是否包含原始特征计算数据
        session: 数据库会话

    Returns:
        APIResponse: 包含球队特征的响应
    """
    try:
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
                "league_id": team.league_id,
                "founded_year": team.founded_year,
                "venue": team.venue,
            },
            "calculation_date": calculation_date.isoformat(),
            "features": (
                team_features.to_dict("records")[0] if not team_features.empty else {}
            ),
        }

        # 如果需要原始特征数据，直接计算
        if include_raw:
            try:
                team_entity = TeamEntity(
                    team_id=team.id,
                    team_name=team.name,
                    league_id=team.league_id,
                    home_venue=team.venue,
                )

                all_features = await feature_calculator.calculate_all_team_features(
                    team_entity, calculation_date
                )
                response_data["raw_features"] = all_features.to_dict()
            except Exception as e:
                response_data["raw_features_error"] = str(e)

        return APIResponse.success(
            data=response_data, message=f"成功获取球队 {team.name} 的特征"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取球队特征失败: {str(e)}")


@router.post(
    "/calculate/{match_id}",
    summary="计算比赛特征",
    description="实时计算指定比赛的所有特征并存储到特征存储",
)
async def calculate_match_features(
    match_id: int,
    force_recalculate: bool = Query(False, description="是否强制重新计算"),
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
    try:
        # 查询比赛信息
        match_query = select(Match).where(Match.id == match_id)
        match_result = await session.execute(match_query)
        match = match_result.scalar_one_or_none()

        if not match:
            raise HTTPException(status_code=404, detail=f"比赛 {match_id} 不存在")

        # 创建比赛实体
        match_entity = MatchEntity(
            match_id=match.id,
            home_team_id=match.home_team_id,
            away_team_id=match.away_team_id,
            league_id=match.league_id,
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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计算比赛特征失败: {str(e)}")


@router.post(
    "/calculate/teams/{team_id}",
    summary="计算球队特征",
    description="实时计算指定球队的特征并存储到特征存储",
)
async def calculate_team_features(
    team_id: int,
    calculation_date: Optional[datetime] = Query(None, description="特征计算日期"),
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
    try:
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
                "team_name": team.name,
                "features_stored": success,
                "calculation_date": calculation_date.isoformat(),
            },
            message=f"球队 {team.name} 特征计算完成",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"计算球队特征失败: {str(e)}")


@router.post(
    "/batch/calculate",
    summary="批量计算特征",
    description="批量计算指定时间范围内的特征",
)
async def batch_calculate_features(
    start_date: datetime = Query(..., description="开始日期"),
    end_date: datetime = Query(..., description="结束日期"),
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """
    批量计算特征

    Args:
        start_date: 开始日期
        end_date: 结束日期
        session: 数据库会话

    Returns:
        APIResponse: 批量计算结果
    """
    try:
        if start_date >= end_date:
            raise HTTPException(status_code=400, detail="开始日期必须早于结束日期")

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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量计算特征失败: {str(e)}")


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
    try:
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
                "match_id": match_id,
                "feature_refs": feature_refs,
                "features": historical_features.to_dict("records"),
                "feature_count": len(historical_features.columns),
                "record_count": len(historical_features),
            },
            message="成功获取历史特征数据",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史特征失败: {str(e)}")
