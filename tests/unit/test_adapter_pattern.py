"""
适配器模式单元测试
Unit Tests for Adapter Pattern

测试适配器模式的各个组件。
Tests all components of the adapter pattern.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch, MagicMock

from src.adapters.base import (
    Adaptee,
    Target,
    Adapter,
    AdapterStatus,
    DataTransformer,
    CompositeAdapter,
    AsyncAdapter,
    RetryableAdapter,
    CachedAdapter,
)
from src.adapters.football import (
    FootballApiAdaptee,
    ApiFootballAdaptee,
    FootballDataTransformer,
    FootballApiAdapter,
    ApiFootballAdapter,
    CompositeFootballAdapter,
    FootballMatch,
    FootballTeam,
    MatchStatus,
)
from src.adapters.factory import (
    AdapterFactory,
    AdapterConfig,
    AdapterGroupConfig,
    AdapterBuilder,
)
from src.adapters.registry import (
    AdapterRegistry,
    RegistryStatus,
)


class TestAdapterBase:
    """测试适配器基类"""

    @pytest.fixture
    def mock_adaptee(self):
        """模拟被适配者"""
        adaptee = Mock(spec=Adaptee)
        adaptee.get_data = AsyncMock(return_value={"data": "test"})
        adaptee.send_data = AsyncMock(return_value={"result": "success"})
        return adaptee

    @pytest.fixture
    def concrete_adapter(self, mock_adaptee):
        """具体适配器"""

        class TestAdapter(Adapter):
            async def _initialize(self):
                pass

            async def _cleanup(self):
                pass

            async def _request(self, *args, **kwargs):
                return await self.adaptee.get_data(*args, **kwargs)

            async def _health_check(self):
                pass

        return TestAdapter(mock_adaptee, name="test_adapter")

    @pytest.mark.asyncio
    async def test_adapter_initialization(self, concrete_adapter):
        """测试适配器初始化"""
        await concrete_adapter.initialize()
        assert concrete_adapter.status == AdapterStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_adapter_cleanup(self, concrete_adapter):
        """测试适配器清理"""
        await concrete_adapter.initialize()
        await concrete_adapter.cleanup()
        assert concrete_adapter.status == AdapterStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_adapter_request(self, concrete_adapter):
        """测试适配器请求"""
        await concrete_adapter.initialize()
        result = await concrete_adapter.request()
        assert result == {"data": "test"}
        assert concrete_adapter.metrics["total_requests"] == 1
        assert concrete_adapter.metrics["successful_requests"] == 1

    @pytest.mark.asyncio
    async def test_adapter_request_failure(self, concrete_adapter):
        """测试适配器请求失败"""
        concrete_adapter.adaptee.get_data = AsyncMock(
            side_effect=Exception("Test error")
        )
        await concrete_adapter.initialize()

        with pytest.raises(Exception):
            await concrete_adapter.request()

        assert concrete_adapter.metrics["total_requests"] == 1
        assert concrete_adapter.metrics["failed_requests"] == 1
        assert concrete_adapter.last_error == "Test error"

    @pytest.mark.asyncio
    async def test_adapter_health_check(self, concrete_adapter):
        """测试适配器健康检查"""
        await concrete_adapter.initialize()
        health = await concrete_adapter.health_check()
        assert health["adapter"] == "test_adapter"
        assert health["status"] == "healthy"

    def test_adapter_metrics(self, concrete_adapter):
        """测试适配器指标"""
        metrics = concrete_adapter.get_metrics()
        assert "name" in metrics
        assert "status" in metrics
        assert "total_requests" in metrics
        assert "success_rate" in metrics

    def test_adapter_reset_metrics(self, concrete_adapter):
        """测试重置适配器指标"""
        concrete_adapter.metrics["total_requests"] = 10
        concrete_adapter.reset_metrics()
        assert concrete_adapter.metrics["total_requests"] == 0

    @pytest.mark.asyncio
    async def test_composite_adapter(self, mock_adaptee):
        """测试复合适配器"""
        composite = CompositeAdapter(name="composite_test")

        # 添加适配器
        adapter1 = Mock(spec=Adapter)
        adapter1.status = AdapterStatus.ACTIVE
        adapter1.request = AsyncMock(return_value="result1")
        adapter1.get_metrics.return_value = {"total_requests": 1}

        adapter2 = Mock(spec=Adapter)
        adapter2.status = AdapterStatus.INACTIVE
        adapter2.request = AsyncMock(return_value="result2")

        composite.add_adapter("adapter1", adapter1, priority=1)
        composite.add_adapter("adapter2", adapter2, priority=2)

        await composite.initialize()

        result = await composite.request()
        assert result == "result1"

        # 获取所有指标
        all_metrics = composite.get_all_metrics()
        assert all_metrics["total_adapters"] == 2
        assert all_metrics["active_adapters"] == 1

    @pytest.mark.asyncio
    async def test_retryable_adapter(self, mock_adaptee):
        """测试可重试适配器"""
        # 前两次失败，第三次成功
        mock_adaptee.get_data = AsyncMock(
            side_effect=[Exception("Fail 1"), Exception("Fail 2"), {"data": "success"}]
        )

        class TestRetryableAdapter(RetryableAdapter):
            async def _initialize(self):
                pass

            async def _cleanup(self):
                pass

            async def _request(self, *args, **kwargs):
                return await self.adaptee.get_data(*args, **kwargs)

            async def _health_check(self):
                pass

        adapter = TestRetryableAdapter(
            mock_adaptee, name="retryable_test", max_retries=3, retry_delay=0.01
        )

        await adapter.initialize()
        result = await adapter.request()
        assert result == {"data": "success"}

    @pytest.mark.asyncio
    async def test_cached_adapter(self, mock_adaptee):
        """测试缓存适配器"""
        call_count = 0

        async def get_data(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return {"data": f"call_{call_count}"}

        mock_adaptee.get_data = get_data

        class TestCachedAdapter(CachedAdapter):
            async def _initialize(self):
                pass

            async def _cleanup(self):
                pass

            async def _request(self, *args, **kwargs):
                return await self.adaptee.get_data(*args, **kwargs)

            async def _health_check(self):
                pass

        adapter = TestCachedAdapter(
            mock_adaptee, name="cached_test", cache_ttl=1.0, cache_size=10
        )

        await adapter.initialize()

        # 第一次调用
        result1 = await adapter.request("test_key")
        assert result1 == {"data": "call_1"}

        # 第二次调用应该从缓存获取
        result2 = await adapter.request("test_key")
        assert result2 == {"data": "call_1"}

        # 只调用了一次原始方法
        assert call_count == 1


class TestFootballAdapters:
    """测试足球适配器"""

    @pytest.fixture
    def api_football_adaptee(self):
        """API-Football被适配者"""
        with patch("aiohttp.ClientSession"):
            adaptee = ApiFootballAdaptee("test_key")
            return adaptee

    @pytest.fixture
    def football_transformer(self):
        """足球数据转换器"""
        return FootballDataTransformer("api-football")

    @pytest.fixture
    def sample_api_response(self):
        """示例API响应"""
        return {
            "fixture": {
                "id": 12345,
                "date": "2023-12-01T19:00:00+00:00",
                "status": {"short": "FT"},
                "venue": {"name": "Test Stadium"},
            },
            "teams": {
                "home": {"id": 111, "name": "Team A"},
                "away": {"id": 222, "name": "Team B"},
            },
            "goals": {"home": 2, "away": 1},
            "league": {"id": 333, "name": "Test League"},
        }

    def test_football_match_model(self):
        """测试足球比赛模型"""
        match = FootballMatch(
            id="123",
            home_team="Team A",
            away_team="Team B",
            match_date=datetime.now(),
            status=MatchStatus.LIVE,
            home_score=1,
            away_score=0,
        )
        assert match.id == "123"
        assert match.home_team == "Team A"
        assert match.away_team == "Team B"
        assert match.status == MatchStatus.LIVE

    @pytest.mark.asyncio
    async def test_football_data_transformer(self, sample_api_response):
        """测试足球数据转换器"""
        transformer = FootballDataTransformer("api-football")
        match = await transformer.transform(sample_api_response, target_type="match")

        assert isinstance(match, FootballMatch)
        assert match.id == "12345"
        assert match.home_team == "Team A"
        assert match.away_team == "Team B"
        assert match.home_score == 2
        assert match.away_score == 1

    def test_data_transformer_schemas(self):
        """测试数据转换器结构"""
        transformer = FootballDataTransformer("api-football")
        source_schema = transformer.get_source_schema()
        target_schema = transformer.get_target_schema()

        assert isinstance(source_schema, dict)
        assert isinstance(target_schema, dict)
        assert "fixture" in source_schema
        assert "id" in target_schema

    @pytest.mark.asyncio
    async def test_api_football_adapter(
        self, api_football_adaptee, football_transformer
    ):
        """测试API-Football适配器"""
        adapter = ApiFootballAdapter("test_key")

        # 模拟API响应
        mock_response = {
            "response": [
                {
                    "fixture": {
                        "id": 12345,
                        "date": "2023-12-01T19:00:00+00:00",
                        "status": {"short": "FT"},
                        "venue": {"name": "Test Stadium"},
                    },
                    "teams": {
                        "home": {"id": 111, "name": "Team A"},
                        "away": {"id": 222, "name": "Team B"},
                    },
                    "goals": {"home": 2, "away": 1},
                    "league": {"id": 333, "name": "Test League"},
                }
            ]
        }

        with patch.object(adapter.adaptee, "get_data", return_value=mock_response):
            matches = await adapter.get_matches()

            assert len(matches) == 1
            assert isinstance(matches[0], FootballMatch)
            assert matches[0].home_team == "Team A"
            assert matches[0].away_team == "Team B"

    @pytest.mark.asyncio
    async def test_composite_football_adapter(self):
        """测试复合适球适配器"""
        composite = CompositeFootballAdapter()

        # 创建模拟适配器
        adapter1 = Mock(spec=FootballApiAdapter)
        adapter1.status = AdapterStatus.ACTIVE
        adapter1.get_matches = AsyncMock(
            return_value=[FootballMatch("1", "Team A", "Team B")]
        )

        adapter2 = Mock(spec=FootballApiAdapter)
        adapter2.status = AdapterStatus.ACTIVE
        adapter2.get_matches = AsyncMock(
            return_value=[FootballMatch("2", "Team C", "Team D")]
        )

        composite.add_adapter(adapter1, is_primary=True)
        composite.add_adapter(adapter2)

        await composite.initialize()

        # 测试获取比赛
        await composite.get_matches()
        adapter1.get_matches.assert_called_once()

    @pytest.mark.asyncio
    async def test_composite_football_adapter_aggregation(self):
        """测试复合适球适配器数据聚合"""
        composite = CompositeFootballAdapter()

        # 创建模拟适配器
        adapter1 = Mock(spec=FootballApiAdapter)
        adapter1.status = AdapterStatus.ACTIVE
        adapter1.name = "adapter1"
        adapter1.get_matches = AsyncMock(
            return_value=[FootballMatch("1", "Team A", "Team B")]
        )

        adapter2 = Mock(spec=FootballApiAdapter)
        adapter2.status = AdapterStatus.ACTIVE
        adapter2.name = "adapter2"
        adapter2.get_matches = AsyncMock(
            return_value=[FootballMatch("2", "Team C", "Team D")]
        )

        composite.add_adapter(adapter1)
        composite.add_adapter(adapter2)

        await composite.initialize()

        # 测试数据聚合
        results = await composite.get_matches_aggregated()

        assert "adapter1" in results
        assert "adapter2" in results
        assert len(results["adapter1"]) == 1
        assert len(results["adapter2"]) == 1


class TestAdapterFactory:
    """测试适配器工厂"""

    def test_adapter_factory_registration(self):
        """测试适配器类型注册"""
        factory = AdapterFactory()

        # 注册自定义适配器
        class TestAdapter(Adapter):
            async def _initialize(self):
                pass

            async def _cleanup(self):
                pass

            async def _request(self, *args, **kwargs):
                return "test"

            async def _health_check(self):
                pass

        factory.register_adapter_type("test", TestAdapter)
        assert "test" in factory._adapter_types

        # 注销
        factory.unregister_adapter_type("test")
        assert "test" not in factory._adapter_types

    def test_adapter_factory_create(self):
        """测试创建适配器"""
        factory = AdapterFactory()

        config = AdapterConfig(
            name="test_adapter",
            adapter_type="api-football",
            parameters={"api_key": "test_key"},
        )

        with patch("src.adapters.football.ApiFootballAdapter") as mock_adapter:
            factory.create_adapter(config)
            mock_adapter.assert_called_once_with(api_key="test_key")

    def test_adapter_factory_parameter_resolution(self):
        """测试参数解析"""
        factory = AdapterFactory()

        # 模拟环境变量
        with patch.dict("os.environ", {"TEST_API_KEY": "env_key_value"}):
            parameters = {"api_key": "$TEST_API_KEY"}
            resolved = factory._resolve_parameters(parameters)
            assert resolved["api_key"] == "env_key_value"

    def test_adapter_factory_invalid_env_var(self):
        """测试无效环境变量"""
        factory = AdapterFactory()

        parameters = {"api_key": "$NONEXISTENT_VAR"}

        with pytest.raises(ValueError):
            factory._resolve_parameters(parameters)

    def test_adapter_builder(self):
        """测试适配器构建器"""
        builder = AdapterBuilder("api-football")

        config = (
            builder.with_name("test_builder")
            .with_parameter("api_key", "test_key")
            .with_priority(100)
            .with_cache(ttl=600)
            .with_retry(max_retries=5)
            .build()
        )

        assert config.name == "test_builder"
        assert config.adapter_type == "api-football"
        assert config.parameters["api_key"] == "test_key"
        assert config.priority == 100
        assert config.cache_config["ttl"] == 600
        assert config.retry_config["max_retries"] == 5

    def test_adapter_config_validation(self):
        """测试配置验证"""
        factory = AdapterFactory()

        # 有效配置
        valid_config = AdapterConfig(
            name="valid",
            adapter_type="api-football",
            parameters={"api_key": "test"},
        )
        errors = factory.validate_config(valid_config)
        assert len(errors) == 0

        # 无效配置
        invalid_config = AdapterConfig(
            name="invalid",
            adapter_type="nonexistent_type",
            parameters={"api_key": "test"},
        )
        errors = factory.validate_config(invalid_config)
        assert len(errors) > 0


class TestAdapterRegistry:
    """测试适配器注册表"""

    @pytest.fixture
    def registry(self):
        """适配器注册表"""
        return AdapterRegistry()

    @pytest.mark.asyncio
    async def test_registry_initialization(self, registry):
        """测试注册表初始化"""
        assert registry.status == RegistryStatus.INACTIVE

        await registry.initialize()
        assert registry.status == RegistryStatus.ACTIVE

        await registry.shutdown()
        assert registry.status == RegistryStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_adapter_registration(self, registry):
        """测试适配器注册"""
        await registry.initialize()

        config = AdapterConfig(
            name="test_adapter",
            adapter_type="api-football",
            parameters={"api_key": "test"},
        )

        with patch("src.adapters.football.ApiFootballAdapter") as mock_adapter_class:
            mock_adapter = Mock()
            mock_adapter.initialize = AsyncMock()
            mock_adapter_class.return_value = mock_adapter

            adapter = await registry.register_adapter(config)

            assert "test_adapter" in registry.adapters
            assert adapter == mock_adapter

    @pytest.mark.asyncio
    async def test_get_active_adapters(self, registry):
        """测试获取活跃适配器"""
        await registry.initialize()

        # 创建模拟适配器
        adapter1 = Mock(spec=Adapter)
        adapter1.status = AdapterStatus.ACTIVE

        adapter2 = Mock(spec=Adapter)
        adapter2.status = AdapterStatus.INACTIVE

        registry.adapters["active"] = adapter1
        registry.adapters["inactive"] = adapter2

        active_adapters = registry.get_active_adapters()
        assert len(active_adapters) == 1
        assert active_adapters[0] == adapter1

    @pytest.mark.asyncio
    async def test_health_status(self, registry):
        """测试健康状态"""
        await registry.initialize()

        # 创建模拟适配器
        adapter = Mock(spec=Adapter)
        adapter.status = AdapterStatus.ACTIVE
        adapter.get_metrics.return_value = {
            "total_requests": 10,
            "successful_requests": 9,
            "failed_requests": 1,
        }

        registry.adapters["test"] = adapter

        health_status = await registry.get_health_status()

        assert health_status["registry_status"] == "active"
        assert health_status["total_adapters"] == 1
        assert health_status["active_adapters"] == 1
        assert "test" in health_status["adapters"]

    @pytest.mark.asyncio
    async def test_find_best_adapter(self, registry):
        """测试查找最佳适配器"""
        await registry.initialize()

        # 创建模拟适配器
        adapter1 = Mock(spec=Adapter)
        adapter1.__class__.__name__ = "TestAdapter"
        adapter1.status = AdapterStatus.ACTIVE
        adapter1.get_metrics.return_value = {
            "total_requests": 10,
            "successful_requests": 8,
            "average_response_time": 0.1,
            "success_rate": 0.8,
        }

        adapter2 = Mock(spec=Adapter)
        adapter2.__class__.__name__ = "TestAdapter"
        adapter2.status = AdapterStatus.ACTIVE
        adapter2.get_metrics.return_value = {
            "total_requests": 10,
            "successful_requests": 9,
            "average_response_time": 0.2,
            "success_rate": 0.9,
        }

        registry.adapters["adapter1"] = adapter1
        registry.adapters["adapter2"] = adapter2

        best = await registry.find_best_adapter(
            adapter_type="TestAdapter", min_success_rate=0.7
        )

        # 应该返回成功率更高的adapter2
        assert best == adapter2

    def test_metrics_summary(self, registry):
        """测试指标摘要"""
        # 创建模拟适配器
        adapter1 = Mock(spec=Adapter)
        adapter1.__class__.__name__ = "TestAdapter1"
        adapter1.get_metrics.return_value = {
            "total_requests": 10,
            "successful_requests": 8,
            "failed_requests": 2,
        }

        adapter2 = Mock(spec=Adapter)
        adapter2.__class__.__name__ = "TestAdapter2"
        adapter2.get_metrics.return_value = {
            "total_requests": 5,
            "successful_requests": 5,
            "failed_requests": 0,
        }

        registry.adapters["adapter1"] = adapter1
        registry.adapters["adapter2"] = adapter2

        summary = registry.get_metrics_summary()

        assert summary["total_requests"] == 15
        assert summary["total_successful"] == 13
        assert summary["total_failed"] == 2
        assert summary["success_rate"] == 13 / 15
        assert summary["adapter_types"]["TestAdapter1"] == 1
        assert summary["adapter_types"]["TestAdapter2"] == 1
