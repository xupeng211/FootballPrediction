"""
缓存管理API
Cache Management API

提供缓存状态查询、管理和维护的API端点
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from src.cache.init_cache import get_cache_initializer
from src.cache.optimization import get_cache_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cache", tags=["缓存管理"])


class CacheStatsResponse(BaseModel):
    """缓存统计响应"""
    l1_cache: Dict[str, Any] = Field(description="L1缓存统计")
    l2_cache: Dict[str, Any] = Field(description="L2缓存统计")
    overall: Dict[str, Any] = Field(description="总体统计")
    config: Dict[str, Any] = Field(description="缓存配置")


class CacheOperationResponse(BaseModel):
    """缓存操作响应"""
    success: bool = Field(description="操作是否成功")
    message: str = Field(description="操作结果消息")
    data: Optional[Dict[str, Any]] = Field(default=None, description="附加数据")


class CacheKeyRequest(BaseModel):
    """缓存键请求"""
    keys: List[str] = Field(description="要操作的缓存键列表")
    pattern: Optional[str] = Field(description="键模式（支持通配符）")


class CachePrewarmRequest(BaseModel):
    """缓存预热请求"""
    task_types: List[str] = Field(description="预热任务类型列表")
    force: bool = Field(default=False, description="是否强制重新预热")


@router.get("/stats", response_model=CacheStatsResponse, summary="获取缓存统计")
async def get_cache_stats():
    """
    获取缓存系统统计信息

    返回L1缓存、L2缓存和总体统计信息，包括：
    - 命中率
    - 缓存大小
    - 淘汰次数
    - 错误次数
    """
    try:
        cache_manager = get_cache_manager()
        if not cache_manager:
            raise HTTPException(
                status_code=503,
                detail="缓存管理器未初始化"
            )

        stats = cache_manager.get_stats()
        return CacheStatsResponse(**stats)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取缓存统计失败: {str(e)}"
        )


@router.post("/clear", response_model=CacheOperationResponse, summary="清理缓存")
async def clear_cache(
    request: CacheKeyRequest,
    background_tasks: BackgroundTasks
):
    """
    清理指定的缓存项

    可以指定具体的键列表，也可以使用模式匹配。
    支持通配符 * 和 ?
    """
    try:
        cache_manager = get_cache_manager()
        if not cache_manager:
            raise HTTPException(
                status_code=503,
                detail="缓存管理器未初始化"
            )

        cleared_keys = []

        # 清理指定的键
        for key in request.keys:
            success = await cache_manager.delete(key)
            if success:
                cleared_keys.append(key)

        # 如果提供了模式，清理匹配的键
        if request.pattern:
            # 这里应该实现模式匹配逻辑
            # 简化实现，实际应该支持Redis的SCAN或keys命令
            logger.info(f"清理模式匹配的缓存: {request.pattern}")
            background_tasks.add_task(
                clear_cache_by_pattern,
                request.pattern
            )

        return CacheOperationResponse(
            success=True,
            message=f"成功清理 {len(cleared_keys)} 个缓存项",
            data={"cleared_keys": cleared_keys}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清理缓存失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"清理缓存失败: {str(e)}"
        )


@router.post("/prewarm", response_model=CacheOperationResponse, summary="缓存预热")
async def prewarm_cache(
    request: CachePrewarmRequest,
    background_tasks: BackgroundTasks
):
    """
    执行缓存预热

    根据指定的任务类型预热缓存数据。
    支持的预热任务：
    - predictions: 预测数据
    - teams: 球队数据
    - hot_matches: 热门比赛
    """
    try:
        cache_initializer = get_cache_initializer()
        if not cache_initializer:
            raise HTTPException(
                status_code=503,
                detail="缓存初始化器未初始化"
            )

        # 验证任务类型
        valid_tasks = {"predictions", "teams", "hot_matches"}
        invalid_tasks = set(request.task_types) - valid_tasks
        if invalid_tasks:
            raise HTTPException(
                status_code=400,
                detail=f"无效的任务类型: {', '.join(invalid_tasks)}"
            )

        # 在后台执行预热任务
        background_tasks.add_task(
            execute_prewarm_tasks,
            request.task_types,
            request.force
        )

        return CacheOperationResponse(
            success=True,
            message=f"已启动 {len(request.task_types)} 个预热任务",
            data={"task_types": request.task_types}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"缓存预热失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"缓存预热失败: {str(e)}"
        )


@router.post("/optimize", response_model=CacheOperationResponse, summary="优化缓存")
async def optimize_cache(background_tasks: BackgroundTasks):
    """
    执行缓存优化

    执行缓存优化任务，包括：
    - 清理过期缓存
    - 根据访问模式调整TTL
    - 提升热键到更高缓存级别
    """
    try:
        cache_initializer = get_cache_initializer()
        if not cache_initializer:
            raise HTTPException(
                status_code=503,
                detail="缓存初始化器未初始化"
            )

        # 在后台执行优化任务
        background_tasks.add_task(
            execute_cache_optimization
        )

        return CacheOperationResponse(
            success=True,
            message="已启动缓存优化任务"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"缓存优化失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"缓存优化失败: {str(e)}"
        )


@router.get("/health", summary="缓存健康检查")
async def cache_health_check():
    """
    检查缓存系统健康状态

    返回缓存系统的连接状态和基本健康指标
    """
    try:
        health_info = {
            "status": "healthy",
            "checks": {},
            "details": {}
        }

        # 检查L1缓存
        cache_manager = get_cache_manager()
        if cache_manager:
            l1_stats = cache_manager.l1_cache.get_stats()
            health_info["checks"]["l1_cache"] = {
                "status": "healthy",
                "size": l1_stats.get("size", 0),
                "max_size": l1_stats.get("max_size", 0),
                "utilization": l1_stats.get("utilization", 0)
            }
        else:
            health_info["checks"]["l1_cache"] = {
                "status": "unavailable",
                "message": "缓存管理器未初始化"
            }
            health_info["status"] = "degraded"

        # 检查L2缓存（Redis）
        if cache_manager and cache_manager.redis_manager:
            try:
                # 测试Redis连接
                await cache_manager.redis_manager.ping()
                health_info["checks"]["l2_cache"] = {
                    "status": "healthy",
                    "type": "Redis"
                }
            except Exception as e:
                health_info["checks"]["l2_cache"] = {
                    "status": "unhealthy",
                    "message": f"Redis连接失败: {str(e)}"
                }
                health_info["status"] = "degraded"
        else:
            health_info["checks"]["l2_cache"] = {
                "status": "disabled",
                "message": "Redis未配置"
            }

        return health_info

    except Exception as e:
        logger.error(f"缓存健康检查失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"健康检查失败: {str(e)}"
        )


@router.get("/config", summary="获取缓存配置")
async def get_cache_config():
    """
    获取当前缓存配置

    返回缓存系统的配置信息
    """
    try:
        from src.config.cache import get_cache_config_manager

        config_manager = get_cache_config_manager()

        return {
            "enabled": config_manager.settings.enabled,
            "default_ttl": config_manager.settings.default_ttl,
            "redis": {
                "host": config_manager.settings.redis_host,
                "port": config_manager.settings.redis_port,
                "db": config_manager.settings.redis_db,
                "max_connections": config_manager.settings.redis_max_connections
            },
            "memory_cache": {
                "size": config_manager.settings.memory_cache_size,
                "ttl": config_manager.settings.memory_cache_ttl
            },
            "preload": {
                "enabled": config_manager.settings.preload_enabled,
                "batch_size": config_manager.settings.preload_batch_size
            },
            "path_configs": config_manager.settings.path_configs
        }

    except Exception as e:
        logger.error(f"获取缓存配置失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取缓存配置失败: {str(e)}"
        )


# 后台任务函数
async def clear_cache_by_pattern(pattern: str):
    """根据模式清理缓存"""
    try:
        cache_manager = get_cache_manager()
        if cache_manager:
            # 这里应该实现模式匹配逻辑
            # 可以使用Redis的SCAN命令或者内存缓存的遍历
            logger.info(f"执行缓存清理任务，模式: {pattern}")
    except Exception as e:
        logger.error(f"缓存清理任务失败: {e}")


async def execute_prewarm_tasks(task_types: List[str], force: bool = False):
    """执行预热任务"""
    try:
        cache_initializer = get_cache_initializer()
        if cache_initializer and cache_initializer.cache_warmer:
            for task_type in task_types:
                if task_type == "predictions":
                    await cache_initializer.cache_warmer.warmup_predictions()
                elif task_type == "teams":
                    await cache_initializer.cache_warmer.warmup_teams()
                elif task_type == "hot_matches":
                    await cache_initializer.cache_warmer._warmup_hot_matches()
                logger.info(f"完成预热任务: {task_type}")
    except Exception as e:
        logger.error(f"预热任务失败: {e}")


async def execute_cache_optimization():
    """执行缓存优化"""
    try:
        cache_initializer = get_cache_initializer()
        if cache_initializer and cache_initializer.cache_optimizer:
            await cache_initializer.cache_optimizer.optimize()
            logger.info("缓存优化任务完成")
    except Exception as e:
        logger.error(f"缓存优化任务失败: {e}")