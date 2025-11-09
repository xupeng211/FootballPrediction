"""
Football Prediction FastAPI Application
足球预测系统主应用文件
"""

import logging
import warnings
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 可选的速率限制功能
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address

    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False

# 导入项目模块
from src.api.health import router as health_router
from src.api.predictions.optimized_router import router as optimized_predictions_router
from src.api.prometheus_metrics import router as prometheus_router
from src.api.schemas import RootResponse
from src.config.openapi_config import setup_openapi
from src.core.event_application import initialize_event_system, shutdown_event_system
from src.cqrs.application import initialize_cqrs
from src.database.definitions import initialize_database
from src.middleware.i18n import I18nMiddleware
from src.observers import ObserverManager
from src.performance.integration import setup_performance_monitoring
from src.performance.middleware import PerformanceMonitoringMiddleware

# 配置日志
warnings.filterwarnings("ignore", category=DeprecationWarning)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    logger.info("启动足球预测系统...")

    # 初始化各个系统
    try:
        # 初始化数据库
        await initialize_database()
        logger.info("✅ 数据库初始化完成")

        # 初始化事件系统
        await initialize_event_system()
        logger.info("✅ 事件系统初始化完成")

        # 初始化CQRS系统
        await initialize_cqrs()
        logger.info("✅ CQRS系统初始化完成")

        # 初始化观察者系统
        ObserverManager.initialize()
        logger.info("✅ 观察者系统初始化完成")

        # 设置性能监控
        setup_performance_monitoring(app)
        logger.info("✅ 性能监控设置完成")

        logger.info("🚀 足球预测系统启动完成!")

    except Exception as e:
        logger.error(f"❌ 系统初始化失败: {e}")
        raise

    yield

    # 清理资源
    logger.info("正在关闭足球预测系统...")
    try:
        await shutdown_event_system()
        logger.info("✅ 事件系统已关闭")
        logger.info("👋 足球预测系统已安全关闭")
    except Exception as e:
        logger.error(f"❌ 系统关闭时出错: {e}")


# 创建FastAPI应用
app = FastAPI(
    title="足球预测系统 API",
    description="基于机器学习的足球比赛结果预测系统",
    version="2.0.0",
    lifespan=lifespan,
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加性能监控中间件
app.add_middleware(PerformanceMonitoringMiddleware)

# 添加中间件
app.add_middleware(I18nMiddleware)

# 配置速率限制(如果可用)
if SLOWAPI_AVAILABLE:
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 注册路由
app.include_router(health_router, prefix="/health", tags=["健康检查"])
app.include_router(
    optimized_predictions_router, prefix="/api/v2/predictions", tags=["预测"]
)
app.include_router(prometheus_router, prefix="/metrics", tags=["监控"])

# 配置OpenAPI
setup_openapi(app)


@app.get("/", response_model=RootResponse, tags=["根端点"])
async def root() -> RootResponse:
    """根端点"""
    return RootResponse(
        message="足球预测系统 API",
        version="2.0.0",
        status="running",
    )


@app.get("/health", tags=["健康检查"])
async def health_check() -> dict:
    """健康检查端点"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "service": "football-prediction-api",
    }


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
