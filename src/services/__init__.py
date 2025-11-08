from .base_unified import BaseService

# from .base_unified import SimpleService  # 未使用
from .content_analysis import ContentAnalysisService
from .data_processing import DataProcessingService
from .manager import ServiceManager, service_manager
from .prediction_service import (
    PredictionResult,
    PredictionService,
    get_prediction_service,
    predict_match,
    predict_match_async,
)
from .user_profile import UserProfileService

"""
足球预测系统业务服务模块

提供系统业务逻辑服务,包括:
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
    "PredictionService",
    # 预测相关
    "PredictionResult",
    "get_prediction_service",
    "predict_match",
    "predict_match_async",
    # 服务管理
    "ServiceManager",
    "service_manager",
]
