# TODO: Consider creating a fixture for 13 repeated Mock creations

# TODO: Consider creating a fixture for 13 repeated Mock creations

from unittest.mock import AsyncMock, MagicMock

"""
门面模式单元测试（简化版）
"""


import pytest

from src.patterns.facade_simple import (
    AnalyticsFacade,
    DataCollectionConfig,
    DataCollectionFacade,
    FacadeFactory,
    PredictionFacade,
    PredictionRequest,
    PredictionResult,
    SystemFacade,
)


@pytest.mark.unit
class TestPredictionFacade:
    """预测门面测试"""

    @pytest.fixture
    def mock_services(self):
        """模拟服务"""
        return {
            "match_service": MagicMock(),
            "prediction_service": MagicMock(),
            "data_collector": MagicMock(),
        }

    @pytest.fixture
    def prediction_facade(self, mock_services):
        """创建预测门面实例"""
        return PredictionFacade(mock_services)

    @pytest.mark.asyncio
    async def test_make_prediction(self, prediction_facade):
        """测试执行预测"""
        # 创建预测请求
        request = PredictionRequest(match_id=123, user_id=456, algorithm="ensemble")

        # 执行预测
        _result = await prediction_facade.make_prediction(request)

        # 验证结果
        assert isinstance(result, PredictionResult)
        assert _result.prediction["match_id"] == 123
        assert _result.prediction["algorithm"] == "ensemble"
        assert _result.confidence > 0
        assert len(result.recommendations) > 0

    @pytest.mark.asyncio
    async def test_make_prediction_with_value_assessment(self, prediction_facade):
        """测试带价值评估的预测"""
        request = PredictionRequest(match_id=123, user_id=456)
        _result = await prediction_facade.make_prediction(request)

        # 验证价值评估
        assert _result.value_assessment is not None
        assert "is_value" in result.value_assessment
        assert "value" in result.value_assessment

    @pytest.mark.asyncio
    async def test_get_prediction_history(self, prediction_facade):
        """测试获取预测历史"""
        history = await prediction_facade.get_prediction_history(user_id=456)

        # 验证
        assert len(history) == 1
        assert history[0]["id"] == 1
        assert history[0]["match_id"] == 123

    @pytest.mark.asyncio
    async def test_get_prediction_stats(self, prediction_facade):
        """测试获取预测统计"""
        _stats = await prediction_facade.get_prediction_stats(days=30)

        # 验证
        assert stats["period_days"] == 30
        assert stats["total_predictions"] == 100
        assert stats["correct_predictions"] == 65
        assert stats["accuracy"] == 65.0
        assert "profit_loss" in stats
        assert "roi" in stats

    @pytest.mark.asyncio
    async def test_make_prediction_match_not_found(self, prediction_facade):
        """测试比赛不存在的情况"""
        # 重写_get_match_data方法返回None
        prediction_facade._get_match_data = AsyncMock(return_value=None)

        request = PredictionRequest(match_id=999, user_id=456)

        # 验证抛出异常
        with pytest.raises(ValueError, match="Match 999 not found"):
            await prediction_facade.make_prediction(request)


class TestDataCollectionFacade:
    """数据收集门面测试"""

    @pytest.fixture
    def mock_services(self):
        """模拟服务"""
        return {
            "match_service": MagicMock(),
            "team_service": MagicMock(),
            "league_service": MagicMock(),
        }

    @pytest.fixture
    def data_facade(self, mock_services):
        """创建数据收集门面实例"""
        return DataCollectionFacade(mock_services)

    @pytest.mark.asyncio
    async def test_sync_all_data(self, data_facade):
        """测试同步所有数据"""
        # 创建配置
        _config = DataCollectionConfig(
            sources=["football", "odds"],
            refresh_interval=timedelta(hours=1),
            batch_size=50,
        )

        # 执行同步
        _result = await data_facade.sync_all_data(config)

        # 验证结果
        assert "matches" in result
        assert "teams" in result
        assert "leagues" in result
        assert "external" in result
        assert _result["matches"]["updated"] == 50
        assert _result["teams"]["updated"] == 20
        assert _result["leagues"]["updated"] == 5
        assert _result["external"]["updated"] == 100

    @pytest.mark.asyncio
    async def test_get_data_health(self, data_facade):
        """测试获取数据健康状态"""
        health = await data_facade.get_data_health()

        # 验证结果
        assert health["total_matches"] == 1000
        assert health["stale_matches"] == 50
        assert health["total_teams"] == 200
        assert health["teams_without_stats"] == 10
        assert health["overall_health"] in ["good", "warning", "poor", "error"]
        assert health["last_sync"] is not None


