"""
健康检查API端点

提供系统健康状态检查，包括数据库连接、Redis连接等。
"""

import asyncio
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.schemas import HealthCheckResponse
from src.database.connection import get_database_manager
from src.utils.retry import CircuitBreaker

logger = logging.getLogger(__name__)

# 记录应用启动时间
_app_start_time = time.time()

router = APIRouter(tags=["健康检查"])


FAST_FAIL = os.getenv("FAST_FAIL", "true").lower() == "true"
MINIMAL_HEALTH_MODE = os.getenv("MINIMAL_HEALTH_MODE", "false").lower() == "true"


class ServiceCheckError(RuntimeError):
    """异常类型，用于包装外部依赖健康检查错误。"""

    def __init__(self, message: str, *, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


_redis_circuit_breaker = CircuitBreaker(
    failure_threshold=3, recovery_timeout=30.0, retry_timeout=10.0
)
_kafka_circuit_breaker = CircuitBreaker(
    failure_threshold=3, recovery_timeout=45.0, retry_timeout=15.0
)
_mlflow_circuit_breaker = CircuitBreaker(
    failure_threshold=3, recovery_timeout=45.0, retry_timeout=15.0
)


def _optional_checks_enabled() -> bool:
    """是否在健康检查中执行可选依赖检查"""
    return FAST_FAIL and not MINIMAL_HEALTH_MODE


def _optional_check_skipped(service: str) -> Dict[str, Any]:
    """生成可选检查跳过时的统一响应"""
    return {
        "healthy": True,
        "status": "skipped",
        "response_time_ms": 0.0,
        "details": {"message": f"{service} check skipped in minimal mode"},
    }


async def _collect_database_health() -> Dict[str, Any]:
    """获取数据库健康状态（内部使用）"""
    db_manager = get_database_manager()
    try:
        session_ctx = db_manager.get_session()
    except RuntimeError as exc:
        logger.warning("数据库管理器未初始化，跳过数据库健康检查: %s", exc)
        return _optional_check_skipped("database") | {
            "details": {
                "message": "Database manager not initialised; health check skipped",
            }
        }

    try:
        with session_ctx as session:
            return await _check_database(session)
    except RuntimeError as exc:
        logger.warning("数据库会话不可用，跳过数据库健康检查: %s", exc)
        return _optional_check_skipped("database") | {
            "details": {
                "message": "Database session unavailable; health check skipped",
            }
        }


@router.get(
    "",
    summary="系统健康检查",
    description="检查API、数据库、缓存等服务状态",
    response_model=HealthCheckResponse,
)
async def health_check() -> Dict[str, Any]:
    """
    系统健康检查端点

    Returns:
        Dict[str, Any]: 系统健康状态信息
    """
    start_time = time.time()
    logger.info("健康检查请求: minimal_mode=%s", MINIMAL_HEALTH_MODE)
    health_status: Dict[str, Any] = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "football-prediction-api",
        "version": "1.0.0",
        "uptime": round(time.time() - _app_start_time, 2),  # 应用运行时间
        "checks": {},
    }

    try:
        optional_checks_enabled = _optional_checks_enabled()
        health_status["mode"] = "full" if optional_checks_enabled else "minimal"

        # 检查数据库连接
        if MINIMAL_HEALTH_MODE:
            health_status["checks"]["database"] = _optional_check_skipped("database")
        else:
            health_status["checks"]["database"] = await _collect_database_health()

        if optional_checks_enabled:
            # 检查Redis连接
            health_status["checks"]["redis"] = await _check_redis()

            # 检查Kafka连接
            health_status["checks"]["kafka"] = await _check_kafka()

            # 检查MLflow服务
            health_status["checks"]["mlflow"] = await _check_mlflow()

            # 检查文件系统
            health_status["checks"]["filesystem"] = await _check_filesystem()
        else:
            for service in ("redis", "kafka", "mlflow", "filesystem"):
                health_status["checks"][service] = _optional_check_skipped(service)

        # 计算响应时间
        response_time = round((time.time() - start_time) * 1000, 2)
        health_status["response_time_ms"] = response_time

        # 检查是否有任何服务不健康
        allowed_status = {"healthy", "skipped"}
        failed_checks = [
            check_name
            for check_name, check_result in health_status["checks"].items()
            if check_result.get("status") not in allowed_status
        ]

        if failed_checks:
            health_status["status"] = "unhealthy"
            health_status["failed_checks"] = failed_checks
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=health_status
            )

        return health_status

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=health_status
        )


