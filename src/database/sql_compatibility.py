"""
SQL兼容性工具模块

提供跨数据库的SQL语法兼容性支持，主要解决SQLite和PostgreSQL之间的语法差异。
"""

import logging
from typing import Union

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
            sqlite_unit = unit_map.get(interval_unit, interval_unit)
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
    """兼容性查询构建器"""

    def __init__(self, db_type: str):
        self.db_type = db_type
        self.helper = SQLCompatibilityHelper()

    def build_error_statistics_query(self, hours: int = 24) -> str:
        """构建错误统计查询"""
        time_filter = self.helper.get_interval_sql(
            self.db_type,
            base_time="created_at" if self.db_type == "sqlite" else "NOW()",
            interval_value=hours,
            interval_unit="hour",
        )

        if self.db_type == "sqlite":
            # SQLite版本：需要修改比较逻辑
            return f"""
                SELECT COUNT(*) as total_errors
                FROM error_logs
                WHERE created_at >= datetime('now', '-{hours} hours')
            """
        else:
            # PostgreSQL版本
            return f"""
                SELECT COUNT(*) as total_errors
                FROM error_logs
                WHERE created_at >= {time_filter}
            """

    def build_task_errors_query(self, hours: int = 24) -> str:
        """构建任务错误统计查询"""
        if self.db_type == "sqlite":
            return f"""
                SELECT task_name, COUNT(*) as error_count
                FROM error_logs
                WHERE created_at >= datetime('now', '-{hours} hours')
                GROUP BY task_name
                ORDER BY error_count DESC
            """
        else:
            time_filter = self.helper.get_interval_sql(
                self.db_type, interval_value=hours, interval_unit="hour"
            )
            return f"""
                SELECT task_name, COUNT(*) as error_count
                FROM error_logs
                WHERE created_at >= {time_filter}
                GROUP BY task_name
                ORDER BY error_count DESC
            """

    def build_type_errors_query(self, hours: int = 24) -> str:
        """构建错误类型统计查询"""
        if self.db_type == "sqlite":
            return f"""
                SELECT error_type, COUNT(*) as error_count
                FROM error_logs
                WHERE created_at >= datetime('now', '-{hours} hours')
                GROUP BY error_type
                ORDER BY error_count DESC
            """
        else:
            time_filter = self.helper.get_interval_sql(
                self.db_type, interval_value=hours, interval_unit="hour"
            )
            return f"""
                SELECT error_type, COUNT(*) as error_count
                FROM error_logs
                WHERE created_at >= {time_filter}
                GROUP BY error_type
                ORDER BY error_count DESC
            """

    def build_cleanup_old_logs_query(self, days: int = 7) -> str:
        """构建清理旧日志查询"""
        if self.db_type == "sqlite":
            return f"""
                DELETE FROM error_logs
                WHERE created_at < datetime('now', '-{days} days')
            """
        else:
            time_filter = self.helper.get_interval_sql(
                self.db_type, interval_value=days, interval_unit="day"
            )
            return f"""
                DELETE FROM error_logs
                WHERE created_at < {time_filter}
            """

    def build_task_delay_query(self) -> str:
        """构建任务延迟查询"""
        if self.db_type == "sqlite":
            return """
                SELECT
                    task_name,
                    AVG((julianday('now') - julianday(created_at)) * 86400) as avg_delay_seconds
                FROM error_logs
                WHERE created_at >= datetime('now', '-1 hour')
                AND task_name IS NOT NULL
                GROUP BY task_name
            """
        else:
            return """
                SELECT
                    task_name,
                    AVG(EXTRACT(EPOCH FROM (NOW() - created_at))) as avg_delay_seconds
                FROM error_logs
                WHERE created_at >= NOW() - INTERVAL '1 hour'
                AND task_name IS NOT NULL
                GROUP BY task_name
            """


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
