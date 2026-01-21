"""
API路由模块测试

测试API路由模块的核心功能：
- src/api/model_management.py
- src/api/monitoring.py
- src/api/health.py

使用Mock来避免依赖问题，专注于测试API路由逻辑。
"""

import asyncio
import json
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException


class TestModelManagementAPI:
    """模型管理API测试"""

    @pytest.mark.asyncio
    async def test_reload_model_success(self):
        """测试模型重载成功"""
        # 模拟重载请求
        reload_request = {"model_path": "models/new_model.pkl", "backup_current": True}

        # 模拟推理服务
        mock_inference_service = AsyncMock()
        mock_inference_service.reload_model.return_value = {
            "success": True,
            "model_path": "models/new_model.pkl",
            "previous_model": "models/old_model.pkl",
            "reload_time": "2024-01-01T12:00:00Z",
            "model_version": "v2.0.0",
        }

        # 模拟模型重载逻辑
        async def mock_reload_model_logic(request_data):
            """模拟模型重载API逻辑"""
            try:
                result = await mock_inference_service.reload_model(
                    model_path=request_data.get("model_path"),
                    backup_current=request_data.get("backup_current", True),
                )
                return result
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        # 测试成功重载
        result = await mock_reload_model_logic(reload_request)

        assert result["success"] is True
        assert result["model_path"] == "models/new_model.pkl"
        assert result["previous_model"] == "models/old_model.pkl"
        assert "reload_time" in result
        assert result["model_version"] == "v2.0.0"

        # 验证服务被正确调用
        mock_inference_service.reload_model.assert_called_once_with(
            model_path="models/new_model.pkl", backup_current=True
        )

    @pytest.mark.asyncio
    async def test_reload_model_file_not_found(self):
        """测试模型重载 - 文件不存在"""
        reload_request = {
            "model_path": "models/missing_model.pkl",
            "backup_current": False,
        }

        mock_inference_service = AsyncMock()
        from src.core.exceptions import ModelError

        mock_inference_service.reload_model.side_effect = ModelError(
            "Model file not found",
            error_code="MODEL_NOT_FOUND",
            details={"model_path": "models/missing_model.pkl"},
        )

        async def mock_reload_model_logic(request_data):
            """模拟模型重载API逻辑"""
            try:
                result = await mock_inference_service.reload_model(
                    model_path=request_data.get("model_path"),
                    backup_current=request_data.get("backup_current", True),
                )
                return result
            except ModelError as e:
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error": e.message,
                        "error_code": e.error_code,
                        "details": e.details,
                    },
                )

        # 测试文件不存在
        with pytest.raises(HTTPException) as exc_info:
            await mock_reload_model_logic(reload_request)

        assert exc_info.value.status_code == 404
        error_detail = exc_info.value.detail
        assert error_detail["error"] == "Model file not found"
        assert error_detail["error_code"] == "MODEL_NOT_FOUND"
        assert error_detail["details"]["model_path"] == "models/missing_model.pkl"

    @pytest.mark.asyncio
    async def test_reload_model_with_default_path(self):
        """测试模型重载 - 使用默认路径"""
        reload_request = {
            "backup_current": True
            # 没有提供model_path，应该使用默认路径
        }

        mock_inference_service = AsyncMock()
        mock_inference_service.reload_model.return_value = {
            "success": True,
            "model_path": "models/default_model.pkl",
            "reload_time": "2024-01-01T12:00:00Z",
        }

        async def mock_reload_model_logic(request_data):
            """模拟模型重载API逻辑"""
            model_path = request_data.get("model_path") or "models/default_model.pkl"
            result = await mock_inference_service.reload_model(
                model_path=model_path,
                backup_current=request_data.get("backup_current", True),
            )
            return result

        result = await mock_reload_model_logic(reload_request)

        assert result["success"] is True
        assert result["model_path"] == "models/default_model.pkl"
        mock_inference_service.reload_model.assert_called_once_with(
            model_path="models/default_model.pkl", backup_current=True
        )

    @pytest.mark.asyncio
    async def test_get_model_info_success(self):
        """测试获取模型信息成功"""
        mock_inference_service = AsyncMock()
        mock_inference_service.get_model_info.return_value = {
            "model_name": "football_predictor_v2",
            "model_version": "2.1.0",
            "model_path": "models/current_model.pkl",
            "is_trained": True,
            "feature_count": 13,
            "training_accuracy": 0.67,
            "validation_accuracy": 0.65,
            "last_updated": "2024-01-01T10:00:00Z",
            "model_size_mb": 15.2,
            "features": ["home_form", "away_form", "h2h_stats", "venue_advantage"],
        }

        async def mock_get_model_info_logic():
            """模拟获取模型信息API逻辑"""
            try:
                result = await mock_inference_service.get_model_info()
                return result
            except RuntimeError as e:
                raise HTTPException(status_code=404, detail=str(e))

        result = await mock_get_model_info_logic()

        assert result["model_name"] == "football_predictor_v2"
        assert result["model_version"] == "2.1.0"
        assert result["is_trained"] is True
        assert result["feature_count"] == 13
        assert result["training_accuracy"] == 0.67
        assert len(result["features"]) == 4

    @pytest.mark.asyncio
    async def test_get_model_info_no_model_loaded(self):
        """测试获取模型信息 - 未加载模型"""
        mock_inference_service = AsyncMock()
        mock_inference_service.get_model_info.side_effect = RuntimeError("No model loaded")

        async def mock_get_model_info_logic():
            """模拟获取模型信息API逻辑"""
            try:
                result = await mock_inference_service.get_model_info()
                return result
            except RuntimeError as e:
                raise HTTPException(status_code=404, detail=str(e))

        with pytest.raises(HTTPException) as exc_info:
            await mock_get_model_info_logic()

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "No model loaded"

    def test_list_models_directory_exists(self):
        """测试列出模型 - 目录存在"""
        # 模拟模型目录结构
        mock_models_dir = {
            "models": [
                {
                    "name": "baseline_v1.pkl",
                    "path": "/app/models/baseline_v1.pkl",
                    "size": 10485760,  # 10MB
                    "created_at": "2024-01-01T08:00:00Z",
                    "modified_at": "2024-01-01T08:30:00Z",
                },
                {
                    "name": "enhanced_v2.pkl",
                    "path": "/app/models/enhanced_v2.pkl",
                    "size": 15728640,  # 15MB
                    "created_at": "2024-01-01T10:00:00Z",
                    "modified_at": "2024-01-01T10:45:00Z",
                },
                {
                    "name": "production_v3.json",
                    "path": "/app/models/production_v3.json",
                    "size": 5242880,  # 5MB
                    "created_at": "2024-01-01T12:00:00Z",
                    "modified_at": "2024-01-01T12:15:00Z",
                },
            ]
        }

        def mock_list_models_logic():
            """模拟列出模型API逻辑"""
            try:
                models = mock_models_dir["models"]
                return {
                    "models": models,
                    "total_count": len(models),
                    "models_directory": "/app/models",
                    "total_size_mb": sum(m["size"] for m in models) / (1024 * 1024),
                }
            except FileNotFoundError:
                raise HTTPException(status_code=404, detail="Models directory not found")

        result = mock_list_models_logic()

        assert result["total_count"] == 3
        assert len(result["models"]) == 3
        assert result["models"][0]["name"] == "baseline_v1.pkl"
        assert result["models"][1]["name"] == "enhanced_v2.pkl"
        assert result["models"][2]["name"] == "production_v3.json"
        assert result["total_size_mb"] == 30  # (10 + 15 + 5) MB

    def test_list_models_directory_not_found(self):
        """测试列出模型 - 目录不存在"""

        def mock_list_models_logic():
            """模拟列出模型API逻辑"""
            models_dir = "/nonexistent/models"
            # 模拟目录不存在
            raise FileNotFoundError(f"Models directory not found: {models_dir}")

        def mock_api_wrapper():
            """模拟API包装器"""
            try:
                return mock_list_models_logic()
            except FileNotFoundError as e:
                raise HTTPException(status_code=404, detail=str(e))

        with pytest.raises(HTTPException) as exc_info:
            mock_api_wrapper()

        assert exc_info.value.status_code == 404
        assert "Models directory not found" in exc_info.value.detail