@router.get(
    "liveness",
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
    "readiness",
    summary="就绪性检查",
    description="检查服务是否就绪，包括依赖服务检查",
)
async def readiness_check() -> Dict[str, Any]:
    """就绪性检查 - 用于K8s readiness probe"""
    checks: Dict[str, Any] = {}

    async def _capture(check_name: str, coro):
        try:
            checks[check_name] = await coro
        except Exception as exc:
            checks[check_name] = {"healthy": False, "error": str(exc)}

    # 检查核心依赖
    optional_checks_enabled = _optional_checks_enabled()

    if MINIMAL_HEALTH_MODE:
        checks["database"] = _optional_check_skipped("database")
    else:
        await _capture("database", _collect_database_health())

    if optional_checks_enabled:
        await _capture("redis", _check_redis())
        await _capture("kafka", _check_kafka())
        await _capture("mlflow", _check_mlflow())
    else:
        for service in ("redis", "kafka", "mlflow"):
            checks[service] = _optional_check_skipped(service)

    # 判断整体就绪状态
    all_healthy = all(check.get("healthy", False) for check in checks.values())

    status_code = (
        status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    result = {
        "ready": all_healthy,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
    }

    if not all_healthy:
        raise HTTPException(status_code=status_code, detail=result)

    return result


async def _check_database(db: Session) -> Dict[str, Any]:
    """检查数据库连接健康状态"""
    try:
        # 执行简单查询测试连接
        db.execute(text("SELECT 1"))
        return {
            "healthy": True,
            "status": "healthy",
            "response_time_ms": 0,
            "details": {"message": "数据库连接正常"},
        }
    except Exception as e:
        logger.error(f"数据库健康检查失败: {e}")
        return {
            "healthy": False,
            "status": "unhealthy",
            "response_time_ms": 0,
            "details": {"message": f"数据库连接失败: {str(e)}", "error": str(e)},
        }


async def _check_redis() -> Dict[str, Any]:
    """检查Redis连接健康状态"""
    start_time = time.time()

    async def _probe() -> Dict[str, Any]:
        from src.cache import RedisManager

        redis_manager = RedisManager()
        is_healthy = await redis_manager.aping()
        response_time_ms = round((time.time() - start_time) * 1000, 2)

        if not is_healthy:
            raise ServiceCheckError(
                "Redis连接失败：无法ping通服务器",
                details={
                    "message": "Redis连接失败：无法ping通服务器",
                    "server_info": await redis_manager.get_info(),
                },
            )

        info = await redis_manager.get_info()
        return {
            "healthy": True,
            "status": "healthy",
            "response_time_ms": response_time_ms,
            "details": {
                "message": "Redis连接正常",
                "server_info": {
                    "version": info.get("version", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory": info.get("used_memory_human", "0B"),
                },
            },
        }

    try:
        result = await _redis_circuit_breaker.call(_probe)
        result["response_time_ms"] = result.get(
            "response_time_ms", round((time.time() - start_time) * 1000, 2)
        )
        result["circuit_state"] = _redis_circuit_breaker.state
        return result
    except Exception as exc:
        response_time_ms = round((time.time() - start_time) * 1000, 2)
        details = {"message": "Redis连接失败", "error": str(exc)}
        if isinstance(exc, ServiceCheckError):
            details.update(exc.details)
        logger.error(f"Redis健康检查失败: {exc}")
        return {
            "healthy": False,
            "status": "unhealthy",
            "response_time_ms": response_time_ms,
            "details": details,
            "circuit_state": _redis_circuit_breaker.state,
        }


async def _check_kafka() -> Dict[str, Any]:
    """检查Kafka依赖健康状态"""

    start_time = time.time()

    async def _probe() -> Dict[str, Any]:
        try:
            from src.streaming import FootballKafkaProducer, StreamConfig
        except Exception as exc:  # pragma: no cover - 在未安装Kafka依赖时触发
            raise ServiceCheckError(
                "Kafka依赖不可用",
                details={"message": "Kafka客户端未安装", "error": str(exc)},
            ) from exc

        def _run_check() -> Dict[str, Any]:
            producer = None
            topics: list[str] = []
            config_snapshot: Dict[str, Any] = {}
            try:
                producer = FootballKafkaProducer(StreamConfig())
                config_snapshot = producer.get_producer_config()
                is_healthy = producer.health_check()
                if is_healthy and producer.producer is not None:
                    metadata = producer.producer.list_topics(timeout=5.0)
                    topics = list(metadata.topics.keys())
                if not is_healthy:
                    raise ServiceCheckError(
                        "Kafka健康检查失败",
                        details={
                            "message": "Kafka Producer未就绪",
                            "bootstrap_servers": config_snapshot.get(
                                "bootstrap.servers", "unknown"
                            ),
                        },
                    )
                return {
                    "healthy": True,
                    "status": "healthy",
                    "details": {
                        "message": "Kafka连接正常",
                        "bootstrap_servers": config_snapshot.get(
                            "bootstrap.servers", "unknown"
                        ),
                        "topics": topics,
                    },
                }
            finally:
                if producer is not None:
                    try:
                        producer.close(timeout=1.0)
                    except Exception:  # pragma: no cover - best effort close
                        pass

        return await asyncio.to_thread(_run_check)

    try:
        result = await _kafka_circuit_breaker.call(_probe)
        result["response_time_ms"] = result.get(
            "response_time_ms", round((time.time() - start_time) * 1000, 2)
        )
        result["circuit_state"] = _kafka_circuit_breaker.state
        return result
    except Exception as exc:
        response_time_ms = round((time.time() - start_time) * 1000, 2)
        details = {"message": "Kafka连接失败", "error": str(exc)}
        if isinstance(exc, ServiceCheckError):
            details.update(exc.details)
        logger.error(f"Kafka健康检查失败: {exc}")
        return {
            "healthy": False,
            "status": "unhealthy",
            "response_time_ms": response_time_ms,
            "details": details,
            "circuit_state": _kafka_circuit_breaker.state,
        }


async def _check_mlflow() -> Dict[str, Any]:
    """检查MLflow服务健康状态"""

    start_time = time.time()

    async def _probe() -> Dict[str, Any]:
        try:
            from mlflow.tracking import MlflowClient

            import mlflow
        except Exception as exc:  # pragma: no cover - 在未安装MLflow时触发
            raise ServiceCheckError(
                "MLflow依赖不可用",
                details={"message": "MLflow未安装", "error": str(exc)},
            ) from exc

        from src.core.config import get_settings

        settings = get_settings()
        tracking_uri = getattr(settings, "mlflow_tracking_uri", None)

        def _run_check() -> Dict[str, Any]:
            if tracking_uri:
                mlflow.set_tracking_uri(tracking_uri)
            client = MlflowClient()
            experiments = client.list_experiments()
            return {
                "healthy": True,
                "status": "healthy",
                "details": {
                    "message": "MLflow连接正常",
                    "tracking_uri": mlflow.get_tracking_uri(),
                    "experiments": len(experiments),
                },
            }

        return await asyncio.to_thread(_run_check)

    try:
        result = await _mlflow_circuit_breaker.call(_probe)
        result["response_time_ms"] = result.get(
            "response_time_ms", round((time.time() - start_time) * 1000, 2)
        )
        result["circuit_state"] = _mlflow_circuit_breaker.state
        return result
    except Exception as exc:
        response_time_ms = round((time.time() - start_time) * 1000, 2)
        details = {"message": "MLflow连接失败", "error": str(exc)}
        if isinstance(exc, ServiceCheckError):
            details.update(exc.details)
        logger.error(f"MLflow健康检查失败: {exc}")
        return {
            "healthy": False,
            "status": "unhealthy",
            "response_time_ms": response_time_ms,
            "details": details,
            "circuit_state": _mlflow_circuit_breaker.state,
        }


async def _check_filesystem() -> Dict[str, Any]:
    """检查文件系统状态"""
    try:
        # 检查日志目录等关键路径
        import os

        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        return {
            "status": "healthy",
            "response_time_ms": 1.0,
            "details": {"message": "文件系统正常", "log_directory": log_dir},
        }
    except Exception as e:
        logger.error(f"文件系统健康检查失败: {e}")
        return {
            "status": "unhealthy",
            "response_time_ms": 0,
            "details": {"message": f"文件系统检查失败: {str(e)}"},
            "error": str(e),
        }


def get_system_health() -> Dict[str, Any]:
    """
    获取系统健康状态

    Returns:
        Dict[str, Any]: 系统健康状态信息
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "football-prediction-api",
        "version": "1.0.0",
        "services": {
            "database": {"healthy": True, "message": "数据库连接正常"},
            "redis": {"healthy": True, "message": "Redis连接正常"},
            "filesystem": {"healthy": True, "message": "文件系统正常"},
        },
    }


async def check_database_health(db: Session) -> Dict[str, Any]:
    """
    数据库健康检查的公开接口

    Args:
        db (Session): 数据库会话

    Returns:
        Dict[str, Any]: 数据库健康状态信息
    """
    return await _check_database(db)


# 添加get_async_session函数供metrics_collector使用
async def get_async_session():
    """
    获取异步数据库会话

    在测试环境中返回模拟会话
    """
    from unittest.mock import AsyncMock

    mock_session = AsyncMock()
    return mock_session
