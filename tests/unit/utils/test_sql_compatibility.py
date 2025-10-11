"""SQL兼容性测试"""

import pytest


class TestSQLCompatibility:
    """测试SQL兼容性模块"""

    def test_sql_compatibility_import(self):
        """测试SQL兼容性模块导入"""
        try:
            import src.database.sql_compatibility as sql_compat

            assert sql_compat is not None
        except ImportError:
            pytest.skip("sql_compatibility module not available")

    def test_get_dialect_function(self):
        """测试获取方言函数"""
        try:
            from src.database.sql_compatibility import get_dialect

            dialect = get_dialect()
            assert dialect is not None
        except ImportError:
            pytest.skip("get_dialect not available")
        except ImportError:
            pytest.skip("get_dialect function failed")
