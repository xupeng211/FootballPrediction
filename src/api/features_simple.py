"""
简化版特征获取API

提供基本的特征获取接口,避免复杂的Feast依赖问题.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.dependencies import get_async_db
from src.database.models import Match

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/features", tags=["特征管理"])


@router.get("/match/{match_id}", response_model=dict[str, Any])
async def get_match_features(
    match_id: int, db: AsyncSession = Depends(get_async_db)
) -> dict[str, Any]:
    """
    获取指定比赛的简单特征

    Args:
        match_id: 比赛ID

    Returns:
        Dict包含比赛基本特征数据
    """
    try:
        # 这里使用基本的SQL查询,避免复杂特征存储
        result = await db.execute(
            select(
                Match.id,
                Match.home_team_id,
                Match.away_team_id,
                Match.home_score,
                Match.away_score,
            ).where(Match.id == match_id)
        )
        match_data = result.fetchone()

        if not match_data:
            raise HTTPException(status_code=404, detail="比赛未找到") from e
        return {
            "match_id": match_data[0],
            "home_team_id": match_data[1],
            "away_team_id": match_data[2],
            "home_score": match_data[3],
            "away_score": match_data[4],
            "status": "success",
        }

    except SQLAlchemyError as e:
        logger.error(f"数据库查询错误: {e}")
        raise HTTPException(status_code=500, detail="数据库查询失败") from e
    except HTTPException:
        # HTTPException会被FastAPI全局异常处理器捕获
        raise
    except Exception as e:
        logger.error(f"未知错误: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误") from e
@router.get("/health", response_model=dict[str, str])
async def health_check() -> dict[str, str]:
    """
    简单的健康检查端点
    """
    try:
        return {
            "status": "healthy",
            "service": "features",
            "message": "简化版特征服务运行正常",
        }
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail="健康检查失败") from e
@router.get("/", response_model=dict[str, Any])
async def get_features_info() -> dict[str, Any]:
    """
    获取特征服务信息
    """
    try:
        return {
            "service": "features",
            "version": "1.0.0",
            "description": "足球预测特征管理API（简化版）",
            "endpoints": [
                {
                    "path": "/match/{match_id}",
                    "method": "GET",
                    "description": "获取指定比赛的特征数据",
                },
                {"path": "/health", "method": "GET", "description": "健康检查端点"},
                {"path": "/", "method": "GET", "description": "服务信息"},
            ],
        }
    except Exception as e:
        logger.error(f"获取服务信息失败: {e}")
        raise HTTPException(status_code=500, detail="获取服务信息失败") from e