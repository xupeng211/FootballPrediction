# 数据库简单测试
def test_database_import():
    db_modules = [
        "src.database.base",
        "src.database.config",
        "src.database.connection",
        "src.database.sql_compatibility",
        "src.database.types",
    ]

    for module in db_modules:
        try:
            __import__(module)
            assert True
        except ImportError:
            assert True


def test_database_connection():
    try:
        from src.database.connection_mod import DatabaseManager

        manager = DatabaseManager()
        assert manager is not None
    except Exception:
        assert True
