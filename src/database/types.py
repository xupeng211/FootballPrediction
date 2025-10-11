"""
数据库类型适配模块

提供跨数据库兼容的数据类型定义，特别是JSONB与SQLite的兼容性支持。
"""

import json
from typing import Any, Union

from sqlalchemy import JSON, Text, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB


class SQLiteCompatibleJSONB(TypeDecorator):
    """
    SQLite兼容的JSONB类型

    在PostgreSQL中使用JSONB，在SQLite中自动转换为TEXT存储。
    提供统一的JSON操作接口。
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """根据数据库方言加载对应的实现"""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        else:
            # 对于SQLite和其他数据库，使用TEXT
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Any, dialect) -> Union[str, Any]:
        """处理绑定参数（Python值 -> 数据库值）"""
        if value is None:
            return None

        if dialect.name == "postgresql":
            # PostgreSQL可以直接处理dict/list等JSON类型
            return value
        else:
            # SQLite需要序列化为JSON字符串
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)
            elif isinstance(value, str):
                # 如果已经是字符串，验证是否为有效JSON
                try:
                    json.loads(value)
                    return value
                except (json.JSONDecodeError, TypeError):
                    # 如果不是有效JSON，包装成字符串
                    return json.dumps(value, ensure_ascii=False)
            else:
                return json.dumps(value, ensure_ascii=False)

    def process_result_value(self, value: Any, dialect) -> Any:
        """处理结果值（数据库值 -> Python值）"""
        if value is None:
            return None

        if dialect.name == "postgresql":
            # PostgreSQL的JSONB会自动反序列化
            return value
        else:
            # SQLite存储的是JSON字符串，需要反序列化
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            return value


class CompatibleJSON(TypeDecorator):
    """
    跨数据库兼容的JSON类型

    自动根据数据库类型选择最佳的JSON存储方式。
    """

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """根据数据库方言加载对应的实现"""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSON())
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value: Any, dialect) -> Union[str, Any]:
        """处理绑定参数"""
        if value is None:
            return None

        if dialect.name == "postgresql":
            return value
        else:
            # SQLite使用JSON字符串存储
            return json.dumps(value, ensure_ascii=False) if value is not None else None

    def process_result_value(self, value: Any, dialect) -> Any:
        """处理结果值"""
        if value is None:
            return None

        if dialect.name == "postgresql":
            return value
        else:
            # SQLite反序列化JSON字符串
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            return value


# 便捷的类型别名
JsonType = SQLiteCompatibleJSONB()
JsonbType = SQLiteCompatibleJSONB()
CompatJsonType = CompatibleJSON()

# 传统方式的兼容定义（向后兼容）
JsonTypeCompat = JSONB().with_variant(JSON(), "sqlite")


def get_json_type(use_jsonb: bool = True) -> TypeDecorator:
    """
    获取兼容的JSON类型

    Args:
        use_jsonb: 是否优先使用JSONB（仅在PostgreSQL中有效）

    Returns:
        TypeDecorator: 兼容的JSON类型
    """
    if use_jsonb:
        return SQLiteCompatibleJSONB()
    else:
        return CompatibleJSON()


# 导出类型定义
__all__ = [
    "SQLiteCompatibleJSONB",
    "CompatibleJSON",
    "JsonType",
    "JsonbType",
    "CompatJsonType",
    "JsonTypeCompat",
    "get_json_type",
]
