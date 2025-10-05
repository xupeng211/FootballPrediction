"""
SQL兼容性工具模块

提供跨数据库的SQL语法兼容性支持，主要解决SQLite和PostgreSQL之间的语法差异。
"""

import logging
from typing import Any, Dict, Tuple, Union

from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


class SQLCompatibilityHelper:
    """SQL兼容性助手类"""

    @staticmethod
    def detect_database_type(engine_or_url: Union[Engine, AsyncEngine, str]) -> str:
        """
        检测数据库类型

        Args:
            engine_or_url: SQLAlchemy引擎或连接URL

        Returns:
            数据库类型: 'sqlite', 'postgresql', 'mysql' 等
        """
        if isinstance(engine_or_url, str):
            url = engine_or_url
        else:
            url = str(engine_or_url.url)

        if url.startswith("sqlite"):
            return "sqlite"
        elif url.startswith("postgresql"):
            return "postgresql"
        elif url.startswith("mysql"):
            return "mysql"
        else:
            return "unknown"

    @classmethod
    def get_interval_sql(
        cls,
        db_type: str,
        base_time: str = "NOW()",
        interval_value: int = 1,
        interval_unit: str = "hour",
    ) -> str:
        """
        生成跨数据库的时间间隔SQL

        Args:
            db_type: 数据库类型
            base_time: 基准时间（默认为NOW()）
            interval_value: 间隔值
            interval_unit: 间隔单位 (hour, day, minute等)

        Returns:
            兼容的时间间隔SQL字符串
        """
        if db_type == "postgresql":
            return f"{base_time} - INTERVAL '{interval_value} {interval_unit}'"
        elif db_type == "sqlite":
            # SQLite使用datetime函数
            unit_map = {
                "hour": "hours",
                "day": "days",
                "minute": "minutes",
                "second": "seconds",
            }
            sqlite_unit = unit_map.get(str(interval_unit), interval_unit)
            if base_time.upper() == "NOW()":
                base_time = "'now'"
            return f"datetime({base_time}, '-{interval_value} {sqlite_unit}')"
        else:
            # 默认使用PostgreSQL语法
            return f"{base_time} - INTERVAL '{interval_value} {interval_unit}'"

    @classmethod
    def get_epoch_extract_sql(cls, db_type: str, timestamp_expr: str) -> str:
        """
        生成跨数据库的时间戳提取SQL

        Args:
            db_type: 数据库类型
            timestamp_expr: 时间戳表达式

        Returns:
            兼容的EPOCH提取SQL
        """
        if db_type == "postgresql":
            return f"EXTRACT(EPOCH FROM {timestamp_expr})"
        elif db_type == "sqlite":
            # SQLite使用julianday函数计算秒数
            return f"((julianday({timestamp_expr}) - julianday('1970 - 01 - 01 00:00:00')) * 86400)"
        else:
            # 默认使用PostgreSQL语法
            return f"EXTRACT(EPOCH FROM {timestamp_expr})"

    @classmethod
    def get_time_diff_sql(cls, db_type: str, time1: str, time2: str) -> str:
        """
        生成跨数据库的时间差计算SQL（秒）

        Args:
            db_type: 数据库类型
            time1: 时间1（较新的时间）
            time2: 时间2（较旧的时间）

        Returns:
            兼容的时间差SQL
        """
        if db_type == "postgresql":
            return f"EXTRACT(EPOCH FROM ({time1} - {time2}))"
        elif db_type == "sqlite":
            return f"((julianday({time1}) - julianday({time2})) * 86400)"
        else:
            return f"EXTRACT(EPOCH FROM ({time1} - {time2}))"

    @classmethod
    def get_serial_primary_key_sql(cls, db_type: str, column_name: str = "id") -> str:
        """
        生成跨数据库的自增主键SQL

        Args:
            db_type: 数据库类型
            column_name: 列名

        Returns:
            兼容的主键定义SQL
        """
        if db_type == "postgresql":
            return f"{column_name} SERIAL PRIMARY KEY"
        elif db_type == "sqlite":
            return f"{column_name} INTEGER PRIMARY KEY AUTOINCREMENT"
        else:
            return f"{column_name} SERIAL PRIMARY KEY"

    @classmethod
    def get_current_timestamp_sql(cls, db_type: str) -> str:
        """
        生成跨数据库的当前时间戳SQL

        Args:
            db_type: 数据库类型

        Returns:
            兼容的当前时间戳SQL
        """
        if db_type == "postgresql":
            return "NOW()"
        elif db_type == "sqlite":
            return "datetime('now')"
        else:
            return "NOW()"

    @classmethod
    def create_error_logs_table_sql(cls, db_type: str) -> str:
        """
        生成创建error_logs表的兼容SQL

        Args:
            db_type: 数据库类型

        Returns:
            兼容的建表SQL
        """
        if db_type == "postgresql":
            return """
                CREATE TABLE IF NOT EXISTS error_logs (
                    id SERIAL PRIMARY KEY,
                    task_name VARCHAR(100) NOT NULL,
                    task_id VARCHAR(100),
                    error_type VARCHAR(100) NOT NULL,
                    error_message TEXT,
                    traceback TEXT,
                    retry_count INTEGER DEFAULT 0,
                    context_data TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """
        elif db_type == "sqlite":
            return """
                CREATE TABLE IF NOT EXISTS error_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name VARCHAR(100) NOT NULL,
                    task_id VARCHAR(100),
                    error_type VARCHAR(100) NOT NULL,
                    error_message TEXT,
                    traceback TEXT,
                    retry_count INTEGER DEFAULT 0,
                    context_data TEXT,
                    created_at TIMESTAMP DEFAULT (datetime('now'))
                );
            """
        else:
            # 默认PostgreSQL
            return cls.create_error_logs_table_sql("postgresql")


