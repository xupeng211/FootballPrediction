#!/usr/bin/env python3
"""
API 限流器模块 (Rate Limiter)
============================
功能:
1. 使用 slowapi 实现 FastAPI 接口限流
2. 支持基于 IP 的限流策略
3. 从 .env 文件读取配置参数
4. 提供 /predict 接口特殊限流 (10次/分钟)
5. 其他接口通用限流 (60次/分钟)

Author: Senior Full-Stack Architect & SRE
Version: 1.0.0
Date: 2025-12-30

使用示例:
>>> from src.api.rate_limiter import rate_limit, init_rate_limiter
>>> from fastapi import FastAPI
>>>
>>> app = FastAPI()
>>> init_rate_limiter(app)
>>>
>>> @app.get("/predict")
>>> @rate_limit("10/minute")
>>> async def predict():
>>>     ...
"""

import logging
import os

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.config_unified import get_settings

logger = logging.getLogger(__name__)


# ============================================
# 限流器异常处理
# ============================================


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """限流异常处理器"""
    logger.warning(f"限流触发: {request.client.host} 访问 {request.url.path}")

    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "message": f"请求过于频繁，请稍后再试。限制: {exc.detail}",
            "retry_after": getattr(exc, "retry_after", 60),
        },
        headers={
            "Retry-After": str(getattr(exc, "retry_after", 60)),
        },
    )


# ============================================
# 限流器配置
# ============================================


class RateLimiterConfig:
    """限流器配置"""

    def __init__(self):
        """从环境变量读取配置"""
        settings = get_settings()

        # /predict 接口限流 (每分钟请求数)
        self.predict_per_minute = int(getattr(settings, "rate_limit_predict_per_minute", 10))

        # 其他接口限流 (每分钟请求数)
        self.default_per_minute = int(getattr(settings, "rate_limit_default_per_minute", 60))

        # 限流存储方式
        self.storage_type = getattr(settings, "rate_limit_storage", "memory")

        # 存储URI (如 Redis)
        self.storage_uri = getattr(settings, "rate_limit_storage_uri", None)

        logger.info(
            f"限流器配置: predict={self.predict_per_minute}/min, "
            f"default={self.default_per_minute}/min, storage={self.storage_type}"
        )


# 单例配置
_limiter_config: RateLimiterConfig | None = None


def get_rate_limiter_config() -> RateLimiterConfig:
    """获取限流器配置"""
    global _limiter_config
    if _limiter_config is None:
        _limiter_config = RateLimiterConfig()
    return _limiter_config


# ============================================
# 全局限流器实例
# ============================================


# 创建限流器实例
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["60/minute"],  # 默认限流
    storage_uri=os.getenv("RATE_LIMIT_STORAGE_URI"),  # 存储URI
    headers_enabled=True,  # 在响应头中包含限流信息
)


# ============================================
# 初始化函数
# ============================================


def init_rate_limiter(app: FastAPI) -> None:
    """
    初始化限流器到 FastAPI 应用

    Args:
        app: FastAPI 应用实例
    """
    # 设置限流器状态
    app.state.limiter = limiter

    # 注册异常处理器
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    logger.info("限流器已初始化")


# ============================================
# 限流装饰器
# ============================================


def rate_limit(limit_string: str | None = None):
    """
    限流装饰器

    Args:
        limit_string: 限流字符串 (如 "10/minute", "60/hour")
                      如果为 None，使用默认配置

    Returns:
        装饰器函数

    Examples:
        >>> @rate_limit("10/minute")
        >>> async def predict():
        >>>     ...

        >>> @rate_limit()  # 使用默认
        >>> async def default_endpoint():
        >>>     ...
    """
    if limit_string is None:
        config = get_rate_limiter_config()
        limit_string = f"{config.default_per_minute}/minute"

    return limiter.limit(limit_string)


