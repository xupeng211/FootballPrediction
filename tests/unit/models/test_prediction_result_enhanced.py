"""
增强的预测服务测试
补充缺失的测试用例以提高覆盖率
"""

from datetime import datetime

import pytest

from src.models.prediction_service import PredictionResult

pytestmark = pytest.mark.unit


class TestPredictionResultEnhanced:
    """增强的PredictionResult测试类"""

    def test_prediction_result_to_dict_full_coverage(self):
        """测试预测结果转换为字典（完整字段覆盖）"""
        # 创建包含所有字段的预测结果
        created_at = datetime(2024, 1, 1, 12, 0, 0)
        verified_at = datetime(2024, 1, 1, 14, 0, 0)

        result = PredictionResult(
            match_id=12345,
            model_version="v1.0",
            model_name="football_baseline_model",
            home_win_probability=0.45,
            draw_probability=0.30,
            away_win_probability=0.25,
            predicted_result="home",
            confidence_score=0.75,
            features_used={"feature1": 1.0, "feature2": 2.0},
            prediction_metadata={"algorithm": "xgboost", "version": "1.0"},
            created_at=created_at,
            actual_result="home",
            is_correct=True,
            verified_at=verified_at,
        )

        result_dict = result.to_dict()

        # 验证所有字段都被正确转换
        assert result_dict["match_id"] == 12345
        assert result_dict["model_version"] == "v1.0"
        assert result_dict["model_name"] == "football_baseline_model"
        assert result_dict["home_win_probability"] == 0.45
        assert result_dict["draw_probability"] == 0.30
        assert result_dict["away_win_probability"] == 0.25
        assert result_dict["predicted_result"] == "home"
        assert result_dict["confidence_score"] == 0.75
        assert result_dict["features_used"] == {"feature1": 1.0, "feature2": 2.0}
        assert result_dict["prediction_metadata"] == {
            "algorithm": "xgboost",
            "version": "1.0",
        }
        assert result_dict["created_at"] == "2024-01-01T12:00:00"
        assert result_dict["actual_result"] == "home"
        assert result_dict["is_correct"] is True
        assert result_dict["verified_at"] == "2024-01-01T14:00:00"

    def test_prediction_result_to_dict_none_values(self):
        """测试预测结果转换为字典（None值处理）"""
        result = PredictionResult(
            match_id=12345,
            model_version="v1.0",
            model_name="football_baseline_model",
            # 其他字段为None
        )

        result_dict = result.to_dict()

        # 验证None值被正确处理
        assert result_dict["match_id"] == 12345
        assert result_dict["model_version"] == "v1.0"
        assert result_dict["model_name"] == "football_baseline_model"
        assert result_dict["home_win_probability"] == 0.0
        assert result_dict["draw_probability"] == 0.0
        assert result_dict["away_win_probability"] == 0.0
        assert result_dict["predicted_result"] == "draw"
        assert result_dict["confidence_score"] == 0.0
        assert result_dict["features_used"] is None
        assert result_dict["prediction_metadata"] is None
        assert result_dict["created_at"] is None
        assert result_dict["actual_result"] is None
        assert result_dict["is_correct"] is None
        assert result_dict["verified_at"] is None


# 如果直接运行此文件，则执行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
