"""
特征定义模块的单元测试.

测试特征定义、验证器和相关功能。
"""

from __future__ import annotations

from datetime import datetime, timezone


from src.features.feature_definitions import (
    AdvancedStatsFeatures,
    FeatureDefinition,
    FeatureKeys,
    FeatureType,
    HeadToHeadFeatures,
    OddsFeatures,
    RecentPerformanceFeatures,
    get_all_feature_keys,
    get_feature_definition,
    get_required_feature_keys,
    sanitize_features,
    validate_feature_data,
    validate_features_object,
)


class TestFeatureKeys:
    """测试特征键常量。"""

    def test_feature_keys_constants(self):
        """测试特征键常量的定义。"""
        # 测试基础比赛信息
        assert FeatureKeys.MATCH_ID == "match_id"
        assert FeatureKeys.HOME_TEAM_ID == "home_team_id"
        assert FeatureKeys.AWAY_TEAM_ID == "away_team_id"

        # 测试近期战绩特征
        assert FeatureKeys.HOME_RECENT_5_WINS == "home_recent_5_wins"
        assert FeatureKeys.AWAY_RECENT_5_WIN_RATE == "away_recent_5_win_rate"

        # 测试历史对战特征
        assert FeatureKeys.H2H_TOTAL_MATCHES == "h2h_total_matches"
        assert FeatureKeys.H2H_HOME_WIN_RATE == "h2h_home_win_rate"

        # 测试赔率特征
        assert FeatureKeys.HOME_WIN_ODDS == "home_win_odds"
        assert FeatureKeys.HOME_IMPLIED_PROBABILITY == "home_implied_probability"

        # 测试高级分析特征
        assert FeatureKeys.HOME_XG == "home_xg"
        assert FeatureKeys.HOME_POSSESSION == "home_possession"

        # 测试统计特征
        assert FeatureKeys.HOME_AVG_GOALS_SCORED == "home_avg_goals_scored"

        # 测试时间特征
        assert FeatureKeys.DAYS_SINCE_LAST_HOME == "days_since_last_home"


class TestFeatureDefinition:
    """测试特征定义类。"""

    def test_feature_definition_creation(self):
        """测试特征定义的创建。"""
        definition = FeatureDefinition(
            key="test_feature",
            name="Test Feature",
            feature_type=FeatureType.NUMERICAL,
            description="A test feature for validation",
            min_value=0.0,
            max_value=100.0,
            required=True,
            default_value=50.0,
        )

        assert definition.key == "test_feature"
        assert definition.name == "Test Feature"
        assert definition.feature_type == FeatureType.NUMERICAL
        assert definition.description == "A test feature for validation"
        assert definition.min_value == 0.0
        assert definition.max_value == 100.0
        assert definition.required is True
        assert definition.default_value == 50.0

    def test_feature_definition_optional_fields(self):
        """测试特征定义的可选字段。"""
        definition = FeatureDefinition(
            key="simple_feature",
            name="Simple Feature",
            feature_type=FeatureType.CATEGORICAL,
            description="A simple feature",
        )

        assert definition.min_value is None
        assert definition.max_value is None
        assert definition.required is True  # 默认值
        assert definition.default_value is None


