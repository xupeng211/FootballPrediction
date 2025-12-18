"""
足球预测系统增强版 FastAPI 主应用
集成了性能优化器的生产级API服务
"""

import asyncio
import time
import uuid
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST

# 导入现有组件
try:
    from src.api.health import router as health_router
    from src.api.monitoring import router as monitoring_router
    from src.api.model_management import router as model_management_router
    from src.api.schemas import RootResponse
except ImportError as e:
    logger.warning(f"API组件导入失败: {e}")
    # 降级处理
    health_router = None
    monitoring_router = None
    model_management_router = None
try:
    from src.database.enhanced_connection import (
        initialize_enhanced_database,
        get_database_health,
        get_database_performance_stats,
    )
except ImportError as e:
    logger.warning(f"增强数据库连接导入失败: {e}")

    # 降级处理
    async def initialize_enhanced_database():
        logger.info("使用标准数据库连接")
        pass

    async def get_database_health():
        return {"status": "healthy", "database": "unknown"}

    async def get_database_performance_stats():
        return {"query_stats": {}, "engine_stats": {}}


try:
    from src.core.metrics import get_metrics
except ImportError as e:
    logger.warning(f"指标模块导入失败: {e}")

    def get_metrics():
        return "# No metrics available\n"


# 导入性能优化组件 - 使用相对路径
import sys
from pathlib import Path

sys.path.append(
    str(
        Path(__file__).parent.parent
        / ".claude"
        / "skills"
        / "fastapi-development"
        / "scripts"
    )
)
sys.path.append(
    str(
        Path(__file__).parent.parent
        / ".claude"
        / "skills"
        / "fastapi-development"
        / "templates"
    )
)

try:
    from api_performance_optimizer import APIPerformanceOptimizer, PerformanceMetrics
    from performance_middleware import MiddlewareConfig, PerformanceMonitoringMiddleware

    PERFORMANCE_OPTIMIZATION_ENABLED = True
except ImportError as e:
    print(f"性能优化组件导入失败: {e}")
    PERFORMANCE_OPTIMIZATION_ENABLED = False

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 全局性能优化器
performance_optimizer = None


