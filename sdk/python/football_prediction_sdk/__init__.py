#!/usr/bin/env python3
"""Football Prediction Python SDK
足球比赛结果预测系统 - 官方Python SDK.

Version: 1.0.0
Author: Claude Code
Description: 官方Python SDK，提供完整的API访问功能
"""

from .auth import AuthManager
from .client import FootballPredictionClient
from .exceptions import (
    AuthenticationError,
    BusinessError,
    FootballPredictionError,
    RateLimitError,
    SystemServiceError,
    ValidationError,
)
from .models import (
    Match,
    MatchListResponse,
    Prediction,
    PredictionRequest,
    PredictionResponse,
    Team,
    User,
    UserProfileResponse,
)
from .utils import retry_with_backoff, validate_request_data

__version__ = "1.0.0"
__author__ = "Claude Code"
__email__ = "support@football-prediction.com"
__url__ = "https://docs.football-prediction.com/sdk/python"

__all__ = [
    # 核心客户端
    "FootballPredictionClient",

    # 异常类
    "FootballPredictionError",
    "AuthenticationError",
    "ValidationError",
    "BusinessError",
    "SystemServiceError",
    "RateLimitError",

    # 数据模型
    "Prediction",
    "Match",
    "Team",
    "User",
    "PredictionRequest",
    "PredictionResponse",
    "MatchListResponse",
    "UserProfileResponse",

    # 工具类
    "AuthManager",
    "retry_with_backoff",
    "validate_request_data"
]

# SDK版本检查
import sys
import warnings


def check_python_version():
    """检查Python版本兼容性."""

def check_sdk_version():
    """检查SDK版本更新."""
    try:
        import requests
        response = requests.get(
            "https://pypi.org/pypi/football-prediction-sdk/json",
            timeout=5
        )
        if response.status_code == 200:
            latest_version = response.json()["info"]["version"]
            if latest_version != __version__:
                warnings.warn(
                    f"New SDK version available: {latest_version} (current: {__version__})",
                    UserWarning, stacklevel=2
                )
    except Exception:
        pass  # 忽略网络错误

# 初始化检查
check_python_version()
check_sdk_version()

# 模块级便捷函数
def create_client(api_key: str, base_url: str = "https://api.football-prediction.com/v1", **kwargs) -> FootballPredictionClient:
    """便捷函数：创建客户端实例.

    Args:
        api_key: API密钥
        base_url: API基础URL
        **kwargs: 其他配置参数

    Returns:
        FootballPredictionClient: 客户端实例

    Example:
        >>> client = create_client("your_api_key")
        >>> prediction = client.predictions.create(
        ...     match_id="match_123",
        ...     home_team="Team A",
        ...     away_team="Team B"
        ... )
    """
    return FootballPredictionClient(api_key=api_key, base_url=base_url, **kwargs)
