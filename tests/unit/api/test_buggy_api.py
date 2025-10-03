"""
Buggy API测试
测试覆盖src/api/buggy_api.py中的所有路由
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from fastapi import HTTPException

from src.api.buggy_api import router


@pytest.mark.asyncio
class TestBuggyEndpoints:
    """测试有问题的API端点"""

    @patch('src.api.buggy_api.get_async_session')
    async def test_get_buggy_data_success(self, mock_get_session):
        """测试获取错误数据成功"""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        # 模拟查询结果
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            {"id": 1, "data": "test"}
        ]
        mock_session.execute.return_value = mock_result

        from src.api.buggy_api import get_buggy_data
        result = await get_buggy_data()

        assert result is not None
        assert isinstance(result, list)

    @patch('src.api.buggy_api.get_async_session')
    async def test_get_buggy_data_database_error(self, mock_get_session):
        """测试获取错误数据时数据库错误"""
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_session.execute.side_effect = Exception("Database error")

        from src.api.buggy_api import get_buggy_data

        with pytest.raises(HTTPException) as exc_info:
            await get_buggy_data()

        assert exc_info.value.status_code == 500

    async def test_buggy_operation_zero_division(self):
        """测试零除错误"""
        from src.api.buggy_api import buggy_operation

        with pytest.raises(ZeroDivisionError):
            buggy_operation(1, 0)

    async def test_buggy_operation_success(self):
        """测试有问题的操作成功"""
        from src.api.buggy_api import buggy_operation
        result = buggy_operation(10, 2)
        assert result == 5

    async def test_buggy_validation_none_input(self):
        """测试验证None输入"""
        from src.api.buggy_api import buggy_validation

        with pytest.raises(AttributeError):
            buggy_validation(None)

    async def test_buggy_validation_success(self):
        """测试验证成功"""
        from src.api.buggy_api import buggy_validation
        mock_obj = MagicMock()
        mock_obj.attribute = "test"
        result = buggy_validation(mock_obj)
        assert result == "test"


class TestRouterConfiguration:
    """测试路由配置"""

    def test_router_exists(self):
        """测试路由器存在"""
        assert router is not None
        assert hasattr(router, 'routes')

    def test_router_tags(self):
        """测试路由标签"""
        assert router.tags == ["buggy"]

    def test_router_has_endpoints(self):
        """测试路由器有端点"""
        route_count = len(list(router.routes))
        assert route_count > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])