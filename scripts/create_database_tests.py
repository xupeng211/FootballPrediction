#!/usr/bin/env python3
"""
创建数据库模型测试以提升测试覆盖率
"""

from pathlib import Path


def create_match_model_test():
    """创建比赛模型测试"""
    content = '''"""比赛模型测试"""
import pytest
from datetime import datetime
from src.database.models.match import Match, MatchStatus, MatchResult
from src.database.models.team import Team

class TestMatchModel:
    """比赛模型测试"""

    def test_match_creation(self):
        """测试比赛创建"""
        home_team = Team(id=1, name="Team A", league="Premier League")
        away_team = Team(id=2, name="Team B", league="Premier League")

        match = Match(
            id=1,
            home_team=home_team,
            away_team=away_team,
            date=datetime(2024, 1, 1, 15, 0),
            status=MatchStatus.SCHEDULED,
            league="Premier League",
            season="2023-24"
        )

        assert match.id == 1
        assert match.home_team == home_team
        assert match.away_team == away_team
        assert match.status == MatchStatus.SCHEDULED

    def test_match_status_transitions(self):
        """测试比赛状态转换"""
        match = Match(
            id=1,
            home_team=Team(id=1, name="Team A"),
            away_team=Team(id=2, name="Team B"),
            date=datetime(2024, 1, 1),
            status=MatchStatus.SCHEDULED
        )

        # 从预定到进行中
        match.status = MatchStatus.LIVE
        assert match.status == MatchStatus.LIVE

        # 从进行中到完成
        match.status = MatchStatus.COMPLETED
        assert match.status == MatchStatus.COMPLETED

        # 从完成到已取消（特殊情况）
        match.status = MatchStatus.CANCELLED
        assert match.status == MatchStatus.CANCELLED

    def test_match_result_calculation(self):
        """测试比赛结果计算"""
        home_team = Team(id=1, name="Team A")
        away_team = Team(id=2, name="Team B")

        match = Match(
            id=1,
            home_team=home_team,
            away_team=away_team,
            home_score=2,
            away_score=1,
            status=MatchStatus.COMPLETED
        )

        assert match.result == MatchResult.HOME_WIN

        match.home_score = 1
        match.away_score = 1
        assert match.result == MatchResult.DRAW

        match.home_score = 0
        match.away_score = 1
        assert match.result == MatchResult.AWAY_WIN

    def test_match_properties(self):
        """测试比赛属性"""
        match = Match(
            id=1,
            home_team=Team(id=1, name="Team A"),
            away_team=Team(id=2, name="Team B"),
            date=datetime(2024, 1, 1, 15, 0),
            home_score=2,
            away_score=1,
            status=MatchStatus.COMPLETED
        )

        assert match.goal_difference == 1
        assert match.total_goals == 3
        assert match.home_goals == 2
        assert match.away_goals == 1

    def test_match_to_dict(self):
        """测试比赛转换为字典"""
        home_team = Team(id=1, name="Team A", code="TA")
        away_team = Team(id=2, name="Team B", code="TB")

        match = Match(
            id=1,
            home_team=home_team,
            away_team=away_team,
            date=datetime(2024, 1, 1),
            home_score=3,
            away_score=0,
            status=MatchStatus.COMPLETED,
            league="Premier League"
        )

        match_dict = match.to_dict()
        assert match_dict["id"] == 1
        assert match_dict["home_team_name"] == "Team A"
        assert match_dict["away_team_name"] == "Team B"
        assert match_dict["home_score"] == 3
        assert match_dict["away_score"] == 0

    def test_match_validation(self):
        """测试比赛验证"""
        # 测试无效的比分
        with pytest.raises(ValueError):
            Match(
                id=1,
                home_team=Team(id=1, name="Team A"),
                away_team=Team(id=2, name="Team B"),
                home_score=-1,  # 无效的比分
                away_score=1,
                status=MatchStatus.COMPLETED
            )

        # 测试取消的比赛没有比分
        match = Match(
            id=1,
            home_team=Team(id=1, name="Team A"),
            away_team=Team(id=2, name="Team B"),
            status=MatchStatus.CANCELLED
        )
        assert match.home_score is None
        assert match.away_score is None

    def test_match_string_representation(self):
        """测试比赛字符串表示"""
        match = Match(
            id=1,
            home_team=Team(id=1, name="Team A"),
            away_team=Team(id=2, name="Team B"),
            date=datetime(2024, 1, 1)
        )
        assert "Team A vs Team B" in str(match)
'''

    file_path = Path("tests/unit/database/test_match_model.py")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    print(f"✅ 创建文件: {file_path}")


