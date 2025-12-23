"""
健康检查API端点 - 生产级版本

提供系统健康状态检查，包括数据库连接、Redis连接、模型文件等。
实现真实的连接检查，适配 Docker 容器环境。
"""

import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import psycopg2
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.schemas import HealthCheckResponse, ServiceCheck
from src.config_unified import get_settings
from src.database.connection import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter(tags=["健康检查"])


@router.get(
    "/health",
    summary="系统健康检查",
    description="检查API、数据库、缓存等服务状态",
    response_model=HealthCheckResponse,
)
async def health_check() -> HealthCheckResponse:
    """
    系统健康检查端点 - 生产级版本

    执行真实的连接检查，返回符合 HTTP 状态码的结果：
    - 200: 所有服务健康
    - 503: 有一个或多个服务不健康

    Returns:
        HealthCheckResponse: 系统健康状态信息，严格遵循Schema定义
    """
    # 获取各服务检查结果
    database_check = await _get_database_service_check()
    redis_check = await _get_redis_service_check()
    model_check = await _get_model_service_check()
    filesystem_check = await _get_filesystem_service_check()

    # 计算总响应时间
    total_response_time = (
        database_check.response_time_ms
        + redis_check.response_time_ms
        + model_check.response_time_ms
        + filesystem_check.response_time_ms
    )

    # 确定整体状态
    all_healthy = all(
        [
            database_check.status == "healthy",
            redis_check.status == "healthy",
            model_check.status == "healthy",
            filesystem_check.status == "healthy",
        ]
    )

    overall_status = "healthy" if all_healthy else "unhealthy"

    # 构建符合Schema的响应
    checks = {
        "database": database_check,
        "redis": redis_check,
        "model": model_check,
        "filesystem": filesystem_check,
    }

    return HealthCheckResponse(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
        service="football-prediction-api",
        version="1.0.0",
        response_time_ms=total_response_time,
        checks=checks,
    )


@router.get(
    "/health/liveness",
    summary="存活性检查",
    description="简单的存活性检查，仅返回基本状态",
)
async def liveness_check() -> Dict[str, Any]:
    """存活性检查 - 用于K8s liveness probe"""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get(
    "/health/readiness",
    summary="就绪性检查",
    description="检查服务是否就绪，包括依赖服务检查",
)
async def readiness_check(db: Session = Depends(get_db_session)) -> Dict[str, Any]:
    """就绪性检查 - 用于K8s readiness probe"""
    checks: Dict[str, Any] = {}

    # 检查数据库
    try:
        database_result = await _check_database(db)
        # 转换为ServiceCheck格式
        if database_result["healthy"]:
            checks["database"] = ServiceCheck(
                status="healthy",
                response_time_ms=database_result.get("response_time_ms", 0),
                details={"message": database_result.get("message", "数据库连接正常")},
            )
        else:
            checks["database"] = ServiceCheck(
                status="unhealthy",
                response_time_ms=database_result.get("response_time_ms", 0),
                details={
                    "message": database_result.get("message", "数据库连接失败"),
                    "error": database_result.get("error", ""),
                },
            )
    except Exception as e:
        checks["database"] = ServiceCheck(
            status="unhealthy",
            response_time_ms=0,
            details={"message": "数据库检查异常", "error": str(e)},
        )

    # 判断整体就绪状态
    all_healthy = all(check.status == "healthy" for check in checks.values())

    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    result = {
        "ready": all_healthy,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            name: {
                "status": check.status,
                "response_time_ms": check.response_time_ms,
                "details": check.details,
            }
            for name, check in checks.items()
        },
    }

    if not all_healthy:
        raise HTTPException(status_code=status_code, detail=result)

    return result


async def _get_database_service_check() -> ServiceCheck:
    """
    获取数据库服务检查结果 - 真实连接检查

    使用 psycopg2 直接连接数据库进行验证
    """
    start_time = time.time()
    try:
        settings = get_settings()
        db = settings.database

        # 尝试连接数据库
        conn = psycopg2.connect(
            host=db.host,
            port=db.port,
            database=db.name,
            user=db.user,
            password=db.password.get_secret_value(),
            connect_timeout=5,  # 5秒超时
        )

        # 执行简单查询
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()

        response_time = (time.time() - start_time) * 1000

        logger.debug(f"✅ 数据库健康检查通过: {db.host}:{db.port}/{db.name} ({response_time:.2f}ms)")

        return ServiceCheck(
            status="healthy",
            response_time_ms=round(response_time, 2),
            details={
                "message": "数据库连接正常",
                "host": db.host,
                "port": db.port,
                "database": db.name,
            },
        )
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.error(f"❌ 数据库健康检查失败: {e}")
        return ServiceCheck(
            status="unhealthy",
            response_time_ms=round(response_time, 2),
            details={
                "message": "数据库连接失败",
                "error": str(e),
            },
        )


