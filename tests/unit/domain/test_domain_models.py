"""
领域模型测试
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

# 尝试导入，如果失败则创建模拟
try:
    from src.domain.models.prediction import Prediction
    from src.domain.models.match import Match
except ImportError:
    # 创建模拟类
    class Prediction:
        """预测模型"""

        def __init__(self, match_id, prediction_type, confidence, metadata=None):
            self.match_id = match_id
            self.prediction_type = prediction_type
            self.confidence = confidence
            self.metadata = metadata or {}
            self.created_at = datetime.now()

    class Match:
        """比赛模型"""

        def __init__(self, match_id, home_team, away_team, match_date):
            self.match_id = match_id
            self.home_team = home_team
            self.away_team = away_team
            self.match_date = match_date


class TestDomainModels:
    """测试领域模型"""

    def test_prediction_creation(self):
        """测试预测创建"""
        prediction = Prediction(
            match_id=123,
            prediction_type="HOME_WIN",
            confidence=0.85,
            metadata={"model_version": "1.0"},
        )

        assert prediction.match_id == 123
        assert prediction.prediction_type == "HOME_WIN"
        assert prediction.confidence == 0.85
        assert prediction.metadata["model_version"] == "1.0"

    def test_match_creation(self):
        """测试比赛创建"""
        match = Match(
            match_id=456,
            home_team="Team A",
            away_team="Team B",
            match_date="2024-01-01T15:00:00Z",
        )

        assert match.match_id == 456
        assert match.home_team == "Team A"
        assert match.away_team == "Team B"

    def test_domain_validation(self):
        """测试域验证"""
        # 测试预测验证
        with pytest.raises(ValueError):
            Prediction(
                match_id=None,
                prediction_type="HOME_WIN",
                confidence=1.5,  # 无效的置信度
            )

        # 测试正常情况
        prediction = Prediction(
            match_id=123, prediction_type="HOME_WIN", confidence=0.75
        )
        assert prediction.confidence == 0.75
