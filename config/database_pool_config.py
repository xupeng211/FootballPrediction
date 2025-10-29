"""
数据库连接池配置
生成时间: 2025-10-26 20:57:22
"""

# 连接池配置
CONNECTION_POOL_CONFIG = {
    "engine": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "football_prediction",
    "username": "postgres",
    "password": "password",
    "pool_size": 20,  # 连接池大小
    "max_overflow": 30,  # 最大溢出连接数
    "pool_timeout": 30,  # 连接超时时间
    "pool_recycle": 3600,  # 连接回收时间（1小时）
    "pool_pre_ping": True,  # 连接前检查
    "max_lifetime": 7200,  # 连接最大生存时间（2小时）
}


# 连接池使用示例
class DatabaseConnectionPool:
    def __init__(self):
        self.config = CONNECTION_POOL_CONFIG

    async def get_connection(self):
        """获取数据库连接"""
        # 这里应该是实际的连接池实现
        print("获取数据库连接...")

    async def release_connection(self, connection):
        """释放数据库连接"""
        # 这里应该是实际的连接释放实现
        print("释放数据库连接...")

    async def close_all(self):
        """关闭所有连接"""
        print("关闭所有连接...")
