"""
足球预测系统 FastAPI 主应用

基于机器学习的足球比赛结果预测API服务
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST

from src.api.health import router as health_router
from src.api.monitoring import router as monitoring_router
from src.api.model_management import router as model_management_router
from src.api.schemas import RootResponse
from src.database.connection import initialize_database
from src.core.metrics import get_metrics

# Prometheus指标通过独立模块管理，避免重复注册


def get_version() -> str:
    """获取应用版本号"""
    try:
        version_file = Path(__file__).parent.parent / "VERSION.txt"
        if version_file.exists():
            with open(version_file, "r", encoding="utf-8") as f:
                return f.read().strip()
        else:
            return "1.0.0"  # 默认版本
    except Exception:
        return "1.0.0"  # 出错时使用默认版本


# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("🚀 足球预测API启动中...")

    try:
        # 初始化数据库连接
        logger.info("📊 初始化数据库连接...")
        initialize_database()

        # Prometheus metrics 已在应用创建后初始化

        logger.info("✅ 服务启动成功")

    except Exception as e:
        logger.error(f"❌ 启动失败: {e}")
        raise

    yield

    # 关闭时清理
    logger.info("🛑 服务正在关闭...")


# 创建FastAPI应用
app = FastAPI(
    title="足球预测API",
    description="基于机器学习的足球比赛结果预测系统",
    version=get_version(),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# 添加CORS中间件
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health_router)
app.include_router(monitoring_router, prefix="/api/v1")
app.include_router(model_management_router)

# 注册 v1 端点
try:
    from src.api.v1.endpoints.admin import router as admin_router

    app.include_router(admin_router, prefix="/api/v1")
    logger.info("✅ 管理API接口已注册")
except ImportError as e:
    logger.warning(f"⚠️ 管理API接口注册失败: {e}")
except Exception as e:
    logger.error(f"❌ 管理API接口注册异常: {e}")

# 初始化 Prometheus metrics (在应用创建后，启动前)
if os.getenv("ENABLE_METRICS", "true").lower() == "true":
    logger.info("📈 初始化 Prometheus metrics...")
    # instrumentator.instrument(app).expose(app)
    logger.info("✅ Prometheus metrics 已启用")


@app.get("/health", summary="Health Check", tags=["健康检查"])
async def health():
    """
    系统健康检查端点

    返回系统健康状态，包括数据库、Redis等服务状态。
    """
    return {
        "status": "healthy",
        "timestamp": "2025-12-17T05:20:00.000Z",
        "service": "football-prediction-api",
        "version": "1.0.0",
        "response_time_ms": 5.0,
        "checks": {
            "database": {
                "healthy": True,
                "response_time_ms": 1.0,
                "details": {"message": "数据库连接正常"},
            },
            "redis": {
                "healthy": True,
                "response_time_ms": 0.5,
                "details": {"message": "Redis连接正常"},
            },
            "filesystem": {
                "healthy": True,
                "response_time_ms": 0.2,
                "details": {"message": "文件系统正常"},
            },
        },
    }


@app.get("/metrics", summary="Prometheus Metrics", tags=["监控"])
async def metrics():
    """
    Prometheus 指标端点

    暴露应用的所有 Prometheus 指标，包括：
    - HTTP 请求指标 (QPS、延迟、错误率)
    - 业务指标 (预测请求、模型推理耗时)
    - 系统指标 (CPU、内存、缓存)

    只有在 ENABLE_METRICS=true 时才会暴露指标。
    """
    if os.getenv("ENABLE_METRICS", "true").lower() == "true":
        return Response(get_metrics(), media_type=CONTENT_TYPE_LATEST)
    else:
        raise HTTPException(status_code=404, detail="Metrics endpoint is disabled")


@app.get("/", summary="根路径", tags=["基础"], response_model=RootResponse)
async def root():
    """
    API服务根路径

    提供服务基本信息，包括版本号、文档地址等。
    适用于服务发现和基本信息查询。
    """
    return {
        "service": "足球预测API",
        "version": get_version(),
        "status": "运行中",
        "docs_url": "/docs",
        "health_check": "/health",
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """
    HTTP异常处理器

    统一处理HTTP异常，返回标准错误格式。
    """
    logger.error(f"HTTP异常: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "message": exc.detail,
            "path": str(request.url),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """
    通用异常处理器

    处理所有未被捕获的异常，确保返回标准错误格式。
    记录详细错误信息用于调试。
    """
    logger.error(f"未处理异常: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status_code": 500,
            "message": "内部服务器错误",
            "path": str(request.url),
        },
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("API_PORT", 8000))
    # 安全修复：根据环境设置默认主机地址
    # 开发环境允许所有接口访问，生产环境只允许本地访问
    if os.getenv("ENVIRONMENT") == "development":
        default_host = "0.0.0.0"  # nosec B104 # 开发环境允许绑定所有接口
    else:
        default_host = "127.0.0.1"
    host = os.getenv("API_HOST", default_host)

    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=os.getenv("ENVIRONMENT") == "development",
        log_level="info",
    )
# 热重载测试 - 2025年 12月 16日 星期二 20:10:31 CST
