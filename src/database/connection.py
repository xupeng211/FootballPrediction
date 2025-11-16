"""数据库连接管理模块 / Database Connection Management Module.

提供同步和异步的PostgreSQL数据库连接,会话管理和生命周期控制。
支持多用户权限分离的数据库连接管理。
集成重试机制以提高连接可靠性。

Provides synchronous and asynchronous PostgreSQL database connection, session management,
and lifecycle control. Supports multi-user permission-separated database connection management.
Integrates retry mechanisms to improve connection reliability.

⚠️ 注意：此文件已重构为模块化结构。
为了向后兼容性，这里保留了原始的导入接口.
建议使用：from src.database.connection import <class_name>

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
    DATABASE_RETRY_MAX_ATTEMPTS: 数据库重试最大尝试次数，默认5 / Database retry max attempts,
    default 5
    DATABASE_RETRY_BASE_DELAY: 数据库重试基础延迟秒数,
    默认1.0 / Database retry base delay in seconds,
    default 1.0

依赖 / Dependencies:
    - sqlalchemy: 数据库ORM框架 / Database ORM framework
    - psycopg2: PostgreSQL数据库适配器 / PostgreSQL database adapter
    - src.utils.retry: 重试机制 / Retry mechanism

重构历史 / Refactoring History:
    - 原始文件:1110行,
    包含所有数据库连接管理功能
    - 重构为模块化结构:
      - roles.py: 数据库角色定义
      - config.py: 数据库配置
      - manager.py: 数据库连接管理器
      - multi_user_manager.py: 多用户数据库管理器
      - factory.py: 数据库管理器工厂
      - sessions.py: 会话获取辅助函数
"""

# 从definitions模块导入所有内容（替代connection_mod）
from .definitions import (
    DatabaseManager,  # 角色定义; 核心管理器; 工厂函数; 会话获取
    DatabaseRole,
    MultiUserDatabaseManager,
    get_admin_session,
    get_async_admin_session,
    get_async_reader_session,
    get_async_session,
    get_async_writer_session,
    get_database_manager,
    get_db_session,
    get_multi_user_database_manager,
    get_reader_session,
    get_session,
    get_writer_session,
    initialize_database,
    initialize_multi_user_database,
    initialize_test_database,
)

# 重新导出以保持原始接口
__all__ = [
    # 角色定义
    "DatabaseRole",
    # 核心管理器
    "DatabaseManager",
    "MultiUserDatabaseManager",
    # 工厂函数
    "get_database_manager",
    "get_multi_user_database_manager",
    "initialize_database",
    "initialize_multi_user_database",
    "initialize_test_database",
    # 会话获取
    "get_db_session",
    "get_reader_session",
    "get_writer_session",
    "get_admin_session",
    "get_session",
    "get_async_session",
    "get_async_reader_session",
    "get_async_writer_session",
    "get_async_admin_session",
]

# 原始实现已移至 src/database/connection_mod/ 模块
# 此处保留仅用于向后兼容性
# 请使用新的模块化结构以获得更好的维护性

# 包含的所有功能:
# - DatabaseRole: 数据库用户角色枚举（READER,WRITER,ADMIN）
# - DatabaseManager: 单例数据库连接管理器
# - MultiUserDatabaseManager: 多用户数据库连接管理器
# - get_database_manager: 获取数据库管理器单例
# - initialize_database: 初始化数据库连接
# - 各种会话获取函数:get_db_session, get_reader_session等
