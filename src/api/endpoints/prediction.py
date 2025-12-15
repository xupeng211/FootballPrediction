"""
Prediction API Endpoints - 预测服务API端点

Phase 4: API Integration - 将PredictionService集成到FastAPI

实现预测相关的REST API端点，包括：
- 单场比赛预测
- 批量预测
- 服务健康检查
- 依赖注入和错误处理
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from src.schemas.prediction import (
    PredictionRequest,
    PredictionResponse,
    ErrorResponse,
    HealthResponse
)
from src.ml.inference.service import PredictionService
from typing import List, Dict, Any
import logging
import time
from datetime import datetime, timezone

router = APIRouter()
logger = logging.getLogger(__name__)

# 全局变量记录服务启动时间
service_start_time = None


async def get_prediction_service() -> PredictionService:
    """
    依赖注入：获取PredictionService实例

    Returns:
        PredictionService: 全局单例预测服务实例

    Raises:
        HTTPException: 当服务未就绪时
    """
    service = PredictionService.get_instance()

    if not service.is_ready:
        logger.warning("预测服务未就绪，尝试重新初始化")
        try:
            await service.initialize()
        except Exception as e:
            logger.error(f"预测服务初始化失败: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"预测服务不可用: {str(e)}"
            )

    return service


def format_error_response(error_type: str, message: str, details: Dict[str, Any] = None) -> ErrorResponse:
    """
    格式化错误响应

    Args:
        error_type: 错误类型
        message: 错误消息
        details: 错误详情

    Returns:
        ErrorResponse: 标准化的错误响应
    """
    return ErrorResponse(
        error=error_type,
        message=message,
        details=details,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@router.post("/predict", response_model=PredictionResponse, summary="预测单场比赛结果")
async def predict_match(
    request: PredictionRequest,
    service: PredictionService = Depends(get_prediction_service),
    background_tasks: BackgroundTasks = None
):
    """
    基于实时特征预测比赛胜负。

    如果模型未就绪，会自动触发冷启动训练。

    Args:
        request: 预测请求，包含球队ID和比赛时间
        service: 注入的预测服务实例
        background_tasks: 后台任务（用于日志记录等）

    Returns:
        PredictionResponse: 预测结果，包含概率、置信度和特征信息

    Raises:
        HTTPException: 当预测失败时返回错误响应
    """
    start_time = time.time()

    try:
        # 记录请求信息
        logger.info(f"收到预测请求: {request.home_team_id} vs {request.away_team_id} on {request.match_date}")

        # 参数验证
        if request.home_team_id == request.away_team_id:
            raise HTTPException(
                status_code=400,
                detail="主队和客队ID不能相同"
            )

        # 执行预测
        result = await service.predict_match(
            home_team_id=request.home_team_id,
            away_team_id=request.away_team_id,
            match_date=request.match_date
        )

        # 记录处理时间
        processing_time = time.time() - start_time
        logger.info(f"预测完成: {result['prediction']} (耗时: {processing_time:.3f}s)")

        # 添加后台任务（如果需要）
        if background_tasks:
            background_tasks.add_task(
                log_prediction_async,
                request.home_team_id,
                request.away_team_id,
                result,
                processing_time
            )

        return PredictionResponse(**result)

    except ValueError as e:
        # 输入验证错误
        logger.warning(f"输入验证失败: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"输入参数无效: {str(e)}"
        )

    except RuntimeError as e:
        # 服务运行时错误
        logger.error(f"预测服务运行时错误: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"预测服务错误: {str(e)}"
        )

    except Exception as e:
        # 未知错误
        logger.error(f"预测失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"预测服务内部错误: {str(e)}"
        )


@router.get("/health", response_model=HealthResponse, summary="预测服务健康检查")
async def health_check(service: PredictionService = Depends(get_prediction_service)):
    """
    检查预测服务的健康状态

    Returns:
        HealthResponse: 服务健康状态信息
    """
    global service_start_time

    try:
        # 计算运行时间
        uptime = None
        if service_start_time:
            uptime_seconds = time.time() - service_start_time
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            seconds = int(uptime_seconds % 60)
            uptime = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        return HealthResponse(
            status="healthy",
            model_ready=service.is_ready,
            model_version=service._model_version if service.is_ready else None,
            uptime=uptime
        )

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return HealthResponse(
            status="unhealthy",
            model_ready=False,
            uptime=None
        )


@router.post("/predict/batch", response_model=List[PredictionResponse], summary="批量预测比赛结果")
async def predict_batch(
    requests: List[PredictionRequest],
    service: PredictionService = Depends(get_prediction_service)
):
    """
    批量预测多场比赛结果

    Args:
        requests: 预测请求列表
        service: 注入的预测服务实例

    Returns:
        List[PredictionResponse]: 预测结果列表

    Raises:
        HTTPException: 当批量预测失败时
    """
    if len(requests) > 100:
        raise HTTPException(
            status_code=400,
            detail="批量预测请求数量不能超过100个"
        )

    results = []
    errors = []

    logger.info(f"收到批量预测请求: {len(requests)} 场比赛")

    for i, request in enumerate(requests):
        try:
            result = await service.predict_match(
                home_team_id=request.home_team_id,
                away_team_id=request.away_team_id,
                match_date=request.match_date
            )
            results.append(PredictionResponse(**result))
        except Exception as e:
            error_msg = f"比赛 {i+1} 预测失败: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

    if errors:
        logger.warning(f"批量预测完成，部分失败: {len(errors)}/{len(requests)}")

        # 如果所有预测都失败，返回错误
        if len(results) == 0:
            raise HTTPException(
                status_code=500,
                detail=f"所有预测都失败了: {'; '.join(errors[:3])}"
            )

        # 如果部分预测失败，在响应中包含警告
        # 这里可以选择返回成功的预测，或者返回错误信息

    logger.info(f"批量预测完成: {len(results)}/{len(requests)} 成功")
    return results


@router.get("/info", summary="获取预测服务信息")
async def get_service_info(service: PredictionService = Depends(get_prediction_service)):
    """
    获取预测服务的详细信息

    Returns:
        Dict: 服务信息
    """
    return {
        "service_name": "PredictionService",
        "model_version": service._model_version,
        "model_ready": service.is_ready,
        "model_path": service.model_path,
        "feature_columns_count": len(service.feature_columns),
        "feature_columns_sample": service.feature_columns[:5] if service.feature_columns else [],
        "supported_operations": [
            "single_prediction",
            "batch_prediction",
            "health_check"
        ]
    }


# 后台任务函数
async def log_prediction_async(
    home_team_id: int,
    away_team_id: int,
    result: Dict[str, Any],
    processing_time: float
):
    """
    异步记录预测日志

    Args:
        home_team_id: 主队ID
        away_team_id: 客队ID
        result: 预测结果
        processing_time: 处理时间
    """
    try:
        # 这里可以添加数据库记录、日志分析等
        logger.info(
            f"Prediction logged: {home_team_id} vs {away_team_id} -> "
            f"{result['prediction']} (confidence: {result['confidence']:.2f}, "
            f"processing_time: {processing_time:.3f}s)"
        )
    except Exception as e:
        logger.error(f"Failed to log prediction: {e}")


# 初始化服务启动时间
def set_service_start_time():
    """设置服务启动时间"""
    global service_start_time
    service_start_time = time.time()
    logger.info("Prediction API service started")


# 确保在模块导入时设置启动时间
set_service_start_time()