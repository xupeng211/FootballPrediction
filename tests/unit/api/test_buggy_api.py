"""
测试有问题的 API 代码，演示 FastAPI Query 参数错误和异步 Mock 对象错误
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.buggy_api import router


class TestBuggyAPI:
    """测试有问题的 API"""

    def setup_method(self):
        """设置测试环境"""
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)

    def test_buggy_query_parameter_error(self):
        """测试 FastAPI Query 参数错误 - 会导致 TypeError"""
        # 这个测试会暴露 Query 参数的问题
        response = self.client.get("/buggy_query?limit=abc")  # 传入非数字字符串
        # 由于缺少类型注解和验证，这可能导致 TypeError: int() argument must be...
        assert response.status_code in [200, 422]  # 可能返回验证错误

    @pytest.mark.asyncio
    async def test_buggy_async_mock_error(self):
        """测试修复后的异步 Mock 对象 - 现在正确使用 AsyncMock"""

        # ✅ 修复后的 Mock 用法 - 正确使用 AsyncMock
        with patch("src.api.buggy_api.service") as mock_service:
            # 修复1：使用 AsyncMock 而不是普通 Mock
            mock_service.get_status = AsyncMock(return_value="fixed_mocked_status")

            from src.api.buggy_api import buggy_async

            # 修复2：正确 await 异步方法
            result = await buggy_async()

            # 验证结果
            assert result == {"status": "fixed_mocked_status"}

            # 验证 mock 被正确调用
            mock_service.get_status.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_correct_async_mock_usage(self):
        """演示正确的异步 Mock 用法"""

        # ✅ 正确的 AsyncMock 用法
        with patch("src.api.buggy_api.service") as mock_service:
            # 正确1：使用 AsyncMock
            mock_service.get_status = AsyncMock(return_value="correct_mocked_status")

            from src.api.buggy_api import buggy_async

            # 正确2：正确 await 异步方法
            result = await buggy_async()

            # 验证结果
            assert result == {"status": "correct_mocked_status"}

            # 验证 mock 被正确调用
            mock_service.get_status.assert_awaited_once()


class TestFixedAPI:
    """测试修复后的 API"""

    def setup_method(self):
        """设置测试环境"""
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)

    def test_fixed_query_parameter(self):
        """测试修复后的 Query 参数"""
        response = self.client.get("/fixed_query?limit=20")
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 20
        assert data["type"] == "int"

    def test_fixed_query_parameter_validation(self):
        """测试 Query 参数验证"""
        # 测试超出范围的值
        response = self.client.get("/fixed_query?limit=0")  # 小于最小值
        assert response.status_code == 422  # 验证错误

        response = self.client.get("/fixed_query?limit=101")  # 大于最大值
        assert response.status_code == 422

    def test_fixed_query_parameter_default(self):
        """测试默认值"""
        response = self.client.get("/fixed_query")  # 不传参数
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10  # 默认值

    @pytest.mark.asyncio
    async def test_fixed_async_mock(self):
        """测试修复后的异步 Mock"""
        from src.api.buggy_api import buggy_async

        result = await buggy_async()
        assert result == {"status": "real_status"}

    def test_buggy_query_parameter_success(self):
        """测试修复后的 buggy_query 成功情况"""
        response = self.client.get("/buggy_query?limit=50")
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 50
        assert data["type"] == "int"

    def test_buggy_query_parameter_validation(self):
        """测试 buggy_query 参数验证"""
        # 测试无效参数
        response = self.client.get("/buggy_query?limit=abc")
        assert response.status_code == 422  # 应该返回验证错误

        response = self.client.get("/buggy_query?limit=0")
        assert response.status_code == 422

        response = self.client.get("/buggy_query?limit=101")
        assert response.status_code == 422
