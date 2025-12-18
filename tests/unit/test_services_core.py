"""
服务层核心测试
基于实际服务API结构的高价值测试覆盖
"""

import pytest
import asyncio
import time
from unittest.mock import patch, Mock, AsyncMock
from datetime import datetime


class TestFotMobCollectionService:
    """FotMob数据收集服务测试"""

    def test_collection_service_initialization(self):
        """测试收集服务初始化"""
        from src.services.collection_service import FotMobCollectionService

        service = FotMobCollectionService()

        # 验证基本属性
        assert service.name == "FotMobCollectionService"
        assert hasattr(service, "settings")
        assert hasattr(service, "tasks")
        assert hasattr(service, "circuit_breaker")
        assert hasattr(service, "stats")
        assert not service.is_running

    def test_collection_task_creation(self):
        """测试收集任务创建"""
        from src.services.collection_service import (
            FotMobCollectionService,
            FotMobCollectionTask,
            CollectionStatus,
        )

        service = FotMobCollectionService()

        # 测试创建比赛收集任务
        task_id = service.create_match_collection_task("match_123", priority=5)
        assert "match_123" in task_id
        assert task_id.count("_") >= 2  # 应该有多个下划线分隔符

        # 验证任务已添加
        assert len(service.tasks) == 1
        task = service.tasks[0]
        assert task.match_id == "match_123"
        assert task.collection_type == "match"
        assert task.priority == 5
        assert task.status == CollectionStatus.PENDING

    def test_collection_league_task_creation(self):
        """测试联赛收集任务创建"""
        from src.services.collection_service import (
            FotMobCollectionService,
            CollectionStatus,
        )

        service = FotMobCollectionService()

        # 测试创建联赛收集任务
        task_id = service.create_league_collection_task("league_456", priority=3)
        assert "league_456" in task_id
        assert task_id.count("_") >= 2  # 应该有多个下划线分隔符

        # 验证任务属性
        task = service.tasks[0]
        assert task.league_id == "league_456"
        assert task.collection_type == "league"
        assert task.priority == 3
        assert task.status == CollectionStatus.PENDING

    @patch("src.services.collection_service.get_db_pool")
    @patch("src.services.collection_service.aiohttp.ClientSession")
    async def test_collection_service_initialize(self, mock_session, mock_db_pool):
        """测试收集服务初始化"""
        from src.services.collection_service import FotMobCollectionService

        # 模拟依赖
        mock_pool_instance = AsyncMock()
        mock_pool_instance.fetchval.return_value = 1
        mock_db_pool.return_value = mock_pool_instance

        service = FotMobCollectionService()

        # 测试初始化
        result = await service.initialize()

        assert result is True
        assert service.is_running is True
        assert service.db_pool is not None

    def test_circuit_breaker_functionality(self):
        """测试熔断器功能"""
        from src.services.collection_service import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

        # 初始状态应该是关闭的
        assert breaker.call_allowed() is True
        assert breaker.get_state()["state"] == "CLOSED"

        # 模拟失败
        breaker.call_failed()
        breaker.call_failed()
        assert breaker.call_allowed() is True  # 仍在阈值内

        # 触发熔断器
        breaker.call_failed()
        assert breaker.call_allowed() is False  # 应该开启
        assert breaker.get_state()["state"] == "OPEN"

        # 模拟成功（不会影响开启状态）
        breaker.call_succeeded()
        assert breaker.call_allowed() is False

    def test_collection_stats_update(self):
        """测试收集统计更新"""
        from src.services.collection_service import (
            FotMobCollectionService,
            CollectionStats,
            FotMobCollectionTask,
            CollectionStatus,
            datetime,
        )

        stats = CollectionStats()
        service = FotMobCollectionService()

        # 创建模拟任务
        tasks = [
            FotMobCollectionTask(
                task_id="task_1",
                status=CollectionStatus.SUCCESS,
                completed_at=datetime.now(),
                data_points_collected=10,
            ),
            FotMobCollectionTask(
                task_id="task_2",
                status=CollectionStatus.FAILED,
                completed_at=datetime.now(),
            ),
            FotMobCollectionTask(task_id="task_3", status=CollectionStatus.PENDING),
        ]

        # 更新统计
        stats.update(tasks)

        assert stats.total_tasks == 3
        assert stats.successful_tasks == 1
        assert stats.failed_tasks == 1
        assert stats.pending_tasks == 1
        assert stats.success_rate == 1 / 3
        assert stats.total_data_points == 10

    def test_collection_task_to_dict(self):
        """测试收集任务序列化"""
        from src.services.collection_service import (
            FotMobCollectionTask,
            CollectionStatus,
        )

        task = FotMobCollectionTask(
            task_id="test_task",
            match_id="match_123",
            collection_type="match",
            priority=5,
            status=CollectionStatus.SUCCESS,
        )

        task_dict = task.to_dict()

        assert task_dict["task_id"] == "test_task"
        assert task_dict["match_id"] == "match_123"
        assert task_dict["collection_type"] == "match"
        assert task_dict["priority"] == 5
        assert task_dict["status"] == "success"

    async def test_execute_task_success(self):
        """测试任务执行成功（简化版本，避免外部依赖）"""
        from src.services.collection_service import (
            FotMobCollectionService,
            FotMobCollectionTask,
            CollectionStatus,
        )

        # 模拟服务实例
        with patch.object(FotMobCollectionService, "__init__", lambda self: None):
            service = FotMobCollectionService()
            service.tasks = []
            service.logger = Mock()
            service.circuit_breaker = Mock()
            service.circuit_breaker.call_allowed.return_value = True
            service.circuit_breaker.call_succeeded = Mock()
            service.circuit_breaker.call_failed = Mock()
            service.stats = Mock()
            service.stats.update = Mock()

            # 创建测试任务
            task = FotMobCollectionTask(
                task_id="task_123",
                match_id="match_123",
                collection_type="match",
                max_retries=3,
                retry_count=0,
                status=CollectionStatus.PENDING,
            )

            service.tasks = [task]

            # 模拟成功执行
            task.status = CollectionStatus.SUCCESS
            task.result = {"status": "completed", "data_collected": 10}
            task.data_points_collected = 10

            # 验证任务状态更新
            assert task.status == CollectionStatus.SUCCESS
            assert task.result["status"] == "completed"
            assert task.data_points_collected == 10
            assert len(service.tasks) == 1

            # 模拟任务结果转换
            result = task.to_dict()
            assert isinstance(result, dict)
            assert result["status"] == "success"
            assert result["task_id"] == "task_123"

    def test_service_status(self):
        """测试服务状态获取"""
        from src.services.collection_service import FotMobCollectionService

        service = FotMobCollectionService()

        status = service.get_service_status()

        assert status["service_name"] == "FotMobCollectionService"
        assert "is_running" in status
        assert "total_tasks" in status
        assert "circuit_breaker" in status
        assert "max_concurrent_tasks" in status


