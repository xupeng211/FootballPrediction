"""
基础服务类

所有服务的基类，提供通用的功能。
"""

import logging
from abc import ABC
from typing import Any, Dict, Optional

from src.database.connection_mod import DatabaseManager


class BaseService(ABC):
    """服务基类 / Base Service Class"""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        初始化基础服务

        Args:
            db_manager: 数据库管理器实例
        """
        self.db_manager = db_manager or DatabaseManager()
        self.logger = logging.getLogger(self.__class__.__name__)

    async def get_async_session(self):
        """获取异步数据库会话"""
        return self.db_manager.get_async_session()

    def get_sync_session(self):
        """获取同步数据库会话"""
        return self.db_manager.get_session()

    def log_operation(self, operation: str, details: Optional[Dict[str, Any]] = None):
        """
        记录操作日志

        Args:
            operation: 操作名称
            details: 操作详情
        """
        self.logger.info(f"Operation: {operation}, Details: {details or {}}")
