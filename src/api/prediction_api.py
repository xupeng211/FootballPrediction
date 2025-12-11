"""
Unified Prediction API
统一的预测API接口

提供标准化的预测服务API，支持单场预测、批量预测、模型管理等功能。
替代原有的多套预测路由，实现统一的接口规范。
"""

import logging
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks

from src.inference import (
    get_predictor,
    get_model_loader,
    get_hot_reload_manager,
    get_prediction_cache,
    Predictor,
    ModelLoader,
    HotReloadManager,
    PredictionCache,
    PredictionRequest,
    PredictionResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
    ModelListResponse,
    HealthCheckResponse,
)
from src.inference.errors import (
    InferenceError,
    PredictionError,
    ModelLoadError,
    FeatureBuilderError,
    CacheError,
    ErrorCode,
)

logger = logging.getLogger(__name__)

# 创建统一路由器
router = APIRouter(prefix="/v1/predictions", tags=["predictions"])


# 依赖注入
async def get_predictor_dependency() -> Predictor:
    """获取预测器依赖"""
    return await get_predictor()


async def get_model_loader_dependency() -> ModelLoader:
    """获取模型加载器依赖"""
    return await get_model_loader()


async def get_hot_reload_manager_dependency() -> HotReloadManager:
    """获取热更新管理器依赖"""
    return await get_hot_reload_manager()


async def get_cache_dependency() -> PredictionCache:
    """获取缓存依赖"""
    return await get_prediction_cache()


# 错误处理
def handle_inference_error(func):
    """推理服务错误处理装饰器"""

    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except PredictionError as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": e.error_code.value,
                    "message": e.message,
                    "details": e.details,
                },
            )
        except ModelLoadError as e:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": e.error_code.value,
                    "message": e.message,
                    "details": e.details,
                },
            )
        except FeatureBuilderError as e:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": e.error_code.value,
                    "message": e.message,
                    "details": e.details,
                },
            )
        except CacheError as e:
            # 缓存错误不应该阻止请求
            logger.warning(f"Cache error in {func.__name__}: {e}")
            return await func(*args, **kwargs)
        except InferenceError as e:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": e.error_code.value,
                    "message": e.message,
                    "details": e.details,
                },
            )
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": ErrorCode.INTERNAL_ERROR.value,
                    "message": "Internal server error",
                    "details": {"original_error": str(e)},
                },
            )

    return wrapper


# ============================================================================
# Prediction Endpoints
# ============================================================================


@router.post("/{model_name}/{match_id}", response_model=PredictionResponse)
@handle_inference_error
async def create_prediction(
    model_name: str,
    match_id: str,
    request: PredictionRequest,
    background_tasks: BackgroundTasks,
    predictor: Predictor = Depends(get_predictor_dependency),
):
    """
    创建单场预测

    Args:
        model_name: 模型名称
        match_id: 比赛ID
        request: 预测请求
        background_tasks: 后台任务

    Returns:
        PredictionResponse: 预测结果
    """
    # 更新请求参数
    request.model_name = model_name
    request.match_id = match_id

    # 执行预测
    result = await predictor.predict(request)

    # 添加后台任务（例如：记录预测历史）
    background_tasks.add_task(
        log_prediction, model_name, match_id, result.predicted_outcome
    )

    return result


@router.post("/batch/{model_name}", response_model=BatchPredictionResponse)
@handle_inference_error
async def create_batch_prediction(
    model_name: str,
    request: BatchPredictionRequest,
    background_tasks: BackgroundTasks,
    predictor: Predictor = Depends(get_predictor_dependency),
):
    """
    批量预测

    Args:
        model_name: 模型名称
        request: 批量预测请求
        background_tasks: 后台任务

    Returns:
        BatchPredictionResponse: 批量预测结果
    """
    # 更新所有请求的模型名称
    for req in request.requests:
        req.model_name = model_name

    # 执行批量预测
    result = await predictor.predict_batch(request)

    # 添加后台任务
    background_tasks.add_task(
        log_batch_prediction,
        model_name,
        result.batch_id,
        result.successful_predictions,
        result.failed_predictions,
    )

    return result


