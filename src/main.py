"""
Football Prediction FastAPI Application
足球预测系统主应用文件
"""

import logging
import os
from contextlib import asynccontextmanager

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# 可选的速率限制功能
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address
    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False

from src.api.health import router as health_router
from src.api.schemas import RootResponse
from src.config.openapi_config import setup_openapi
from src.core.event_application import initialize_event_system, shutdown_event_system
from src.cqrs.application import initialize_cqrs
from src.database.connection import initialize_database
from src.middleware.i18n import I18nMiddleware
from src.monitoring.metrics_collector import MetricsCollector
from src.observers import ObserverManager
from src.performance.integration import setup_performance_monitoring

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 Starting Football Prediction API...")

    # 初始化各个系统
    await initialize_database()
    initialize_event_system()
    initialize_cqrs()
    ObserverManager.initialize()
    MetricsCollector.initialize()
    setup_performance_monitoring()

    logger.info("✅ All systems initialized successfully")

    yield

    # 清理资源
    logger.info("🔄 Shutting down...")
    shutdown_event_system()
    logger.info("✅ Shutdown complete")


# 创建FastAPI应用
app = FastAPI(
    title="Football Prediction API",
    description="Advanced football match prediction system",
    version="2.0.0",
    lifespan=lifespan,
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加中间件
app.add_middleware(I18nMiddleware)

# 注册路由
app.include_router(health_router, prefix="/api", tags=["health"])

# 配置OpenAPI
setup_openapi(app)


# 配置速率限制（如果可用）
if SLOWAPI_AVAILABLE:
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/", response_model=RootResponse)
async def root():
    """根端点"""
    return RootResponse(
        message="Football Prediction API",
        version="2.0.0",
        status="healthy"
    )


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )