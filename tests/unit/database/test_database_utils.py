"""数据库工具测试"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers import create_sqlite_memory_engine, create_sqlite_sessionmaker


@pytest.mark.skip(reason="需要重构数据库集成测试 - 异步fixture问题")
class TestDatabaseUtils:
    """数据库工具测试 - 使用内存 SQLite"""
    pass
