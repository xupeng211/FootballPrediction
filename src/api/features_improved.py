"""
改进版特征获取API

提供更可靠、更详细的特征获取接口，包含完善的错误处理和日志记录。
"""

import logging
from typing import Any, Dict, Optional, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.features.feature_store import FootballFeatureStore
from src.database.connection_mod import get_async_session
from src.database.models import Match

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/features-improved", tags=["特征管理"])

# 全局特征存储实例（惰性初始化，避免导入时报错）
feature_store: Optional[FootballFeatureStore] = None


def get_feature_store() -> Optional[FootballFeatureStore]:
    """获取（或初始化）特征存储实例。"""
    global feature_store
    if feature_store is not None:
        return feature_store

    try:
        feature_store = FootballFeatureStore()
        logger.info("特征存储初始化成功")
    except Exception as exc:  # pragma: no cover - 初始化失败只记录日志
        logger.error("特征存储初始化失败: %s", exc)
        feature_store = None
    return feature_store


def validate_match_id(match_id: int) -> None:
    """验证比赛ID参数"""
    if match_id <= 0:
        logger.warning(f"无效的比赛ID: {match_id}")
        raise HTTPException(status_code=400, detail="比赛ID必须大于0")


def check_feature_store_availability() -> None:
    """检查特征存储服务可用性"""
    if get_feature_store() is None:
        logger.error("特征存储服务不可用")
        raise HTTPException(
            status_code=503, detail="特征存储服务暂时不可用，请稍后重试"
        )


async def get_match_info(session: AsyncSession, match_id: int) -> Match:
    """获取比赛基础信息"""
    logger.debug(f"查询比赛 {match_id} 的基础信息")

    try:
        match_query = select(Match).where(Match.id == match_id)
        match_result = await session.execute(match_query)
        match = match_result.scalar_one_or_none()

        if not match:
            logger.warning(f"比赛 {match_id} 不存在")
            raise HTTPException(status_code=404, detail=f"比赛 {match_id} 不存在")

        logger.debug(f"成功获取比赛信息: {match.home_team_id} vs {match.away_team_id}")
        return match
    except HTTPException:
        raise
    except SQLAlchemyError as db_error:
        logger.error(f"数据库查询失败 (match_id={match_id}): {db_error}")
        raise HTTPException(status_code=500, detail="数据库查询失败，请稍后重试")
    except Exception as query_error:
        logger.error(f"查询比赛信息时发生未知错误: {query_error}")
        raise HTTPException(status_code=500, detail="查询比赛信息失败")


async def get_features_data(match_id: int, match: Match) -> tuple[Dict[str, Any], str]:
    """获取特征数据（支持优雅降级）"""
    store = get_feature_store()
    if store is None:
        return {}, "feature store unavailable"

    try:
        logger.debug(f"从特征存储获取特征 (match_id={match_id})")
        features = await store.get_match_features_for_prediction(
            match_id=match_id,
            home_team_id=int(match.home_team_id),
            away_team_id=int(match.away_team_id),
        )

        if features:
            logger.info("成功获取 %s 组特征数据", len(features))
            return features, None

        logger.warning(f"比赛 {match_id} 暂无特征数据")
        return {}, None
    except Exception as feature_error:
        logger.error(f"获取特征数据失败: {feature_error}")
        return {}, str(feature_error)  # 优雅降级：返回空特征而不是完全失败


def build_response_data(
    match: Match,
    features: Dict[str, Any],
    features_error: str,
    include_raw: bool,
) -> Dict[str, Any]:
    """构造响应数据"""
    response_data = {
        "match_id": match.id,
        "home_team_id": match.home_team_id,
        "away_team_id": match.away_team_id,
        "league_id": match.league_id,
        "match_time": match.match_time.isoformat() if match.match_time else None,
        "season": match.season,
        "features": features,
        "status": "success",
        "message": "特征数据获取成功",
    }

    # 错误处理信息
    if features_error:
        response_data["status"] = "partial_success"
        response_data["warning"] = f"部分特征获取失败: {features_error}"

    # 原始数据选项
    if include_raw and features:
        response_data["raw_features"] = {
            "feature_count": len(features),
            "feature_keys": list(features.keys()) if isinstance(features, dict) else [],
        }

    return response_data


@router.get(
    "/{match_id}",
    summary="获取比赛特征",
    description="获取指定比赛的所有特征，包括球队近期表现、历史对战、赔率等",
)
async def get_match_features_improved(
    match_id: int,
    include_raw: bool = Query(default=False, description="是否包含原始特征数据"),
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """
    改进版本：获取比赛特征

    改进点：
    1. ✅ 详细的日志记录
    2. ✅ 分层错误处理
    3. ✅ 服务可用性检查
    4. ✅ 防御性参数验证
    5. ✅ 优雅降级
    """
    logger.info(f"开始获取比赛 {match_id} 的特征数据")

    # 1. 参数验证
    validate_match_id(match_id)

    # 2. 服务可用性检查
    check_feature_store_availability()

    # 3. 获取比赛信息
    match = await get_match_info(session, match_id)

    # 4. 获取特征数据
    features, features_error = await get_features_data(match_id, match)

    # 5. 构造响应数据
    response_data = build_response_data(match, features, features_error, include_raw)

    logger.info("比赛 %s 特征获取完成: %s", match_id, response_data["status"])
    return response_data


@router.get("/health", summary="特征服务健康检查")
async def health_check() -> Dict[str, Any]:
    """特征服务健康检查"""
    return {
        "service": "特征获取服务",
        "status": "healthy" if get_feature_store() else "unhealthy",
        "feature_store": "available" if get_feature_store() else "unavailable",
    }
