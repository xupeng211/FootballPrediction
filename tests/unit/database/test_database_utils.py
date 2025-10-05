"""数据库工具测试"""

import pytest


@pytest.mark.skip(reason="需要重构数据库集成测试 - 异步fixture问题")
class TestDatabaseUtils:
    """数据库工具测试 - 使用内存 SQLite"""

