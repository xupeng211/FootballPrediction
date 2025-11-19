from typing import Optional

"""
服务集成测试
Services Integration Tests

测试服务之间的集成和协作.
Tests integration and collaboration between services.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.services.audit_service import AuditService, AuditSeverity
from src.services.auth_service import AuthService
from src.services.data_quality_monitor import DataQualityMonitor
from src.services.manager.manager import ServiceManager
from src.services.prediction_service import PredictionService


class MockUser:
    """模拟用户对象"""

    def __init__(self, user_id=1, username="testuser", email="test@example.com"):
        self.id = user_id
        self.username = username
        self.email = email
        self.password_hash = "$2b$12$hashed_password"
        self.is_active = True
        self.is_verified = False
        self.role = "user"
        self.preferences = {}
        self.statistics = {}

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
        }

    def update_last_login(self):
        pass


class TestAuthServiceIntegration:
    """认证服务集成测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return AsyncMock()

    @pytest.fixture
    def auth_service(self, mock_db):
        """认证服务实例"""
        with patch("src.services.auth_service.AuthUserRepository") as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo_class.return_value = mock_repo
            service = AuthService(mock_db)
            service.user_repo = mock_repo
            return service

    @pytest.fixture
    def audit_service(self):
        """审计服务实例"""
        return AuditService()

    @pytest.fixture
    def mock_user(self):
        """模拟用户对象"""
        return MockUser()

    @pytest.mark.asyncio
    async def test_user_registration_with_audit(
        self, auth_service, audit_service, mock_user
    ):
        """测试用户注册与审计集成"""
        # 模拟用户注册
        auth_service.user_repo.get_by_username.return_value = None
        auth_service.user_repo.get_by_email.return_value = None
        auth_service.user_repo.create.return_value = mock_user

        # 执行用户注册
        user = await auth_service.register_user(
            username="testuser", email="test@example.com", password="password123"
        )

        # 记录审计事件
        audit_event = audit_service.log_event(
            "user_registration",
            "system",
            {"username": "testuser", "email": "test@example.com", "user_id": user.id},
        )

        # 验证结果
        assert user is not None
        assert audit_event.action == "user_registration"
        assert audit_event._user == "system"
        assert audit_event.severity == AuditSeverity.LOW

        # 验证审计摘要
        summary = audit_service.get_summary()
        assert summary.total_logs == 1
        assert "user_registration" in summary.by_action

    @pytest.mark.asyncio
    async def test_user_login_with_audit(self, auth_service, audit_service, mock_user):
        """测试用户登录与审计集成"""
        # 模拟用户认证
        auth_service.user_repo.get_by_username.return_value = mock_user

        # 执行用户登录
        login_result = await auth_service.login_user("testuser", "password123")

        # 记录审计事件
        audit_event = audit_service.log_event(
            "user_login",
            mock_user.username,
            {"user_id": mock_user.id, "timestamp": datetime.now().isoformat()},
        )

        # 验证结果
        assert login_result is not None
        assert audit_event.action == "user_login"
        assert audit_event._user == mock_user.username

    @pytest.mark.asyncio
    async def test_failed_login_with_audit(self, auth_service, audit_service):
        """测试失败登录与审计集成"""
        # 模拟用户不存在
        auth_service.user_repo.get_by_username.return_value = None

        # 执行用户登录（应该失败）
        login_result = await auth_service.login_user("nonexistent", "password123")

        # 记录审计事件
        audit_event = audit_service.log_event(
            "failed_login_attempt",
            "anonymous",
            {"username": "nonexistent", "reason": "user_not_found"},
        )

        # 验证结果
        assert login_result is None
        assert audit_event.action == "failed_login_attempt"
        assert audit_event.severity == AuditSeverity.MEDIUM  # 失败登录中等严重性


