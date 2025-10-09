"""
管理功能端点
Admin Endpoints

处理缓存管理、健康检查等管理功能的API端点。
"""




    CacheClearResponse,
    HealthCheckResponse,
)

logger = get_logger(__name__)

# 创建路由器
router = APIRouter()


@router.delete("/cache", response_model=CacheClearResponse)
async def clear_prediction_cache(
    pattern: str = Query("predictions:*", description="缓存键模式"),
    engine: PredictionEngine = Depends(get_prediction_engine),
    current_user: Dict = Depends(get_current_user),
):
    """
    清理预测缓存

    Args:
        pattern: 缓存键模式
        engine: 预测引擎
        current_user: 当前用户

    Returns:
        CacheClearResponse: 清理结果
    """
    try:
        # 检查权限（只有管理员可以清理缓存）
        if current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="权限不足")

        cleared = await engine.clear_cache(pattern)

        logger.info(f"用户 {current_user.get('id')} 清理了 {cleared} 个缓存项")

        return CacheClearResponse(
            pattern=pattern,
            cleared_items=cleared,
            message=f"成功清理 {cleared} 个缓存项",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清理缓存失败: {e}")
        raise HTTPException(status_code=500, detail="清理缓存失败")


@router.get("/health", response_model=HealthCheckResponse)
async def prediction_health_check(
    engine: PredictionEngine = Depends(get_prediction_engine),
):
    """
    预测服务健康检查

    Args:
        engine: 预测引擎

    Returns:
        HealthCheckResponse: 健康状态
    """
    try:
        health_status = await engine.health_check()

        # 确保响应符合模型
        if isinstance(health_status, dict):
            health_status["timestamp"] = health_status.get("timestamp", datetime.now().isoformat())
            return HealthCheckResponse(**health_status)



        else:
            # 如果返回的不是字典，创建默认响应
            return HealthCheckResponse(
                status="healthy",
                timestamp=datetime.now().isoformat(),
            )

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return HealthCheckResponse(
            status="unhealthy",
            error=str(e),
            timestamp=datetime.now().isoformat(),
        )