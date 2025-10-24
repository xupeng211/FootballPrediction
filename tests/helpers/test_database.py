"""数据库相关测试工具"""

from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def create_sqlite_memory_engine(
    *, echo: bool = False, future: bool = True, **kwargs: Any
):
    """生成内存 SQLite Engine"""

    url = "sqlite+pysqlite:///:memory:"
    return create_engine(url, echo=echo, future=future, **kwargs)


def create_sqlite_sessionmaker(*, engine=None, **kwargs: Any):
    """基于内存 Engine 输出 Session 工厂"""

    engine = engine or create_sqlite_memory_engine()
    return sessionmaker(
        bind=engine, autoflush=False, autocommit=False, future=True, **kwargs
    )


__all__ = [
    "create_sqlite_memory_engine",
    "create_sqlite_sessionmaker",
]