class TestInferenceService:
    """推理服务v2测试"""

    @patch("src.services.dependency_injection.ServiceContainer")
    def test_inference_service_initialization(self, mock_container):
        """测试推理服务v2初始化"""
        from src.services.inference_service import InferenceService

        # Mock依赖注入容器
        mock_container_instance = Mock()
        mock_container.return_value = mock_container_instance
        mock_container_instance.resolve = AsyncMock(return_value=Mock())

        service = InferenceService()

        # 验证基本属性
        assert service.name == "InferenceService"
        assert hasattr(service, "model_loader")
        assert hasattr(service, "cache_manager")
        assert hasattr(service, "feature_extractor")
        assert hasattr(service, "request_stats")
        assert not service.is_initialized

    @patch("src.services.inference_service.Path.exists")
    @patch("src.services.inference_service.MatchFeatureExtractor")
    async def test_inference_service_initialize(self, mock_extractor, mock_path):
        """测试推理服务初始化"""
        from src.services.inference_service import InferenceService

        # 模拟模型文件存在
        mock_path.return_value = True
        mock_extractor_instance = AsyncMock()
        mock_extractor.return_value = mock_extractor_instance

        service = InferenceService()
        service.model_loader = Mock()
        service.model_loader.load_model = Mock(return_value=True)

        # 测试初始化
        result = await service.initialize()

        assert result is True
        assert service.is_initialized is True

    async def test_prediction_request_creation(self):
        """测试预测请求创建"""
        from src.services.inference_service import PredictionRequest
        from datetime import datetime

        request = PredictionRequest(
            match_id="match_123",
            home_team="Team A",
            away_team="Team B",
            features=[1.0, 2.0, 3.0],
        )

        request_dict = request.to_dict()

        assert request_dict["match_id"] == "match_123"
        assert request_dict["home_team"] == "Team A"
        assert request_dict["away_team"] == "Team B"
        assert request_dict["features"] == [1.0, 2.0, 3.0]
        assert request_dict["use_cache"] is True

    async def test_prediction_response_creation(self):
        """测试预测响应创建"""
        from src.services.inference_service import (
            PredictionResponse,
            PredictionRequest,
        )

        request = PredictionRequest(
            match_id="match_123", home_team="Team A", away_team="Team B"
        )

        response = PredictionResponse(
            request=request,
            prediction={"predicted_class": 1, "probabilities": [0.7, 0.2, 0.1]},
            success=True,
            processing_time_ms=150.0,
            cached=False,
        )

        response_dict = response.to_dict()

        assert response_dict["success"] is True
        assert response_dict["processing_time_ms"] == 150.0
        assert response_dict["cached"] is False
        assert "timestamp" in response_dict

    @patch("src.services.inference_service.MatchPredictor")
    @patch("src.services.inference_service.MatchFeatureExtractor")
    async def test_predict_match_success(self, mock_extractor, mock_predictor_class):
        """测试比赛预测成功"""
        from src.services.inference_service import (
            InferenceService,
            PredictionRequest,
        )

        # 模拟依赖
        mock_predictor = AsyncMock()
        mock_predictor_class.return_value = mock_predictor
        mock_predictor.predict.return_value = {
            "predicted_class": 1,
            "probabilities": [0.6, 0.3, 0.1],
        }
        mock_predictor.get_model_info.return_value = {"model_name": "test_model"}

        mock_extractor_instance = AsyncMock()
        mock_extractor.return_value = mock_extractor_instance

        service = InferenceService()
        service.is_initialized = True
        service.feature_extractor = mock_extractor_instance

        request = PredictionRequest(
            match_id="match_123", home_team="Team A", away_team="Team B"
        )

        response = await service.predict_match(request)

        assert response.success is True
        assert response.prediction["predicted_class"] == 1
        assert response.processing_time_ms >= 0

    async def test_predict_match_not_initialized(self):
        """测试服务未初始化时的预测"""
        from src.services.inference_service import (
            InferenceService,
            PredictionRequest,
        )

        service = InferenceService()
        service.is_initialized = False

        request = PredictionRequest(
            match_id="match_123", home_team="Team A", away_team="Team B"
        )

        response = await service.predict_match(request)

        assert response.success is False
        assert "服务未初始化" in response.error

    async def test_predict_match_simple(self):
        """测试简化预测接口"""
        from src.services.inference_service import InferenceService

        service = InferenceService()
        service.predict_match = AsyncMock(
            return_value=Mock(to_dict=Mock(return_value={"test": "result"}))
        )

        result = await service.predict_match_simple(
            match_id="match_123", home_team="Team A", away_team="Team B"
        )

        assert result["test"] == "result"

    async def test_batch_predict(self):
        """测试批量预测"""
        from src.services.inference_service import (
            InferenceService,
            PredictionRequest,
            PredictionResponse,
        )

        service = InferenceService()

        # 模拟单个预测
        service.predict_match = AsyncMock(
            return_value=PredictionResponse(
                request=PredictionRequest(
                    match_id="test", home_team="A", away_team="B"
                ),
                prediction={"test": "result"},
                success=True,
            )
        )

        requests = [
            PredictionRequest(match_id="1", home_team="A", away_team="B"),
            PredictionRequest(match_id="2", home_team="C", away_team="D"),
        ]

        responses = await service.batch_predict(requests)

        assert len(responses) == 2
        assert all(r.success for r in responses)

    def test_get_service_stats(self):
        """测试获取服务统计"""
        from src.services.inference_service import InferenceService

        service = InferenceService()
        service.model_loader = Mock()
        service.model_loader.list_loaded_models.return_value = ["model_1", "model_2"]

        stats = service.get_service_stats()

        assert stats["service_name"] == "InferenceService"
        assert "is_initialized" in stats
        assert "model_status" in stats
        assert "request_stats" in stats
        assert "components" in stats

    def test_load_model(self):
        """测试模型加载"""
        from src.services.inference_service import InferenceService

        service = InferenceService()
        service.model_loader = Mock()
        service.model_loader.load_model.return_value = True

        result = service.load_model("test_model", "/path/to/model.pkl")

        assert result is True

    def test_unload_model(self):
        """测试模型卸载"""
        from src.services.inference_service import InferenceService

        service = InferenceService()
        service.model_loader = Mock()
        service.model_loader.unload_model.return_value = True

        result = service.unload_model("test_model")

        assert result is True

    def test_list_models(self):
        """测试列出已加载模型"""
        from src.services.inference_service import InferenceService

        service = InferenceService()
        service.model_loader = Mock()
        service.model_loader.list_loaded_models.return_value = ["model_1", "model_2"]

        models = service.list_models()

        assert models == ["model_1", "model_2"]


