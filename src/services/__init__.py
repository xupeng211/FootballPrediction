"""
足球预测系统业务服务模块

提供系统业务逻辑服务，包括：
- 基础服务类和生命周期管理
- 内容分析服务
- 用户画像服务
- 数据处理服务
- 服务管理器
"""

# 核心基础服务
from .core import (
    ServiceConfig,
    ServiceMetrics,
    EnhancedBaseService,
    BaseService,
    AbstractBaseService,
)

# 生命周期管理
from .lifecycle import (
    ServiceLifecycleManager,
    lifecycle_manager,
)

# 具体服务
from .content_analysis import ContentAnalysisService
from .data_processing import DataProcessingService
from .user_profile import UserProfileService

# 服务管理器
from .manager import ServiceManager, service_manager

__all__ = [
    # 核心服务类
    "ServiceConfig",
    "ServiceMetrics",
    "EnhancedBaseService",
    "BaseService",
    "AbstractBaseService",
    # 生命周期管理
    "ServiceLifecycleManager",
    "lifecycle_manager",
    # 具体服务
    "ContentAnalysisService",
    "UserProfileService",
    "DataProcessingService",
    # 服务管理
    "ServiceManager",
    "service_manager",
]
