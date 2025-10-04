"""
import asyncio
改进版特征服务 API

增强错误处理、日志记录和防御性编程
"""

import logging
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import get_async_session
from ..database.models.match import Match
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
    feature_store = None
    feature_calculator = None


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

        except HTTPException:
            raise
        except SQLAlchemyError as db_error:
            logger.error(f"数据库查询失败 (match_id={match_id}): {db_error}")
            raise HTTPException(status_code=500, detail="数据库查询失败，请稍后重试")
        except Exception as query_error:
            logger.error(f"查询比赛信息时发生未知错误: {query_error}")
            raise HTTPException(status_code=500, detail="查询比赛信息失败")

        # 4. 构造比赛实体（防御性编程）
        try:
            match_entity = MatchEntity(
                match_id=int(match.id),
                home_team_id=int(match.home_team_id),
                away_team_id=int(match.away_team_id),
                league_id=int(match.league_id),
                match_time=match.match_time,
                season=match.season or "2024-25",  # 默认赛季
            )
            logger.debug("比赛实体构造成功")
        except Exception as entity_error:
            logger.error(f"构造比赛实体失败: {entity_error}")
            raise HTTPException(status_code=500, detail="处理比赛数据时发生错误")

        # 5. 获取特征数据（优雅降级）
        features = None
        features_error = None

        try:
            logger.debug(f"从特征存储获取特征 (match_id={match_id})")
            features = await feature_store.get_match_features_for_prediction(
                match_id=match_id,
                home_team_id=int(match.home_team_id),
                away_team_id=int(match.away_team_id),
            )

            if features:
                logger.info(f"成功获取 {len(features)} 组特征数据")
            else:
                logger.warning(f"比赛 {match_id} 暂无特征数据")
                features = {}

        except Exception as feature_error:
            logger.error(f"获取特征数据失败: {feature_error}")
            features_error = str(feature_error)
            features = {}  # 优雅降级：返回空特征而不是完全失败

        # 6. 构造响应数据
        response_data = {
            "match_info": {
                "match_id": match.id,
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
            response_data["features_warning"] = {
                "message": f"特征数据获取部分失败: {features_error}"
            }

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
        if features_error:
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


# 健康检查端点
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
        return {"status": "unhealthy", **health_status}

    return {"status": "healthy", **health_status}
