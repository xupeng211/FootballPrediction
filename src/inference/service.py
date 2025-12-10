"""
FastAPI推理服务
提供足球比赛预测的REST API端点

功能:
1. 单场比赛预测
2. 模型信息查询
3. 健康检查
4. 错误处理

作者: Backend Engineer
创建时间: 2025-12-10
版本: 1.0.0 - Phase 3 Inference
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from .model_loader import model_loader
from .schemas import (
    PredictionRequest,
    PredictionResponse,
    ModelInfoResponse,
    ErrorResponse
)

logger = logging.getLogger(__name__)

# 创建推理API路由
router = APIRouter(
    prefix="/api/v1/inference",
    tags=["inference"],
    responses={
        404: {"model": ErrorResponse, "description": "Not Found"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    }
)


@router.post("/predict", response_model=PredictionResponse, status_code=status.HTTP_200_OK)
async def predict_match(request: PredictionRequest) -> PredictionResponse:
    """
    对单场比赛进行预测

    Args:
        request: 预测请求数据

    Returns:
        预测结果

    Raises:
        HTTPException: 当预测失败时
    """
    start_time = time.time()

    try:
        # 记录请求
        logger.info(f"🎯 收到预测请求: 比赛ID {request.match_id}, "
                   f"{request.home_team_name} vs {request.away_team_name}")

        # 检查模型是否已加载
        if not model_loader.is_loaded():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Model not loaded. Please check server logs."
            )

        # 转换为模型需要的格式
        match_data = {
            "id": request.match_id,
            "home_team_name": request.home_team_name,
            "away_team_name": request.away_team_name,
            "match_date": request.match_date.isoformat(),
            "home_score": request.home_score or 0,
            "away_score": request.away_score or 0,
            "home_xg": request.home_xg,
            "away_xg": request.away_xg,
            "home_total_shots": request.home_total_shots,
            "away_total_shots": request.away_total_shots,
            "home_shots_on_target": request.home_shots_on_target,
            "away_shots_on_target": request.away_shots_on_target,
            "league_id": request.league_id,
            "league_name": request.league_name,
            "stats_json": request.stats_json or {}
        }

        # 执行预测
        prediction_result = model_loader.predict(match_data)

        # 计算处理时间
        processing_time_ms = (time.time() - start_time) * 1000

        # 构建响应
        response = PredictionResponse(
            match_id=request.match_id,
            prediction=prediction_result["prediction"],
            probabilities=prediction_result["probabilities"],
            confidence=prediction_result["confidence"],
            model_version=model_loader.model_metadata.get("version", "v1.0.0") if model_loader.model_metadata else "v1.0.0",
            timestamp=datetime.now(),
            feature_count=prediction_result["feature_count"],
            missing_features=prediction_result["missing_features"],
            processing_time_ms=round(processing_time_ms, 2)
        )

        logger.info(f"✅ 预测完成: {response.prediction} "
                   f"(置信度: {response.confidence:.3f}, "
                   f"处理时间: {processing_time_ms:.1f}ms)")

        return response

    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"❌ 预测失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )


@router.get("/model/info", response_model=ModelInfoResponse)
async def get_model_info() -> ModelInfoResponse:
    """
    获取模型信息

    Returns:
        模型详细信息
    """
    try:
        model_info = model_loader.get_model_info()

        if model_info["status"] == "not_loaded":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Model not loaded"
            )

        response = ModelInfoResponse(
            status=model_info["status"],
            model_type=model_info["model_type"],
            model_version=model_info["model_metadata"].get("version", "v1.0.0") if model_info.get("model_metadata") else "v1.0.0",
            feature_count=model_info["feature_count"],
            target_classes=model_info["target_classes"],
            performance_metrics=model_info["model_metadata"].get("performance", {}) if model_info.get("model_metadata") else None,
            loaded_at=datetime.now()  # 这里应该从模型加载器获取实际加载时间
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取模型信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get model info: {str(e)}"
        )


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    健康检查端点

    Returns:
        服务状态信息
    """
    try:
        model_status = "loaded" if model_loader.is_loaded() else "not_loaded"

        return {
            "status": "healthy",
            "service": "football-prediction-inference",
            "model_status": model_status,
            "timestamp": datetime.now().isoformat(),
            "version": "v1.0.0"
        }
    except Exception as e:
        logger.error(f"❌ 健康检查失败: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@router.post("/predict/batch")
async def predict_batch(matches: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    批量预测端点 (简化版本)

    Args:
        matches: 比赛数据列表

    Returns:
        批量预测结果
    """
    if not model_loader.is_loaded():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded"
        )

    if len(matches) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 matches allowed per batch request"
        )

    start_time = time.time()
    predictions = []

    try:
        for i, match_data in enumerate(matches):
            logger.info(f"处理第 {i+1}/{len(matches)} 场比赛")

            # 确保必要的字段存在
            if "match_id" not in match_data or "home_team_name" not in match_data or "away_team_name" not in match_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Match {i+1} missing required fields"
                )

            # 执行预测
            prediction_result = model_loader.predict(match_data)

            predictions.append({
                "match_id": match_data["match_id"],
                "prediction": prediction_result["prediction"],
                "probabilities": prediction_result["probabilities"],
                "confidence": prediction_result["confidence"]
            })

        # 计算处理时间
        processing_time_ms = (time.time() - start_time) * 1000

        # 统计预测分布
        prediction_counts = {}
        for pred in predictions:
            result = pred["prediction"]
            prediction_counts[result] = prediction_counts.get(result, 0) + 1

        result = {
            "predictions": predictions,
            "total_matches": len(matches),
            "processing_time_ms": round(processing_time_ms, 2),
            "prediction_distribution": prediction_counts
        }

        logger.info(f"✅ 批量预测完成: {len(matches)} 场比赛, "
                   f"处理时间: {processing_time_ms:.1f}ms")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 批量预测失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch prediction failed: {str(e)}"
        )


def create_inference_router() -> APIRouter:
    """
    创建推理API路由器

    Returns:
        配置好的APIRouter实例
    """
    return router


# 启动时加载模型
async def startup_load_model():
    """应用启动时加载模型"""
    try:
        logger.info("🚀 启动推理服务，开始加载模型...")
        success = model_loader.load_model_artifacts()

        if success:
            logger.info("✅ 模型加载成功，推理服务就绪")
        else:
            logger.error("❌ 模型加载失败，推理服务将无法正常工作")

    except Exception as e:
        logger.error(f"❌ 启动时加载模型失败: {e}")


# 优雅关闭时的清理
async def shutdown_cleanup():
    """应用关闭时的清理工作"""
    logger.info("🔄 推理服务正在关闭...")
    # 这里可以添加清理逻辑
    logger.info("✅ 推理服务已安全关闭")