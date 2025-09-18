"""
增强的模型层测试 - 快速提升覆盖率
针对src/models目录的核心功能测试
"""

from src.models.common_models import (DataValidationResult, FeatureVector,
                                      MatchData, ModelMetrics,
                                      PredictionRequest, PredictionResponse)


class TestPredictionRequest:
    """测试预测请求模型"""

    def test_prediction_request_init(self):
        """测试预测请求初始化"""
        request = PredictionRequest(
            match_id="123", home_team="Team A", away_team="Team B"
        )
        assert request.match_id == "123"
        assert request.home_team == "Team A"
        assert request.away_team == "Team B"

    def test_prediction_request_to_dict(self):
        """测试预测请求转字典"""
        request = PredictionRequest(
            match_id="123", home_team="Team A", away_team="Team B"
        )
        result = request.to_dict()
        assert isinstance(result, dict)
        assert result["match_id"] == "123"

    def test_prediction_request_from_dict(self):
        """测试从字典创建预测请求"""
        data = {"match_id": "456", "home_team": "Team C", "away_team": "Team D"}
        request = PredictionRequest.from_dict(data)
        assert request.match_id == "456"
        assert request.home_team == "Team C"

    def test_prediction_request_validation(self):
        """测试预测请求验证"""
        request = PredictionRequest(
            match_id="123", home_team="Team A", away_team="Team B"
        )
        assert request.is_valid() is True

    def test_prediction_request_invalid(self):
        """测试无效的预测请求"""
        request = PredictionRequest(match_id="", home_team="Team A", away_team="Team B")
        assert request.is_valid() is False


class TestPredictionResponse:
    """测试预测响应模型"""

    def test_prediction_response_init(self):
        """测试预测响应初始化"""
        response = PredictionResponse(
            match_id="123",
            home_win_prob=0.4,
            draw_prob=0.3,
            away_win_prob=0.3,
            confidence=0.8,
        )
        assert response.match_id == "123"
        assert response.home_win_prob == 0.4
        assert response.confidence == 0.8

    def test_prediction_response_probabilities_sum(self):
        """测试预测概率总和"""
        response = PredictionResponse(
            match_id="123",
            home_win_prob=0.4,
            draw_prob=0.3,
            away_win_prob=0.3,
            confidence=0.8,
        )
        total = response.home_win_prob + response.draw_prob + response.away_win_prob
        assert abs(total - 1.0) < 0.01

    def test_prediction_response_most_likely_outcome(self):
        """测试最可能的结果"""
        response = PredictionResponse(
            match_id="123",
            home_win_prob=0.5,
            draw_prob=0.2,
            away_win_prob=0.3,
            confidence=0.8,
        )
        outcome = response.get_most_likely_outcome()
        assert outcome == "home_win"

    def test_prediction_response_to_dict(self):
        """测试预测响应转字典"""
        response = PredictionResponse(
            match_id="123",
            home_win_prob=0.4,
            draw_prob=0.3,
            away_win_prob=0.3,
            confidence=0.8,
        )
        result = response.to_dict()
        assert isinstance(result, dict)
        assert "match_id" in result
        assert "confidence" in result


class TestMatchData:
    """测试比赛数据模型"""

    def test_match_data_init(self):
        """测试比赛数据初始化"""
        match = MatchData(
            match_id="123",
            home_team="Team A",
            away_team="Team B",
            match_date="2024-01-01",
        )
        assert match.match_id == "123"
        assert match.home_team == "Team A"

    def test_match_data_with_scores(self):
        """测试带比分的比赛数据"""
        match = MatchData(
            match_id="123",
            home_team="Team A",
            away_team="Team B",
            match_date="2024-01-01",
            home_score=2,
            away_score=1,
        )
        assert match.home_score == 2
        assert match.away_score == 1

    def test_match_data_result(self):
        """测试比赛结果判断"""
        match = MatchData(
            match_id="123",
            home_team="Team A",
            away_team="Team B",
            match_date="2024-01-01",
            home_score=2,
            away_score=1,
        )
        assert match.get_result() == "home_win"

    def test_match_data_draw(self):
        """测试平局结果"""
        match = MatchData(
            match_id="123",
            home_team="Team A",
            away_team="Team B",
            match_date="2024-01-01",
            home_score=1,
            away_score=1,
        )
        assert match.get_result() == "draw"

    def test_match_data_validation(self):
        """测试比赛数据验证"""
        match = MatchData(
            match_id="123",
            home_team="Team A",
            away_team="Team B",
            match_date="2024-01-01",
        )
        assert match.is_valid() is True

    def test_match_data_invalid_same_team(self):
        """测试相同队伍的无效比赛"""
        match = MatchData(
            match_id="123",
            home_team="Team A",
            away_team="Team A",
            match_date="2024-01-01",
        )
        assert match.is_valid() is False


