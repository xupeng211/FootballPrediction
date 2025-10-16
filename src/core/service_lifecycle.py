from typing import Any

"""
服务生命周期管理
Service Lifecycle Management

管理服务的创建,初始化,运行和销毁.
Manages service creation, initialization, running and destruction.
"""
import asyncio
import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..core.exceptions import ServiceLifecycleError

logger = logging.getLogger(__name__)


class ServiceStatus(Enum)
:
    """服务状态"""
    INACTIVE = "inactive"
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ServiceInfo:
    """服务信息"""
    service: "Service"
    status: ServiceStatus = ServiceStatus.INACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    error: str | None = None
    health_status: bool = False


class Service(ABC)
:
    """服务基类"""

    @abstractmethod
    async def initialize(self) -> None:
        """初始化服务"""
        pass

    @abstractmethod
    async def start(self) -> None:
        """启动服务"""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """停止服务"""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """清理资源"""
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """健康检查"""
        pass


class ServiceLifecycleManager:
    """
    服务生命周期管理器
    """

    def __init__(self) -> None:
        self._services: dict[str, ServiceInfo] = {}
        self._start_order: list[str] = []
        self._stop_order: list[str] = []
        self._lock = threading.RLock()
        self._shutdown_event = asyncio.Event()
        self._monitor_task: asyncio.Task | None = None
