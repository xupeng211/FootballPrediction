"""
FootballPrediction V7.0 数据库连接工具
提供统一的数据库连接管理和操作
"""

import psycopg2
import logging
from contextlib import contextmanager
from typing import Dict, Any, List, Optional, Union
from psycopg2.extras import RealDictCursor, DictCursor
from psycopg2.pool import SimpleConnectionPool

from src.core.config import get_config

logger = logging.getLogger(__name__)

class DatabaseManager:
    """数据库管理器"""

    def __init__(self, config=None):
        self.config = config or get_config()
        self.db_config = self.config.database
        self.pool = None
        self.available = False
        self._initialize()

    def _initialize(self):
        """初始化数据库连接池"""
        try:
            # 创建连接池
            self.pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                host=self.db_config.host,
                port=self.db_config.port,
                database=self.db_config.name,
                user=self.db_config.user,
                password=self.db_config.password
            )
            self.available = True
            logger.info("✅ 数据库连接池初始化成功")

        except Exception as e:
            logger.warning(f"⚠️ 数据库连接失败，仅使用文件模式: {e}")
            self.available = False

    def is_available(self) -> bool:
        """检查数据库是否可用"""
        return self.available and self.pool is not None

    @contextmanager
    def get_connection(self, dict_cursor: bool = True):
        """获取数据库连接的上下文管理器"""
        if not self.is_available():
            raise ConnectionError("数据库不可用")

        conn = None
        try:
            conn = self.pool.getconn()
            if dict_cursor:
                cursor_class = RealDictCursor
            else:
                cursor_class = DictCursor
            cursor = conn.cursor(cursor_factory=cursor_class)
            yield conn, cursor
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                self.pool.putconn(conn)

    def execute_query(self, query: str, params: tuple = None, fetch: str = 'all') -> Optional[Union[List[Dict], Dict]]:
        """执行查询"""
        if not self.is_available():
            logger.warning("数据库不可用，跳过查询")
            return None

        try:
            with self.get_connection() as (conn, cursor):
                cursor.execute(query, params)

                if fetch == 'all':
                    return [dict(row) for row in cursor.fetchall()]
                elif fetch == 'one':
                    result = cursor.fetchone()
                    return dict(result) if result else None
                elif fetch == 'none':
                    conn.commit()
                    return None

        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            return None

    def execute_many(self, query: str, data_list: List[tuple]) -> bool:
        """批量执行"""
        if not self.is_available():
            logger.warning("数据库不可用，跳过批量插入")
            return False

        try:
            with self.get_connection(dict_cursor=False) as (conn, cursor):
                cursor.executemany(query, data_list)
                conn.commit()
                logger.info(f"✅ 批量插入成功: {len(data_list)} 条记录")
                return True

        except Exception as e:
            logger.error(f"批量执行失败: {e}")
            return False

    def create_table_if_not_exists(self, table_name: str, create_sql: str) -> bool:
        """创建表（如果不存在）"""
        if not self.is_available():
            return False

        try:
            with self.get_connection() as (conn, cursor):
                cursor.execute(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = %s
                    );
                """, (table_name,))

                table_exists = cursor.fetchone()[0]

                if not table_exists:
                    cursor.execute(create_sql)
                    conn.commit()
                    logger.info(f"✅ 表 {table_name} 创建成功")
                else:
                    logger.info(f"ℹ️ 表 {table_name} 已存在")

                return True

        except Exception as e:
            logger.error(f"创建表失败 {table_name}: {e}")
            return False

    def get_table_info(self, table_name: str) -> Optional[Dict[str, Any]]:
        """获取表信息"""
        if not self.is_available():
            return None

        try:
            # 获取列信息
            columns_query = """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position;
            """

            columns = self.execute_query(columns_query, (table_name,))

            # 获取行数
            count_query = f"SELECT COUNT(*) as count FROM {table_name}"
            count_result = self.execute_query(count_query, fetch='one')

            return {
                'table_name': table_name,
                'columns': columns or [],
                'row_count': count_result['count'] if count_result else 0
            }

        except Exception as e:
            logger.error(f"获取表信息失败 {table_name}: {e}")
            return None

    def close(self):
        """关闭连接池"""
        if self.pool:
            self.pool.closeall()
            logger.info("🔒 数据库连接池已关闭")


# 便利函数
def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例"""
    return DatabaseManager()

@contextmanager
def database_connection(dict_cursor: bool = True):
    """便利的数据库连接上下文管理器"""
    db = get_db_manager()
    if db.is_available():
        with db.get_connection(dict_cursor) as (conn, cursor):
            yield conn, cursor
    else:
        raise ConnectionError("数据库不可用")