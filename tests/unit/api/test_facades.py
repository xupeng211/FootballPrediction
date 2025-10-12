"""
门面模式API端点测试
Tests for Facade Pattern API Endpoints

测试门面模式的所有API端点，包括：
- 门面管理（初始化、关闭、状态查询）
- 主系统门面演示
- 预测门面演示
- 数据收集门面演示
- 分析门面演示
- 通知门面演示
- 完整工作流演示
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.facades import router, global_facades


class MockFacade:
    """模拟门面"""

    def __init__(self, facade_type="mock", name="mock_facade"):
        self.facade_type = facade_type
        self.name = name
        self.initialized = False
        self.subsystem_manager = Mock()
        self.subsystem_manager.list_subsystems.return_value = ["subsystem1", "subsystem2"]
        self.metrics = {
            "operations_count": 0,
            "cache_hits": 0,
            "average_response_time": 100.0,
        }

    async def initialize(self):
        """初始化门面"""
        self.initialized = True

    async def shutdown(self):
        """关闭门面"""
        self.initialized = False

    def get_status(self):
        """获取状态"""
        return {
            "name": self.name,
            "type": self.facade_type,
            "initialized": self.initialized,
            "subsystem_count": len(self.subsystem_manager.list_subsystems()),
            "metrics": self.metrics,
        }

    async def health_check(self):
        """健康检查"""
        return {
            "overall_health": self.initialized,
            "subsystems": {
                "subsystem1": {"healthy": True},
                "subsystem2": {"healthy": True},
            },
            "last_check": datetime.utcnow().isoformat(),
        }

    async def execute(self, operation, **kwargs):
        """执行操作"""
        self.metrics["operations_count"] += 1

        # 模拟不同操作的返回值
        if operation == "store_and_predict":
            return {
                "prediction": 0.85,
                "confidence": 0.92,
                "model": kwargs.get("model", "neural_network"),
            }
        elif operation == "batch_process":
            return [{"result": f"processed_{item}"} for item in kwargs.get("items", [])]
        elif operation == "predict":
            return {
                "output": {"prediction": 0.78},
                "model": kwargs.get("model", "neural_network"),
            }
        elif operation == "batch_predict":
            predictions = kwargs.get("predictions", [])
            return [{"prediction": 0.8} for _ in predictions]
        elif operation == "get_model_info":
            return {
                "models": ["neural_network", "random_forest", "svm"],
                "default": "neural_network",
            }
        elif operation == "store_data":
            return {"stored": True, "id": "data_123"}
        elif operation == "query_data":
            return [{"id": 1, "data": "test"}]
        elif operation == "track_event":
            return {"tracked": True, "event_id": "evt_456"}
        elif operation == "generate_report":
            return {
                "report_type": kwargs.get("report_type", "summary"),
                "data": {"summary": "Report data"},
            }
        elif operation == "send_notification":
            return {"sent": True, "message_id": "msg_789"}
        elif operation == "queue_notification":
            return {"queued": True, "queue_id": "queue_123"}
        elif operation == "get_notification_stats":
            return {
                "sent_today": 100,
                "queued": 5,
                "failed": 2,
            }
        elif operation == "get_system_status":
            return {
                "status": "healthy",
                "uptime": 3600,
                "active_processes": 5,
            }
        elif operation == "get_analytics_summary":
            return {
                "total_events": 1000,
                "unique_users": 150,
                "conversion_rate": 0.05,
            }
        else:
            return {"operation": operation, "success": True}


@pytest.fixture
def app():
    """创建测试应用"""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_facades():
    """清理全局门面缓存"""
    global_facades.clear()
    yield
    global_facades.clear()


@pytest.fixture
def mock_facade_factory():
    """模拟门面工厂"""
    factory = Mock()
    factory.list_facade_types.return_value = [
        "main",
        "prediction",
        "data_collection",
        "analytics",
        "notification",
    ]
    factory.list_configs.return_value = ["main_config", "prediction_config"]
    factory.create_facade.return_value = MockFacade()
    factory._instance_cache = {}
    factory._config_cache = {}
    return factory


class TestFacadesAPI:
    """门面API测试"""

    # ==================== 门面管理测试 ====================

    @patch("src.api.facades.facade_factory")
    def test_list_facades(self, mock_factory, client):
        """测试：获取所有可用门面"""
        # Given
        mock_factory.list_facade_types.return_value = ["main", "prediction"]
        mock_factory.list_configs.return_value = ["main_config", "pred_config"]
        global_facades["test_facade"] = Mock()

        # When
        response = client.get("/facades/")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "available_types" in data
        assert "configured_facades" in data
        assert "cached_instances" in data
        assert "factory_info" in data

    @patch("src.api.facades.facade_factory")
    def test_initialize_facade(self, mock_factory, client):
        """测试：初始化门面"""
        # Given
        mock_facade = MockFacade()
        mock_factory.create_facade.return_value = mock_facade

        # When
        response = client.post(
            "/facades/initialize?facade_type=main&facade_name=test_main"
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["facade_name"] == "test_main"
        assert data["facade_type"] == "main"
        assert data["initialized"] is True
        assert "test_main" in global_facades

    @patch("src.api.facades.facade_factory")
    def test_initialize_facade_existing(self, mock_factory, client):
        """测试：初始化已存在的门面"""
        # Given
        mock_facade = MockFacade()
        global_facades["existing_facade"] = mock_facade

        # When
        response = client.post(
            "/facades/initialize?facade_type=main&facade_name=existing_facade"
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["facade_name"] == "existing_facade"
        mock_factory.create_facade.assert_not_called()

    @patch("src.api.facades.facade_factory")
    def test_initialize_facade_error(self, mock_factory, client):
        """测试：初始化门面失败"""
        # Given
        mock_factory.create_facade.side_effect = ValueError("Invalid facade type")

        # When
        response = client.post(
            "/facades/initialize?facade_type=invalid_type&facade_name=test"
        )

        # Then
        assert response.status_code == 400  # ValueError会被转换为400错误

    def test_shutdown_facade(self, client):
        """测试：关闭门面"""
        # Given
        mock_facade = MockFacade()
        mock_facade.shutdown = AsyncMock()
        global_facades["test_facade"] = mock_facade

        # When
        response = client.post("/facades/shutdown?facade_name=test_facade")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "test_facade 已成功关闭" in data["message"]
        assert "test_facade" not in global_facades

    def test_shutdown_facade_not_found(self, client):
        """测试：关闭不存在的门面"""
        # When
        response = client.post("/facades/shutdown?facade_name=nonexistent")

        # Then
        assert response.status_code == 404

    def test_get_facade_status_specific(self, client):
        """测试：获取特定门面状态"""
        # Given
        mock_facade = MockFacade(name="test_facade")  # 设置正确的名称
        global_facades["test_facade"] = mock_facade

        # When
        response = client.get("/facades/status?facade_name=test_facade")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_facade"
        assert data["initialized"] is False  # Mock的默认值

    def test_get_facade_status_all(self, client):
        """测试：获取所有门面状态"""
        # Given
        facade1 = MockFacade("main", "main_facade")
        facade1.initialized = True
        facade2 = MockFacade("prediction", "pred_facade")
        global_facades.update({"main_facade": facade1, "pred_facade": facade2})

        # When
        response = client.get("/facades/status")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["total_facades"] == 2
        assert "facades" in data
        assert len(data["facades"]) == 2

    def test_get_facade_status_not_found(self, client):
        """测试：获取不存在门面的状态"""
        # When
        response = client.get("/facades/status?facade_name=nonexistent")

        # Then
        assert response.status_code == 404

    def test_health_check_facade_specific(self, client):
        """测试：检查特定门面健康状态"""
        # Given
        mock_facade = MockFacade()
        mock_facade.initialized = True
        global_facades["test_facade"] = mock_facade

        # When
        response = client.post("/facades/health-check?facade_name=test_facade")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["overall_health"] is True

    def test_health_check_facade_all(self, client):
        """测试：检查所有门面健康状态"""
        # Given
        facade1 = MockFacade()
        facade1.initialized = True
        facade2 = MockFacade()
        facade2.initialized = False
        global_facades.update({"facade1": facade1, "facade2": facade2})

        # When
        response = client.post("/facades/health-check")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["overall_healthy"] is False
        assert data["checked_facades"] == 2
        assert data["healthy_facades"] == 1

    # ==================== 主系统门面演示测试 ====================

    @patch("src.api.facades.initialize_facade")
    def test_demo_main_system_prediction(self, mock_init, client):
        """测试：主系统门面预测演示"""
        # Given
        mock_facade = MockFacade()
        global_facades["main"] = mock_facade
        input_data = {"match_id": 123, "features": [1, 2, 3]}

        # When
        response = client.post(
            "/facades/demo/main-system-predict",
            json={
                "input_data": input_data,
                "model": "neural_network",
                "use_cache": True,
            },
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["operation"] == "store_and_predict"
        assert data["model"] == "neural_network"
        assert data["cache_enabled"] is True
        assert "result" in data
        assert "facade_metrics" in data

    @patch("src.api.facades.initialize_facade")
    def test_demo_batch_processing(self, mock_init, client):
        """测试：批量处理演示"""
        # Given
        mock_facade = MockFacade()
        global_facades["main"] = mock_facade
        items = [{"input_data": {"id": 1}}, {"input_data": {"id": 2}}]

        # When
        response = client.post("/facades/demo/batch-process", json=items)

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["operation"] == "batch_process"
        assert data["items_count"] == 2
        assert "execution_time_seconds" in data
        assert len(data["results"]) == 2

    # ==================== 预测门面演示测试 ====================

    @patch("src.api.facades.initialize_facade")
    def test_demo_prediction_facade(self, mock_init, client):
        """测试：预测门面演示"""
        # Given
        mock_facade = MockFacade()
        global_facades["prediction"] = mock_facade

        # When
        response = client.post(
            "/facades/demo/prediction",
            json={
                "model": "random_forest",
                "input_data": {"features": [1, 2, 3, 4]},
                "cache_key": "test_cache",
            },
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["operation"] == "predict"
        assert data["model"] == "random_forest"
        assert data["cache_key"] == "test_cache"
        assert "result" in data

    @patch("src.api.facades.initialize_facade")
    def test_demo_batch_prediction(self, mock_init, client):
        """测试：批量预测演示"""
        # Given
        mock_facade = MockFacade()
        global_facades["prediction"] = mock_facade
        predictions = [
            {"input_data": {"id": 1}},
            {"input_data": {"id": 2}},
            {"input_data": {"id": 3}},
        ]

        # When
        response = client.post("/facades/demo/batch-predict", json=predictions)

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["operation"] == "batch_predict"
        assert data["predictions_count"] == 3
        assert len(data["results"]) == 3

    @patch("src.api.facades.initialize_facade")
    def test_get_prediction_models(self, mock_init, client):
        """测试：获取预测模型信息"""
        # Given
        mock_facade = MockFacade()
        global_facades["prediction"] = mock_facade

        # When
        response = client.get("/facades/demo/prediction-models")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "model_info" in data
        assert "facade_metrics" in data

    # ==================== 数据收集门面演示测试 ====================

    @patch("src.api.facades.initialize_facade")
    def test_demo_data_storage(self, mock_init, client):
        """测试：数据存储演示"""
        # Given
        mock_facade = MockFacade()
        global_facades["data_collection"] = mock_facade

        # When
        response = client.post(
            "/facades/demo/store-data",
            json={"data": {"match_id": 123, "score": "2:1"}, "table": "matches"},
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["operation"] == "store_data"
        assert data["table"] == "matches"
        assert data["result"]["stored"] is True

    @patch("src.api.facades.initialize_facade")
    def test_demo_data_query(self, mock_init, client):
        """测试：数据查询演示"""
        # Given
        mock_facade = MockFacade()
        global_facades["data_collection"] = mock_facade

        # When
        response = client.post(
            "/facades/demo/query-data",
            json={"query": "SELECT * FROM matches", "use_cache": True},
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["operation"] == "query_data"
        assert data["query"] == "SELECT * FROM matches"
        assert data["cache_enabled"] is True
        assert data["result_count"] == 1

    # ==================== 分析门面演示测试 ====================

    @patch("src.api.facades.initialize_facade")
    def test_demo_event_tracking(self, mock_init, client):
        """测试：事件跟踪演示"""
        # Given
        mock_facade = MockFacade()
        global_facades["analytics"] = mock_facade

        # When
        response = client.post(
            "/facades/demo/track-event",
            json={
                "event_name": "prediction_made",
                "properties": {"model": "neural_network", "confidence": 0.95},
            },
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["operation"] == "track_event"
        assert data["event_name"] == "prediction_made"
        assert data["properties"]["model"] == "neural_network"

    @patch("src.api.facades.initialize_facade")
    def test_demo_report_generation(self, mock_init, client):
        """测试：报告生成演示"""
        # Given
        mock_facade = MockFacade()
        global_facades["analytics"] = mock_facade

        # When
        response = client.post(
            "/facades/demo/generate-report",
            json={
                "report_type": "daily_summary",
                "filters": {"date": "2023-12-01"},
            },
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["operation"] == "generate_report"
        assert data["report_type"] == "daily_summary"
        assert "generation_time_seconds" in data
        assert "report" in data

    @patch("src.api.facades.initialize_facade")
    def test_get_analytics_summary(self, mock_init, client):
        """测试：获取分析摘要"""
        # Given
        mock_facade = MockFacade()
        global_facades["analytics"] = mock_facade

        # When
        response = client.get("/facades/demo/analytics-summary")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "facade_metrics" in data

    # ==================== 通知门面演示测试 ====================

    @patch("src.api.facades.initialize_facade")
    def test_demo_send_notification(self, mock_init, client):
        """测试：发送通知演示"""
        # Given
        mock_facade = MockFacade()
        global_facades["notification"] = mock_facade

        # When
        response = client.post(
            "/facades/demo/send-notification",
            json={
                "recipient": "user@example.com",
                "message": "您的预测已完成",
                "channel": "email",
            },
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["operation"] == "send_notification"
        assert data["recipient"] == "user@example.com"
        assert data["channel"] == "email"
        assert data["result"]["sent"] is True

    @patch("src.api.facades.initialize_facade")
    def test_demo_queue_notification(self, mock_init, client):
        """测试：排队通知演示"""
        # Given
        mock_facade = MockFacade()
        global_facades["notification"] = mock_facade

        # When
        response = client.post(
            "/facades/demo/queue-notification",
            json={
                "notification": {
                    "recipient": "user@example.com",
                    "message": "批量通知",
                    "channel": "sms",
                }
            },
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["operation"] == "queue_notification"
        assert data["result"]["queued"] is True

    @patch("src.api.facades.initialize_facade")
    def test_get_notification_stats(self, mock_init, client):
        """测试：获取通知统计"""
        # Given
        mock_facade = MockFacade()
        global_facades["notification"] = mock_facade

        # When
        response = client.get("/facades/demo/notification-stats")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "stats" in data
        assert data["stats"]["sent_today"] == 100

    # ==================== 门面配置管理测试 ====================

    @patch("src.api.facades.facade_factory")
    def test_get_facade_configs(self, mock_factory, client):
        """测试：获取门面配置"""
        # Given
        mock_config = Mock()
        mock_config.facade_type = "main"
        mock_config.enabled = True
        mock_config.auto_initialize = True
        mock_config.parameters = {"timeout": 30}
        mock_config.environment = "production"

        mock_factory.list_configs.return_value = ["main_config"]
        mock_factory.get_config.return_value = mock_config
        mock_factory._instance_cache = {"main": Mock()}

        # When
        response = client.get("/facades/configs")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "configs" in data
        assert "factory_info" in data
        assert data["configs"]["main_config"]["type"] == "main"

    @patch("src.api.facades.facade_factory")
    def test_reload_facade_configs(self, mock_factory, client):
        """测试：重新加载门面配置"""
        # When
        response = client.post("/facades/configs/reload")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "门面配置已重新加载" in data["message"]
        mock_factory.clear_cache.assert_called_once()
        mock_factory.create_default_configs.assert_called_once()

    # ==================== 完整工作流演示测试 ====================

    @patch("src.api.facades.initialize_facade")
    def test_demo_complete_workflow(self, mock_init, client):
        """测试：完整工作流演示"""
        # Given
        data_facade = MockFacade()
        analytics_facade = MockFacade()
        prediction_facade = MockFacade()
        notification_facade = MockFacade()
        main_facade = MockFacade()

        global_facades.update({
            "data_collection": data_facade,
            "analytics": analytics_facade,
            "prediction": prediction_facade,
            "notification": notification_facade,
            "main": main_facade,
        })

        # When
        response = client.post(
            "/facades/demo/complete-workflow",
            json={"input_data": {"match_id": 123, "teams": ["A", "B"]}},
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["workflow"] == "complete_workflow"
        assert data["success"] is True
        assert "total_time_seconds" in data
        assert data["steps_completed"] == 5
        assert "results" in data
        assert "facade_metrics" in data
        assert "data_storage" in data["results"]
        assert "prediction" in data["results"]
        assert "notification" in data["results"]

    @patch("src.api.facades.initialize_facade")
    def test_demo_complete_workflow_with_error(self, mock_init, client):
        """测试：完整工作流演示（带错误）"""
        # Given
        data_facade = MockFacade()
        # 让预测操作失败
        prediction_facade = MockFacade()
        prediction_facade.execute = AsyncMock(side_effect=ValueError("Prediction failed"))

        global_facades.update({
            "data_collection": data_facade,
            "prediction": prediction_facade,
        })

        # When
        response = client.post(
            "/facades/demo/complete-workflow",
            json={"input_data": {"match_id": 123}},
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "partial_results" in data

    # ==================== 边界条件测试 ====================

    def test_get_facade_status_empty(self, client):
        """测试：获取状态时没有门面"""
        # When
        response = client.get("/facades/status")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["total_facades"] == 0
        assert data["facades"] == {}

    def test_health_check_empty(self, client):
        """测试：健康检查时没有门面"""
        # When
        response = client.post("/facades/health-check")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["overall_healthy"] is True  # 没有门面认为是健康的
        assert data["checked_facades"] == 0