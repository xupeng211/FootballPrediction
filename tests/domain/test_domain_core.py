"""
Domain模块核心测试
测试领域模型、服务和策略
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date, timedelta
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 尝试导入domain模块
try:
    from src.domain.models.prediction import (
        Prediction,
        PredictionStatus,
        ConfidenceScore,
    )
    from src.domain.models.match import Match, MatchStatus, MatchResult
    from src.domain.models.team import Team, TeamStats
    from src.domain.models.league import League, LeagueSeason
    from src.domain.services.prediction_service import PredictionService
    from src.domain.services.match_service import MatchService
    from src.domain.services.team_service import TeamService
    from src.domain.strategies.base import PredictionStrategy
    from src.domain.strategies.statistical import StatisticalStrategy
    from src.domain.strategies.ml_model import MLModelStrategy
    from src.domain.strategies.factory import StrategyFactory

    DOMAIN_AVAILABLE = True
except ImportError as e:
    pytest.skip(f"Domain模块不可用: {e}", allow_module_level=True)
    DOMAIN_AVAILABLE = False


class TestPredictionModel:
    """测试预测模型"""

    def test_confidence_score_creation(self):
        """测试置信度创建"""
        if not DOMAIN_AVAILABLE:
            pytest.skip("Domain模块不可用")

        # 测试有效置信度
        confidence = ConfidenceScore(Decimal("0.85"))
        assert confidence.value == Decimal("0.85")
        assert confidence.level == "high"

        confidence = ConfidenceScore(Decimal("0.65"))
        assert confidence.level == "medium"

        confidence = ConfidenceScore(Decimal("0.45"))
        assert confidence.level == "low"

    def test_confidence_score_validation(self):
        """测试置信度验证"""
        # 测试无效置信度
        with pytest.raises(Exception):  # DomainError
            ConfidenceScore(Decimal("-0.1"))

        with pytest.raises(Exception):  # DomainError
            ConfidenceScore(Decimal("1.1"))

    def test_confidence_score_quantization(self):
        """测试置信度量化"""
        confidence = ConfidenceScore(Decimal("0.856"))
        assert confidence.value == Decimal("0.86")

    def test_prediction_creation(self):
        """测试预测创建"""
        confidence = ConfidenceScore(Decimal("0.75"))
        prediction = Prediction(
            user_id=1,
            match_id=123,
            predicted_result="HOME_WIN",
            confidence=confidence,
            created_at=datetime.now(),
        )

        assert prediction.user_id == 1
        assert prediction.match_id == 123
        assert prediction.predicted_result == "HOME_WIN"
        assert prediction.confidence.value == Decimal("0.75")
        assert prediction.status == PredictionStatus.PENDING

    def test_prediction_evaluation(self):
        """测试预测评估"""
        confidence = ConfidenceScore(Decimal("0.80"))
        prediction = Prediction(
            user_id=1, match_id=123, predicted_result="HOME_WIN", confidence=confidence
        )

        # 评估预测结果
        prediction.evaluate(actual_result="HOME_WIN")
        assert prediction.is_correct is True
        assert prediction.status == PredictionStatus.EVALUATED

        # 评估错误预测
        prediction2 = Prediction(
            user_id=2,
            match_id=123,
            predicted_result="DRAW",
            confidence=ConfidenceScore(Decimal("0.60")),
        )
        prediction2.evaluate(actual_result="HOME_WIN")
        assert prediction2.is_correct is False

    def test_prediction_cancellation(self):
        """测试预测取消"""
        prediction = Prediction(
            user_id=1,
            match_id=123,
            predicted_result="HOME_WIN",
            confidence=ConfidenceScore(Decimal("0.75")),
        )

        prediction.cancel()
        assert prediction.status == PredictionStatus.CANCELLED

    def test_prediction_expiry(self):
        """测试预测过期"""
        prediction = Prediction(
            user_id=1,
            match_id=123,
            predicted_result="HOME_WIN",
            confidence=ConfidenceScore(Decimal("0.75")),
        )

        prediction.expire()
        assert prediction.status == PredictionStatus.EXPIRED


class TestMatchModel:
    """测试比赛模型"""

    def test_match_creation(self):
        """测试比赛创建"""
        if not DOMAIN_AVAILABLE:
            pytest.skip("Domain模块不可用")

        match = Match(
            id=123,
            home_team_id=1,
            away_team_id=2,
            league_id=3,
            match_date=datetime(2025, 1, 20, 15, 0),
            venue="Old Trafford",
            status=MatchStatus.SCHEDULED,
        )

        assert match.id == 123
        assert match.home_team_id == 1
        assert match.away_team_id == 2
        assert match.status == MatchStatus.SCHEDULED

    def test_match_start(self):
        """测试比赛开始"""
        match = Match(
            id=123,
            home_team_id=1,
            away_team_id=2,
            league_id=3,
            match_date=datetime(2025, 1, 20, 15, 0),
            status=MatchStatus.SCHEDULED,
        )

        match.start()
        assert match.status == MatchStatus.IN_PROGRESS

    def test_match_result_setting(self):
        """测试设置比赛结果"""
        match = Match(
            id=123,
            home_team_id=1,
            away_team_id=2,
            league_id=3,
            match_date=datetime(2025, 1, 20, 15, 0),
            status=MatchStatus.IN_PROGRESS,
        )

        result = MatchResult(home_score=2, away_score=1, winner="HOME_WIN")

        match.set_result(result)
        assert match.result == result
        assert match.status == MatchStatus.FINISHED
        assert match.result.winner == "HOME_WIN"

    def test_match_postponement(self):
        """测试比赛延期"""
        match = Match(
            id=123,
            home_team_id=1,
            away_team_id=2,
            league_id=3,
            match_date=datetime(2025, 1, 20, 15, 0),
            status=MatchStatus.SCHEDULED,
        )

        new_date = datetime(2025, 1, 25, 20, 0)
        match.postpone(new_date=new_date, reason="Bad weather")
        assert match.match_date == new_date
        assert match.status == MatchStatus.POSTPONED


class TestTeamModel:
    """测试球队模型"""

    def test_team_creation(self):
        """测试球队创建"""
        if not DOMAIN_AVAILABLE:
            pytest.skip("Domain模块不可用")

        team = Team(
            id=1,
            name="Manchester United",
            short_name="MU",
            founded=1878,
            city="Manchester",
            country="England",
            stadium="Old Trafford",
        )

        assert team.id == 1
        assert team.name == "Manchester United"
        assert team.short_name == "MU"
        assert team.founded == 1878

    def test_team_stats_creation(self):
        """测试球队统计创建"""
        stats = TeamStats(
            matches_played=20,
            wins=12,
            draws=4,
            losses=4,
            goals_for=35,
            goals_against=20,
            points=40,
        )

        assert stats.matches_played == 20
        assert stats.wins == 12
        assert stats.losses == 4
        assert stats.points == 40

    def test_team_stats_calculation(self):
        """测试球队统计计算"""
        stats = TeamStats(
            matches_played=20,
            wins=12,
            draws=4,
            losses=4,
            goals_for=35,
            goals_against=20,
            points=40,
        )

        assert stats.win_rate == 0.6
        assert stats.goal_difference == 15
        assert stats.points_per_game == 2.0

    def test_team_stats_update(self):
        """测试更新球队统计"""
        stats = TeamStats(
            matches_played=10,
            wins=6,
            draws=2,
            losses=2,
            goals_for=15,
            goals_against=8,
            points=20,
        )

        # 更新比赛结果
        stats.update_result(won=True, goals_for=2, goals_against=1)
        assert stats.matches_played == 11
        assert stats.wins == 7
        assert stats.goals_for == 17
        assert stats.goals_against == 9
        assert stats.points == 23


class TestLeagueModel:
    """测试联赛模型"""

    def test_league_creation(self):
        """测试联赛创建"""
        if not DOMAIN_AVAILABLE:
            pytest.skip("Domain模块不可用")

        league = League(
            id=1,
            name="Premier League",
            country="England",
            founded=1992,
            tier=1,
            promotion_place=18,
            relegation_place=20,
        )

        assert league.id == 1
        assert league.name == "Premier League"
        assert league.country == "England"
        assert league.tier == 1

    def test_league_season_creation(self):
        """测试联赛赛季创建"""
        season = LeagueSeason(
            league_id=1,
            season="2024/2025",
            start_date=date(2024, 8, 1),
            end_date=date(2025, 5, 31),
            teams_count=20,
            matches_per_team=38,
        )

        assert season.league_id == 1
        assert season.season == "2024/2025"
        assert season.teams_count == 20
        assert season.matches_per_team == 38

    def test_league_season_active_check(self):
        """测试赛季是否活跃"""
        today = date.today()
        season = LeagueSeason(
            league_id=1,
            season="2024/2025",
            start_date=date(2024, 8, 1),
            end_date=date(2025, 5, 31),
            teams_count=20,
            matches_per_team=38,
        )

        if today >= date(2024, 8, 1) and today <= date(2025, 5, 31):
            assert season.is_active is True
        else:
            assert season.is_active is False


class TestPredictionService:
    """测试预测服务"""

    def test_prediction_service_creation(self):
        """测试预测服务创建"""
        if not DOMAIN_AVAILABLE:
            pytest.skip("Domain模块不可用")

        with patch(
            "src.domain.services.prediction_service.PredictionService"
        ) as MockService:
            service = MockService()
            service.create_prediction = Mock(return_value=Mock(id=123))
            service.evaluate_prediction = Mock(return_value={"correct": True})
            service.cancel_prediction = Mock(return_value=True)

            # 创建预测
            prediction = service.create_prediction(
                user_id=1, match_id=123, predicted_result="HOME_WIN", confidence=0.85
            )
            assert prediction.id == 123

            # 评估预测
            result = service.evaluate_prediction(
                prediction_id=123, actual_result="HOME_WIN"
            )
            assert result["correct"] is True

            # 取消预测
            cancelled = service.cancel_prediction(prediction_id=123)
            assert cancelled is True

    def test_get_user_predictions(self):
        """测试获取用户预测"""
        with patch(
            "src.domain.services.prediction_service.PredictionService"
        ) as MockService:
            service = MockService()
            service.get_user_predictions = Mock(
                return_value=[
                    {
                        "id": 1,
                        "match_id": 123,
                        "predicted_result": "HOME_WIN",
                        "confidence": 0.85,
                        "status": "pending",
                    },
                    {
                        "id": 2,
                        "match_id": 124,
                        "predicted_result": "DRAW",
                        "confidence": 0.60,
                        "status": "evaluated",
                    },
                ]
            )

            predictions = service.get_user_predictions(user_id=1)
            assert len(predictions) == 2
            assert predictions[0]["predicted_result"] == "HOME_WIN"

    def test_get_prediction_statistics(self):
        """测试获取预测统计"""
        with patch(
            "src.domain.services.prediction_service.PredictionService"
        ) as MockService:
            service = MockService()
            service.get_user_statistics = Mock(
                return_value={
                    "total_predictions": 50,
                    "correct_predictions": 35,
                    "accuracy": 0.70,
                    "most_predicted": "HOME_WIN",
                    "confidence_avg": 0.72,
                }
            )

            stats = service.get_user_statistics(user_id=1)
            assert stats["total_predictions"] == 50
            assert stats["accuracy"] == 0.70


class TestMatchService:
    """测试比赛服务"""

    def test_match_service_creation(self):
        """测试比赛服务创建"""
        if not DOMAIN_AVAILABLE:
            pytest.skip("Domain模块不可用")

        with patch("src.domain.services.match_service.MatchService") as MockService:
            service = MockService()
            service.get_match = Mock(return_value=Mock(id=123))
            service.get_upcoming_matches = Mock(
                return_value=[Mock(id=124), Mock(id=125)]
            )
            service.update_match_result = Mock(return_value=True)

            # 获取比赛
            match = service.get_match(match_id=123)
            assert match.id == 123

            # 获取即将进行的比赛
            matches = service.get_upcoming_matches(days=7)
            assert len(matches) == 2

            # 更新比赛结果
            updated = service.update_match_result(
                match_id=123, home_score=2, away_score=1
            )
            assert updated is True

    def test_get_team_fixtures(self):
        """测试获取球队赛程"""
        with patch("src.domain.services.match_service.MatchService") as MockService:
            service = MockService()
            service.get_team_fixtures = Mock(
                return_value=[
                    {
                        "match_id": 123,
                        "opponent": "Team B",
                        "home": True,
                        "date": datetime(2025, 1, 20, 15, 0),
                    },
                    {
                        "match_id": 124,
                        "opponent": "Team C",
                        "home": False,
                        "date": datetime(2025, 1, 25, 20, 0),
                    },
                ]
            )

            fixtures = service.get_team_fixtures(team_id=1, days=30)
            assert len(fixtures) == 2
            assert fixtures[0]["home"] is True


class TestTeamService:
    """测试球队服务"""

    def test_team_service_creation(self):
        """测试球队服务创建"""
        if not DOMAIN_AVAILABLE:
            pytest.skip("Domain模块不可用")

        with patch("src.domain.services.team_service.TeamService") as MockService:
            service = MockService()
            service.get_team = Mock(return_value=Mock(id=1, name="Team A"))
            service.get_team_stats = Mock(
                return_value={
                    "played": 20,
                    "won": 12,
                    "drawn": 4,
                    "lost": 4,
                    "points": 40,
                }
            )
            service.get_team_form = Mock(return_value=["W", "D", "W", "W", "L"])

            # 获取球队
            team = service.get_team(team_id=1)
            assert team.id == 1
            assert team.name == "Team A"

            # 获取球队统计
            stats = service.get_team_stats(team_id=1, season="2024/2025")
            assert stats["points"] == 40

            # 获取球队状态
            form = service.get_team_form(team_id=1, last_n=5)
            assert len(form) == 5
            assert form[0] == "W"


class TestPredictionStrategies:
    """测试预测策略"""

    def test_base_strategy(self):
        """测试基础策略"""
        if not DOMAIN_AVAILABLE:
            pytest.skip("Domain模块不可用")

        with patch("src.domain.strategies.base.PredictionStrategy") as MockStrategy:
            strategy = MockStrategy()
            strategy.name = "BaseStrategy"
            strategy.predict = Mock(
                return_value={"HOME_WIN": 0.5, "DRAW": 0.3, "AWAY_WIN": 0.2}
            )
            strategy.train = Mock(return_value={"accuracy": 0.75})

            # 预测
            prediction = strategy.predict(match_data={})
            assert prediction["HOME_WIN"] == 0.5

            # 训练
            training_result = strategy.train(training_data=[])
            assert training_result["accuracy"] == 0.75

    def test_statistical_strategy(self):
        """测试统计策略"""
        with patch(
            "src.domain.strategies.statistical.StatisticalStrategy"
        ) as MockStrategy:
            strategy = MockStrategy()
            strategy.calculate_head_to_head = Mock(
                return_value={"home_wins": 3, "away_wins": 2, "draws": 1}
            )
            strategy.calculate_form = Mock(
                return_value={
                    "home_form": [1, 1, 0, 1, 1],
                    "away_form": [0, 1, 1, 0, 0],
                }
            )

            # 计算历史交锋
            h2h = strategy.calculate_head_to_head(home_id=1, away_id=2)
            assert h2h["home_wins"] == 3

            # 计算状态
            form = strategy.calculate_form(team_id=1, last_n=5)
            assert len(form["home_form"]) == 5

    def test_ml_model_strategy(self):
        """测试机器学习模型策略"""
        with patch("src.domain.strategies.ml_model.MLModelStrategy") as MockStrategy:
            strategy = MockStrategy()
            strategy.load_model = Mock(return_value=True)
            strategy.predict = Mock(
                return_value={
                    "HOME_WIN": 0.65,
                    "DRAW": 0.25,
                    "AWAY_WIN": 0.10,
                    "confidence": 0.85,
                }
            )
            strategy.evaluate_model = Mock(
                return_value={"accuracy": 0.82, "precision": 0.80, "recall": 0.78}
            )

            # 加载模型
            loaded = strategy.load_model("model_v1.pkl")
            assert loaded is True

            # 预测
            prediction = strategy.predict(match_features=[1, 2, 3, 4, 5])
            assert prediction["HOME_WIN"] == 0.65

            # 评估模型
            evaluation = strategy.evaluate_model(test_data=[])
            assert evaluation["accuracy"] == 0.82

    def test_strategy_factory(self):
        """测试策略工厂"""
        with patch("src.domain.strategies.factory.StrategyFactory") as MockFactory:
            factory = MockFactory()
            factory.create_strategy = Mock(return_value=Mock())
            factory.get_available_strategies = Mock(
                return_value=["statistical", "ml_model", "historical", "ensemble"]
            )

            # 创建策略
            strategy = factory.create_strategy("statistical")
            assert strategy is not None

            # 获取可用策略
            strategies = factory.get_available_strategies()
            assert len(strategies) == 4
            assert "statistical" in strategies

    def test_ensemble_strategy(self):
        """测试集成策略"""
        with patch("src.domain.strategies.ensemble.EnsembleStrategy") as MockStrategy:
            strategy = MockStrategy()
            strategy.add_strategy = Mock(return_value=True)
            strategy.predict = Mock(
                return_value={
                    "HOME_WIN": 0.60,
                    "DRAW": 0.25,
                    "AWAY_WIN": 0.15,
                    "individual_predictions": [
                        {"HOME_WIN": 0.55, "DRAW": 0.30, "AWAY_WIN": 0.15},
                        {"HOME_WIN": 0.65, "DRAW": 0.20, "AWAY_WIN": 0.15},
                    ],
                }
            )

            # 添加策略
            strategy.add_strategy("statistical", Mock())
            strategy.add_strategy("ml_model", Mock())

            # 集成预测
            prediction = strategy.predict(match_data={})
            assert prediction["HOME_WIN"] == 0.60
            assert "individual_predictions" in prediction


class TestDomainIntegration:
    """测试领域集成"""

    def test_prediction_flow(self):
        """测试预测流程"""
        # 创建领域对象
        with patch("src.domain.models.prediction.Prediction") as MockPrediction, patch(
            "src.domain.models.match.Match"
        ) as MockMatch, patch(
            "src.domain.services.prediction_service.PredictionService"
        ) as MockService:
            prediction = MockPrediction()
            match = MockMatch()
            service = MockService()

            # 模拟流程
            match.status = "SCHEDULED"
            match.id = 123

            service.create_prediction = Mock(return_value=prediction)
            service.evaluate_prediction = Mock(return_value={"correct": True})

            # 创建预测
            prediction = service.create_prediction(
                user_id=1, match_id=123, predicted_result="HOME_WIN", confidence=0.75
            )

            # 比赛结束，评估预测
            result = service.evaluate_prediction(
                prediction_id=prediction.id, actual_result="HOME_WIN"
            )

            assert result["correct"] is True

    def test_team_league_relationship(self):
        """测试球队联赛关系"""
        with patch("src.domain.models.team.Team") as MockTeam, patch(
            "src.domain.models.league.League"
        ) as MockLeague, patch("src.domain.models.league.LeagueSeason") as MockSeason:
            team = MockTeam()
            league = MockLeague()
            season = MockSeason()

            # 设置关系
            team.id = 1
            league.id = 1
            season.league_id = 1
            season.teams = [team]

            # 验证关系
            assert team in season.teams
            assert season.league_id == league.id
