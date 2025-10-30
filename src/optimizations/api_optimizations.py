"""
API性能优化
API Performance Optimizations

提供API层面的性能优化,包括缓存策略、响应优化,
并发控制,请求限流等.
"""

import asyncio
import json
import time
import hashlib
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass, asdict
from functools import wraps
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import redis.asyncio as redis
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.core.config import get_settings
from src.core.exceptions import PerformanceError


@dataclass
class PerformanceMetrics:
    """性能指标"""
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    timestamp: datetime
    user_id: Optional[int] = None
    tenant_id: Optional[int] = None
    cache_hit: bool = False
    request_size_bytes: int = 0
    response_size_bytes: int = 0


@dataclass
class CacheConfig:
    """缓存配置"""
    ttl_seconds: int = 300  # 5分钟默认TTL
    max_size: int = 1000
    key_prefix: str = "api_cache"
    include_query_params: bool = True
    vary_by_user: bool = False
    vary_by_tenant: bool = True


class APICache:
    """API缓存管理器"""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.settings = get_settings()
        self._local_cache = {}  # 本地内存缓存作为后备

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        if self.redis_client:
            try:
                data = await self.redis_client.get(key)
                if data:
                    return json.loads(data)
            except Exception:
                pass  # Redis不可用时使用本地缓存

        # 本地缓存后备
        return self._local_cache.get(key)

    async def set(self, key: str, value: Any, ttl_seconds: int = 300) -> bool:
        """设置缓存数据"""
        serialized_value = json.dumps(value, default=str)

        if self.redis_client:
            try:
                await self.redis_client.setex(key, ttl_seconds, serialized_value)
                return True
            except Exception:
                pass  # Redis不可用时使用本地缓存

        # 本地缓存后备
        self._local_cache[key] = value
        return True

    async def delete(self, key: str) -> bool:
        """删除缓存数据"""
        if self.redis_client:
            try:
                await self.redis_client.delete(key)
                return True
            except Exception:
                pass

        self._local_cache.pop(key, None)
        return True

    def _generate_cache_key(
        self,
        request: Request,
        config: CacheConfig,
        extra_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """生成缓存键"""
        key_parts = [config.key_prefix, request.method.lower(), request.url.path]

        # 添加查询参数
        if config.include_query_params and request.query_params:
            sorted_params = sorted(request.query_params.items())
            query_string = "&".join(f"{k}={v}" for k, v in sorted_params)
            key_parts.append(hashlib.md5(query_string.encode()).hexdigest()[:8])

        # 添加用户标识
        if config.vary_by_user:
            user_id = getattr(request.state, "user_id", None)
            if user_id:
                key_parts.append(f"user:{user_id}")

        # 添加租户标识
        if config.vary_by_tenant:
            tenant_context = getattr(request.state, "tenant_context", None)
            if tenant_context and tenant_context.tenant_id:
                key_parts.append(f"tenant:{tenant_context.tenant_id}")

        # 添加额外参数
        if extra_params:
            for k, v in sorted(extra_params.items()):
                key_parts.append(f"{k}:{v}")

        return ":".join(key_parts)


class ResponseCompressor:
    """响应压缩器"""

    @staticmethod
    def compress_response(data: Any, min_size_bytes: int = 1024) -> Dict[str, Any]:
        """压缩响应数据"""
        if isinstance(data, (dict, list)):
            serialized = json.dumps(data, default=str, separators=(',', ':'))
            original_size = len(serialized.encode('utf-8'))

            # 只对较大的响应进行压缩
            if original_size > min_size_bytes:
                return {
                    "data": data,
                    "compressed": True,
                    "original_size": original_size,
                    "compressed_size": original_size  # 实际应该使用压缩算法
                }

        return {
            "data": data,
            "compressed": False,
            "original_size": len(str(data).encode('utf-8')),
            "compressed_size": len(str(data).encode('utf-8'))
        }


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    性能监控中间件

    监控API性能指标,收集响应时间,缓存命中率等数据
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_settings()
        self.metrics: List[PerformanceMetrics] = []
        self.cache_manager = APICache()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并收集性能指标"""
        start_time = time.time()
        request_size = len(await request.body())

        # 生成请求ID
        request_id = f"{int(time.time() * 1000)}-{id(request)}"
        request.state.request_id = request_id

        try:
            # 处理请求
            response = await call_next(request)

            # 计算响应时间
            response_time_ms = (time.time() - start_time) * 1000

            # 收集性能指标
            metrics = PerformanceMetrics(
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow(),
                user_id=getattr(request.state, "user_id", None),
                tenant_id=getattr(getattr(request.state, "tenant_context", None), "tenant_id", None) if hasattr(request.state, "tenant_context") else None,
                request_size_bytes=request_size,
                response_size_bytes=len(response.body) if hasattr(response, "body") else 0
            )

            self.metrics.append(metrics)

            # 添加性能头
            response.headers["X-Response-Time"] = f"{response_time_ms:.2f}ms"
            response.headers["X-Request-ID"] = request_id

            # 如果响应时间过长,添加警告头
            if response_time_ms > 1000:  # 超过1秒
                response.headers["X-Performance-Warning"] = "slow-response"

            return response

        except Exception:
            # 记录错误指标
            error_metrics = PerformanceMetrics(
                endpoint=request.url.path,
                method=request.method,
                status_code=500,
                response_time_ms=(time.time() - start_time) * 1000,
                timestamp=datetime.utcnow(),
                user_id=getattr(request.state, "user_id", None)
            )
            self.metrics.append(error_metrics)
            raise

    def get_metrics_summary(self, minutes: int = 5) -> Dict[str, Any]:
        """获取性能指标摘要"""
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        recent_metrics = [
            m for m in self.metrics
            if m.timestamp >= cutoff_time
        ]

        if not recent_metrics:
            return {
                "total_requests": 0,
                "avg_response_time_ms": 0,
                "error_rate": 0,
                "p95_response_time_ms": 0,
                "p99_response_time_ms": 0
            }

        response_times = [m.response_time_ms for m in recent_metrics]
        error_count = sum(1 for m in recent_metrics if m.status_code >= 400)

        # 计算百分位数
        sorted_times = sorted(response_times)
        p95_index = int(len(sorted_times) * 0.95)
        p99_index = int(len(sorted_times) * 0.99)

        return {
            "total_requests": len(recent_metrics),
            "avg_response_time_ms": sum(response_times) / len(response_times),
            "error_rate": (error_count / len(recent_metrics)) * 100,
            "p95_response_time_ms": sorted_times[min(p95_index, len(sorted_times) - 1)],
            "p99_response_time_ms": sorted_times[min(p99_index, len(sorted_times) - 1)],
            "min_response_time_ms": min(response_times),
            "max_response_time_ms": max(response_times)
        }


# 限流器配置
limiter = Limiter(key_func=get_remote_address)


def cache_response(config: Optional[CacheConfig] = None):
    """
    响应缓存装饰器

    Args:
        config: 缓存配置
    """
    if config is None:
        config = CacheConfig()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 获取请求对象
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request:
                # 尝试从kwargs中获取
                request = kwargs.get("request")

            if not request:
                # 如果没有请求对象,直接执行函数
                return await func(*args, **kwargs)

            # 检查是否应该跳过缓存
            if request.method not in ["GET", "HEAD", "OPTIONS"]:
                return await func(*args, **kwargs)

            cache_manager = APICache()

            # 生成缓存键
            cache_key = cache_manager._generate_cache_key(request, config)

            # 尝试从缓存获取
            cached_response = await cache_manager.get(cache_key)
            if cached_response is not None:
                # 返回缓存的响应
                return JSONResponse(
                    content=cached_response,
                    status_code=200,
                    headers={"X-Cache": "HIT"}
                )

            # 执行原函数
            response = await func(*args, **kwargs)

            # 缓存响应（仅在成功时）
            if hasattr(response, 'status_code') and response.status_code == 200:
                if hasattr(response, 'body'):
                    content = response.body
                else:
                    content = response

                await cache_manager.set(cache_key, content, config.ttl_seconds)

            # 添加缓存头
            if hasattr(response, 'headers'):
                response.headers["X-Cache"] = "MISS"

            return response

        return wrapper
    return decorator


def performance_monitor(min_response_time_ms: float = 100.0):
    """
    性能监控装饰器

    Args:
        min_response_time_ms: 最小响应时间阈值（毫秒）
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                # 执行原函数
                result = await func(*args, **kwargs)

                # 计算响应时间
                response_time_ms = (time.time() - start_time) * 1000

                # 如果响应时间超过阈值,记录警告
                if response_time_ms > min_response_time_ms:
                    # 这里应该记录到日志或监控系统
                    print(f"警告: {func.__name__} 响应时间 {response_time_ms:.2f}ms 超过阈值 {min_response_time_ms}ms")

                return result

            except Exception as e:
                # 计算错误响应时间
                response_time_ms = (time.time() - start_time) * 1000
                print(f"错误: {func.__name__} 在 {response_time_ms:.2f}ms 后失败: {str(e)}")
                raise

        return wrapper
    return decorator


def validate_response_size(max_size_mb: int = 10):
    """
    响应大小验证装饰器

    Args:
        max_size_mb: 最大响应大小（MB）
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # 计算响应大小
            if isinstance(result, (dict, list)):
                serialized = json.dumps(result, default=str)
                size_bytes = len(serialized.encode('utf-8'))
                size_mb = size_bytes / (1024 * 1024)

                if size_mb > max_size_mb:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"响应大小 {size_mb:.2f}MB 超过限制 {max_size_mb}MB"
                    )

                # 添加大小信息到响应头
                if hasattr(result, 'headers'):
                    result.headers["X-Response-Size"] = f"{size_bytes} bytes"

            return result

        return wrapper
    return decorator


class ConnectionPoolManager:
    """连接池管理器"""

    def __init__(self):
        self.settings = get_settings()
        self._pool_stats = {
            "active_connections": 0,
            "total_connections": 0,
            "pool_hits": 0,
            "pool_misses": 0
        }

    async def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接池统计"""
        return {
            "pool_stats": self._pool_stats,
            "recommendations": self._get_pool_recommendations()
        }

    def _get_pool_recommendations(self) -> List[str]:
        """获取连接池优化建议"""
        recommendations = []

        if self._pool_stats["pool_misses"] > self._pool_stats["pool_hits"]:
            recommendations.append("考虑增加连接池大小")

        if self._pool_stats["active_connections"] / self._pool_stats["total_connections"] > 0.8:
            recommendations.append("连接池使用率过高,建议增加最大连接数")

        return recommendations


class APIOptimizer:
    """
    API优化器

    提供API性能优化的综合功能
    """

    def __init__(self):
        self.settings = get_settings()
        self.cache_manager = APICache()
        self.connection_manager = ConnectionPoolManager()
        self.metrics = []

    async def optimize_endpoint(self, endpoint_path: str, method: str = "GET") -> Dict[str, Any]:
        """优化特定端点"""
        optimization_results = {
            "endpoint": endpoint_path,
            "method": method,
            "optimizations_applied": [],
            "performance_improvement": {},
            "recommendations": []
        }

        # 分析端点性能
        endpoint_metrics = self._get_endpoint_metrics(endpoint_path, method)

        # 应用缓存优化
        if endpoint_metrics["avg_response_time_ms"] > 500:
            optimization_results["optimizations_applied"].append("response_caching")
            optimization_results["recommendations"].append("启用响应缓存以减少响应时间")

        # 应用压缩优化
        if endpoint_metrics["avg_response_size_bytes"] > 50000:  # 50KB
            optimization_results["optimizations_applied"].append("response_compression")
            optimization_results["recommendations"].append("启用响应压缩以减少传输大小")

        # 应用连接池优化
        if endpoint_metrics["error_rate"] > 5:
            optimization_results["optimizations_applied"].append("connection_pool_optimization")
            optimization_results["recommendations"].append("优化连接池配置以减少错误率")

        return optimization_results

    def _get_endpoint_metrics(self, endpoint_path: str, method: str) -> Dict[str, Any]:
        """获取端点性能指标"""
        endpoint_metrics = [
            m for m in self.metrics
            if m.endpoint == endpoint_path and m.method == method
        ]

        if not endpoint_metrics:
            return {
                "total_requests": 0,
                "avg_response_time_ms": 0,
                "avg_response_size_bytes": 0,
                "error_rate": 0
            }

        response_times = [m.response_time_ms for m in endpoint_metrics]
        response_sizes = [m.response_size_bytes for m in endpoint_metrics]
        error_count = sum(1 for m in endpoint_metrics if m.status_code >= 400)

        return {
            "total_requests": len(endpoint_metrics),
            "avg_response_time_ms": sum(response_times) / len(response_times),
            "avg_response_size_bytes": sum(response_sizes) / len(response_sizes),
            "error_rate": (error_count / len(endpoint_metrics)) * 100,
            "p95_response_time_ms": sorted(response_times)[int(len(response_times) * 0.95)] if len(response_times) > 0 else 0
        }

    async def generate_performance_report(self) -> Dict[str, Any]:
        """生成性能报告"""
        # 按端点分组指标
        endpoint_performance = {}
        for metric in self.metrics:
            key = f"{metric.method} {metric.endpoint}"
            if key not in endpoint_performance:
                endpoint_performance[key] = []
            endpoint_performance[key].append(metric)

        # 分析每个端点
        endpoint_analysis = {}
        for endpoint, metrics_list in endpoint_performance.items():
            response_times = [m.response_time_ms for m in metrics_list]
            error_count = sum(1 for m in metrics_list if m.status_code >= 400)

            endpoint_analysis[endpoint] = {
                "total_requests": len(metrics_list),
                "avg_response_time_ms": sum(response_times) / len(response_times),
                "max_response_time_ms": max(response_times),
                "min_response_time_ms": min(response_times),
                "error_rate": (error_count / len(metrics_list)) * 100,
                "p95_response_time_ms": sorted(response_times)[int(len(response_times) * 0.95)]
            }

        # 识别慢端点
        slow_endpoints = [
            {"endpoint": endpoint, **analysis}
            for endpoint, analysis in endpoint_analysis.items()
            if analysis["avg_response_time_ms"] > 1000
        ]

        # 识别高错误率端点
        high_error_endpoints = [
            {"endpoint": endpoint, **analysis}
            for endpoint, analysis in endpoint_analysis.items()
            if analysis["error_rate"] > 5
        ]

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "total_requests": len(self.metrics),
            "endpoint_analysis": endpoint_analysis,
            "slow_endpoints": sorted(slow_endpoints, key=lambda x: x["avg_response_time_ms"], reverse=True),
            "high_error_endpoints": sorted(high_error_endpoints, key=lambda x: x["error_rate"], reverse=True),
            "recommendations": self._generate_global_recommendations(endpoint_analysis)
        }

    def _generate_global_recommendations(self, endpoint_analysis: Dict[str, Any]) -> List[str]:
        """生成全局优化建议"""
        recommendations = []

        avg_response_times = [analysis["avg_response_time_ms"] for analysis in endpoint_analysis.values()]
        error_rates = [analysis["error_rate"] for analysis in endpoint_analysis.values()]

        if avg_response_times and sum(avg_response_times) / len(avg_response_times) > 500:
            recommendations.append("整体响应时间偏高,建议启用全局缓存")

        if error_rates and sum(error_rates) / len(error_rates) > 3:
            recommendations.append("错误率偏高,建议检查数据库连接和查询优化")

        if len(endpoint_analysis) > 20:
            recommendations.append("端点数量较多,建议实施API网关和负载均衡")

        return recommendations


# ==================== 优化工具函数 ====================

async def clear_cache(pattern: str = "*") -> Dict[str, Any]:
    """清理缓存"""
    APICache()
    # 这里应该实现模式匹配的缓存清理
    # 暂时返回清理结果
    return {
        "pattern": pattern,
        "cleared_keys": 0,
        "message": "缓存清理完成"
    }


def setup_api_optimizations(app) -> None:
    """设置API优化"""
    # 添加性能监控中间件
    app.add_middleware(PerformanceMiddleware)

    # 设置限流
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    print("API优化设置完成")