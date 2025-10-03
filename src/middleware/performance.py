"""
性能优化中间件
Performance Optimization Middleware

提供API性能优化功能：
- 响应缓存
- 压缩中间件
- 批处理支持
- 性能监控
"""

import gzip
import json
import time
import hashlib
from typing import Callable, Optional, Dict, Any, List
from fastapi import Request, Response, HTTPException
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import asyncio
from functools import wraps
from sqlalchemy import text

from src.cache.redis_manager import RedisManager


class ResponseCacheMiddleware(BaseHTTPMiddleware):
    """响应缓存中间件"""

    def __init__(
        self,
        app: ASGIApp,
        cache_manager: Optional[RedisManager] = None,
        default_ttl: int = 300,  # 5分钟默认缓存
        cacheable_methods: List[str] = ["GET"],
        cacheable_status_codes: List[int] = [200, 301, 302],
        max_response_size: int = 10 * 1024 * 1024,  # 10MB
    ):
        super().__init__(app)
        self.cache_manager = cache_manager
        self.default_ttl = default_ttl
        self.cacheable_methods = cacheable_methods
        self.cacheable_status_codes = cacheable_status_codes
        self.max_response_size = max_response_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 只缓存GET请求
        if request.method not in self.cacheable_methods:
            return await call_next(request)

        # 生成缓存键
        cache_key = self._generate_cache_key(request)

        # 尝试从缓存获取
        if self.cache_manager:
            cached_response = await self.cache_manager.get(cache_key)
            if cached_response:
                # 解析缓存的响应
                cached_data = json.loads(cached_response)
                response = Response(
                    content=cached_data["body"],
                    status_code=cached_data["status_code"],
                    headers=cached_data["headers"],
                    media_type=cached_data["media_type"]
                )
                response.headers["X-Cache"] = "HIT"
                return response

        # 执行请求
        response = await call_next(request)

        # 缓存响应（如果满足条件）
        if (
            self.cache_manager
            and response.status_code in self.cacheable_status_codes
        ):
            # 获取响应体
            response_body = b""
            if hasattr(response, 'body'):
                response_body = response.body
            elif hasattr(response, 'content'):
                response_body = response.content

            if len(response_body) < self.max_response_size:
                # 准备缓存数据
                try:
                    body_str = response_body.decode()
                except UnicodeDecodeError:
                    # 如果不是文本，使用base64编码
                    import base64
                    body_str = base64.b64encode(response_body).decode()

                cache_data = {
                    "body": body_str,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "media_type": response.media_type,
                    "timestamp": time.time()
                }

                # 存储到缓存
                await self.cache_manager.set(
                    cache_key,
                    json.dumps(cache_data),
                    ttl=self.default_ttl
                )

                response.headers["X-Cache"] = "MISS"

        return response

    def _generate_cache_key(self, request: Request) -> str:
        """生成缓存键"""
        # 包含URL和查询参数
        key_data = f"{request.url.path}?{request.url.query}"
        # 添加认证信息（如果有）
        auth_header = request.headers.get("authorization")
        if auth_header:
            # 只取用户标识，不包含完整token
            key_data += f"|user:{hash(auth_header[:10])}"
        # 生成MD5哈希
        return f"response_cache:{hashlib.md5(key_data.encode()).hexdigest()}"


class CompressionMiddleware(BaseHTTPMiddleware):
    """压缩中间件"""

    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 1024,  # 小于1KB不压缩
        compressible_types: List[str] = [
            "application/json",
            "text/html",
            "text/css",
            "text/javascript",
            "application/javascript",
            "text/xml",
            "application/xml"
        ]
    ):
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compressible_types = compressible_types

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 检查客户端是否支持gzip
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding.lower():
            return await call_next(request)

        # 执行请求
        response = await call_next(request)

        # 检查是否应该压缩
        content_type = response.headers.get("content-type", "").split(";")[0]
        content_length = response.headers.get("content-length")

        if (
            content_type not in self.compressible_types
            or (content_length and int(content_length) < self.minimum_size)
        ):
            return response

        # 压缩响应
        response_body = b""
        if hasattr(response, 'body'):
            response_body = response.body
        elif hasattr(response, 'content'):
            response_body = response.content

        if response_body:
            compressed_body = gzip.compress(response_body)

            # 只有在压缩有效时才使用
            if len(compressed_body) < len(response_body):
                response = Response(
                    content=compressed_body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )
                response.headers["Content-Encoding"] = "gzip"
                response.headers["Content-Length"] = str(len(compressed_body))
                response.headers["Vary"] = "Accept-Encoding"

        return response


