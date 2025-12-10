import os
import time
from contextlib import asynccontextmanager
from datetime import datetime

# API Constants
DEFAULT_PORT = 8000
GZIP_MINIMUM_SIZE = 1000
DEFAULT_LIMIT = 100
STATUS_OK = 200
STATUS_BAD_REQUEST = 400
STATUS_UNPROCESSABLE_ENTITY = 422
STATUS_INTERNAL_SERVER_ERROR = 500
STATUS_SERVICE_UNAVAILABLE = 503

# 全局异常处理
# 根路径
# 健康检查
# Metrics 端点
# 简单的占位符指标
# TYPE http_requests_total counter
# HELP request_duration_seconds Request duration in seconds
# TYPE request_duration_seconds histogram
# HELP api_health_status API health status
# TYPE api_health_status gauge
# 测试端点
import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response
from requests.exceptions import HTTPError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.adapters.router import router as adapters_router

# 全局预测引擎实例
# 不抛出异常,允许应用继续启动
# 如果预测引擎有清理方法,在这里调用
# 启动时初始化
# 关闭时清理
# 创建FastAPI应用
# 设置自定义OpenAPI schema
# 中间件配置
# 记录请求开始
# 处理请求
# 记录请求完成
# 添加处理时间到响应头
# 记录错误
# 添加请求日志中间件
# 注册路由
# 导入并注册数据集成路由
from src.api.data_integration import router as data_integration_router
from src.api.data_router import router as data_router
from src.api.health import router as health_router
from src.api.monitoring import router as monitoring_router
from src.api.predictions import router as predictions_router

# 导入并注册SRS规范增强预测路由
from src.api.predictions_enhanced import router as predictions_enhanced_router

# 导入并注册SRS规范简化预测路由（不依赖数据库）
from src.api.predictions_srs_simple import router as predictions_srs_simple_router
from src.config.openapi_config import setup_openapi
from src.core.logging import get_logger
from src.core.prediction import PredictionEngine

# 开发环境配置
"""
FastAPI主应用
FastAPI Main Application
整合所有API路由和中间件.
Integrates all API routes and middleware.
"""
logger = get_logger(__name__)
prediction_engine: PredictionEngine | None = None


async def init_prediction_engine():
    """初始化预测引擎."""
    global prediction_engine
    try:
        prediction_engine = PredictionEngine()
        logger.info("预测引擎初始化成功")
    except (ValueError, KeyError, AttributeError, HTTPError) as e:
        logger.error(f"预测引擎初始化失败: {e}")


async def close_prediction_engine():
    """关闭预测引擎."""
    global prediction_engine
    if prediction_engine:
        try:
            prediction_engine = None
            logger.info("预测引擎已关闭")
        except (ValueError, KeyError, AttributeError, HTTPError) as e:
            logger.error(f"关闭预测引擎时出错: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理."""
    logger.info("启动足球预测API服务...")
    await init_prediction_engine()
    logger.info("服务启动完成")
    yield
    logger.info("关闭足球预测API服务...")
    await close_prediction_engine()
    logger.info("服务已关闭")


app = FastAPI(
    title="Football Prediction API",
    description="足球预测系统API - 提供比赛预测,数据查询和统计分析功能",
    version="1.0.0-rc1",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)
setup_openapi(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=GZIP_MINIMUM_SIZE)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件."""

    async def dispatch(self, request: Request, call_next):
        start_time = None
        try:
            start_time = time.time()
            logger.info(
                f"Request started: {request.method} {request.url.path} "
                f"from {request.client.host if request.client else 'unknown'}"
            )
            response = await call_next(request)
            process_time = time.time() - start_time if start_time else 0
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"status={response.status_code} "
                f"duration={process_time:.3f}s"
            )
            response.headers["x-Process-Time"] = str(process_time)
            return response
        except (ValueError, KeyError, AttributeError, HTTPError) as e:
            process_time = time.time() - start_time if start_time else 0
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"error={str(e)} "
                f"duration={process_time:.3f}s"
            )
            raise


app.add_middleware(RequestLoggingMiddleware)
app.include_router(health_router, prefix="/api/v1/health", tags=["health"])
app.include_router(predictions_router)
app.include_router(data_router)
app.include_router(monitoring_router, prefix="/monitoring", tags=["monitoring"])
app.include_router(adapters_router)
app.include_router(data_integration_router, prefix="/api/v1", tags=["data-integration"])
app.include_router(
    predictions_enhanced_router, prefix="/api/v1", tags=["predictions-srs"]
)
app.include_router(
    predictions_srs_simple_router, prefix="/api/v1", tags=["predictions-srs-simple"]
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP异常处理."""
    logger.warning(
        f"HTTP exception: {exc.status_code} {exc.detail} "
        f"at {request.method} {request.url.path}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "typing.Type": "http_error",
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求验证异常处理."""
    logger.warning(
        f"Validation error at {request.method} {request.url.path}: {exc.errors()}"
    )
    return JSONResponse(
        status_code=STATUS_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": STATUS_UNPROCESSABLE_ENTITY,
                "message": "请求参数验证失败",
                "typing.Type": "validation_error",
                "details": exc.errors(),
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理."""
    logger.error(
        f"Unhandled exception at {request.method} {request.url.path}: {str(exc)}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=STATUS_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": STATUS_INTERNAL_SERVER_ERROR,
                "message": "服务器内部错误",
                "typing.Type": "internal_error",
            }
        },
    )


@app.get("/")
async def root():
    """根路径."""
    return {
        "message": "Football Prediction API",
        "version": "1.0.0-rc1",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api")
async def api_info():
    """API信息端点."""
    return {
        "service": "Football Prediction API",
        "version": "1.0.0-rc1",
        "status": "active",
        "endpoints": {
            "health": "/api/health",
            "docs": "/docs",
            "predictions": "/api/v1/predictions",
            "monitoring": "/api/monitoring",
            "data": "/api/v1/data",
        },
    }


@app.get("/api/health")
async def health_check():
    """健康检查端点."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "football-prediction-api",
    }


@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus 格式的指标端点."""
    metrics_data = """# HELP http_requests_total Total number of HTTP requests"
http_requests_total{method="GET",endpoint="/api/health"} 1
request_duration_seconds_bucket{le="0.1"} 1
request_duration_seconds_bucket{le="1.0"} 1
request_duration_seconds_bucket{le="+Inf"} 1
api_health_status 1
"""
    return Response(content=metrics_data, media_type="text/plain")


@app.get("/api/test")
async def test_endpoint():
    """测试端点."""
    return {
        "message": "API is working!",
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    # FIX: 安全的主机绑定配置 - 优先使用环境变量，默认回环地址
    host = os.getenv("HOST", "127.0.0.1")  # 默认绑定到安全的回环地址而非 0.0.0.0
    port = int(os.getenv("PORT", str(DEFAULT_PORT)))

    # 生产环境安全检查
    if host == "0.0.0.0":
        print("⚠️  安全警告: 检测到绑定所有接口 (0.0.0.0)，在生产环境中请使用具体IP地址")

    uvicorn.run(
        "app:app",
        host=host,
        port=port,
        reload=True,
        log_level="info",
    )
