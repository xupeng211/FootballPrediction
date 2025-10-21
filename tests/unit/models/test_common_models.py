"""
测试通用模型
"""

from datetime import datetime
from pydantic import ValidationError
import pytest

from src.models.common_models import (
    DataValidationResult,
    FeatureVector,
    MatchData,
    ModelMetrics,
)


def test_data_validation_result():
    """测试数据验证结果"""
    # 测试有效的验证结果
    _result = DataValidationResult(is_valid=True)
    assert _result.is_valid is True
    assert _result.errors == []
    assert _result.warnings == []

    # 测试无效的验证结果
    _result = DataValidationResult(is_valid=False)
    assert _result.is_valid is False

    # 测试添加错误
    result.add_error("Invalid email format")
    assert _result.is_valid is False
    assert "Invalid email format" in result.errors

    # 测试添加警告
    result.add_warning("Deprecated field used")
    assert "Deprecated field used" in result.warnings


def test_feature_vector():
    """测试特征向量"""
    # 测试创建特征向量
    features = {"goals": 2.5, "assists": 1.0, "minutes": 90}
    vector = FeatureVector(
        match_id=123, features=features, feature_names=["goals", "assists", "minutes"]
    )

    assert vector.match_id == 123
    assert vector.features == features
    assert vector.get_feature("goals") == 2.5
    assert vector.get_feature("nonexistent") is None

    # 测试设置特征
    vector.set_feature("cards", 2.0)
    assert vector.get_feature("cards") == 2.0
    assert "cards" in vector.feature_names


def test_match_data():
    """测试比赛数据"""
    now = datetime.now()
    match = MatchData(
        match_id=456,
        home_team="Team A",
        away_team="Team B",
        league="Premier League",
        match_date=now,
        status="upcoming",
    )

    assert match.match_id == 456
    assert match.home_team == "Team A"
    assert match.away_team == "Team B"
    assert match.status == "upcoming"
    assert match.home_score is None
    assert match.away_score is None


def test_model_metrics():
    """测试模型指标"""
    metrics = ModelMetrics(
        model_name="football_predictor",
        model_version="v1.0",
        accuracy=0.85,
        precision=0.82,
        recall=0.88,
        f1_score=0.85,
        total_predictions=1000,
        correct_predictions=850,
    )

    assert metrics.model_name == "football_predictor"
    assert metrics.accuracy == 0.85
    assert abs(metrics.error_rate - 0.15) < 0.001  # 浮点数精度

    # 测试更新指标
    metrics.update_metrics(100, 90)
    assert metrics.total_predictions == 1100
    assert metrics.correct_predictions == 940
    assert abs(metrics.accuracy - 0.8545) < 0.001  # 浮点数精度
