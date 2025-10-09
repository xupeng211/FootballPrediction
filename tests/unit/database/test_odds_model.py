"""赔率模型测试"""
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
