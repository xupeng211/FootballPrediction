"""
TDD Red Phase Tests - PredictionService 未实现方法验证

Phase 3: PredictionService - TDD Red Phase (验证NotImplementedError)

这个文件专门用于验证TDD红阶段 - 确保所有关键方法都抛出NotImplementedError。
这证明了我们正在正确的红-绿-重构循环中。
"""

import pytest
from datetime import datetime
from unittest.mock import patch


class TestPredictionServiceRedPhase:
    """专门验证TDD红阶段的测试用例"""

    async def test_load_model_not_implemented(self):
        """验证_load_model方法抛出NotImplementedError"""
        from src.ml.inference.service import PredictionService

        service = PredictionService()

        with pytest.raises(NotImplementedError, match="TDD Red Phase"):
            await service._load_model()

    async def test_build_prediction_features_not_implemented(self):
        """验证_build_prediction_features方法抛出NotImplementedError"""
        from src.ml.inference.service import PredictionService

        service = PredictionService()

        with pytest.raises(NotImplementedError, match="TDD Red Phase"):
            await service._build_prediction_features(1, 2, datetime.now())

    async def test_run_inference_not_implemented(self):
        """验证_run_inference方法抛出NotImplementedError"""
        from src.ml.inference.service import PredictionService

        service = PredictionService()

        with pytest.raises(NotImplementedError, match="TDD Red Phase"):
            await service._run_inference({"feature1": 1.0})

    def test_save_model_not_implemented(self):
        """验证_save_model方法抛出NotImplementedError"""
        from src.ml.inference.service import PredictionService

        service = PredictionService()

        with pytest.raises(NotImplementedError, match="TDD Red Phase"):
            service._save_model()

    async def test_cold_start_training_integration_not_implemented(self):
        """验证冷启动训练流程中的NotImplementedError"""
        from src.ml.inference.service import PredictionService

        service = PredictionService()

        # 模拟模型文件不存在，触发冷启动训练
        with patch('src.ml.inference.service.os.path.exists', return_value=False):
            # 冷启动训练会调用_save_model，这应该抛出NotImplementedError
            with pytest.raises(NotImplementedError, match="TDD Red Phase"):
                await service.initialize()

    async def test_prediction_flow_not_implemented_without_mocks(self):
        """验证不使用mock的预测流程会抛出NotImplementedError"""
        from src.ml.inference.service import PredictionService

        service = PredictionService()
        service.is_ready = True

        # 这个预测会调用未实现的方法，应该抛出NotImplementedError
        with pytest.raises(NotImplementedError, match="TDD Red Phase"):
            await service.predict_match(1, 2, datetime.now())