def create_team_model_test():
    """创建球队模型测试"""
    content = '''"""球队模型测试"""
import pytest
from src.database.models.team import Team, TeamForm

class TestTeamModel:
    """球队模型测试"""

    def test_team_creation(self):
        """测试球队创建"""
        team = Team(
            id=1,
            name="Team A",
            code="TA",
            league="Premier League",
            country="England",
            founded=1886
        )

        assert team.id == 1
        assert team.name == "Team A"
        assert team.code == "TA"
        assert team.league == "Premier League"
        assert team.founded == 1886

    def test_team_properties(self):
        """测试球队属性"""
        team = Team(
            id=1,
            name="Manchester United",
            code="MUN",
            league="Premier League"
        )

        assert team.short_name == "MUN"
        assert team.display_name == "Manchester United"

    def test_team_form_calculation(self):
        """测试球队状态计算"""
        team = Team(id=1, name="Team A")

        # 添加比赛记录
        team.recent_matches = [
            {"result": "W", "score": "2-1"},
            {"result": "D", "score": "0-0"},
            {"result": "W", "score": "3-0"},
            {"result": "L", "score": "1-2"},
            {"result": "W", "score": "2-0"}
        ]

        form = team.calculate_form()
        assert form["played"] == 5
        assert form["won"] == 3
        assert form["drawn"] == 1
        assert form["lost"] == 1
        assert form["points"] == 10

    def test_team_statistics(self):
        """测试球队统计"""
        team = Team(
            id=1,
            name="Team A",
            goals_scored=45,
            goals_conceded=20,
            matches_played=25
        )

        stats = team.get_statistics()
        assert stats["goals_scored"] == 45
        assert stats["goals_conceded"] == 20
        assert stats["goal_difference"] == 25
        assert stats["goals_per_match"] == 1.8

    def test_team_validation(self):
        """测试球队验证"""
        # 测试无效的代码
        with pytest.raises(ValueError):
            Team(
                id=1,
                name="Team A",
                code="",  # 空代码
                league="Premier League"
            )

        # 测试过长的代码
        with pytest.raises(ValueError):
            Team(
                id=1,
                name="Team A",
                code="TOOLONGCODE",  # 超过3个字符
                league="Premier League"
            )

    def test_team_form_string(self):
        """测试球队状态字符串"""
        team = Team(id=1, name="Team A")
        team.recent_form = TeamForm.WDLWD

        assert str(team.recent_form) == "WDLWD"
        assert len(team.recent_form) == 5

    def test_team_home_advantage(self):
        """测试主场优势"""
        team = Team(
            id=1,
            name="Team A",
            home_matches_played=15,
            home_matches_won=10,
            away_matches_played=15,
            away_matches_won=5
        )

        home_advantage = team.calculate_home_advantage()
        assert home_advantage > 0  # 主场胜率应该更高

    def test_team_head_to_head(self):
        """测试交锋记录"""
        team_a = Team(id=1, name="Team A")
        team_b = Team(id=2, name="Team B")

        # 设置交锋记录
        team_a.head_to_head = {
            team_b.id: {
                "played": 10,
                "won": 6,
                "drawn": 2,
                "lost": 2,
                "goals_for": 20,
                "goals_against": 10
            }
        }

        h2h = team_a.get_head_to_head(team_b.id)
        assert h2h["played"] == 10
        assert h2h["win_rate"] == 0.6
        assert h2h["goal_difference"] == 10
'''

    file_path = Path("tests/unit/database/test_team_model.py")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    print(f"✅ 创建文件: {file_path}")


def create_prediction_model_test():
    """创建预测模型测试"""
    content = '''"""预测模型测试"""
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
'''

    file_path = Path("tests/unit/database/test_prediction_model.py")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    print(f"✅ 创建文件: {file_path}")


