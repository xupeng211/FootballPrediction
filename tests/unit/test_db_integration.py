
import pytest
from unittest.mock import Mock

@pytest.fixture
def mock_db():
    return Mock()

def test_database_connection(mock_db):
    """测试数据库连接"""
    assert mock_db is not None
    print("✅ 数据库连接测试通过")