class TestRecentPerformanceFeatures:
    """测试近期战绩特征类。"""

    def test_recent_performance_creation(self):
        """测试近期战绩特征的创建。"""
        features = RecentPerformanceFeatures(
            team_id=123,
            calculation_date=datetime.now(timezone.utc),
            recent_5_wins=3,
            recent_5_draws=1,
            recent_5_losses=1,
            recent_5_goals_for=8,
            recent_5_goals_against=5,
        )

        assert features.team_id == 123
        assert features.recent_5_wins == 3
        assert features.recent_5_draws == 1
        assert features.recent_5_losses == 1
        assert features.recent_5_goals_for == 8
        assert features.recent_5_goals_against == 5

    def test_recent_performance_win_rate_property(self):
        """测试胜率计算属性。"""
        # 有胜利的情况
        features = RecentPerformanceFeatures(
            team_id=123, calculation_date=datetime.now(timezone.utc), recent_5_wins=3
        )
        assert features.recent_5_win_rate == 0.6

        # 没有胜利的情况
        features_no_wins = RecentPerformanceFeatures(
            team_id=124, calculation_date=datetime.now(timezone.utc), recent_5_wins=0
        )
        assert features_no_wins.recent_5_win_rate == 0.0

    def test_recent_performance_goals_diff_property(self):
        """测试净胜球计算属性。"""
        features = RecentPerformanceFeatures(
            team_id=123,
            calculation_date=datetime.now(timezone.utc),
            recent_5_goals_for=8,
            recent_5_goals_against=5,
        )
        assert features.recent_5_goals_diff == 3

        # 净失球情况
        features_negative = RecentPerformanceFeatures(
            team_id=124,
            calculation_date=datetime.now(timezone.utc),
            recent_5_goals_for=3,
            recent_5_goals_against=7,
        )
        assert features_negative.recent_5_goals_diff == -4

    def test_recent_performance_validation_success(self):
        """测试有效数据验证。"""
        features = RecentPerformanceFeatures(
            team_id=123,
            calculation_date=datetime.now(timezone.utc),
            recent_5_wins=2,
            recent_5_draws=2,
            recent_5_losses=1,
            recent_5_goals_for=5,
            recent_5_goals_against=4,
        )

        errors = features.validate()
        assert len(errors) == 0

    def test_recent_performance_validation_invalid_wins(self):
        """测试无效胜场数验证。"""
        features = RecentPerformanceFeatures(
            team_id=123,
            calculation_date=datetime.now(timezone.utc),
            recent_5_wins=6,  # 超过5场
            recent_5_draws=0,
            recent_5_losses=0,
        )

        errors = features.validate()
        assert len(errors) > 0
        assert any("Invalid recent_5_wins" in error for error in errors)

    def test_recent_performance_validation_total_exceeds(self):
        """测试总场次超过5场的验证。"""
        features = RecentPerformanceFeatures(
            team_id=123,
            calculation_date=datetime.now(timezone.utc),
            recent_5_wins=3,
            recent_5_draws=3,
            recent_5_losses=0,  # 总共6场，超过限制
        )

        errors = features.validate()
        assert len(errors) > 0
        assert any("Total matches exceed 5" in error for error in errors)

    def test_recent_performance_validation_negative_values(self):
        """测试负数验证。"""
        features = RecentPerformanceFeatures(
            team_id=123,
            calculation_date=datetime.now(timezone.utc),
            recent_5_wins=-1,  # 负数
            recent_5_draws=0,
            recent_5_losses=0,
        )

        errors = features.validate()
        assert len(errors) > 0
        assert any("Invalid recent_5_wins" in error for error in errors)


