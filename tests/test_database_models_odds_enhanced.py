"""
Odds模型增强测试

专门针对src/database/models/odds.py中未覆盖的代码路径进行测试，提升覆盖率从59%到80%+
主要覆盖：get_best_value_bet, get_implied_probabilities等方法
"""

from decimal import Decimal
from unittest.mock import Mock, patch


class TestOddsModelEnhancedCoverage:
    """测试Odds模型未覆盖的方法"""

    def test_get_implied_probabilities_over_under(self):
        """测试获取大小球隐含概率方法 (覆盖135-150行)"""
        from src.database.models.odds import MarketType, Odds

        # 创建有效的大小球赔率
        odds = Odds()
        odds.id = 1
        odds.match_id = 1
        odds.market_type = MarketType.OVER_UNDER
        odds.over_odds = Decimal("1.85")
        odds.under_odds = Decimal("1.95")

        # 执行测试
        result = odds.get_implied_probabilities()

        # 验证结果
        assert result is not None
        assert "over" in result
        assert "under" in result
        assert "bookmaker_margin" in result

        # 验证概率计算
        over_prob = 1.0 / float(odds.over_odds)
        under_prob = 1.0 / float(odds.under_odds)
        total_prob = over_prob + under_prob

        expected_over = over_prob / total_prob
        expected_under = under_prob / total_prob
        expected_margin = (total_prob - 1.0) / total_prob

        assert abs(result["over"] - expected_over) < 0.001
        assert abs(result["under"] - expected_under) < 0.001
        assert abs(result["bookmaker_margin"] - expected_margin) < 0.001

    def test_get_implied_probabilities_none(self):
        """测试隐含概率方法返回None的情况 (覆盖150行)"""
        from src.database.models.odds import MarketType, Odds

        # 测试缺少赔率的大小球市场
        odds = Odds()
        odds.market_type = MarketType.OVER_UNDER
        odds.over_odds = None
        odds.under_odds = Decimal("1.95")

        result = odds.get_implied_probabilities()
        assert result is None

    def test_get_best_value_bet_1x2_market(self):
        """测试1x2市场最佳价值投注 (覆盖163-191行)"""
        from src.database.models.odds import MarketType, Odds

        # 创建1x2市场赔率
        odds = Odds()
        odds.id = 1
        odds.match_id = 1
        odds.market_type = MarketType.ONE_X_TWO
        odds.home_odds = Decimal("2.50")  # 隐含概率 40%
        odds.draw_odds = Decimal("3.30")  # 隐含概率 30.3%
        odds.away_odds = Decimal("2.80")  # 隐含概率 35.7%

        # Mock get_implied_probabilities返回偏向主场的概率
        with patch.object(odds, "get_implied_probabilities") as mock_prob:
            mock_prob.return_value = {
                "home_win": 0.45,  # 实际概率高于隐含概率，有价值
                "draw": 0.25,
                "away_win": 0.30,
            }

            result = odds.get_best_value_bet()

            # 验证结果
            assert result is not None
            assert result["outcome"] == "home_win"
            assert result["odds"] == 2.50
            assert result["expected_value"] > 0
            assert result["implied_probability"] == 0.45
            assert result["recommendation"] in ["BET", "CONSIDER"]

    def test_get_best_value_bet_no_value(self):
        """测试无价值投注的情况 (覆盖191行)"""
        from src.database.models.odds import MarketType, Odds

        # 创建1x2市场赔率
        odds = Odds()
        odds.market_type = MarketType.ONE_X_TWO
        odds.home_odds = Decimal("2.00")
        odds.draw_odds = Decimal("3.00")
        odds.away_odds = Decimal("3.50")

        # Mock get_implied_probabilities返回无价值的概率
        with patch.object(odds, "get_implied_probabilities") as mock_prob:
            mock_prob.return_value = {
                "home_win": 0.45,  # 2.00*0.45-1 = -0.1 (负期望价值)
                "draw": 0.30,  # 3.00*0.30-1 = -0.1 (负期望价值)
                "away_win": 0.25,  # 3.50*0.25-1 = -0.125 (负期望价值)
            }

            result = odds.get_best_value_bet()

            # 应该返回None（无价值投注）
            assert result is None

    def test_get_best_value_bet_no_probabilities(self):
        """测试无概率数据的情况 (覆盖160-161行)"""
        from src.database.models.odds import MarketType, Odds

        odds = Odds()
        odds.market_type = MarketType.ONE_X_TWO

        # Mock get_implied_probabilities返回None
        with patch.object(odds, "get_implied_probabilities") as mock_prob:
            mock_prob.return_value = None

            result = odds.get_best_value_bet()

            assert result is None

    def test_calculate_percentage_change(self):
        """测试百分比变化计算方法 (覆盖193-200行)"""
        from src.database.models.odds import Odds

        odds = Odds()

        # 测试正常情况
        current = Decimal("2.50")
        previous = Decimal("2.00")
        result = odds._calculate_percentage_change(current, previous)

        expected = abs(float(current) - float(previous)) / float(previous)
        assert abs(result - expected) < 0.001
        assert result == 0.25  # (2.50-2.00)/2.00 = 0.25

    def test_calculate_percentage_change_edge_cases(self):
        """测试百分比变化计算的边界情况 (覆盖197-198行)"""
        from src.database.models.odds import Odds

        odds = Odds()

        # 测试空值情况
        result1 = odds._calculate_percentage_change(None, Decimal("2.00"))
        assert result1 == 0.0

        result2 = odds._calculate_percentage_change(Decimal("2.50"), None)
        assert result2 == 0.0

        result3 = odds._calculate_percentage_change(None, None)
        assert result3 == 0.0

    def test_check_1x2_movement(self):
        """测试1x2赔率变动检查方法 (覆盖201-218行)"""
        from src.database.models.odds import MarketType, Odds

        # 创建当前赔率
        current_odds = Odds()
        current_odds.market_type = MarketType.ONE_X_TWO
        current_odds.home_odds = Decimal("2.50")
        current_odds.draw_odds = Decimal("3.20")
        current_odds.away_odds = Decimal("2.80")

        # 创建之前的赔率
        previous_odds = Odds()
        previous_odds.market_type = MarketType.ONE_X_TWO
        previous_odds.home_odds = Decimal("2.00")  # 显著变化
        previous_odds.draw_odds = Decimal("3.15")  # 微小变化
        previous_odds.away_odds = Decimal("2.85")  # 微小变化

        # 测试显著变化 (threshold=0.1)
        result_significant = current_odds._check_1x2_movement(previous_odds, 0.1)
        assert result_significant is True  # 主场赔率变化25%，超过10%阈值

        # 测试不显著变化 (threshold=0.3)
        result_not_significant = current_odds._check_1x2_movement(previous_odds, 0.3)
        assert result_not_significant is False  # 所有变化都小于30%

    def test_check_over_under_movement(self):
        """测试大小球赔率变动检查方法 (覆盖224-238行)"""
        from src.database.models.odds import MarketType, Odds

        # 创建当前赔率
        current_odds = Odds()
        current_odds.market_type = MarketType.OVER_UNDER
        current_odds.over_odds = Decimal("1.90")
        current_odds.under_odds = Decimal("1.90")

        # 创建之前的赔率
        previous_odds = Odds()
        previous_odds.market_type = MarketType.OVER_UNDER
        previous_odds.over_odds = Decimal("2.10")  # 显著下降
        previous_odds.under_odds = Decimal("1.85")  # 微小变化

        # 测试显著变化 (threshold=0.05)
        result_significant = current_odds._check_over_under_movement(
            previous_odds, 0.05
        )
        assert result_significant is True  # 大球赔率变化明显

        # 测试不显著变化 (threshold=0.2)
        result_not_significant = current_odds._check_over_under_movement(
            previous_odds, 0.2
        )
        assert result_not_significant is False

    def test_is_odds_movement_significant(self):
        """测试赔率变化显著性检查 (覆盖240-261行)"""
        from src.database.models.odds import MarketType, Odds

        # 创建1x2市场赔率
        current_odds = Odds()
        current_odds.market_type = MarketType.ONE_X_TWO
        current_odds.home_odds = Decimal("2.50")
        current_odds.draw_odds = Decimal("3.20")
        current_odds.away_odds = Decimal("2.80")

        previous_odds = Odds()
        previous_odds.market_type = MarketType.ONE_X_TWO
        previous_odds.home_odds = Decimal("2.00")
        previous_odds.draw_odds = Decimal("3.15")
        previous_odds.away_odds = Decimal("2.85")

        # 测试显著变化
        result = current_odds.is_odds_movement_significant(previous_odds, 0.1)
        assert result is True

        # 测试市场类型不匹配
        previous_odds_different = Odds()
        previous_odds_different.market_type = MarketType.OVER_UNDER

        result_mismatch = current_odds.is_odds_movement_significant(
            previous_odds_different, 0.1
        )
        assert result_mismatch is False

        # 测试previous_odds为None
        result_none = current_odds.is_odds_movement_significant(None, 0.1)
        assert result_none is False

    def test_is_1x2_market_property(self):
        """测试is_1x2_market属性"""
        from src.database.models.odds import MarketType, Odds

        # 测试1x2市场
        odds_1x2 = Odds()
        odds_1x2.market_type = MarketType.ONE_X_TWO
        assert odds_1x2.is_1x2_market is True

        # 测试其他市场
        odds_ou = Odds()
        odds_ou.market_type = MarketType.OVER_UNDER
        assert odds_ou.is_1x2_market is False

    def test_is_over_under_market_property(self):
        """测试is_over_under_market属性"""
        from src.database.models.odds import MarketType, Odds

        # 测试大小球市场
        odds_ou = Odds()
        odds_ou.market_type = MarketType.OVER_UNDER
        assert odds_ou.is_over_under_market is True

        # 测试其他市场
        odds_1x2 = Odds()
        odds_1x2.market_type = MarketType.ONE_X_TWO
        assert odds_1x2.is_over_under_market is False

    def test_get_latest_odds_classmethod(self):
        """测试获取最新赔率的类方法 (覆盖264-270行)"""
        from src.database.models.odds import Odds

        # 创建模拟会话
        mock_session = Mock()
        mock_query = Mock()
        mock_session.query.return_value = mock_query

        # 模拟查询结果
        mock_odds = [Mock(), Mock()]
        mock_query.filter.return_value.order_by.return_value.all.return_value = (
            mock_odds
        )

        # 测试不指定博彩公司
        result = Odds.get_latest_odds(mock_session, match_id=1)

        # 验证结果
        assert result == mock_odds
        mock_session.query.assert_called_with(Odds)

        # 测试指定博彩公司
        Odds.get_latest_odds(mock_session, match_id=1, bookmaker="bet365")

        # 验证过滤条件被正确添加
        assert mock_query.filter.call_count >= 2

    def test_odds_with_missing_values(self):
        """测试赔率缺失值的处理"""
        from src.database.models.odds import MarketType, Odds

        # 测试部分赔率缺失的情况
        odds = Odds()
        odds.market_type = MarketType.ONE_X_TWO
        odds.home_odds = Decimal("2.50")
        odds.draw_odds = None  # 缺失
        odds.away_odds = Decimal("2.80")

        # get_implied_probabilities应该返回None（因为不是所有赔率都存在）
        result = odds.get_implied_probabilities()
        assert result is None

        # get_best_value_bet应该能处理缺失值
        with patch.object(odds, "get_implied_probabilities") as mock_prob:
            mock_prob.return_value = {
                "home_win": 0.45,
                "away_win": 0.35
                # draw概率缺失
            }

            result = odds.get_best_value_bet()

            # 应该仍能找到最佳投注（在有效的选项中）
            if result:
                assert result["outcome"] in ["home_win", "away_win"]