class TestFeatureVector:
    """测试特征向量模型"""

    def test_feature_vector_init(self):
        """测试特征向量初始化"""
        features = FeatureVector(match_id="123", features=[0.1, 0.2, 0.3, 0.4, 0.5])
        assert features.match_id == "123"
        assert len(features.features) == 5

    def test_feature_vector_normalization(self):
        """测试特征向量归一化"""
        features = FeatureVector(match_id="123", features=[1.0, 2.0, 3.0, 4.0, 5.0])
        normalized = features.normalize()
        assert len(normalized) == 5
        assert all(0 <= f <= 1 for f in normalized)

    def test_feature_vector_scaling(self):
        """测试特征向量缩放"""
        features = FeatureVector(match_id="123", features=[1.0, 2.0, 3.0])
        scaled = features.scale(2.0)
        assert scaled == [2.0, 4.0, 6.0]

    def test_feature_vector_statistics(self):
        """测试特征向量统计"""
        features = FeatureVector(match_id="123", features=[1.0, 2.0, 3.0, 4.0, 5.0])
        stats = features.get_statistics()
        assert "mean" in stats
        assert "std" in stats
        assert "min" in stats
        assert "max" in stats

    def test_feature_vector_empty(self):
        """测试空特征向量"""
        features = FeatureVector(match_id="123", features=[])
        assert len(features.features) == 0
        assert features.is_empty() is True


class TestModelMetrics:
    """测试模型指标"""

    def test_model_metrics_init(self):
        """测试模型指标初始化"""
        metrics = ModelMetrics(
            accuracy=0.85, precision=0.82, recall=0.88, f1_score=0.85
        )
        assert metrics.accuracy == 0.85
        assert metrics.precision == 0.82

    def test_model_metrics_calculation(self):
        """测试模型指标计算"""
        metrics = ModelMetrics(
            accuracy=0.85, precision=0.82, recall=0.88, f1_score=0.85
        )
        overall_score = metrics.get_overall_score()
        assert isinstance(overall_score, float)
        assert 0 <= overall_score <= 1

    def test_model_metrics_comparison(self):
        """测试模型指标比较"""
        metrics1 = ModelMetrics(0.85, 0.82, 0.88, 0.85)
        metrics2 = ModelMetrics(0.80, 0.78, 0.83, 0.80)

        assert metrics1.is_better_than(metrics2) is True
        assert metrics2.is_better_than(metrics1) is False

    def test_model_metrics_to_dict(self):
        """测试模型指标转字典"""
        metrics = ModelMetrics(0.85, 0.82, 0.88, 0.85)
        result = metrics.to_dict()
        assert isinstance(result, dict)
        assert "accuracy" in result
        assert "f1_score" in result


class TestDataValidationResult:
    """测试数据验证结果"""

    def test_validation_result_valid(self):
        """测试有效的验证结果"""
        result = DataValidationResult(is_valid=True, errors=[], warnings=[])
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validation_result_invalid(self):
        """测试无效的验证结果"""
        result = DataValidationResult(
            is_valid=False,
            errors=["缺少必需字段", "数据格式错误"],
            warnings=["建议添加更多特征"],
        )
        assert result.is_valid is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 1

    def test_validation_result_add_error(self):
        """测试添加错误"""
        result = DataValidationResult(True, [], [])
        result.add_error("新的错误")
        assert result.is_valid is False
        assert "新的错误" in result.errors

    def test_validation_result_add_warning(self):
        """测试添加警告"""
        result = DataValidationResult(True, [], [])
        result.add_warning("新的警告")
        assert result.is_valid is True  # 警告不影响有效性
        assert "新的警告" in result.warnings

    def test_validation_result_summary(self):
        """测试验证结果摘要"""
        result = DataValidationResult(
            is_valid=False, errors=["错误1", "错误2"], warnings=["警告1"]
        )
        summary = result.get_summary()
        assert "2" in summary  # 错误数量
        assert "1" in summary  # 警告数量