class TestHeadToHeadFeatures:
    """测试历史对战特征类。"""

    def test_head_to_head_creation(self):
        """测试历史对战特征的创建。"""
        features = HeadToHeadFeatures(
            home_team_id=123,
            away_team_id=456,
            calculation_date=datetime.now(timezone.utc),
            total_matches=10,
            home_wins=6,
            away_wins=3,
            draws=1,
            home_goals=15,
            away_goals=8,
        )

        assert features.home_team_id == 123
        assert features.away_team_id == 456
        assert features.total_matches == 10
        assert features.home_wins == 6
        assert features.away_wins == 3
        assert features.draws == 1

    def test_head_to_head_home_win_rate_property(self):
        """测试主队胜率计算属性。"""
        features = HeadToHeadFeatures(
            home_team_id=123,
            away_team_id=456,
            calculation_date=datetime.now(timezone.utc),
            total_matches=10,
            home_wins=6,
            away_wins=3,
            draws=1,
        )

        assert features.home_win_rate == 0.6

        # 没有比赛的情况
        features_no_matches = HeadToHeadFeatures(
            home_team_id=123,
            away_team_id=456,
            calculation_date=datetime.now(timezone.utc),
            total_matches=0,
            home_wins=0,
            away_wins=0,
            draws=0,
        )

        assert features_no_matches.home_win_rate == 0.0

    def test_head_to_head_avg_total_goals_property(self):
        """测试场均总进球数计算属性。"""
        features = HeadToHeadFeatures(
            home_team_id=123,
            away_team_id=456,
            calculation_date=datetime.now(timezone.utc),
            total_matches=10,
            home_goals=25,
            away_goals=15,
        )

        assert features.avg_total_goals == 4.0

    def test_head_to_head_validation_success(self):
        """测试有效数据验证。"""
        features = HeadToHeadFeatures(
            home_team_id=123,
            away_team_id=456,
            calculation_date=datetime.now(timezone.utc),
            total_matches=10,
            home_wins=6,
            away_wins=3,
            draws=1,
        )

        errors = features.validate()
        assert len(errors) == 0

    def test_head_to_head_validation_mismatch(self):
        """测试总数不匹配的验证。"""
        features = HeadToHeadFeatures(
            home_team_id=123,
            away_team_id=456,
            calculation_date=datetime.now(timezone.utc),
            total_matches=10,
            home_wins=6,
            away_wins=3,
            draws=2,  # 6+3+2=11，不等于total_matches=10
        )

        errors = features.validate()
        assert len(errors) > 0
        assert any("Total mismatch" in error for error in errors)

    def test_head_to_head_validation_negative_values(self):
        """测试负数验证。"""
        features = HeadToHeadFeatures(
            home_team_id=123,
            away_team_id=456,
            calculation_date=datetime.now(timezone.utc),
            total_matches=10,
            home_wins=-1,  # 负数
            away_wins=5,
            draws=5,
        )

        errors = features.validate()
        assert len(errors) > 0
        assert any("Negative match counts" in error for error in errors)


class TestOddsFeatures:
    """测试赔率特征类。"""

    def test_odds_features_creation(self):
        """测试赔率特征的创建。"""
        features = OddsFeatures(
            match_id=12345,
            calculation_date=datetime.now(timezone.utc),
            bookmaker="William Hill",
            home_win_odds=2.1,
            draw_odds=3.2,
            away_win_odds=3.8,
        )

        assert features.match_id == 12345
        assert features.bookmaker == "William Hill"
        assert features.home_win_odds == 2.1
        assert features.draw_odds == 3.2
        assert features.away_win_odds == 3.8

    def test_odds_implied_probability_property(self):
        """测试隐含概率计算属性。"""
        features = OddsFeatures(
            match_id=12345,
            calculation_date=datetime.now(timezone.utc),
            bookmaker="Test",
            home_win_odds=2.0,
        )

        assert features.home_implied_probability == 0.5

        # 无赔率的情况
        features_no_odds = OddsFeatures(
            match_id=12346,
            calculation_date=datetime.now(timezone.utc),
            bookmaker="Test",
        )

        assert features_no_odds.home_implied_probability is None

        # 无效赔率的情况
        features_invalid = OddsFeatures(
            match_id=12347,
            calculation_date=datetime.now(timezone.utc),
            bookmaker="Test",
            home_win_odds=1.0,  # 1.0的隐含概率是1.0，但通常赔率会>1.0
        )

        assert features_invalid.home_implied_probability is None

    def test_odds_bookmaker_consensus_property(self):
        """测试庄家倾向属性。"""
        # 主队最低赔率
        features_home = OddsFeatures(
            match_id=12345,
            calculation_date=datetime.now(timezone.utc),
            bookmaker="Test",
            home_win_odds=2.0,
            draw_odds=3.0,
            away_win_odds=4.0,
        )
        assert features_home.bookmaker_consensus == "home"

        # 客队最低赔率
        features_away = OddsFeatures(
            match_id=12346,
            calculation_date=datetime.now(timezone.utc),
            bookmaker="Test",
            home_win_odds=4.0,
            draw_odds=3.0,
            away_win_odds=2.0,
        )
        assert features_away.bookmaker_consensus == "away"

        # 平局最低赔率
        features_draw = OddsFeatures(
            match_id=12347,
            calculation_date=datetime.now(timezone.utc),
            bookmaker="Test",
            home_win_odds=3.0,
            draw_odds=2.5,
            away_win_odds=4.0,
        )
        assert features_draw.bookmaker_consensus == "draw"

        # 缺少赔率信息
        features_missing = OddsFeatures(
            match_id=12348,
            calculation_date=datetime.now(timezone.utc),
            bookmaker="Test",
        )
        assert features_missing.bookmaker_consensus is None

    def test_odds_validation_success(self):
        """测试有效赔率数据验证。"""
        features = OddsFeatures(
            match_id=12345,
            calculation_date=datetime.now(timezone.utc),
            bookmaker="Test",
            home_win_odds=2.1,
            draw_odds=3.2,
            away_win_odds=3.8,
        )

        errors = features.validate()
        assert len(errors) == 0

    def test_odds_validation_invalid_odds(self):
        """测试无效赔率验证。"""
        features = OddsFeatures(
            match_id=12345,
            calculation_date=datetime.now(timezone.utc),
            bookmaker="Test",
            home_win_odds=0.5,  # 赔率不能 <= 1.0
        )

        errors = features.validate()
        assert len(errors) > 0
        assert any("Invalid home_win_odds" in error for error in errors)


