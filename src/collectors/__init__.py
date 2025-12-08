from typing import Optional

"""数据收集器模块
专注于FotMob数据源收集足球相关数据，包含反爬对抗技术.
已废弃：base_collector, football_data_collector, match_collector 等第三方数据源代码已归档至 _deprecated_sources/
"""

# 🎯 核心FotMob采集器
from .fotmob_api_collector import FotMobAPICollector
from .enhanced_fotmob_collector import EnhancedFotMobCollector, create_fotmob_collector

# 通用工具类
from .rate_limiter import RateLimiter
from .user_agent import UserAgentManager
from .proxy_pool import ProxyPool
from .http_client_factory import HttpClientFactory

__all__ = [
    # 🎯 核心FotMob采集器
    "FotMobAPICollector",
    "EnhancedFotMobCollector",
    "create_fotmob_collector",
    # 通用工具类
    "RateLimiter",
    "UserAgentManager",
    "ProxyPool",
    "HttpClientFactory",
]
