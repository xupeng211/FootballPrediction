"""
from datetime import datetime, timezone
数据库业务逻辑约束测试

测试 CHECK 约束和触发器的正确性，验证非法数据插入时约束能正确触发。
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from src.database.config import get_test_database_config
from src.database.connection import get_session, initialize_multi_user_database
from src.database.models import League, MarketType, Match, Odds, Team


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """初始化多用户数据库以进行约束测试"""
    config = get_test_database_config()
    initialize_multi_user_database(config)


class TestMatchConstraints:
    """测试比赛表的约束条件"""

    def setup_method(self):
        """设置测试数据"""
        with get_session() as db:
            # 创建测试联赛
            self.test_league = League(
                league_name="Test League", country="Test Country", api_league_id=999999
            )
            db.add(self.test_league)

            # 创建测试球队
            self.test_team1 = Team(
                team_name="Test Team 1",
                team_code="TT1",
                country="Test Country",
                api_team_id=999998,
            )
            self.test_team2 = Team(
                team_name="Test Team 2",
                team_code="TT2",
                country="Test Country",
                api_team_id=999997,
            )
            db.add_all([self.test_team1, self.test_team2])
            db.commit()

            # 获取ID用于后续测试
            self.league_id = self.test_league.id
            self.team1_id = self.test_team1.id
            self.team2_id = self.test_team2.id

    def teardown_method(self):
        """清理测试数据"""
        with get_session() as db:
            # 删除测试数据
            db.query(Match).filter(Match.league_id == self.league_id).delete()
            db.query(Team).filter(Team.id.in_([self.team1_id, self.team2_id])).delete()
            db.query(League).filter(League.id == self.league_id).delete()
            db.commit()

    def test_valid_match_creation(self):
        """测试创建有效的比赛记录"""
        with get_session() as db:
            match = Match(
                home_team_id=self.team1_id,
                away_team_id=self.team2_id,
                league_id=self.league_id,
                season="2024-25",
                match_time=datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
                home_score=2,
                away_score=1,
                home_ht_score=1,
                away_ht_score=0,
            )
            db.add(match)
            db.commit()  # 应该成功
            assert match.id is not None

    def test_score_range_constraints_negative(self):
        """测试比分不能为负数"""
        with get_session() as db:
            # 测试主队比分为负数
            match = Match(
                home_team_id=self.team1_id,
                away_team_id=self.team2_id,
                league_id=self.league_id,
                season="2024-25",
                match_time=datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
                home_score=-1,  # 无效比分
            )
            db.add(match)

            with pytest.raises(IntegrityError, match="ck_matches_home_score_range"):
                db.commit()

    def test_score_range_constraints_too_high(self):
        """测试比分不能超过99"""
        with get_session() as db:
            # 测试主队比分超过99
            match = Match(
                home_team_id=self.team1_id,
                away_team_id=self.team2_id,
                league_id=self.league_id,
                season="2024-25",
                match_time=datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
                home_score=100,  # 无效比分
            )
            db.add(match)

            with pytest.raises(IntegrityError, match="ck_matches_home_score_range"):
                db.commit()

    def test_match_time_constraint(self):
        """测试比赛时间必须大于2000-01-01"""
        with get_session() as db:
            match = Match(
                home_team_id=self.team1_id,
                away_team_id=self.team2_id,
                league_id=self.league_id,
                season="1999-00",
                match_time=datetime(1999, 12, 31, 15, 0, tzinfo=timezone.utc),  # 无效时间
            )
            db.add(match)

            with pytest.raises(IntegrityError, match="ck_matches_match_time_range"):
                db.commit()

    def test_same_team_constraint(self):
        """测试主队和客队不能相同"""
        with get_session() as db:
            match = Match(
                home_team_id=self.team1_id,
                away_team_id=self.team1_id,  # 主队和客队相同
                league_id=self.league_id,
                season="2024-25",
                match_time=datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
            )
            db.add(match)

            with pytest.raises(
                IntegrityError, match="Home team and away team cannot be the same"
            ):
                db.commit()

    def test_nonexistent_team_constraint(self):
        """测试不存在的球队ID"""
        with get_session() as db:
            match = Match(
                home_team_id=999999,  # 不存在的球队ID
                away_team_id=self.team2_id,
                league_id=self.league_id,
                season="2024-25",
                match_time=datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
            )
            db.add(match)

            with pytest.raises(IntegrityError, match="Home team does not exist"):
                db.commit()

    def test_nonexistent_league_constraint(self):
        """测试不存在的联赛ID"""
        with get_session() as db:
            match = Match(
                home_team_id=self.team1_id,
                away_team_id=self.team2_id,
                league_id=999999,  # 不存在的联赛ID
                season="2024-25",
                match_time=datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
            )
            db.add(match)

            with pytest.raises(IntegrityError, match="League does not exist"):
                db.commit()


class TestOddsConstraints:
    """测试赔率表的约束条件"""

    def setup_method(self):
        """设置测试数据"""
        with get_session() as db:
            # 创建测试联赛
            self.test_league = League(
                league_name="Test League", country="Test Country", api_league_id=999996
            )
            db.add(self.test_league)

            # 创建测试球队
            self.test_team1 = Team(
                team_name="Test Team 1",
                team_code="TT1",
                country="Test Country",
                api_team_id=999995,
            )
            self.test_team2 = Team(
                team_name="Test Team 2",
                team_code="TT2",
                country="Test Country",
                api_team_id=999994,
            )
            db.add_all([self.test_team1, self.test_team2])

            # 创建测试比赛
            self.test_match = Match(
                home_team_id=self.test_team1.id,
                away_team_id=self.test_team2.id,
                league_id=self.test_league.id,
                season="2024-25",
                match_time=datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
            )
            db.add(self.test_match)
            db.commit()

            self.match_id = self.test_match.id

    def teardown_method(self):
        """清理测试数据"""
        with get_session() as db:
            # 删除测试数据
            db.query(Odds).filter(Odds.match_id == self.match_id).delete()
            db.query(Match).filter(Match.id == self.match_id).delete()
            db.query(Team).filter(
                Team.id.in_([self.test_team1.id, self.test_team2.id])
            ).delete()
            db.query(League).filter(League.id == self.test_league.id).delete()
            db.commit()

    def test_valid_odds_creation(self):
        """测试创建有效的赔率记录"""
        with get_session() as db:
            odds = Odds(
                match_id=self.match_id,
                bookmaker="Test Bookmaker",
                market_type=MarketType.ONE_X_TWO,
                home_odds=Decimal("2.50"),
                draw_odds=Decimal("3.20"),
                away_odds=Decimal("1.85"),
                collected_at=datetime.now(timezone.utc),
            )
            db.add(odds)
            db.commit()  # 应该成功
            assert odds.id is not None

    def test_odds_minimum_value_constraint(self):
        """测试赔率必须大于1.01"""
        with get_session() as db:
            odds = Odds(
                match_id=self.match_id,
                bookmaker="Test Bookmaker",
                market_type=MarketType.ONE_X_TWO,
                home_odds=Decimal("1.00"),  # 无效赔率
                collected_at=datetime.now(timezone.utc),
            )
            db.add(odds)

            with pytest.raises(IntegrityError, match="ck_odds_home_odds_range"):
                db.commit()

    def test_odds_boundary_value(self):
        """测试赔率边界值"""
        with get_session() as db:
            # 测试正好1.01的边界值（应该失败）
            odds = Odds(
                match_id=self.match_id,
                bookmaker="Test Bookmaker",
                market_type=MarketType.ONE_X_TWO,
                home_odds=Decimal("1.01"),  # 边界值，应该失败
                collected_at=datetime.now(timezone.utc),
            )
            db.add(odds)

            with pytest.raises(IntegrityError, match="ck_odds_home_odds_range"):
                db.commit()

    def test_odds_valid_boundary(self):
        """测试有效的赔率边界值"""
        with get_session() as db:
            # 测试1.02的值（应该成功）
            odds = Odds(
                match_id=self.match_id,
                bookmaker="Test Bookmaker",
                market_type=MarketType.ONE_X_TWO,
                home_odds=Decimal("1.02"),  # 有效值
                collected_at=datetime.now(timezone.utc),
            )
            db.add(odds)
            db.commit()  # 应该成功
            assert odds.id is not None

    def test_odds_match_reference_constraint(self):
        """测试赔率表的比赛引用约束"""
        with get_session() as db:
            odds = Odds(
                match_id=999999,  # 不存在的比赛ID
                bookmaker="Test Bookmaker",
                market_type=MarketType.ONE_X_TWO,
                home_odds=Decimal("2.00"),
                collected_at=datetime.now(timezone.utc),
            )
            db.add(odds)

            with pytest.raises(IntegrityError, match="Match does not exist"):
                db.commit()

    def test_odds_null_values_allowed(self):
        """测试赔率的NULL值是被允许的"""
        with get_session() as db:
            odds = Odds(
                match_id=self.match_id,
                bookmaker="Test Bookmaker",
                market_type=MarketType.ONE_X_TWO,
                home_odds=None,  # NULL值应该被允许
                draw_odds=None,
                away_odds=None,
                collected_at=datetime.now(timezone.utc),
            )
            db.add(odds)
            db.commit()  # 应该成功
            assert odds.id is not None


class TestConstraintsIntegration:
    """测试约束的集成场景"""

    def test_multiple_constraints_violation(self):
        """测试同时违反多个约束"""
        with get_session() as db:
            # 这个测试需要创建一些基础数据
            league = League(
                league_name="Test League", country="Test Country", api_league_id=999993
            )
            team1 = Team(
                team_name="Test Team 1",
                team_code="TT1",
                country="Test Country",
                api_team_id=999992,
            )
            team2 = Team(
                team_name="Test Team 2",
                team_code="TT2",
                country="Test Country",
                api_team_id=999991,
            )
            db.add_all([league, team1, team2])
            db.commit()

            # 尝试创建一个违反多个约束的比赛
            match = Match(
                home_team_id=team1.id,
                away_team_id=team2.id,
                league_id=league.id,
                season="2024-25",
                match_time=datetime(1999, 1, 1, 15, 0, tzinfo=timezone.utc),  # 时间约束违反
                home_score=-5,  # 比分约束违反
                away_score=150,  # 比分约束违反
            )
            db.add(match)

            # 应该触发第一个遇到的约束错误
            with pytest.raises(IntegrityError):
                db.commit()

            # 清理
            db.rollback()
            db.query(Team).filter(Team.id.in_([team1.id, team2.id])).delete()
            db.query(League).filter(League.id == league.id).delete()
            db.commit()

    def test_constraints_with_updates(self):
        """测试约束在UPDATE操作中的行为"""
        with get_session() as db:
            # 创建基础数据
            league = League(
                league_name="Test League", country="Test Country", api_league_id=999990
            )
            team1 = Team(
                team_name="Test Team 1",
                team_code="TT1",
                country="Test Country",
                api_team_id=999989,
            )
            team2 = Team(
                team_name="Test Team 2",
                team_code="TT2",
                country="Test Country",
                api_team_id=999988,
            )
            db.add_all([league, team1, team2])

            # 创建有效的比赛
            match = Match(
                home_team_id=team1.id,
                away_team_id=team2.id,
                league_id=league.id,
                season="2024-25",
                match_time=datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
                home_score=2,
                away_score=1,
            )
            db.add(match)
            db.commit()

            # 尝试更新为无效值
            match.home_score = -1

            with pytest.raises(IntegrityError, match="ck_matches_home_score_range"):
                db.commit()

            # 清理
            db.rollback()
            db.query(Match).filter(Match.id == match.id).delete()
            db.query(Team).filter(Team.id.in_([team1.id, team2.id])).delete()
            db.query(League).filter(League.id == league.id).delete()
            db.commit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
