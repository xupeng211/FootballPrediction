"""
足球预测系统 FastAPI 主应用

基于机器学习的足球比赛结果预测API服务
"""

import logging
import os
from contextlib import asynccontextmanager

# 🔧 在应用启动前设置警告过滤器,确保测试日志清洁
try:
    from src.utils.warning_filters import setup_warning_filters

    setup_warning_filters()
except ImportError:
    # 如果警告过滤器模块不可用,手动设置基本过滤器
    import warnings

    # Marshmallow 4.x 已经移除了 warnings 模块
    # 使用通用的消息过滤器
    warnings.filterwarnings()
        "ignore",
        message=r".*Number.*field.*should.*not.*be.*instantiated.*",
        category=DeprecationWarning,
    

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 可选的速率限制功能
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address

    RATE_LIMIT_AVAILABLE = True
except ImportError:
    RATE_LIMIT_AVAILABLE = False
    Limiter = None
    _rate_limit_exceeded_handler = None
    RateLimitExceeded = None

# from src.api.auth import router as auth_router  # Temporarily disabled
from src.api.health import router as health_router
from src.api.schemas import RootResponse
from src.config.openapi_config import setup_openapi
from src.core.event_application import ()
    initialize_event_system,
    shutdown_event_system,

from src.cqrs.application import initialize_cqrs
from src.database.connection import initialize_database
from src.middleware.i18n import I18nMiddleware
from src.monitoring.metrics_collector import ()
    start_metrics_collection,
    stop_metrics_collection,

from src.observers import ()
    initialize_observer_system,
    start_observer_system,
    stop_observer_system,

from src.performance.integration import setup_performance_monitoring

# 配置日志
logging.basicConfig()
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"

logger = logging.getLogger(__name__)

MINIMAL_API_MODE = os.getenv("MINIMAL_API_MODE", "false").lower() == "true"

# 配置API速率限制(如果可用)
if RATE_LIMIT_AVAILABLE:
    limiter = Limiter()
        key_func=get_remote_address,
        default_limits=[)
            "100/minute",
            "1000/hour",
        ,  # 默认限制:每分钟100次,每小时1000次
        storage_uri=os.getenv("REDIS_URL", "memory://"),  # 使用Redis存储,回退到内存
        headers_enabled=True,  # 在响应头中返回速率限制信息
    
else:
    limiter = None
    logger.warning()
        "⚠️  slowapi 未安装,API速率限制功能已禁用.安装方法: pip install slowapi"
    


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("🚀 足球预测API启动中...")

    try:
        # 初始化数据库连接
        logger.info("📊 初始化数据库连接...")
        initialize_database()

        # 启动监控指标收集
        logger.info("📈 启动监控指标收集...")
        await start_metrics_collection()

        # 初始化事件系统
        logger.info("🔌 初始化事件系统...")
        await initialize_event_system()

        # 初始化观察者系统
        logger.info("👁️ 初始化观察者系统...")
        await initialize_observer_system()
        await start_observer_system()

        # 初始化CQRS系统
        logger.info("⚡ 初始化CQRS系统...")
        await initialize_cqrs()

        # 初始化性能监控系统
        logger.info("📊 初始化性能监控系统...")
        setup_performance_monitoring(app)

        logger.info("✅ 服务启动成功")

    except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
        logger.error(f"❌ 启动失败: {e}")
        raise

    yield

    # 关闭时清理
    logger.info("🛑 服务正在关闭...")

    # 停止监控指标收集
    logger.info("📉 停止监控指标收集...")
    await stop_metrics_collection()

    # 关闭事件系统
    logger.info("🔌 关闭事件系统...")
    await shutdown_event_system()

    # 关闭观察者系统
    logger.info("👁️ 关闭观察者系统...")
    await stop_observer_system()

    # 清理性能监控系统
    logger.info("📊 清理性能监控系统...")
    from src.performance.integration import get_performance_integration

    performance_integration = get_performance_integration()
    performance_integration.cleanup()


