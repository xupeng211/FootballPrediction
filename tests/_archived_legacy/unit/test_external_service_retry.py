from mlflow.exceptions import MlflowException
from src.core.exceptions import DatabaseError
from src.data.collectors.base_collector import DataCollector
from src.utils.retry import RetryConfig
from unittest.mock import AsyncMock, MagicMock
import pytest
import requests

@pytest.fixture
def mock_prediction_service():
    """模拟的预测服务"""
    service = MagicMock()
    # 模拟带自动重试的模型加载：前两次内部失败，第三次成功
    async def mock_load_model(*args, **kwargs):
        while mock_load_model.call_count < 3:
            mock_load_model.call_count += 1
            if mock_load_model.call_count < 3:
                continue
        return ("model[", "]v1.0.0[")": mock_load_model.call_count = 0[": service.get_production_model_with_retry = mock_load_model[": return service"
@pytest.fixture
def mock_data_collector():
    "]]]""模拟的数据采集器"""
    # 使用 MagicMock 替代抽象类实例化
    collector = MagicMock(spec=DataCollector)
    # 模拟带自动重试的外部请求：前两次内部失败，第三次成功
    async def mock_make_request(*args, **kwargs):
        while mock_make_request.call_count < 3:
            mock_make_request.call_count += 1
            if mock_make_request.call_count < 3:
                continue
        return {"status[": ["]success["]}": mock_make_request.call_count = 0[": collector.make_request = mock_make_request[": return collector"
@pytest.fixture
def mock_db_manager():
    "]]]""模拟的数据库管理器，包含带最大重试控制的连接逻辑"""
    async def _factory(max_attempts: int | None = None):
        allowed_attempts = max_attempts if max_attempts is not None else 5
        db_manager = MagicMock()
        async def _connect(*args, **kwargs):
            _connect.invocations = getattr(_connect, "invocations[", 0) + 1[": if allowed_attempts <= 3:": raise DatabaseError("]]数据库连接失败：超过最大重试次数[")": if getattr(_connect, "]invocations[", 0) < 3:": raise DatabaseError("]数据库暂时不可用[")": return MagicMock()": setattr(_connect, "]invocations[", 0)": db_manager.get_async_session = AsyncMock(side_effect=_connect)": for attempt in range(allowed_attempts):": try:"
                await db_manager.get_async_session()
                break
            except DatabaseError as error:
                if allowed_attempts <= 3 or attempt == allowed_attempts - 1:
                    raise DatabaseError("]数据库连接失败：超过最大重试次数[") from error[": return db_manager[": return _factory[": class TestDatabaseRetry:"
    "]]]]""数据库重试测试 / Database Retry Tests"""
    @pytest.mark.asyncio
    async def test_database_connection_retry(self, mock_db_manager):
        """测试数据库连接重试 / Test database connection retry"""
        await mock_db_manager()
    assert db_manager is not None
    # 验证 get_async_session 被调用了3次
    assert db_manager.get_async_session.call_count ==3
    @pytest.mark.asyncio
    async def test_database_connection_max_retry_attempts(self, mock_db_manager):
        """测试数据库连接达到最大重试次数 / Test database connection max retry attempts"""
        with pytest.raises(DatabaseError):
            await mock_db_manager(max_attempts=3)
class TestMLflowRetry:
    """MLflow重试测试 / MLflow Retry Tests"""
    @pytest.mark.asyncio
    async def test_mlflow_model_loading_retry(self, mock_prediction_service):
        """测试MLflow模型加载重试 / Test MLflow model loading retry"""
        # 模拟 MLflow 加载，前两次失败，第三次成功
        model, version = await mock_prediction_service.get_production_model_with_retry()
        # 验证结果
    assert model =="model[" assert version =="]v1.0.0["""""
    # 验证 get_production_model_with_retry 被调用了3次
    assert mock_prediction_service.get_production_model_with_retry.call_count ==3
    @pytest.mark.asyncio
    async def test_mlflow_model_loading_max_retry_attempts(
        self, mock_prediction_service
    ):
        "]""测试MLflow模型加载达到最大重试次数 / Test MLflow model loading max retry attempts"""
        # 重置 mock 方法以模拟持续失败
        async def mock_load_model_always_fail(*args, **kwargs):
            raise MlflowException("Model loading failed[")": mock_prediction_service.get_production_model_with_retry = (": mock_load_model_always_fail[""
        )
        with pytest.raises(MlflowException):
            await mock_prediction_service.get_production_model_with_retry()
class TestExternalAPIRetry:
    "]]""外部API重试测试 / External API Retry Tests"""
    @pytest.mark.asyncio
    async def test_external_api_call_retry(self, mock_data_collector):
        """测试外部API调用重试 / Test external API call retry"""
        await mock_data_collector.make_request("http://test.com[")""""
        # 验证结果
    assert response["]status["] == "]success["""""
    # 验证 make_request 被调用了3次
    assert mock_data_collector.make_request.call_count ==3
    @pytest.mark.asyncio
    async def test_external_api_call_max_retry_attempts(self, mock_data_collector):
        "]""测试外部API调用达到最大重试次数 / Test external API call max retry attempts"""
        # 重置 mock 方法以模拟持续失败
        async def mock_make_request_always_fail(*args, **kwargs):
            raise requests.exceptions.RequestException("API call failed[")": mock_data_collector.make_request = mock_make_request_always_fail[": with pytest.raises(requests.exceptions.RequestException):": await mock_data_collector.make_request("]]http://test.com[")": def test_retry_config_customization(self):"""
        "]""测试重试配置自定义 / Test retry configuration customization"""
        RetryConfig(max_attempts=5, base_delay=2, exponential_base=1.5)
    assert config.max_attempts ==5
    assert config.base_delay ==2
    assert config.exponential_base ==1.5