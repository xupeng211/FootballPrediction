"""
 models.py 测试文件
 测试机器学习模型管理API功能，包括MLflow集成
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from fastapi import FastAPI, Request, HTTPException
from fastapi.testclient import TestClient
import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from api.models import router

# 定义测试用的数据模型
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime

class ModelInfo(BaseModel):
    model_id: str
    model_name: str
    version: str
    status: str = "active"
    created_at: datetime = Field(default_factory=datetime.now)
    metrics: Optional[Dict[str, Any]] = None

class ModelService:
    def __init__(self):
        self.models = {}
        self.mlflow_client = None

    def get_active_models(self) -> List[ModelInfo]:
        """获取活跃模型列表"""
        return [
            ModelInfo(
                model_id="model_1",
                model_name="football_predictor",
                version="v1.0",
                status="active",
                metrics={"accuracy": 0.85, "precision": 0.82}
            )
        ]

    def get_model_by_id(self, model_id: str) -> Optional[ModelInfo]:
        """根据ID获取模型信息"""
        models = self.get_active_models()
        for model in models:
            if model.model_id == model_id:
                return model
        return None

    def get_model_metrics(self, model_id: str) -> Dict[str, Any]:
        """获取模型性能指标"""
        return {
            "accuracy": 0.85,
            "precision": 0.82,
            "recall": 0.78,
            "f1_score": 0.80
        }


class TestModelInfo:
    """测试 ModelInfo 数据模型"""

    def test_model_info_creation(self):
        """测试 ModelInfo 对象创建"""
        model_info = ModelInfo(
            model_id="test_model_1",
            model_name="test_model",
            version="v1.0",
            status="active",
            created_at=datetime.now(),
            metrics={"accuracy": 0.95}
        )

        assert model_info.model_id == "test_model_1"
        assert model_info.model_name == "test_model"
        assert model_info.version == "v1.0"
        assert model_info.status == "active"
        assert isinstance(model_info.created_at, datetime)
        assert model_info.metrics == {"accuracy": 0.95}

    def test_model_info_validation(self):
        """测试 ModelInfo 数据验证"""
        # 测试默认值和必填字段
        model_info = ModelInfo(
            model_id="test_model_1",
            model_name="test_model",
            version="v1.0"
        )
        assert model_info.status == "active"  # 默认值
        assert model_info.created_at is not None  # 默认工厂函数

        # 测试可选字段
        model_info_no_metrics = ModelInfo(
            model_id="test_model_2",
            model_name="test_model",
            version="v1.0"
        )
        assert model_info_no_metrics.metrics is None

    def test_model_info_serialization(self):
        """测试 ModelInfo 序列化"""
        model_info = ModelInfo(
            model_id="test_model_1",
            model_name="test_model",
            version="v1.0",
            status="active",
            created_at=datetime.now(),
            metrics={"accuracy": 0.95}
        )

        # 测试字典转换
        model_dict = model_info.dict()
        assert model_dict["model_id"] == "test_model_1"
        assert model_dict["model_name"] == "test_model"
        assert model_dict["version"] == "v1.0"
        assert model_dict["status"] == "active"


class TestModelService:
    """测试 ModelService 业务逻辑"""

    def setup_method(self):
        """设置测试环境"""
        self.model_service = ModelService()

    @patch('api.models.mlflow')
    def test_get_model_info_success(self, mock_mlflow):
        """测试获取模型信息成功"""
        # 模拟 MLflow 响应
        mock_client = Mock()
        mock_mlflow.tracking.MlflowClient.return_value = mock_client
        mock_client.get_model_info_by_name.return_value = Mock()

        model_info = self.model_service.get_model_info("test_model")
        assert model_info is not None
        mock_mlflow.tracking.MlflowClient.assert_called_once()

    @patch('api.models.mlflow')
    def test_get_model_info_not_found(self, mock_mlflow):
        """测试模型不存在"""
        mock_client = Mock()
        mock_mlflow.tracking.MlflowClient.return_value = mock_client
        mock_client.get_model_info_by_name.side_effect = Exception("Model not found")

        with pytest.raises(HTTPException) as exc_info:
            self.model_service.get_model_info("nonexistent_model")
        assert exc_info.value.status_code == 404

    @patch('api.models.mlflow')
    def test_list_models_success(self, mock_mlflow):
        """测试列出模型成功"""
        mock_client = Mock()
        mock_mlflow.tracking.MlflowClient.return_value = mock_client
        mock_client.list_registered_models.return_value = [
            Mock(name="model1", creation_timestamp=1234567890),
            Mock(name="model2", creation_timestamp=1234567891)
        ]

        models = self.model_service.list_models()
        assert len(models) == 2
        assert models[0]["name"] == "model1"

    @patch('api.models.mlflow')
    def test_list_models_empty(self, mock_mlflow):
        """测试空模型列表"""
        mock_client = Mock()
        mock_mlflow.tracking.MlflowClient.return_value = mock_client
        mock_client.list_registered_models.return_value = []

        models = self.model_service.list_models()
        assert models == []

    @patch('api.models.mlflow')
    def test_get_model_version(self, mock_mlflow):
        """测试获取模型版本"""
        mock_client = Mock()
        mock_mlflow.tracking.MlflowClient.return_value = mock_client
        mock_client.get_model_version.return_value = Mock(
            version="1",
            stage="production",
            creation_timestamp=1234567890
        )

        version_info = self.model_service.get_model_version("test_model", "1")
        assert version_info is not None
        assert version_info["version"] == "1"

    @patch('api.models.mlflow')
    def test_transition_model_stage(self, mock_mlflow):
        """测试模型阶段转换"""
        mock_client = Mock()
        mock_mlflow.tracking.MlflowClient.return_value = mock_client

        result = self.model_service.transition_model_stage(
            "test_model", "1", "production"
        )
        assert result is not None
        mock_client.transition_model_version_stage.assert_called_once()

    @patch('api.models.mlflow')
    def test_get_model_metrics(self, mock_mlflow):
        """测试获取模型指标"""
        mock_client = Mock()
        mock_mlflow.tracking.MlflowClient.return_value = mock_client
        mock_client.get_run.return_value = Mock(
            data=Mock(metrics={"accuracy": 0.95, "loss": 0.05})
        )

        metrics = self.model_service.get_model_metrics("test_model", "1")
        assert metrics == {"accuracy": 0.95, "loss": 0.05}

    @patch('api.models.mlflow')
    def test_get_model_history(self, mock_mlflow):
        """测试获取模型历史"""
        mock_client = Mock()
        mock_mlflow.tracking.MlflowClient.return_value = mock_client
        mock_client.search_model_versions.return_value = [
            Mock(version="1", creation_timestamp=1234567890),
            Mock(version="2", creation_timestamp=1234567891)
        ]

        history = self.model_service.get_model_history("test_model")
        assert len(history) == 2
        assert history[0]["version"] == "1"

    def test_validate_model_name(self):
        """测试模型名称验证"""
        assert self.model_service.validate_model_name("valid_model") == True
        assert self.model_service.validate_model_name("invalid model") == False
        assert self.model_service.validate_model_name("") == False

    def test_validate_version(self):
        """测试版本验证"""
        assert self.model_service.validate_version("1.0") == True
        assert self.model_service.validate_version("v1.0") == True
        assert self.model_service.validate_version("") == False

    def test_validate_stage(self):
        """测试阶段验证"""
        assert self.model_service.validate_stage("production") == True
        assert self.model_service.validate_stage("staging") == True
        assert self.model_service.validate_stage("invalid") == False


class TestModelAPI:
    """测试模型管理 API 端点"""

    def setup_method(self):
        """设置测试环境"""
        self.app = FastAPI()
        self.app.include_router(router)
        self.client = TestClient(self.app)

    @patch('api.models.ModelService.get_model_info')
    def test_get_model_info_endpoint(self, mock_get_info):
        """测试获取模型信息端点"""
        mock_get_info.return_value = ModelInfo(
            model_name="test_model",
            version="v1.0",
            stage="production",
            created_at=datetime.now(),
            metrics={"accuracy": 0.95}
        )

        response = self.client.get("/api/models/test_model")
        assert response.status_code == 200

        data = response.json()
        assert data["model_name"] == "test_model"
        assert data["version"] == "v1.0"

    @patch('api.models.ModelService.get_model_info')
    def test_get_model_info_not_found(self, mock_get_info):
        """测试模型不存在端点"""
        mock_get_info.side_effect = HTTPException(status_code=404, detail="Model not found")

        response = self.client.get("/api/models/nonexistent_model")
        assert response.status_code == 404

    @patch('api.models.ModelService.list_models')
    def test_list_models_endpoint(self, mock_list_models):
        """测试列出模型端点"""
        mock_list_models.return_value = [
            {"name": "model1", "version": "1"},
            {"name": "model2", "version": "1"}
        ]

        response = self.client.get("/api/models")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "model1"

    @patch('api.models.ModelService.get_model_version')
    def test_get_model_version_endpoint(self, mock_get_version):
        """测试获取模型版本端点"""
        mock_get_version.return_value = {
            "version": "1",
            "stage": "production",
            "created_at": "2023-01-01T00:00:00"
        }

        response = self.client.get("/api/models/test_model/versions/1")
        assert response.status_code == 200

        data = response.json()
        assert data["version"] == "1"
        assert data["stage"] == "production"

    @patch('api.models.ModelService.transition_model_stage')
    def test_transition_model_stage_endpoint(self, mock_transition):
        """测试模型阶段转换端点"""
        mock_transition.return_value = {
            "model_name": "test_model",
            "version": "1",
            "new_stage": "production"
        }

        response = self.client.post(
            "/api/models/test_model/versions/1/transition",
            json={"stage": "production"}
        )
        assert response.status_code == 200

    @patch('api.models.ModelService.get_model_metrics')
    def test_get_model_metrics_endpoint(self, mock_get_metrics):
        """测试获取模型指标端点"""
        mock_get_metrics.return_value = {
            "accuracy": 0.95,
            "loss": 0.05,
            "precision": 0.92
        }

        response = self.client.get("/api/models/test_model/versions/1/metrics")
        assert response.status_code == 200

        data = response.json()
        assert data["accuracy"] == 0.95
        assert data["loss"] == 0.05

    @patch('api.models.ModelService.get_model_history')
    def test_get_model_history_endpoint(self, mock_get_history):
        """测试获取模型历史端点"""
        mock_get_history.return_value = [
            {"version": "1", "created_at": "2023-01-01T00:00:00"},
            {"version": "2", "created_at": "2023-01-02T00:00:00"}
        ]

        response = self.client.get("/api/models/test_model/history")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 2
        assert data[0]["version"] == "1"

    def test_invalid_model_name(self):
        """测试无效模型名称"""
        response = self.client.get("/api/models/invalid model")
        assert response.status_code == 422  # 验证错误

    def test_invalid_version_format(self):
        """测试无效版本格式"""
        response = self.client.get("/api/models/test_model/versions/invalid")
        assert response.status_code == 422

    def test_invalid_stage_format(self):
        """测试无效阶段格式"""
        response = self.client.post(
            "/api/models/test_model/versions/1/transition",
            json={"stage": "invalid_stage"}
        )
        assert response.status_code == 422

    @patch('api.models.ModelService.get_model_info')
    def test_model_info_cache(self, mock_get_info):
        """测试模型信息缓存"""
        mock_get_info.return_value = ModelInfo(
            model_name="test_model",
            version="v1.0",
            stage="production",
            created_at=datetime.now(),
            metrics={"accuracy": 0.95}
        )

        # 第一次请求
        response1 = self.client.get("/api/models/test_model")
        assert response1.status_code == 200

        # 第二次请求（应该从缓存获取）
        response2 = self.client.get("/api/models/test_model")
        assert response2.status_code == 200

        # 验证只调用了一次服务
        assert mock_get_info.call_count == 1

    def test_concurrent_requests(self):
        """测试并发请求"""
        import threading
        import time

        def make_request():
            response = self.client.get("/api/models/test_model")
            assert response.status_code in [200, 404]

        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

    def test_rate_limiting(self):
        """测试速率限制"""
        # 快速发送多个请求
        for i in range(10):
            response = self.client.get("/api/models/test_model")
            assert response.status_code in [200, 404, 429]

    @patch('api.models.logger')
    def test_logging_endpoint(self, mock_logger):
        """测试端点日志记录"""
        response = self.client.get("/api/models/test_model")
        assert response.status_code in [200, 404]

        # 验证日志被记录
        mock_logger.info.assert_called()

    def test_error_handling(self):
        """测试错误处理"""
        # 测试各种错误情况
        response = self.client.get("/api/models/")
        assert response.status_code == 404

        response = self.client.get("/api/models/test_model/versions/")
        assert response.status_code == 404

        response = self.client.get("/api/models/test_model/versions/1/metrics/")
        assert response.status_code == 404


class TestModelServiceIntegration:
    """测试 ModelService 集成功能"""

    def setup_method(self):
        """设置测试环境"""
        self.model_service = ModelService()

    @patch('api.models.mlflow')
    def test_full_model_lifecycle(self, mock_mlflow):
        """测试完整的模型生命周期"""
        mock_client = Mock()
        mock_mlflow.tracking.MlflowClient.return_value = mock_client

        # 模拟模型创建
        mock_client.create_model.return_value = "model_id"

        # 模拟模型更新
        mock_client.update_model.return_value = True

        # 模拟模型删除
        mock_client.delete_model.return_value = True

        # 测试创建
        result = self.model_service.create_model("test_model")
        assert result == "model_id"

        # 测试更新
        result = self.model_service.update_model("test_model", {"description": "Updated"})
        assert result is True

        # 测试删除
        result = self.model_service.delete_model("test_model")
        assert result is True

    @patch('api.models.mlflow')
    def test_model_performance_monitoring(self, mock_mlflow):
        """测试模型性能监控"""
        mock_client = Mock()
        mock_mlflow.tracking.MlflowClient.return_value = mock_client

        # 模拟性能数据
        mock_client.get_run.return_value = Mock(
            data=Mock(metrics={
                "accuracy": 0.95,
                "precision": 0.92,
                "recall": 0.88,
                "f1_score": 0.90
            })
        )

        performance = self.model_service.get_model_performance("test_model", "1")
        assert performance["accuracy"] == 0.95
        assert performance["f1_score"] == 0.90

    def test_model_validation_rules(self):
        """测试模型验证规则"""
        # 测试模型名称规则
        valid_names = ["model1", "test_model", "football_predictor"]
        invalid_names = ["", "model 1", "model@1", "1model"]

        for name in valid_names:
            assert self.model_service.validate_model_name(name) == True

        for name in invalid_names:
            assert self.model_service.validate_model_name(name) == False

    def test_model_version_compatibility(self):
        """测试模型版本兼容性"""
        # 测试版本兼容性检查
        compatible_versions = [
            ("1.0.0", "1.0.1"),
            ("2.0.0", "2.1.0"),
            ("1.0.0", "1.0.0")
        ]

        for v1, v2 in compatible_versions:
            result = self.model_service.check_version_compatibility(v1, v2)
            assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])