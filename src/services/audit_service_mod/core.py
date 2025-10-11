"""
Core Audit Service

提供审计服务的核心功能和统一接口。
Provides core audit service functionality and unified interface.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime

from src.core.logging import get_logger
from src.database.connection_mod import DatabaseManager

from .data_sanitizer import DataSanitizer
from .severity_analyzer import SeverityAnalyzer
from .models import (
    AuditLog,
    AuditAction,
    AuditSeverity,
    AuditLogSummary,
)


class AuditService:
    """
    权限审计服务 / Permission Audit Service

    提供API层面的自动审计功能，记录所有写操作到audit_log表。
    支持装饰器模式，自动捕获操作上下文和数据变更。

    Provides API-level automatic audit functionality, recording all write operations
    to the audit_log table. Supports decorator pattern to automatically capture
    operation context and data changes.
    """

    def __init__(self):
        """初始化审计服务 / Initialize Audit Service"""
        self.db_manager: Optional[DatabaseManager] = None
        self.logger = get_logger(f"audit.{self.__class__.__name__}")

        # 组合其他组件
        self.data_sanitizer = DataSanitizer()
        self.severity_analyzer = SeverityAnalyzer()

    async def initialize(self) -> bool:
        """
        初始化服务 / Initialize Service

        Returns:
            初始化是否成功 / Whether initialization was successful
        """
        try:
            if not self.db_manager:
                self.db_manager = DatabaseManager()
                self.db_manager.initialize()

            self.logger.info("审计服务初始化完成")
            return True

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            self.logger.error(f"初始化审计服务失败: {e}")
            return False

    def close(self) -> None:
        """关闭服务 / Close Service"""
        if self.db_manager:
            self.db_manager.close()
        self.logger.info("审计服务已关闭")

    # 委托方法到相应组件
    def _hash_sensitive_value(self, value: str) -> str:
        """委托给data_sanitizer"""
        return self.data_sanitizer._hash_sensitive_value(value)

    def _sanitize_data(self, data: Any) -> Any:
        """委托给data_sanitizer"""
        return self.data_sanitizer._sanitize_data(data)

    def _determine_severity(
        self, action: str, table: str, user_role: str
    ) -> AuditSeverity:
        """委托给severity_analyzer"""
        return self.severity_analyzer._determine_severity(action, table, user_role)

    # TODO: 迁移其他方法...
    # 这里需要逐步迁移其他方法，暂时保留接口