class TestPredictionServiceIntegration:
    """预测服务集成测试"""

    @pytest.fixture
    def prediction_service(self):
        """预测服务实例"""
        return PredictionService()

    @pytest.fixture
    def audit_service(self):
        """审计服务实例"""
        return AuditService()

    def test_prediction_with_audit_logging(self, prediction_service, audit_service):
        """测试预测与审计日志集成"""
        match_data = {
            "match_id": 12345,
            "home_team_id": 1,
            "away_team_id": 2,
            "league_id": 39,
        }

        # 执行预测
        prediction = prediction_service.predict_match(match_data, "test_model")

        # 记录审计事件
        audit_event = audit_service.log_event(
            "prediction_created",
            "system",
            {
                "match_id": prediction.match_id,
                "model": "test_model",
                "predicted_outcome": prediction.predicted_outcome,
                "confidence": prediction.confidence_score,
            },
        )

        # 验证结果
        assert prediction.match_id == 12345
        assert audit_event.action == "prediction_created"
        assert audit_event.details["match_id"] == 12345

    def test_batch_prediction_with_audit(self, prediction_service, audit_service):
        """测试批量预测与审计集成"""
        batch_data = [
            {"match_id": 1, "home_team_id": 1, "away_team_id": 2},
            {"match_id": 2, "home_team_id": 3, "away_team_id": 4},
            {"match_id": 3, "home_team_id": 5, "away_team_id": 6},
        ]

        # 执行批量预测
        predictions = prediction_service.predict_batch(batch_data, "batch_model")

        # 记录审计事件
        audit_event = audit_service.log_event(
            "batch_prediction",
            "system",
            {
                "batch_size": len(predictions),
                "model": "batch_model",
                "successful_predictions": len(predictions),
            },
        )

        # 验证结果
        assert len(predictions) == 3
        assert audit_event.details["batch_size"] == 3
        assert audit_event.severity == AuditSeverity.LOW

    def test_high_confidence_prediction_audit(self, prediction_service, audit_service):
        """测试高置信度预测审计"""
        match_data = {"match_id": 12345, "home_team_id": 1, "away_team_id": 2}

        # 执行预测
        prediction = prediction_service.predict_match(
            match_data, "high_confidence_model"
        )

        # 检查置信度
        confidence_analysis = prediction_service.get_prediction_confidence(prediction)

        # 如果是高置信度预测，记录特殊审计事件
        if confidence_analysis["confidence_level"] == "high":
            audit_event = audit_service.log_event(
                "high_confidence_prediction",
                "system",
                {
                    "match_id": prediction.match_id,
                    "confidence": prediction.confidence_score,
                    "outcome": prediction.predicted_outcome,
                },
            )
            assert audit_event.action == "high_confidence_prediction"


class TestDataQualityIntegration:
    """数据质量服务集成测试"""

    @pytest.fixture
    def data_quality_monitor(self):
        """数据质量监控实例"""
        return DataQualityMonitor()

    @pytest.fixture
    def audit_service(self):
        """审计服务实例"""
        return AuditService()

    @pytest.mark.asyncio
    async def test_data_processing_with_audit(
        self, data_quality_monitor, audit_service
    ):
        """测试数据处理与审计集成"""
        processed_items = []
        quality_issues = []

        # 处理数据
        async for data in data_quality_monitor.process_data("test_source"):
            processed_items.append(data)

            # 验证数据质量
            validation = await data_quality_monitor.validate_data(data)
            if not validation["valid"]:
                quality_issues.append(validation)

        # 记录审计事件
        audit_event = audit_service.log_event(
            "data_processing_completed",
            "system",
            {
                "source": "test_source",
                "processed_items": len(processed_items),
                "quality_issues": len(quality_issues),
                "processing_time": data_quality_monitor.get_metrics()["duration"],
            },
        )

        # 验证结果
        assert len(processed_items) == 10
        assert audit_event.details["processed_items"] == 10

    @pytest.mark.asyncio
    async def test_quality_issues_with_audit(self, data_quality_monitor, audit_service):
        """测试质量问题与审计集成"""
        # 模拟有质量问题的数据
        invalid_data = {"invalid": "data"}

        # 验证数据
        validation = await data_quality_monitor.validate_data(invalid_data)

        # 如果验证失败，记录审计事件
        if not validation["valid"]:
            audit_event = audit_service.log_event(
                "data_quality_issue_detected",
                "quality_monitor",
                {
                    "issues": validation["issues"],
                    "recommendations": validation["recommendations"],
                    "data_sample": str(invalid_data)[:100],  # 限制长度
                },
            )
            assert audit_event.action == "data_quality_issue_detected"
            assert audit_event.severity >= AuditSeverity.MEDIUM


