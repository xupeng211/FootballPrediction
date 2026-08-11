"""
健康检查API端点 - 生产级版本

提供系统健康状态检查，包括数据库连接、Redis连接、模型文件等。
实现真实的连接检查，适配 Docker 容器环境。

V76.100: 移除 SQLAlchemy 双轨制，统一使用 asyncpg 连接池。
"""

from datetime import UTC, datetime
import logging
from pathlib import Path
import time
from typing import Any

from fastapi import APIRouter, HTTPException, status
import redis

from src.api.schemas import HealthCheckResponse, ServiceCheck
from src.config import get_settings
from src.database.db_pool import DatabasePool
from src.ml.inference.artifact_manifest import ReadinessManager
from src.utils.data_quality_checker import DataQualityChecker

logger = logging.getLogger(__name__)

router = APIRouter(tags=["健康检查"])

# 进程本地模型就绪状态（每 Uvicorn worker 独立实例）。整文件 SHA256 校验
# 只在显式初始化/刷新时执行并缓存；健康请求只读缓存，绝不重复哈希。
_readiness_manager = ReadinessManager()


async def _model_readiness() -> tuple[bool, str]:
    """缓存的 API 模型就绪状态：(ready, reason)。首次调用触发一次性校验。"""
    return _readiness_manager.api_ready()