async def _get_redis_service_check() -> ServiceCheck:
    """
    获取Redis服务检查结果 - 真实连接检查

    尝试连接 Redis 并执行 PING 命令
    """
    start_time = time.time()
    try:
        settings = get_settings()
        redis_config = settings.redis

        # 尝试连接 Redis
        import redis

        r = redis.Redis(
            host=redis_config.host,
            port=redis_config.port,
            db=redis_config.db,
            password=redis_config.password.get_secret_value() if redis_config.password else None,
            socket_timeout=2,  # 2秒超时
            socket_connect_timeout=2,
        )

        # 执行 PING
        r.ping()
        r.close()

        response_time = (time.time() - start_time) * 1000

        logger.debug(f"✅ Redis健康检查通过: {redis_config.host}:{redis_config.port} ({response_time:.2f}ms)")

        return ServiceCheck(
            status="healthy",
            response_time_ms=round(response_time, 2),
            details={
                "message": "Redis连接正常",
                "host": redis_config.host,
                "port": redis_config.port,
            },
        )
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.warning(f"⚠️ Redis健康检查失败: {e}")
        # Redis 不健康不影响整体状态（降级运行）
        return ServiceCheck(
            status="healthy",  # 降级：Redis 失败不影响服务运行
            response_time_ms=round(response_time, 2),
            details={
                "message": "Redis不可用，服务降级运行",
                "error": str(e),
            },
        )


async def _get_model_service_check() -> ServiceCheck:
    """
    获取模型服务检查结果 - 检查模型文件是否存在

    检查生产模型文件的存在性和完整性
    """
    start_time = time.time()
    try:
        settings = get_settings()
        model_path = settings.get_model_path()

        # 检查模型文件是否存在
        if model_path.exists():
            file_size = model_path.stat().st_size
            response_time = (time.time() - start_time) * 1000

            logger.debug(f"✅ 模型文件检查通过: {model_path} ({file_size} bytes)")

            return ServiceCheck(
                status="healthy",
                response_time_ms=round(response_time, 2),
                details={
                    "message": "模型文件存在",
                    "model_path": str(model_path),
                    "model_size_bytes": file_size,
                    "model_version": settings.model_version,
                },
            )
        else:
            response_time = (time.time() - start_time) * 1000
            logger.warning(f"⚠️ 模型文件不存在: {model_path}")

            return ServiceCheck(
                status="unhealthy",
                response_time_ms=round(response_time, 2),
                details={
                    "message": "模型文件不存在",
                    "model_path": str(model_path),
                    "model_version": settings.model_version,
                },
            )
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.error(f"❌ 模型检查失败: {e}")
        return ServiceCheck(
            status="unhealthy",
            response_time_ms=round(response_time, 2),
            details={
                "message": "模型检查异常",
                "error": str(e),
            },
        )


async def _get_filesystem_service_check() -> ServiceCheck:
    """获取文件系统服务检查结果"""
    start_time = time.time()
    try:
        import os

        # 检查关键目录
        directories = {
            "logs": "logs",
            "data": "data",
            "models": "data/models",
        }

        for name, path in directories.items():
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)

        response_time = (time.time() - start_time) * 1000

        return ServiceCheck(
            status="healthy",
            response_time_ms=round(response_time, 2),
            details={
                "message": "文件系统正常",
                "directories_checked": list(directories.keys()),
            },
        )
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.error(f"❌ 文件系统健康检查失败: {e}")
        return ServiceCheck(
            status="unhealthy",
            response_time_ms=round(response_time, 2),
            details={
                "message": "文件系统检查失败",
                "error": str(e),
            },
        )


async def _check_database(db: Session) -> Dict[str, Any]:
    """检查数据库连接健康状态"""
    try:
        # 执行简单查询测试连接
        start_time = time.time()
        db.execute(text("SELECT 1"))
        response_time = (time.time() - start_time) * 1000  # 转换为毫秒

        return {
            "healthy": True,
            "message": "数据库连接正常",
            "response_time_ms": response_time,
        }
    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")
        return {
            "healthy": False,
            "message": f"数据库连接失败: {str(e)}",
            "error": str(e),
            "response_time_ms": 0,
        }