def create_odds_model_test():
    """创建赔率模型测试"""
    content = '''"""赔率模型测试"""
import pytest
from datetime import datetime
from decimal import Decimal
from src.database.models.odds import Odds, MarketType
from src.database.models.match import Match
from src.database.models.team import Team

class TestOddsModel:
    """赔率模型测试"""

    def test_odds_creation(self):
        """测试赔率创建"""
        home_team = Team(id=1, name="Team A")
        away_team = Team(id=2, name="Team B")
        match = Match(id=1, home_team=home_team, away_team=away_team)

        odds = Odds(
            id=1,
            match=match,
            bookmaker="Bet365",
            market_type=MarketType.MATCH_WINNER,
            home_odds=Decimal("2.10"),
            draw_odds=Decimal("3.20"),
            away_odds=Decimal("3.40"),
            timestamp=datetime.now()
        )

        assert odds.id == 1
        assert odds.match == match
        assert odds.bookmaker == "Bet365"
        assert odds.market_type == MarketType.MATCH_WINNER
        assert odds.home_odds == Decimal("2.10")

    def test_odds_implied_probability(self):
        """测试赔率隐含概率"""
        odds = Odds(
            home_odds=Decimal("2.00"),
            draw_odds=Decimal("3.00"),
            away_odds=Decimal("4.00")
        )

        # 计算隐含概率
        home_prob = odds.implied_probability("home")
        draw_prob = odds.implied_probability("draw")
        away_prob = odds.implied_probability("away")

        assert home_prob == Decimal("0.50")  # 1/2.00
        assert draw_prob == Decimal("0.333")  # 约 1/3.00
        assert away_prob == Decimal("0.25")  # 1/4.00

        # 验证总概率（考虑博彩公司利润）
        total_prob = home_prob + draw_prob + away_prob
        assert total_prob > Decimal("1.0")

    def test_odds_overround(self):
        """测试赔率溢出率"""
        odds = Odds(
            home_odds=Decimal("2.00"),
            draw_odds=Decimal("3.00"),
            away_odds=Decimal("4.00")
        )

        overround = odds.calculate_overround()
        assert overround > 0  # 应该有正的溢出率

    def test_odds_value_bet(self):
        """测试价值投注识别"""
        odds = Odds(
            home_odds=Decimal("2.50"),
            draw_odds=Decimal("3.20"),
            away_odds=Decimal("2.80")
        )

        # 如果我们认为主队胜率是50%，那么2.50的赔率有价值
        home_prob = Decimal("0.50")
        value = odds.calculate_value("home", home_prob)
        assert value > 0  # 正值表示有价值

        # 如果我们认为主队胜率只有30%，则没有价值
        home_prob = Decimal("0.30")
        value = odds.calculate_value("home", home_prob)
        assert value < 0  # 负值表示无价值

    def test_odds_comparison(self):
        """测试赔率比较"""
        odds1 = Odds(home_odds=Decimal("2.10"))
        odds2 = Odds(home_odds=Decimal("2.15"))

        # odds2 提供更好的主队赔率
        assert odds2 > odds1  # 通过重载比较运算符

    def test_odds_movement(self):
        """测试赔率变动"""
        home_team = Team(id=1, name="Team A")
        away_team = Team(id=2, name="Team B")
        match = Match(id=1, home_team=home_team, away_team=away_team)

        initial_odds = Odds(
            match=match,
            home_odds=Decimal("2.00"),
            draw_odds=Decimal("3.20"),
            away_odds=Decimal("3.40"),
            timestamp=datetime(2024, 1, 1, 10, 0)
        )

        updated_odds = Odds(
            match=match,
            home_odds=Decimal("1.90"),
            draw_odds=Decimal("3.30"),
            away_odds=Decimal("3.60"),
            timestamp=datetime(2024, 1, 1, 12, 0)
        )

        # 主队赔率下降（变得更被看好）
        movement = initial_odds.calculate_movement(updated_odds)
        assert movement["home_change"] < 0
        assert movement["significant_change"] is True

    def test_different_market_types(self):
        """测试不同市场类型"""
        home_team = Team(id=1, name="Team A")
        away_team = Team(id=2, name="Team B")
        match = Match(id=1, home_team=home_team, away_team=away_team)

        # 亚盘
        asian_odds = Odds(
            match=match,
            market_type=MarketType.ASIAN_HANDICAP,
            home_odds=Decimal("1.95"),
            handicap="-0.5"
        )
        assert asian_odds.handicap == "-0.5"

        # 大小球
        total_odds = Odds(
            match=match,
            market_type=MarketType.TOTAL_GOALS,
            over_odds=Decimal("1.90"),
            under_odds=Decimal("1.95"),
            line=2.5
        )
        assert total_odds.line == 2.5

    def test_odds_validation(self):
        """测试赔率验证"""
        # 无效的赔率（过小）
        with pytest.raises(ValueError):
            Odds(home_odds=Decimal("1.01"))

        # 无效的赔率（过大）
        with pytest.raises(ValueError):
            Odds(home_odds=Decimal("1001.00"))

        # 有效的赔率
        odds = Odds(home_odds=Decimal("1.10"))
        assert odds.is_valid()

    def test_odds_from_json(self):
        """测试从JSON创建赔率"""
        json_data = {
            "match_id": 1,
            "bookmaker": "William Hill",
            "home_odds": "2.10",
            "draw_odds": "3.20",
            "away_odds": "3.40"
        }

        odds = Odds.from_json(json_data)
        assert odds.home_odds == Decimal("2.10")
        assert odds.draw_odds == Decimal("3.20")
        assert odds.away_odds == Decimal("3.40")

    def test_odds_to_dict(self):
        """测试赔率转换为字典"""
        odds = Odds(
            id=1,
            home_odds=Decimal("2.10"),
            draw_odds=Decimal("3.20"),
            away_odds=Decimal("3.40")
        )

        odds_dict = odds.to_dict()
        assert odds_dict["home_odds"] == "2.10"
        assert odds_dict["draw_odds"] == "3.20"
        assert odds_dict["away_odds"] == "3.40"
'''

    file_path = Path("tests/unit/database/test_odds_model.py")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    print(f"✅ 创建文件: {file_path}")