class TestAdvancedStatsFeatures:
    """测试高级统计特征类。"""

    def test_advanced_stats_creation(self):
        """测试高级统计特征的创建。"""
        features = AdvancedStatsFeatures(
            match_id=12345,
            team_id=123,
            calculation_date=datetime.now(timezone.utc),
            xg=1.5,
            xga=1.2,
            ppda=8.5,
            possession=55.0,
        )

        assert features.match_id == 12345
        assert features.team_id == 123
        assert features.xg == 1.5
        assert features.xga == 1.2
        assert features.ppda == 8.5
        assert features.possession == 55.0

    def test_advanced_stats_validation_success(self):
        """测试有效高级统计数据验证。"""
        features = AdvancedStatsFeatures(
            match_id=12345,
            team_id=123,
            calculation_date=datetime.now(timezone.utc),
            xg=1.5,
            xga=1.2,
            ppda=8.5,
            possession=55.0,
        )

        errors = features.validate()
        assert len(errors) == 0

    def test_advanced_stats_validation_invalid_xg(self):
        """测试无效xG值验证。"""
        features = AdvancedStatsFeatures(
            match_id=12345,
            team_id=123,
            calculation_date=datetime.now(timezone.utc),
            xg=-1.0,  # xG不能为负数
        )

        errors = features.validate()
        assert len(errors) > 0
        assert any("Invalid xg" in error for error in errors)

    def test_advanced_stats_validation_invalid_possession(self):
        """测试无效控球率验证。"""
        features = AdvancedStatsFeatures(
            match_id=12345,
            team_id=123,
            calculation_date=datetime.now(timezone.utc),
            possession=150.0,  # 控球率不能超过100%
        )

        errors = features.validate()
        assert len(errors) > 0
        assert any("Invalid possession" in error for error in errors)


