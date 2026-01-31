"""
API模块

提供API路由和端点，以及外部API客户端
"""

from .fotmob_client import FotMobAPIClient, fetch_match_data
from .health import router as health_router

__all__ = ["FotMobAPIClient", "fetch_match_data", "health_router"]