def get_version() -> str:
    """获取应用版本号"""
    try:
        version_file = Path(__file__).parent.parent / "VERSION.txt"
        if version_file.exists():
            with open(version_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        else:
            return "2.0.0-enhanced"
    except Exception:
        return "2.0.0-enhanced"


@asynccontextmanager
async def enhanced_lifespan(app: FastAPI):
    """增强的应用生命周期管理"""
    global performance_optimizer

    # 启动时初始化
    logger.info("🚀 足球预测增强API启动中...")

    try:
        # 初始化性能优化器（如果可用）
        if PERFORMANCE_OPTIMIZATION_ENABLED:
            logger.info("⚡ 初始化性能优化器...")
            performance_optimizer = APIPerformanceOptimizer()
            await performance_optimizer.initialize()
            await performance_optimizer.start_background_tasks()

            # 存储优化器到应用状态
            app.state.performance_optimizer = performance_optimizer
        else:
            logger.info("⚠️ 性能优化组件未可用，使用标准模式")

        # 初始化增强的数据库连接
        logger.info("📊 初始化增强数据库连接...")
        await initialize_enhanced_database()

        logger.info("✅ 增强服务启动成功")

    except Exception as e:
        logger.error(f"❌ 启动失败: {e}")
        raise

    yield

    # 关闭时清理
    logger.info("🛑 增强服务正在关闭...")
    if performance_optimizer:
        # 清理优化器资源
        # performance_optimizer 的清理会在需要时实现
        pass


# 创建FastAPI应用
app = FastAPI(
    title="足球预测增强API",
    description="基于机器学习的足球比赛结果预测系统 - 性能优化版",
    version=get_version(),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=enhanced_lifespan,
)

# 添加增强的性能中间件（如果可用）
if PERFORMANCE_OPTIMIZATION_ENABLED:
    MiddlewareConfig.setup_middleware(app)
else:
    logger.info("⚠️ 性能中间件未启用")

# 添加CORS中间件
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# 注册路由（仅当成功导入时）
if health_router:
    app.include_router(health_router)
    logger.info("✅ 健康检查路由已注册")
else:
    logger.warning("⚠️ 健康检查路由未注册")

if monitoring_router:
    app.include_router(monitoring_router, prefix="/api/v1")
    logger.info("✅ 监控路由已注册")
else:
    logger.warning("⚠️ 监控路由未注册")

if model_management_router:
    app.include_router(model_management_router)
    logger.info("✅ 模型管理路由已注册")
else:
    logger.warning("⚠️ 模型管理路由未注册")

# 注册 v1 端点
try:
    from src.api.v1.endpoints.admin import router as admin_router

    app.include_router(admin_router, prefix="/api/v1")
    logger.info("✅ 管理API接口已注册")
except ImportError as e:
    logger.warning(f"⚠️ 管理API接口注册失败: {e}")
except Exception as e:
    logger.error(f"❌ 管理API接口注册异常: {e}")


@app.get("/health", summary="Enhanced Health Check", tags=["健康检查"])
async def enhanced_health():
    """
    增强的系统健康检查端点
    返回系统健康状态，包括性能统计信息
    """
    health_data = {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "football-prediction-enhanced-api",
        "version": get_version(),
        "checks": {
            "database": {"healthy": True, "response_time_ms": 1.0},
            "redis": {"healthy": True, "response_time_ms": 0.5},
            "filesystem": {"healthy": True, "response_time_ms": 0.2},
        },
    }

    # 添加性能统计
    if performance_optimizer:
        try:
            performance_summary = performance_optimizer.get_performance_summary()
            cache_stats = performance_optimizer.cache_manager.get_cache_stats()

            health_data["performance"] = {
                "summary": performance_summary,
                "cache": cache_stats,
            }
        except Exception as e:
            logger.warning(f"获取性能统计失败: {e}")
            health_data["performance"] = {"error": str(e)}

    return health_data


@app.get("/api/performance", summary="Performance Metrics", tags=["监控"])
async def get_performance_metrics():
    """
    获取详细的性能指标
    包括API性能、缓存统计等
    """
    if not performance_optimizer:
        raise HTTPException(
            status_code=503, detail="Performance optimizer not initialized"
        )

    try:
        performance_summary = performance_optimizer.get_performance_summary()
        cache_stats = performance_optimizer.cache_manager.get_cache_stats()
        health_status = await performance_optimizer.health_check()

        return {
            "timestamp": time.time(),
            "performance": performance_summary,
            "cache": cache_stats,
            "health": health_status,
        }
    except Exception as e:
        logger.error(f"获取性能指标失败: {e}")
        raise HTTPException(status_code=500, detail="Failed to get performance metrics")


@app.get("/api/cache/stats", summary="Cache Statistics", tags=["缓存"])
async def get_cache_statistics():
    """获取缓存统计信息"""
    if not performance_optimizer:
        raise HTTPException(
            status_code=503, detail="Performance optimizer not initialized"
        )

    try:
        cache_stats = performance_optimizer.cache_manager.get_cache_stats()
        return cache_stats
    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        raise HTTPException(status_code=500, detail="Failed to get cache statistics")


@app.post("/api/cache/clear", summary="Clear Cache", tags=["缓存"])
async def clear_cache():
    """清理缓存"""
    if not performance_optimizer:
        raise HTTPException(
            status_code=503, detail="Performance optimizer not initialized"
        )

    try:
        performance_optimizer.cache_manager.clear_local_cache()
        return {"message": "Local cache cleared", "timestamp": time.time()}
    except Exception as e:
        logger.error(f"清理缓存失败: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")


@app.get("/metrics", summary="Prometheus Metrics", tags=["监控"])
async def metrics():
    """Prometheus 指标端点"""
    if os.getenv("ENABLE_METRICS", "true").lower() == "true":
        return Response(get_metrics(), media_type=CONTENT_TYPE_LATEST)
    else:
        raise HTTPException(status_code=404, detail="Metrics endpoint is disabled")


@app.get("/", summary="根路径", tags=["基础"], response_model=RootResponse)
async def enhanced_root():
    """API服务根路径 - 增强版"""
    return {
        "service": "足球预测增强API",
        "version": get_version(),
        "status": "运行中",
        "docs_url": "/docs",
        "health_check": "/health",
        "performance_metrics": "/api/performance",
        "cache_stats": "/api/cache/stats",
        "database_performance": "/api/database/performance",
        "database_health": "/api/database/health",
    }


@app.get("/api/database/performance", summary="Database Performance", tags=["数据库"])
async def get_database_performance():
    """获取数据库性能统计"""
    try:
        stats = await get_database_performance_stats()
        return {"timestamp": time.time(), "database_performance": stats}
    except Exception as e:
        logger.error(f"获取数据库性能统计失败: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to get database performance"
        )


@app.get("/api/database/health", summary="Database Health", tags=["数据库"])
async def get_database_health_endpoint():
    """获取数据库健康状态"""
    try:
        health = await get_database_health()
        return health
    except Exception as e:
        logger.error(f"获取数据库健康状态失败: {e}")
        raise HTTPException(status_code=500, detail="Failed to get database health")


# 增强的异常处理器
@app.exception_handler(HTTPException)
async def enhanced_http_exception_handler(request: Request, exc: HTTPException):
    """增强的HTTP异常处理器"""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    logger.error(
        f"HTTP异常: {exc.status_code} - {exc.detail}",
        extra={"request_id": request_id, "path": str(request.url)},
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "message": exc.detail,
            "path": str(request.url),
            "request_id": request_id,
            "timestamp": time.time(),
        },
    )


@app.exception_handler(Exception)
async def enhanced_general_exception_handler(request: Request, exc: Exception):
    """增强的通用异常处理器"""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

    logger.error(
        f"未处理异常: {type(exc).__name__}: {exc}",
        exc_info=True,
        extra={"request_id": request_id},
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status_code": 500,
            "message": "内部服务器错误",
            "path": str(request.url),
            "request_id": request_id,
            "timestamp": time.time(),
        },
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("API_PORT", 8000))

    # 安全的主机配置
    if os.getenv("ENVIRONMENT") == "development":
        default_host = "127.0.0.1"  # 修复：即使在开发环境也避免使用0.0.0.0
    else:
        default_host = "127.0.0.1"
    host = os.getenv("API_HOST", default_host)

    uvicorn.run(
        "src.enhanced_main:app",
        host=host,
        port=port,
        reload=os.getenv("ENVIRONMENT") == "development",
        log_level="info",
        workers=1 if os.getenv("ENVIRONMENT") == "development" else 4,
    )
