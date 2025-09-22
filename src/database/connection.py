"""
数据库连接管理模块 / Database Connection Management Module

提供同步和异步的PostgreSQL数据库连接、会话管理和生命周期控制。
支持多用户权限分离的数据库连接管理。
集成重试机制以提高连接可靠性。

Provides synchronous and asynchronous PostgreSQL database connection, session management,
and lifecycle control. Supports multi-user permission-separated database connection management.
Integrates retry mechanisms to improve connection reliability.

主要类 / Main Classes:
    DatabaseManager: 单例数据库连接管理器 / Singleton database connection manager
    MultiUserDatabaseManager: 多用户数据库连接管理器 / Multi-user database connection manager

主要方法 / Main Methods:
    DatabaseManager.initialize(): 初始化数据库连接 / Initialize database connection
    DatabaseManager.get_session(): 获取同步会话 / Get synchronous session
    DatabaseManager.get_async_session(): 获取异步会话 / Get asynchronous session

使用示例 / Usage Example:
    ```python
    from src.database.connection import DatabaseManager

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

环境变量 / Environment Variables:
    DB_HOST: 数据库主机地址 / Database host address
    DB_PORT: 数据库端口 / Database port
    DB_NAME: 数据库名称 / Database name
    DB_USER: 数据库用户名 / Database username
    DB_PASSWORD: 数据库密码 / Database password
    DATABASE_RETRY_MAX_ATTEMPTS: 数据库重试最大尝试次数，默认5 / Database retry max attempts, default 5
    DATABASE_RETRY_BASE_DELAY: 数据库重试基础延迟秒数，默认1.0 / Database retry base delay in seconds, default 1.0

依赖 / Dependencies:
    - sqlalchemy: 数据库ORM框架 / Database ORM framework
    - psycopg2: PostgreSQL数据库适配器 / PostgreSQL database adapter
    - src.utils.retry: 重试机制 / Retry mechanism
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager, contextmanager
from enum import Enum
from typing import Any, AsyncGenerator, Dict, Generator, Optional

from sqlalchemy import Engine, create_engine, select, text, update
from sqlalchemy.ext.asyncio import (AsyncEngine, AsyncSession,
                                    async_sessionmaker, create_async_engine)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from src.utils.retry import RetryConfig, retry

from .config import DatabaseConfig, get_database_config

logger = logging.getLogger(__name__)

# 数据库重试配置 / Database retry configuration
DATABASE_RETRY_CONFIG = RetryConfig(
    max_attempts=int(os.getenv("DATABASE_RETRY_MAX_ATTEMPTS", "5")),
    base_delay=float(os.getenv("DATABASE_RETRY_BASE_DELAY", "1.0")),
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
    retryable_exceptions=(ConnectionError, TimeoutError, asyncio.TimeoutError),
)


class DatabaseRole(str, Enum):
    """
    数据库用户角色枚举 / Database User Role Enumeration

    定义数据库用户的三种角色，用于权限分离。
    Defines three roles for database users for permission separation.

    Roles:
        READER: 只读用户（分析、前端） / Read-only user (analytics, frontend)
        WRITER: 读写用户（数据采集） / Read-write user (data collection)
        ADMIN: 管理员用户（运维、迁移） / Administrator user (operations, migration)

    Example:
        ```python
        from src.database.connection import DatabaseRole

        # 使用枚举值
        role = DatabaseRole.READER
        print(role.value)  # 输出: reader
        ```

    Note:
        基于DATA_DESIGN.md第5.3节权限控制设计。
        Based on DATA_DESIGN.md Section 5.3 Permission Control Design.
    """

    READER = "reader"  # 只读用户（分析、前端） / Read-only user (analytics, frontend)
    WRITER = "writer"  # 读写用户（数据采集） / Read-write user (data collection)
    ADMIN = "admin"  # 管理员用户（运维、迁移） / Administrator user (operations, migration)


class DatabaseManager:
    """
    数据库连接管理器 / Database Connection Manager

    提供单例模式的数据库连接管理，支持同步和异步操作。
    实现连接池管理、会话管理和健康检查功能。

    Provides singleton database connection management with support for both
    synchronous and asynchronous operations. Implements connection pool management,
    session management, and health check functionality.

    Attributes:
        _instance (Optional[DatabaseManager]): 单例实例 / Singleton instance
        _sync_engine (Optional[Engine]): 同步数据库引擎 / Synchronous database engine
        _async_engine (Optional[AsyncEngine]): 异步数据库引擎 / Asynchronous database engine
        _session_factory (Optional[sessionmaker]): 同步会话工厂 / Synchronous session factory
        _async_session_factory (Optional[async_sessionmaker]): 异步会话工厂 / Asynchronous session factory
        _config (Optional[DatabaseConfig]): 数据库配置 / Database configuration

    Example:
        ```python
        from src.database.connection import DatabaseManager

        # 获取单例实例
        db_manager = DatabaseManager()
        db_manager.initialize()

        # 检查数据库健康状态
        is_healthy = db_manager.health_check()
        ```
    """

    _instance: Optional["DatabaseManager"] = None
    _sync_engine: Optional[Engine] = None
    _async_engine: Optional[AsyncEngine] = None
    _session_factory: Optional[sessionmaker] = None
    _async_session_factory: Optional[async_sessionmaker] = None

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, "_initialized"):
            self._config: Optional[DatabaseConfig] = None
            self._initialized = True

    def initialize(self, config: Optional[DatabaseConfig] = None) -> None:
        """
        初始化数据库连接 / Initialize Database Connection

        根据提供的配置初始化同步和异步数据库引擎及会话工厂。
        如果未提供配置，则使用默认配置。

        Initialize synchronous and asynchronous database engines and session factories
        based on the provided configuration. If no configuration is provided,
        use the default configuration.

        Args:
            config (Optional[DatabaseConfig]): 数据库配置对象 / Database configuration object
                If None, uses default configuration from environment variables.
                Defaults to None.

        Raises:
            ValueError: 当配置参数无效时抛出 / Raised when configuration parameters are invalid
            RuntimeError: 当数据库连接初始化失败时抛出 / Raised when database connection initialization fails

        Example:
            ```python
            from src.database.connection import DatabaseManager, DatabaseConfig

            db_manager = DatabaseManager()

            # 使用默认配置
            db_manager.initialize()

            # 使用自定义配置
            config = DatabaseConfig(
                host="localhost",
                port=5432,
                database="football_prediction",
                user="football_user",
                password="football_password"
            )
            db_manager.initialize(config)
            ```

        Note:
            该方法应该在应用程序启动时调用一次。
            This method should be called once at application startup.
        """
        if config is None:
            config = get_database_config()

        self._config = config
        logger.info(f"初始化数据库连接到 {config.host}:{config.port}/{config.database}")

        # 创建同步引擎
        # 对于SQLite，不使用连接池
        if config.database.endswith(".db") or config.database == ":memory:":
            self._sync_engine = create_engine(
                config.sync_url,
                echo=config.echo,
                echo_pool=config.echo_pool,
            )
        else:
            self._sync_engine = create_engine(
                config.sync_url,
                poolclass=QueuePool,
                pool_size=config.pool_size,
                max_overflow=config.max_overflow,
                pool_timeout=config.pool_timeout,
                pool_recycle=config.pool_recycle,
                echo=config.echo,
                echo_pool=config.echo_pool,
            )

        # 创建异步引擎
        # 对于SQLite，不使用连接池参数
        if config.database.endswith(".db") or config.database == ":memory:":
            self._async_engine = create_async_engine(
                config.async_url,
                echo=config.echo,
                echo_pool=config.echo_pool,
            )
        else:
            self._async_engine = create_async_engine(
                config.async_url,
                pool_size=config.async_pool_size,
                max_overflow=config.async_max_overflow,
                pool_timeout=config.pool_timeout,
                pool_recycle=config.pool_recycle,
                echo=config.echo,
                echo_pool=config.echo_pool,
            )

        # 创建会话工厂
        self._session_factory = sessionmaker(
            bind=self._sync_engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

        self._async_session_factory = async_sessionmaker(
            bind=self._async_engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

        logger.info("数据库连接初始化完成")

    def get_config(self) -> Optional[DatabaseConfig]:
        """
        获取数据库配置

        Returns:
            数据库配置对象，如果未初始化则返回None
        """
        return self._config

    @property
    def sync_engine(self) -> Engine:
        """获取同步数据库引擎"""
        if self._sync_engine is None:
            raise RuntimeError("数据库连接未初始化，请先调用 initialize()")
        return self._sync_engine

    @property
    def async_engine(self) -> AsyncEngine:
        """获取异步数据库引擎"""
        if self._async_engine is None:
            raise RuntimeError("数据库连接未初始化，请先调用 initialize()")
        return self._async_engine

    def create_session(self) -> Session:
        """创建同步数据库会话"""
        if self._session_factory is None:
            raise RuntimeError("数据库连接未初始化，请先调用 initialize()")
        return self._session_factory()

    def create_async_session(self) -> AsyncSession:
        """创建异步数据库会话"""
        if self._async_session_factory is None:
            raise RuntimeError("数据库连接未初始化，请先调用 initialize()")
        return self._async_session_factory()

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        获取同步数据库会话上下文管理器 / Get Synchronous Database Session Context Manager

        提供一个同步数据库会话的上下文管理器，自动处理事务提交和回滚。
        Provides a context manager for synchronous database sessions that automatically
        handles transaction commit and rollback.

        Yields:
            Session: 同步数据库会话 / Synchronous database session

        Raises:
            Exception: 当数据库操作发生错误时抛出 / Raised when database operations fail

        Example:
            ```python
            from src.database.connection import DatabaseManager

            db_manager = DatabaseManager()
            db_manager.initialize()

            # 使用同步会话进行数据库操作
            with db_manager.get_session() as session:
                # 执行数据库查询
                result = session.query(SomeModel).all()
                # 执行数据库更新
                session.add(new_record)
                # 自动提交或回滚
            ```

        Note:
            会话在使用完毕后会自动关闭。
            Session is automatically closed after use.
        """
        session = self.create_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            session.close()

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        获取异步数据库会话上下文管理器 / Get Asynchronous Database Session Context Manager

        提供一个异步数据库会话的上下文管理器，自动处理事务提交和回滚。
        Provides a context manager for asynchronous database sessions that automatically
        handles transaction commit and rollback.

        Yields:
            AsyncSession: 异步数据库会话 / Asynchronous database session

        Raises:
            Exception: 当异步数据库操作发生错误时抛出 / Raised when asynchronous database operations fail

        Example:
            ```python
            from src.database.connection import DatabaseManager

            db_manager = DatabaseManager()
            db_manager.initialize()

            # 使用异步会话进行数据库操作
            async with db_manager.get_async_session() as session:
                # 执行异步数据库查询
                result = await session.execute(select(SomeModel))
                # 执行异步数据库更新
                session.add(new_record)
                # 自动提交或回滚
            ```

        Note:
            会话在使用完毕后会自动关闭。
            Session is automatically closed after use.
        """
        session = self.create_async_session()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"异步数据库操作失败: {e}")
            raise
        finally:
            await session.close()

    @retry(DATABASE_RETRY_CONFIG)
    async def get_match(self, match_id: int) -> Optional[Dict[str, Any]]:
        """
        获取比赛信息 / Get Match Information

        从数据库查询指定比赛的基本信息，包含重试机制以提高可靠性。
        Query basic information of specified match from database with retry mechanism for improved reliability.

        Args:
            match_id (int): 比赛唯一标识符 / Unique match identifier

        Returns:
            Optional[Dict[str, Any]]: 比赛信息字典，如果比赛不存在则返回None /
                                     Match information dictionary, or None if match doesn't exist
                - id (int): 比赛ID / Match ID
                - home_team_id (int): 主队ID / Home team ID
                - away_team_id (int): 客队ID / Away team ID
                - league_id (int): 联赛ID / League ID
                - match_time (datetime): 比赛时间 / Match time
                - match_status (str): 比赛状态 / Match status
                - season (str): 赛季 / Season

        Raises:
            Exception: 当数据库查询发生错误时抛出 / Raised when database query fails

        Example:
            ```python
            from src.database.connection import DatabaseManager

            db_manager = DatabaseManager()
            db_manager.initialize()

            match_info = await db_manager.get_match(12345)
            if match_info:
                print(f"主队: {match_info['home_team_id']}, 客队: {match_info['away_team_id']}")
            ```

        Note:
            该方法包含自动重试机制，最大尝试5次。
            This method includes an automatic retry mechanism with up to 5 attempts.
        """
        from src.database.models.match import Match

        async with self.get_async_session() as session:
            result = await session.execute(select(Match).where(Match.id == match_id))
            match = result.scalar_one_or_none()
            if match:
                return {c.name: getattr(match, c.name) for c in match.__table__.columns}
            return None

    @retry(DATABASE_RETRY_CONFIG)
    async def update_match(self, match_id: int, data: Dict[str, Any]) -> bool:
        """
        更新比赛信息 / Update Match Information

        更新指定比赛的信息，包含重试机制以提高可靠性。
        Update information of specified match with retry mechanism for improved reliability.

        Args:
            match_id (int): 比赛唯一标识符 / Unique match identifier
            data (Dict[str, Any]): 要更新的数据 / Data to update

        Returns:
            bool: 更新是否成功 / Whether update was successful

        Raises:
            Exception: 当数据库更新发生错误时抛出 / Raised when database update fails

        Example:
            ```python
            from src.database.connection import DatabaseManager

            db_manager = DatabaseManager()
            db_manager.initialize()

            success = await db_manager.update_match(12345, {"match_status": "completed"})
            if success:
                print("比赛信息更新成功")
            ```

        Note:
            该方法包含自动重试机制，最大尝试5次。
            This method includes an automatic retry mechanism with up to 5 attempts.
        """
        from src.database.models.match import Match

        async with self.get_async_session() as session:
            stmt = update(Match).where(Match.id == match_id).values(**data)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    @retry(DATABASE_RETRY_CONFIG)
    async def get_prediction(self, match_id: int) -> Optional[Dict[str, Any]]:
        """
        获取预测信息 / Get Prediction Information

        从数据库查询指定比赛的预测信息，包含重试机制以提高可靠性。
        Query prediction information of specified match from database with retry mechanism for improved reliability.

        Args:
            match_id (int): 比赛唯一标识符 / Unique match identifier

        Returns:
            Optional[Dict[str, Any]]: 预测信息字典，如果预测不存在则返回None /
                                     Prediction information dictionary, or None if prediction doesn't exist

        Raises:
            Exception: 当数据库查询发生错误时抛出 / Raised when database query fails

        Example:
            ```python
            from src.database.connection import DatabaseManager

            db_manager = DatabaseManager()
            db_manager.initialize()

            prediction = await db_manager.get_prediction(12345)
            if prediction:
                print(f"预测结果: {prediction['predicted_result']}")
            ```

        Note:
            该方法包含自动重试机制，最大尝试5次。
            This method includes an automatic retry mechanism with up to 5 attempts.
        """
        from src.database.models.predictions import Predictions

        async with self.get_async_session() as session:
            result = await session.execute(
                select(Predictions).where(Predictions.match_id == match_id)
            )
            prediction = result.scalar_one_or_none()
            if prediction:
                return {
                    c.name: getattr(prediction, c.name)
                    for c in prediction.__table__.columns
                }
            return None

    async def close(self) -> None:
        """关闭数据库连接"""
        if self._async_engine:
            try:
                await self._async_engine.dispose()
                logger.info("异步数据库连接已关闭")
            except Exception as e:
                logger.error(f"关闭异步数据库连接失败: {e}")

        if self._sync_engine:
            try:
                self._sync_engine.dispose()
                logger.info("同步数据库连接已关闭")
            except Exception as e:
                logger.error(f"关闭同步数据库连接失败: {e}")

    def health_check(self) -> bool:
        """
        检查数据库连接健康状态（同步版本） / Check Database Connection Health (Synchronous Version)

        执行简单的数据库查询以验证连接是否正常。
        Execute a simple database query to verify that the connection is healthy.

        Returns:
            bool: 数据库是否健康 / Whether the database is healthy
                True if connection is healthy, False otherwise

        Example:
            ```python
            from src.database.connection import DatabaseManager

            db_manager = DatabaseManager()
            db_manager.initialize()

            if db_manager.health_check():
                print("数据库连接正常")
            else:
                print("数据库连接异常")
            ```

        Note:
            该方法用于健康检查端点和监控系统。
            This method is used for health check endpoints and monitoring systems.
        """
        try:
            session = self.create_session()
            # 使用text()包装SQL字符串
            session.execute(text("SELECT 1"))
            session.close()
            return True
        except Exception:
            return False

    async def async_health_check(self) -> bool:
        """
        检查数据库连接健康状态（异步版本） / Check Database Connection Health (Asynchronous Version)

        执行简单的异步数据库查询以验证连接是否正常。
        Execute a simple asynchronous database query to verify that the connection is healthy.

        Returns:
            bool: 数据库是否健康 / Whether the database is healthy
                True if connection is healthy, False otherwise

        Example:
            ```python
            from src.database.connection import DatabaseManager

            db_manager = DatabaseManager()
            db_manager.initialize()

            is_healthy = await db_manager.async_health_check()
            if is_healthy:
                print("数据库连接正常")
            else:
                print("数据库连接异常")
            ```

        Note:
            该方法用于异步健康检查场景。
            This method is used for asynchronous health check scenarios.
        """
        try:
            session = self.create_async_session()
            # 使用text()包装SQL字符串
            await session.execute(text("SELECT 1"))
            await session.close()
            return True
        except Exception:
            return False

    @retry(DATABASE_RETRY_CONFIG)
    async def health_check_with_retry(self) -> bool:
        """
        检查数据库连接健康状态（异步版本，带重试） / Check Database Connection Health (Asynchronous Version with Retry)

        执行简单的异步数据库查询以验证连接是否正常，包含重试机制。
        Execute a simple asynchronous database query to verify that the connection is healthy, with retry mechanism.

        Returns:
            bool: 数据库是否健康 / Whether the database is healthy
                True if connection is healthy, False otherwise

        Example:
            ```python
            from src.database.connection import DatabaseManager

            db_manager = DatabaseManager()
            db_manager.initialize()

            is_healthy = await db_manager.health_check_with_retry()
            if is_healthy:
                print("数据库连接正常")
            else:
                print("数据库连接异常")
            ```

        Note:
            该方法包含自动重试机制，最大尝试5次。
            This method includes an automatic retry mechanism with up to 5 attempts.
        """
        try:
            session = self.create_async_session()
            # 使用text()包装SQL字符串
            await session.execute(text("SELECT 1"))
            await session.close()
            return True
        except Exception:
            return False

    @retry(DATABASE_RETRY_CONFIG)
    def health_check_sync_with_retry(self) -> bool:
        """
        检查数据库连接健康状态（同步版本，带重试） / Check Database Connection Health (Synchronous Version with Retry)

        执行简单的同步数据库查询以验证连接是否正常，包含重试机制。
        Execute a simple synchronous database query to verify that the connection is healthy, with retry mechanism.

        Returns:
            bool: 数据库是否健康 / Whether the database is healthy
                True if connection is healthy, False otherwise

        Example:
            ```python
            from src.database.connection import DatabaseManager

            db_manager = DatabaseManager()
            db_manager.initialize()

            is_healthy = db_manager.health_check_sync_with_retry()
            if is_healthy:
                print("数据库连接正常")
            else:
                print("数据库连接异常")
            ```

        Note:
            该方法包含自动重试机制，最大尝试5次。
            This method includes an automatic retry mechanism with up to 5 attempts.
        """
        try:
            session = self.create_session()
            # 使用text()包装SQL字符串
            session.execute(text("SELECT 1"))
            session.close()
            return True
        except Exception:
            return False


class MultiUserDatabaseManager:
    """
    多用户数据库连接管理器

    支持按用户角色管理数据库连接，实现权限分离。
    基于 DATA_DESIGN.md 第5.3节权限控制设计。
    """

    _instance: Optional["MultiUserDatabaseManager"] = None
    _managers: Dict[DatabaseRole, DatabaseManager] = {}
    _configs: Dict[DatabaseRole, DatabaseConfig] = {}

    def __new__(cls) -> "MultiUserDatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, "_initialized"):
            self._initialized = True

    def initialize(self, base_config: Optional[DatabaseConfig] = None) -> None:
        """
        初始化多用户数据库连接

        Args:
            base_config: 基础数据库配置，将为每个角色创建专用配置
        """
        if base_config is None:
            base_config = get_database_config()

        # 用户凭据映射
        user_credentials = {
            DatabaseRole.READER: {
                "username": "football_reader",
                "password": "reader_password_2025",
            },
            DatabaseRole.WRITER: {
                "username": "football_writer",
                "password": "writer_password_2025",
            },
            DatabaseRole.ADMIN: {
                "username": "football_admin",
                "password": "admin_password_2025",
            },
        }

        # 为每个角色创建专用的数据库配置和连接管理器
        for role, credentials in user_credentials.items():
            # 创建角色专用配置
            role_config = DatabaseConfig(
                host=base_config.host,
                port=base_config.port,
                database=base_config.database,
                username=credentials["username"],
                password=credentials["password"],
                pool_size=base_config.pool_size,
                max_overflow=base_config.max_overflow,
                pool_timeout=base_config.pool_timeout,
                pool_recycle=base_config.pool_recycle,
                async_pool_size=base_config.async_pool_size,
                async_max_overflow=base_config.async_max_overflow,
                echo=base_config.echo,
                echo_pool=base_config.echo_pool,
            )

            self._configs[role] = role_config

            # 为每个角色创建独立的数据库管理器
            manager = DatabaseManager()
            manager.initialize(role_config)

            self._managers[role] = manager

            logger.info(f"初始化 {role.value} 用户数据库连接: {credentials['username']}")

        logger.info("多用户数据库连接管理器初始化完成")

    def get_manager(self, role: DatabaseRole) -> DatabaseManager:
        """
        获取指定角色的数据库管理器

        Args:
            role: 数据库用户角色

        Returns:
            DatabaseManager: 角色对应的数据库管理器

        Raises:
            RuntimeError: 如果管理器未初始化或角色不存在
        """
        if role not in self._managers:
            raise RuntimeError(f"数据库角色 {role.value} 的管理器未初始化，请先调用 initialize()")
        return self._managers[role]

    @contextmanager
    def get_session(self, role: DatabaseRole) -> Generator[Session, None, None]:
        """
        获取指定角色的同步数据库会话

        Args:
            role: 数据库用户角色

        Usage:
            with multi_db_manager.get_session(DatabaseRole.READER) as session:
                # 只读操作
                results = session.query(Match).all()
        """
        manager = self.get_manager(role)
        with manager.get_session() as session:
            yield session

    @asynccontextmanager
    async def get_async_session(
        self, role: DatabaseRole
    ) -> AsyncGenerator[AsyncSession, None]:
        """
        获取指定角色的异步数据库会话

        Args:
            role: 数据库用户角色

        Usage:
            async with multi_db_manager.get_async_session(DatabaseRole.WRITER) as session:
                # 读写操作
                await session.execute(insert(RawMatchData).values(data))
        """
        manager = self.get_manager(role)
        async with manager.get_async_session() as session:
            yield session

    def health_check(self, role: Optional[DatabaseRole] = None) -> Dict[str, bool]:
        """
        检查数据库连接健康状态

        Args:
            role: 要检查的角色，如果为None则检查所有角色

        Returns:
            Dict[str, bool]: 角色名到健康状态的映射
        """
        if role:
            manager = self.get_manager(role)
            return {role.value: manager.health_check()}

        health_status = {}
        for role, manager in self._managers.items():
            health_status[role.value] = manager.health_check()

        return health_status

    async def async_health_check(
        self, role: Optional[DatabaseRole] = None
    ) -> Dict[str, bool]:
        """
        异步检查数据库连接健康状态

        Args:
            role: 要检查的角色，如果为None则检查所有角色

        Returns:
            Dict[str, bool]: 角色名到健康状态的映射
        """
        if role:
            manager = self.get_manager(role)
            return {role.value: await manager.async_health_check()}

        health_status = {}
        for role, manager in self._managers.items():
            health_status[role.value] = await manager.async_health_check()

        return health_status

    async def close(self) -> None:
        """关闭所有数据库连接"""
        for role, manager in self._managers.items():
            try:
                await manager.close()
                logger.info(f"已关闭 {role.value} 用户的数据库连接")
            except Exception as e:
                logger.error(f"关闭 {role.value} 用户数据库连接失败: {e}")

    def get_role_permissions(self, role: DatabaseRole) -> Dict[str, str]:
        """
        获取角色权限描述

        Args:
            role: 数据库用户角色

        Returns:
            Dict[str, str]: 权限描述
        """
        permissions_map = {
            DatabaseRole.READER: {
                "description": "只读用户（分析、前端）",
                "permissions": "SELECT on all tables",
                "use_cases": "数据分析、前端展示、报告生成",
            },
            DatabaseRole.WRITER: {
                "description": "读写用户（数据采集）",
                "permissions": "SELECT, INSERT, UPDATE on all tables; DELETE on raw_data tables",
                "use_cases": "数据采集、数据处理、清理任务",
            },
            DatabaseRole.ADMIN: {
                "description": "管理员用户（运维、迁移）",
                "permissions": "ALL PRIVILEGES on database",
                "use_cases": "数据库维护、架构迁移、用户管理",
            },
        }

        return permissions_map.get(role, {})


# 全局数据库管理器实例
_db_manager = DatabaseManager()
_multi_db_manager = MultiUserDatabaseManager()


def get_database_manager() -> DatabaseManager:
    """获取数据库管理器实例"""
    return _db_manager


def get_multi_user_database_manager() -> MultiUserDatabaseManager:
    """获取多用户数据库管理器实例"""
    return _multi_db_manager


def initialize_database(config: Optional[DatabaseConfig] = None) -> None:
    """
    初始化数据库连接

    Args:
        config: 数据库配置
    """
    _db_manager.initialize(config)


def initialize_multi_user_database(config: Optional[DatabaseConfig] = None) -> None:
    """
    初始化多用户数据库连接

    Args:
        config: 基础数据库配置
    """
    _multi_db_manager.initialize(config)


def initialize_test_database(config: Optional[DatabaseConfig] = None) -> None:
    """
    初始化测试数据库连接（仅创建同步引擎）

    专门为测试环境设计，避免异步引擎相关问题。
    使用in-memory SQLite数据库，自动创建所有表结构。

    Args:
        config: 测试数据库配置
    """
    from .base import Base

    if config is None:
        config = get_database_config("test")

    # 创建一个简化的数据库管理器，只用于测试
    _db_manager._config = config

    # 创建同步引擎（测试环境）
    _db_manager._sync_engine = create_engine(
        config.sync_url,
        echo=config.echo,
        echo_pool=config.echo_pool,
    )

    # 创建会话工厂
    _db_manager._session_factory = sessionmaker(
        bind=_db_manager._sync_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    # 创建所有表结构
    Base.metadata.create_all(bind=_db_manager._sync_engine)

    logger.info(f"测试数据库初始化完成: {config.sync_url}")


def get_db_session() -> Generator[Session, None, None]:
    """
    FastAPI依赖注入使用的同步数据库会话获取器

    使用示例:
        @app.get("/items/")
        def read_items(db: Session = Depends(get_db_session)):
            return db.query(Item).all()
    """
    with _db_manager.get_session() as session:
        yield session


async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI依赖注入使用的异步数据库会话获取器

    使用示例:
        @app.get("/items/")
        async def read_items(db: AsyncSession = Depends(get_async_db_session)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async with _db_manager.get_async_session() as session:
        yield session


# 多用户数据库会话依赖注入函数
def get_reader_session() -> Generator[Session, None, None]:
    """获取只读用户会话（用于数据分析、前端展示）"""
    with _multi_db_manager.get_session(DatabaseRole.READER) as session:
        yield session


def get_writer_session() -> Generator[Session, None, None]:
    """获取读写用户会话（用于数据采集、处理）"""
    with _multi_db_manager.get_session(DatabaseRole.WRITER) as session:
        yield session


def get_admin_session() -> Generator[Session, None, None]:
    """获取管理员用户会话（用于运维、迁移）"""
    with _multi_db_manager.get_session(DatabaseRole.ADMIN) as session:
        yield session


async def get_async_reader_session() -> AsyncGenerator[AsyncSession, None]:
    """获取异步只读用户会话"""
    async with _multi_db_manager.get_async_session(DatabaseRole.READER) as session:
        yield session


async def get_async_writer_session() -> AsyncGenerator[AsyncSession, None]:
    """获取异步读写用户会话"""
    async with _multi_db_manager.get_async_session(DatabaseRole.WRITER) as session:
        yield session


async def get_async_admin_session() -> AsyncGenerator[AsyncSession, None]:
    """获取异步管理员用户会话"""
    async with _multi_db_manager.get_async_session(DatabaseRole.ADMIN) as session:
        yield session


# 便捷的会话获取函数，用于直接使用
@contextmanager
def get_session(
    role: DatabaseRole = DatabaseRole.READER,
) -> Generator[Session, None, None]:
    """
    获取指定角色的数据库会话

    在测试环境中，如果多用户管理器未初始化，则回退到基础数据库管理器。

    Args:
        role: 数据库用户角色，默认为只读用户
    """
    # 检查多用户管理器是否已初始化
    try:
        with _multi_db_manager.get_session(role) as session:
            yield session
    except RuntimeError as e:
        if "未初始化" in str(e):
            # 多用户管理器未初始化，回退到基础数据库管理器（测试环境）
            logger.warning(f"多用户数据库管理器未初始化，回退到基础管理器: {e}")
            with _db_manager.get_session() as session:
                yield session
        else:
            raise


@asynccontextmanager
async def get_async_session(
    role: DatabaseRole = DatabaseRole.READER,
) -> AsyncGenerator[AsyncSession, None]:
    """
    获取指定角色的异步数据库会话

    Args:
        role: 数据库用户角色，默认为只读用户
    """
    async with _multi_db_manager.get_async_session(role) as session:
        yield session
