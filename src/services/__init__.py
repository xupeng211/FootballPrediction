"""
FootballPrediction 业务服务模块

提供足球预测系统核心业务逻辑服务，包括：
- 预测推理服务
- 可解释性分析服务
- 真实预测服务
"""

# 导入服务类
from .base_service import BaseService
from .service_manager import ServiceManager, service_manager

__all__ = [
    "BaseService",
    "ServiceManager",
    "service_manager",
]
