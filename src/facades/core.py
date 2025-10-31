"""
外观模式核心类模块
Facade Core Classes Module

提供外观模式的核心实现类.
"""

from .base import SubsystemManager, SystemFacade

__all__ = [
    "SubsystemManager",
    "SystemFacade"
]