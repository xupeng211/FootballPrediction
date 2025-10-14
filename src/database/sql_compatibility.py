from typing import Any, Dict, List, Optional, Union
"""
sql_compatibility.py
sql_compatibility

SQL兼容性工具模块 - 为各种SQL操作提供兼容性支持
"""

from sqlalchemy.engine import Engine


class Compatibility:
    """SQL兼容性支持"""

    @staticmethod
    def normalize_column_name(name: str, dialect: str = "sqlite") -> str:
        """规范化列名"""
        return name.lower()

    @staticmethod
    def get_datetime_string(dialect: str = "sqlite") -> str:
        """获取日期时间字符串"""
        if dialect == "postgresql":
            return "NOW()"
        return "datetime('now')"


class CompatibleQueryBuilder:
    """兼容的SQL查询构建器"""

    def __init__(self, dialect: str = "sqlite"):
        self.dialect = dialect

    def build_insert_query(self, table: str, data: Dict[str, Any]) -> str:
        """构建插入查询"""
        columns = ", ".join(data.keys())
        placeholders = ", ".join([f":{key}" for key in data.keys()])
        return f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

    def build_update_query(
        self, table: str, data: Dict[str, Any], where_clause: str
    ) -> str:
        """构建更新查询"""
        set_clause = ", ".join([f"{key} = :{key}" for key in data.keys()])
        return f"UPDATE {table} SET {set_clause} WHERE {where_clause}"


class SQLCompatibilityHelper:
    """SQL兼容性助手"""

    def __init__(self, engine: Engine):
        self.engine = engine
        self.db_type = get_db_type_from_engine(engine)

    def get_query_builder(self) -> CompatibleQueryBuilder:
        """获取查询构建器"""
        return CompatibleQueryBuilder(self.db_type)

    def normalize_value(self, value: Any) -> Any:
        """规范化值"""
        return value


def get_db_type_from_engine(engine: Engine) -> str:
    """从引擎获取数据库类型"""
    dialect_name = engine.dialect.name.lower()
    if "postgresql" in dialect_name or "postgres" in dialect_name:
        return "postgresql"
    elif "mysql" in dialect_name:
        return "mysql"
    elif "sqlite" in dialect_name:
        return "sqlite"
    else:
        return dialect_name


# 创建默认实例
compatibility = Compatibility()

# 导出所有类
__all__ = [
    "compatibility",
    "Compatibility",
    "CompatibleQueryBuilder",
    "SQLCompatibilityHelper",
    "get_db_type_from_engine",
]