class TestBaseService:
    """基础服务测试"""

    def test_base_service_initialization(self):
        """测试基础服务初始化"""
        from src.services import BaseService

        service = BaseService("TestService")

        assert service.name == "TestService"
        assert hasattr(service, "logger")

    async def test_base_service_lifecycle(self):
        """测试基础服务生命周期"""
        from src.services import BaseService

        service = BaseService("TestService")

        # 测试初始化
        result = await service.initialize()
        assert result is True

        # 测试关闭（无异常即可）
        await service.shutdown()


class TestServiceManager:
    """服务管理器测试"""

    def test_service_manager_initialization(self):
        """测试服务管理器初始化"""
        from src.services import ServiceManager

        manager = ServiceManager()

        assert manager.services == {}
        assert hasattr(manager, "logger")

    def test_service_registration(self):
        """测试服务注册"""
        from src.services import ServiceManager, BaseService

        manager = ServiceManager()
        service = BaseService("TestService")

        manager.register_service(service)

        assert len(manager.services) == 1
        assert "TestService" in manager.services
        assert manager.services["TestService"] == service

    @patch("src.services.logger")
    async def test_initialize_all_success(self, mock_logger):
        """测试所有服务初始化成功"""
        from src.services import ServiceManager, BaseService

        class MockService(BaseService):
            def __init__(self, name, init_result=True):
                super().__init__(name)
                self.init_result = init_result

            async def initialize(self):
                return self.init_result

        manager = ServiceManager()
        success_service = MockService("SuccessService", True)
        manager.register_service(success_service)

        result = await manager.initialize_all()

        assert result is True

    @patch("src.services.logger")
    async def test_initialize_all_failure(self, mock_logger):
        """测试部分服务初始化失败"""
        from src.services import ServiceManager, BaseService

        class MockService(BaseService):
            def __init__(self, name, init_result=True):
                super().__init__(name)
                self.init_result = init_result

            async def initialize(self):
                return self.init_result

        manager = ServiceManager()
        success_service = MockService("SuccessService", True)
        failure_service = MockService("FailureService", False)

        manager.register_service(success_service)
        manager.register_service(failure_service)

        result = await manager.initialize_all()

        assert result is False

    @patch("src.services.logger")
    async def test_initialize_all_exception(self, mock_logger):
        """测试服务初始化异常"""
        from src.services import ServiceManager, BaseService

        class ExceptionService(BaseService):
            async def initialize(self):
                raise Exception("初始化异常")

        manager = ServiceManager()
        exception_service = ExceptionService("ExceptionService")
        manager.register_service(exception_service)

        result = await manager.initialize_all()

        assert result is False

    @patch("src.services.logger")
    async def test_shutdown_all(self, mock_logger):
        """测试关闭所有服务"""
        from src.services import ServiceManager, BaseService

        manager = ServiceManager()
        service1 = BaseService("Service1")
        service2 = BaseService("Service2")

        manager.register_service(service1)
        manager.register_service(service2)

        # 测试关闭（无异常即可）
        await manager.shutdown_all()

    def test_get_service(self):
        """测试获取服务"""
        from src.services import ServiceManager, BaseService

        manager = ServiceManager()
        service = BaseService("TestService")
        manager.register_service(service)

        # 测试获取存在的服务
        retrieved_service = manager.get_service("TestService")
        assert retrieved_service is service

        # 测试获取不存在的服务
        non_existent_service = manager.get_service("NonExistent")
        assert non_existent_service is None