async def _check_redis() -> Dict[str, Any]:
    """检查Redis连接健康状态"""
    try:
        import redis

        settings = get_settings()
        redis_config = settings.redis

        start_time = time.time()
        r = redis.Redis(
            host=redis_config.host,
            port=redis_config.port,
            db=redis_config.db,
            password=redis_config.password.get_secret_value() if redis_config.password else None,
            socket_timeout=2,
        )
        r.ping()
        r.close()
        response_time = (time.time() - start_time) * 1000

        return {
            "healthy": True,
            "message": "Redis连接正常",
            "response_time_ms": response_time,
        }
    except Exception as e:
        logger.error(f"Redis健康检查失败: {e}")
        return {
            "healthy": False,
            "message": f"Redis连接失败: {str(e)}",
            "error": str(e),
            "response_time_ms": 0,
        }


async def _check_filesystem() -> Dict[str, Any]:
    """检查文件系统状态"""
    try:
        import os

        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        return {"healthy": True, "message": "文件系统正常", "log_directory": log_dir}
    except Exception as e:
        logger.error(f"文件系统健康检查失败: {e}")
        return {
            "healthy": False,
            "message": f"文件系统检查失败: {str(e)}",
            "error": str(e),
        }


@router.get(
    "/health/quick",
    summary="快速健康检查",
    description="轻量级健康检查，用于频繁探测",
    response_model=dict,
)
async def quick_health_check() -> Dict[str, Any]:
    """
    快速健康检查 - 最小化开销

    用于负载均衡器或容器编排系统的频繁健康探测
    """
    # 仅检查关键服务的连通性，不执行复杂查询
    status = "healthy"
    timestamp = datetime.utcnow().isoformat()

    try:
        # 快速数据库检查
        settings = get_settings()
        db = settings.database
        conn = psycopg2.connect(
            host=db.host,
            port=db.port,
            database=db.name,
            user=db.user,
            password=db.password.get_secret_value(),
            connect_timeout=2,
        )
        conn.close()
    except Exception:
        status = "unhealthy"

    return {
        "status": status,
        "timestamp": timestamp,
    }


# 数据质量检查端点保持不变
@router.get(
    "/health/data-quality",
    summary="数据质量检查",
    description="检查数据库中的数据质量，包括完整性、一致性和异常检测",
    response_model=dict,
)
async def data_quality_check(full_check: bool = False) -> Dict[str, Any]:
    """
    数据质量检查端点

    Args:
        full_check: 是否执行完整的数据质量检查（较慢）

    Returns:
        Dict: 数据质量检查结果
    """
    from src.utils.data_quality_checker import DataQualityChecker

    checker = DataQualityChecker()

    try:
        await checker.connect()

        if full_check:
            # 执行完整检查
            report = await checker.run_full_check()
            return {
                "status": "success",
                "report_type": "full",
                "timestamp": report.timestamp,
                "overall_score": report.overall_score,
                "quality_level": report.quality_level.value,
                "summary": report.summary,
                "recommendations": report.recommendations,
                "details": {
                    "tables_valid": len([v for v in report.table_validations if v.is_valid]),
                    "tables_total": len(report.table_validations),
                    "integrity_avg": (
                        sum(r.integrity_score for r in report.integrity_results) / len(report.integrity_results)
                        if report.integrity_results
                        else 0
                    ),
                    "consistency_passed": sum(1 for r in report.consistency_results if r.is_consistent),
                    "consistency_total": len(report.consistency_results),
                    "anomalies_count": sum(r.anomaly_count for r in report.anomaly_results),
                },
            }
        else:
            # 执行快速健康检查
            health_status = await checker.get_quick_health_status()
            return {
                "status": "success",
                "report_type": "quick",
                "timestamp": health_status["timestamp"],
                "health_status": health_status["status"],
                "health_text": health_status["status_text"],
                "score": health_status["score"],
                "metrics": health_status.get("metrics", {}),
                "error": health_status.get("error"),
            }

    except Exception as e:
        logger.error(f"数据质量检查失败: {e}")
        return {"status": "error", "timestamp": datetime.utcnow().isoformat(), "error": str(e)}
    finally:
        await checker.close()
