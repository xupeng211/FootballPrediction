"""
缓存性能API测试
Cache Performance API Tests.

测试缓存性能监控、分析和优化功能的API端点。
使用Mock完全隔离外部依赖，专注测试API逻辑。
"""

import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.api.optimization.cache_performance_api import router


class TestCachePerformanceAPI:
    """缓存性能API测试类."""

    def setup_method(self):
        """每个测试方法前的设置."""
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

        # Mock数据模板
        self.mock_redis_status = {
            "cluster_info": {
                "total_nodes": 3,
                "healthy_nodes": 2,
                "failed_nodes": 1,
                "cluster_name": "football_prediction_cache"
            },
            "metrics": {
                "cache_hit_rate": 85.5,
                "avg_response_time": 12.3,
                "total_operations": 10000,
                "failed_operations": 145,
                "operation_stats": {
                    "get": {"success": 8500, "failed": 100},
                    "set": {"success": 1200, "failed": 30},
                    "delete": {"success": 155, "failed": 15}
                }
            }
        }

        self.mock_cache_status = {
            "performance": {
                "hit_rate": 88.2,
                "miss_rate": 11.8,
                "avg_response_time": 8.7,
                "total_requests": 5000,
                "cache_size": "2.3GB"
            }
        }

        self.mock_consistency_stats = {
            "consistency_level": "strong",
            "conflict_strategy": "last_write_wins",
            "statistics": {
                "total_operations": 1500,
                "conflicts_resolved": 23,
                "successful_operations": 1477
            },
            "error_rate": 1.2,
            "conflict_rate": 1.5,
            "active_sessions": 5
        }

        self.mock_warmup_stats = {
            "total_plans": 12,
            "active_plans": 3,
            "completed_plans": 8,
            "failed_plans": 1,
            "total_tasks": 450,
            "completed_tasks": 395,
            "failed_tasks": 55,
            "execution_time_avg": 125.6,
            "cache_hit_rate_improvement": 15.3
        }

    # ==================== 缓存状态监控端点测试 ====================

    @patch('src.api.optimization.cache_performance_api.get_redis_cluster_manager')
    @patch('src.api.optimization.cache_performance_api.get_distributed_cache_manager')
    @patch('src.api.optimization.cache_performance_api.get_cache_consistency_manager')
    @patch('src.api.optimization.cache_performance_api.get_intelligent_warmup_manager')
    def test_get_cache_status_healthy(self, mock_warmup, mock_consistency, mock_distributed, mock_redis):
        """测试获取缓存状态 - 健康状态."""
        # 设置Mock返回值
        mock_redis.return_value = AsyncMock()
        mock_distributed.return_value = AsyncMock()
        mock_consistency.return_value = AsyncMock()
        mock_warmup.return_value = AsyncMock()

        mock_redis.return_value.get_cluster_status.return_value = self.mock_redis_status
        mock_distributed.return_value.get_cache_status.return_value = self.mock_cache_status
        mock_consistency.return_value.get_statistics.return_value = self.mock_consistency_stats
        mock_warmup.return_value.get_warmup_statistics.return_value = self.mock_warmup_stats

        response = self.client.get("/api/v1/cache/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "components" in data
        assert "timestamp" in data
        assert data["components"]["redis_cluster"]["enabled"] is True
        assert data["components"]["distributed_cache"]["enabled"] is True

    @patch('src.api.optimization.cache_performance_api.get_redis_cluster_manager')
    @patch('src.api.optimization.cache_performance_api.get_distributed_cache_manager')
    @patch('src.api.optimization.cache_performance_api.get_cache_consistency_manager')
    @patch('src.api.optimization.cache_performance_api.get_intelligent_warmup_manager')
    def test_get_cache_status_degraded(self, mock_warmup, mock_consistency, mock_distributed, mock_redis):
        """测试获取缓存状态 - 降级状态."""
        # 部分组件禁用
        mock_redis.return_value = None
        mock_distributed.return_value = AsyncMock()
        mock_consistency.return_value = None
        mock_warmup.return_value = AsyncMock()

        mock_distributed.return_value.get_cache_status.return_value = self.mock_cache_status
        mock_warmup.return_value.get_warmup_statistics.return_value = self.mock_warmup_stats

        response = self.client.get("/api/v1/cache/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"  # 有活跃组件
        assert data["components"]["redis_cluster"]["enabled"] is False
        assert data["components"]["consistency_manager"]["enabled"] is False

    @patch('src.api.optimization.cache_performance_api.get_redis_cluster_manager')
    @patch('src.api.optimization.cache_performance_api.get_distributed_cache_manager')
    @patch('src.api.optimization.cache_performance_api.get_cache_consistency_manager')
    @patch('src.api.optimization.cache_performance_api.get_intelligent_warmup_manager')
    def test_get_cache_status_unhealthy(self, mock_warmup, mock_consistency, mock_distributed, mock_redis):
        """测试获取缓存状态 - 不可用状态."""
        # 所有组件禁用
        mock_redis.return_value = None
        mock_distributed.return_value = None
        mock_consistency.return_value = None
        mock_warmup.return_value = None

        response = self.client.get("/api/v1/cache/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert all(not comp["enabled"] for comp in data["components"].values())

    # ==================== 性能指标端点测试 ====================

    @patch('src.api.optimization.cache_performance_api.get_redis_cluster_manager')
    @patch('src.api.optimization.cache_performance_api.get_distributed_cache_manager')
    @patch('src.api.optimization.cache_performance_api.get_cache_consistency_manager')
    @patch('src.api.optimization.cache_performance_api.get_intelligent_warmup_manager')
    def test_get_performance_metrics_default(self, mock_warmup, mock_consistency, mock_distributed, mock_redis):
        """测试获取性能指标 - 默认参数."""
        mock_redis.return_value = AsyncMock()
        mock_distributed.return_value = AsyncMock()
        mock_consistency.return_value = AsyncMock()
        mock_warmup.return_value = AsyncMock()

        mock_redis.return_value.get_cluster_status.return_value = self.mock_redis_status
        mock_distributed.return_value.get_cache_status.return_value = self.mock_cache_status
        mock_consistency.return_value.get_statistics.return_value = self.mock_consistency_stats
        mock_warmup.return_value.get_warmup_statistics.return_value = self.mock_warmup_stats

        response = self.client.get("/api/v1/cache/performance/metrics")

        assert response.status_code == 200
        data = response.json()
        assert data["time_range_hours"] == 24  # 默认值
        assert "metrics" in data
        assert "redis_cluster" in data["metrics"]
        assert "distributed_cache" in data["metrics"]
        assert "consistency_manager" in data["metrics"]
        assert "warmup_manager" in data["metrics"]

    @patch('src.api.optimization.cache_performance_api.get_redis_cluster_manager')
    def test_get_performance_metrics_filtered(self, mock_redis):
        """测试获取性能指标 - 组件过滤."""
        mock_redis.return_value = AsyncMock()
        mock_redis.return_value.get_cluster_status.return_value = self.mock_redis_status

        response = self.client.get("/api/v1/cache/performance/metrics?component=redis&time_range_hours=48")

        assert response.status_code == 200
        data = response.json()
        assert data["time_range_hours"] == 48
        assert "redis_cluster" in data["metrics"]
        assert len(data["metrics"]) == 1  # 只有redis组件

    def test_get_performance_metrics_invalid_time_range(self):
        """测试获取性能指标 - 无效时间范围."""
        response = self.client.get("/api/v1/cache/performance/metrics?time_range_hours=200")
        # FastAPI会自动验证Query参数并返回422
        assert response.status_code == 422

    # ==================== Redis集群管理端点测试 ====================

    @patch('src.api.optimization.cache_performance_api.get_redis_cluster_manager')
    def test_get_redis_cluster_status_success(self, mock_get_manager):
        """测试获取Redis集群状态 - 成功."""
        mock_manager = AsyncMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.get_cluster_status.return_value = self.mock_redis_status

        response = self.client.get("/api/v1/cache/cluster/status")

        assert response.status_code == 200
        data = response.json()
        assert "cluster_info" in data
        assert "metrics" in data

    @patch('src.api.optimization.cache_performance_api.get_redis_cluster_manager')
    def test_get_redis_cluster_status_disabled(self, mock_get_manager):
        """测试获取Redis集群状态 - 服务禁用."""
        mock_get_manager.return_value = None

        response = self.client.get("/api/v1/cache/cluster/status")

        assert response.status_code == 503
        data = response.json()
        assert "Redis集群管理器未启用" in data["detail"]

    @patch('src.api.optimization.cache_performance_api.get_redis_cluster_manager')
    def test_get_redis_cluster_status_exception(self, mock_get_manager):
        """测试获取Redis集群状态 - 异常."""
        mock_manager = AsyncMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.get_cluster_status.side_effect = Exception("Connection failed")

        response = self.client.get("/api/v1/cache/cluster/status")

        assert response.status_code == 500
        data = response.json()
        assert "获取Redis集群状态失败" in data["detail"]

    @patch('src.api.optimization.cache_performance_api.get_redis_cluster_manager')
    def test_add_redis_node_success(self, mock_get_manager):
        """测试添加Redis节点 - 成功."""
        mock_manager = AsyncMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.add_node.return_value = True

        node_config = {
            "node_id": "redis-node-4",
            "host": "192.168.1.104",
            "port": 6379
        }

        response = self.client.post("/api/v1/cache/cluster/nodes", json=node_config)

        assert response.status_code == 200
        data = response.json()
        assert "redis-node-4 添加成功" in data["message"]

    @patch('src.api.optimization.cache_performance_api.get_redis_cluster_manager')
    def test_add_redis_node_failure(self, mock_get_manager):
        """测试添加Redis节点 - 失败."""
        mock_manager = AsyncMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.add_node.return_value = False

        node_config = {"node_id": "redis-node-5"}

        response = self.client.post("/api/v1/cache/cluster/nodes", json=node_config)

        assert response.status_code == 400
        data = response.json()
        assert "添加Redis节点失败" in data["detail"]

    @patch('src.api.optimization.cache_performance_api.get_redis_cluster_manager')
    def test_remove_redis_node_success(self, mock_get_manager):
        """测试移除Redis节点 - 成功."""
        mock_manager = AsyncMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.remove_node.return_value = True

        response = self.client.delete("/api/v1/cache/cluster/nodes/redis-node-3")

        assert response.status_code == 200
        data = response.json()
        assert "redis-node-3 移除成功" in data["message"]

    @patch('src.api.optimization.cache_performance_api.get_redis_cluster_manager')
    def test_remove_redis_node_not_found(self, mock_get_manager):
        """测试移除Redis节点 - 节点不存在."""
        mock_manager = AsyncMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.remove_node.return_value = False

        response = self.client.delete("/api/v1/cache/cluster/nodes/nonexistent-node")

        assert response.status_code == 404
        data = response.json()
        assert "nonexistent-node 不存在" in data["detail"]

    # ==================== 分布式缓存管理端点测试 ====================

    @patch('src.api.optimization.cache_performance_api.get_distributed_cache_manager')
    def test_get_distributed_cache_status_success(self, mock_get_manager):
        """测试获取分布式缓存状态 - 成功."""
        mock_manager = AsyncMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.get_cache_status.return_value = self.mock_cache_status

        response = self.client.get("/api/v1/cache/distributed/status")

        assert response.status_code == 200
        data = response.json()
        assert "performance" in data

    @patch('src.api.optimization.cache_performance_api.get_distributed_cache_manager')
    def test_invalidate_cache_keys_success(self, mock_get_manager):
        """测试缓存失效 - 成功."""
        mock_manager = AsyncMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.invalidate_keys.return_value = {"invalidated": 1}

        request_data = {
            "keys": ["key1", "key2", "key3"]
        }

        response = self.client.post("/api/v1/cache/distributed/invalidate", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["invalidated"] == 3
        assert data["keys"] == ["key1", "key2", "key3"]

    @patch('src.api.optimization.cache_performance_api.get_distributed_cache_manager')
    def test_invalidate_cache_pattern_success(self, mock_get_manager):
        """测试缓存模式失效 - 成功."""
        mock_manager = AsyncMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.invalidate_pattern.return_value = 5

        request_data = {
            "keys": [],
            "pattern": "user:*"
        }

        response = self.client.post("/api/v1/cache/distributed/invalidate", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["invalidated"] == 5
        assert data["pattern"] == "user:*"

    @patch('src.api.optimization.cache_performance_api.get_distributed_cache_manager')
    def test_warmup_cache_success(self, mock_get_manager):
        """测试缓存预热 - 成功."""
        mock_manager = AsyncMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.warmup_cache.return_value = {
            "warmed_keys": 10,
            "failed_keys": 0,
            "execution_time": 2.5
        }

        request_data = {
            "keys": ["key1", "key2", "key3"],
            "ttl": 3600
        }

        response = self.client.post("/api/v1/cache/distributed/warmup", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["warmed_keys"] == 10

    # ==================== 缓存一致性管理端点测试 ====================

    @patch('src.api.optimization.cache_performance_api.get_cache_consistency_manager')
    def test_consistency_operation_success(self, mock_get_manager):
        """测试一致性操作 - 成功."""
        mock_manager = AsyncMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.read.return_value = {"success": True, "data": "value"}

        request_data = {
            "operation_type": "read",
            "target_keys": ["key1", "key2"],
            "parameters": {"session_id": "session123"}
        }

        response = self.client.post("/api/v1/cache/consistency/operations", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["operation_type"] == "read"
        assert data["status"] == "completed"
        assert "operation_id" in data

    @patch('src.api.optimization.cache_performance_api.get_cache_consistency_manager')
    def test_get_consistency_statistics_success(self, mock_get_manager):
        """测试获取一致性统计 - 成功."""
        mock_manager = AsyncMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.get_statistics.return_value = self.mock_consistency_stats

        response = self.client.get("/api/v1/cache/consistency/statistics")

        assert response.status_code == 200
        data = response.json()
        assert data["consistency_level"] == "strong"
        assert "statistics" in data

    @patch('src.api.optimization.cache_performance_api.get_cache_consistency_manager')
    def test_cleanup_consistency_session_success(self, mock_get_manager):
        """测试清理一致性会话 - 成功."""
        mock_manager = AsyncMock()
        mock_get_manager.return_value = mock_manager

        response = self.client.delete("/api/v1/cache/consistency/sessions/session123")

        assert response.status_code == 200
        data = response.json()
        assert "session123 数据已清理" in data["message"]

    # ==================== 智能预热管理端点测试 ====================

    @patch('src.api.optimization.cache_performance_api.get_intelligent_warmup_manager')
    def test_create_warmup_plan_success(self, mock_get_manager):
        """测试创建预热计划 - 成功."""
        mock_manager = AsyncMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.create_warmup_plan.return_value = "plan_123"

        request_data = {
            "strategy": "hybrid",
            "keys": ["key1", "key2", "key3"],
            "priority_levels": ["high", "medium"]
        }

        response = self.client.post("/api/v1/cache/warmup/plans", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["plan_id"] == "plan_123"
        assert data["strategy"] == "hybrid"
        assert data["keys_count"] == 3

    @patch('src.api.optimization.cache_performance_api.get_intelligent_warmup_manager')
    def test_get_warmup_plan_status_success(self, mock_get_manager):
        """测试获取预热计划状态 - 成功."""
        mock_manager = MagicMock()
        mock_manager.warmup_plans = {
            "plan_123": MagicMock(
                strategy=MagicMock(value="hybrid"),
                status="running",
                total_tasks=10,
                completed_tasks=7,
                failed_tasks=1,
                created_at=datetime.now(),
                scheduled_at=None
            )
        }
        mock_get_manager.return_value = mock_manager

        response = self.client.get("/api/v1/cache/warmup/plans/plan_123/status")

        assert response.status_code == 200
        data = response.json()
        assert data["plan_id"] == "plan_123"
        assert data["strategy"] == "hybrid"
        assert data["status"] == "running"

    @patch('src.api.optimization.cache_performance_api.get_intelligent_warmup_manager')
    def test_get_warmup_plan_status_not_found(self, mock_get_manager):
        """测试获取预热计划状态 - 计划不存在."""
        mock_manager = MagicMock()
        mock_manager.warmup_plans = {}  # 空计划列表
        mock_get_manager.return_value = mock_manager

        response = self.client.get("/api/v1/cache/warmup/plans/nonexistent/status")

        assert response.status_code == 404
        data = response.json()
        assert "nonexistent 不存在" in data["detail"]

    @patch('src.api.optimization.cache_performance_api.get_intelligent_warmup_manager')
    def test_execute_warmup_plan_success(self, mock_get_manager):
        """测试执行预热计划 - 成功."""
        mock_manager = MagicMock()
        mock_manager.warmup_plans = {"plan_123": MagicMock()}
        mock_get_manager.return_value = mock_manager

        response = self.client.post("/api/v1/cache/warmup/plans/plan_123/execute")

        assert response.status_code == 200
        data = response.json()
        assert "plan_123 开始执行" in data["message"]

    @patch('src.api.optimization.cache_performance_api.get_intelligent_warmup_manager')
    def test_cancel_warmup_plan_success(self, mock_get_manager):
        """测试取消预热计划 - 成功."""
        mock_manager = AsyncMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.cancel_plan.return_value = True

        response = self.client.delete("/api/v1/cache/warmup/plans/plan_123")

        assert response.status_code == 200
        data = response.json()
        assert "plan_123 已取消" in data["message"]

    # ==================== 缓存分析和优化端点测试 ====================

    @patch('src.api.optimization.cache_performance_api.get_redis_cluster_manager')
    def test_analyze_cache_performance_success(self, mock_get_manager):
        """测试缓存性能分析 - 成功."""
        mock_manager = AsyncMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.get_cluster_status.return_value = self.mock_redis_status

        request_data = {
            "analysis_type": "performance",
            "time_range_hours": 24,
            "include_details": True
        }

        response = self.client.post("/api/v1/cache/analysis", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["analysis_type"] == "performance"
        assert "results" in data
        assert "performance" in data["results"]

    def test_analyze_cache_performance_invalid_type(self):
        """测试缓存性能分析 - 无效分析类型."""
        request_data = {
            "analysis_type": "invalid_type",
            "time_range_hours": 24
        }

        response = self.client.post("/api/v1/cache/analysis", json=request_data)

        assert response.status_code == 400
        data = response.json()
        assert "不支持的分析类型" in data["detail"]

    @patch('src.api.optimization.cache_performance_api.get_distributed_cache_manager')
    def test_optimize_cache_system_cleanup_success(self, mock_get_manager):
        """测试缓存系统优化 - 清理成功."""
        mock_manager = AsyncMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.delete.return_value = True

        request_data = {
            "optimization_type": "cleanup",
            "target_keys": ["key1", "key2", "key3"]
        }

        response = self.client.post("/api/v1/cache/optimization", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["optimization_type"] == "cleanup"
        assert "optimization_id" in data

    def test_optimize_cache_system_invalid_type(self):
        """测试缓存系统优化 - 无效优化类型."""
        request_data = {
            "optimization_type": "invalid_type"
        }

        response = self.client.post("/api/v1/cache/optimization", json=request_data)

        assert response.status_code == 400
        data = response.json()
        assert "不支持的优化类型" in data["detail"]

    # ==================== 健康检查端点测试 ====================

    @patch('src.api.optimization.cache_performance_api.get_redis_cluster_manager')
    @patch('src.api.optimization.cache_performance_api.get_distributed_cache_manager')
    @patch('src.api.optimization.cache_performance_api.get_cache_consistency_manager')
    @patch('src.api.optimization.cache_performance_api.get_intelligent_warmup_manager')
    def test_cache_system_health_healthy(self, mock_warmup, mock_consistency, mock_distributed, mock_redis):
        """测试缓存系统健康检查 - 健康."""
        mock_redis.return_value = AsyncMock()
        mock_redis.return_value.get_cluster_status.return_value = self.mock_redis_status
        mock_distributed.return_value = AsyncMock()
        mock_consistency.return_value = AsyncMock()
        mock_warmup.return_value = AsyncMock()

        response = self.client.get("/api/v1/cache/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "cache_performance_monitoring"
        assert "components" in data

    @patch('src.api.optimization.cache_performance_api.get_redis_cluster_manager')
    def test_cache_system_health_unhealthy(self, mock_get_manager):
        """测试缓存系统健康检查 - 不健康."""
        mock_manager = AsyncMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.get_cluster_status.return_value = {
            "cluster_info": {"healthy_nodes": 0, "total_nodes": 3}
        }

        response = self.client.get("/api/v1/cache/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["components"]["redis_cluster"] == "unhealthy"

    # ==================== 边界和异常测试 ====================

    def test_invalid_json_request(self):
        """测试无效JSON请求."""
        response = self.client.post(
            "/api/v1/cache/distributed/invalidate",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_missing_required_fields(self):
        """测试缺少必填字段."""
        # 测试缺少keys字段
        request_data = {"ttl": 3600}  # 缺少keys
        response = self.client.post("/api/v1/cache/distributed/warmup", json=request_data)
        assert response.status_code == 422

    def test_invalid_query_parameters(self):
        """测试无效查询参数."""
        response = self.client.get("/api/v1/cache/performance/metrics?time_range_hours=0")
        assert response.status_code == 422

        response = self.client.get("/api/v1/cache/performance/metrics?time_range_hours=200")
        assert response.status_code == 422

    @patch('src.api.optimization.cache_performance_api.get_distributed_cache_manager')
    def test_internal_server_error(self, mock_get_manager):
        """测试内部服务器错误."""
        mock_manager = AsyncMock()
        mock_get_manager.return_value = mock_manager
        mock_manager.invalidate_keys.side_effect = Exception("Unexpected error")

        request_data = {"keys": ["key1"]}
        response = self.client.post("/api/v1/cache/distributed/invalidate", json=request_data)

        assert response.status_code == 500
        data = response.json()
        assert "缓存失效失败" in data["detail"]
