"""
设计模式实现的单元测试
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.patterns.observer import (
    MetricsObserver,
    LoggingObserver,
    AlertingObserver,
    ObservableService,
    PredictionService,
)
from src.patterns.decorator import (
    DatabaseService,
    LoggingDecorator,
    RetryDecorator,
    MetricsDecorator,
    ValidationDecorator,
    async_retry,
    async_log,
)
from src.patterns.adapter import (
    FootballApiAdapter,
    WeatherApiAdapter,
    OddsApiAdapter,
    AdapterFactory,
    UnifiedDataCollector,
    ExternalData,
)


class TestObserverPattern:
    """观察者模式测试"""

    @pytest.mark.asyncio
    async def test_metrics_observer(self):
        """测试指标观察者"""
        observer = MetricsObserver()
        service = ObservableService("TestService")

        service.attach(observer)

        # 模拟事件
        await service.notify("test_event", {"data": "test"})

        metrics = observer.get_metrics()
        assert metrics["total_events"] == 1
        assert metrics["event_counts"]["test_event"] == 1
        assert "test_event" in metrics["last_events"]

    @pytest.mark.asyncio
    async def test_logging_observer(self):
        """测试日志观察者"""
        observer = LoggingObserver()
        service = ObservableService("TestService")

        service.attach(observer)

        # 测试日志记录
        await service.notify("error_event", {"error": "test error"})

        # 验证观察者仍然在工作
        assert observer.get_name() == "LoggingObserver"

    @pytest.mark.asyncio
    async def test_alerting_observer(self):
        """测试告警观察者"""
        observer = AlertingObserver()
        observer.add_alert_rule("error_event", "always", "Test error occurred")

        service = ObservableService("TestService")
        service.attach(observer)

        # 触发告警
        await service.notify("error_event", {"error": "test error"})

        alerts = observer.get_alert_history()
        assert len(alerts) == 1
        assert alerts[0]["message"] == "Test error occurred"
        assert alerts[0]["event_type"] == "error_event"

    @pytest.mark.asyncio
    async def test_prediction_service_with_observers(self):
        """测试预测服务与观察者集成"""
        service = PredictionService()
        metrics_observer = MetricsObserver()
        logging_observer = LoggingObserver()

        service.attach(metrics_observer)
        service.attach(logging_observer)

        # 模拟服务操作
        result = await service.predict_match(123)

        assert result["match_id"] == 123
        assert result["prediction"] == "home_win"

        # 验证指标收集
        metrics = metrics_observer.get_metrics()
        assert metrics["total_events"] > 0

    @pytest.mark.asyncio
    async def test_observer_detach(self):
        """测试移除观察者"""
        observer = MetricsObserver()
        service = ObservableService("TestService")

        service.attach(observer)
        assert len(service.get_observers()) == 1

        service.detach(observer)
        assert len(service.get_observers()) == 0


class TestDecoratorPattern:
    """装饰器模式测试"""

    @pytest.mark.asyncio
    async def test_logging_decorator(self):
        """测试日志装饰器"""
        base_service = DatabaseService("test")
        decorated_service = LoggingDecorator(base_service)

        result = await decorated_service.execute("SELECT * FROM test")

        assert result["query"] == "SELECT * FROM test"
        assert result["result"] == "success"

    @pytest.mark.asyncio
    async def test_retry_decorator_success(self):
        """测试重试装饰器 - 成功情况"""
        base_service = DatabaseService("test")
        decorated_service = RetryDecorator(base_service, max_retries=3)

        result = await decorated_service.execute("SELECT * FROM test")

        assert result["result"] == "success"

    @pytest.mark.asyncio
    async def test_retry_decorator_failure(self):
        """测试重试装饰器 - 失败情况"""
        base_service = DatabaseService("test")
        decorated_service = RetryDecorator(base_service, max_retries=2)

        with pytest.raises(Exception, match="Database error"):
            await decorated_service.execute("SELECT error")

    @pytest.mark.asyncio
    async def test_metrics_decorator(self):
        """测试指标装饰器"""
        base_service = DatabaseService("test")
        decorated_service = MetricsDecorator(base_service)

        # 执行多次
        await decorated_service.execute("SELECT * FROM test1")
        await decorated_service.execute("SELECT * FROM test2")

        metrics = decorated_service.get_metrics()
        assert metrics["calls"] == 2
        assert metrics["errors"] == 0
        assert metrics["avg_time"] > 0

    @pytest.mark.asyncio
    async def test_validation_decorator_valid_input(self):
        """测试验证装饰器 - 有效输入"""
        base_service = DatabaseService("test")

        def validator(q):
            if not isinstance(q, str) or len(q) == 0:
                raise ValueError("Query cannot be empty")

        decorated_service = ValidationDecorator(base_service, validators=[validator])

        result = await decorated_service.execute("SELECT * FROM test")

        assert result["result"] == "success"

    @pytest.mark.asyncio
    async def test_validation_decorator_invalid_input(self):
        """测试验证装饰器 - 无效输入"""
        base_service = DatabaseService("test")

        def validator(q):
            if not isinstance(q, str) or len(q) == 0:
                raise ValueError("Query cannot be empty")

        decorated_service = ValidationDecorator(base_service, validators=[validator])

        with pytest.raises(ValueError, match="Invalid input"):
            await decorated_service.execute("")

    @pytest.mark.asyncio
    async def test_decorator_chain(self):
        """测试装饰器链"""
        base_service = DatabaseService("test")

        # 创建装饰器链
        service = LoggingDecorator(base_service)
        service = MetricsDecorator(service)
        service = RetryDecorator(service)

        def validator(q):
            if not isinstance(q, str) or len(q) == 0:
                raise ValueError("Query cannot be empty")

        service = ValidationDecorator(service, validators=[validator])

        result = await service.execute("SELECT * FROM test")

        assert result["result"] == "success"

        # 验证指标装饰器收集了数据
        if hasattr(service, "get_metrics"):
            metrics = service.get_metrics()
            assert metrics["calls"] == 1

    @pytest.mark.asyncio
    async def test_async_retry_decorator(self):
        """测试异步重试装饰器"""
        attempt_count = 0

        @async_retry(max_retries=3, delay=0.01)
        async def failing_function():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise Exception("Temporary failure")
            return "success"

        result = await failing_function()
        assert result == "success"
        assert attempt_count == 3

    @pytest.mark.asyncio
    async def test_async_log_decorator(self):
        """测试异步日志装饰器"""

        @async_log()
        async def test_function(x):
            return x * 2

        result = await test_function(5)
        assert result == 10


class TestAdapterPattern:
    """适配器模式测试"""

    @pytest.fixture
    def mock_football_api(self):
        """模拟足球API"""
        api = MagicMock()
        api.fetch_data = AsyncMock(
            return_value={
                "id": 123,
                "name": "Test Match",
                "homeTeam": {"name": "Team A"},
                "awayTeam": {"name": "Team B"},
                "score": {"fullTime": {"home": 2, "away": 1}},
                "status": "FINISHED",
                "competition": {"name": "Premier League"},
                "lastUpdated": "2024-01-01T12:00:00Z",
            }
        )
        return api

    @pytest.fixture
    def mock_weather_api(self):
        """模拟天气API"""
        api = MagicMock()
        api.fetch_data = AsyncMock(
            return_value={
                "main": {
                    "temp": 20.5,
                    "feels_like": 18.3,
                    "temp_min": 15.2,
                    "temp_max": 25.1,
                    "humidity": 65,
                    "pressure": 1013,
                },
                "weather": [{"main": "Clear", "description": "clear sky"}],
                "wind": {"speed": 3.5, "deg": 180},
                "rain": {},
                "visibility": 10000,
                "clouds": {"all": 0},
            }
        )
        return api

    @pytest.fixture
    def mock_odds_api(self):
        """模拟赔率API"""
        api = MagicMock()
        api.fetch_data = AsyncMock(
            return_value={
                "id": 123,
                "sport_key": "soccer_epl",
                "sport_title": "Premier League",
                "commence_time": "2024-01-01T15:00:00Z",
                "home_team": "Team A",
                "away_team": "Team B",
                "bookmakers": [
                    {
                        "title": "Bookmaker1",
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {"name": "Team A", "price": 2.10},
                                    {"name": "Draw", "price": 3.40},
                                    {"name": "Team B", "price": 3.20},
                                ],
                            }
                        ],
                    }
                ],
            }
        )
        return api

    @pytest.mark.asyncio
    async def test_football_adapter_transform_data(self, mock_football_api):
        """测试足球适配器数据转换"""
        adapter = FootballApiAdapter(mock_football_api)

        raw_data = await mock_football_api.fetch_data("matches", {"id": 123})
        transformed = adapter.transform_data(raw_data)

        assert transformed["id"] == 123
        assert transformed["name"] == "Test Match"
        assert transformed["home_team"]["name"] == "Team A"
        assert transformed["away_team"]["name"] == "Team B"
        assert transformed["score"]["home"] == 2
        assert transformed["score"]["away"] == 1
        assert transformed["status"] == "FINISHED"

    @pytest.mark.asyncio
    async def test_weather_adapter_transform_data(self, mock_weather_api):
        """测试天气适配器数据转换"""
        adapter = WeatherApiAdapter(mock_weather_api)

        raw_data = await mock_weather_api.fetch_data("weather", {"q": "London"})
        transformed = adapter.transform_data(raw_data)

        assert transformed["temperature"]["current"] == 20.5
        assert transformed["humidity"] == 65
        assert transformed["weather"]["main"] == "Clear"
        assert transformed["wind"]["speed"] == 3.5

    @pytest.mark.asyncio
    async def test_odds_adapter_transform_data(self, mock_odds_api):
        """测试赔率适配器数据转换"""
        adapter = OddsApiAdapter(mock_odds_api)

        raw_data = await mock_odds_api.fetch_data("odds", {"match": 123})
        transformed = adapter.transform_data(raw_data)

        assert transformed["match_id"] == 123
        assert transformed["home_team"] == "Team A"
        assert transformed["away_team"] == "Team B"
        assert "Bookmaker1" in transformed["bookmakers"]
        assert "h2h" in transformed["bookmakers"]["Bookmaker1"]
        assert transformed["bookmakers"]["Bookmaker1"]["h2h"]["Team A"]["price"] == 2.10

    @pytest.mark.asyncio
    async def test_adapter_factory(self, mock_football_api):
        """测试适配器工厂"""
        adapter = AdapterFactory.create_adapter("football", mock_football_api)

        assert isinstance(adapter, FootballApiAdapter)

        with pytest.raises(ValueError, match="Unknown adapter type"):
            AdapterFactory.create_adapter("unknown", mock_football_api)

    @pytest.mark.asyncio
    async def test_unified_data_collector(
        self, mock_football_api, mock_weather_api, mock_odds_api
    ):
        """测试统一数据收集器"""
        collector = UnifiedDataCollector()

        # 添加适配器
        football_adapter = FootballApiAdapter(mock_football_api)
        weather_adapter = WeatherApiAdapter(mock_weather_api)
        odds_adapter = OddsApiAdapter(mock_odds_api)

        collector.add_adapter("football", football_adapter)
        collector.add_adapter("weather", weather_adapter)
        collector.add_adapter("odds", odds_adapter)

        # 收集比赛数据
        match_data = await collector.collect_match_data(123)

        assert "football" in match_data
        assert "odds" in match_data
        assert isinstance(match_data["football"], ExternalData)
        assert isinstance(match_data["odds"], ExternalData)

        # 收集天气数据
        weather_data = await collector.collect_weather_data("London", datetime.now())
        assert isinstance(weather_data, ExternalData)
        assert weather_data.source == "weather_api"