@router.post("/predict", response_model=PredictionResponse)
@handle_inference_error
async def predict(
    request: PredictionRequest,
    background_tasks: BackgroundTasks,
    predictor: Predictor = Depends(get_predictor_dependency),
):
    """
    通用预测接口（不指定模型名称和比赛ID）

    Args:
        request: 完整的预测请求
        background_tasks: 后台任务

    Returns:
        PredictionResponse: 预测结果
    """
    # 执行预测
    result = await predictor.predict(request)

    # 添加后台任务
    background_tasks.add_task(
        log_prediction, request.model_name, request.match_id, result.predicted_outcome
    )

    return result


@router.post("/predict/batch", response_model=BatchPredictionResponse)
@handle_inference_error
async def predict_batch(
    request: BatchPredictionRequest,
    background_tasks: BackgroundTasks,
    predictor: Predictor = Depends(get_predictor_dependency),
):
    """
    通用批量预测接口

    Args:
        request: 批量预测请求
        background_tasks: 后台任务

    Returns:
        BatchPredictionResponse: 批量预测结果
    """
    # 执行批量预测
    result = await predictor.predict_batch(request)

    # 添加后台任务
    background_tasks.add_task(
        log_batch_prediction,
        "mixed",  # 可能使用多个模型
        result.batch_id,
        result.successful_predictions,
        result.failed_predictions,
    )

    return result


# ============================================================================
# Model Management Endpoints
# ============================================================================


@router.get("/models", response_model=ModelListResponse)
@handle_inference_error
async def list_models(
    model_type: Optional[str] = Query(None, description="模型类型过滤"),
    model_loader: ModelLoader = Depends(get_model_loader_dependency),
):
    """
    获取可用模型列表

    Args:
        model_type: 模型类型过滤
        model_loader: 模型加载器

    Returns:
        ModelListResponse: 模型列表
    """
    from src.inference.schemas import ModelType

    # 转换模型类型
    model_type_enum = None
    if model_type:
        try:
            model_type_enum = ModelType(model_type)
        except ValueError:
            raise HTTPException(
                status_code=400, detail=f"Invalid model type: {model_type}"
            )

    # 获取模型列表
    models = await model_loader.list_models(model_type_enum)

    # 获取默认模型
    from src.inference.schemas import ModelType

    default_model = None
    try:
        default_model = await model_loader.get_default_model(ModelType.XGBOOST)
    except Exception:
        pass

    return ModelListResponse(
        models=models, total_models=len(models), default_model=default_model
    )


@router.get("/models/{model_name}")
@handle_inference_error
async def get_model_info(
    model_name: str, model_loader: ModelLoader = Depends(get_model_loader_dependency)
):
    """
    获取模型详细信息

    Args:
        model_name: 模型名称
        model_loader: 模型加载器

    Returns:
        dict: 模型信息
    """
    model_info = await model_loader.get_model_info(model_name)
    if not model_info:
        raise HTTPException(status_code=404, detail=f"Model '{model_name}' not found")

    return model_info.model_dump()


@router.post("/models/{model_name}/reload")
@handle_inference_error
async def reload_model(
    model_name: str,
    background_tasks: BackgroundTasks,
    model_loader: ModelLoader = Depends(get_model_loader_dependency),
    hot_reload_manager: HotReloadManager = Depends(get_hot_reload_manager_dependency),
):
    """
    重载指定模型

    Args:
        model_name: 模型名称
        background_tasks: 后台任务
        model_loader: 模型加载器
        hot_reload_manager: 热更新管理器

    Returns:
        dict: 重载结果
    """
    try:
        # 重载模型
        loaded_model = await model_loader.reload_model(model_name)

        return {
            "status": "success",
            "message": f"Model '{model_name}' reloaded successfully",
            "model_name": model_name,
            "model_version": loaded_model.metadata.model_info.model_version,
            "reloaded_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to reload model '{model_name}': {str(e)}"
        )


