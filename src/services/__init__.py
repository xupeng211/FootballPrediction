from .base import BaseService
from .content_analysis import ContentAnalysisService
from .data_processing import DataProcessingService
from .manager import ServiceManager, service_manager
from .user_profile import UserProfileService

"""
足球预测系统业务服务模块

提供系统业务逻辑服务，包括：
- 内容分析服务
- 用户画像服务
- 数据处理服务
- 服务管理器
"""

__all__ = [
    # 基础服务
    "BaseService",
    # 具体服务
    "ContentAnalysisService",
    "UserProfileService",
    "DataProcessingService",
    # 服务管理
    "ServiceManager",
    "service_manager",
]