@router.get(
    "/health",
    summary="系统健康检查",
    description="检查API、数据库、缓存等服务状态",
    response_model=HealthCheckResponse,
)
async def health_check() -> HealthCheckResponse:
    """
    系统健康检查端点 - 信息性汇总（非就绪门控）

    汇总 database / redis / model / filesystem 检查结果；无论服务是否
    健康均返回 HTTP 200（body 中对应 check 为 unhealthy）。该端点不决定
    容器就绪状态 — 就绪语义由 /health/readiness 与 /health/quick 承担。

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
        timestamp=datetime.now(tz=UTC).isoformat(),
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
async def liveness_check() -> dict[str, Any]:
    """存活性检查 - 用于K8s liveness probe"""
    return {
        "status": "alive",
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }


@router.get(
    "/health/readiness",
    summary="就绪性检查",
    description="检查服务是否就绪，包括依赖服务检查",
)
async def readiness_check() -> dict[str, Any]:
    """就绪性检查 - 用于K8s readiness probe"""
    checks: dict[str, Any] = {}

    # 检查数据库 (V76.100: 使用 asyncpg)
    try:
        database_result = await _check_database_async()
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

    # 模型就绪状态（缓存读取；不在此处做整文件哈希）
    model_ready, model_reason = await _model_readiness()
    checks["model"] = ServiceCheck(
        status="healthy" if model_ready else "unhealthy",
        response_time_ms=0.0,
        details={"message": model_reason or "模型就绪"},
    )

    # 判断整体就绪状态
    all_healthy = all(check.status == "healthy" for check in checks.values())

    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    result = {
        "ready": all_healthy,
        "timestamp": datetime.now(tz=UTC).isoformat(),
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

    V76.100: 使用 DatabasePool (asyncpg) 替代 psycopg2
    """
    start_time = time.time()
    try:
        # V76.100: 使用 DatabasePool 进行健康检查

        pool = await DatabasePool.get_instance()
        async with pool.acquire() as conn:
            await conn.fetchrow("SELECT 1")

        response_time = (time.time() - start_time) * 1000

        logger.debug("✅ 数据库健康检查通过 (asyncpg): (%.2fms)", response_time)

        return ServiceCheck(
            status="healthy",
            response_time_ms=round(response_time, 2),
            details={
                "message": "数据库连接正常",
                "driver": "asyncpg",
            },
        )
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.exception("❌ 数据库健康检查失败")
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

        logger.debug(
            "✅ Redis健康检查通过: %s:%s (%.2fms)",
            redis_config.host,
            redis_config.port,
            response_time,
        )

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
        logger.warning("⚠️ Redis健康检查失败: %s", e)
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
    获取模型服务检查结果 - 基于 canonical manifest 的完整性状态（信息性）

    检查 git-tracked manifest 中 API 必需 artifact 的验证状态
    （pending / file missing / checksum mismatch / verified）。整文件
    SHA256 只在初始化/刷新时计算并缓存。本端点不反序列化模型，也不决定
    容器就绪状态 — 就绪语义由 /health/readiness 与 /health/quick 承担。
    """
    start_time = time.time()
    model_ready, model_reason = _readiness_manager.api_ready()
    snapshot = _readiness_manager.snapshot()
    response_time = (time.time() - start_time) * 1000

    api_artifact_status = "unknown"
    for info in snapshot.get("artifacts", {}).values():
        if info.get("required_for") == "api":
            api_artifact_status = info.get("status", "unknown")
            break

    if model_ready:
        logger.debug("模型就绪: manifest 整文件校验通过")
        return ServiceCheck(
            status="healthy",
            response_time_ms=round(response_time, 2),
            details={
                "message": "模型就绪（manifest 整文件校验通过）",
                "artifact_status": api_artifact_status,
            },
        )
    logger.warning("模型未就绪: %s", model_reason)
    return ServiceCheck(
        status="unhealthy",
        response_time_ms=round(response_time, 2),
        details={
            "message": model_reason or "模型未就绪",
            "artifact_status": api_artifact_status,
        },
    )


async def _get_filesystem_service_check() -> ServiceCheck:
    """获取文件系统服务检查结果"""
    start_time = time.time()
    try:
        # 检查关键目录
        directories = {
            "logs": "logs",
            "data": "data",
            "models": "data/models",
        }

        for dir_path in directories.values():
            Path(dir_path).mkdir(parents=True, exist_ok=True)

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
        logger.exception("❌ 文件系统健康检查失败")
        return ServiceCheck(
            status="unhealthy",
            response_time_ms=round(response_time, 2),
            details={
                "message": "文件系统检查失败",
                "error": str(e),
            },
        )


async def _check_database_async() -> dict[str, Any]:
    """
    V76.100: 检查数据库连接健康状态 (asyncpg 版本)

    使用 DatabasePool 和 asyncpg 替代 SQLAlchemy
    """
    start_time = time.time()
    try:
        pool = await DatabasePool.get_instance()
        async with pool.acquire() as conn:
            await conn.fetchrow("SELECT 1")

        response_time = (time.time() - start_time) * 1000

        logger.debug("✅ 数据库健康检查通过 (asyncpg): (%.2fms)", response_time)

        return {
            "healthy": True,
            "message": "数据库连接正常",
            "response_time_ms": round(response_time, 2),
        }
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.exception("❌ 数据库健康检查失败")
        return {
            "healthy": False,
            "message": f"数据库连接失败: {e!s}",
            "error": str(e),
            "response_time_ms": round(response_time, 2),
        }


async def _check_redis() -> dict[str, Any]:
    """检查Redis连接健康状态"""
    try:
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
    except Exception as e:
        logger.exception("Redis健康检查失败")
        return {
            "healthy": False,
            "message": f"Redis连接失败: {e!s}",
            "error": str(e),
            "response_time_ms": 0,
        }
    else:
        return {
            "healthy": True,
            "message": "Redis连接正常",
            "response_time_ms": response_time,
        }


async def _check_filesystem() -> dict[str, Any]:
    """检查文件系统状态"""
    try:
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.exception("文件系统健康检查失败")
        return {
            "healthy": False,
            "message": f"文件系统检查失败: {e!s}",
            "error": str(e),
        }
    else:
        return {"healthy": True, "message": "文件系统正常", "log_directory": str(log_dir)}


@router.get(
    "/health/quick",
    summary="快速健康检查",
    description="轻量级就绪探测（Docker healthcheck）：DB 连通性 + 缓存的模型就绪状态；不做整文件哈希、不加载模型。not-ready 返回 503。",
    response_model=dict,
)
async def quick_health_check() -> dict[str, Any]:
    """
    快速健康检查 - readiness 的廉价子集

    仅执行：
    - 轻量 DB 检查（SELECT 1，无错误详情外泄）
    - 读取缓存的 API 模型就绪状态（首次初始化后不再哈希）

    任一不满足 → HTTP 503（绝不返回假绿 200）。用于负载均衡器或
    容器编排系统的频繁就绪探测。
    """
    timestamp = datetime.now(tz=UTC).isoformat()
    checks = {"database": await _check_database_quick()}
    model_ready, _model_reason = await _model_readiness()
    checks["model"] = model_ready

    if not all(checks.values()):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "timestamp": timestamp, "checks": checks},
        )
    return {"status": "healthy", "timestamp": timestamp, "checks": checks}


async def _check_database_quick() -> bool:
    """Cheap DB liveness (SELECT 1 via asyncpg pool); no error detail leak."""
    try:
        pool = await DatabasePool.get_instance()
        async with pool.acquire() as conn:
            await conn.fetchrow("SELECT 1")
    except Exception:
        logger.exception("快速健康检查数据库连接失败")
        return False
    else:
        return True


# 数据质量检查端点保持不变
@router.get(
    "/health/data-quality",
    summary="数据质量检查",
    description="检查数据库中的数据质量，包括完整性、一致性和异常检测",
    response_model=dict,
)
async def data_quality_check(full_check: bool = False) -> dict[str, Any]:
    """
    数据质量检查端点

    Args:
        full_check: 是否执行完整的数据质量检查（较慢）

    Returns:
        Dict: 数据质量检查结果
    """
    checker = DataQualityChecker()  # type: ignore[no-untyped-call]

    try:
        await checker.connect()  # type: ignore[no-untyped-call]

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
                        sum(r.integrity_score for r in report.integrity_results)
                        / len(report.integrity_results)
                        if report.integrity_results
                        else 0
                    ),
                    "consistency_passed": sum(
                        1 for r in report.consistency_results if r.is_consistent
                    ),
                    "consistency_total": len(report.consistency_results),
                    "anomalies_count": sum(r.anomaly_count for r in report.anomaly_results),
                },
            }
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
        logger.exception("数据质量检查失败")
        return {"status": "error", "timestamp": datetime.now(tz=UTC).isoformat(), "error": str(e)}
    finally:
        await checker.close()  # type: ignore[no-untyped-call]
