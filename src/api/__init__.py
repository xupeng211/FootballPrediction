"""
API模块

提供API路由和端点，以及外部API客户端
"""

from .health import router as health_router
from .fotmob_client import FotMobAPIClient, fetch_match_data

__all__ = ["health_router", "FotMobAPIClient", "fetch_match_data"]
