"""
统一的基础服务类

合并了原来两个基础服务类的功能，提供完整的服务基础设施。
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime

from src.database.connection_mod import DatabaseManager
from src.core import logger


class BaseService(ABC):
    """
    统一的基础服务类

    提供以下功能：
    - 服务生命周期管理（初始化、启动、停止、关闭）
    - 数据库会话管理（同步和异步）
    - 日志记录
    - 操作追踪
    """

    def __init__(
        self, name: Optional[str] = None, db_manager: Optional[DatabaseManager] = None
    ):
        """
        初始化基础服务

        Args:
            name: 服务名称，默认使用类名
            db_manager: 数据库管理器实例，可选
        """
        self.name = name or self.__class__.__name__
        self.db_manager = db_manager or DatabaseManager()
        self.logger = logging.getLogger(self.name)
        self._running = False
        self._initialized = False
        self._created_at = datetime.now()

    # ========================================
    # 生命周期管理方法
    # ========================================

    async def initialize(self) -> bool:
        """
        初始化服务

        子类可以重写此方法来实现自定义初始化逻辑

        Returns:
            bool: 初始化是否成功
        """
        if self._initialized:
            self.logger.warning(f"服务 {self.name} 已经初始化")
            return True

        self.logger.info(f"正在初始化服务: {self.name}")
        try:
            # 执行自定义初始化
            success = await self._on_initialize()
            self._initialized = success
            if success:
                self.logger.info(f"服务 {self.name} 初始化成功")
            else:
                self.logger.error(f"服务 {self.name} 初始化失败")
            return success
        except Exception as e:
            self.logger.error(f"服务 {self.name} 初始化异常: {e}")
            return False

    async def shutdown(self) -> None:
        """
        关闭服务

        子类可以重写此方法来实现自定义清理逻辑
        """
        if not self._initialized:
            return

        self.logger.info(f"正在关闭服务: {self.name}")
        try:
            # 停止服务
            await self.stop()
            # 执行自定义清理
            await self._on_shutdown()
            self._initialized = False
            self.logger.info(f"服务 {self.name} 已关闭")
        except Exception as e:
            self.logger.error(f"服务 {self.name} 关闭异常: {e}")

    def start(self) -> bool:
        """
        启动服务

        Returns:
            bool: 启动是否成功
        """
        if not self._initialized:
            self.logger.error(f"服务 {self.name} 未初始化，无法启动")
            return False

        if self._running:
            self.logger.warning(f"服务 {self.name} 已在运行")
            return True

        self.logger.info(f"正在启动服务: {self.name}")
        try:
            # 执行自定义启动逻辑
            success = self._on_start()
            self._running = success
            if success:
                self.logger.info(f"服务 {self.name} 启动成功")
            else:
                self.logger.error(f"服务 {self.name} 启动失败")
            return success
        except Exception as e:
            self.logger.error(f"服务 {self.name} 启动异常: {e}")
            return False

    async def stop(self) -> None:
        """停止服务"""
        if not self._running:
            return

        self.logger.info(f"正在停止服务: {self.name}")
        try:
            # 执行自定义停止逻辑
            await self._on_stop()
            self._running = False
            self.logger.info(f"服务 {self.name} 已停止")
        except Exception as e:
            self.logger.error(f"服务 {self.name} 停止异常: {e}")

    # ========================================
    # 数据库会话管理
    # ========================================

    async def get_async_session(self):
        """获取异步数据库会话"""
        return self.db_manager.get_async_session()

    def get_sync_session(self):
        """获取同步数据库会话"""
        return self.db_manager.get_session()

    # ========================================
    # 日志和操作追踪
    # ========================================

    def log_operation(
        self,
        operation: str,
        details: Optional[Dict[str, Any]] = None,
        level: str = "info",
    ) -> None:
        """
        记录操作日志

        Args:
            operation: 操作名称
            details: 操作详情
            level: 日志级别 (info, warning, error)
        """
        message = f"Operation: {operation}"
        if details:
            message += f", Details: {details}"

        getattr(self.logger, level)(message)

    def log_error(
        self, operation: str, error: Exception, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        记录错误日志

        Args:
            operation: 操作名称
            error: 错误对象
            details: 额外详情
        """
        self.logger.error(
            f"Error in {operation}: {str(error)}",
            exc_info=True,
            extra={"details": details} if details else {},
        )

    # ========================================
    # 服务状态和健康检查
    # ========================================

    def get_status(self) -> str:
        """获取服务状态"""
        if not self._initialized:
            return "uninitialized"
        elif self._running:
            return "running"
        else:
            return "stopped"

    def is_healthy(self) -> bool:
        """
        检查服务健康状态

        子类可以重写此方法来实现自定义健康检查

        Returns:
            bool: 服务是否健康
        """
        return self._initialized and self._running

    async def health_check(self) -> Dict[str, Any]:
        """
        获取详细的健康检查信息

        Returns:
            Dict: 包含健康状态的详细信息
        """
        return {
            "service": self.name,
            "status": self.get_status(),
            "healthy": self.is_healthy(),
            "initialized": self._initialized,
            "running": self._running,
            "uptime": str(datetime.now() - self._created_at),
            "database_connected": self._check_database_connection(),
        }

    def _check_database_connection(self) -> bool:
        """检查数据库连接"""
        try:
            with self.db_manager.get_session() as session:
                session.execute("SELECT 1")  # type: ignore
            return True
        except Exception:
            return False

    # ========================================
    # 可重写的生命周期钩子方法
    # ========================================

    async def _on_initialize(self) -> bool:
        """
        初始化钩子方法

        子类重写此方法来实现自定义初始化逻辑

        Returns:
            bool: 初始化是否成功
        """
        return True

    async def _on_shutdown(self) -> None:
        """
        关闭钩子方法

        子类重写此方法来实现自定义清理逻辑
        """
        pass

    def _on_start(self) -> bool:
        """
        启动钩子方法

        子类重写此方法来实现自定义启动逻辑

        Returns:
            bool: 启动是否成功
        """
        return True

    async def _on_stop(self) -> None:
        """
        停止钩子方法

        子类重写此方法来实现自定义停止逻辑
        """
        pass

    # ========================================
    # 抽象方法（强制子类实现）
    # ========================================

    @abstractmethod
    async def _get_service_info(self) -> Dict[str, Any]:
        """
        获取服务信息

        子类必须实现此方法，返回服务的基本信息

        Returns:
            Dict: 服务信息
        """
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "description": "Service description not provided",
            "version": "1.0.0",
        }


class SimpleService(BaseService):
    """
    简单服务实现

    适用于不需要复杂初始化逻辑的服务
    """

    async def _get_service_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        return {
            "name": self.name,
            "type": self.__class__.__name__,
            "description": "Simple service implementation",
            "version": "1.0.0",
        }
