from .base import Subsystem, SubsystemManager, SystemFacade
from .facades import (
    AnalyticsFacade,
    DataCollectionFacade,
    MainSystemFacade,
    NotificationFacade,
    PredictionFacade,
)
from .factory import FacadeConfig, FacadeFactory

"""
门面模式模块
Facade Pattern Module

提供简化的接口来访问复杂的子系统.
Provides simplified interfaces to access complex subsystems.
"""

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
