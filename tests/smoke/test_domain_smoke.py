#!/usr/bin/env python3
"""
Domain模块smoke测试
测试领域模型是否可以正常导入和初始化
"""

import pytest
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestDomainSmoke:
    """Domain模块冒烟测试"""

    def test_domain_models(self):
        """测试领域模型"""
        from src.domain.models.match import Match
        from src.domain.models.team import Team
        from src.domain.models.league import League
        from src.domain.models.prediction import Prediction

        # 测试模型可以创建
        match = Match()
        assert match is not None

        team = Team()
        assert team is not None

        league = League()
        assert league is not None

        prediction = Prediction()
        assert prediction is not None

    def test_domain_events(self):
        """测试领域事件"""
        from src.domain.events.base import DomainEvent
        from src.domain.events.match_events import MatchCreated
        from src.domain.events.prediction_events import PredictionMade

        # 测试事件可以创建
        event = DomainEvent()
        assert event is not None
        assert hasattr(event, "timestamp")

        match_event = MatchCreated(match_id=1)
        assert match_event is not None
        assert match_event.match_id == 1

        prediction_event = PredictionMade(prediction_id=1)
        assert prediction_event is not None
        assert prediction_event.prediction_id == 1

    def test_domain_services(self):
        """测试领域服务"""
        from src.domain.services.match_service import MatchService
        from src.domain.services.prediction_service import PredictionService
        from src.domain.services.team_service import TeamService
        from src.domain.services.scoring_service import ScoringService

        # 测试服务可以创建
        match_service = MatchService()
        assert match_service is not None

        prediction_service = PredictionService()
        assert prediction_service is not None

        team_service = TeamService()
        assert team_service is not None

        scoring_service = ScoringService()
        assert scoring_service is not None

    def test_domain_strategies(self):
        """测试领域策略"""
        from src.domain.strategies.base import PredictionStrategy
        from src.domain.strategies.statistical import StatisticalStrategy
        from src.domain.strategies.historical import HistoricalStrategy

        # 测试策略类存在
        assert PredictionStrategy is not None
        assert StatisticalStrategy is not None
        assert HistoricalStrategy is not None

        # 测试基类方法
        assert hasattr(PredictionStrategy, "predict")
        assert hasattr(PredictionStrategy, "train")
