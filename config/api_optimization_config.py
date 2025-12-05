"""
API路由优化配置
生成时间: 2025-10-26 20:57:22
"""

# 路由优化配置
ROUTE_OPTIMIZATION = {
    "enable_caching": True,
    "cache_ttl": 300,  # 5分钟
    "rate_limiting": {"enabled": True, "default_limit": 100, "burst_limit": 200},
    "response_compression": {"enabled": True, "min_length": 1024},
    "connection_pooling": {
        "enabled": True,
        "max_connections": 100,
        "min_connections": 10,
    },
}

# 性能优化建议
PERFORMANCE_TIPS = [
    "使用数据库连接池减少连接开销",
    "实现请求缓存减少重复计算",
    "使用异步处理提高并发能力",
    "优化数据库查询避免N+1问题",
    "实现分页减少数据传输量",
    "使用CDN加速静态资源",
]
