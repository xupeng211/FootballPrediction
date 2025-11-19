"""API缓存中间件
API Cache Middleware.

为FastAPI应用提供自动缓存功能。
"""

import time
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ...cache.api_cache import ApiCacheConfig, get_api_cache


class CacheMiddleware(BaseHTTPMiddleware):
    """API缓存中间件."""

    def __init__(
        self,
        app,
        config: ApiCacheConfig | None = None,
        cacheable_methods: list[str] = None,
        cacheable_status_codes: list[int] = None,
        skip_cache_paths: list[str] = None
    ):
        super().__init__(app)
        self.api_cache = get_api_cache(config)
        self.cacheable_methods = cacheable_methods or ["GET"]
        self.cacheable_status_codes = cacheable_status_codes or [200, 201, 202]
        self.skip_cache_paths = skip_cache_paths or [
            "/health",
            "/metrics",
            "/cache",
            "/admin"
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 检查是否应该跳过缓存
        if self._should_skip_cache(request):
            return await call_next(request)

        # 生成缓存键
        cache_key = self._generate_cache_key(request)

        # 尝试从缓存获取响应
        cached_response = await self.api_cache.get(
            endpoint=cache_key,
            method=request.method,
            params=dict(request.query_params),
            headers=dict(request.headers),
            user_id=self._get_user_id(request)
        )

        if cached_response:
            return self._build_response_from_cache(cached_response)

        # 执行请求
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        # 缓存响应
        if self._should_cache_response(response):
            response_data = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response.body.decode('utf-8') if response.body else None,
                "process_time": process_time
            }

            await self.api_cache.set(
                endpoint=cache_key,
                value=response_data,
                method=request.method,
                params=dict(request.query_params),
                headers=dict(request.headers),
                user_id=self._get_user_id(request),
                ttl=self._calculate_ttl(request, response)
            )

        return response

    def _should_skip_cache(self, request: Request) -> bool:
        """检查是否应该跳过缓存."""
        # 检查请求方法
        if request.method not in self.cacheable_methods:
            return True

        # 检查路径
        for skip_path in self.skip_cache_paths:
            if request.url.path.startswith(skip_path):
                return True

        # 检查查询参数（跳过包含特殊参数的请求）
        skip_params = ["no_cache", "refresh", "bust"]
        for param in skip_params:
            if param in request.query_params:
                return True

        return False

    def _generate_cache_key(self, request: Request) -> str:
        """生成缓存键."""
        return f"{request.method}:{request.url.path}"

    def _get_user_id(self, request: Request) -> str | None:
        """获取用户ID."""
        # 从请求状态或头部获取用户信息
        if hasattr(request.state, 'user_id'):
            return request.state.user_id

        if 'x-user-id' in request.headers:
            return request.headers['x-user-id']

        return None

    def _should_cache_response(self, response: Response) -> bool:
        """检查是否应该缓存响应."""
        # 检查状态码
        if response.status_code not in self.cacheable_status_codes:
            return False

        # 检查响应头
        if 'cache-control' in response.headers:
            cache_control = response.headers['cache-control'].lower()
            if 'no-cache' in cache_control or 'private' in cache_control:
                return False

        # 检查响应大小
        if response.body and len(response.body) > 1024 * 1024:  # 1MB
            return False

        return True

    def _calculate_ttl(self, request: Request, response: Response) -> int:
        """计算TTL."""
        # 从响应头获取缓存控制信息
        if 'cache-control' in response.headers:
            cache_control = response.headers['cache-control']
            if 'max-age=' in cache_control:
                try:
                    max_age = int(cache_control.split('max-age=')[1].split(',')[0])
                    return max_age
                except (ValueError, IndexError):
                    pass

        # 根据内容类型设置默认TTL
        content_type = response.headers.get('content-type', '').lower()

        if 'application/json' in content_type:
            return 300  # 5分钟
        elif 'text/html' in content_type:
            return 600  # 10分钟
        elif 'image' in content_type:
            return 3600  # 1小时
        else:
            return 180  # 3分钟

    def _build_response_from_cache(self, cached_data: dict) -> Response:
        """从缓存数据构建响应."""
        response = Response(
            content=cached_data.get('body'),
            status_code=cached_data.get('status_code', 200),
            headers=cached_data.get('headers', {})
        )

        # 添加缓存标识头
        response.headers['X-Cache'] = 'HIT'
        response.headers['X-Cache-TTL'] = str(cached_data.get('process_time', 0))

        return response


def add_cache_middleware(app, config: ApiCacheConfig | None = None) -> None:
    """为FastAPI应用添加缓存中间件."""
    app.add_middleware(CacheMiddleware, config=config)


# 导出公共接口
__all__ = [
    "CacheMiddleware",
    "add_cache_middleware"
]

__version__ = "1.0.0"
__description__ = "FastAPI缓存中间件"