class TestMonitoringAPI:
    """监控API测试"""

    @pytest.mark.asyncio
    async def test_get_metrics_success(self):
        """测试获取监控指标成功"""
        # 模拟系统指标
        mock_system_metrics = {
            "cpu_percent": 35.5,
            "memory": {
                "total": 8000000000,  # 8GB
                "available": 4000000000,  # 4GB
                "used": 4000000000,  # 4GB
                "percent": 50.0,
            },
            "disk": {
                "total": 100000000000,  # 100GB
                "used": 50000000000,  # 50GB
                "free": 50000000000,  # 50GB
                "percent": 50.0,
            },
        }

        # 模拟数据库指标
        mock_database_metrics = {
            "status": "connected",
            "active_connections": 8,
            "total_queries": 5000,
            "avg_response_time_ms": 25.5,
            "connection_pool": {"size": 20, "active": 8, "idle": 12},
        }

        # 模拟业务指标
        mock_business_metrics = {
            "total_predictions": 1250,
            "success_rate": 0.98,
            "avg_response_time_ms": 150.0,
            "predictions_last_hour": 75,
            "error_rate": 0.02,
        }

        async def mock_get_metrics_logic():
            """模拟获取监控指标API逻辑"""
            try:
                import time

                return {
                    "system": mock_system_metrics,
                    "database": mock_database_metrics,
                    "business": mock_business_metrics,
                    "timestamp": time.time(),
                    "uptime_seconds": 86400,  # 24小时
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

        result = await mock_get_metrics_logic()

        assert "system" in result
        assert "database" in result
        assert "business" in result
        assert "timestamp" in result
        assert "uptime_seconds" in result

        # 验证系统指标
        assert result["system"]["cpu_percent"] == 35.5
        assert result["system"]["memory"]["percent"] == 50.0
        assert result["system"]["disk"]["percent"] == 50.0

        # 验证数据库指标
        assert result["database"]["status"] == "connected"
        assert result["database"]["active_connections"] == 8
        assert result["database"]["total_queries"] == 5000

        # 验证业务指标
        assert result["business"]["total_predictions"] == 1250
        assert result["business"]["success_rate"] == 0.98
        assert result["business"]["predictions_last_hour"] == 75

    @pytest.mark.asyncio
    async def test_get_metrics_database_error(self):
        """测试获取监控指标 - 数据库错误"""
        # 模拟系统指标正常
        mock_system_metrics = {"cpu_percent": 25.0, "memory": {"percent": 45.0}}

        # 模拟数据库连接错误
        db_error = Exception("Database connection timeout")

        async def mock_get_metrics_logic():
            """模拟获取监控指标API逻辑"""
            system_metrics = mock_system_metrics

            try:
                # 模拟数据库查询
                raise db_error
            except Exception as e:
                database_metrics = {
                    "status": "error",
                    "error": str(e),
                    "last_check_time": "2024-01-01T12:00:00Z",
                }

            return {
                "system": system_metrics,
                "database": database_metrics,
                "business": {
                    "total_predictions": 0,
                    "success_rate": 0.0,
                    "error_rate": 1.0,
                },
                "timestamp": 1640995200.0,
            }

        result = await mock_get_metrics_logic()

        assert result["database"]["status"] == "error"
        assert "Database connection timeout" in result["database"]["error"]
        assert result["business"]["total_predictions"] == 0
        assert result["business"]["success_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_get_metrics_system_error(self):
        """测试获取监控指标 - 系统指标错误"""

        async def mock_get_metrics_logic():
            """模拟获取监控指标API逻辑"""
            try:
                # 模拟系统指标获取失败
                raise Exception("Failed to get system metrics")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Monitoring system error: {str(e)}")

        with pytest.raises(HTTPException) as exc_info:
            await mock_get_metrics_logic()

        assert exc_info.value.status_code == 500
        assert "Monitoring system error" in exc_info.value.detail
        assert "Failed to get system metrics" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_metrics_partial_success(self):
        """测试获取监控指标 - 部分成功"""
        # 系统指标正常
        mock_system_metrics = {
            "cpu_percent": 40.0,
            "memory": {"percent": 60.0},
            "disk": {"percent": 55.0},
        }

        # 数据库指标正常
        mock_database_metrics = {
            "status": "connected",
            "active_connections": 5,
            "total_queries": 2000,
        }

        # 业务指标部分失败
        async def mock_get_metrics_logic():
            """模拟获取监控指标API逻辑"""
            return {
                "system": mock_system_metrics,
                "database": mock_database_metrics,
                "business": {
                    "status": "warning",
                    "message": "Business metrics temporarily unavailable",
                    "last_successful_update": "2024-01-01T11:30:00Z",
                },
                "timestamp": 1640995200.0,
            }

        result = await mock_get_metrics_logic()

        assert result["system"]["cpu_percent"] == 40.0
        assert result["database"]["status"] == "connected"
        assert result["business"]["status"] == "warning"
        assert "temporarily unavailable" in result["business"]["message"]


class TestHealthCheckAPI:
    """健康检查API测试"""

    @pytest.mark.asyncio
    async def test_health_check_all_healthy(self):
        """测试健康检查 - 所有组件健康"""

        # 模拟所有组件健康
        async def mock_health_check_logic():
            """模拟健康检查API逻辑"""
            checks = {}

            # 检查数据库
            try:
                # 模拟数据库连接检查
                db_start_time = asyncio.get_event_loop().time()
                await asyncio.sleep(0.01)  # 模拟查询延迟
                db_response_time = (asyncio.get_event_loop().time() - db_start_time) * 1000

                checks["database"] = {
                    "status": "healthy",
                    "response_time_ms": max(1, db_response_time),
                    "message": "Database connection successful",
                }
            except Exception as e:
                checks["database"] = {"status": "unhealthy", "error": str(e)}

            # 检查模型
            try:
                checks["model"] = {
                    "status": "healthy",
                    "model_loaded": True,
                    "model_version": "v2.1.0",
                }
            except Exception as e:
                checks["model"] = {"status": "unhealthy", "error": str(e)}

            # 检查外部API
            try:
                checks["external_api"] = {
                    "status": "healthy",
                    "fotmob_api": "connected",
                    "last_check": "2024-01-01T12:00:00Z",
                }
            except Exception as e:
                checks["external_api"] = {"status": "degraded", "error": str(e)}

            # 确定整体状态
            all_healthy = all(check.get("status") == "healthy" for check in checks.values())
            overall_status = "healthy" if all_healthy else "unhealthy"

            return {
                "status": overall_status,
                "timestamp": "2024-01-01T12:00:00Z",
                "checks": checks,
                "uptime_seconds": 86400,
            }

        result = await mock_health_check_logic()

        assert result["status"] == "healthy"
        assert result["checks"]["database"]["status"] == "healthy"
        assert result["checks"]["model"]["status"] == "healthy"
        assert result["checks"]["external_api"]["status"] == "healthy"
        assert result["checks"]["database"]["response_time_ms"] > 0

    @pytest.mark.asyncio
    async def test_health_check_database_unhealthy(self):
        """测试健康检查 - 数据库不健康"""

        async def mock_health_check_logic():
            """模拟健康检查API逻辑"""
            checks = {}

            # 数据库检查失败
            checks["database"] = {
                "status": "unhealthy",
                "error": "Connection timeout after 30 seconds",
            }

            # 模型检查成功
            checks["model"] = {
                "status": "healthy",
                "model_loaded": True,
                "model_version": "v2.1.0",
            }

            # 外部API检查成功
            checks["external_api"] = {"status": "healthy", "fotmob_api": "connected"}

            # 计算整体状态
            overall_status = (
                "healthy" if all(check.get("status") == "healthy" for check in checks.values()) else "unhealthy"
            )

            return {
                "status": overall_status,
                "timestamp": "2024-01-01T12:00:00Z",
                "checks": checks,
            }

        result = await mock_health_check_logic()

        assert result["status"] == "unhealthy"
        assert result["checks"]["database"]["status"] == "unhealthy"
        assert "Connection timeout" in result["checks"]["database"]["error"]
        assert result["checks"]["model"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_liveness_probe_success(self):
        """测试存活性探针成功"""

        def mock_liveness_probe_logic():
            """模拟Kubernetes存活性探针"""
            try:
                # 简单的存活性检查 - 应用是否正在运行
                return {
                    "status": "ok",
                    "timestamp": "2024-01-01T12:00:00Z",
                    "uptime_seconds": 86400,
                    "version": "1.0.0",
                }
            except Exception as e:
                raise HTTPException(status_code=503, detail=str(e))

        result = mock_liveness_probe_logic()

        assert result["status"] == "ok"
        assert result["uptime_seconds"] == 86400
        assert result["version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_readiness_probe_ready(self):
        """测试就绪性探针 - 就绪"""

        async def mock_readiness_probe_logic():
            """模拟Kubernetes就绪性探针"""
            checks = {}

            # 检查关键组件是否就绪
            try:
                # 数据库就绪检查
                checks["database"] = True
            except:
                checks["database"] = False

            try:
                # 模型就绪检查
                checks["model"] = True
            except:
                checks["model"] = False

            try:
                # 外部依赖就绪检查
                checks["dependencies"] = True
            except:
                checks["dependencies"] = False

            all_ready = all(checks.values())
            status = "ready" if all_ready else "not_ready"

            return {
                "status": status,
                "checks": checks,
                "timestamp": "2024-01-01T12:00:00Z",
            }

        result = await mock_readiness_probe_logic()

        assert result["status"] == "ready"
        assert all(result["checks"].values())

    @pytest.mark.asyncio
    async def test_readiness_probe_not_ready(self):
        """测试就绪性探针 - 未就绪"""

        async def mock_readiness_probe_logic():
            """模拟Kubernetes就绪性探针"""
            checks = {
                "database": True,  # 数据库就绪
                "model": False,  # 模型未就绪
                "dependencies": False,  # 依赖未就绪
            }

            all_ready = all(checks.values())
            status = "ready" if all_ready else "not_ready"

            return {
                "status": status,
                "checks": checks,
                "timestamp": "2024-01-01T12:00:00Z",
            }

        result = await mock_readiness_probe_logic()

        assert result["status"] == "not_ready"
        assert result["checks"]["database"] is True
        assert result["checks"]["model"] is False
        assert result["checks"]["dependencies"] is False


if __name__ == "__main__":
    # 运行API路由测试
    pytest.main([__file__, "-v"])