class TestFeatureValidator:
    """测试特征验证器类。"""

    def test_validate_feature_data_success(self):
        """测试有效特征数据验证。"""
        features = {
            "match_id": 12345,
            "home_recent_5_wins": 3,
            "home_recent_5_win_rate": 0.6,
            "home_xg": 1.5,
        }

        errors = validate_feature_data(features)
        assert len(errors) == 0

    def test_validate_feature_data_missing_required(self):
        """测试缺少必需特征验证。"""
        features = {
            "home_recent_5_wins": 3,
            "home_recent_5_win_rate": 0.6,
            # 缺少必需的 match_id
        }

        errors = validate_feature_data(features)
        assert len(errors) > 0
        assert any("Missing required feature: match_id" in error for error in errors)

    def test_validate_feature_data_invalid_type(self):
        """测试无效类型验证。"""
        features = {"match_id": "12345", "home_recent_5_wins": 3}  # 应该是数值

        errors = validate_feature_data(features)
        assert len(errors) > 0
        assert any("must be numerical" in error for error in errors)

    def test_validate_feature_data_out_of_range(self):
        """测试超出范围验证。"""
        features = {
            "match_id": 12345,
            "home_recent_5_wins": 6,  # 超过最大值5
            "home_recent_5_win_rate": 1.5,  # 超过最大值1.0
        }

        errors = validate_feature_data(features)
        assert len(errors) >= 2  # 应该有两个错误

    def test_sanitize_features_type_conversion(self):
        """测试特征数据类型转换。"""
        features = {
            "match_id": "12345",  # 字符串转数值
            "home_recent_5_win_rate": "0.6",  # 字符串转浮点数
            "invalid_feature": "not_convertible",
        }

        sanitized = sanitize_features(features)

        # 验证类型转换
        assert isinstance(sanitized["match_id"], float)
        assert sanitized["match_id"] == 12345.0
        assert isinstance(sanitized["home_recent_5_win_rate"], float)
        assert sanitized["home_recent_5_win_rate"] == 0.6
        # 无效特征应该被过滤掉
        assert "invalid_feature" not in sanitized

    def test_sanitize_features_default_values(self):
        """测试默认值填充。"""
        features = {
            "match_id": 12345
            # 缺少其他必需特征
        }

        sanitized = sanitize_features(features)

        # 应该包含默认值的特征
        assert "match_id" in sanitized
        assert "home_recent_5_wins" in sanitized
        assert sanitized["home_recent_5_wins"] == 0  # 默认值


class TestUtilityFunctions:
    """测试工具函数。"""

    def test_get_all_feature_keys(self):
        """测试获取所有特征键。"""
        keys = get_all_feature_keys()

        assert isinstance(keys, list)
        assert len(keys) > 0
        assert FeatureKeys.MATCH_ID in keys
        assert FeatureKeys.HOME_RECENT_5_WINS in keys

    def test_get_required_feature_keys(self):
        """测试获取必需特征键。"""
        keys = get_required_feature_keys()

        assert isinstance(keys, list)
        assert len(keys) > 0
        assert FeatureKeys.MATCH_ID in keys
        assert FeatureKeys.HOME_TEAM_ID in keys
        assert FeatureKeys.AWAY_TEAM_ID in keys

    def test_get_feature_definition(self):
        """测试获取特征定义。"""
        # 获取存在的特征定义
        definition = get_feature_definition(FeatureKeys.MATCH_ID)
        assert definition is not None
        assert definition.key == FeatureKeys.MATCH_ID
        assert definition.feature_type == FeatureType.NUMERICAL

        # 获取不存在的特征定义
        definition = get_feature_definition("nonexistent_feature")
        assert definition is None

    def test_validate_features_object_with_validation_method(self):
        """测试有验证方法的特征对象验证。"""
        features = RecentPerformanceFeatures(
            team_id=123,
            calculation_date=datetime.now(timezone.utc),
            recent_5_wins=3,
            recent_5_draws=1,
            recent_5_losses=1,
        )

        errors = validate_features_object(features)
        assert len(errors) == 0  # 有效数据

        # 无效数据
        invalid_features = RecentPerformanceFeatures(
            team_id=123,
            calculation_date=datetime.now(timezone.utc),
            recent_5_wins=6,  # 超过5场限制
        )

        errors = validate_features_object(invalid_features)
        assert len(errors) > 0

    def test_validate_features_object_without_validation_method(self):
        """测试没有验证方法的普通对象。"""

        class SimpleObject:
            pass

        obj = SimpleObject()
        errors = validate_features_object(obj)
        assert len(errors) == 0  # 没有验证方法，直接通过
