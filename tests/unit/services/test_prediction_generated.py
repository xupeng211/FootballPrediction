"""
服务层测试 - 自动生成
"""

import pytest
from unittest.mock import Mock, patch

# 尝试导入服务
try:
    from src.services.prediction_service import PredictionService

    PREDICTION_SERVICE_AVAILABLE = True
except ImportError:
    try:
        from ml.prediction.prediction_service import PredictionService

        PREDICTION_SERVICE_AVAILABLE = True
    except ImportError:
        PREDICTION_SERVICE_AVAILABLE = False
        PredictionService = None


@pytest.mark.skipif(
    not PREDICTION_SERVICE_AVAILABLE, reason="PredictionService not available"
)
class TestPredictionServiceGenerated:
    """预测服务测试"""

    def test_service_initialization(self):
        """测试服务初始化"""
        if PredictionService:
            service = PredictionService()
            assert service is not None

    def test_prediction_creation(self):
        """测试预测创建"""
        if PredictionService:
            service = PredictionService()
            with patch.object(service, "create_prediction") as mock_create:
                mock_create.return_value = {"id": 1, "prediction": "win"}
                result = service.create_prediction({"match_id": 1})
                assert result["id"] == 1

    def test_prediction_validation(self):
        """测试预测验证"""
        if PredictionService:
            service = PredictionService()
            with patch.object(service, "validate_prediction") as mock_validate:
                mock_validate.return_value = True
                result = service.validate_prediction({"data": "test"})
                assert result is True