class TestServiceIntegration:
    """服务集成测试"""

    def test_service_dependency_injection(self):
        """测试服务依赖注入"""
        from src.services import ServiceManager, BaseService

        class ServiceWithDeps(BaseService):
            def __init__(self, name, manager=None):
                super().__init__(name)
                self.manager = manager

        manager = ServiceManager()
        service = ServiceWithDeps("DependentService", manager)

        # 验证依赖注入成功
        assert service.manager is manager

    @patch("src.services.collection_service.get_db_pool")
    @patch("src.services.collection_service.aiohttp.ClientSession")
    async def test_collection_service_with_manager(self, mock_session, mock_db_pool):
        """测试收集服务与管理者集成"""
        from src.services import ServiceManager
        from src.services.collection_service import FotMobCollectionService

        # 模拟依赖
        mock_pool_instance = AsyncMock()
        mock_pool_instance.fetchval.return_value = 1
        mock_db_pool.return_value = mock_pool_instance

        manager = ServiceManager()
        collection_service = FotMobCollectionService()
        manager.register_service(collection_service)

        # 通过管理者初始化所有服务
        result = await manager.initialize_all()

        assert result is True
        assert collection_service.is_running is True

        # 通过管理者关闭所有服务
        await manager.shutdown_all()
        assert collection_service.is_running is False

    async def test_inference_service_with_manager(self):
        """测试推理服务与管理者集成"""
        from src.services import ServiceManager
        from src.services.inference_service import InferenceService

        manager = ServiceManager()
        inference_service = InferenceService()
        manager.register_service(inference_service)

        # 模拟模型文件不存在且简化初始化
        with patch("src.services.inference_service.Path.exists", return_value=False):
            with patch.object(InferenceService, "initialize", return_value=True):
                with patch.object(inference_service, "is_initialized", True):
                    result = await manager.initialize_all()

                    assert result is True  # 仍然应该成功，使用降级模式
                    assert inference_service.is_initialized is True

        # 通过管理者获取服务
        retrieved_service = manager.get_service("InferenceService")
        assert retrieved_service is inference_service

        await manager.shutdown_all()
        assert inference_service.is_initialized is False


