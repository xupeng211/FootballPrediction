"""
缓存性能API测试
Cache Performance API Tests

专注于测试src/api/optimization/cache_performance_api.py模块
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

# 导入目标模块
try:
    from src.api.optimization.cache_performance_api import (
        CacheAnalysisRequest,
        CacheOptimizationRequest,
        ConsistencyRequest,
        WarmupRequest,
    )
    from src.api.optimization.cache_performance_api import (
        router as cache_performance_router,
    )

    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    pytest.skip(f"无法导入cache_performance_api模块: {e}", allow_module_level=True)


class TestCachePerformanceAPI:
    """缓存性能API测试"""

    @pytest.fixture
    def mock_cache_consistency_manager(self):
        """模拟缓存一致性管理器"""
        manager = AsyncMock()
        manager.get_status.return_value = {
            "status": "healthy",
            "consistency_score": 95.5,
            "nodes": 3,
            "pending_operations": 0,
        }
        manager.create_consistency_session.return_value = {"session_id": "test_session"}
        manager.get_statistics.return_value = {
            "total_sessions": 10,
            "successful_operations": 95,
            "failed_operations": 5,
        }
        return manager

    @pytest.fixture
    def mock_distributed_cache_manager(self):
        """模拟分布式缓存管理器"""
        manager = AsyncMock()
        manager.get_cluster_status.return_value = {
            "cluster_status": "healthy",
            "node_count": 3,
            "total_keys": 1000,
            "memory_usage_mb": 50.2,
        }
        manager.invalidate_keys.return_value = {"invalidated": 5}
        manager.warmup_cache.return_value = {"warmed_keys": 10}
        return manager

    @pytest.fixture
    def mock_intelligent_warmup_manager(self):
        """模拟智能预热管理器"""
        manager = AsyncMock()
        manager.create_warmup_plan.return_value = {
            "plan_id": "plan_123",
            "status": "created",
            "estimated_keys": 20,
        }
        manager.get_plan_status.return_value = {
            "plan_id": "plan_123",
            "status": "in_progress",
            "completed_keys": 10,
            "total_keys": 20,
        }
        manager.execute_warmup.return_value = {"started": True}
        manager.get_statistics.return_value = {
            "total_plans": 5,
            "successful_executions": 20,
            "total_warmed_keys": 100,
        }
        manager.record_access.return_value = True
        return manager

    @pytest.fixture
    def test_client(
        self,
        mock_cache_consistency_manager,
        mock_distributed_cache_manager,
        mock_intelligent_warmup_manager,
    ):
        """测试客户端"""
        with (
            patch(
                "src.api.optimization.cache_performance_api.get_cache_consistency_manager",
                return_value=mock_cache_consistency_manager,
            ),
            patch(
                "src.api.optimization.cache_performance_api.get_distributed_cache_manager",
                return_value=mock_distributed_cache_manager,
            ),
            patch(
                "src.api.optimization.cache_performance_api.get_intelligent_warmup_manager",
                return_value=mock_intelligent_warmup_manager,
            ),
        ):
            from fastapi import FastAPI

            app = FastAPI()
            app.include_router(cache_performance_router)
            return TestClient(app)

    def test_get_cache_status_success(self, test_client):
        """测试获取缓存状态 - 成功"""
        response = test_client.get("/api/v1/cache/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    def test_get_performance_metrics_success(self, test_client):
        """测试获取性能指标 - 成功"""
        response = test_client.get("/api/v1/cache/performance/metrics")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "metrics" in data
        assert "timestamp" in data
        assert isinstance(data["metrics"], dict)

    def test_get_cluster_status_success(self, test_client):
        """测试获取集群状态 - 成功"""
        response = test_client.get("/api/v1/cache/cluster/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "cluster_status" in data
        assert "node_count" in data
        assert "total_keys" in data
        assert data["cluster_status"] == "healthy"

    def test_post_cluster_nodes_success(self, test_client):
        """测试添加集群节点 - 成功"""
        payload = {"node_id": "node_004", "host": "192.168.1.104", "port": 6379}

        response = test_client.post("/api/v1/cache/cluster/nodes", json=payload)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "node_id" in data
        assert "status" in data
        assert data["status"] in ["added", "existing", "failed"]

    def test_delete_cluster_node_success(self, test_client):
        """测试删除集群节点 - 成功"""
        response = test_client.delete("/api/v1/cache/cluster/nodes/node_001")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "node_id" in data
        assert "status" in data
        assert data["status"] in ["removed", "not_found", "failed"]

    def test_get_distributed_status_success(self, test_client):
        """测试获取分布式缓存状态 - 成功"""
        response = test_client.get("/api/v1/cache/distributed/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "cluster_status" in data
        assert "node_count" in data
        assert "total_keys" in data

    def test_post_distributed_invalidate_success(self, test_client):
        """测试分布式缓存失效 - 成功"""
        payload = {"keys": ["user:123", "session:456"], "pattern": None}

        response = test_client.post(
            "/api/v1/cache/distributed/invalidate", json=payload
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "invalidated" in data
        assert isinstance(data["invalidated"], int)

    def test_post_distributed_warmup_success(self, test_client):
        """测试分布式缓存预热 - 成功"""
        payload = {"keys": ["config:app", "user:123:profile"], "ttl": 3600}

        response = test_client.post("/api/v1/cache/distributed/warmup", json=payload)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "warmed_keys" in data
        assert isinstance(data["warmed_keys"], int)

    def test_post_consistency_operations_success(self, test_client):
        """测试一致性操作 - 成功"""
        payload = {
            "operation_type": "verify",
            "target_keys": ["key1", "key2"],
            "parameters": {},
        }

        response = test_client.post(
            "/api/v1/cache/consistency/operations", json=payload
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "operation_id" in data
        assert "status" in data

    def test_get_consistency_statistics_success(self, test_client):
        """测试获取一致性统计 - 成功"""
        response = test_client.get("/api/v1/cache/consistency/statistics")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_sessions" in data
        assert "successful_operations" in data
        assert "failed_operations" in data

    def test_delete_consistency_session_success(self, test_client):
        """测试删除一致性会话 - 成功"""
        response = test_client.delete("/api/v1/cache/consistency/sessions/session_123")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "session_id" in data
        assert "status" in data

    def test_post_warmup_plans_success(self, test_client):
        """测试创建预热计划 - 成功"""
        payload = {
            "plan_name": "daily_warmup",
            "target_keys": ["config:*", "user:*:profile"],
            "schedule": "0 2 * * *",
            "ttl": 7200,
        }

        response = test_client.post("/api/v1/cache/warmup/plans", json=payload)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "plan_id" in data
        assert "status" in data

    def test_get_warmup_plan_status_success(self, test_client):
        """测试获取预热计划状态 - 成功"""
        response = test_client.get("/api/v1/cache/warmup/plans/plan_123/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "plan_id" in data
        assert "status" in data
        assert "completed_keys" in data
        assert "total_keys" in data

    def test_post_warmup_plan_execute_success(self, test_client):
        """测试执行预热计划 - 成功"""
        response = test_client.post("/api/v1/cache/warmup/plans/plan_123/execute")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "started" in data
        assert data["started"] is True

    def test_delete_warmup_plan_success(self, test_client):
        """测试删除预热计划 - 成功"""
        response = test_client.delete("/api/v1/cache/warmup/plans/plan_123")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "plan_id" in data
        assert "status" in data

    def test_get_warmup_statistics_success(self, test_client):
        """测试获取预热统计 - 成功"""
        response = test_client.get("/api/v1/cache/warmup/statistics")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_plans" in data
        assert "successful_executions" in data
        assert "total_warmed_keys" in data

    def test_post_warmup_record_access_success(self, test_client):
        """测试记录访问模式 - 成功"""
        payload = {
            "key_pattern": "user:*:profile",
            "access_frequency": "high",
            "access_time": "morning",
        }

        response = test_client.post("/api/v1/cache/warmup/record-access", json=payload)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "recorded" in data
        assert data["recorded"] is True

    def test_post_analysis_success(self, test_client):
        """测试缓存分析 - 成功"""
        payload = {
            "analysis_type": "performance",
            "time_range_hours": 24,
            "key_pattern": "user:*",
            "include_details": True,
        }

        response = test_client.post("/api/v1/cache/analysis", json=payload)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "analysis_id" in data
        assert "analysis_type" in data

    def test_post_optimization_success(self, test_client):
        """测试缓存优化 - 成功"""
        payload = {
            "optimization_type": "cleanup",
            "target_keys": ["temp:*", "expired:*"],
            "parameters": {"force": True},
        }

        response = test_client.post("/api/v1/cache/optimization", json=payload)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "optimization_id" in data
        assert "optimization_type" in data

    def test_health_check_endpoint_success(self, test_client):
        """测试健康检查端点 - 成功"""
        response = test_client.get("/api/v1/cache/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "components" in data
        assert isinstance(data["components"], dict)

    def test_error_handling_invalid_json(self, test_client):
        """测试错误处理 - 无效JSON"""
        response = test_client.post(
            "/api/v1/cache/analysis",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_error_handling_missing_required_fields(self, test_client):
        """测试错误处理 - 缺少必需字段"""
        # 测试缺少必需字段的分析请求
        payload = {"time_range_hours": 24}  # 缺少 analysis_type
        response = test_client.post("/api/v1/cache/analysis", json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_error_handling_invalid_values(self, test_client):
        """测试错误处理 - 无效值"""
        # 测试无效的时间范围
        payload = {
            "analysis_type": "performance",
            "time_range_hours": 200,  # 超出验证范围 (1-168)
            "include_details": True,
        }
        response = test_client.post("/api/v1/cache/analysis", json=payload)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_cache_status_error(self, test_client, mock_cache_consistency_manager):
        """测试缓存状态获取错误"""
        mock_cache_consistency_manager.get_status.side_effect = Exception(
            "Cache service unavailable"
        )

        response = test_client.get("/api/v1/cache/status")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "detail" in data
        assert "获取缓存状态失败" in data["detail"]

    def test_cluster_status_error(self, test_client, mock_distributed_cache_manager):
        """测试集群状态获取错误"""
        mock_distributed_cache_manager.get_cluster_status.side_effect = Exception(
            "Cluster connection failed"
        )

        response = test_client.get("/api/v1/cache/cluster/status")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "detail" in data
        assert "获取集群状态失败" in data["detail"]


class TestCachePerformanceAPIModels:
    """缓存性能API模型测试"""

    def test_cache_analysis_request_model(self):
        """测试缓存分析请求模型"""
        # 测试有效数据
        request = CacheAnalysisRequest(
            analysis_type="performance",
            time_range_hours=24,
            key_pattern="user:*",
            include_details=True,
        )

        assert request.analysis_type == "performance"
        assert request.time_range_hours == 24
        assert request.key_pattern == "user:*"
        assert request.include_details is True

    def test_cache_optimization_request_model(self):
        """测试缓存优化请求模型"""
        request = CacheOptimizationRequest(
            optimization_type="cleanup",
            target_keys=["temp:*", "expired:*"],
            parameters={"force": True},
        )

        assert request.optimization_type == "cleanup"
        assert request.target_keys == ["temp:*", "expired:*"]
        assert request.parameters == {"force": True}

    def test_warmup_request_model(self):
        """测试预热请求模型"""
        request = WarmupRequest(
            plan_name="daily_warmup",
            target_keys=["config:*"],
            schedule="0 2 * * *",
            ttl=7200,
        )

        assert request.plan_name == "daily_warmup"
        assert request.target_keys == ["config:*"]
        assert request.schedule == "0 2 * * *"
        assert request.ttl == 7200

    def test_consistency_request_model(self):
        """测试一致性请求模型"""
        request = ConsistencyRequest(
            operation_type="verify",
            target_keys=["key1", "key2"],
            parameters={"timeout": 30},
        )

        assert request.operation_type == "verify"
        assert request.target_keys == ["key1", "key2"]
        assert request.parameters == {"timeout": 30}


class TestCachePerformanceAPIIntegration:
    """缓存性能API集成测试"""

    def test_complete_cache_monitoring_workflow(self, test_client):
        """测试完整的缓存监控工作流程"""
        # 1. 检查缓存状态
        response = test_client.get("/api/v1/cache/status")
        assert response.status_code == 200

        # 2. 检查性能指标
        response = test_client.get("/api/v1/cache/performance/metrics")
        assert response.status_code == 200

        # 3. 检查集群状态
        response = test_client.get("/api/v1/cache/cluster/status")
        assert response.status_code == 200

        # 4. 检查分布式状态
        response = test_client.get("/api/v1/cache/distributed/status")
        assert response.status_code == 200

        # 5. 检查健康状态
        response = test_client.get("/api/v1/cache/health")
        assert response.status_code == 200

    def test_cache_management_workflow(self, test_client):
        """测试缓存管理工作流程"""
        # 1. 创建一致性操作
        consistency_payload = {
            "operation_type": "verify",
            "target_keys": ["user:123", "config:app"],
            "parameters": {},
        }
        response = test_client.post(
            "/api/v1/cache/consistency/operations", json=consistency_payload
        )
        assert response.status_code == 200

        # 2. 获取一致性统计
        response = test_client.get("/api/v1/cache/consistency/statistics")
        assert response.status_code == 200

        # 3. 执行分布式缓存失效
        invalidate_payload = {"keys": ["temp:*"], "pattern": None}
        response = test_client.post(
            "/api/v1/cache/distributed/invalidate", json=invalidate_payload
        )
        assert response.status_code == 200

        # 4. 执行分布式缓存预热
        warmup_payload = {"keys": ["config:app", "user:123:profile"], "ttl": 3600}
        response = test_client.post(
            "/api/v1/cache/distributed/warmup", json=warmup_payload
        )
        assert response.status_code == 200

    def test_cache_analysis_and_optimization_workflow(self, test_client):
        """测试缓存分析和优化工作流程"""
        # 1. 执行缓存分析
        analysis_payload = {
            "analysis_type": "performance",
            "time_range_hours": 24,
            "key_pattern": None,
            "include_details": True,
        }
        response = test_client.post("/api/v1/cache/analysis", json=analysis_payload)
        assert response.status_code == 200

        # 2. 执行缓存优化
        optimization_payload = {
            "optimization_type": "cleanup",
            "target_keys": None,
            "parameters": {"force": False},
        }
        response = test_client.post(
            "/api/v1/cache/optimization", json=optimization_payload
        )
        assert response.status_code == 200

    def test_warmup_management_workflow(self, test_client):
        """测试预热管理工作流程"""
        # 1. 创建预热计划
        warmup_payload = {
            "plan_name": "test_plan",
            "target_keys": ["config:*", "user:*:profile"],
            "schedule": "0 3 * * *",
            "ttl": 7200,
        }
        response = test_client.post("/api/v1/cache/warmup/plans", json=warmup_payload)
        assert response.status_code == 200
        plan_data = response.json()
        plan_id = plan_data.get("plan_id", "test_plan_id")

        # 2. 获取预热计划状态
        response = test_client.get(f"/api/v1/cache/warmup/plans/{plan_id}/status")
        assert response.status_code == 200

        # 3. 执行预热计划
        response = test_client.post(f"/api/v1/cache/warmup/plans/{plan_id}/execute")
        assert response.status_code == 200

        # 4. 记录访问模式
        access_payload = {
            "key_pattern": "user:*:profile",
            "access_frequency": "high",
            "access_time": "morning",
        }
        response = test_client.post(
            "/api/v1/cache/warmup/record-access", json=access_payload
        )
        assert response.status_code == 200

        # 5. 获取预热统计
        response = test_client.get("/api/v1/cache/warmup/statistics")
        assert response.status_code == 200

        # 6. 清理测试计划
        response = test_client.delete(f"/api/v1/cache/warmup/plans/{plan_id}")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_concurrent_api_requests(self):
        """测试并发API请求"""
        import asyncio

        with (
            patch(
                "src.api.optimization.cache_performance_api.get_cache_consistency_manager"
            ) as mock_consistency,
            patch(
                "src.api.optimization.cache_performance_api.get_distributed_cache_manager"
            ) as mock_distributed,
            patch(
                "src.api.optimization.cache_performance_api.get_intelligent_warmup_manager"
            ) as mock_warmup,
        ):

            # 设置模拟
            mock_consistency.return_value.get_status.return_value = {
                "status": "healthy"
            }
            mock_distributed.return_value.get_cluster_status.return_value = {
                "cluster_status": "healthy"
            }
            mock_warmup.return_value.get_statistics.return_value = {"total_plans": 5}

            # 创建应用
            from fastapi import FastAPI

            app = FastAPI()
            app.include_router(cache_performance_router)

            # 并发请求函数
            async def make_request(client, endpoint):
                return client.get(endpoint)

            # 使用TestClient创建并发请求
            with TestClient(app) as client:
                # 创建多个并发任务
                tasks = [
                    asyncio.create_task(
                        asyncio.to_thread(make_request, client, "/api/v1/cache/status")
                    ),
                    asyncio.create_task(
                        asyncio.to_thread(
                            make_request, client, "/api/v1/cache/cluster/status"
                        )
                    ),
                    asyncio.create_task(
                        asyncio.to_thread(
                            make_request, client, "/api/v1/cache/distributed/status"
                        )
                    ),
                    asyncio.create_task(
                        asyncio.to_thread(make_request, client, "/api/v1/cache/health")
                    ),
                ]

                # 等待所有请求完成
                responses = await asyncio.gather(*tasks)

                # 验证所有请求都成功
                for response in responses:
                    assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__])
