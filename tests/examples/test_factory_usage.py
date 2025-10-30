"""测试数据工厂使用示例。"""

pytest_plugins = ["tests.conftest_containers"]

from datetime import datetime

import pytest

from src.database.models.match import MatchStatus
from tests.factories import (
    LeagueFactory,
    MatchFactory,
    OddsFactory,
    PredictionFactory,
    TeamFactory,
    UserFactory,
)
from tests.factories.league_factory import InternationalLeagueFactory
from tests.factories.prediction_factory import MLModelPredictionFactory
from tests.factories.team_factory import ChineseTeamFactory, HistoricTeamFactory


@pytest.mark.integration
class TestFactoryUsage:
    """测试工厂使用示例"""

    def test_create_single_team(self, test_db_session):
        """测试创建单个球队"""
        # 使用默认工厂创建球队
        team = TeamFactory.create()
        test_db_session.commit()

        assert team.id is not None
        assert team.team_name is not None
        assert team.team_code is not None
        assert team.country is not None

    def test_create_custom_team(self, test_db_session):
        """测试创建自定义球队"""
        # 使用自定义参数
        team = TeamFactory.create(
            team_name="Real Madrid", team_code="RMA", country="Spain", founded_year=1902
        )
        test_db_session.commit()

        assert team.team_name == "Real Madrid"
        assert team.team_code == "RMA"
        assert team.country == "Spain"
        assert team.founded_year == 1902

    def test_create_chinese_team(self, test_db_session):
        """测试创建中国球队"""
        team = ChineseTeamFactory.create()
        test_db_session.commit()

        assert team.country == "China"
        assert any(ord(c) > 127 for c in team.team_name)  # 包含中文字符

    def test_create_historic_team(self, test_db_session):
        """测试创建历史球队"""
        team = HistoricTeamFactory.create()
        test_db_session.commit()

        assert team.founded_year < 1920
        assert "Ground" in team.stadium

    def test_create_batch_teams(self, test_db_session):
        """测试批量创建球队"""
        _teams = TeamFactory.create_batch(5)
        test_db_session.commit()

        assert len(teams) == 5
        for team in teams:
            assert team.id is not None

    def test_create_league_with_teams(self, test_db_session):
        """测试创建联赛和球队关系"""
        # 创建联赛
        league = LeagueFactory.create_premier_league()
        test_db_session.flush()

        # 创建属于该联赛的球队
        _teams = TeamFactory.create_batch_with_league(count=4, league_id=league.id)
        test_db_session.commit()

        assert league.id is not None
        assert len(teams) == 4
        for team in teams:
            assert team.league_id == league.id

    def test_create_complete_match(self, test_db_session):
        """测试创建完整的比赛数据"""
        # 创建联赛
        league = LeagueFactory.create()
        test_db_session.flush()

        # 创建球队
        home_team = TeamFactory.create()
        away_team = TeamFactory.create()
        test_db_session.flush()

        # 创建比赛
        match = MatchFactory.create_with_teams(
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            league_id=league.id,
            match_status=MatchStatus.SCHEDULED,
        )
        test_db_session.commit()

        assert match.league_id == league.id
        assert match.home_team_id == home_team.id
        assert match.away_team_id == away_team.id

    def test_create_finished_match_with_prediction(self, test_db_session):
        """测试创建已结束的比赛和预测"""
        # 创建基础数据
        league = LeagueFactory.create()
        home_team = TeamFactory.create()
        away_team = TeamFactory.create()
        test_db_session.flush()

        # 创建已结束的比赛
        match = MatchFactory.create_finished_match(
            league_id=league.id,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_score=2,
            away_score=1,
        )
        test_db_session.flush()

        # 创建正确的预测
        _prediction = PredictionFactory.create_correct_prediction(
            match_id=match.id,
            actual_home_score=2,
            actual_away_score=1,
        )
        test_db_session.commit()

        assert prediction.is_correct is True
        assert prediction.match_id == match.id

    def test_create_ml_prediction(self, test_db_session):
        """测试创建机器学习预测"""
        match = MatchFactory.create()
        test_db_session.flush()

        ml_prediction = MLModelPredictionFactory.create(match_id=match.id)
        test_db_session.commit()

        assert ml_prediction.model_name == "ml-service"
        assert ml_prediction.model_version == "ML-v2.1.0"
        assert "team_form_last_5" in ml_prediction.features_used

    def test_create_users(self, test_db_session):
        """测试创建用户"""
        # 创建普通用户
        _user = UserFactory.create()
        test_db_session.commit()

        # 创建管理员
        admin = UserFactory.create_admin()
        test_db_session.commit()

        # 创建分析师
        analyst = UserFactory.create_analyst()
        test_db_session.commit()

        assert user.id is not None
        assert admin.is_admin is True
        assert analyst.is_analyst is True

    def test_create_odds_for_match(self, test_db_session):
        """测试为比赛创建赔率"""
        match = MatchFactory.create()
        test_db_session.flush()

        # 创建多个博彩公司的赔率
        odds1 = OddsFactory.create_bet365_odds(match_id=match.id)
        odds2 = OddsFactory.create_william_hill_odds(match_id=match.id)
        odds3 = OddsFactory.create_betfair_odds(match_id=match.id)
        test_db_session.commit()

        assert odds1.bookmaker == "Bet365"
        assert odds2.bookmaker == "William Hill"
        assert odds3.bookmaker == "Betfair"

    def test_create_season_data(self, test_db_session):
        """测试创建整个赛季的数据"""
        # 创建联赛
        league = LeagueFactory.create()
        test_db_session.flush()

        # 创建20支球队
        _teams = TeamFactory.create_batch_with_league(20, league.id)
        test_db_session.flush()

        # 获取球队ID列表
        team_ids = [team.id for team in teams]

        # 创建赛季比赛（简化版）
        _matches = []
        for i in range(10):  # 只创建10轮作为示例
            for j in range(0, 20, 2):  # 每轮10场比赛
                if j + 1 < 20:
                    match = MatchFactory.create_with_teams(
                        league_id=league.id,
                        home_team_id=team_ids[j],
                        away_team_id=team_ids[j + 1],
                        match_status=MatchStatus.SCHEDULED,
                    )
                    matches.append(match)

        test_db_session.commit()

        assert len(teams) == 20
        assert len(matches) == 100  # 10轮 * 10场/轮

    def test_complex_test_scenario(self, test_db_session):
        """复杂测试场景:完整的预测流程"""
        # 1. 创建联赛
        premier_league = LeagueFactory.create_premier_league()
        test_db_session.flush()

        # 2. 创建球队
        manchester_united = TeamFactory.create(
            team_name="Manchester United", team_code="MUN", country="England"
        )
        liverpool = TeamFactory.create(team_name="Liverpool", team_code="LIV", country="England")
        test_db_session.flush()

        # 3. 创建比赛
        match = MatchFactory.create_with_teams(
            home_team_id=manchester_united.id,
            away_team_id=liverpool.id,
            league_id=premier_league.id,
            venue="Old Trafford",
            match_time=datetime.now(),
        )
        test_db_session.flush()

        # 4. 创建多个用户
        users = UserFactory.create_test_users()
        test_db_session.flush()

        # 5. 创建赔率
        odds = OddsFactory.create_balanced_odds(match_id=match.id)
        test_db_session.flush()

        # 6. 创建多个预测
        predictions = []
        for i, user in enumerate(users):
            if i == 0:  # 管理员预测
                pred = PredictionFactory.create_home_win_prediction(
                    match_id=match.id,
                    confidence_score=0.85,
                )
            elif i == 1:  # 普通用户预测
                pred = PredictionFactory.create_draw_prediction(
                    match_id=match.id,
                    confidence_score=0.60,
                )
            else:  # 其他预测
                pred = PredictionFactory.create(match_id=match.id)
            predictions.append(pred)

        test_db_session.commit()

        # 验证数据完整性
        assert premier_league.league_name == "Premier League"
        assert match.home_team_id == manchester_united.id
        assert match.away_team_id == liverpool.id
        assert len(users) == 4
        assert len(predictions) == 4
        assert odds.match_id == match.id

        print(f"\n创建的测试数据:")
        print(f"- 联赛: {premier_league.league_name}")
        print(f"- 比赛: {manchester_united.team_name} vs {liverpool.team_name}")
        print(f"- 用户数: {len(users)}")
        print(f"- 预测数: {len(predictions)}")
        print(f"- 赔率来源: {odds.bookmaker}")