class TestServiceManagerIntegration:
    """服务管理器集成测试"""

    @pytest.fixture
    def service_manager(self):
        """服务管理器实例"""
        return ServiceManager()

    @pytest.fixture
    def audit_service(self):
        """审计服务实例"""
        return AuditService()

    @pytest.mark.asyncio
    async def test_service_lifecycle_with_audit(self, service_manager, audit_service):
        """测试服务生命周期与审计集成"""

        class TestService:
            def __init__(self, name):
                self.name = name
                self.initialized = False

            async def initialize(self):
                self.initialized = True
                return True

            async def shutdown(self):
                self.initialized = False

        # 注册服务
        service1 = TestService("service1")
        service2 = TestService("service2")

        service_manager.register_service("service1", service1)
        audit_event1 = audit_service.log_event(
            "service_registered",
            "service_manager",
            {"service_name": "service1", "service_type": "TestService"},
        )

        service_manager.register_service("service2", service2)
        audit_event2 = audit_service.log_event(
            "service_registered",
            "service_manager",
            {"service_name": "service2", "service_type": "TestService"},
        )

        # 初始化所有服务
        init_success = await service_manager.initialize_all()
        audit_event3 = audit_service.log_event(
            "services_initialized",
            "service_manager",
            {"success": init_success, "service_count": len(service_manager.services)},
        )

        # 关闭所有服务
        await service_manager.shutdown_all()
        audit_event4 = audit_service.log_event(
            "services_shutdown",
            "service_manager",
            {"service_count": len(service_manager.services)},
        )

        # 验证审计事件
        assert audit_event1.details["service_name"] == "service1"
        assert audit_event2.details["service_name"] == "service2"
        assert audit_event3.details["success"] is True
        assert audit_event4.details["service_count"] == 2

    @pytest.mark.asyncio
    async def test_service_failure_with_audit(self, service_manager, audit_service):
        """测试服务失败与审计集成"""

        class FailingService:
            def __init__(self, name):
                self.name = name

            async def initialize(self):
                raise Exception(f"Service {self.name} failed to initialize")

            async def shutdown(self):
                pass

        # 注册会失败的服务
        failing_service = FailingService("failing_service")
        service_manager.register_service("failing_service", failing_service)

        # 尝试初始化（应该失败）
        init_success = await service_manager.initialize_all()

        # 记录失败审计事件
        audit_event = audit_service.log_event(
            "service_initialization_failed",
            "service_manager",
            {
                "service_name": "failing_service",
                "failure_reason": "Service failing_service failed to initialize",
                "recovery_attempted": False,
            },
        )

        # 验证结果
        assert init_success is False
        assert audit_event.action == "service_initialization_failed"
        assert audit_event.severity == AuditSeverity.HIGH


