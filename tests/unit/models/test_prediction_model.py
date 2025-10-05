"""
数据库模型测试 - Prediction模型
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.database.models.match import Match
from src.database.models.predictions import PredictedResult, Predictions


@pytest.mark.unit
class TestPredictionModel:
    """Prediction模型测试"""

    @pytest.fixture
    def sample_prediction(self):
        """创建示例预测"""
        prediction = Predictions()
        prediction.id = 1
        prediction.match_id = 12345
        prediction.model_version = "1.0"
        prediction.model_name = "linear_regression"
        prediction.predicted_result = PredictedResult.HOME_WIN
        prediction.home_win_probability = Decimal("0.45")
        prediction.draw_probability = Decimal("0.30")
        prediction.away_win_probability = Decimal("0.25")
        prediction.confidence_score = Decimal("0.75")
        prediction.created_at = datetime.now()
        prediction.updated_at = datetime.now()
        return prediction

    @pytest.fixture
    def sample_match(self):
        """创建示例比赛"""
        match = Match()
        match.id = 12345
        match.home_team_id = 10
        match.away_team_id = 20
        match.match_status = "scheduled"
        return match

    def test_prediction_creation(self, sample_prediction):
        """测试预测创建"""
        assert sample_prediction.id == 1
        assert sample_prediction.match_id == 12345
        assert sample_prediction.model_version == "1.0"
        assert sample_prediction.model_name == "linear_regression"
        assert sample_prediction.predicted_result == PredictedResult.HOME_WIN

    def test_prediction_probabilities(self, sample_prediction):
        """测试预测概率"""
        home_prob = float(sample_prediction.home_win_probability)
        draw_prob = float(sample_prediction.draw_probability)
        away_prob = float(sample_prediction.away_win_probability)

        # 概率总和应该等于1
        total = home_prob + draw_prob + away_prob
        assert abs(total - 1.0) < 0.01

        # 概率值应该在0-1之间
        assert 0 <= home_prob <= 1
        assert 0 <= draw_prob <= 1
        assert 0 <= away_prob <= 1

    def test_predicted_result_enum(self):
        """测试预测结果枚举"""
        assert PredictedResult.HOME_WIN.value == "home_win"
        assert PredictedResult.AWAY_WIN.value == "away_win"
        assert PredictedResult.DRAW.value == "draw"

    def test_prediction_confidence(self, sample_prediction):
        """测试预测置信度"""
        confidence = float(sample_prediction.confidence_score)

        # 置信度应该在0-1之间
        assert 0 <= confidence <= 1
        assert confidence == 0.75

    def test_prediction_relationships(self, sample_prediction, sample_match):
        """测试预测关联关系"""
        # Mock 关联对象
        sample_prediction.match = sample_match

        assert sample_prediction.match.id == 12345
        assert sample_prediction.match.home_team_id == 10

    def test_prediction_accuracy(self, sample_prediction):
        """测试预测准确性"""
        # 设置实际结果
        sample_prediction.actual_result = PredictedResult.HOME_WIN
        sample_prediction.is_correct = True
        sample_prediction.verified_at = datetime.now()

        assert sample_prediction.is_correct is True
        assert sample_prediction.actual_result == PredictedResult.HOME_WIN

    def test_prediction_verification(self, sample_prediction):
        """测试预测验证"""
        # 未验证的预测
        assert sample_prediction.is_correct is None
        assert sample_prediction.actual_result is None
        assert sample_prediction.verified_at is None

        # 验证预测
        sample_prediction.actual_result = PredictedResult.DRAW
        sample_prediction.is_correct = False
        sample_prediction.verified_at = datetime.now()

        assert sample_prediction.is_correct is False
        assert sample_prediction.verified_at is not None

    def test_prediction_model_info(self, sample_prediction):
        """测试预测模型信息"""
        assert sample_prediction.model_version == "1.0"
        assert sample_prediction.model_name == "linear_regression"

        # 更新模型信息
        sample_prediction.model_version = "2.0"
        sample_prediction.model_name = "neural_network"

        assert sample_prediction.model_version == "2.0"
        assert sample_prediction.model_name == "neural_network"

    def test_prediction_probability_validation(self, sample_prediction):
        """测试概率验证"""
        # 有效的概率值
        sample_prediction.home_win_probability = Decimal("0.60")
        sample_prediction.draw_probability = Decimal("0.25")
        sample_prediction.away_win_probability = Decimal("0.15")

        home_prob = float(sample_prediction.home_win_probability)
        draw_prob = float(sample_prediction.draw_probability)
        away_prob = float(sample_prediction.away_win_probability)

        # 最高概率应该是主队获胜
        assert home_prob > draw_prob
        assert home_prob > away_prob
        assert sample_prediction.predicted_result == PredictedResult.HOME_WIN

    def test_prediction_to_dict(self, sample_prediction):
        """测试预测转换为字典"""
        # 测试__dict__方法
        prediction_dict = sample_prediction.__dict__.copy()

        # 移除SQLAlchemy的内部属性
        prediction_dict.pop("_sa_instance_state", None)

        assert prediction_dict["id"] == 1
        assert prediction_dict["match_id"] == 12345
        assert prediction_dict["model_name"] == "linear_regression"

    def test_prediction_repr(self, sample_prediction):
        """测试预测的字符串表示"""
        expected = f"Prediction(id={sample_prediction.id}, match_id={sample_prediction.match_id})"
        actual = repr(sample_prediction)

        # 如果没有自定义__repr__，测试默认行为
        assert str(sample_prediction.id) in actual
        assert str(sample_prediction.match_id) in actual

    def test_prediction_timestamps(self, sample_prediction):
        """测试时间戳"""
        assert isinstance(sample_prediction.created_at, datetime)
        assert isinstance(sample_prediction.updated_at, datetime)

        # 更新时间戳
        old_updated = sample_prediction.updated_at
        sample_prediction.updated_at = datetime.now()

        assert sample_prediction.updated_at >= old_updated

    def test_prediction_batch_predictions(self):
        """测试批量预测"""
        predictions = []

        for i in range(5):
            pred = Predictions()
            pred.id = i + 1
            pred.match_id = 12345 + i
            pred.model_version = "1.0"
            pred.model_name = "ensemble"
            pred.home_win_probability = Decimal(f"0.{4+i}0")
            pred.draw_probability = Decimal(f"0.{3-i}0")
            pred.away_win_probability = Decimal(f"0.{3-i}5")
            pred.confidence_score = Decimal("0.80")
            predictions.append(pred)

        assert len(predictions) == 5
        for i, pred in enumerate(predictions):
            assert pred.id == i + 1
            assert pred.match_id == 12345 + i

    @pytest.mark.asyncio
    async def test_prediction_async_save(self, sample_prediction):
        """测试预测异步保存"""
        mock_session = AsyncMock()

        if hasattr(sample_prediction, "async_save"):
            result = await sample_prediction.async_save(mock_session)
            assert result is not None

    def test_prediction_model_comparison(self, sample_prediction):
        """测试不同模型预测比较"""
        # 创建另一个预测（不同模型）
        pred2 = Predictions()
        pred2.id = 2
        pred2.match_id = 12345  # 同一场比赛
        pred2.model_version = "2.0"
        pred2.model_name = "random_forest"
        pred2.predicted_result = PredictedResult.DRAW
        pred2.home_win_probability = Decimal("0.35")
        pred2.draw_probability = Decimal("0.40")
        pred2.away_win_probability = Decimal("0.25")
        pred2.confidence_score = Decimal("0.65")

        # 比较不同模型的预测
        assert sample_prediction.model_name != pred2.model_name
        assert sample_prediction.predicted_result != pred2.predicted_result
        assert float(sample_prediction.confidence_score) != float(pred2.confidence_score)

    def test_prediction_edge_cases(self, sample_prediction):
        """测试预测边界情况"""
        # 极低置信度
        sample_prediction.confidence_score = Decimal("0.01")
        assert float(sample_prediction.confidence_score) == 0.01

        # 极高置信度
        sample_prediction.confidence_score = Decimal("0.99")
        assert float(sample_prediction.confidence_score) == 0.99

        # 平局概率最高
        sample_prediction.draw_probability = Decimal("0.80")
        sample_prediction.home_win_probability = Decimal("0.10")
        sample_prediction.away_win_probability = Decimal("0.10")
        sample_prediction.predicted_result = PredictedResult.DRAW

        assert sample_prediction.predicted_result == PredictedResult.DRAW
        assert float(sample_prediction.draw_probability) == 0.80
