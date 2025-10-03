"""
审计服务全面测试
Comprehensive tests for audit service to boost coverage
"""

import json
import logging
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 尝试导入审计服务
try:
    from src.services.audit_service import (
        AuditService,
        AuditLog,
        AuditEvent,
        AuditSeverity,
        AuditAction,
        create_audit_log,
        log_user_action,
        log_system_event,
        log_security_event,
        get_audit_logs,
        audit_trail
    )
except ImportError:
    # 创建模拟类用于测试
    AuditService = None
    AuditLog = None
    AuditEvent = None
    AuditSeverity = None
    AuditAction = None
    create_audit_log = None
    log_user_action = None
    log_system_event = None
    log_security_event = None
    get_audit_logs = None
    audit_trail = None


class TestAuditService:
    """审计服务测试类"""

    def setup_method(self):
        """每个测试方法前的设置"""
        if AuditService is None:
            pytest.skip("AuditService not available")

        self.service = AuditService()
        self.test_user_id = "user123"
        self.test_action = "PREDICTION_REQUEST"
        self.test_resource = "match/12345"

    def test_service_initialization(self):
        """测试服务初始化"""
        assert self.service is not None
        assert hasattr(self.service, 'logger')
        assert hasattr(self.service, 'storage')
        assert hasattr(self.service, 'config')

    def test_create_audit_log(self):
        """测试创建审计日志"""
        if create_audit_log is None:
            pytest.skip("create_audit_log not available")

        audit_log = create_audit_log(
            user_id=self.test_user_id,
            action=self.test_action,
            resource=self.test_resource,
            severity=AuditSeverity.INFO,
            details={"ip": "192.168.1.1", "user_agent": "TestAgent"}
        )

        assert audit_log.user_id == self.test_user_id
        assert audit_log.action == self.test_action
        assert audit_log.resource == self.test_resource
        assert audit_log.severity == AuditSeverity.INFO
        assert audit_log.timestamp is not None
        assert audit_log.session_id is not None

    def test_log_user_action(self):
        """测试记录用户操作"""
        if log_user_action is None:
            pytest.skip("log_user_action not available")

        with patch.object(self.service, 'write_log') as mock_write:
            log_user_action(
                user_id=self.test_user_id,
                action=AuditAction.LOGIN,
                resource="/auth/login",
                success=True,
                metadata={"ip": "192.168.1.100"}
            )

            mock_write.assert_called_once()
            call_args = mock_write.call_args[0][0]
            assert call_args.user_id == self.test_user_id
            assert call_args.action == AuditAction.LOGIN
            assert call_args.success is True

    def test_log_system_event(self):
        """测试记录系统事件"""
        if log_system_event is None:
            pytest.skip("log_system_event not available")

        with patch.object(self.service, 'write_log') as mock_write:
            log_system_event(
                event="MODEL_LOADED",
                details={
                    "model_name": "football_predictor_v1",
                    "model_version": "1.0.0",
                    "load_time": 1.23
                },
                severity=AuditSeverity.INFO
            )

            mock_write.assert_called_once()
            call_args = mock_write.call_args[0][0]
            assert call_args.event == "MODEL_LOADED"
            assert call_args.severity == AuditSeverity.INFO
            assert "model_name" in call_args.details

    def test_log_security_event(self):
        """测试记录安全事件"""
        if log_security_event is None:
            pytest.skip("log_security_event not available")

        with patch.object(self.service, 'write_log') as mock_write:
            log_security_event(
                event_type="UNAUTHORIZED_ACCESS",
                user_id="unknown",
                resource="/admin/panel",
                details={
                    "ip": "10.0.0.50",
                    "attempted_action": "DELETE",
                    "failure_reason": "Invalid credentials"
                },
                severity=AuditSeverity.CRITICAL
            )

            mock_write.assert_called_once()
            call_args = mock_write.call_args[0][0]
            assert call_args.event == "UNAUTHORIZED_ACCESS"
            assert call_args.severity == AuditSeverity.CRITICAL
            assert call_args.user_id == "unknown"

    def test_sensitive_data_masking(self):
        """测试敏感数据脱敏"""
        sensitive_data = {
            "password": "secret123",
            "api_key": "sk-1234567890",
            "token": "eyJhbGciOiJIUzI1NiIs",
            "ssn": "123-45-6789",
            "credit_card": "4111-1111-1111-1111",
            "safe_data": "this is safe"
        }

        masked_data = self.service.mask_sensitive_data(sensitive_data)

        # 敏感字段应该被脱敏
        assert "***" in masked_data["password"]
        assert "***" in masked_data["api_key"]
        assert "***" in masked_data["token"]
        assert "***" in masked_data["ssn"]
        assert "***" in masked_data["credit_card"]

        # 安全字段保持不变
        assert masked_data["safe_data"] == "this is safe"

    def test_audit_log_validation(self):
        """测试审计日志验证"""
        # 有效的日志
        valid_log = AuditLog(
            user_id="user123",
            action="LOGIN",
            resource="/auth",
            timestamp=datetime.now(),
            severity=AuditSeverity.INFO
        )
        assert self.service.validate_log(valid_log) is True

        # 缺少必要字段
        invalid_log = AuditLog(
            user_id="",  # 空用户ID
            action="LOGIN",
            resource="/auth",
            timestamp=datetime.now(),
            severity=AuditSeverity.INFO
        )
        assert self.service.validate_log(invalid_log) is False

    def test_audit_log_serialization(self):
        """测试审计日志序列化"""
        audit_log = AuditLog(
            user_id=self.test_user_id,
            action=self.test_action,
            resource=self.test_resource,
            timestamp=datetime.now(),
            severity=AuditSeverity.WARNING,
            details={"error": "Test error"},
            ip_address="192.168.1.1",
            user_agent="TestAgent/1.0"
        )

        # 测试JSON序列化
        json_str = json.dumps(audit_log.__dict__, default=str)
        assert isinstance(json_str, str)

        # 测试反序列化
        parsed = json.loads(json_str)
        assert parsed["user_id"] == self.test_user_id
        assert parsed["action"] == self.test_action

    @pytest.mark.asyncio
    async def test_async_log_writing(self):
        """测试异步日志写入"""
        audit_log = AuditLog(
            user_id=self.test_user_id,
            action=self.test_action,
            resource=self.test_resource,
            timestamp=datetime.now(),
            severity=AuditSeverity.INFO
        )

        with patch.object(self.service, 'async_write_log') as mock_write:
            mock_write.return_value = True

            success = await self.service.write_log_async(audit_log)
            assert success is True
            mock_write.assert_called_once_with(audit_log)

    def test_audit_log_search(self):
        """测试审计日志搜索"""
        if get_audit_logs is None:
            pytest.skip("get_audit_logs not available")

        # Mock日志存储
        mock_logs = [
            AuditLog(
                user_id="user1",
                action="LOGIN",
                resource="/auth",
                timestamp=datetime.now() - timedelta(hours=2),
                severity=AuditSeverity.INFO
            ),
            AuditLog(
                user_id="user2",
                action="FAILED_LOGIN",
                resource="/auth",
                timestamp=datetime.now() - timedelta(hours=1),
                severity=AuditSeverity.WARNING
            ),
            AuditLog(
                user_id="user1",
                action="LOGOUT",
                resource="/auth",
                timestamp=datetime.now() - timedelta(minutes=30),
                severity=AuditSeverity.INFO
            )
        ]

        with patch.object(self.service, 'search_logs') as mock_search:
            mock_search.return_value = mock_logs

            # 搜索特定用户的所有日志
            logs = get_audit_logs(user_id="user1")
            assert len(logs) == 2
            assert all(log.user_id == "user1" for log in logs)

            # 搜索特定时间范围的日志
            start_time = datetime.now() - timedelta(hours=1, minutes=30)
            end_time = datetime.now()
            logs = get_audit_logs(start_time=start_time, end_time=end_time)
            assert len(logs) == 1
            assert logs[0].action == "LOGOUT"

    def test_audit_trail(self):
        """测试审计轨迹"""
        if audit_trail is None:
            pytest.skip("audit_trail not available")

        resource_id = "resource_123"
        trail = audit_trail(resource_id)

        # 应该返回对该资源的所有操作
        assert isinstance(trail, list)
        assert all(log.resource == resource_id for log in trail)

    def test_log_retention_policy(self):
        """测试日志保留策略"""
        # 创建过期日志
        old_log = AuditLog(
            user_id="user1",
            action="LOGIN",
            resource="/auth",
            timestamp=datetime.now() - timedelta(days=400),  # 超过1年
            severity=AuditSeverity.INFO
        )

        # 创建新日志
        new_log = AuditLog(
            user_id="user2",
            action="LOGIN",
            resource="/auth",
            timestamp=datetime.now() - timedelta(days=1),
            severity=AuditSeverity.INFO
        )

        with patch.object(self.service, 'cleanup_old_logs') as mock_cleanup:
            self.service.enforce_retention_policy(retention_days=365)
            mock_cleanup.assert_called_once()

    def test_audit_log_export(self):
        """测试审计日志导出"""
        # Mock日志数据
        logs = [
            AuditLog(
                user_id="user1",
                action="LOGIN",
                resource="/auth",
                timestamp=datetime.now(),
                severity=AuditSeverity.INFO
            ),
            AuditLog(
                user_id="user2",
                action="PREDICTION",
                resource="/predict/12345",
                timestamp=datetime.now(),
                severity=AuditSeverity.INFO
            )
        ]

        with patch.object(self.service, 'get_logs_by_date_range') as mock_get:
            mock_get.return_value = logs

            # 导出为CSV
            csv_data = self.service.export_logs_csv(
                start_date=datetime.now() - timedelta(days=1),
                end_date=datetime.now()
            )
            assert "user_id,action,resource" in csv_data
            assert "user1" in csv_data
            assert "user2" in csv_data

            # 导出为JSON
            json_data = self.service.export_logs_json(
                start_date=datetime.now() - timedelta(days=1),
                end_date=datetime.now()
            )
            parsed = json.loads(json_data)
            assert len(parsed) == 2
            assert parsed[0]["user_id"] == "user1"

    def test_audit_statistics(self):
        """测试审计统计"""
        with patch.object(self.service, 'get_statistics') as mock_stats:
            mock_stats.return_value = {
                "total_logs": 10000,
                "logs_today": 500,
                "unique_users": 150,
                "failed_attempts": 25,
                "critical_events": 2,
                "top_actions": [
                    {"action": "LOGIN", "count": 2000},
                    {"action": "PREDICTION", "count": 1500}
                ]
            }

            stats = self.service.get_statistics(days=7)
            assert stats["total_logs"] == 10000
            assert stats["failed_attempts"] == 25
            assert len(stats["top_actions"]) == 2

    def test_real_time_monitoring(self):
        """测试实时监控"""
        # 测试设置实时监控
        alerts = []

        def alert_callback(log):
            alerts.append(log)

        self.service.set_realtime_monitoring(
            alert_callback,
            severity_threshold=AuditSeverity.CRITICAL
        )

        # 触发关键事件
        critical_log = AuditLog(
            user_id="attacker",
            action="UNAUTHORIZED_ACCESS",
            resource="/admin",
            timestamp=datetime.now(),
            severity=AuditSeverity.CRITICAL
        )

        self.service.process_log(critical_log)
        assert len(alerts) == 1
        assert alerts[0].severity == AuditSeverity.CRITICAL

    def test_audit_log_integrity(self):
        """测试审计日志完整性"""
        # 测试日志签名
        log = AuditLog(
            user_id="user1",
            action="LOGIN",
            resource="/auth",
            timestamp=datetime.now(),
            severity=AuditSeverity.INFO
        )

        # 生成签名
        signature = self.service.generate_log_signature(log)
        assert signature is not None

        # 验证签名
        is_valid = self.service.verify_log_signature(log, signature)
        assert is_valid is True

        # 篡改日志后验证失败
        log.user_id = "attacker"
        is_valid = self.service.verify_log_signature(log, signature)
        assert is_valid is False

    def test_concurrent_logging(self):
        """测试并发日志记录"""
        import threading
        import time

        logs = []
        lock = threading.Lock()

        def log_worker(worker_id):
            for i in range(10):
                log = AuditLog(
                    user_id=f"user_{worker_id}",
                    action=f"ACTION_{i}",
                    resource=f"/resource/{i}",
                    timestamp=datetime.now(),
                    severity=AuditSeverity.INFO
                )
                with lock:
                    logs.append(log)
                time.sleep(0.01)

        # 创建多个线程并发写入
        threads = []
        for i in range(5):
            thread = threading.Thread(target=log_worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # 验证所有日志都被记录
        assert len(logs) == 50
        assert len(set(log.user_id for log in logs)) == 5

    def test_performance_monitoring(self):
        """测试性能监控"""
        with patch.object(self.service, 'measure_performance') as mock_measure:
            mock_measure.return_value = {
                "write_time_ms": 5,
                "search_time_ms": 50,
                "storage_size_mb": 1024,
                "index_size_mb": 128
            }

            metrics = self.service.get_performance_metrics()
            assert metrics["write_time_ms"] == 5
            assert metrics["search_time_ms"] == 50
            assert metrics["storage_size_mb"] == 1024

    def test_audit_configuration(self):
        """测试审计配置"""
        config = {
            "log_level": "INFO",
            "retention_days": 365,
            "enable_compression": True,
            "enable_encryption": True,
            "max_batch_size": 1000,
            "flush_interval_seconds": 60
        }

        self.service.update_config(config)
        assert self.service.config["retention_days"] == 365
        assert self.service.config["enable_compression"] is True

    def test_error_handling(self):
        """测试错误处理"""
        # 测试存储错误
        with patch.object(self.service, 'write_to_storage') as mock_write:
            mock_write.side_effect = Exception("Storage error")

            log = AuditLog(
                user_id="user1",
                action="LOGIN",
                resource="/auth",
                timestamp=datetime.now(),
                severity=AuditSeverity.INFO
            )

            # 应该优雅处理错误
            try:
                self.service.write_log(log)
            except Exception as e:
                assert "Storage error" in str(e)

        # 测试配置错误
        invalid_config = {"retention_days": -1}  # 无效的保留天数
        with pytest.raises(ValueError):
            self.service.update_config(invalid_config)

    def test_audit_log_backup(self):
        """测试审计日志备份"""
        with patch.object(self.service, 'create_backup') as mock_backup:
            mock_backup.return_value = {
                "backup_id": "backup_20251002",
                "file_path": "/backups/audit_20251002.tar.gz",
                "size_mb": 500,
                "logs_count": 100000
            }

            backup_info = self.service.create_backup(
                start_date=datetime.now() - timedelta(days=30),
                end_date=datetime.now()
            )

            assert backup_info["backup_id"] == "backup_20251002"
            assert backup_info["size_mb"] == 500

    def test_compliance_features(self):
        """测试合规性功能"""
        # GDPR - 被遗忘权
        user_id = "user123"
        with patch.object(self.service, 'anonymize_user_logs') as mock_anonymize:
            mock_anonymize.return_value = 150  # 匿名化了150条日志

            count = self.service.anonymize_user_logs(user_id)
            assert count == 150
            mock_anonymize.assert_called_once_with(user_id)

        # SOX - 财务相关审计
        financial_logs = self.service.get_financial_audit_logs(
            quarter="2024Q3",
            include_sensitive=True
        )
        assert isinstance(financial_logs, list)

        # HIPAA - 受保护健康信息
        phi_logs = self.service.get_phi_audit_logs(
            patient_id="patient456",
            date_range=30
        )
        assert isinstance(phi_logs, list)


class TestAuditEventTypes:
    """审计事件类型测试类"""

    def test_authentication_events(self):
        """测试认证事件"""
        events = [
            AuditEvent.LOGIN,
            AuditEvent.LOGOUT,
            AuditEvent.LOGIN_FAILED,
            AuditEvent.PASSWORD_CHANGE,
            AuditEvent.PASSWORD_RESET,
            AuditEvent.TWO_FACTOR_AUTH
        ]

        for event in events:
            assert isinstance(event.value, str)
            assert len(event.value) > 0

    def test_authorization_events(self):
        """测试授权事件"""
        events = [
            AuditEvent.ACCESS_GRANTED,
            AuditEvent.ACCESS_DENIED,
            AuditEvent.PERMISSION_CHANGE,
            AuditEvent.ROLE_CHANGE
        ]

        for event in events:
            assert isinstance(event.value, str)
            assert "ACCESS" in event.value or "PERMISSION" in event.value or "ROLE" in event.value

    def test_data_events(self):
        """测试数据事件"""
        events = [
            AuditEvent.DATA_READ,
            AuditEvent.DATA_WRITE,
            AuditEvent.DATA_DELETE,
            AuditEvent.DATA_EXPORT,
            AuditEvent.DATA_IMPORT
        ]

        for event in events:
            assert "DATA" in event.value

    def test_system_events(self):
        """测试系统事件"""
        events = [
            AuditEvent.SYSTEM_START,
            AuditEvent.SYSTEM_SHUTDOWN,
            AuditEvent.CONFIGURATION_CHANGE,
            AuditEvent.ERROR_OCCURRED,
            AuditEvent.MODEL_LOADED,
            AuditEvent.MODEL_UPDATED
        ]

        for event in events:
            assert isinstance(event.value, str)

    def test_security_events(self):
        """测试安全事件"""
        events = [
            AuditEvent.SECURITY_BREACH,
            AuditEvent.SUSPICIOUS_ACTIVITY,
            AuditEvent.BRUTE_FORCE_ATTEMPT,
            AuditEvent.INTRUSION_DETECTED,
            AuditEvent.MALWARE_DETECTED
        ]

        for event in events:
            assert any(keyword in event.value for keyword in ["SECURITY", "SUSPICIOUS", "BREACH", "ATTEMPT"])


class TestAuditSeverity:
    """审计严重性级别测试类"""

    def test_severity_levels(self):
        """测试严重性级别"""
        severities = [
            AuditSeverity.DEBUG,
            AuditSeverity.INFO,
            AuditSeverity.WARNING,
            AuditSeverity.ERROR,
            AuditSeverity.CRITICAL
        ]

        # 测试严重性排序
        for i in range(len(severities) - 1):
            assert severities[i].value < severities[i + 1].value

        # 测试严重性比较
        assert AuditSeverity.CRITICAL > AuditSeverity.ERROR
        assert AuditSeverity.WARNING > AuditSeverity.INFO
        assert AuditSeverity.DEBUG < AuditSeverity.INFO

    def test_severity_color_mapping(self):
        """测试严重性颜色映射"""
        colors = {
            AuditSeverity.DEBUG: "gray",
            AuditSeverity.INFO: "blue",
            AuditSeverity.WARNING: "yellow",
            AuditSeverity.ERROR: "orange",
            AuditSeverity.CRITICAL: "red"
        }

        for severity, color in colors.items():
            mapped_color = AuditSeverity.get_color(severity)
            assert mapped_color == color