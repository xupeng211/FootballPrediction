from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from src.core.logging import get_logger
from src.monitoring.health_checker import HealthStatus, health_checker

"""
健康检查路由
Health Check Routes

提供全面的健康检查API端点，包括系统状态、依赖检查和性能指标。
"""

logger = get_logger(__name__)
router = APIRouter()


async def basic_health_check():
    """基础健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
        "service": "football-prediction-api",
        "version": "1.0.0",
    }


async def detailed_health_check():
    """详细健康检查端点"""
    try:
        health_report = await health_checker.check_all()
        return JSONResponse(
            content=health_report,
            status_code=(
                200 if health_report["status"] == HealthStatus.HEALTHY.value else 503
            ),
        )
    except Exception as e:
        logger.error(f"详细健康检查失败: {e}")
        return JSONResponse(
            content={
                "status": "unhealthy",
                "timestamp": datetime.now(UTC).isoformat(),
                "error": f"健康检查执行失败: {str(e)}",
            },
            status_code=503,
        )


async def component_health_check(
    component: str = Query(..., description="组件名称"),
):
    """检查特定组件的健康状态"""
    try:
        result = await health_checker.check_single(component)
        if not result:
            raise HTTPException(status_code=404, detail=f"组件 '{component}' 不存在")

        status_code = 200
        if result.status == HealthStatus.UNHEALTHY:
            status_code = 503
        elif result.status == HealthStatus.DEGRADED:
            status_code = 200  # 降级但仍可访问

        return JSONResponse(
            content={
                "component": result.name,
                "status": result.status.value,
                "message": result.message,
                "response_time": round(result.response_time, 3),
                "timestamp": result.timestamp.isoformat(),
                "details": result.details,
            },
            status_code=status_code,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"组件健康检查失败 {component}: {e}")
        return JSONResponse(
            content={
                "component": component,
                "status": "unknown",
                "message": f"检查失败: {str(e)}",
                "timestamp": datetime.now(UTC).isoformat(),
            },
            status_code=500,
        )


async def readiness_check():
    """就绪检查 - 服务是否准备好接收请求"""
    try:
        health_report = await health_checker.check_all()

        # 检查关键组件是否健康
        critical_checks = ["database", "redis"]
        for check_name in critical_checks:
            for check in health_report.get("checks", []):
                if check.get("name") == check_name and check.get("status") in [
                    "unhealthy",
                    "unknown",
                ]:
                    return JSONResponse(
                        content={
                            "status": "not_ready",
                            "timestamp": datetime.now(UTC).isoformat(),
                            "reason": f"关键组件 {check_name} 状态异常",
                            "details": check,
                        },
                        status_code=503,
                    )

        return JSONResponse(
            content={
                "status": "ready",
                "timestamp": datetime.now(UTC).isoformat(),
                "checks": health_report.get("checks", []),
            },
            status_code=200,
        )

    except Exception as e:
        logger.error(f"就绪检查失败: {e}")
        return JSONResponse(
            content={
                "status": "not_ready",
                "timestamp": datetime.now(UTC).isoformat(),
                "reason": f"就绪检查失败: {str(e)}",
            },
            status_code=503,
        )


async def liveness_check():
    """存活检查 - 服务是否还在运行"""
    try:
        # 简单的存活检查
        return JSONResponse(
            content={
                "status": "alive",
                "timestamp": datetime.now(UTC).isoformat(),
                "uptime": "running",
            },
            status_code=200,
        )
    except Exception as e:
        logger.error(f"存活检查失败: {e}")
        return JSONResponse(
            content={
                "status": "dead",
                "timestamp": datetime.now(UTC).isoformat(),
                "error": str(e),
            },
            status_code=503,
        )


async def health_metrics():
    """获取健康相关的指标"""
    try:
        # 获取最近的检查结果
        last_results = health_checker.get_last_results()

        # 计算指标
        total_checks = len(last_results)
        healthy_checks = len(
            [r for r in last_results.values() if r.status == HealthStatus.HEALTHY]
        )
        degraded_checks = len(
            [r for r in last_results.values() if r.status == HealthStatus.DEGRADED]
        )
        unhealthy_checks = len(
            [r for r in last_results.values() if r.status == HealthStatus.UNHEALTHY]
        )
        unknown_checks = len(
            [r for r in last_results.values() if r.status == HealthStatus.UNKNOWN]
        )

        # 计算平均响应时间
        avg_response_time = 0.0
        if last_results:
            total_response_time = sum(r.response_time for r in last_results.values())
            avg_response_time = total_response_time / total_checks

        # 计算健康分数 (0-100)
        health_score = 0
        if total_checks > 0:
            health_score = (
                healthy_checks * 100 + degraded_checks * 50 + unknown_checks * 25
            ) / total_checks

        metrics = {
            "timestamp": datetime.now(UTC).isoformat(),
            "total_checks": total_checks,
            "healthy_checks": healthy_checks,
            "degraded_checks": degraded_checks,
            "unhealthy_checks": unhealthy_checks,
            "unknown_checks": unknown_checks,
            "health_score": round(health_score, 2),
            "avg_response_time": round(avg_response_time, 3),
            "last_update": (
                max(r.timestamp for r in last_results.values()).isoformat()
                if last_results
                else None
            ),
        }

        return metrics

    except Exception as e:
        logger.error(f"获取健康指标失败: {e}")
        return JSONResponse(
            content={
                "error": f"获取健康指标失败: {str(e)}",
                "timestamp": datetime.now(UTC).isoformat(),
            },
            status_code=500,
        )


async def health_summary():
    """获取健康状态摘要"""
    try:
        summary = health_checker.get_check_summary()
        available_checks = health_checker.get_available_checks()

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "summary": summary,
            "available_checks": available_checks,
        }

    except Exception as e:
        logger.error(f"获取健康摘要失败: {e}")
        return JSONResponse(
            content={
                "error": f"获取健康摘要失败: {str(e)}",
                "timestamp": datetime.now(UTC).isoformat(),
            },
            status_code=500,
        )


async def health_history(
    limit: int = Query(100, description="返回记录数量限制", ge=1, le=1000),
):
    """获取健康检查历史记录"""
    try:
        # 这里应该从数据库或缓存中获取历史记录
        # 暂时返回当前状态
        current_health = await health_checker.check_all()

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "current": current_health,
            "history": [],  # TODO: 实现历史记录存储
            "note": "历史记录功能待实现",
        }

    except Exception as e:
        logger.error(f"获取健康历史失败: {e}")
        return JSONResponse(
            content={
                "error": f"获取健康历史失败: {str(e)}",
                "timestamp": datetime.now(UTC).isoformat(),
            },
            status_code=500,
        )


async def dependency_check():
    """检查外部依赖状态"""
    try:
        dependencies = {
            "database": {
                "name": "PostgreSQL数据库",
                "status": "unknown",
                "details": {},
            },
            "redis": {
                "name": "Redis缓存",
                "status": "unknown",
                "details": {},
            },
            "external_apis": {
                "name": "外部API服务",
                "status": "unknown",
                "details": {},
            },
        }

        # 检查数据库
        db_result = await health_checker.check_single("database")
        if db_result:
            dependencies["database"]["status"] = db_result.status.value
            dependencies["database"]["details"] = db_result.details

        # 检查Redis
        redis_result = await health_checker.check_single("redis")
        if redis_result:
            dependencies["redis"]["status"] = redis_result.status.value
            dependencies["redis"]["details"] = redis_result.details

        # 检查外部API（示例）
        dependencies["external_apis"]["status"] = "healthy"
        dependencies["external_apis"]["details"] = {"note": "外部API检查待实现"}

        # 计算整体依赖状态
        all_healthy = all(dep["status"] == "healthy" for dep in dependencies.values())
        any_unhealthy = any(
            dep["status"] == "unhealthy" for dep in dependencies.values()
        )

        overall_status = (
            "healthy" if all_healthy else ("unhealthy" if any_unhealthy else "degraded")
        )

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "overall_status": overall_status,
            "dependencies": dependencies,
        }

    except Exception as e:
        logger.error(f"依赖检查失败: {e}")
        return JSONResponse(
            content={
                "error": f"依赖检查失败: {str(e)}",
                "timestamp": datetime.now(UTC).isoformat(),
            },
            status_code=500,
        )


def setup_health_routes(app):
    """设置健康检查路由"""
    app.include_router(router, prefix="/api/v1", tags=["health"])
    logger.info("健康检查路由已设置")


__all__ = ["router", "setup_health_routes", "health_checker"]
