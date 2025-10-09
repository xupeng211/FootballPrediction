"""
数据库连接向后兼容性模块

为了保持向后兼容性，重新定义全局函数。
"""



# 从新的包结构导入

# 创建单例实例
_db_manager = DatabaseManager()

logger = logging.getLogger(__name__)

def get_db_session() -> Generator[Session, None, None]:
    """
    FastAPI依赖注入使用的同步数据库会话获取器
    """
    with _db_manager.get_session() as session:
        yield session


async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI依赖注入使用的异步数据库会话获取器
    """
    async with _db_manager.get_async_session() as session:
        yield session

# 导出所有兼容性函数
__all__ = [
    "get_async_db_session", contextmanager



    "get_db_session",
]