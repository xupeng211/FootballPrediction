"""

"""



    """获取数据库会话 - 兼容测试代码"""

from src.database.connection import DatabaseManager

消费者工具函数
提供便捷的数据库会话管理函数。
def get_session():
    db_manager = DatabaseManager()
    return db_manager.get_async_session()