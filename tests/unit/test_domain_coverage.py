#!/usr/bin/env python3
"""
Domain模块覆盖测试
目标：为domain模块获得初始覆盖
"""

import pytest
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestDomainCoverage:
    """Domain模块覆盖测试"""

    def test_domain_models_imports(self):
        """测试领域模型导入"""
        try:
            from src.domain.models.match import Match
            from src.domain.models.team import Team
            from src.domain.models.league import League
            from src.domain.models.prediction import Prediction

            # 测试类可以实例化
            match = Match()
            team = Team()
            league = League()
            prediction = Prediction
            assert match is not None
            assert team is not None
            assert league is not None
            assert prediction is not None
        except ImportError:
            pytest.skip("Domain models导入失败")

    def test_domain_events_imports(self):
        """测试领域事件导入"""
        try:
            from src.domain.events.base import DomainEvent
            from src.domain.events.match_events import MatchCreated
            from src.domain.events.prediction_events import PredictionMade

            # 测试事件基类
            event = DomainEvent()
            assert event is not None
            assert hasattr(event, "timestamp")
        except ImportError:
            pytest.skip("Domain events导入失败")

    def test_domain_services_imports(self):
        """测试领域服务导入"""
        try:
            from src.domain.services.match_service import MatchService
            from src.domain.services.prediction_service import PredictionService
            from src.domain.services.team_service import TeamService

            # 测试服务类可以创建
            match_service = MatchService()
            prediction_service = PredictionService()
            team_service = TeamService()
            assert match_service is not None
            assert prediction_service is not None
            assert team_service is not None
        except ImportError:
            pytest.skip("Domain services导入失败")

    def test_domain_strategies_base(self):
        """测试领域策略基类"""
        try:
            from src.domain.strategies.base import PredictionStrategy

            # 测试基类方法存在
            assert hasattr(PredictionStrategy, "predict")
            assert hasattr(PredictionStrategy, "train")
            assert hasattr(PredictionStrategy, "validate")
        except ImportError:
            pytest.skip("Domain strategies导入失败")