class TestAnalyticsFacade:
    """分析门面测试"""

    @pytest.fixture
    def mock_services(self):
        """模拟服务"""
        return {
            "match_service": MagicMock(),
            "prediction_service": MagicMock(),
            "user_service": MagicMock(),
        }

    @pytest.fixture
    def analytics_facade(self, mock_services):
        """创建分析门面实例"""
        return AnalyticsFacade(mock_services)

    @pytest.mark.asyncio
    async def test_generate_dashboard_data(self, analytics_facade):
        """测试生成仪表板数据"""
        dashboard = await analytics_facade.generate_dashboard_data(days=30)

        # 验证结果
        assert "overview" in dashboard
        assert "predictions" in dashboard
        assert "performance" in dashboard
        assert "trends" in dashboard
        assert "insights" in dashboard

        # 验证概览数据
        overview = dashboard["overview"]
        assert overview["total_predictions"] == 100
        assert overview["accuracy"] == 65.0
        assert overview["active_users"] == 25

        # 验证洞察
        insights = dashboard["insights"]
        assert len(insights) > 0
        assert isinstance(insights, list)

    @pytest.mark.asyncio
    async def test_generate_performance_report(self, analytics_facade):
        """测试生成性能报告"""
        report = await analytics_facade.generate_report("performance", {"period": "30d"})

        assert report["report_type"] == "performance"
        assert report["period"] == "30d"
        assert "data" in report

    @pytest.mark.asyncio
    async def test_generate_accuracy_report(self, analytics_facade):
        """测试生成准确率报告"""
        report = await analytics_facade.generate_report("accuracy", {"period": "7d"})

        assert report["report_type"] == "accuracy"
        assert report["period"] == "7d"

    @pytest.mark.asyncio
    async def test_generate_profitability_report(self, analytics_facade):
        """测试生成盈利报告"""
        report = await analytics_facade.generate_report("profitability", {"period": "90d"})

        assert report["report_type"] == "profitability"
        assert report["period"] == "90d"

    @pytest.mark.asyncio
    async def test_generate_report_invalid_type(self, analytics_facade):
        """测试生成无效类型的报告"""
        with pytest.raises(ValueError, match="Unknown report type"):
            await analytics_facade.generate_report("invalid", {})


class TestFacadeFactory:
    """门面工厂测试"""

    @pytest.mark.asyncio
    async def test_create_prediction_facade(self):
        """测试创建预测门面"""
        services = {"test": "value"}
        facade = FacadeFactory.create_prediction_facade(services)

        assert isinstance(facade, PredictionFacade)
        assert facade.services == services

    @pytest.mark.asyncio
    async def test_create_data_collection_facade(self):
        """测试创建数据收集门面"""
        services = {"test": "value"}
        facade = FacadeFactory.create_data_collection_facade(services)

        assert isinstance(facade, DataCollectionFacade)
        assert facade.services == services

    @pytest.mark.asyncio
    async def test_create_analytics_facade(self):
        """测试创建分析门面"""
        services = {"test": "value"}
        facade = FacadeFactory.create_analytics_facade(services)

        assert isinstance(facade, AnalyticsFacade)
        assert facade.services == services


class TestSystemFacade:
    """系统门面测试"""

    @pytest.fixture
    def system_facade(self):
        """创建系统门面实例"""
        return SystemFacade()

    @pytest.fixture
    def initialized_facade(self, system_facade):
        """初始化的系统门面"""
        services = {
            "match_service": MagicMock(),
            "prediction_service": MagicMock(),
            "analytics_service": MagicMock(),
        }
        system_facade.initialize(services)
        return system_facade

    @pytest.mark.asyncio
    async def test_initialize(self, system_facade):
        """测试初始化"""
        services = {"test": "value"}
        system_facade.initialize(services)

        assert system_facade.services == services
        assert system_facade._prediction_facade is not None
        assert system_facade._data_facade is not None
        assert system_facade._analytics_facade is not None

    @pytest.mark.asyncio
    async def test_quick_predict(self, initialized_facade):
        """测试快速预测"""
        _result = await initialized_facade.quick_predict(123, 456)

        assert "prediction" in result
        assert "confidence" in result
        assert "top_recommendation" in result
        assert _result["confidence"] > 0

    @pytest.mark.asyncio
    async def test_quick_predict_not_initialized(self, system_facade):
        """测试未初始化时的快速预测"""
        with pytest.raises(RuntimeError, match="System not initialized"):
            await system_facade.quick_predict(123, 456)

    @pytest.mark.asyncio
    async def test_get_dashboard_summary(self, initialized_facade):
        """测试获取仪表板摘要"""
        summary = await initialized_facade.get_dashboard_summary(user_id=456)

        assert "accuracy" in summary
        assert "total_predictions" in summary
        assert "roi" in summary
        assert "trend" in summary
        assert summary["accuracy"] == 65.0

    @pytest.mark.asyncio
    async def test_health_check(self, initialized_facade):
        """测试系统健康检查"""
        health = await initialized_facade.health_check()

        assert "system" in health
        assert "services" in health
        assert "timestamp" in health
        assert health["system"] == "healthy"
        assert "data" in health["services"]


class TestPredictionRequestAndResult:
    """测试请求和结果类"""

    def test_prediction_request_creation(self):
        """测试预测请求创建"""
        request = PredictionRequest(match_id=123, user_id=456, algorithm="ensemble")

        assert request.match_id == 123
        assert request.user_id == 456
        assert request.algorithm == "ensemble"
        assert request.features is None

    def test_prediction_request_with_features(self):
        """测试带特征的预测请求"""
        features = {"team_form": 0.8, "weather": "sunny"}
        request = PredictionRequest(match_id=123, user_id=456, features=features)

        assert request.features == features

    def test_prediction_result_creation(self):
        """测试预测结果创建"""
        _prediction = {"match_id": 123, "prediction": "home_win"}
        _result = PredictionResult(
            _prediction=prediction,
            confidence=0.75,
            value_assessment={"is_value": True},
            recommendations=["建议投注"],
        )

        assert _result._prediction == prediction
        assert _result.confidence == 0.75
        assert _result.value_assessment["is_value"] is True
        assert len(result.recommendations) == 1


class TestDataCollectionConfig:
    """测试数据收集配置"""

    def test_config_creation(self):
        """测试配置创建"""
        _config = DataCollectionConfig(
            sources=["football", "odds"],
            refresh_interval=timedelta(hours=1),
            batch_size=50,
        )

        assert _config.sources == ["football", "odds"]
        assert _config.refresh_interval == timedelta(hours=1)
        assert _config.batch_size == 50

    def test_config_defaults(self):
        """测试配置默认值"""
        _config = DataCollectionConfig(sources=["test"], refresh_interval=timedelta(days=1))

        assert _config.batch_size == 100
