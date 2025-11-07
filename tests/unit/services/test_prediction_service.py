"""预测服务测试"""

from datetime import datetime
from unittest.mock import Mock

import pytest
from src.database.models.prediction import Prediction

from src.database.models.match import Match
from src.database.models.team import Team
from src.models.prediction_service import PredictionService


class TestPredictionService:
    """预测服务测试"""

    @pytest.fixture
    def mock_repository(self):
        """模拟预测仓库"""
        return Mock()

    @pytest.fixture
    def mock_model(self):
        """模拟ML模型"""
        mock_model = Mock()
        mock_model.predict.return_value = {
            "home_win": 0.65,
            "draw": 0.20,
            "away_win": 0.15,
        }
        return mock_model

    @pytest.fixture
    def service(self, mock_repository, mock_model):
        """创建预测服务"""
        return PredictionService(repository=mock_repository, model=mock_model)

    def test_predict_match(self, service, mock_repository, mock_model):
        """测试比赛预测"""
        # 准备测试数据
        home_team = Team(id=1, name="Team A")
        away_team = Team(id=2, name="Team B")
        match = Match(
            id=1,
            home_team=home_team,
            away_team=away_team,
            date=datetime(2024, 1, 1, 15, 0),
        )

        # 设置模拟返回
        mock_repository.get_match_features.return_value = {
            "home_form": [1, 1, 0],
            "away_form": [0, 0, 1],
            "head_to_head": {"home_wins": 2, "away_wins": 1},
        }

        # 调用方法
        result = service.predict_match(match.id)

        # 验证
        assert result["predicted_winner"] in ["home", "draw", "away"]
        assert "confidence" in result
        assert "probabilities" in result
        mock_model.predict.assert_called_once()

    def test_batch_predict(self, service, mock_repository, mock_model):
        """测试批量预测"""
        # 准备测试数据
        match_ids = [1, 2, 3]

        # 设置模拟返回
        mock_repository.get_matches_by_ids.return_value = [
            Mock(id=1),
            Mock(id=2),
            Mock(id=3),
        ]

        # 调用方法
        results = service.batch_predict(match_ids)

        # 验证
        assert len(results) == 3
        assert all("predicted_winner" in r for r in results)

    def test_get_prediction_accuracy(self, service, mock_repository):
        """测试获取预测准确率"""
        # 设置模拟返回
        mock_repository.get_completed_predictions.return_value = [
            Mock(is_correct=True),
            Mock(is_correct=True),
            Mock(is_correct=False),
            Mock(is_correct=True),
        ]

        # 调用方法
        accuracy = service.get_accuracy(30)  # 最近30天

        # 验证
        assert accuracy == 0.75  # 3/4 正确

    def test_update_prediction(self, service, mock_repository):
        """测试更新预测"""
        prediction_id = 1
        update_data = {"confidence": 0.90, "notes": "Updated prediction"}

        # 设置模拟返回
        mock_prediction = Mock(spec=Prediction)
        mock_repository.get_by_id.return_value = mock_prediction

        # 调用方法
        result = service.update_prediction(prediction_id, update_data)

        # 验证
        assert result == mock_prediction
        mock_repository.save.assert_called_once()

    def test_validate_prediction_input(self, service):
        """测试预测输入验证"""
        # 有效输入
        valid_input = {
            "match_id": 1,
            "features": {"home_form": [1, 1, 0], "away_form": [0, 1, 1]},
        }
        assert service.validate_input(valid_input) is True

        # 无效输入（缺少必要字段）
        invalid_input = {"features": {}}
        assert service.validate_input(invalid_input) is False

    def test_get_feature_importance(self, service, mock_model):
        """测试获取特征重要性"""
        # 设置模拟返回
        mock_model.get_feature_importance.return_value = {
            "home_form": 0.30,
            "away_form": 0.25,
            "head_to_head": 0.20,
            "goals_average": 0.15,
            "injuries": 0.10,
        }

        # 调用方法
        importance = service.get_feature_importance()

        # 验证
        assert "home_form" in importance
        assert importance["home_form"] == 0.30

    def test_calculate_confidence(self, service):
        """测试计算置信度"""
        probabilities = {"home_win": 0.65, "draw": 0.20, "away_win": 0.15}

        # 计算置信度（最高概率）
        confidence = service.calculate_confidence(probabilities)
        assert confidence == 0.65

    def test_predict_with_outcome(self, service, mock_repository):
        """测试带结果的预测"""
        # 准备测试数据
        match_id = 1
        actual_result = "home"

        # 设置模拟返回
        mock_prediction = Mock(
            predicted_winner="home", confidence=0.70, is_correct=True
        )
        mock_repository.get_prediction_by_match.return_value = mock_prediction

        # 调用方法
        result = service.predict_with_outcome(match_id, actual_result)

        # 验证
        assert result["correct"] is True
        assert result["predicted"] == actual_result

    def test_get_model_performance(self, service, mock_repository):
        """测试获取模型性能"""
        # 设置模拟返回
        mock_repository.get_performance_metrics.return_value = {
            "accuracy": 0.75,
            "precision": 0.80,
            "recall": 0.70,
            "f1_score": 0.75,
        }

        # 调用方法
        performance = service.get_model_performance()

        # 验证
        assert performance["accuracy"] == 0.75
        assert "precision" in performance
        assert "recall" in performance
        assert "f1_score" in performance