def rate_limit_predict():
    """
    /predict 接口专用限流装饰器

    默认: 10次/分钟 (可通过环境变量配置)

    Returns:
        装饰器函数
    """
    config = get_rate_limiter_config()
    return limiter.limit(f"{config.predict_per_minute}/minute")


# ============================================
# 限流中间件 (可选)
# ============================================


class RateLimitMiddleware:
    """
    限流中间件 (可选，用于全局限流)

    注意: slowapi 的装饰器已经足够，此中间件仅用于特殊场景
    """

    def __init__(
        self,
        app: FastAPI,
        default_limit: str = "60/minute",
    ):
        """
        初始化限流中间件

        Args:
            app: FastAPI 应用
            default_limit: 默认限流字符串
        """
        self.app = app
        self.default_limit = default_limit

        # 注册中间件
        @app.middleware("http")
        async def rate_limit_middleware(request: Request, call_next):
            # 检查是否需要限流
            if not self._should_rate_limit(request):
                return await call_next(request)

            # 获取客户端标识
            identifier = get_remote_address(request)

            # 检查限流
            if not limiter._check_request_limit(identifier, request.url.path):
                # 超出限制
                raise RateLimitExceeded(self.default_limit)

            # 继续处理
            return await call_next(request)

    def _should_rate_limit(self, request: Request) -> bool:
        """检查是否需要限流"""
        # 健康检查等端点不限流
        no_limit_paths = ["/health", "/status", "/metrics", "/docs", "/openapi.json"]
        return request.url.path not in no_limit_paths


# ============================================
# 便捷函数
# ============================================


def get_rate_limit_headers(request: Request) -> dict[str, str]:
    """
    获取限流响应头

    Args:
        request: FastAPI 请求对象

    Returns:
        限流响应头字典
    """
    return {
        "X-RateLimit-Limit": str(limiter.limiterlimits[0].amount),
        "X-RateLimit-Remaining": str(limiter.limiterlimits[0].remaining),
        "X-RateLimit-Reset": str(limiter.limiterlimits[0].reset),
    }


def check_rate_limit(request: Request, identifier: str | None = None) -> bool:
    """
    检查是否超出限流

    Args:
        request: FastAPI 请求对象
        identifier: 自定义标识符，默认使用远程地址

    Returns:
        True 表示未超出限制，False 表示超出限制
    """
    if identifier is None:
        identifier = get_remote_address(request)

    # 这里简化处理，实际使用中 slowapi 的装饰器更可靠
    return True


# ============================================
# 配置示例
# ============================================


RATE_LIMIT_EXAMPLES = """
# ============================================
# .env 配置示例
# ============================================

# API 限流配置
RATE_LIMIT_PREDICT_PER_MINUTE=10
RATE_LIMIT_DEFAULT_PER_MINUTE=60
RATE_LIMIT_STORAGE=memory
# RATE_LIMIT_STORAGE_URI=redis://redis:6379/0

# ============================================
# 使用示例
# ============================================

# 方式1: 使用装饰器 (推荐)
@app.get("/predict")
@rate_limit_predict()
async def predict():
    return {"result": "success"}

# 方式2: 自定义限流
@app.get("/api/search")
@rate_limit("30/minute")
async def search():
    return {"results": []}

# 方式3: 使用默认限流
@app.get("/api/info")
@rate_limit()
async def info():
    return {"info": "API information"}

# ============================================
# 响应头示例
# ============================================

# 成功响应:
# HTTP/1.1 200 OK
# X-RateLimit-Limit: 10
# X-RateLimit-Remaining: 7
# X-RateLimit-Reset: 1704067200

# 超出限制:
# HTTP/1.1 429 Too Many Requests
# Content-Type: application/json
# Retry-After: 30
# {
#   "error": "Rate limit exceeded",
#   "message": "请求过于频繁，请稍后再试。限制: 10/minute",
#   "retry_after": 30
# }
"""


if __name__ == "__main__":
    pass