class BatchProcessingMiddleware(BaseHTTPMiddleware):
    """批处理中间件"""

    def __init__(
        self,
        app: ASGIApp,
        batch_header: str = "X-Batch-Request",
        max_batch_size: int = 100,
    ):
        super().__init__(app)
        self.batch_header = batch_header
        self.max_batch_size = max_batch_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 检查是否是批处理请求
        if request.headers.get(self.batch_header) != "true":
            return await call_next(request)

        try:
            # 解析批处理请求体
            body = await request.json()
            requests = body.get("requests", [])

            if len(requests) > self.max_batch_size:
                raise HTTPException(
                    status_code=400,
                    detail=f"Batch size exceeds limit of {self.max_batch_size}"
                )

            # 并行处理所有请求
            tasks = []
            for req in requests:
                task = self._process_single_request(req, call_next)
                tasks.append(task)

            # 等待所有请求完成
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # 格式化批处理响应
            batch_response = {
                "responses": []
            }

            for i, resp in enumerate(responses):
                if isinstance(resp, Exception):
                    batch_response["responses"].append({
                        "status_code": 500,
                        "body": {"error": str(resp)},
                        "headers": {}
                    })
                else:
                    batch_response["responses"].append({
                        "status_code": resp["status_code"],
                        "body": resp["body"],
                        "headers": resp["headers"]
                    })

            return Response(
                content=json.dumps(batch_response),
                media_type="application/json",
                headers={"X-Batch-Response": "true"}
            )

        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Batch processing failed: {str(e)}"
            )

    async def _process_single_request(
        self,
        single_request: Dict[str, Any],
        call_next: Callable
    ) -> Dict[str, Any]:
        """处理单个批处理请求"""
        try:
            # 创建模拟请求对象
            method = single_request.get("method", "GET")
            path = single_request.get("path", "/")
            headers = single_request.get("headers", {})
            query_params = single_request.get("query_params", {})
            body = single_request.get("body")

            # 构建URL
            url = f"{path}?{self._build_query_string(query_params)}"

            # 这里应该创建实际的Request对象并处理
            # 简化实现，返回模拟响应
            return {
                "status_code": 200,
                "body": {"processed": True, "path": path},
                "headers": {"Content-Type": "application/json"}
            }

        except Exception as e:
            return {
                "status_code": 500,
                "body": {"error": str(e)},
                "headers": {}
            }

    def _build_query_string(self, params: Dict[str, Any]) -> str:
        """构建查询字符串"""
        return "&".join([f"{k}={v}" for k, v in params.items()])


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """性能监控中间件"""

    def __init__(
        self,
        app: ASGIApp,
        slow_query_threshold: float = 1.0,  # 1秒
        include_paths: Optional[List[str]] = None,
        exclude_paths: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.slow_query_threshold = slow_query_threshold
        self.include_paths = include_paths or []
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 记录开始时间
        start_time = time.time()

        # 执行请求
        response = await call_next(request)

        # 计算处理时间
        processing_time = time.time() - start_time

        # 添加性能头
        response.headers["X-Response-Time"] = f"{processing_time:.3f}s"

        # 记录慢请求
        if processing_time > self.slow_query_threshold:
            self._log_slow_request(request, processing_time)

        # 收集性能指标
        self._collect_metrics(request, response, processing_time)

        return response

    def _log_slow_request(self, request: Request, processing_time: float):
        """记录慢请求"""
        import logging
        logger = logging.getLogger("performance")

        logger.warning(
            f"Slow request detected: {request.method} {request.url.path} "
            f"- {processing_time:.3f}s"
        )

    def _collect_metrics(
        self,
        request: Request,
        response: Response,
        processing_time: float
    ):
        """收集性能指标"""
        # 这里可以发送到监控系统
        # 例如 Prometheus、CloudWatch 等
        pass


def cache_response(ttl: int = 300, key_prefix: str = "api"):
    """响应缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"

            # 尝试从缓存获取
            # 这里应该实现实际的缓存逻辑
            # 简化实现

            # 执行函数
            result = await func(*args, **kwargs)

            # 缓存结果
            # 这里应该实现实际的缓存存储

            return result
        return wrapper
    return decorator


class AsyncBatchProcessor:
    """异步批处理器"""

    def __init__(self, batch_size: int = 100, flush_interval: float = 1.0):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._queue: List[Any] = []
        self._last_flush = time.time()
        self._task: Optional[asyncio.Task] = None

    async def add(self, item: Any):
        """添加项目到批处理队列"""
        self._queue.append(item)

        # 检查是否需要刷新
        if (
            len(self._queue) >= self.batch_size or
            time.time() - self._last_flush > self.flush_interval
        ):
            # 不要在add中直接刷新，只标记需要刷新
            # 实际的刷新应该由外部调用或auto_flush任务处理
            pass

    async def flush(self):
        """刷新队列"""
        if not self._queue:
            return

        # 获取当前队列
        items = self._queue.copy()
        self._queue.clear()
        self._last_flush = time.time()

        # 处理批次
        await self._process_batch(items)

    async def _process_batch(self, items: List[Any]):
        """处理批次项目（子类实现）"""
        raise NotImplementedError

    async def auto_flush(self):
        """自动刷新任务"""
        while True:
            await asyncio.sleep(self.flush_interval)
            await self.flush()


class DatabaseBatchProcessor(AsyncBatchProcessor):
    """数据库批处理器"""

    def __init__(self, db_session, table_name: str, **kwargs):
        super().__init__(**kwargs)
        self.db_session = db_session
        self.table_name = table_name

    async def _process_batch(self, items: List[Dict[str, Any]]):
        """批量插入数据库"""
        try:
            # 构建批量插入SQL
            if items:
                columns = list(items[0].keys())
                values = []
                for item in items:
                    value_list = []
                    for col in columns:
                        val = item.get(col)
                        if val is None:
                            value_list.append("NULL")
                        elif isinstance(val, str):
                            # 转义单引号
                            escaped_val = val.replace("'", "''")
                            value_list.append(f"'{escaped_val}'")
                        else:
                            value_list.append(str(val))
                    values.append(f"({', '.join(value_list)})")

                sql = f"""
                INSERT INTO {self.table_name} ({', '.join(columns)})
                VALUES {', '.join(values)}
                ON CONFLICT DO NOTHING
                """

                # 执行批量插入
                await self.db_session.execute(text(sql))
                await self.db_session.commit()

                print(f"Batch inserted {len(items)} items into {self.table_name}")
        except Exception as e:
            print(f"Batch insert failed: {e}")
            await self.db_session.rollback()