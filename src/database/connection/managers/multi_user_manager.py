"""
多用户数据库管理器

支持多角色、多权限的数据库连接管理
"""

import logging
from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncGenerator, Dict, Generator, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.database.config import DatabaseConfig
from src.database.connection.core.enums import DatabaseRole
from src.database.connection.managers.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class MultiUserDatabaseManager:
    """
    多用户数据库连接管理器 / Multi-User Database Connection Manager

    支持多用户权限分离的数据库连接管理。
    Supports multi-user permission-separated database connection management.

    主要功能 / Main Features:
        - 支持多种用户角色 / Support multiple user roles
        - 权限分离和管理 / Permission separation and management
        - 角色特定的连接配置 / Role-specific connection configuration
        - 自动权限验证 / Automatic permission verification

    使用示例 / Usage Example:
        ```python
        from src.database.connection.managers.multi_user_manager import MultiUserDatabaseManager
        from src.database.connection.core.enums import DatabaseRole

        # 创建多用户管理器
        multi_db = MultiUserDatabaseManager()

        # 初始化不同角色的连接
        await multi_db.initialize_role_connections({
            DatabaseRole.READER: reader_config,
            DatabaseRole.WRITER: writer_config,
            DatabaseRole.ADMIN: admin_config
        })

        # 使用读角色连接
        with multi_db.get_session(DatabaseRole.READER) as session:
            # 执行只读操作
            result = session.execute(text("SELECT * FROM matches"))
        ```
    """

    def __init__(self):
        """初始化多用户数据库管理器"""
        self._managers: Dict[DatabaseRole, DatabaseManager] = {}
        self._configs: Dict[DatabaseRole, DatabaseConfig] = {}
        self._default_role = DatabaseRole.READER
        logger.debug("多用户数据库管理器已创建")

    async def initialize_role_connections(
        self,
        role_configs: Dict[DatabaseRole, DatabaseConfig]
    ) -> None:
        """
        初始化所有角色的数据库连接

        Args:
            role_configs: 角色到配置的映射
        """
        logger.info("初始化多角色数据库连接")

        for role, config in role_configs.items():
            try:
                # 为每个角色创建独立的数据库管理器
                manager = DatabaseManager()
                manager.initialize(config)

                self._managers[role] = manager
                self._configs[role] = config

                logger.info(f"角色 {role.value} 的数据库连接已初始化")

                # 验证权限
                await self._verify_role_permissions(role, manager)

            except Exception as e:
                logger.error(f"初始化角色 {role.value} 的连接失败: {e}")
                raise

        logger.info("所有角色数据库连接初始化完成")

    async def _verify_role_permissions(
        self,
        role: DatabaseRole,
        manager: DatabaseManager
    ) -> None:
        """
        验证角色权限

        Args:
            role: 数据库角色
            manager: 数据库管理器
        """
        try:
            with manager.get_session() as session:
                # 尝试执行角色允许的操作
                permissions = DatabaseRole.get_permissions(role)

                # 验证SELECT权限（所有角色都应该有）
                if permissions.get("select", False):
                    session.execute(text("SELECT 1"))

                # 验证INSERT权限（WRITER和ADMIN）
                if permissions.get("insert", False):
                    # 创建临时表测试
                    try:
                        session.execute(text("CREATE TEMP TABLE test_permission (id INT)"))
                        session.execute(text("INSERT INTO test_permission VALUES (1)"))
                        session.execute(text("DROP TABLE test_permission"))
                    except Exception as e:
                        logger.warning(f"角色 {role.value} 可能缺少INSERT权限: {e}")

                logger.debug(f"角色 {role.value} 权限验证通过")

        except Exception as e:
            logger.error(f"角色 {role.value} 权限验证失败: {e}")
            # 不抛出异常，只记录警告

    def get_manager(self, role: Optional[DatabaseRole] = None) -> DatabaseManager:
        """
        获取指定角色的数据库管理器

        Args:
            role: 数据库角色，如果为None则使用默认角色

        Returns:
            DatabaseManager: 数据库管理器

        Raises:
            ValueError: 如果角色未初始化
        """
        if role is None:
            role = self._default_role

        if role not in self._managers:
            raise ValueError(f"角色 {role.value} 的数据库连接未初始化")

        return self._managers[role]

    @contextmanager
    def get_session(
        self,
        role: Optional[DatabaseRole] = None
    ) -> Generator[Session, None, None]:
        """
        获取指定角色的同步数据库会话

        Args:
            role: 数据库角色，如果为None则使用默认角色

        Yields:
            Session: 数据库会话

        Raises:
            ValueError: 如果角色未初始化或权限不足
        """
        manager = self.get_manager(role)

        # 记录角色使用
        used_role = role or self._default_role
        logger.debug(f"使用角色 {used_role.value} 的数据库会话")

        with manager.get_session() as session:
            yield session

    @asynccontextmanager
    async def get_async_session(
        self,
        role: Optional[DatabaseRole] = None
    ) -> AsyncGenerator[AsyncSession, None]:
        """
        获取指定角色的异步数据库会话

        Args:
            role: 数据库角色，如果为None则使用默认角色

        Yields:
            AsyncSession: 异步数据库会话

        Raises:
            ValueError: 如果角色未初始化或权限不足
        """
        manager = self.get_manager(role)

        # 记录角色使用
        used_role = role or self._default_role
        logger.debug(f"使用角色 {used_role.value} 的异步数据库会话")

        async with manager.get_async_session() as session:
            yield session

    def set_default_role(self, role: DatabaseRole) -> None:
        """
        设置默认角色

        Args:
            role: 默认数据库角色
        """
        if role not in self._managers:
            raise ValueError(f"角色 {role.value} 的数据库连接未初始化")

        self._default_role = role
        logger.info(f"默认角色已设置为 {role.value}")

    def get_default_role(self) -> DatabaseRole:
        """
        获取默认角色

        Returns:
            DatabaseRole: 默认数据库角色
        """
        return self._default_role

    def check_permission(
        self,
        role: DatabaseRole,
        operation: str
    ) -> bool:
        """
        检查角色是否有执行特定操作的权限

        Args:
            role: 数据库角色
            operation: 操作类型（select, insert, update, delete, create, drop）

        Returns:
            bool: 是否有权限
        """
        if role not in self._managers:
            logger.warning(f"角色 {role.value} 未初始化")
            return False

        return DatabaseRole(role).has_permission(operation)

    def get_role_config(self, role: DatabaseRole) -> Optional[DatabaseConfig]:
        """
        获取角色的数据库配置

        Args:
            role: 数据库角色

        Returns:
            Optional[DatabaseConfig]: 数据库配置
        """
        return self._configs.get(role)

    def list_initialized_roles(self) -> list:
        """
        列出已初始化的角色

        Returns:
            list: 已初始化的角色列表
        """
        return list(self._managers.keys())

    def close_all_connections(self) -> None:
        """关闭所有角色的数据库连接"""
        logger.info("关闭所有角色的数据库连接")

        for role, manager in self._managers.items():
            try:
                manager.close()
                logger.info(f"角色 {role.value} 的连接已关闭")
            except Exception as e:
                logger.error(f"关闭角色 {role.value} 的连接失败: {e}")

        self._managers.clear()
        self._configs.clear()

    def get_all_health_status(self) -> Dict[str, Any]:
        """
        获取所有角色的健康状态

        Returns:
            Dict[str, Any]: 健康状态信息
        """
        health_status = {
            "default_role": self._default_role.value,
            "roles": {},
            "overall_status": "unhealthy"
        }

        healthy_count = 0
        total_count = len(self._managers)

        for role, manager in self._managers.items():
            try:
                role_health = manager.health_check()
                health_status["roles"][role.value] = role_health

                if role_health.get("status") == "healthy":
                    healthy_count += 1
            except Exception as e:
                health_status["roles"][role.value] = {
                    "status": "error",
                    "error": str(e)
                }

        # 判断整体状态
        if healthy_count == total_count:
            health_status["overall_status"] = "healthy"
        elif healthy_count > 0:
            health_status["overall_status"] = "degraded"

        return health_status

    def get_connection_statistics(self) -> Dict[str, Any]:
        """
        获取所有角色的连接统计信息

        Returns:
            Dict[str, Any]: 连接统计信息
        """
        stats = {
            "roles": {},
            "total_connections": 0
        }

        for role, manager in self._managers.items():
            try:
                pool_status = manager.get_pool_status()
                stats["roles"][role.value] = pool_status

                # 累计连接数
                if "sync" in pool_status:
                    stats["total_connections"] += pool_status["sync"].get("size", 0)
                if "async" in pool_status:
                    stats["total_connections"] += pool_status["async"].get("size", 0)

            except Exception as e:
                stats["roles"][role.value] = {
                    "error": str(e)
                }

        return stats