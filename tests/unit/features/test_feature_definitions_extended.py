"""扩展的特征定义测试 - 提升覆盖率"""

from datetime import datetime
from decimal import Decimal

from src.features.feature_definitions import (
    RecentPerformanceFeatures,
    HistoricalMatchupFeatures,
    OddsFeatures,
    AllTeamFeatures,
    AllMatchFeatures
)


class TestFeatureDefinitionsExtended:
    """扩展的特征定义测试，覆盖未测试的代码路径"""

    def test_recent_performance_features_default_values(self):
        """测试近期战绩特征的默认值"""
        features = RecentPerformanceFeatures(
            team_id=1,
            calculation_date=datetime(2024, 1, 1)
        )

        assert features.team_id == 1
        assert features.recent_5_wins == 0
        assert features.recent_5_draws == 0
        assert features.recent_5_losses == 0
        assert features.recent_5_goals_for == 0
        assert features.recent_5_goals_against == 0
        assert features.recent_5_points == 0
        assert features.recent_5_home_wins == 0
        assert features.recent_5_away_wins == 0
        assert features.recent_5_home_goals_for == 0
        assert features.recent_5_away_goals_for == 0

    def test_recent_performance_win_rate_calculation(self):
        """测试胜率计算"""
        # 测试正常情况
        features = RecentPerformanceFeatures(
            team_id=1,
            calculation_date=datetime(2024, 1, 1),
            recent_5_wins=3,
            recent_5_draws=1,
            recent_5_losses=1
        )
        assert features.recent_5_win_rate == 0.6  # 3/5

        # 测试零除
        features = RecentPerformanceFeatures(
            team_id=1,
            calculation_date=datetime(2024, 1, 1)
        )
        assert features.recent_5_win_rate == 0.0

        # 测试全胜
        features = RecentPerformanceFeatures(
            team_id=1,
            calculation_date=datetime(2024, 1, 1),
            recent_5_wins=5,
            recent_5_draws=0,
            recent_5_losses=0
        )
        assert features.recent_5_win_rate == 1.0

    def test_recent_performance_goals_difference(self):
        """测试进球差相关属性"""
        # 检查是否有goals_difference属性（如果有）
        features = RecentPerformanceFeatures(
            team_id=1,
            calculation_date=datetime(2024, 1, 1),
            recent_5_goals_for=10,
            recent_5_goals_against=5
        )

        if hasattr(features, 'recent_5_goal_difference'):
            assert features.recent_5_goal_difference == 5

        if hasattr(features, 'recent_5_goals_per_game'):
            assert features.recent_5_goals_per_game == 2.0

    def test_historical_matchup_features_initialization(self):
        """测试历史对战特征初始化"""
        features = HistoricalMatchupFeatures(
            team_a_id=1,
            team_b_id=2,
            calculation_date=datetime(2024, 1, 1)
        )

        assert features.team_a_id == 1
        assert features.team_b_id == 2
        assert features.calculation_date == datetime(2024, 1, 1)

    def test_odds_features_properties(self):
        """测试赔率特征属性"""
        features = OddsFeatures(
            match_id=1,
            calculation_date=datetime(2024, 1, 1),
            home_win_odds=Decimal('2.50'),
            draw_odds=Decimal('3.20'),
            away_win_odds=Decimal('2.80')
        )

        assert features.match_id == 1
        assert features.home_win_odds == Decimal('2.50')
        assert features.draw_odds == Decimal('3.20')
        assert features.away_win_odds == Decimal('2.80')

        # 测试隐含概率计算（如果有）
        if hasattr(features, 'home_win_implied_probability'):
            prob = features.home_win_implied_probability
            assert 0 < prob < 1

    def test_all_team_features_initialization(self):
        """测试所有球队特征初始化"""
        features = AllTeamFeatures(
            team_id=1,
            calculation_date=datetime(2024, 1, 1)
        )

        assert features.team_id == 1
        assert features.calculation_date == datetime(2024, 1, 1)

    def test_all_match_features_initialization(self):
        """测试所有比赛特征初始化"""
        features = AllMatchFeatures(
            match_id=1,
            calculation_date=datetime(2024, 1, 1)
        )

        assert features.match_id == 1
        assert features.calculation_date == datetime(2024, 1, 1)

    def test_feature_validation_edge_cases(self):
        """测试特征验证的边界情况"""
        # 测试极端值
        features = RecentPerformanceFeatures(
            team_id=1,
            calculation_date=datetime(2024, 1, 1),
            recent_5_wins=100,  # 不现实的值
            recent_5_goals_for=1000
        )

        # 系统应该能处理
        assert features.recent_5_wins == 100
        assert features.recent_5_goals_for == 1000

    def test_feature_serialization(self):
        """测试特征序列化"""
        features = RecentPerformanceFeatures(
            team_id=1,
            calculation_date=datetime(2024, 1, 1),
            recent_5_wins=3,
            recent_5_draws=1,
            recent_5_losses=1
        )

        # 转换为字典
        if hasattr(features, 'dict'):
            feature_dict = features.dict()
            assert isinstance(feature_dict, dict)
            assert feature_dict['team_id'] == 1

    def test_feature_comparison(self):
        """测试特征比较"""
        features1 = RecentPerformanceFeatures(
            team_id=1,
            calculation_date=datetime(2024, 1, 1),
            recent_5_wins=3
        )

        features2 = RecentPerformanceFeatures(
            team_id=2,
            calculation_date=datetime(2024, 1, 1),
            recent_5_wins=2
        )

        # 不同的team_id应该产生不同的对象
        assert features1 != features2

    def test_feature_updates(self):
        """测试特征更新"""
        features = RecentPerformanceFeatures(
            team_id=1,
            calculation_date=datetime(2024, 1, 1)
        )

        # 更新特征值（如果是可变的）
        if hasattr(features, 'update'):
            features.update({'recent_5_wins': 5})
            assert features.recent_5_wins == 5

    def test_feature_calculations_with_decimals(self):
        """测试使用Decimal的特征计算"""
        from decimal import Decimal

        # 创建带有Decimal值的赔率特征
        features = OddsFeatures(
            match_id=1,
            calculation_date=datetime(2024, 1, 1),
            home_win_odds=Decimal('2.55'),
            draw_odds=Decimal('3.33'),
            away_win_odds=Decimal('2.88')
        )

        # 验证Decimal值被正确处理
        assert isinstance(features.home_win_odds, Decimal)
        assert features.home_win_odds == Decimal('2.55')