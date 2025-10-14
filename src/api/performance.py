from typing import Any, Dict, List, Optional, Union
"""
API性能优化配置和中间件
"""

import time
import asyncio
from fastapi import Request, Response, HTTPException
from fastapi.middleware import Middleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import RequestResponseEndpoint
import uvloop
import logging

from src.core.logging import get_logger
from src.cache.optimizer import cache_optimizer

logger = get_logger(__name__)


class PerformanceMiddleware(BaseHTTPMiddleware):
    """性能监控中间件"""

    def __init__(self, app, max_request_size: int = 10 * 1024 * 1024):  # 10MB
        super().__init__(app)
        self.max_request_size = max_request_size
        self.request_count = 0
        self.error_count = 0
        self.total_response_time = 0

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()

        # 检查请求大小
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_request_size:
            raise HTTPException(
                status_code=413,
                detail=f"Request too large. Max size: {self.max_request_size} bytes"
            )

        # 添加请求ID
        request_id = f"{int(time.time() * 1000)"-{self.request_count}"
        request.state.request_id = request_id

        # 记录请求开始
        logger.info(
            "Request started",
            method=request.method,
            url=str(request.url),
            request_id=request_id
        )

        # 执行请求
        try:
            response = await call_next(request)
            status_code = response.status_code

            # 计算响应时间
            process_time = time.time() - start_time
            self.total_response_time += process_time
            self.request_count += 1

            # 添加响应头
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.4f""
            response.headers["X-Request-Count"] = str(self.request_count)

            # 记录慢请求
            if process_time > 1.0:
                logger.warning(
                    "Slow request detected",
                    method=request.method,
                    url=str(request.url),
                    process_time=process_time,
                    request_id=request_id
                )

            # 记录请求完成
            logger.info(
                "Request completed",
                method=request.method,
                url=str(request.url),
                status_code=status_code,
                process_time=process_time,
                request_id=request_id
            )

            return response

        except Exception as e:
            self.error_count += 1
            process_time = time.time() - start_time

            logger.error(
                "Request failed",
                method=request.method,
                url=str(request.url),
                error=str(e),
                process_time=process_time,
                request_id=request_id
            )

            # 记录错误指标
            await cache_optimizer.increment("api:error_count")

            raise

    def get_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        avg_response_time = self.total_response_time / self.request_count if self.request_count > 0 else 0
        error_rate = self.error_count / self.request_count if self.request_count > 0 else 0

        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "avg_response_time": avg_response_time,
            "error_rate": error_rate
        }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件"""

    def __init__(self, app, requests_per_minute: int = 60, burst: int = 10):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst = burst
        self.clients: Dict[str, Dict[str, Any] = {}

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_ip = self.get_client_ip(request)
        current_time = time.time()

        # 获取或创建客户端记录
        if client_ip not in self.clients:
            self.clients[client_ip] = {
                "tokens": self.burst,
                "last_update": current_time
            }

        client = self.clients[client_ip]

        # 更新令牌（令牌桶算法）
        time_passed = current_time - client["last_update"]
        tokens_to_add = time_passed * (self.requests_per_minute / 60)
        client["tokens"] = min(self.burst, client["tokens"] + tokens_to_add)
        client["last_update"] = current_time

        # 检查是否有可用令牌
        if client["tokens"] < 1:
            logger.warning(
                "Rate limit exceeded",
                ip=client_ip,
                tokens=client["tokens"]
            )
            raise HTTPException(
                status_code=429,
                detail="Too many requests"
            )

        # 消耗一个令牌
        client["tokens"] -= 1

        # 清理过期客户端记录
        await self.cleanup_clients()

        return await call_next(request)

    def get_client_ip(self, request: Request) -> str:
        """获取客户端IP"""
        # 检查代理头
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # 使用直接连接的IP
        return request.client.host

    async def cleanup_clients(self):
        """清理过期的客户端记录"""
        current_time = time.time()
        expired_clients = []

        for ip, client in self.clients.items():
            if current_time - client["last_update"] > 300:  # 5分钟
                expired_clients.append(ip)

        for ip in expired_clients:
            del self.clients[ip]


class CacheMiddleware(BaseHTTPMiddleware):
    """响应缓存中间件"""

    def __init__(self, app, cache_ttl: int = 300):
        super().__init__(app)
        self.cache_ttl = cache_ttl
        self.cacheable_methods = ["GET"]
        self.cacheable_paths = [
            "/api/health",
            "/api/teams",
            "/api/matches",
            "/api/statistics"
        ]

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # 只缓存GET请求
        if request.method not in self.cacheable_methods:
            return await call_next(request)

        # 检查是否为可缓存路径
        path = request.url.path
        if not any(path.startswith(p) for p in self.cacheable_paths):
            return await call_next(request)

        # 生成缓存键
        cache_key = f"response:{path}:{str(request.query_params)}"

        # 尝试从缓存获取
        cached_response = await cache_optimizer.get(cache_key)
        if cached_response:
            logger.debug("Cache hit", path=path, cache_key=cache_key)
            return Response(
                content=cached_response["content"],
                status_code=cached_response["status_code"],
                headers=cached_response["headers"],
                media_type=cached_response["media_type"]
            )

        # 执行请求
        response = await call_next(request)

        # 缓存响应（仅缓存成功的响应）
        if response.status_code == 200:
            # 读取响应内容
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk

            # 创建缓存数据
            cache_data = {
                "content": response_body.decode(),
                "status_code": response.status_code,
                "headers": dict[str, Any](response.headers),
                "media_type": response.media_type
            }

            # 存储到缓存
            await cache_optimizer.set(cache_key, cache_data, ttl=self.cache_ttl)
            logger.debug("Response cached", path=path, cache_key=cache_key)

            # 重新创建响应（因为body_iterator已被消费）
            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict[str, Any](response.headers),
                media_type=response.media_type
            )

        return response


def setup_performance_middleware(app) -> None:
    """设置性能优化中间件"""

    # 1. 使用uvloop事件循环（性能提升）
    if asyncio.get_event_loop().__class__.__name__ != 'uvloop.Loop':
        try:
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            logger.info("uvloop已启用")
        except Exception as e:
            logger.warning("无法启用uvloop", error=str(e))

    # 2. 添加中间件（注意顺序）
    middleware = [
        # CORS中间件
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],  # 生产环境应该限制
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        ),
        # Gzip压缩中间件
        Middleware(
            GZipMiddleware,
            minimum_size=1000,
        ),
        # 性能监控中间件
        Middleware(
            PerformanceMiddleware,
            max_request_size=10 * 1024 * 1024,
        ),
        # 速率限制中间件
        Middleware(
            RateLimitMiddleware,
            requests_per_minute=60,
            burst=10,
        ),
        # 缓存中间件
        Middleware(
            CacheMiddleware,
            cache_ttl=300,
        ),
    ]

    # 应用中间件
    for m in middleware:
        app.add_middleware(m)

    logger.info("性能中间件已配置")


class ConnectionPoolManager:
    """连接池管理器"""

    def __init__(self):
        self.pools = {}

    async def create_pool(self, name: str, **kwargs):
        """创建连接池"""
        import aiohttp

        connector = aiohttp.TCPConnector(
            limit=kwargs.get("limit", 100),
            limit_per_host=kwargs.get("limit_per_host", 30),
            ttl_dns_cache=kwargs.get("ttl_dns_cache", 300),
            use_dns_cache=kwargs.get("use_dns_cache", True),
            keepalive_timeout=kwargs.get("keepalive_timeout", 30),
            enable_cleanup_closed=kwargs.get("enable_cleanup_closed", True),
        )

        timeout = aiohttp.ClientTimeout(
            total=kwargs.get("total_timeout", 30),
            connect=kwargs.get("connect_timeout", 10),
            sock_read=kwargs.get("read_timeout", 30),
        )

        session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            trust_env=kwargs.get("trust_env", True),
        )

        self.pools[name] = session
        logger.info(f"连接池已创建: {name}")

        return session

    async def get_pool(self, name: str):
        """获取连接池"""
        return self.pools.get(name)

    async def close_all(self):
        """关闭所有连接池"""
        for name, pool in self.pools.items():
            await pool.close()
            logger.info(f"连接池已关闭: {name}")


# 全局连接池管理器
pool_manager = ConnectionPoolManager()


# 性能优化装饰器
def async_lru_cache(maxsize: int = 128, ttl: int = 300):
    """异步LRU缓存装饰器"""
    def decorator(func: Callable):
        cache = {}
        cache_times = {}

        async def wrapper(*args, **kwargs):
            # 生成缓存键
            key = str(args) + str(sorted(kwargs.items()))
            current_time = time.time()

            # 检查缓存
            if key in cache:
                cached_time = cache_times[key]
                if current_time - cached_time < ttl:
                    return cache[key]
                else:
                    # 过期删除
                    del cache[key]
                    del cache_times[key]

            # 执行函数
            result = await func(*args, **kwargs)

            # 存储到缓存
            if len(cache) >= maxsize:
                # 删除最旧的项
                oldest_key = min(cache_times.keys(), key=cache_times.get)
                del cache[oldest_key]
                del cache_times[oldest_key]

            cache[key] = result
            cache_times[key] = current_time

            return result

        return wrapper
    return decorator


# 批处理装饰器
def batch_process(batch_size: int = 100, timeout: float = 1.0):
    """批处理装饰器"""
    def decorator(func: Callable):
        queue = asyncio.Queue()

        async def worker():
            batch = []
            last_process = time.time()

            while True:
                try:
                    # 获取项目
                    item = await asyncio.wait_for(queue.get(), timeout=timeout)
                    batch.append(item)

                    # 检查是否需要处理批次
                    if (len(batch) >= batch_size or
                        (batch and time.time() - last_process > timeout)):
                        await func(batch)
                        batch.clear()
                        last_process = time.time()

                except asyncio.TimeoutError:
                    # 超时处理剩余批次
                    if batch:
                        await func(batch)
                        batch.clear()
                        last_process = time.time()

        # 启动工作进程
        asyncio.create_task(worker())

        async def wrapper(*args, **kwargs):
            await queue.put((args, kwargs))

        return wrapper
    return decorator