class CompatibleQueryBuilder:
    """兼容性查询构建器 - 使用参数化查询防止SQL注入"""

    def __init__(self, db_type: str):
        self.db_type = db_type
        self.helper = SQLCompatibilityHelper()

    def get_error_statistics_query(self, hours: int = 24) -> Tuple[str, dict]:
        """获取错误统计查询和参数"""
        if self.db_type == "sqlite":
            # SQLite版本：使用参数化查询
            query = """
                SELECT COUNT(*) as total_errors
                FROM error_logs
                WHERE created_at >= datetime('now', :hours_param || ' hours')
            """
            params = {"hours_param": f"-{hours}"}
        else:
            # PostgreSQL版本：使用参数化查询
            query = """
                SELECT COUNT(*) as total_errors
                FROM error_logs
                WHERE created_at >= NOW() - INTERVAL :hours_interval
            """
            params = {"hours_interval": f"{hours} hours"}

        return query.strip(), params

    def get_task_errors_query(self, hours: int = 24) -> Tuple[str, dict]:
        """获取任务错误统计查询和参数"""
        if self.db_type == "sqlite":
            query = """
                SELECT task_name, COUNT(*) as error_count
                FROM error_logs
                WHERE created_at >= datetime('now', :hours_param || ' hours')
                GROUP BY task_name
                ORDER BY error_count DESC
            """
            params = {"hours_param": f"-{hours}"}
        else:
            query = """
                SELECT task_name, COUNT(*) as error_count
                FROM error_logs
                WHERE created_at >= NOW() - INTERVAL :hours_interval
                GROUP BY task_name
                ORDER BY error_count DESC
            """
            params = {"hours_interval": f"{hours} hours"}

        return query.strip(), params

    def get_type_errors_query(self, hours: int = 24) -> Tuple[str, dict]:
        """获取错误类型统计查询和参数"""
        if self.db_type == "sqlite":
            query = """
                SELECT error_type, COUNT(*) as error_count
                FROM error_logs
                WHERE created_at >= datetime('now', :hours_param || ' hours')
                GROUP BY error_type
                ORDER BY error_count DESC
            """
            params = {"hours_param": f"-{hours}"}
        else:
            query = """
                SELECT error_type, COUNT(*) as error_count
                FROM error_logs
                WHERE created_at >= NOW() - INTERVAL :hours_interval
                GROUP BY error_type
                ORDER BY error_count DESC
            """
            params = {"hours_interval": f"{hours} hours"}

        return query.strip(), params

    def get_cleanup_old_logs_query(self, days: int = 7) -> Tuple[str, dict]:
        """获取清理旧日志查询和参数"""
        if self.db_type == "sqlite":
            query = """
                DELETE FROM error_logs
                WHERE created_at < datetime('now', :days_param || ' days')
            """
            params = {"days_param": f"-{days}"}
        else:
            query = """
                DELETE FROM error_logs
                WHERE created_at < NOW() - INTERVAL :days_interval
            """
            params = {"days_interval": f"{days} days"}

        return query.strip(), params

    def get_task_delay_query(self) -> Tuple[str, dict]:
        """获取任务延迟查询和参数"""
        if self.db_type == "sqlite":
            query = """
                SELECT
                    task_name,
                    AVG((julianday('now') - julianday(created_at)) * 86400) as avg_delay_seconds
                FROM error_logs
                WHERE created_at >= datetime('now', '-1 hour')
                AND task_name IS NOT NULL
                GROUP BY task_name
            """
            params: Dict[str, Any] = {}
        else:
            query = """
                SELECT
                    task_name,
                    AVG(EXTRACT(EPOCH FROM (NOW() - created_at))) as avg_delay_seconds
                FROM error_logs
                WHERE created_at >= NOW() - INTERVAL '1 hour'
                AND task_name IS NOT NULL
                GROUP BY task_name
            """
            params = {}

        return query.strip(), params

    # 兼容性方法 - 保持向后兼容，但不推荐使用
    def build_error_statistics_query(self, hours: int = 24) -> str:
        """构建错误统计查询（已弃用，使用get_error_statistics_query）"""
        logger.warning(
            "build_error_statistics_query is deprecated, use get_error_statistics_query instead"
        )
        query, _ = self.get_error_statistics_query(hours)
        return query

    def build_task_errors_query(self, hours: int = 24) -> str:
        """构建任务错误统计查询（已弃用，使用get_task_errors_query）"""
        logger.warning("build_task_errors_query is deprecated, use get_task_errors_query instead")
        query, _ = self.get_task_errors_query(hours)
        return query

    def build_type_errors_query(self, hours: int = 24) -> str:
        """构建错误类型统计查询（已弃用，使用get_type_errors_query）"""
        logger.warning("build_type_errors_query is deprecated, use get_type_errors_query instead")
        query, _ = self.get_type_errors_query(hours)
        return query

    def build_cleanup_old_logs_query(self, days: int = 7) -> str:
        """构建清理旧日志查询（已弃用，使用get_cleanup_old_logs_query）"""
        logger.warning(
            "build_cleanup_old_logs_query is deprecated, use get_cleanup_old_logs_query instead"
        )
        query, _ = self.get_cleanup_old_logs_query(days)
        return query

    def build_task_delay_query(self) -> str:
        """构建任务延迟查询（已弃用，使用get_task_delay_query）"""
        logger.warning("build_task_delay_query is deprecated, use get_task_delay_query instead")
        query, _ = self.get_task_delay_query()
        return query


def get_db_type_from_engine(engine) -> str:
    """从SQLAlchemy引擎获取数据库类型"""
    try:
        return SQLCompatibilityHelper.detect_database_type(engine)
    except Exception as e:
        logger.warning(f"无法检测数据库类型: {e}")
        return "postgresql"  # 默认值


def create_compatible_query_builder(engine) -> CompatibleQueryBuilder:
    """创建兼容性查询构建器"""
    db_type = get_db_type_from_engine(engine)
    return CompatibleQueryBuilder(db_type)