@router.delete("/models/{model_name}/cache")
@handle_inference_error
async def clear_model_cache(
    model_name: str, cache: PredictionCache = Depends(get_cache_dependency)
):
    """
    清除指定模型的缓存

    Args:
        model_name: 模型名称
        cache: 缓存实例

    Returns:
        dict: 清除结果
    """
    try:
        # 清除模型相关的缓存
        pattern = f"*:{model_name}:*"
        deleted_count = await cache.clear_pattern(pattern)

        return {
            "status": "success",
            "message": f"Cleared {deleted_count} cache entries for model '{model_name}'",
            "model_name": model_name,
            "deleted_count": deleted_count,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache for model '{model_name}': {str(e)}",
        )


# ============================================================================
# Cache Management Endpoints
# ============================================================================


@router.delete("/cache")
@handle_inference_error
async def clear_cache(
    pattern: Optional[str] = Query(None, description="缓存模式，默认清除所有"),
    cache: PredictionCache = Depends(get_cache_dependency),
):
    """
    清除缓存

    Args:
        pattern: 缓存模式
        cache: 缓存实例

    Returns:
        dict: 清除结果
    """
    try:
        if pattern:
            deleted_count = await cache.clear_pattern(pattern)
        else:
            deleted_count = await cache.clear_pattern("*")

        return {
            "status": "success",
            "message": f"Cleared {deleted_count} cache entries",
            "pattern": pattern or "*",
            "deleted_count": deleted_count,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


@router.get("/cache/stats")
@handle_inference_error
async def get_cache_stats(cache: PredictionCache = Depends(get_cache_dependency)):
    """
    获取缓存统计信息

    Args:
        cache: 缓存实例

    Returns:
        dict: 缓存统计
    """
    return cache.get_stats()


@router.get("/cache/health")
@handle_inference_error
async def cache_health_check(cache: PredictionCache = Depends(get_cache_dependency)):
    """
    缓存健康检查

    Args:
        cache: 缓存实例

    Returns:
        dict: 健康检查结果
    """
    return await cache.health_check()


# ============================================================================
# Hot Reload Management Endpoints
# ============================================================================


@router.post("/hot-reload/start")
@handle_inference_error
async def start_hot_reload(
    background_tasks: BackgroundTasks,
    hot_reload_manager: HotReloadManager = Depends(get_hot_reload_manager_dependency),
):
    """
    启动热更新监控

    Args:
        background_tasks: 后台任务
        hot_reload_manager: 热更新管理器

    Returns:
        dict: 启动结果
    """
    try:
        await hot_reload_manager.start_monitoring()

        return {
            "status": "success",
            "message": "Hot reload monitoring started",
            "started_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start hot reload: {str(e)}"
        )


@router.post("/hot-reload/stop")
@handle_inference_error
async def stop_hot_reload(
    hot_reload_manager: HotReloadManager = Depends(get_hot_reload_manager_dependency),
):
    """
    停止热更新监控

    Args:
        hot_reload_manager: 热更新管理器

    Returns:
        dict: 停止结果
    """
    try:
        await hot_reload_manager.stop_monitoring()

        return {
            "status": "success",
            "message": "Hot reload monitoring stopped",
            "stopped_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to stop hot reload: {str(e)}"
        )


@router.post("/hot-reload/force/{model_name}")
@handle_inference_error
async def force_reload_model(
    model_name: str,
    background_tasks: BackgroundTasks,
    hot_reload_manager: HotReloadManager = Depends(get_hot_reload_manager_dependency),
):
    """
    强制重载指定模型

    Args:
        model_name: 模型名称
        background_tasks: 后台任务
        hot_reload_manager: 热更新管理器

    Returns:
        dict: 重载结果
    """
    try:
        await hot_reload_manager.force_reload(model_name)

        return {
            "status": "success",
            "message": f"Force reload initiated for model '{model_name}'",
            "model_name": model_name,
            "initiated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to force reload model '{model_name}': {str(e)}",
        )


@router.get("/hot-reload/stats")
@handle_inference_error
async def get_hot_reload_stats(
    hot_reload_manager: HotReloadManager = Depends(get_hot_reload_manager_dependency),
):
    """
    获取热更新统计信息

    Args:
        hot_reload_manager: 热更新管理器

    Returns:
        dict: 热更新统计
    """
    return hot_reload_manager.get_reload_stats()


# ============================================================================
# Health Check Endpoints
# ============================================================================


@router.get("/health")
@handle_inference_error
async def health_check(
    predictor: Predictor = Depends(get_predictor_dependency),
    model_loader: ModelLoader = Depends(get_model_loader_dependency),
    cache: PredictionCache = Depends(get_cache_dependency),
    hot_reload_manager: HotReloadManager = Depends(get_hot_reload_manager_dependency),
):
    """
    推理服务健康检查

    Returns:
        HealthCheckResponse: 健康检查结果
    """
    try:
        # 获取各组件状态
        predictor_stats = predictor.get_prediction_stats()
        model_loader.get_load_stats()
        cache_stats = cache.get_stats()
        hot_reload_stats = hot_reload_manager.get_reload_stats()

        # 获取缓存健康状态
        cache_health = await cache.health_check()
        model_info_list = await model_loader.list_models()

        return HealthCheckResponse(
            status="healthy" if cache_health["status"] == "healthy" else "degraded",
            model_loaded=len(model_info_list) > 0,
            cache_status=cache_health["status"],
            hot_reload_enabled=hot_reload_stats["is_monitoring"],
            loaded_models=[info.model_dump() for info in model_info_list],
            uptime_seconds=predictor_stats.get("uptime_seconds", 0),
            memory_usage_mb=cache_stats.get("used_memory", 0) / 1024 / 1024,  # 转换为MB
            last_prediction_time=datetime.utcnow(),  # 这里应该是实际的最后预测时间
        )

    except Exception:
        return HealthCheckResponse(
            status="unhealthy",
            model_loaded=False,
            cache_status="unknown",
            hot_reload_enabled=False,
            loaded_models=[],
            uptime_seconds=0,
            memory_usage_mb=0,
            last_prediction_time=None,
        )


@router.get("/stats")
@handle_inference_error
async def get_prediction_stats(
    predictor: Predictor = Depends(get_predictor_dependency),
):
    """
    获取预测服务统计信息

    Args:
        predictor: 预测器

    Returns:
        dict: 统计信息
    """
    return predictor.get_prediction_stats()


# ============================================================================
# Background Tasks
# ============================================================================


async def log_prediction(model_name: str, match_id: str, predicted_outcome: str):
    """记录预测历史"""
    try:
        # 这里可以记录到数据库或其他存储
        logger.info(
            f"Prediction logged: {model_name} - {match_id} -> {predicted_outcome}"
        )
    except Exception as e:
        logger.error(f"Failed to log prediction: {e}")


async def log_batch_prediction(
    model_name: str, batch_id: str, successful_count: int, failed_count: int
):
    """记录批量预测历史"""
    try:
        # 这里可以记录到数据库或其他存储
        logger.info(
            f"Batch prediction logged: {model_name} - {batch_id} -> "
            f"successful: {successful_count}, failed: {failed_count}"
        )
    except Exception as e:
        logger.error(f"Failed to log batch prediction: {e}")


# ============================================================================
# Application Lifecycle
# ============================================================================


@asynccontextmanager
async def lifespan(app):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("Initializing Prediction API...")

    try:
        # 初始化各个组件
        predictor = await get_predictor()
        await get_model_loader()
        cache = await get_prediction_cache()
        hot_reload_manager = await get_hot_reload_manager()

        # 启动热更新监控（如果启用）
        import os

        if os.getenv("HOT_RELOAD_ENABLED", "false").lower() == "true":
            await hot_reload_manager.start_monitoring()
            logger.info("Hot reload monitoring started")

        logger.info("Prediction API initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize Prediction API: {e}")
        raise

    yield

    # 关闭时清理
    logger.info("Shutting down Prediction API...")

    try:
        predictor = await get_predictor()
        await get_model_loader()
        cache = await get_prediction_cache()
        hot_reload_manager = await get_hot_reload_manager()

        await hot_reload_manager.cleanup()
        await cache.cleanup()
        await predictor.cleanup()

        logger.info("Prediction API shutdown completed")

    except Exception as e:
        logger.error(f"Error during Prediction API shutdown: {e}")


# 注册路由和生命周期
app = router
app.lifespan = lifespan
