"""审计服务测试"""

import logging
from datetime import datetime
from unittest.mock import Mock

import pytest

from src.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class TestAuditService:
    """审计服务测试"""

    @pytest.fixture
    def mock_repository(self):
        """模拟审计仓库"""
        return Mock()

    @pytest.fixture
    def mock_logger(self):
        """模拟日志记录器"""
        return Mock()

    @pytest.fixture
    def service(self, mock_repository, mock_logger):
        """创建审计服务"""
        return AuditService(repository=mock_repository, logger=mock_logger)

    def test_log_user_action(self, service, mock_repository, mock_logger):
        """测试记录用户操作"""
        # 准备测试数据
        user_id = 123
        action = "create_prediction"
        details = {"match_id": 456, "prediction": "home_win"}

        # 设置模拟返回
        mock_repository.save_audit_log.return_value = True

        # 调用方法
        result = service.log_user_action(user_id, action, details)

        # 验证
        assert result is True
        mock_repository.save_audit_log.assert_called_once()
        mock_logger.info.assert_called_once()

    def test_log_system_event(self, service, mock_repository):
        """测试记录系统事件"""
        # 准备测试数据
        event_type = "model_training"
        details = {"model_version": "v1.0.0", "accuracy": 0.85, "duration": 3600}

        # 调用方法
        result = service.log_system_event(event_type, details)

        # 验证
        assert result is True
        mock_repository.save_audit_log.assert_called_once()

    def test_log_api_access(self, service, mock_repository):
        """测试记录API访问"""
        # 准备测试数据
        request_data = {
            "endpoint": "/api/predictions",
            "method": "POST",
            "user_id": 123,
            "ip_address": "192.168.1.1",
            "status_code": 200,
            "response_time": 150,
        }

        # 调用方法
        result = service.log_api_access(request_data)

        # 验证
        assert result is True
        mock_repository.save_audit_log.assert_called_once()

    def test_log_data_access(self, service, mock_repository):
        """测试记录数据访问"""
        # 准备测试数据
        access_data = {
            "table": "matches",
            "operation": "SELECT",
            "user_id": 123,
            "query": "SELECT * FROM matches WHERE date > '2024-01-01'",
            "records_affected": 50,
        }

        # 调用方法
        result = service.log_data_access(access_data)

        # 验证
        assert result is True
        mock_repository.save_audit_log.assert_called_once()

    def test_log_security_event(self, service, mock_repository):
        """测试记录安全事件"""
        # 准备测试数据
        security_data = {
            "event_type": "failed_login",
            "user_id": 123,
            "ip_address": "192.168.1.1",
            "details": "Invalid password attempt",
        }

        # 调用方法
        result = service.log_security_event(security_data)

        # 验证
        assert result is True
        mock_repository.save_audit_log.assert_called_once()

    def test_get_user_activity(self, service, mock_repository):
        """测试获取用户活动"""
        # 准备测试数据
        user_id = 123
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        # 设置模拟返回
        mock_activities = [
            {
                "id": 1,
                "user_id": user_id,
                "action": "login",
                "timestamp": datetime(2024, 1, 15, 10, 0),
            },
            {
                "id": 2,
                "user_id": user_id,
                "action": "create_prediction",
                "timestamp": datetime(2024, 1, 15, 11, 0),
            },
        ]
        mock_repository.get_user_activities.return_value = mock_activities

        # 调用方法
        activities = service.get_user_activity(user_id, start_date, end_date)

        # 验证
        assert len(activities) == 2
        assert all(a["user_id"] == user_id for a in activities)

    def test_generate_audit_report(self, service, mock_repository):
        """测试生成审计报告"""
        # 准备测试数据
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)

        # 设置模拟返回
        mock_repository.get_audit_summary.return_value = {
            "total_actions": 1000,
            "user_actions": 800,
            "system_events": 150,
            "api_accesses": 400,
            "security_events": 5,
        }

        # 调用方法
        report = service.generate_audit_report(start_date, end_date)

        # 验证
        assert "summary" in report
        assert "period" in report
        assert report["summary"]["total_actions"] == 1000

    def test_check_compliance(self, service, mock_repository):
        """测试合规性检查"""
        # 设置模拟返回
        mock_repository.get_failed_logins.return_value = 10
        mock_repository.get_unauthorized_access.return_value = 2

        # 调用方法
        compliance = service.check_compliance()

        # 验证
        assert "failed_login_count" in compliance
        assert "unauthorized_access_count" in compliance
        assert compliance["failed_login_count"] == 10

    def test_anonymize_sensitive_data(self, service):
        """测试敏感数据匿名化"""
        # 准备包含敏感信息的数据
        data = {
            "user_id": 123,
            "email": "user@example.com",
            "ip_address": "192.168.1.1",
            "credit_card": "4111-1111-1111-1111",
        }

        # 调用方法
        anonymized = service.anonymize_sensitive_data(data)

        # 验证
        assert anonymized["user_id"] == 123  # 非敏感数据保留
        assert "@" in anonymized["email"]  # 邮箱部分保留
        assert anonymized["credit_card"] == "****-****-****-1111"  # 信用卡匿名化

    def test_archive_old_logs(self, service, mock_repository):
        """测试归档旧日志"""
        # 准备测试数据
        days_threshold = 90

        # 设置模拟返回
        mock_repository.archive_logs.return_value = 1000  # 归档了1000条记录

        # 调用方法
        archived_count = service.archive_old_logs(days_threshold)

        # 验证
        assert archived_count == 1000
        mock_repository.archive_logs.assert_called_once()

    def test_export_audit_logs(self, service, mock_repository):
        """测试导出审计日志"""
        # 准备测试数据
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        format_type = "csv"

        # 设置模拟返回
        mock_logs = [
            {
                "id": 1,
                "action": "login",
                "user_id": 123,
                "timestamp": datetime(2024, 1, 15),
            },
            {
                "id": 2,
                "action": "logout",
                "user_id": 123,
                "timestamp": datetime(2024, 1, 15),
            },
        ]
        mock_repository.get_logs_for_export.return_value = mock_logs

        # 调用方法
        export_data = service.export_audit_logs(start_date, end_date, format_type)

        # 验证
        assert len(export_data) == 2
        assert export_data[0]["action"] == "login"
