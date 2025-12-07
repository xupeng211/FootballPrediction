"""
数据获取器模块
Data Fetchers Module

提供各种数据源的具体实现，所有获取器都继承自AbstractFetcher接口。

可用获取器:
- oddsportal: OddsPortal数据源
- 更多获取器待实现...

作者: Data Integration Team
创建时间: 2025-12-07
版本: 1.0.0
"""

from .oddsportal_fetcher import OddsPortalFetcher
from .fetcher_factory import FetcherFactory

# 导出所有公共接口
__all__ = [
    "OddsPortalFetcher",
    "FetcherFactory",
]