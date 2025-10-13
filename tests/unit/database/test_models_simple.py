"""
数据库模型简单测试
"""

import pytest
from datetime import datetime
from src.models.common_models import (
    DataValidationResult,
    FeatureVector,
    MatchData,
    ModelMetrics,
)


def test_data_validation_result():
    """测试数据验证结果"""
    _result = DataValidationResult(is_valid=True)
    assert result.is_valid is True

    result.add_error("Test error")
    assert result.is_valid is False
    assert "Test error" in result.errors


def test_feature_vector():
    """测试特征向量"""
    features = {"goals": 2, "assists": 1}
    vector = FeatureVector(
        match_id=1, features=features, feature_names=["goals", "assists"]
    )

    assert vector.match_id == 1
    assert vector.get_feature("goals") == 2
    assert vector.get_feature("missing") is None


def test_match_data():
    """测试比赛数据"""
    match = MatchData(
        match_id=1,
        home_team="Team A",
        away_team="Team B",
        league="Premier League",
        match_date=datetime.now(),
        status="upcoming",
    )

    assert match.match_id == 1
    assert match.home_team == "Team A"
    assert match.status == "upcoming"


def test_model_metrics():
    """测试模型指标"""
    metrics = ModelMetrics(
        model_name="test_model",
        model_version="v1.0",
        accuracy=0.85,
        precision=0.82,
        recall=0.88,
        f1_score=0.85,
        total_predictions=100,
        correct_predictions=85,
    )

    assert metrics.model_name == "test_model"
    assert metrics.accuracy == 0.85
    assert abs(metrics.error_rate - 0.15) < 0.001
