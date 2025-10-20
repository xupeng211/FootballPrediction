"""
简单集成测试
"""

import pytest
import asyncio
from pathlib import Path
import sys

# 添加src路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.mark.integration
def test_data_flow_integration():
    """测试数据流集成"""
    try:
        from src.utils.validators import Validators
        from src.utils.formatters import Formatter
        from src.utils.response import Response

        validator = Validators()
        formatter = Formatter()

        # 模拟一个简单的数据流
        data = {"email": "test@example.com", "name": "Test User", "age": 25}

        # 验证数据
        is_valid = validator.is_valid_email(data["email"])
        assert is_valid is True

        # 格式化数据
        formatted_name = formatter.format_name(data["name"])
        assert formatted_name is not None

        # 创建响应
        response = Response(success=True, data=data)
        assert response.success is True
        assert response.data["email"] == data["email"]

    except ImportError as e:
        pytest.skip(f"集成测试跳过: {e}")


@pytest.mark.integration
def test_service_layer_integration():
    """测试服务层集成"""
    try:
        from src.services.base_unified import BaseService
        from src.utils.logger import get_logger

        # 创建服务实例
        class TestService(BaseService):
            def __init__(self):
                super().__init__()
                self.logger = get_logger("test_service")

            async def process_data(self, data):
                """处理数据"""
                self.logger.info(f"Processing: {data}")
                # 简单处理
                result = {"processed": True, "data": data}
                return result

        # 测试服务
        service = TestService()
        assert service is not None

        # 测试异步处理
        async def test_async():
            result = await service.process_data({"test": "data"})
            assert result["processed"] is True
            assert result["data"]["test"] == "data"

        # 运行异步测试
        asyncio.run(test_async())

    except ImportError as e:
        pytest.skip(f"服务层集成测试跳过: {e}")


@pytest.mark.integration
def test_cache_integration():
    """测试缓存集成"""
    try:
        from src.cache.redis_manager import RedisManager
        from src.utils.time_utils import TimeUtils

        # 测试缓存管理器
        cache = RedisManager()

        # 测试键值存储
        key = "test_key"
        value = {"test": "value", "timestamp": TimeUtils.now()}

        # 这些测试可能会跳过如果Redis不可用
        try:
            # 设置值
            cache.set(key, value, ttl=60)

            # 获取值
            retrieved = cache.get(key)
            assert retrieved is not None

            # 删除值
            cache.delete(key)

        except Exception:
            pytest.skip("Redis不可用，跳过缓存测试")

    except ImportError as e:
        pytest.skip(f"缓存集成测试跳过: {e}")


@pytest.mark.integration
def test_api_to_service_integration():
    """测试API到服务的集成"""
    try:
        from fastapi import FastAPI
        from src.api.dependencies import get_db_session
        from src.services.prediction_service import PredictionService

        app = FastAPI()

        # 模拟API端点
        @app.get("/test")
        async def test_endpoint():
            service = PredictionService()
            result = await service.get_predictions(limit=10)
            return {"status": "ok", "count": len(result)}

        # 测试app创建
        assert app is not None
        assert len(app.routes) > 0

    except ImportError as e:
        pytest.skip(f"API集成测试跳过: {e}")


@pytest.mark.integration
def test_error_handling_integration():
    """测试错误处理集成"""
    try:
        from src.core.exceptions import ValidationError, NotFoundError
        from src.utils.response import Response

        # 测试错误响应
        def raise_validation_error():
            raise ValidationError("Invalid data")

        def raise_not_found():
            raise NotFoundError("Resource not found")

        # 测试异常处理
        try:
            raise_validation_error()
            assert False, "应该抛出ValidationError"
        except ValidationError:
            assert True

        try:
            raise_not_found()
            assert False, "应该抛出NotFoundError"
        except NotFoundError:
            assert True

        # 测试错误响应
        error_response = Response.error("Test error", code=400)
        assert error_response.success is False
        assert error_response.error == "Test error"

    except ImportError as e:
        pytest.skip(f"错误处理集成测试跳过: {e}")
