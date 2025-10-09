"""
from .config import DatabaseConfig, get_database_config
from .roles import DatabaseRole
from src.core.logging import get_logger
from src.utils.retry import RetryConfig, retry

多用户数据库管理器
Multi-User Database Manager

支持多角色、多权限的数据库连接管理。
"""


    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)



logger = get_logger(__name__)

# 多用户重试配置
MULTI_USER_RETRY_CONFIG = RetryConfig(
    max_attempts=int(os.getenv("DATABASE_RETRY_MAX_ATTEMPTS", "5")),
    base_delay=float(os.getenv("DATABASE_RETRY_BASE_DELAY", "1.0")),
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
)


class MultiUserDatabaseManager:
    """
    多用户数据库连接管理器 / Multi-User Database Connection Manager

    支持多种角色的数据库连接管理，实现权限分离。
    Supports multi-role database connection management with permission separation.

    Attributes:
        config (DatabaseConfig): 数据库配置 / Database configuration
        _engines (Dict[str, Engine]): 角色到引擎的映射 / Role to engine mapping
        _async_engines (Dict[str, AsyncEngine]): 角色到异步引擎的映射 / Role to async engine mapping
        _session_factories (Dict[str, sessionmaker]): 角色到会话工厂的映射 / Role to session factory mapping
        _async_session_factories (Dict[str, async_sessionmaker]): 角色到异步会话工厂的映射 / Role to async session factory mapping
    """

    def __init__(self, config: Optional[DatabaseConfig] = None):
        """
        初始化多用户数据库管理器 / Initialize Multi-User Database Manager

        Args:
            config (Optional[DatabaseConfig]): 数据库配置 / Database configuration
        """
        self.config = config or get_database_config()
        self._engines: Dict[str, Engine] = {}
        self._async_engines: Dict[str, AsyncEngine] = {}
        self._session_factories: Dict[str, sessionmaker] = {}
        self._async_session_factories: Dict[str, async_sessionmaker] = {}
        self._lock = asyncio.Lock()

    def initialize(
        self,
        role_configs: Optional[Dict[str, Dict[str, str]]] = None,
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
    ) -> None:
        """
        初始化多用户数据库连接 / Initialize Multi-User Database Connections

        Args:
            role_configs (Optional[Dict[str, Dict[str, str]]]): 角色配置字典 / Role configuration dictionary
            echo (bool): 是否输出SQL语句 / Whether to output SQL statements
            pool_size (int): 连接池大小 / Connection pool size
            max_overflow (int): 连接池最大溢出 / Maximum connection pool overflow

        Example:
            ```python
            role_configs = {
                "reader": {"username": "reader_user", "password": "reader_pass"},
                "writer": {"username": "writer_user", "password": "writer_pass"},
                "admin": {"username": "admin_user", "password": "admin_pass"},
            }
            manager = MultiUserDatabaseManager()
            manager.initialize(role_configs=role_configs)
            ```
        """
        try:
            # 默认角色配置
            if role_configs is None:
                role_configs = {
                    DatabaseRole.READER: {
                        "username": os.getenv("DB_READER_USER", "football_reader"),
                        "password": os.getenv("DB_READER_PASSWORD", ""),
                    },
                    DatabaseRole.WRITER: {
                        "username": os.getenv("DB_WRITER_USER", "football_writer"),
                        "password": os.getenv("DB_WRITER_PASSWORD", ""),
                    },
                    DatabaseRole.ADMIN: {
                        "username": os.getenv("DB_ADMIN_USER", "football_admin"),
                        "password": os.getenv("DB_ADMIN_PASSWORD", ""),
                    },
                }

            # 为每个角色创建连接
            for role, role_config in role_configs.items():
                self._initialize_role_engine(
                    role=role,
                    username=role_config["username"],
                    password=role_config["password"],
                    echo=echo,
                    pool_size=pool_size,
                    max_overflow=max_overflow,
                )

            logger.info("多用户数据库连接初始化成功")

        except Exception as e:
            logger.error(f"多用户数据库连接初始化失败: {e}")
            raise

    def _initialize_role_engine(
        self,
        role: str,
        username: str,
        password: str,
        echo: bool,
        pool_size: int,
        max_overflow: int,
    ) -> None:
        """
        为特定角色初始化引擎 / Initialize Engine for Specific Role

        Args:
            role (str): 角色名称 / Role name
            username (str): 用户名 / Username
            password (str): 密码 / Password
            echo (bool): 是否输出SQL / Whether to output SQL
            pool_size (int): 连接池大小 / Connection pool size
            max_overflow (int): 最大溢出 / Maximum overflow
        """
        try:
            # 创建角色特定的配置
            role_config = DatabaseConfig(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                username=username,
                password=password,
                driver=self.config.driver,
                ssl_mode=self.config.ssl_mode,
                timezone=self.config.timezone,
            )

            # 构建连接URL
            sync_url = role_config.get_sync_url()
            async_url = role_config.get_async_url()

            # 创建同步引擎
            self._engines[role] = create_engine(
                sync_url,
                echo=echo,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_pre_ping=True,
                pool_recycle=3600,
            )

            # 创建异步引擎
            self._async_engines[role] = create_async_engine(
                async_url,
                echo=echo,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_pre_ping=True,
                pool_recycle=3600,
            )

            # 创建会话工厂
            self._session_factories[role] = sessionmaker(
                bind=self._engines[role],
                autocommit=False,
                autoflush=False,
            )

            self._async_session_factories[role] = async_sessionmaker(
                bind=self._async_engines[role],
                autocommit=False,
                autoflush=False,
            )

            logger.info(f"角色 {role} 的数据库连接已初始化")

        except Exception as e:
            logger.error(f"初始化角色 {role} 的连接失败: {e}")
            raise

    @contextmanager
    def get_session(self, role: str = DatabaseRole.READER) -> Generator[Session, None, None]:
        """
        获取指定角色的同步会话 / Get Synchronous Session for Specific Role

        Args:
            role (str): 角色名称 / Role name

        Returns:
            Generator[Session, None, None]: 数据库会话 / Database session

        Raises:
            Exception: 当角色未初始化时抛出 / Raised when role is not initialized
        """
        if role not in self._session_factories:
            raise Exception(f"角色 {role} 未初始化")

        session = self._session_factories[role]()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"角色 {role} 的数据库会话错误: {e}")
            raise
        finally:
            session.close()

    @asynccontextmanager
    async def get_async_session(
        self, role: str = DatabaseRole.READER
    ) -> AsyncGenerator[AsyncSession, None]:
        """
        获取指定角色的异步会话 / Get Asynchronous Session for Specific Role

        Args:
            role (str): 角色名称 / Role name

        Returns:
            AsyncGenerator[AsyncSession, None, None]: 异步数据库会话 / Asynchronous database session

        Raises:
            Exception: 当角色未初始化时抛出 / Raised when role is not initialized
        """
        if role not in self._async_session_factories:
            raise Exception(f"角色 {role} 未初始化")

        session = self._async_session_factories[role]()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"角色 {role} 的异步数据库会话错误: {e}")
            raise
        finally:
            await session.close()

    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        role: str = DatabaseRole.READER,
    ) -> Any:
        """
        使用指定角色执行查询 / Execute Query with Specific Role

        Args:
            query (str): SQL查询语句 / SQL query statement
            params (Optional[Dict[str, Any]]): 查询参数 / Query parameters
            role (str): 执行查询的角色 / Role to execute query

        Returns:
            Any: 查询结果 / Query result
        """
        with self.get_session(role) as session:
            return session.execute(text(query), params or {})

    async def execute_query_async(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        role: str = DatabaseRole.READER,
    ) -> Any:
        """
        使用指定角色异步执行查询 / Execute Query Asynchronously with Specific Role

        Args:
            query (str): SQL查询语句 / SQL query statement
            params (Optional[Dict[str, Any]]): 查询参数 / Query parameters
            role (str): 执行查询的角色 / Role to execute query

        Returns:
            Any: 查询结果 / Query result
        """
        async with self.get_async_session(role) as session:
            return await session.execute(text(query), params or {})

    def close(self) -> None:
        """
        关闭所有数据库连接 / Close All Database Connections
        """
        for engine in self._engines.values():
            engine.dispose()

        self._engines.clear()
        self._async_engines.clear()
        self._session_factories.clear()
        self._async_session_factories.clear()

        logger.info("所有多用户数据库连接已关闭")

    async def close_async(self) -> None:
        """
        异步关闭所有数据库连接 / Close All Database Connections Asynchronously
        """
        for engine in self._engines.values():
            engine.dispose()

        for engine in self._async_engines.values():
            await engine.dispose()

        self._engines.clear()
        self._async_engines.clear()
        self._session_factories.clear()
        self._async_session_factories.clear()

        logger.info("所有多用户数据库连接已关闭")

    def get_role_connection_info(self, role: str) -> Dict[str, Any]:
        """
        获取角色连接信息 / Get Role Connection Information

        Args:
            role (str): 角色名称 / Role name

        Returns:
            Dict[str, Any]: 连接信息 / Connection information
        """
        if role not in self._engines:
            return {"error": f"角色 {role} 未初始化"}

        engine = self._engines[role]
        return {
            "role": role,
            "host": self.config.host,
            "port": self.config.port,
            "database": self.config.database,
            "pool_size": engine.pool.size(),
            "checked_in": engine.pool.checkedin(),
            "checked_out": engine.pool.checkedout(),
            "checked_out": engine.pool.checkedout(),)