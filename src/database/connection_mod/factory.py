"""

"""







    """

    """


    """

    """


    """

    """


    """

    """


    """

    """



    """
    """


    """
    """



import os
from .config import DatabaseConfig
from .manager import DatabaseManager
from .multi_user_manager import MultiUserDatabaseManager

数据库管理器工厂
Database Manager Factory
提供数据库管理器的创建和初始化功能。
logger = get_logger(__name__)
# 全局实例
_database_manager: Optional[DatabaseManager] = None
_multi_user_manager: Optional[MultiUserDatabaseManager] = None
def get_database_manager() -> DatabaseManager:
    获取数据库管理器单例 / Get Database Manager Singleton
    Returns:
        DatabaseManager: 数据库管理器实例 / Database manager instance
    global _database_manager
    if _database_manager is None:
        _database_manager = DatabaseManager()
    return _database_manager
def get_multi_user_database_manager() -> MultiUserDatabaseManager:
    获取多用户数据库管理器单例 / Get Multi-User Database Manager Singleton
    Returns:
        MultiUserDatabaseManager: 多用户数据库管理器实例 / Multi-user database manager instance
    global _multi_user_manager
    if _multi_user_manager is None:
        _multi_user_manager = MultiUserDatabaseManager()
    return _multi_user_manager
def initialize_database(config: Optional[DatabaseConfig] = None) -> None:
    初始化数据库连接 / Initialize Database Connection
    Args:
        config (Optional[DatabaseConfig]): 数据库配置 / Database configuration
    manager = get_database_manager()
    manager.initialize(config)
    logger.info("数据库已初始化")
def initialize_multi_user_database(config: Optional[DatabaseConfig] = None) -> None:
    初始化多用户数据库连接 / Initialize Multi-User Database Connection
    Args:
        config (Optional[DatabaseConfig]): 数据库配置 / Database configuration
    manager = get_multi_user_database_manager()
    manager.initialize(config=config)
    logger.info("多用户数据库已初始化")
def initialize_test_database(config: Optional[DatabaseConfig] = None) -> None:
    初始化测试数据库 / Initialize Test Database
    Args:
        config (Optional[DatabaseConfig]): 测试数据库配置 / Test database configuration
    if config is None:
        # 默认测试数据库配置
        config = DatabaseConfig(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_TEST_NAME", "football_prediction_test"),
            username=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", ""),
        )
    manager = get_database_manager()
    manager.initialize(config)
    logger.info(f"测试数据库 {config.database} 已初始化")
def close_database() -> None:
    关闭数据库连接 / Close Database Connection
    global _database_manager
    if _database_manager:
        _database_manager.close()
        _database_manager = None
        logger.info("数据库连接已关闭")
def close_multi_user_database() -> None:
    关闭多用户数据库连接 / Close Multi-User Database Connection
    global _multi_user_manager
    if _multi_user_manager:
        _multi_user_manager.close()
        _multi_user_manager = None
        logger.info("多用户数据库连接已关闭")