class TestCompleteWorkflowIntegration:
    """完整工作流集成测试"""

    @pytest.mark.asyncio
    async def test_prediction_workflow_full_integration(self):
        """测试完整的预测工作流集成"""
        # 初始化所有服务
        auth_service = Mock()
        prediction_service = PredictionService()
        audit_service = AuditService()
        data_quality_monitor = DataQualityMonitor()

        # 模拟用户认证
        mock_user = MockUser()
        auth_service.authenticate_user = AsyncMock(return_value=mock_user)
        auth_service.get_current_user = AsyncMock(return_value=mock_user)

        # 1. 用户登录审计
        audit_service.log_event(
            "user_login",
            mock_user.username,
            {"user_id": mock_user.id, "login_time": datetime.now().isoformat()},
        )

        # 2. 数据质量监控
        data_quality_metrics = data_quality_monitor.get_metrics()
        audit_service.log_event(
            "data_quality_check", "system", {"metrics": data_quality_metrics}
        )

        # 3. 执行预测
        match_data = {"match_id": 12345, "home_team_id": 1, "away_team_id": 2}
        prediction = prediction_service.predict_match(match_data, "integration_model")

        # 4. 预测审计
        audit_service.log_event(
            "prediction_created",
            mock_user.username,
            {
                "match_id": prediction.match_id,
                "model": "integration_model",
                "outcome": prediction.predicted_outcome,
                "confidence": prediction.confidence_score,
                "user_id": mock_user.id,
            },
        )

        # 5. 置信度分析
        confidence_analysis = prediction_service.get_prediction_confidence(prediction)
        if confidence_analysis["confidence_level"] == "high":
            high_conf_audit = audit_service.log_event(
                "high_confidence_prediction_alert",
                "system",
                {
                    "match_id": prediction.match_id,
                    "confidence": confidence_analysis["confidence_score"],
                    "recommended": confidence_analysis["recommended"],
                },
            )
            assert high_conf_audit.action == "high_confidence_prediction_alert"

        # 6. 工作流完成审计
        audit_service.log_event(
            "prediction_workflow_completed",
            "system",
            {
                "user_id": mock_user.id,
                "predictions_made": 1,
                "workflow_duration": "1.2s",  # 模拟
                "data_quality_pass": True,
            },
        )

        # 验证所有审计事件
        summary = audit_service.get_summary()
        assert summary.total_logs >= 5  # 至少5个审计事件
        assert "user_login" in summary.by_action
        assert "prediction_created" in summary.by_action
        assert "prediction_workflow_completed" in summary.by_action

    @pytest.mark.asyncio
    async def test_error_handling_workflow_integration(self):
        """测试错误处理工作流集成"""
        audit_service = AuditService()
        DataQualityMonitor()

        # 模拟错误场景
        error_scenarios = [
            {
                "type": "data_validation_error",
                "description": "Invalid match data format",
                "severity": AuditSeverity.MEDIUM,
            },
            {
                "type": "prediction_model_error",
                "description": "Model prediction failed",
                "severity": AuditSeverity.HIGH,
            },
            {
                "type": "database_connection_error",
                "description": "Could not save prediction result",
                "severity": AuditSeverity.CRITICAL,
            },
        ]

        # 记录错误审计事件
        for scenario in error_scenarios:
            error_audit = audit_service.log_event(
                scenario["type"],
                "system",
                {
                    "error_description": scenario["description"],
                    "timestamp": datetime.now().isoformat(),
                    "error_code": f"ERR_{scenario['type'].upper()}",
                    "recovery_attempted": True,
                },
            )
            assert error_audit.severity == scenario["severity"]

        # 模拟错误恢复
        audit_service.log_event(
            "error_recovery_completed",
            "system",
            {
                "errors_resolved": len(error_scenarios),
                "recovery_time": "5.3s",
                "system_health": "restored",
            },
        )

        # 验证错误处理审计
        summary = audit_service.get_summary()
        assert summary.by_severity.get("critical", 0) >= 1
        assert summary.by_severity.get("high", 0) >= 1
        assert summary.by_severity.get("medium", 0) >= 1
        assert "error_recovery_completed" in summary.by_action

    @pytest.mark.asyncio
    async def test_concurrent_operations_integration(self):
        """测试并发操作集成"""

        audit_service = AuditService()
        prediction_service = PredictionService()

        async def create_prediction_batch(batch_id: int, size: int):
            """创建一批预测"""
            predictions = []
            for i in range(size):
                match_data = {
                    "match_id": batch_id * 1000 + i,
                    "home_team_id": (batch_id * 2 + i) % 10 + 1,
                    "away_team_id": (batch_id * 3 + i) % 10 + 1,
                }
                prediction = prediction_service.predict_match(
                    match_data, f"batch_{batch_id}"
                )
                predictions.append(prediction)

                # 记录预测审计
                audit_service.log_event(
                    "prediction_created",
                    f"batch_{batch_id}",
                    {
                        "match_id": prediction.match_id,
                        "batch_id": batch_id,
                        "prediction_index": i,
                    },
                )

                # 小延迟模拟真实处理
                await asyncio.sleep(0.01)

            return predictions

        # 并发创建多个预测批次
        tasks = [
            create_prediction_batch(1, 5),
            create_prediction_batch(2, 3),
            create_prediction_batch(3, 7),
        ]

        results = await asyncio.gather(*tasks)

        # 记录并发完成审计
        concurrent_audit = audit_service.log_event(
            "concurrent_predictions_completed",
            "system",
            {
                "batches_processed": len(results),
                "total_predictions": sum(len(batch) for batch in results),
                "concurrent_tasks": len(tasks),
                "processing_time": "2.1s",
            },
        )

        # 验证并发操作审计
        summary = audit_service.get_summary()
        assert summary.total_logs >= 15  # 至少15个预测事件 + 1个并发完成事件
        assert summary.by_action.get("prediction_created", 0) >= 15
        assert "concurrent_predictions_completed" in summary.by_action

        # 验证预测结果
        total_predictions = sum(len(batch) for batch in results)
        assert total_predictions == 15  # 5 + 3 + 7
        assert concurrent_audit.details["total_predictions"] == 15
