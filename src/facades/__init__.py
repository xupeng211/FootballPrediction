"""
门面模式模块
Facade Pattern Module

提供简化的接口来访问复杂的子系统.
Provides simplified interfaces to access complex subsystems.
"""

from .base import Subsystem, SubsystemManager, SystemFacade

# 导入__init__相关类
# 模块暂未实现 - 自动修复
# 占位符
AnalyticsFacade = None
DataCollectionFacade = None
MainSystemFacade = None
NotificationFacade = None
PredictionFacade = None

from .factory import FacadeConfig, FacadeFactory

__all__ = [
"SystemFacade",
"Subsystem",
"SubsystemManager",
"MainSystemFacade",
"PredictionFacade",
"DataCollectionFacade",
"AnalyticsFacade",
"NotificationFacade",
"FacadeFactory",
"FacadeConfig",
]
