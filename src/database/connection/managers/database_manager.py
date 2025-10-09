"""
数据库管理器

主要的数据库连接管理类，整合引擎管理和会话管理
"""

import logging
from typing import Optional

from src.database.config import DatabaseConfig, get_database_config
from src.database.connection.core.config import DATABASE_RETRY_CONFIG
from src.database.connection.pools.engine_manager import DatabaseEngineManager
from src.database.connection.sessions.session_manager import DatabaseSessionManager
from src.utils.retry import retry

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    数据库连接管理器 / Database Connection Manager

    单例数据库连接管理器，负责初始化和管理数据库连接。
    Singleton database connection manager responsible for initializing and managing
    database connections.

    主要功能 / Main Features:
        - 初始化同步和异步数据库引擎 / Initialize sync and async database engines
        - 提供数据库会话管理 / Provide database session management
        - 支持连接池配置 / Support connection pool configuration
        - 集成重试机制 / Integrated retry mechanism

    使用示例 / Usage Example:
        ```python
        from src.database.connection.managers.database_manager import DatabaseManager

        # 初始化数据库连接
        db_manager = DatabaseManager()
        db_manager.initialize()

        # 使用同步会话
        with db_manager.get_session() as session:
            # 执行数据库操作
            pass

        # 使用异步会话
        async with db_manager.get_async_session() as session:
            # 执行异步数据库操作
            pass
        ```
    """

    _instance: Optional["DatabaseManager"] = None
    _initialized: bool = False

    def __new__(cls) -> "DatabaseManager":
        """
        实现单例模式 / Implement singleton pattern

        Returns:
            DatabaseManager: 单例实例 / Singleton instance
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化数据库管理器"""
        if not self._initialized:
            self.engine_manager = DatabaseEngineManager()
            self.session_manager = DatabaseSessionManager(self.engine_manager)
            DatabaseManager._initialized = True
            logger.debug("数据库管理器实例已创建")

    @retry(config=DATABASE_RETRY_CONFIG)
    def initialize(self, config: Optional[DatabaseConfig] = None) -> None:
        """
        初始化数据库连接 / Initialize Database Connection

        Args:
            config: 数据库配置对象，如果为None则使用环境变量 / Database config object,
                   if None then use environment variables

        Example:
            ```python
            from src.database.connection.managers.database_manager import DatabaseManager
            from src.database.config import DatabaseConfig
            import os

            # 使用自定义配置
            config = DatabaseConfig(
                host="localhost",
                port=5432,
                database="football_prediction",
                user="football_user",
                password=os.getenv("DB_PASSWORD")
            )
            db_manager = DatabaseManager()
            db_manager.initialize(config)
            ```

        Note:
            该方法应该在应用程序启动时调用一次。
            This method should be called once at application startup.
        """
        if config is None:
            config = get_database_config()

        logger.info(f"初始化数据库连接到 {config.host}:{config.port}/{config.database}")

        try:
            self.engine_manager.initialize_engines(config)
            logger.info("数据库连接初始化完成")
        except Exception as e:
            logger.error(f"数据库连接初始化失败: {e}")
            raise

    def get_config(self) -> Optional[DatabaseConfig]:
        """
        获取数据库配置

        Returns:
            数据库配置对象，如果未初始化则返回None
        """
        return self.engine_manager.get_config()

    @property
    def sync_engine(self):
        """获取同步数据库引擎"""
        return self.engine_manager.sync_engine

    @property
    def async_engine(self):
        """获取异步数据库引擎"""
        return self.engine_manager.async_engine

    def create_session(self):
        """创建同步数据库会话"""
        return self.session_manager.get_sync_session()

    def create_async_session(self):
        """创建异步数据库会话"""
        return self.session_manager.get_async_session_obj()

    def get_session(self):
        """
        获取同步数据库会话上下文管理器

        Returns:
            ContextManager: 同步数据库会话上下文管理器
        """
        return self.session_manager.get_session()

    def get_async_session(self):
        """
        获取异步数据库会话上下文管理器

        Returns:
            AsyncContextManager: 异步数据库会话上下文管理器
        """
        return self.session_manager.get_async_session()

    def execute_with_retry(self, operation):
        """
        带重试机制执行同步数据库操作

        Args:
            operation: 要执行的操作

        Returns:
            操作结果
        """
        with self.get_session() as session:
            return self.session_manager.execute_with_retry(session, operation)

    async def execute_async_with_retry(self, operation):
        """
        带重试机制执行异步数据库操作

        Args:
            operation: 要执行的操作

        Returns:
            操作结果
        """
        async with self.get_async_session() as session:
            return await self.session_manager.execute_async_with_retry(session, operation)

    def close(self) -> None:
        """关闭数据库连接"""
        try:
            self.engine_manager.close_engines()
            logger.info("数据库连接已关闭")
        except Exception as e:
            logger.error(f"关闭数据库连接时出错: {e}")

    def is_initialized(self) -> bool:
        """
        检查数据库是否已初始化

        Returns:
            bool: 是否已初始化
        """
        return self.engine_manager.is_initialized

    def health_check(self) -> dict:
        """
        数据库健康检查

        Returns:
            dict: 健康状态信息
        """
        health_info = {
            "status": "unhealthy",
            "sync_engine": False,
            "async_engine": False,
            "config": None,
            "error": None
        }

        try:
            # 检查引擎状态
            if self.engine_manager._sync_engine:
                health_info["sync_engine"] = True
            if self.engine_manager._async_engine:
                health_info["async_engine"] = True

            # 检查配置
            config = self.get_config()
            if config:
                health_info["config"] = {
                    "host": config.host,
                    "port": config.port,
                    "database": config.database,
                    "user": config.user
                }

            # 执行简单查询测试连接
            with self.get_session() as session:
                session.execute("SELECT 1")
                health_info["status"] = "healthy"

        except Exception as e:
            health_info["error"] = str(e)
            logger.error(f"数据库健康检查失败: {e}")

        return health_info

    def get_pool_status(self) -> dict:
        """
        获取连接池状态

        Returns:
            dict: 连接池状态信息
        """
        pool_status = {}

        try:
            # 同步引擎连接池状态
            if self.engine_manager._sync_engine:
                sync_pool = self.engine_manager._sync_engine.pool
                pool_status["sync"] = {
                    "size": sync_pool.size(),
                    "checked_in": sync_pool.checkedin(),
                    "checked_out": sync_pool.checkedout(),
                    "overflow": sync_pool.overflow(),
                }

            # 异步引擎连接池状态
            if self.engine_manager._async_engine:
                async_pool = self.engine_manager._async_engine.pool
                pool_status["async"] = {
                    "size": async_pool.size(),
                    "checked_in": async_pool.checkedin(),
                    "checked_out": async_pool.checkedout(),
                    "overflow": async_pool.overflow(),
                }

        except Exception as e:
            pool_status["error"] = str(e)
            logger.error(f"获取连接池状态失败: {e}")

        return pool_status