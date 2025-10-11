"""
FastAPI主应用
FastAPI Main Application

整合所有API路由和中间件。
Integrates all API routes and middleware.
"""

import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Union

from requests.exceptions import HTTPError

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.exceptions import RequestValidationError

from src.core.logging import get_logger
from src.core.prediction import PredictionEngine
from src.config.openapi_config import setup_openapi
from src.api.health import router as health_router
from src.api.predictions import router as predictions_router
from src.api.data_router import router as data_router

logger = get_logger(__name__)

# 全局预测引擎实例
prediction_engine: Union[PredictionEngine, None] = None


async def init_prediction_engine():
    """初始化预测引擎"""
    global prediction_engine
    try:
        prediction_engine = PredictionEngine()
        logger.info("预测引擎初始化成功")
    except (ValueError, KeyError, AttributeError, HTTPError) as e:
        logger.error(f"预测引擎初始化失败: {e}")
        # 不抛出异常，允许应用继续启动


async def close_prediction_engine():
    """关闭预测引擎"""
    global prediction_engine
    if prediction_engine:
        try:
            # 如果预测引擎有清理方法，在这里调用
            prediction_engine = None
            logger.info("预测引擎已关闭")
        except (ValueError, KeyError, AttributeError, HTTPError) as e:
            logger.error(f"关闭预测引擎时出错: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("启动足球预测API服务...")
    await init_prediction_engine()
    logger.info("服务启动完成")

    yield

    # 关闭时清理
    logger.info("关闭足球预测API服务...")
    await close_prediction_engine()
    logger.info("服务已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="Football Prediction API",
    description="足球预测系统API - 提供比赛预测、数据查询和统计分析功能",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# 设置自定义OpenAPI schema
setup_openapi(app)


# 中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    async def dispatch(self, request: Request, call_next):
        start_time = None
        try:
            # 记录请求开始
            start_time = time.time()
            logger.info(
                f"Request started: {request.method} {request.url.path} "
                f"from {request.client.host if request.client else 'unknown'}"
            )

            # 处理请求
            response = await call_next(request)

            # 记录请求完成
            process_time = time.time() - start_time if start_time else 0
            logger.info(
                f"Request completed: {request.method} {request.url.path} "
                f"status={response.status_code} "
                f"duration={process_time:.3f}s"
            )

            # 添加处理时间到响应头
            response.headers["X-Process-Time"] = str(process_time)

            return response

        except (ValueError, KeyError, AttributeError, HTTPError) as e:
            # 记录错误
            process_time = time.time() - start_time if start_time else 0
            logger.error(
                f"Request failed: {request.method} {request.url.path} "
                f"error={str(e)} "
                f"duration={process_time:.3f}s"
            )
            raise


# 添加请求日志中间件
app.add_middleware(RequestLoggingMiddleware)


# 注册路由
app.include_router(health_router, prefix="/api/v1/health", tags=["health"])
app.include_router(predictions_router)
app.include_router(data_router)


# 全局异常处理
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """HTTP异常处理"""
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
                "type": "http_error",
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求验证异常处理"""
    logger.warning(
        f"Validation error at {request.method} {request.url.path}: {exc.errors()}"
    )

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": 422,
                "message": "请求参数验证失败",
                "type": "validation_error",
                "details": exc.errors(),
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理"""
    logger.error(
        f"Unhandled exception at {request.method} {request.url.path}: {str(exc)}",
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "服务器内部错误",
                "type": "internal_error",
            }
        },
    )


# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Football Prediction API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }


# 健康检查
@app.get("/api/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "football-prediction-api",
    }


# Metrics 端点
@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus 格式的指标端点"""
    # 简单的占位符指标
    metrics_data = """# HELP http_requests_total Total number of HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/health"} 1

# HELP request_duration_seconds Request duration in seconds
# TYPE request_duration_seconds histogram
request_duration_seconds_bucket{le="0.1"} 1
request_duration_seconds_bucket{le="1.0"} 1
request_duration_seconds_bucket{le="+Inf"} 1

# HELP api_health_status API health status
# TYPE api_health_status gauge
api_health_status 1
"""
    return Response(content=metrics_data, media_type="text/plain")


# 测试端点
@app.get("/api/test")
async def test_endpoint():
    """测试端点"""
    return {
        "message": "API is working!",
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn
    from datetime import datetime

    # 开发环境配置
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