def create_database_repository_test():
    """创建数据库仓库测试"""
    content = '''"""数据库仓库测试"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from src.database.repositories import MatchRepository, TeamRepository
from src.database.models.match import Match, MatchStatus
from src.database.models.team import Team

class TestMatchRepository:
    """比赛仓库测试"""

    @pytest.fixture
    def mock_session(self):
        """模拟数据库会话"""
        return Mock(spec=Session)

    @pytest.fixture
    def repository(self, mock_session):
        """创建比赛仓库"""
        return MatchRepository(mock_session)

    def test_get_match_by_id(self, repository, mock_session):
        """测试根据ID获取比赛"""
        # 设置模拟返回
        mock_match = Mock(spec=Match)
        mock_session.query.return_value.filter.return_value.first.return_value = mock_match

        # 调用方法
        result = repository.get_by_id(1)

        # 验证
        assert result == mock_match
        mock_session.query.assert_called_once_with(Match)

    def test_get_matches_by_league(self, repository, mock_session):
        """测试根据联赛获取比赛"""
        # 设置模拟返回
        mock_matches = [Mock(spec=Match), Mock(spec=Match)]
        mock_session.query.return_value.filter.return_value.all.return_value = mock_matches

        # 调用方法
        result = repository.get_by_league("Premier League")

        # 验证
        assert result == mock_matches

    def test_get_matches_by_date_range(self, repository, mock_session):
        """测试根据日期范围获取比赛"""
        from datetime import date, datetime

        start_date = date(2024, 1, 1)
        end_date = date(2024, 1, 31)

        # 设置模拟返回
        mock_matches = [Mock(spec=Match)]
        mock_session.query.return_value.filter.return_value.all.return_value = mock_matches

        # 调用方法
        result = repository.get_by_date_range(start_date, end_date)

        # 验证
        assert result == mock_matches

    def test_create_match(self, repository, mock_session):
        """测试创建比赛"""
        match_data = {
            "home_team_id": 1,
            "away_team_id": 2,
            "date": datetime(2024, 1, 1, 15, 0),
            "league": "Premier League"
        }

        # 创建新比赛
        new_match = Match(**match_data)
        mock_session.add.return_value = None
        mock_session.commit.return_value = None
        mock_session.refresh.return_value = None

        # 调用方法
        result = repository.create(new_match)

        # 验证
        mock_session.add.assert_called_once_with(new_match)
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(new_match)

    def test_update_match_score(self, repository, mock_session):
        """测试更新比赛比分"""
        # 设置模拟
        mock_match = Mock(spec=Match)
        mock_session.query.return_value.filter.return_value.first.return_value = mock_match

        # 调用方法
        result = repository.update_score(1, 2, 1)

        # 验证
        assert result == mock_match
        mock_match.home_score = 2
        mock_match.away_score = 1
        mock_session.commit.assert_called_once()

    def test_get_live_matches(self, repository, mock_session):
        """测试获取进行中的比赛"""
        # 设置模拟返回
        mock_matches = [Mock(spec=Match), Mock(spec=Match)]
        mock_session.query.return_value.filter.return_value.all.return_value = mock_matches

        # 调用方法
        result = repository.get_live_matches()

        # 验证
        assert result == mock_matches
        mock_session.query.assert_called_once_with(Match)

    def test_delete_match(self, repository, mock_session):
        """测试删除比赛"""
        # 设置模拟
        mock_match = Mock(spec=Match)
        mock_session.query.return_value.filter.return_value.first.return_value = mock_match

        # 调用方法
        result = repository.delete(1)

        # 验证
        assert result is True
        mock_session.delete.assert_called_once_with(mock_match)
        mock_session.commit.assert_called_once()


class TestTeamRepository:
    """球队仓库测试"""

    @pytest.fixture
    def mock_session(self):
        """模拟数据库会话"""
        return Mock(spec=Session)

    @pytest.fixture
    def repository(self, mock_session):
        """创建球队仓库"""
        return TeamRepository(mock_session)

    def test_get_team_by_name(self, repository, mock_session):
        """测试根据名称获取球队"""
        # 设置模拟返回
        mock_team = Mock(spec=Team)
        mock_session.query.return_value.filter.return_value.first.return_value = mock_team

        # 调用方法
        result = repository.get_by_name("Team A")

        # 验证
        assert result == mock_team
        mock_session.query.assert_called_once_with(Team)

    def test_get_teams_by_league(self, repository, mock_session):
        """测试根据联赛获取球队"""
        # 设置模拟返回
        mock_teams = [Mock(spec=Team), Mock(spec=Team)]
        mock_session.query.return_value.filter.return_value.all.return_value = mock_teams

        # 调用方法
        result = repository.get_by_league("Premier League")

        # 验证
        assert result == mock_teams

    def test_get_team_standings(self, repository, mock_session):
        """测试获取球队排名"""
        # 设置模拟返回
        mock_teams = [
            Mock(spec=Team, points=30, goal_diff=20),
            Mock(spec=Team, points=28, goal_diff=15),
            Mock(spec=Team, points=25, goal_diff=10)
        ]
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_teams

        # 调用方法
        result = repository.get_standings("Premier League")

        # 验证
        assert len(result) == 3
        assert result[0].points == 30  # 第一名

    def test_update_team_stats(self, repository, mock_session):
        """测试更新球队统计"""
        # 设置模拟
        mock_team = Mock(spec=Team)
        mock_session.query.return_value.filter.return_value.first.return_value = mock_team

        stats_data = {
            "goals_scored": 5,
            "goals_conceded": 2,
            "matches_played": 3
        }

        # 调用方法
        result = repository.update_stats(1, stats_data)

        # 验证
        assert result == mock_team
        mock_team.goals_scored = 5
        mock_team.goals_conceded = 2
        mock_team.matches_played = 3
        mock_session.commit.assert_called_once()

    def test_search_teams(self, repository, mock_session):
        """测试搜索球队"""
        # 设置模拟返回
        mock_teams = [Mock(spec=Team)]
        mock_session.query.return_value.filter.return_value.all.return_value = mock_teams

        # 调用方法
        result = repository.search("United")

        # 验证
        assert result == mock_teams
'''

    file_path = Path("tests/unit/database/test_repositories.py")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    print(f"✅ 创建文件: {file_path}")


def main():
    """创建所有数据库测试文件"""
    print("🚀 开始创建数据库模型测试文件...")

    # 创建数据库测试目录
    db_test_dir = Path("tests/unit/database")
    db_test_dir.mkdir(parents=True, exist_ok=True)

    # 创建各个测试文件
    create_match_model_test()
    create_team_model_test()
    create_prediction_model_test()
    create_odds_model_test()
    create_database_repository_test()

    print("\n✅ 已创建5个数据库测试文件!")
    print("\n📝 测试文件列表:")
    for file in db_test_dir.glob("test_*.py"):
        print(f"   - {file}")

    print("\n🏃 运行测试:")
    print("   make test-unit")


if __name__ == "__main__":
    main()
