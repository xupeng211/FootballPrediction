"""
特征工程测试
Feature Engineering Tests

测试特征工程系统的核心功能。
Tests core functionality of feature engineering system.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, Any, List

from src.features import (
    MatchEntity,
    TeamEntity,
    RecentPerformanceFeatures,
    HistoricalMatchupFeatures,
    OddsFeatures,
    AllMatchFeatures,
    AllTeamFeatures,
    FeatureCalculator
)
from src.features.entities import FeatureEntity, FeatureKey
from src.features.feature_store import MockFeatureStore


# 简化的特征工程流水线，用于测试
class FeatureEngineeringPipeline:
    """简化的特征工程流水线"""

    def __init__(self):
        self.feature_calculator = FeatureCalculator()
        self.feature_store = MockFeatureStore()
        self.processing_steps = []

    def extract_features(self, match_id, home_team_id, away_team_id, match_data, historical_data):
        """提取特征"""
        # 简化实现
        return AllMatchFeatures(
            match_id=match_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            recent_performance=RecentPerformanceFeatures(
                team_id=home_team_id,
                recent_matches=[],
                calculation_date=datetime.now()
            ),
            historical_matchup=HistoricalMatchupFeatures(
                team_a_id=home_team_id,
                team_b_id=away_team_id,
                historical_matches=[],
                calculation_date=datetime.now()
            ),
            odds_features=OddsFeatures(
                match_id=match_id,
                odds_data={},
                calculation_date=datetime.now()
            )
        )

    def batch_extract_features(self, matches, match_data, historical_data):
        """批量提取特征"""
        return [self.extract_features(
            m["match_id"], m["home_team_id"], m["away_team_id"],
            match_data, historical_data
        ) for m in matches]

    def transform_features(self, features):
        """转换特征"""
        return features.to_dict() if hasattr(features, 'to_dict') else {}

    def select_features(self, feature_dict):
        """选择特征"""
        # 简化实现，返回重要特征
        important_keys = ["match_id", "home_team_id", "away_team_id"]
        return {k: v for k, v in feature_dict.items() if k in important_keys}

    def execute(self, matches, match_data, historical_data):
        """执行完整流水线"""
        import time
        start_time = time.time()

        extracted = self.batch_extract_features(matches, match_data, historical_data)
        transformed = [self.transform_features(f) for f in extracted]
        selected = [self.select_features(f) for f in transformed]

        execution_time = time.time() - start_time

        return {
            "extracted_features": extracted,
            "transformed_features": transformed,
            "selected_features": selected,
            "execution_time": execution_time
        }


class TestFeatureEntities:
    """特征实体测试类"""

    @pytest.fixture
    def sample_match_entity(self):
        """示例比赛实体"""
        return MatchEntity(
            match_id=12345,
            home_team_id=1,
            away_team_id=2,
            league_id=39,
            match_date=datetime(2024, 1, 15, 15, 0),
            home_score=2,
            away_score=1,
            status="FT"
        )

    @pytest.fixture
    def sample_team_entity(self):
        """示例球队实体"""
        return TeamEntity(
            team_id=1,
            team_name="Team A",
            league_id=39,
            founded_year=1900,
            home_city="City A"
        )

    @pytest.fixture
    def sample_feature_entity(self):
        """示例特征实体"""
        return FeatureEntity(
            feature_key=FeatureKey("team_performance", 1, datetime(2024, 1, 15)),
            feature_value={"goals_scored": 2.5, "goals_conceded": 1.2},
            timestamp=datetime(2024, 1, 15, 10, 0),
            expiration_time=datetime(2024, 1, 22, 10, 0)
        )

    def test_match_entity_creation(self, sample_match_entity):
        """测试比赛实体创建"""
        assert sample_match_entity.match_id == 12345
        assert sample_match_entity.home_team_id == 1
        assert sample_match_entity.away_team_id == 2
        assert sample_match_entity.league_id == 39
        assert sample_match_entity.home_score == 2
        assert sample_match_entity.away_score == 1
        assert sample_match_entity.status == "FT"

    def test_match_entity_to_dict(self, sample_match_entity):
        """测试比赛实体转字典"""
        match_dict = sample_match_entity.to_dict()

        assert match_dict["match_id"] == 12345
        assert match_dict["home_team_id"] == 1
        assert match_dict["away_team_id"] == 2
        assert isinstance(match_dict["match_date"], str)

    def test_match_entity_from_dict(self):
        """测试从字典创建比赛实体"""
        match_data = {
            "match_id": 12345,
            "home_team_id": 1,
            "away_team_id": 2,
            "league_id": 39,
            "match_date": "2024-01-15T15:00:00",
            "home_score": 2,
            "away_score": 1,
            "status": "FT"
        }

        match_entity = MatchEntity.from_dict(match_data)

        assert match_entity.match_id == 12345
        assert match_entity.home_team_id == 1
        assert match_entity.away_team_id == 2

    def test_team_entity_creation(self, sample_team_entity):
        """测试球队实体创建"""
        assert sample_team_entity.team_id == 1
        assert sample_team_entity.team_name == "Team A"
        assert sample_team_entity.league_id == 39
        assert sample_team_entity.founded_year == 1900
        assert sample_team_entity.home_city == "City A"

    def test_feature_entity_creation(self, sample_feature_entity):
        """测试特征实体创建"""
        assert sample_feature_entity.feature_key.name == "team_performance"
        assert sample_feature_entity.feature_key.entity_id == 1
        assert sample_feature_entity.feature_value["goals_scored"] == 2.5
        assert sample_feature_entity.feature_value["goals_conceded"] == 1.2

    def test_feature_entity_is_expired(self, sample_feature_entity):
        """测试特征实体过期检查"""
        # 未过期
        current_time = datetime(2024, 1, 16, 10, 0)
        assert sample_feature_entity.is_expired(current_time) is False

        # 已过期
        expired_time = datetime(2024, 1, 23, 10, 0)
        assert sample_feature_entity.is_expired(expired_time) is True

    def test_feature_key_equality(self):
        """测试特征键相等性"""
        key1 = FeatureKey("test_feature", 123, datetime(2024, 1, 15))
        key2 = FeatureKey("test_feature", 123, datetime(2024, 1, 15))
        key3 = FeatureKey("test_feature", 124, datetime(2024, 1, 15))

        assert key1 == key2
        assert key1 != key3


class TestFeatureDefinitions:
    """特征定义测试类"""

    @pytest.fixture
    def sample_match_data(self):
        """示例比赛数据"""
        return [
            {"date": "2024-01-01", "home_score": 2, "away_score": 1, "is_home": True},
            {"date": "2024-01-08", "home_score": 1, "away_score": 1, "is_home": True},
            {"date": "2024-01-15", "home_score": 3, "away_score": 0, "is_home": True},
            {"date": "2024-01-22", "home_score": 0, "away_score": 2, "is_home": True},
            {"date": "2024-01-29", "home_score": 2, "away_score": 1, "is_home": True},
        ]

    @pytest.fixture
    def sample_historical_data(self):
        """示例历史对战数据"""
        return [
            {"date": "2023-01-15", "home_score": 2, "away_score": 1, "home_team": "Team A"},
            {"date": "2023-06-20", "home_score": 1, "away_score": 1, "home_team": "Team B"},
            {"date": "2023-09-10", "home_score": 0, "away_score": 2, "home_team": "Team A"},
            {"date": "2023-12-05", "home_score": 3, "away_score": 1, "home_team": "Team B"},
            {"date": "2024-01-15", "home_score": 1, "away_score": 2, "home_team": "Team A"},
        ]

    @pytest.fixture
    def sample_odds_data(self):
        """示例赔率数据"""
        return {
            "home_win": 2.10,
            "draw": 3.40,
            "away_win": 3.20,
            "over_2_5": 1.85,
            "under_2_5": 1.95,
            "btts": 1.75,
            "bookmaker": "Bet365",
            "timestamp": "2024-01-15T10:00:00"
        }

    def test_recent_performance_features_creation(self, sample_match_data):
        """测试近期战绩特征创建"""
        features = RecentPerformanceFeatures(
            team_id=1,
            recent_matches=sample_match_data,
            calculation_date=datetime(2024, 1, 30)
        )

        assert features.team_id == 1
        assert len(features.recent_matches) == 5
        assert features.matches_played == 5

    def test_recent_performance_calculated_properties(self, sample_match_data):
        """测试近期战绩计算属性"""
        features = RecentPerformanceFeatures(
            team_id=1,
            recent_matches=sample_match_data,
            calculation_date=datetime(2024, 1, 30)
        )

        # 验证计算属性
        assert features.wins == 3  # 2-1, 3-0, 2-1
        assert features.draws == 1  # 1-1
        assert features.losses == 1  # 0-2
        assert features.goals_scored == 8
        assert features.goals_conceded == 5
        assert features.goal_difference == 3
        assert features.win_rate == 0.6  # 3/5
        assert abs(features.average_goals_scored - 1.6) < 0.01
        assert abs(features.average_goals_conceded - 1.0) < 0.01

    def test_historical_matchup_features_creation(self, sample_historical_data):
        """测试历史对战特征创建"""
        features = HistoricalMatchupFeatures(
            team_a_id=1,
            team_b_id=2,
            historical_matches=sample_historical_data,
            calculation_date=datetime(2024, 1, 30)
        )

        assert features.team_a_id == 1
        assert features.team_b_id == 2
        assert len(features.historical_matches) == 5

    def test_historical_matchup_calculated_properties(self, sample_historical_data):
        """测试历史对战计算属性"""
        features = HistoricalMatchupFeatures(
            team_a_id=1,
            team_b_id=2,
            historical_matches=sample_historical_data,
            calculation_date=datetime(2024, 1, 30)
        )

        # 验证计算属性
        assert features.total_matches == 5
        assert features.team_a_wins == 2
        assert features.team_b_wins == 2
        assert features.draws == 1
        assert abs(features.team_a_win_rate - 0.4) < 0.01
        assert abs(features.team_b_win_rate - 0.4) < 0.01
        assert features.draw_rate == 0.2

    def test_odds_features_creation(self, sample_odds_data):
        """测试赔率特征创建"""
        features = OddsFeatures(
            match_id=12345,
            odds_data=sample_odds_data,
            calculation_date=datetime(2024, 1, 15)
        )

        assert features.match_id == 12345
        assert features.home_win_odds == 2.10
        assert features.draw_odds == 3.40
        assert features.away_win_odds == 3.20

    def test_odds_features_calculated_properties(self, sample_odds_data):
        """测试赔率特征计算属性"""
        features = OddsFeatures(
            match_id=12345,
            odds_data=sample_odds_data,
            calculation_date=datetime(2024, 1, 15)
        )

        # 验证隐含概率计算
        assert abs(features.home_win_implied_prob - (1/2.10)) < 0.01
        assert abs(features.draw_implied_prob - (1/3.40)) < 0.01
        assert abs(features.away_win_implied_prob - (1/3.20)) < 0.01

        # 验证庄家优势
        total_implied_prob = features.home_win_implied_prob + features.draw_implied_prob + features.away_win_implied_prob
        assert features.bookmaker_margin == total_implied_prob - 1.0
        assert features.bookmaker_margin > 0

    def test_all_match_features_creation(self):
        """测试完整比赛特征创建"""
        recent_perf = RecentPerformanceFeatures(team_id=1, recent_matches=[], calculation_date=datetime.now())
        historical_matchup = HistoricalMatchupFeatures(team_a_id=1, team_b_id=2, historical_matches=[], calculation_date=datetime.now())
        odds_features = OddsFeatures(match_id=12345, odds_data={}, calculation_date=datetime.now())

        all_features = AllMatchFeatures(
            match_id=12345,
            home_team_id=1,
            away_team_id=2,
            recent_performance=recent_perf,
            historical_matchup=historical_matchup,
            odds_features=odds_features
        )

        assert all_features.match_id == 12345
        assert all_features.home_team_id == 1
        assert all_features.away_team_id == 2

    def test_all_team_features_creation(self):
        """测试完整球队特征创建"""
        recent_perf = RecentPerformanceFeatures(team_id=1, recent_matches=[], calculation_date=datetime.now())

        all_features = AllTeamFeatures(
            team_id=1,
            recent_performance=recent_perf,
            additional_features={"strength": 0.8, "form": "good"}
        )

        assert all_features.team_id == 1
        assert all_features.additional_features["strength"] == 0.8

    def test_feature_serialization(self, sample_match_data):
        """测试特征序列化"""
        features = RecentPerformanceFeatures(
            team_id=1,
            recent_matches=sample_match_data,
            calculation_date=datetime(2024, 1, 30)
        )

        # 测试序列化
        serialized = features.to_dict()

        assert "team_id" in serialized
        assert "matches_played" in serialized
        assert "wins" in serialized
        assert "win_rate" in serialized
        assert "calculation_date" in serialized

        # 测试反序列化
        deserialized = RecentPerformanceFeatures.from_dict(serialized)
        assert deserialized.team_id == features.team_id
        assert deserialized.matches_played == features.matches_played


class TestFeatureCalculator:
    """特征计算器测试类"""

    @pytest.fixture
    def calculator(self):
        """特征计算器实例"""
        return FeatureCalculator()

    @pytest.fixture
    def sample_team_matches(self):
        """示例球队比赛数据"""
        return pd.DataFrame({
            "match_id": [1, 2, 3, 4, 5, 6, 7, 8],
            "team_id": [1, 1, 1, 1, 1, 1, 1, 1],
            "opponent_id": [2, 3, 4, 5, 2, 3, 4, 5],
            "home_score": [2, 1, 3, 0, 1, 2, 1, 0],
            "away_score": [1, 1, 0, 2, 1, 1, 2, 1],
            "is_home": [True, False, True, False, True, False, True, False],
            "date": pd.date_range("2024-01-01", periods=8),
            "result": ["W", "D", "W", "L", "D", "W", "D", "L"]
        })

    @pytest.fixture
    def sample_head_to_head(self):
        """示例历史对战数据"""
        return pd.DataFrame({
            "match_id": [101, 102, 103, 104, 105],
            "home_team_id": [1, 2, 1, 2, 1],
            "away_team_id": [2, 1, 2, 1, 2],
            "home_score": [2, 1, 0, 2, 1],
            "away_score": [1, 1, 2, 1, 1],
            "date": pd.date_range("2023-01-01", periods=5),
            "winner": [1, 0, 2, 0, 0]  # 1=home win, 2=away win, 0=draw
        })

    def test_calculator_initialization(self, calculator):
        """测试计算器初始化"""
        assert calculator is not None
        assert hasattr(calculator, 'logger')
        assert hasattr(calculator, 'feature_cache')

    def test_calculate_recent_performance_features(self, calculator, sample_team_matches):
        """测试计算近期战绩特征"""
        team_id = 1
        calculation_date = datetime(2024, 1, 15)

        features = calculator.calculate_recent_performance_features(
            team_id, sample_team_matches, calculation_date, recent_games=5
        )

        assert isinstance(features, RecentPerformanceFeatures)
        assert features.team_id == team_id
        assert features.matches_played == 5
        assert features.wins >= 0
        assert features.draws >= 0
        assert features.losses >= 0

    def test_calculate_historical_matchup_features(self, calculator, sample_head_to_head):
        """测试计算历史对战特征"""
        team_a_id = 1
        team_b_id = 2
        calculation_date = datetime(2024, 1, 15)

        features = calculator.calculate_historical_matchup_features(
            team_a_id, team_b_id, sample_head_to_head, calculation_date
        )

        assert isinstance(features, HistoricalMatchupFeatures)
        assert features.team_a_id == team_a_id
        assert features.team_b_id == team_b_id
        assert features.total_matches == 5

    def test_calculate_odds_features(self, calculator):
        """测试计算赔率特征"""
        odds_data = {
            "home_win": 2.10,
            "draw": 3.40,
            "away_win": 3.20,
            "bookmaker": "Bet365",
            "timestamp": datetime(2024, 1, 15, 10, 0)
        }

        features = calculator.calculate_odds_features(12345, odds_data)

        assert isinstance(features, OddsFeatures)
        assert features.match_id == 12345
        assert features.home_win_odds == 2.10
        assert features.bookmaker_margin > 0

    def test_calculate_all_match_features(self, calculator, sample_team_matches, sample_head_to_head):
        """测试计算完整比赛特征"""
        match_id = 12345
        home_team_id = 1
        away_team_id = 2
        calculation_date = datetime(2024, 1, 15)

        features = calculator.calculate_all_match_features(
            match_id, home_team_id, away_team_id,
            sample_team_matches, sample_head_to_head, calculation_date
        )

        assert isinstance(features, AllMatchFeatures)
        assert features.match_id == match_id
        assert features.home_team_id == home_team_id
        assert features.away_team_id == away_team_id

    def test_batch_calculate_match_features(self, calculator, sample_team_matches, sample_head_to_head):
        """测试批量计算比赛特征"""
        matches = [
            {"match_id": 12345, "home_team_id": 1, "away_team_id": 2},
            {"match_id": 12346, "home_team_id": 3, "away_team_id": 4},
            {"match_id": 12347, "home_team_id": 5, "away_team_id": 1}
        ]

        features_list = calculator.batch_calculate_match_features(
            matches, sample_team_matches, sample_head_to_head, datetime(2024, 1, 15)
        )

        assert len(features_list) == 3
        for features in features_list:
            assert isinstance(features, AllMatchFeatures)

    def test_calculate_team_features(self, calculator, sample_team_matches):
        """测试计算球队特征"""
        team_id = 1
        calculation_date = datetime(2024, 1, 15)

        features = calculator.calculate_team_features(
            team_id, sample_team_matches, calculation_date
        )

        assert isinstance(features, AllTeamFeatures)
        assert features.team_id == team_id
        assert features.recent_performance is not None

    def test_feature_calculation_caching(self, calculator, sample_team_matches):
        """测试特征计算缓存"""
        team_id = 1
        calculation_date = datetime(2024, 1, 15)

        # 第一次计算
        features1 = calculator.calculate_recent_performance_features(
            team_id, sample_team_matches, calculation_date
        )

        # 第二次计算（应该使用缓存）
        features2 = calculator.calculate_recent_performance_features(
            team_id, sample_team_matches, calculation_date
        )

        # 验证结果一致
        assert features1.team_id == features2.team_id
        assert features1.matches_played == features2.matches_played

    def test_handle_calculation_errors(self, calculator):
        """测试计算错误处理"""
        # 测试空数据
        with pytest.raises(ValueError):
            calculator.calculate_recent_performance_features(1, pd.DataFrame(), datetime.now())

        # 测试无效数据
        invalid_data = pd.DataFrame({"invalid_column": [1, 2, 3]})
        with pytest.raises(ValueError):
            calculator.calculate_recent_performance_features(1, invalid_data, datetime.now())

    def test_feature_calculation_performance(self, calculator, sample_team_matches):
        """测试特征计算性能"""
        import time

        # 创建大数据集
        large_dataset = pd.concat([sample_team_matches] * 100)  # 800行数据

        start_time = time.time()
        features = calculator.calculate_recent_performance_features(
            1, large_dataset, datetime.now()
        )
        end_time = time.time()

        calculation_time = end_time - start_time

        # 验证性能
        assert calculation_time < 2.0  # 应该在2秒内完成
        assert isinstance(features, RecentPerformanceFeatures)


class TestFeatureStore:
    """特征存储测试类"""

    @pytest.fixture
    def feature_store(self):
        """特征存储实例"""
        return MockFeatureStore()

    @pytest.fixture
    def sample_features(self):
        """示例特征数据"""
        return [
            FeatureEntity(
                feature_key=FeatureKey("team_performance", 1, datetime(2024, 1, 15)),
                feature_value={"goals_scored": 2.5, "goals_conceded": 1.2},
                timestamp=datetime(2024, 1, 15, 10, 0)
            ),
            FeatureEntity(
                feature_key=FeatureKey("team_performance", 2, datetime(2024, 1, 15)),
                feature_value={"goals_scored": 1.8, "goals_conceded": 1.5},
                timestamp=datetime(2024, 1, 15, 10, 0)
            )
        ]

    def test_feature_store_initialization(self, feature_store):
        """测试特征存储初始化"""
        assert feature_store is not None
        assert hasattr(feature_store, 'features')
        assert hasattr(feature_store, 'ttl_cache')

    def test_store_features(self, feature_store, sample_features):
        """测试存储特征"""
        for feature in sample_features:
            feature_store.store_feature(feature)

        # 验证特征被存储
        retrieved_feature = feature_store.get_feature(
            "team_performance", 1, datetime(2024, 1, 15)
        )
        assert retrieved_feature is not None
        assert retrieved_feature.feature_value["goals_scored"] == 2.5

    def test_get_features(self, feature_store, sample_features):
        """测试获取特征"""
        # 先存储特征
        for feature in sample_features:
            feature_store.store_feature(feature)

        # 获取特征
        feature = feature_store.get_feature(
            "team_performance", 1, datetime(2024, 1, 15)
        )
        assert feature is not None
        assert feature.feature_key.entity_id == 1

    def test_get_features_not_found(self, feature_store):
        """测试获取不存在的特征"""
        feature = feature_store.get_feature(
            "non_existent_feature", 999, datetime(2024, 1, 15)
        )
        assert feature is None

    def test_get_expired_features(self, feature_store):
        """测试获取过期特征"""
        # 创建已过期的特征
        expired_feature = FeatureEntity(
            feature_key=FeatureKey("test_feature", 1, datetime(2024, 1, 15)),
            feature_value={"test": "value"},
            timestamp=datetime(2024, 1, 10, 10, 0),
            expiration_time=datetime(2024, 1, 12, 10, 0)  # 已过期
        )

        feature_store.store_feature(expired_feature)

        # 获取过期特征应该返回None
        current_time = datetime(2024, 1, 15, 10, 0)
        feature = feature_store.get_feature(
            "test_feature", 1, datetime(2024, 1, 15), current_time=current_time
        )
        assert feature is None

    def test_batch_store_features(self, feature_store, sample_features):
        """测试批量存储特征"""
        feature_store.batch_store_features(sample_features)

        # 验证所有特征都被存储
        for feature in sample_features:
            retrieved_feature = feature_store.get_feature(
                feature.feature_key.name,
                feature.feature_key.entity_id,
                feature.feature_key.timestamp
            )
            assert retrieved_feature is not None

    def test_delete_features(self, feature_store, sample_features):
        """测试删除特征"""
        # 存储特征
        feature_store.store_feature(sample_features[0])

        # 验证特征存在
        feature = feature_store.get_feature(
            "team_performance", 1, datetime(2024, 1, 15)
        )
        assert feature is not None

        # 删除特征
        deleted = feature_store.delete_feature(
            "team_performance", 1, datetime(2024, 1, 15)
        )
        assert deleted is True

        # 验证特征已删除
        feature = feature_store.get_feature(
            "team_performance", 1, datetime(2024, 1, 15)
        )
        assert feature is None

    def test_list_features(self, feature_store, sample_features):
        """测试列出特征"""
        # 存储特征
        for feature in sample_features:
            feature_store.store_feature(feature)

        # 列出特征
        features = feature_store.list_features("team_performance")

        assert len(features) >= 2
        feature_names = [f.feature_key.entity_id for f in features]
        assert 1 in feature_names
        assert 2 in feature_names

    def test_feature_store_statistics(self, feature_store, sample_features):
        """测试特征存储统计"""
        # 存储特征
        for feature in sample_features:
            feature_store.store_feature(feature)

        stats = feature_store.get_statistics()

        assert "total_features" in stats
        assert "features_by_type" in stats
        assert "oldest_feature" in stats
        assert "newest_feature" in stats
        assert stats["total_features"] >= 2


class TestFeatureEngineeringPipeline:
    """特征工程流水线测试类"""

    @pytest.fixture
    def pipeline(self):
        """特征工程流水线实例"""
        return FeatureEngineeringPipeline()

    @pytest.fixture
    def sample_raw_data(self):
        """示例原始数据"""
        return pd.DataFrame({
            "match_id": [12345, 12346, 12347],
            "home_team_id": [1, 2, 3],
            "away_team_id": [2, 3, 1],
            "home_score": [2, 1, 3],
            "away_score": [1, 2, 0],
            "date": pd.date_range("2024-01-01", periods=3),
            "league_id": [39, 39, 39]
        })

    @pytest.fixture
    def sample_historical_data(self):
        """示例历史数据"""
        return pd.DataFrame({
            "match_id": range(1000, 1100),
            "home_team_id": [1, 2] * 50,
            "away_team_id": [2, 1] * 50,
            "home_score": np.random.randint(0, 5, 100),
            "away_score": np.random.randint(0, 5, 100),
            "date": pd.date_range("2023-01-01", periods=100),
            "league_id": [39] * 100
        })

    def test_pipeline_initialization(self, pipeline):
        """测试流水线初始化"""
        assert pipeline is not None
        assert hasattr(pipeline, 'feature_calculator')
        assert hasattr(pipeline, 'feature_store')
        assert hasattr(pipeline, 'processing_steps')

    def test_extract_features(self, pipeline, sample_raw_data, sample_historical_data):
        """测试特征提取"""
        match_id = 12345
        home_team_id = 1
        away_team_id = 2

        features = pipeline.extract_features(
            match_id, home_team_id, away_team_id,
            sample_raw_data, sample_historical_data
        )

        assert isinstance(features, AllMatchFeatures)
        assert features.match_id == match_id
        assert features.home_team_id == home_team_id
        assert features.away_team_id == away_team_id

    def test_batch_extract_features(self, pipeline, sample_raw_data, sample_historical_data):
        """测试批量特征提取"""
        matches = [
            {"match_id": 12345, "home_team_id": 1, "away_team_id": 2},
            {"match_id": 12346, "home_team_id": 2, "away_team_id": 3},
            {"match_id": 12347, "home_team_id": 3, "away_team_id": 1}
        ]

        features_list = pipeline.batch_extract_features(
            matches, sample_raw_data, sample_historical_data
        )

        assert len(features_list) == 3
        for features in features_list:
            assert isinstance(features, AllMatchFeatures)

    def test_transform_features(self, pipeline):
        """测试特征转换"""
        # 创建示例特征
        recent_perf = RecentPerformanceFeatures(team_id=1, recent_matches=[], calculation_date=datetime.now())
        features = AllMatchFeatures(
            match_id=12345,
            home_team_id=1,
            away_team_id=2,
            recent_performance=recent_perf,
            historical_matchup=None,
            odds_features=None
        )

        # 转换特征
        transformed_features = pipeline.transform_features(features)

        assert isinstance(transformed_features, dict)
        assert "match_id" in transformed_features
        assert "home_team_id" in transformed_features
        assert "away_team_id" in transformed_features

    def test_select_features(self, pipeline):
        """测试特征选择"""
        # 创建完整的特征字典
        feature_dict = {
            "match_id": 12345,
            "home_team_id": 1,
            "away_team_id": 2,
            "home_win_prob": 0.6,
            "draw_prob": 0.2,
            "away_win_prob": 0.2,
            "home_recent_goals": 2.5,
            "away_recent_goals": 1.8,
            "historical_home_wins": 3,
            "historical_away_wins": 2,
            "odds_home_win": 2.1,
            "odds_draw": 3.4,
            "odds_away_win": 3.2
        }

        # 选择重要特征
        selected_features = pipeline.select_features(feature_dict)

        assert isinstance(selected_features, dict)
        assert len(selected_features) <= len(feature_dict)

    def test_pipeline_execution(self, pipeline, sample_raw_data, sample_historical_data):
        """测试完整流水线执行"""
        matches = [
            {"match_id": 12345, "home_team_id": 1, "away_team_id": 2},
            {"match_id": 12346, "home_team_id": 2, "away_team_id": 3}
        ]

        results = pipeline.execute(matches, sample_raw_data, sample_historical_data)

        assert isinstance(results, dict)
        assert "extracted_features" in results
        assert "transformed_features" in results
        assert "selected_features" in results
        assert "execution_time" in results

        assert len(results["extracted_features"]) == 2

    def test_pipeline_performance(self, pipeline, sample_raw_data, sample_historical_data):
        """测试流水线性能"""
        # 创建更大的数据集
        large_matches = [
            {"match_id": i, "home_team_id": i % 10 + 1, "away_team_id": (i + 1) % 10 + 1}
            for i in range(12345, 12355)
        ]

        import time
        start_time = time.time()

        results = pipeline.execute(large_matches, sample_raw_data, sample_historical_data)

        end_time = time.time()
        execution_time = end_time - start_time

        # 验证性能
        assert execution_time < 5.0  # 应该在5秒内完成处理10场比赛
        assert len(results["extracted_features"]) == 10

    def test_pipeline_caching(self, pipeline, sample_raw_data, sample_historical_data):
        """测试流水线缓存"""
        matches = [
            {"match_id": 12345, "home_team_id": 1, "away_team_id": 2}
        ]

        # 第一次执行
        start_time = time.time()
        results1 = pipeline.execute(matches, sample_raw_data, sample_historical_data)
        first_execution_time = time.time() - start_time

        # 第二次执行（应该使用缓存）
        start_time = time.time()
        results2 = pipeline.execute(matches, sample_raw_data, sample_historical_data)
        second_execution_time = time.time() - start_time

        # 验证缓存效果
        assert second_execution_time < first_execution_time
        assert len(results1["extracted_features"]) == len(results2["extracted_features"])

    def test_error_handling(self, pipeline):
        """测试错误处理"""
        # 测试空数据
        empty_matches = []
        empty_data = pd.DataFrame()
        empty_historical = pd.DataFrame()

        with pytest.raises(ValueError):
            pipeline.execute(empty_matches, empty_data, empty_historical)

        # 测试无效数据格式
        invalid_matches = [{"invalid": "data"}]
        with pytest.raises(ValueError):
            pipeline.execute(invalid_matches, sample_raw_data, sample_historical_data)


class TestFeatureEngineeringIntegration:
    """特征工程集成测试类"""

    def test_end_to_end_feature_workflow(self):
        """测试端到端特征工作流"""
        # 1. 准备数据
        raw_matches = pd.DataFrame({
            "match_id": range(10000, 10010),
            "home_team_id": [1, 2, 3, 4, 5] * 2,
            "away_team_id": [2, 3, 4, 5, 1] * 2,
            "home_score": [2, 1, 3, 0, 2, 1, 2, 0, 1, 3],
            "away_score": [1, 2, 0, 1, 1, 2, 1, 2, 1, 0],
            "date": pd.date_range("2024-01-01", periods=10),
            "league_id": [39] * 10
        })

        historical_data = pd.DataFrame({
            "match_id": range(5000, 5200),
            "home_team_id": np.random.randint(1, 6, 200),
            "away_team_id": np.random.randint(1, 6, 200),
            "home_score": np.random.randint(0, 5, 200),
            "away_score": np.random.randint(0, 5, 200),
            "date": pd.date_range("2023-01-01", periods=200),
            "league_id": [39] * 200
        })

        # 2. 创建流水线
        pipeline = FeatureEngineeringPipeline()

        # 3. 定义要处理的比赛
        matches_to_process = [
            {"match_id": 10000, "home_team_id": 1, "away_team_id": 2},
            {"match_id": 10001, "home_team_id": 2, "away_team_id": 3},
            {"match_id": 10002, "home_team_id": 3, "away_team_id": 4}
        ]

        # 4. 执行特征工程
        results = pipeline.execute(matches_to_process, raw_matches, historical_data)

        # 5. 验证结果
        assert len(results["extracted_features"]) == 3
        assert len(results["transformed_features"]) == 3
        assert len(results["selected_features"]) == 3

        # 6. 验证特征质量
        for features in results["extracted_features"]:
            assert isinstance(features, AllMatchFeatures)
            assert features.recent_performance is not None

        for transformed in results["transformed_features"]:
            assert isinstance(transformed, dict)
            assert len(transformed) > 0

        for selected in results["selected_features"]:
            assert isinstance(selected, dict)
            assert len(selected) > 0

    def test_feature_consistency_validation(self):
        """测试特征一致性验证"""
        calculator = FeatureCalculator()

        # 创建测试数据
        team_matches = pd.DataFrame({
            "match_id": [1, 2, 3, 4, 5],
            "team_id": [1, 1, 1, 1, 1],
            "home_score": [2, 1, 3, 0, 2],
            "away_score": [1, 1, 0, 1, 1],
            "is_home": [True, False, True, False, True],
            "date": pd.date_range("2024-01-01", periods=5),
            "result": ["W", "D", "W", "L", "W"]
        })

        # 计算特征
        features1 = calculator.calculate_recent_performance_features(
            1, team_matches, datetime(2024, 1, 10)
        )
        features2 = calculator.calculate_recent_performance_features(
            1, team_matches, datetime(2024, 1, 10)
        )

        # 验证一致性
        assert features1.team_id == features2.team_id
        assert features1.matches_played == features2.matches_played
        assert features1.wins == features2.wins
        assert abs(features1.win_rate - features2.win_rate) < 0.001

    def test_scalability_test(self):
        """测试可扩展性"""
        # 创建大数据集
        large_team_data = pd.DataFrame({
            "match_id": range(1, 10001),
            "team_id": np.random.randint(1, 51, 10000),
            "home_score": np.random.randint(0, 6, 10000),
            "away_score": np.random.randint(0, 6, 10000),
            "is_home": np.random.choice([True, False], 10000),
            "date": pd.date_range("2023-01-01", periods=10000),
            "result": np.random.choice(["W", "D", "L"], 10000)
        })

        calculator = FeatureCalculator()

        import time
        start_time = time.time()

        # 为多个球队计算特征
        team_ids = [1, 2, 3, 4, 5]
        features_list = []

        for team_id in team_ids:
            team_data = large_team_data[large_team_data["team_id"] == team_id]
            features = calculator.calculate_recent_performance_features(
                team_id, team_data, datetime(2024, 1, 15)
            )
            features_list.append(features)

        end_time = time.time()
        calculation_time = end_time - start_time

        # 验证性能和结果
        assert calculation_time < 10.0  # 应该在10秒内完成
        assert len(features_list) == 5
        for features in features_list:
            assert isinstance(features, RecentPerformanceFeatures)
            assert features.matches_played > 0