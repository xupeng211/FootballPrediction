"""
Phase 4A 简化版 Mock 工厂
为集成测试提供基础 Mock 对象
"""

from unittest.mock import AsyncMock, Mock


class Phase4AMockFactory:
    """Phase 4A 简化版 Mock 工厂"""

    @staticmethod
    def create_mock_gateway_service():
        """创建网关服务 Mock"""
        service = Mock()
        service.route_request = AsyncMock(
            return_value={"status": "success", "service": "mock_service"}
        )
        service.health_check = AsyncMock(return_value={"healthy": True})
        return service

    @staticmethod
    def create_mock_load_balancer():
        """创建负载均衡器 Mock"""
        balancer = Mock()
        balancer.select_service = AsyncMock(return_value={"service": "service_1", "load": 0.3})
        balancer.get_services = AsyncMock(
            return_value=[
                {"name": "service_1", "healthy": True, "load": 0.3},
                {"name": "service_2", "healthy": True, "load": 0.5},
            ]
        )
        return balancer

    @staticmethod
    def create_mock_database_service():
        """创建数据库服务 Mock"""
        service = Mock()
        service.initialize = AsyncMock(
            return_value={
                "success": True,
                "database_type": "postgresql",
                "connected": True,
            }
        )
        service.execute_query = AsyncMock(
            return_value={"success": True, "rows": [{"id": 1}], "execution_time": 0.002}
        )
        service.execute_batch = AsyncMock(return_value={"success": True, "results": [{"rows": []}]})
        service.health_check = AsyncMock(return_value={"healthy": True, "active_connections": 5})
        return service

    @staticmethod
    def create_mock_cache_service():
        """创建缓存服务 Mock"""
        service = Mock()
        service.get = AsyncMock(return_value={"success": True, "value": "cached_data"})
        service.set = AsyncMock(return_value={"success": True, "key": "test_key"})
        service.delete = AsyncMock(return_value={"success": True, "deleted": True})
        service.health_check = AsyncMock(return_value={"healthy": True, "memory_usage": "45%"})
        return service

    @staticmethod
    def create_mock_prediction_service():
        """创建预测服务 Mock"""
        service = Mock()
        service.predict = AsyncMock(
            return_value={
                "success": True,
                "prediction": {"home_win": 0.6, "draw": 0.3, "away_win": 0.1},
            }
        )
        service.get_prediction_history = AsyncMock(return_value={"predictions": [], "total": 0})
        service.health_check = AsyncMock(return_value={"healthy": True, "models_loaded": 5})
        return service

    @staticmethod
    def create_mock_auth_service():
        """创建认证服务 Mock"""
        service = Mock()
        service.login = AsyncMock(
            return_value={
                "success": True,
                "user_id": "mock_user",
                "token": "mock_token",
                "expires_in": 3600,
            }
        )
        service.logout = AsyncMock(return_value={"success": True, "message": "Session invalidated"})
        service.authenticate = AsyncMock(return_value={"success": True, "user_id": "mock_user"})
        service.validate_token = AsyncMock(return_value={"valid": True, "user_id": "mock_user"})
        return service

    @staticmethod
    def create_mock_notification_service():
        """创建通知服务 Mock"""
        service = Mock()
        service.send_notification = AsyncMock(
            return_value={"success": True, "notification_id": "notif_123"}
        )
        service.get_notifications = AsyncMock(return_value={"notifications": [], "unread_count": 0})
        service.mark_as_read = AsyncMock(return_value={"success": True, "marked_count": 1})
        return service

    @staticmethod
    def create_mock_monitoring_service():
        """创建监控服务 Mock"""
        service = Mock()
        service.get_metrics = AsyncMock(
            return_value={
                "cpu_usage": 45.2,
                "memory_usage": 67.8,
                "disk_usage": 23.4,
                "active_connections": 125,
                "response_time": 0.045,
            }
        )
        service.get_health_status = AsyncMock(return_value={"status": "healthy", "checks": []})
        service.get_logs = AsyncMock(return_value={"logs": [], "total": 0})
        return service

    @staticmethod
    def create_mock_data_collector_service():
        """创建数据收集服务 Mock"""
        service = Mock()
        service.collect_match_data = AsyncMock(
            return_value={"success": True, "matches_collected": 10}
        )
        service.collect_team_stats = AsyncMock(return_value={"success": True, "teams_updated": 20})
        service.process_live_data = AsyncMock(return_value={"success": True, "events_processed": 5})
        return service

    @staticmethod
    def create_mock_service_registry():
        """创建服务注册中心 Mock"""
        registry = Mock()
        registry.register_service = AsyncMock(
            return_value={"success": True, "service_id": "service_123"}
        )
        registry.discover_service = AsyncMock(
            return_value={"service": {"name": "test_service", "host": "localhost", "port": 8080}}
        )
        registry.get_all_services = AsyncMock(return_value={"services": []})
        registry.health_check = AsyncMock(return_value={"healthy": True, "registered_services": 15})
        return registry

    @staticmethod
    def create_mock_circuit_breaker():
        """创建熔断器 Mock"""
        circuit_breaker = Mock()
        circuit_breaker.call = AsyncMock(return_value={"success": True, "data": "mock_response"})
        circuit_breaker.get_state = Mock(return_value="CLOSED")
        circuit_breaker.is_open = Mock(return_value=False)
        return circuit_breaker

    @staticmethod
    def create_mock_rate_limiter():
        """创建限流器 Mock"""
        limiter = Mock()
        limiter.is_allowed = Mock(return_value=True)
        limiter.get_remaining_requests = Mock(return_value=95)
        limiter.get_reset_time = Mock(return_value=60)
        return limiter

    @staticmethod
    def create_mock_message_queue():
        """创建消息队列 Mock"""
        queue = Mock()
        queue.publish = AsyncMock(return_value={"success": True, "message_id": "msg_123"})
        queue.consume = AsyncMock(return_value={"message": {"type": "test", "data": {}}})
        queue.get_queue_size = Mock(return_value=10)
        queue.health_check = AsyncMock(return_value={"healthy": True, "consumers": 3})
        return queue