# 创建FastAPI应用(详细信息在 openapi_config.py 中配置)
app = FastAPI()
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,


# 配置速率限制(如果可用)
if RATE_LIMIT_AVAILABLE and limiter:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info("✅ API速率限制已启用")

# 配置 OpenAPI 文档
setup_openapi(app)

# 配置CORS(使用统一配置)
from src.config.cors_config import get_cors_config

# 添加国际化中间件
app.add_middleware(I18nMiddleware)

# 添加CORS中间件(统一配置)
app.add_middleware(CORSMiddleware, **get_cors_config())

# 注册路由
app.include_router(health_router, prefix="/api/health")
app.include_router(auth_router, prefix="/api/auth", tags=["认证"])

if MINIMAL_API_MODE:
    logger.info("MINIMAL_API_MODE 启用,仅注册健康检查路由")
else:
    from src.api.adapters import router as adapters_router
    from src.api.cqrs import router as cqrs_router
    from src.api.data_router import ()
        router as data_router,
    
    from src.api.decorators import router as decorators_router
    from src.api.events import router as events_router
    from src.api.facades import router as facades_router

    # runtime import for minimal mode
    from src.api.features import router as features_router
    from src.api.monitoring import router as monitoring_router
    from src.api.observers import router as observers_router
    from src.api.predictions import router as predictions_router
    from src.api.repositories import router as repositories_router

    app.include_router(monitoring_router, prefix="/api/v1")
    app.include_router(features_router, prefix="/api/v1")
    app.include_router(data_router, prefix="/api/v1")
    app.include_router(predictions_router, prefix="/api/v1")
    app.include_router(events_router, prefix="/api/v1")
    app.include_router(observers_router, prefix="/api/v1")
    app.include_router(cqrs_router, prefix="/api/v1")
    app.include_router(repositories_router, prefix="/api/v1")
    app.include_router(decorators_router, prefix="/api/v1")
    app.include_router(adapters_router, prefix="/api/v1")
    app.include_router(facades_router, prefix="/api/v1")


@app.get("/", summary="根路径", tags=["基础"], response_model=RootResponse)
async def root():
    """
    API服务根路径

    提供服务基本信息,包括版本号,文档地址等.
    适用于服务发现和基本信息查询.
    """
    return {)
        "service": "足球预测API",
        "version": "1.0.0",
        "status": "运行中",
        "docs_url": "/docs",
        "health_check": "/api/health",
    


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """
    HTTP异常处理器

    统一处理HTTP异常,返回标准错误格式.
    """
    logger.error(f"HTTP异常: {exc.status_code} - {exc.detail}")
    return JSONResponse()
        status_code=exc.status_code,
        content={)
            "error": True,
            "status_code": exc.status_code,
            "message": exc.detail,
            "path": str(request.url),
        ,
    


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """
    通用异常处理器

    处理所有未被捕获的异常,确保返回标准错误格式.
    记录详细错误信息用于调试.
    """
    logger.error(f"未处理异常: {type(exc).__name__}: {exc}")
    return JSONResponse()
        status_code=500,
        content={)
            "error": True,
            "status_code": 500,
            "message": "内部服务器错误",
            "path": str(request.url),
        ,
    


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("API_PORT", 8000))
    # 安全修复:根据环境设置默认主机地址
    # 开发环境允许所有接口访问,生产环境只允许本地访问
    if os.getenv("ENVIRONMENT") == "development":
        default_host = "0.0.0.0"  # nosec B104 # 开发环境允许绑定所有接口
    else:
        default_host = "127.0.0.1"
    host = os.getenv("API_HOST", default_host)

    uvicorn.run()
        "src.main:app",
        host=host,
        port=port,
        reload=os.getenv("ENVIRONMENT") == "development",
        log_level="info",
    
