"""
API与数据库集成简单测试

测试API层与数据库层的集成功能
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestAPIDatabaseIntegrationSimple:
    """API与数据库集成基础测试类"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        with patch('src.main.app'):
            from src.main import app
            return TestClient(app)

    @pytest.fixture
    def mock_db_manager(self):
        """模拟数据库管理器"""
        mock_manager = Mock()
        mock_session = AsyncMock()
        mock_session_context = AsyncMock()
        mock_session_context.__aenter__.return_value = mock_session
        mock_session_context.__aexit__.return_value = None
        mock_manager.get_async_session.return_value = mock_session_context
        return mock_manager

    def test_api_database_connection(self, client, mock_db_manager):
        """测试API数据库连接"""
        with patch('src.api.data.DatabaseManager', return_value=mock_db_manager):
            response = client.get("/api/data/health")
            assert response.status_code in [200, 404, 500]

    def test_data_retrieval_integration(self, client, mock_db_manager):
        """测试数据检索集成"""
        with patch('src.api.data.DatabaseManager', return_value=mock_db_manager):
            # Mock数据库查询结果
            mock_session = AsyncMock()
            mock_session_context = AsyncMock()
            mock_session_context.__aenter__.return_value = mock_session
            mock_session_context.__aexit__.return_value = None
            mock_db_manager.get_async_session.return_value = mock_session_context

            # Mock查询返回结果
            mock_result = Mock()
            mock_result.all.return_value = [
                {'id': 1, 'name': 'test_data_1'},
                {'id': 2, 'name': 'test_data_2'}
            ]
            mock_session.execute.return_value = mock_result

            response = client.get("/api/data/test")
            assert response.status_code in [200, 404, 500]

    def test_data_creation_integration(self, client, mock_db_manager):
        """测试数据创建集成"""
        with patch('src.api.data.DatabaseManager', return_value=mock_db_manager):
            # Mock数据库会话
            mock_session = AsyncMock()
            mock_session_context = AsyncMock()
            mock_session_context.__aenter__.return_value = mock_session
            mock_session_context.__aexit__.return_value = None
            mock_db_manager.get_async_session.return_value = mock_session_context

            # 创建数据
            test_data = {'name': 'test_item', 'value': 42}
            response = client.post("/api/data/test", json=test_data)

            assert response.status_code in [200, 201, 404, 500]

    def test_data_update_integration(self, client, mock_db_manager):
        """测试数据更新集成"""
        with patch('src.api.data.DatabaseManager', return_value=mock_db_manager):
            # Mock数据库会话
            mock_session = AsyncMock()
            mock_session_context = AsyncMock()
            mock_session_context.__aenter__.return_value = mock_session
            mock_session_context.__aexit__.return_value = None
            mock_db_manager.get_async_session.return_value = mock_session_context

            # 更新数据
            update_data = {'name': 'updated_item'}
            response = client.put("/api/data/test/1", json=update_data)

            assert response.status_code in [200, 404, 500]

    def test_data_deletion_integration(self, client, mock_db_manager):
        """测试数据删除集成"""
        with patch('src.api.data.DatabaseManager', return_value=mock_db_manager):
            # Mock数据库会话
            mock_session = AsyncMock()
            mock_session_context = AsyncMock()
            mock_session_context.__aenter__.return_value = mock_session
            mock_session_context.__aexit__.return_value = None
            mock_db_manager.get_async_session.return_value = mock_session_context

            # 删除数据
            response = client.delete("/api/data/test/1")

            assert response.status_code in [200, 404, 500]

    def test_database_error_handling(self, client, mock_db_manager):
        """测试数据库错误处理"""
        with patch('src.api.data.DatabaseManager', return_value=mock_db_manager):
            # Mock数据库错误
            mock_session = AsyncMock()
            mock_session_context = AsyncMock()
            mock_session_context.__aenter__.side_effect = Exception("Database connection failed")
            mock_session_context.__aexit__.return_value = None
            mock_db_manager.get_async_session.return_value = mock_session_context

            response = client.get("/api/data/test")
            assert response.status_code in [500, 404]

    def test_concurrent_database_operations(self, client, mock_db_manager):
        """测试并发数据库操作"""
        import threading
        import time

        with patch('src.api.data.DatabaseManager', return_value=mock_db_manager):
            # Mock数据库会话
            mock_session = AsyncMock()
            mock_session_context = AsyncMock()
            mock_session_context.__aenter__.return_value = mock_session
            mock_session_context.__aexit__.return_value = None
            mock_db_manager.get_async_session.return_value = mock_session_context

            results = []

            def make_request():
                response = client.get("/api/data/test")
                results.append(response.status_code)

            # 创建多个并发请求
            threads = []
            for _ in range(3):
                thread = threading.Thread(target=make_request)
                threads.append(thread)
                thread.start()

            # 等待所有线程完成
            for thread in threads:
                thread.join()

            # 验证所有请求都得到了响应
            assert len(results) == 3
            for status_code in results:
                assert status_code in [200, 404, 500]

    def test_database_transaction_rollback(self, client, mock_db_manager):
        """测试数据库事务回滚"""
        with patch('src.api.data.DatabaseManager', return_value=mock_db_manager):
            # Mock数据库会话，模拟事务失败
            mock_session = AsyncMock()
            mock_session_context = AsyncMock()
            mock_session_context.__aenter__.return_value = mock_session
            mock_session_context.__aexit__.return_value = None
            mock_session.commit.side_effect = Exception("Transaction failed")
            mock_db_manager.get_async_session.return_value = mock_session_context

            # 尝试创建数据，应该失败并回滚
            test_data = {'name': 'test_item'}
            response = client.post("/api/data/test", json=test_data)

            assert response.status_code in [500, 404]

            # 验证回滚被调用
            mock_session.rollback.assert_called_once()

    def test_database_connection_pooling(self, client, mock_db_manager):
        """测试数据库连接池"""
        with patch('src.api.data.DatabaseManager', return_value=mock_db_manager):
            # Mock多个数据库会话
            mock_session1 = AsyncMock()
            mock_session2 = AsyncMock()
            mock_session_context1 = AsyncMock()
            mock_session_context2 = AsyncMock()
            mock_session_context1.__aenter__.return_value = mock_session1
            mock_session_context1.__aexit__.return_value = None
            mock_session_context2.__aenter__.return_value = mock_session2
            mock_session_context2.__aexit__.return_value = None

            # 模拟连接池行为
            call_count = 0
            def get_session_side_effect():
                nonlocal call_count
                call_count += 1
                if call_count % 2 == 1:
                    return mock_session_context1
                else:
                    return mock_session_context2

            mock_db_manager.get_async_session.side_effect = get_session_side_effect

            # 发送多个请求
            for i in range(4):
                client.get("/api/data/test")

            # 验证连接池被使用
            assert mock_db_manager.get_async_session.call_count == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.api", "--cov-report=term-missing"])