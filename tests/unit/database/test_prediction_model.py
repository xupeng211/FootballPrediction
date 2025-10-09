"""预测模型测试"""
import pytest
from datetime import datetime
from decimal import Decimal
from src.database.models.predictions import Prediction, PredictionStatus
from src.database.models.match import Match
from src.database.models.team import Team

class TestPredictionModel:
    """预测模型测试"""

    def test_prediction_creation(self):
        """测试预测创建"""
        home_team = Team(id=1, name="Team A")
        away_team = Team(id=2, name="Team B")
        match = Match(id=1, home_team=home_team, away_team=away_team)

        prediction = Prediction(
            id=1,
            match=match,
            predicted_winner="home",
            home_win_probability=Decimal("0.65"),
            draw_probability=Decimal("0.20"),
            away_win_probability=Decimal("0.15"),
            predicted_home_score=2,
            predicted_away_score=1,
            confidence_score=Decimal("0.85"),
            model_version="v1.0.0"
        )

        assert prediction.id == 1
        assert prediction.match == match
        assert prediction.predicted_winner == "home"
        assert prediction.status == PredictionStatus.PENDING

    def test_prediction_probability_validation(self):
        """测试预测概率验证"""
        home_team = Team(id=1, name="Team A")
        away_team = Team(id=2, name="Team B")
        match = Match(id=1, home_team=home_team, away_team=away_team)

        # 有效概率
        prediction = Prediction(
            id=1,
            match=match,
            predicted_winner="home",
            home_win_probability=Decimal("0.50"),
            draw_probability=Decimal("0.30"),
            away_win_probability=Decimal("0.20"),
            predicted_home_score=1,
            predicted_away_score=1
        )

        total = prediction.home_win_probability + prediction.draw_probability + prediction.away_win_probability
        assert total == Decimal("1.0")

        # 无效概率（总和不为1）
        with pytest.raises(ValueError):
            Prediction(
                id=2,
                match=match,
                predicted_winner="home",
                home_win_probability=Decimal("0.60"),
                draw_probability=Decimal("0.60"),
                away_win_probability=Decimal("0.10"),
                predicted_home_score=1,
                predicted_away_score=1
            )

    def test_prediction_accuracy(self):
        """测试预测准确性"""
        home_team = Team(id=1, name="Team A")
        away_team = Team(id=2, name="Team B")
        match = Match(
            id=1,
            home_team=home_team,
            away_team=away_team,
            home_score=2,
            away_score=1,
            status="completed"
        )

        prediction = Prediction(
            id=1,
            match=match,
            predicted_winner="home",
            predicted_home_score=2,
            predicted_away_score=1,
            home_win_probability=Decimal("0.60"),
            confidence_score=Decimal("0.80")
        )

        # 验证预测正确
        assert prediction.is_correct() is True

        # 验证比分预测准确
        assert prediction.is_score_exact() is True

        # 计算准确率得分
        accuracy = prediction.calculate_accuracy_score()
        assert accuracy > 0.8  # 应该有很高的准确率

    def test_prediction_status_transitions(self):
        """测试预测状态转换"""
        home_team = Team(id=1, name="Team A")
        away_team = Team(id=2, name="Team B")
        match = Match(id=1, home_team=home_team, away_team=away_team)

        prediction = Prediction(
            id=1,
            match=match,
            predicted_winner="home",
            status=PredictionStatus.PENDING
        )

        # 从待处理到已处理
        prediction.status = PredictionStatus.PROCESSED
        assert prediction.status == PredictionStatus.PROCESSED

        # 从已处理到已验证
        prediction.status = PredictionStatus.VERIFIED
        assert prediction.status == PredictionStatus.VERIFIED

    def test_prediction_features(self):
        """测试预测特征"""
        prediction = Prediction(
            id=1,
            features={
                "home_form": [1, 1, 0, 1, 1],
                "away_form": [0, 0, 1, 0, 0],
                "home_goals_avg": 2.5,
                "away_goals_avg": 0.8,
                "head_to_head_home_wins": 3,
                "head_to_head_away_wins": 1
            }
        )

        # 验证特征存在
        assert "home_form" in prediction.features
        assert len(prediction.features["home_form"]) == 5

        # 验证特征统计
        home_avg = prediction.calculate_team_form_avg("home")
        assert home_avg == 0.8  # (1+1+0+1+1)/5

    def test_prediction_model_info(self):
        """测试预测模型信息"""
        prediction = Prediction(
            id=1,
            model_version="v1.0.0",
            model_type="gradient_boosting",
            training_data_size=10000,
            features_count=25
        )

        assert prediction.model_version == "v1.0.0"
        assert prediction.model_type == "gradient_boosting"
        assert prediction.training_data_size == 10000
        assert prediction.features_count == 25

    def test_prediction_confidence_levels(self):
        """测试预测置信度级别"""
        prediction = Prediction(confidence_score=Decimal("0.90"))

        # 高置信度
        assert prediction.get_confidence_level() == "high"

        prediction.confidence_score = Decimal("0.75")
        assert prediction.get_confidence_level() == "medium"

        prediction.confidence_score = Decimal("0.50")
        assert prediction.get_confidence_level() == "low"

    def test_prediction_to_dict(self):
        """测试预测转换为字典"""
        home_team = Team(id=1, name="Team A")
        away_team = Team(id=2, name="Team B")
        match = Match(id=1, home_team=home_team, away_team=away_team)

        prediction = Prediction(
            id=1,
            match=match,
            predicted_winner="home",
            home_win_probability=Decimal("0.60"),
            confidence_score=Decimal("0.85"),
            model_version="v1.0.0"
        )

        pred_dict = prediction.to_dict()
        assert pred_dict["id"] == 1
        assert pred_dict["match_id"] == 1
        assert pred_dict["predicted_winner"] == "home"
        assert pred_dict["confidence_score"] == 0.85
        assert pred_dict["model_version"] == "v1.0.0"
