"""
测试重构后的审计服务
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from src.services.audit import AuditService, AuditContext
from src.services.audit.sanitizer import DataSanitizer
from src.services.audit.loggers.audit_logger import AuditLogger
from src.services.audit.analyzers.data_analyzer import AuditAnalyzer
from src.services.audit.reporters.report_generator import AuditReportGenerator
from src.database.models.audit_log import AuditAction, AuditSeverity


class TestAuditServiceRefactored:
    """测试重构后的审计服务"""

    @pytest.fixture
    def audit_service(self):
        """创建审计服务实例"""
        return AuditService()

    @pytest.fixture
    def sample_context(self):
        """示例审计上下文"""
        return {
            "user_id": "test_user_123",
            "username": "testuser",
            "user_role": "admin",
            "session_id": "session_456",
            "ip_address": "192.168.1.1",
            "user_agent": "Test-Agent/1.0",
        }

    def test_audit_service_creation(self, audit_service):
        """测试审计服务创建"""
        assert audit_service is not None
        assert hasattr(audit_service, 'sanitizer')
        assert hasattr(audit_service, 'audit_logger')
        assert hasattr(audit_service, 'analyzer')
        assert hasattr(audit_service, 'report_generator')
        assert isinstance(audit_service.sanitizer, DataSanitizer)
        assert isinstance(audit_service.audit_logger, AuditLogger)
        assert isinstance(audit_service.analyzer, AuditAnalyzer)
        assert isinstance(audit_service.report_generator, AuditReportGenerator)

    def test_data_sanitizer(self):
        """测试数据清理器"""
        sanitizer = DataSanitizer()

        # 测试敏感表检测
        assert sanitizer.is_sensitive_table("users") == True
        assert sanitizer.is_sensitive_table("matches") == False

        # 测试敏感字段检测
        assert sanitizer.is_sensitive_column("password") == True
        assert sanitizer.is_sensitive_column("name") == False

        # 测试高风险操作检测
        assert sanitizer.is_high_risk_action(AuditAction.DELETE) == True
        assert sanitizer.is_high_risk_action(AuditAction.READ) == False

        # 测试数据清理
        data = {
            "name": "John",
            "password": "secret123",
            "email": "john@example.com",
            "nested": {
                "token": "abc123",
                "value": 42
            }
        }
        cleaned = sanitizer.sanitize_data(data)
        assert cleaned["name"] == "John"
        assert cleaned["password"] != "secret123"  # 应该被哈希
        assert len(cleaned["password"]) == 64  # SHA256长度
        assert cleaned["email"] == "john@example.com"  # 不在high_sensitive_fields中
        assert cleaned["nested"]["token"] != "abc123"  # 应该被哈希
        assert cleaned["nested"]["value"] == 42

    def test_audit_context(self):
        """测试审计上下文"""
        context = AuditContext(
            user_id="user123",
            username="testuser",
            user_role="admin"
        )

        # 测试转换为字典
        context_dict = context.to_dict()
        assert context_dict["user_id"] == "user123"
        assert context_dict["username"] == "testuser"
        assert context_dict["user_role"] == "admin"

        # 测试上下文管理器
        with context:
            from src.services.audit.context import audit_context
            current_context = audit_context.get()
            assert current_context["user_id"] == "user123"

    @pytest.mark.asyncio
    async def test_log_operation(self, audit_service, sample_context):
        """测试记录操作"""
        with patch.object(audit_service.audit_logger, 'log_operation', new_callable=AsyncMock) as mock_log:
            mock_log.return_value = 123

            log_id = await audit_service.log_operation(
                action=AuditAction.CREATE,
                table_name="test_table",
                record_id=1,
                new_values={"name": "test"},
                context=sample_context
            )

            assert log_id == 123
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args.kwargs["action"] == AuditAction.CREATE
            assert call_args.kwargs["table_name"] == "test_table"
            assert call_args.kwargs["context"] == sample_context

    @pytest.mark.asyncio
    async def test_get_audit_summary(self, audit_service):
        """测试获取审计摘要"""
        with patch.object(audit_service.analyzer, 'get_audit_summary', new_callable=AsyncMock) as mock_summary:
            from src.database.models.audit_log import AuditLogSummary

            mock_summary.return_value = AuditLogSummary(
                start_date=datetime.now(),
                end_date=datetime.now(),
                total_operations=100,
                unique_users=10,
                unique_tables=5,
                high_risk_operations=2,
                failed_operations=3,
                avg_execution_time_ms=50.5
            )

            summary = await audit_service.get_audit_summary()
            assert summary.total_operations == 100
            assert summary.unique_users == 10
            mock_summary.assert_called_once()

    def test_generate_summary_report(self, audit_service):
        """测试生成摘要报告"""
        from src.database.models.audit_log import AuditLogSummary

        summary = AuditLogSummary(
            start_date=datetime.now(),
            end_date=datetime.now(),
            total_operations=100,
            unique_users=10,
            unique_tables=5,
            high_risk_operations=2,
            failed_operations=3,
            avg_execution_time_ms=50.5
        )

        # 测试JSON格式
        json_report = audit_service.generate_summary_report(summary, format="json")
        assert isinstance(json_report, str)
        assert '"report_type": "audit_summary"' in json_report
        assert '"total_operations": 100' in json_report

        # 测试文本格式
        text_report = audit_service.generate_summary_report(summary, format="txt")
        assert isinstance(text_report, str)
        assert "审计摘要报告" in text_report
        assert "总操作数: 100" in text_report

    @pytest.mark.asyncio
    async def test_detect_anomalies(self, audit_service):
        """测试检测异常"""
        with patch.object(audit_service.analyzer, 'detect_anomalies', new_callable=AsyncMock) as mock_detect:
            mock_detect.return_value = [
                {
                    "type": "high_failure_rate",
                    "user_id": "user123",
                    "failed_operations": 15,
                    "time_window_hours": 24
                }
            ]

            anomalies = await audit_service.detect_anomalies()
            assert len(anomalies) == 1
            assert anomalies[0]["type"] == "high_failure_rate"
            assert anomalies[0]["user_id"] == "user123"

    def test_backward_compatibility(self, audit_service):
        """测试向后兼容性"""
        # 测试兼容性方法
        hashed = audit_service._hash_sensitive_value("test123")
        assert len(hashed) == 64
        assert hashed != "test123"

        # 测试数据清理兼容性方法
        data = {"password": "secret", "name": "test"}
        cleaned = audit_service._sanitize_data(data)
        assert cleaned["password"] != "secret"
        assert cleaned["name"] == "test"

        # 测试敏感数据检测
        assert audit_service._is_sensitive_data("users", "password") == True
        assert audit_service._is_sensitive_data("matches", "name") == False

    @pytest.mark.asyncio
    async def test_get_recent_activity(self, audit_service):
        """测试获取最近活动"""
        with patch('src.services.audit.audit_service.get_async_session') as mock_session:
            # Mock session and query
            mock_query = Mock()
            mock_session.return_value.__aenter__.return_value.query.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.execute.return_value.scalars.return_value.all.return_value = []

            activities = await audit_service.get_recent_activity(hours=24, limit=50)
            assert isinstance(activities, list)
            mock_query.filter.assert_called()
            mock_query.limit.assert_called_with(50)

    def test_module_imports(self):
        """测试模块导入"""
        # 测试从主模块导入
        from src.services.audit import AuditService as MainAuditService
        from src.services.audit import AuditContext as MainAuditContext
        from src.services.audit import audit_operation, audit_database_operation

        assert MainAuditService is not None
        assert MainAuditContext is not None
        assert callable(audit_operation)
        assert callable(audit_database_operation)

        # 测试从子模块导入
        from src.services.audit.sanitizer import DataSanitizer
        from src.services.audit.loggers.audit_logger import AuditLogger
        from src.services.audit.analyzers.data_analyzer import AuditAnalyzer
        from src.services.audit.reporters.report_generator import AuditReportGenerator

        assert DataSanitizer is not None
        assert AuditLogger is not None
        assert AuditAnalyzer is not None
        assert AuditReportGenerator is not None