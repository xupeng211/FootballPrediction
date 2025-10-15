from typing import Any, Dict, List, Optional, Union

"""
门面模式模块
Facade Pattern Module

提供简化的接口来访问复杂的子系统。
Provides simplified interfaces to access complex subsystems.
"""

from .base import SystemFacade, Subsystem, SubsystemManager
from .facades import (
    MainSystemFacade,
    PredictionFacade,
    DataCollectionFacade,
    AnalyticsFacade,
    NotificationFacade,
)
from .factory import FacadeFactory, FacadeConfig

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
