"""
异步 Mock 对象修复示例

演示如何正确修复异步 Mock 对象错误，避免 RuntimeWarning: coroutine was never awaited
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest


class ExampleService:
    """示例服务类，包含异步和同步方法"""

    async def get_status(self) -> str:
        """异步方法"""
        await asyncio.sleep(0.1)
        return "finished"

    def get_name(self) -> str:
        """同步方法"""
        return "example_service"

    async def process_data(self, data: str) -> dict:
        """异步数据处理方法"""
        await asyncio.sleep(0.1)
        return {"processed": data, "status": "completed"}


# ❌ 错误的 Mock 用法 - 会导致 RuntimeWarning: coroutine was never awaited
def test_wrong_async_mock():
    """错误的异步 Mock 用法示例"""
    ExampleService()

    # 错误1：对异步方法使用普通 Mock
    # service.get_status = Mock(return_value="finished")  # 错误！

    # 错误2：AsyncMock 但没有正确 await
    # service.get_status = AsyncMock(return_value="finished")
    # result = service.get_status()  # 错误：没有 await，会产生 RuntimeWarning

    pass


# ✅ 正确的异步 Mock 用法
@pytest.mark.asyncio
async def test_correct_async_mock():
    """正确的异步 Mock 用法示例"""
    service = ExampleService()

    # ✅ 正确：对异步方法使用 AsyncMock
    service.get_status = AsyncMock(return_value="finished")

    # ✅ 正确：调用时使用 await
    result = await service.get_status()
    assert result == "finished"

    # ✅ 正确：验证调用
    service.get_status.assert_called_once()


@pytest.mark.asyncio
async def test_mixed_sync_async_mock():
    """混合同步和异步方法的正确 Mock 用法"""
    service = ExampleService()

    # ✅ 正确：同步方法使用普通 Mock
    service.get_name = Mock(return_value="mocked_service")

    # ✅ 正确：异步方法使用 AsyncMock
    service.get_status = AsyncMock(return_value="mocked_status")
    service.process_data = AsyncMock(return_value={"mocked": True})

    # ✅ 正确：同步方法直接调用
    name = service.get_name()
    assert name == "mocked_service"

    # ✅ 正确：异步方法使用 await
    status = await service.get_status()
    assert status == "mocked_status"

    data_result = await service.process_data("test")
    assert data_result == {"mocked": True}


@pytest.mark.asyncio
async def test_patch_with_async_mock():
    """使用 patch 和 AsyncMock 的正确用法"""

    # ✅ 正确：patch 异步方法并使用 AsyncMock
    with patch.object(
        ExampleService, "get_status", new_callable=AsyncMock
    ) as mock_get_status:
        mock_get_status.return_value = "patched_status"

        service = ExampleService()
        result = await service.get_status()

        assert result == "patched_status"
        mock_get_status.assert_called_once()


@pytest.mark.asyncio
async def test_database_session_mock():
    """数据库会话的正确 Mock 用法示例"""

    # ✅ 正确：模拟数据库会话和结果
    mock_session = AsyncMock()
    mock_result = AsyncMock()

    # 模拟查询结果
    mock_result.scalar_one_or_none = AsyncMock(return_value={"id": 1, "name": "test"})
    mock_result.scalars = Mock()
    mock_result.scalars.return_value.all = Mock(return_value=[{"id": 1}, {"id": 2}])

    # 模拟会话执行
    mock_session.execute = AsyncMock(return_value=mock_result)

    # ✅ 正确：使用 await 调用异步方法
    result = await mock_session.execute("SELECT * FROM table")
    single_result = await result.scalar_one_or_none()

    assert single_result == {"id": 1, "name": "test"}
    mock_session.execute.assert_called_once()


# ✅ 正确的测试夹具设置
@pytest.fixture
async def mock_service():
    """正确设置异步服务的测试夹具"""
    service = ExampleService()

    # 正确设置 AsyncMock
    service.get_status = AsyncMock(return_value="fixture_status")
    service.process_data = AsyncMock(return_value={"fixture": True})

    return service


@pytest.mark.asyncio
async def test_with_fixture(mock_service):
    """使用测试夹具的正确用法"""
    # ✅ 正确：使用 await 调用异步 mock 方法
    status = await mock_service.get_status()
    data = await mock_service.process_data("test")

    assert status == "fixture_status"
    assert data == {"fixture": True}


if __name__ == "__main__":
    # 运行示例测试
    asyncio.run(test_correct_async_mock())
    print("✅ 异步 Mock 测试通过！")
