"""
Predictions模型增强测试

专门针对src/database/models/predictions.py中未覆盖的代码路径进行测试，提升覆盖率从71%到95%+
主要覆盖：get_predicted_score, get_feature_importance_dict, generate_explanation等方法
"""

import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

from sqlalchemy.orm import Session

# 尝试导入 Predictions
try:
    from src.database.models.predictions import Predictions
except ImportError:
    # 如果导入失败，创建模拟类
    class Predictions:  # type: ignore[no-redef]
        pass


class TestPredictionsModelEnhancedCoverage:
    """测试Predictions模型未覆盖的方法"""

    def test_get_predicted_score_with_values(self):
        """测试获取预测比分方法 - 有预测值的情况 (覆盖166行)"""
        from src.database.models.predictions import Predictions

        # 创建有预测比分的Predictions实例
        prediction = Predictions()
        prediction.predicted_home_score = Decimal("2.3")
        prediction.predicted_away_score = Decimal("1.7")

        # 执行测试
        result = prediction.get_predicted_score()

        # 验证结果格式化正确
        assert result == "2.3-1.7"

    def test_get_predicted_score_with_none_values(self):
        """测试获取预测比分方法 - 无预测值的情况"""

        # 创建无预测比分的Predictions实例
        prediction = Predictions()
        prediction.predicted_home_score = None
        prediction.predicted_away_score = Decimal("1.7")

        # 执行测试
        result = prediction.get_predicted_score()

        # 验证返回None
        assert result is None

    def test_get_feature_importance_dict_with_dict_type(self):
        """测试获取特征重要性字典 - dict类型 (覆盖175-180行)"""

        # 创建带dict类型feature_importance的实例
        prediction = Predictions()
        feature_dict = {
            "attack_strength": 0.3,
            "defense_rating": 0.2,
            "home_advantage": 0.15,
        }
        prediction.feature_importance = feature_dict

        # 执行测试
        result = prediction.get_feature_importance_dict()

        # 验证直接返回dict
        assert result == feature_dict
        assert isinstance(result, dict)

    def test_get_feature_importance_dict_with_invalid_type(self):
        """测试获取特征重要性字典 - 无效类型 (覆盖178-179行)"""

        # 创建带无效类型feature_importance的实例
        prediction = Predictions()
        prediction.feature_importance = ["invalid", "type"]  # 列表类型，应返回None

        # 执行测试
        result = prediction.get_feature_importance_dict()

        # 验证返回None
        assert result is None

    def test_get_top_features_with_empty_importance(self):
        """测试获取最重要特征 - 空特征重要性 (覆盖194行)"""

        # 创建无特征重要性的实例
        prediction = Predictions()
        prediction.feature_importance = None

        # 执行测试
        result = prediction.get_top_features(top_n=3)

        # 验证返回空列表
        assert result == []
        assert isinstance(result, list)

    def test_get_top_features_with_valid_features(self):
        """测试获取最重要特征 - 有效特征"""

        # 创建带特征重要性的实例
        prediction = Predictions()
        feature_dict = {
            "attack_strength": 0.4,
            "defense_rating": 0.25,
            "home_advantage": 0.15,
            "recent_form": 0.1,
            "head_to_head": 0.1,
        }
        prediction.feature_importance = json.dumps(feature_dict)

        # 执行测试
        result = prediction.get_top_features(top_n=3)

        # 验证返回前3个特征，按重要性降序
        assert len(result) == 3
        assert result[0]["feature"] == "attack_strength"
        assert result[0]["importance"] == 0.4
        assert result[1]["feature"] == "defense_rating"
        assert result[1]["importance"] == 0.25

    def test_generate_explanation_complete(self):
        """测试生成预测解释方法 (覆盖299-325行)"""

        # 创建完整的预测实例
        prediction = Predictions()
        prediction.match_id = 1
        prediction.model_name = "advanced_ml_v2"
        prediction.model_version = "2.1.0"
        prediction.predicted_at = datetime(2024, 1, 15, 14, 30)
        prediction.home_win_probability = Decimal("0.45")
        prediction.draw_probability = Decimal("0.25")
        prediction.away_win_probability = Decimal("0.30")
        prediction.predicted_home_score = Decimal("2.1")
        prediction.predicted_away_score = Decimal("1.3")
        prediction.over_under_prediction = Decimal("0.65")
        prediction.btts_probability = Decimal("0.58")
        prediction.feature_importance = json.dumps(
            {"attack_strength": 0.35, "defense_rating": 0.28, "home_advantage": 0.18}
        )

        # 执行测试
        result = prediction.generate_explanation()

        # 验证生成的解释包含所有必要字段
        assert "prediction_summary" in result
        assert "confidence_level" in result
        assert "model_info" in result
        assert "probabilities" in result
        assert "predicted_score" in result
        assert "key_factors" in result
        assert "additional_predictions" in result

        # 验证model_info字段
        model_info = result["model_info"]
        assert model_info["model_name"] == "advanced_ml_v2"
        assert model_info["model_version"] == "2.1.0"
        assert "2024-01-15" in model_info["predicted_at"]

        # 验证additional_predictions字段
        additional = result["additional_predictions"]
        assert additional["over_2_5_goals"] == 0.65
        assert additional["both_teams_score"] == 0.58

        # 验证predicted_score
        assert result["predicted_score"] == "2.1-1.3"

    def test_generate_explanation_minimal_data(self):
        """测试生成预测解释方法 - 最少数据情况"""

        # 创建最少数据的预测实例
        prediction = Predictions()
        prediction.model_name = "basic_model"
        prediction.predicted_at = None
        prediction.over_under_prediction = None
        prediction.btts_probability = None
        prediction.feature_importance = None
        # 设置必需的概率字段，否则get_probabilities_dict()会报错
        prediction.home_win_probability = Decimal("0.33")
        prediction.draw_probability = Decimal("0.33")
        prediction.away_win_probability = Decimal("0.34")

        # 执行测试
        result = prediction.generate_explanation()

        # 验证结构完整但数据为空
        assert result["model_info"]["predicted_at"] is None
        assert result["additional_predictions"]["over_2_5_goals"] is None
        assert result["additional_predictions"]["both_teams_score"] is None
        assert result["key_factors"] == []  # 空特征重要性应返回空列表

    def test_get_match_predictions_classmethod(self):
        """测试获取比赛预测类方法 (覆盖328-330行)"""

        # 创建模拟会话
        mock_session = Mock(spec=Session)
        mock_query = Mock()
        mock_session.query.return_value = mock_query

        # 创建模拟预测结果
        mock_predictions = [Mock(), Mock(), Mock()]
        mock_query.filter.return_value.order_by.return_value.all.return_value = (
            mock_predictions
        )

        # 执行测试
        result = Predictions.get_match_predictions(mock_session, match_id=123)

        # 验证查询被正确调用
        mock_session.query.assert_called_once_with(Predictions)
        mock_query.filter.assert_called_once()

        # 验证返回结果
        assert result == mock_predictions

    def test_calculate_model_accuracy_no_predictions(self):
        """测试计算模型准确率 - 无预测数据 (覆盖393-394行)"""

        # 创建模拟会话，返回空预测列表
        mock_session = Mock(spec=Session)
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.join.return_value.filter.return_value.all.return_value = []

        # 执行测试
        result = Predictions.calculate_model_accuracy(
            mock_session, model_name="test_model", days=7
        )

        # 验证返回只包含总预测数为0
        assert result == {"total_predictions": 0}

    def test_calculate_model_accuracy_with_predictions(self):
        """测试计算模型准确率 - 有预测数据 (覆盖401-417行)"""

        # 创建模拟会话
        mock_session = Mock(spec=Session)
        mock_query = Mock()
        mock_session.query.return_value = mock_query

        # 创建模拟预测和比赛
        mock_prediction1 = Mock()
        mock_match1 = Mock()
        mock_match1.get_result.return_value = "home_win"
        mock_prediction1.match = mock_match1
        mock_prediction1.calculate_accuracy.return_value = {
            "prediction_correct": True,
            "brier_score": 0.15,
            "log_loss": 0.25,
        }

        mock_prediction2 = Mock()
        mock_match2 = Mock()
        mock_match2.get_result.return_value = "away_win"
        mock_prediction2.match = mock_match2
        mock_prediction2.calculate_accuracy.return_value = {
            "prediction_correct": False,
            "brier_score": 0.35,
            "log_loss": 0.65,
        }

        mock_predictions = [mock_prediction1, mock_prediction2]
        mock_query.join.return_value.filter.return_value.all.return_value = (
            mock_predictions
        )

        # 执行测试
        with patch("src.database.models.predictions.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2024, 1, 15)

            result = Predictions.calculate_model_accuracy(
                mock_session, model_name="test_model", days=7
            )

        # 验证结果计算正确
        assert result["total_predictions"] == 2
        assert result["accuracy_rate"] == 0.5  # 1/2
        assert result["average_brier_score"] == 0.25  # (0.15 + 0.35) / 2
        assert result["average_log_loss"] == 0.45  # (0.25 + 0.65) / 2

    def test_calculate_model_accuracy_with_none_result(self):
        """测试计算模型准确率 - 比赛结果为None的情况"""

        # 创建模拟会话
        mock_session = Mock(spec=Session)
        mock_query = Mock()
        mock_session.query.return_value = mock_query

        # 创建比赛结果为None的预测
        mock_prediction = Mock()
        mock_match = Mock()
        mock_match.get_result.return_value = None  # 比赛还未结束
        mock_prediction.match = mock_match

        mock_predictions = [mock_prediction]
        mock_query.join.return_value.filter.return_value.all.return_value = (
            mock_predictions
        )

        # 执行测试
        with patch("src.database.models.predictions.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2024, 1, 15)

            result = Predictions.calculate_model_accuracy(
                mock_session, model_name="test_model", days=7
            )

        # 验证没有调用calculate_accuracy，准确率为0
        assert result["total_predictions"] == 1
        assert result["accuracy_rate"] == 0.0
        assert result["average_brier_score"] == 0.0
        assert result["average_log_loss"] == 0.0

    def test_generate_explanation_edge_cases(self):
        """测试生成预测解释的边界情况"""

        # 测试数值类型转换
        prediction = Predictions()
        prediction.over_under_prediction = "0.75"  # 字符串类型
        prediction.btts_probability = "0.62"  # 字符串类型
        # 设置必需的概率字段
        prediction.home_win_probability = Decimal("0.4")
        prediction.draw_probability = Decimal("0.3")
        prediction.away_win_probability = Decimal("0.3")

        result = prediction.generate_explanation()

        # 验证字符串被正确转换为float
        additional = result["additional_predictions"]
        assert additional["over_2_5_goals"] == 0.75
        assert additional["both_teams_score"] == 0.62