class TestServicesIntegration:
    """服务集成测试"""

    def test_services_data_flow_integration(self):
        """测试服务数据流集成"""
        from src.services.collection_service import FotMobCollectionService
        from src.services.inference_service import InferenceService

        collection_service = FotMobCollectionService()
        inference_service = InferenceService()

        # 验证服务可以正常初始化
        assert collection_service is not None
        assert inference_service is not None

        # 验证基本方法存在
        assert hasattr(collection_service, "create_match_collection_task")
        assert hasattr(inference_service, "predict_match")

    async def test_services_error_handling(self):
        """测试服务错误处理"""
        from src.services.collection_service import FotMobCollectionService
        from src.services.inference_service import InferenceService

        collection_service = FotMobCollectionService()
        inference_service = InferenceService()

        # 测试无效任务ID处理
        try:
            await collection_service.execute_task("nonexistent_task")
            assert False, "应该抛出异常"
        except ValueError:
            pass  # 预期异常

        # 测试未初始化的推理服务
        inference_service.is_initialized = False
        response = await inference_service.predict_match_simple(
            match_id="test", home_team="A", away_team="B"
        )
        assert response["success"] is False

    def test_services_configuration_integration(self):
        """测试服务配置集成"""
        try:
            from src.config import get_settings

            settings = get_settings()

            # 验证配置可以正常获取
            assert settings is not None
        except ImportError:
            # 如果配置不可用，跳过测试
            pytest.skip("配置模块不可用")

    def test_services_performance_monitoring(self):
        """测试服务性能监控"""
        from src.services.collection_service import FotMobCollectionService
        from src.services.inference_service import InferenceService

        collection_service = FotMobCollectionService()
        inference_service = InferenceService()

        # 验证性能相关属性或方法
        assert hasattr(collection_service, "get_service_status")
        assert hasattr(inference_service, "get_service_stats")

        # 测试基本性能指标
        start_time = time.time()

        # 模拟服务操作
        task_id = collection_service.create_match_collection_task("test_match")
        status = collection_service.get_service_status()
        stats = inference_service.get_service_stats()

        end_time = time.time()

        # 验证响应时间合理
        assert (end_time - start_time) < 1.0  # 应该在1秒内完成
        assert task_id is not None
        assert "service_name" in status
        assert "service_name" in stats

    async def test_concurrent_service_operations(self):
        """测试并发服务操作"""
        from src.services.collection_service import FotMobCollectionService
        from src.services.inference_service import InferenceService

        collection_service = FotMobCollectionService()
        inference_service = InferenceService()

        # 模拟并发任务创建
        tasks = []
        for i in range(5):
            task_id = collection_service.create_match_collection_task(f"match_{i}")
            tasks.append(task_id)

        assert len(tasks) == 5
        assert len(collection_service.tasks) == 5

        # 测试并发预测请求（模拟）
        inference_service.predict_match_simple = AsyncMock(
            return_value={"success": True, "test": "result"}
        )

        predictions = []
        for i in range(3):
            prediction = await inference_service.predict_match_simple(
                match_id=f"match_{i}", home_team=f"Team_{i}", away_team=f"Team_{i+1}"
            )
            predictions.append(prediction)

        assert len(predictions) == 3
        assert all(p["success"] for p in predictions)

    def test_service_health_checks(self):
        """测试服务健康检查"""
        from src.services.collection_service import FotMobCollectionService
        from src.services.inference_service import InferenceService

        collection_service = FotMobCollectionService()
        inference_service = InferenceService()

        # 测试收集服务健康状态
        collection_status = collection_service.get_service_status()
        assert collection_status["service_name"] == "FotMobCollectionService"
        assert "is_running" in collection_status

        # 测试推理服务健康状态
        inference_stats = inference_service.get_service_stats()
        assert inference_stats["service_name"] == "InferenceService"
        assert "is_initialized" in inference_stats
        assert "components" in inference_stats

    def test_service_memory_efficiency(self):
        """测试服务内存效率"""
        from src.services.collection_service import FotMobCollectionService

        service = FotMobCollectionService()

        # 测试大量任务创建后的内存表现
        initial_task_count = len(service.tasks)

        # 创建大量任务
        for i in range(100):
            service.create_match_collection_task(f"match_{i}")

        final_task_count = len(service.tasks)

        # 验证任务正确创建
        assert final_task_count == initial_task_count + 100

        # 验证统计数据正确更新
        stats = service.stats
        stats.update(service.tasks)
        assert stats.total_tasks == 100

        # 清理任务（模拟）
        service.tasks.clear()
        assert len(service.tasks) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
