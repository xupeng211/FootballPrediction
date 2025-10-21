"""
特征存储测试
Tests for Feature Store
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pandas as pd

from src.features.feature_store import (
    FeatureStore,
    Entity,
    FeatureView,
    Field,
    Float64,
    Int64,
    _MockFeastResult,
)


class TestFeatureStore:
    """特征存储测试"""

    @pytest.fixture
    def mock_store(self):
        """创建模拟特征存储实例"""
        return FeatureStore()

    @pytest.fixture
    def sample_entities(self):
        """创建示例实体"""
        return [
            Entity(name="team", join_keys=["team_id"]),
            Entity(name="match", join_keys=["match_id"]),
        ]

    @pytest.fixture
    def sample_features(self):
        """创建示例特征"""
        return [
            Field(name="team:avg_goals", dtype=Float64),
            Field(name="team:win_rate", dtype=Float64),
            Field(name="match:home_score", dtype=Int64),
            Field(name="match:away_score", dtype=Int64),
        ]

    @pytest.fixture
    def sample_feature_view(self, sample_entities, sample_features):
        """创建示例特征视图"""
        return FeatureView(
            name="team_match_features",
            entities=sample_entities,
            features=sample_features,
        )

    def test_feature_store_initialization(self, mock_store):
        """测试：特征存储初始化"""
        # Then
        assert mock_store is not None
        assert hasattr(mock_store, "applied_objects")
        assert mock_store.applied_objects == []

    def test_entity_creation(self):
        """测试：实体创建"""
        # When
        entity = Entity(name="team", join_keys=["team_id"])

        # Then
        assert entity.name == "team"

    def test_feature_view_creation(self, sample_entities, sample_features):
        """测试：特征视图创建"""
        # When
        feature_view = FeatureView(
            name="team_features",
            entities=sample_entities[:1],
            features=sample_features[:2],
        )

        # Then
        assert feature_view.name == "team_features"
        assert len(feature_view.entities) == 1
        assert len(feature_view.entities[0].name) > 0

    def test_field_creation(self):
        """测试：字段创建"""
        # When
        field = Field(name="team:avg_goals", dtype=Float64)

        # Then
        assert field.name == "team:avg_goals"
        assert field.dtype == Float64

    def test_apply_object(self, mock_store, sample_feature_view):
        """测试：应用对象到存储"""
        # When
        mock_store.apply(sample_feature_view)

        # Then
        assert len(mock_store.applied_objects) == 1
        assert mock_store.applied_objects[0] == sample_feature_view

    def test_apply_multiple_objects(self, mock_store, sample_entities, sample_features):
        """测试：应用多个对象到存储"""
        # Given
        feature_view1 = FeatureView(
            name="features1",
            entities=[sample_entities[0]],
            features=[sample_features[0]],
        )
        feature_view2 = FeatureView(
            name="features2",
            entities=[sample_entities[1]],
            features=[sample_features[1]],
        )

        # When
        mock_store.apply(feature_view1)
        mock_store.apply(feature_view2)

        # Then
        assert len(mock_store.applied_objects) == 2
        assert mock_store.applied_objects[0] == feature_view1
        assert mock_store.applied_objects[1] == feature_view2

    def test_get_online_features(self, mock_store):
        """测试：获取在线特征"""
        # Given
        features = ["team:avg_goals", "team:win_rate"]
        entity_rows = [{"team_id": 1}, {"team_id": 2}]

        # When
        _result = mock_store.get_online_features(features, entity_rows)

        # Then
        assert isinstance(result, _MockFeastResult)
        df = result.to_df()
        assert len(df) == 2
        assert "avg_goals" in df.columns
        assert "win_rate" in df.columns

    def test_get_online_features_with_existing_data(self, mock_store):
        """测试：获取在线特征 - 带有现有数据"""
        # Given
        features = ["match:home_score", "match:away_score"]
        entity_rows = [
            {"match_id": 100, "home_score": 2},  # 预设值
            {"match_id": 101},  # 无预设值
        ]

        # When
        _result = mock_store.get_online_features(features, entity_rows)

        # Then
        df = result.to_df()
        assert len(df) == 2
        # 第一行应该有预设值
        assert df.iloc[0]["home_score"] == 2
        # 第二行应该有默认值
        assert df.iloc[1]["home_score"] == 0.0

    def test_get_historical_features(self, mock_store):
        """测试：获取历史特征"""
        # Given
        entity_df = pd.DataFrame({"team_id": [1, 2, 3]})
        features = ["team:avg_goals", "team:win_rate"]

        # When
        _result = mock_store.get_historical_features(
            entity_df=entity_df, features=features, full_feature_names=False
        )

        # Then
        assert isinstance(result, _MockFeastResult)
        df = result.to_df()
        assert len(df) == 0  # Mock返回空结果

    def test_get_historical_features_with_full_names(self, mock_store):
        """测试：获取历史特征 - 使用完整特征名"""
        # Given
        entity_df = pd.DataFrame({"match_id": [100, 101]})
        features = ["match:home_score", "match:away_score"]

        # When
        _result = mock_store.get_historical_features(
            entity_df=entity_df, features=features, full_feature_names=True
        )

        # Then
        assert isinstance(result, _MockFeastResult)

    def test_push_features(self, mock_store):
        """测试：推送特征"""
        # Given
        test_data = pd.DataFrame(
            {
                "team_id": [1, 2],
                "avg_goals": [1.5, 2.0],
                "event_timestamp": [datetime.now(), datetime.now()],
            }
        )

        # When
        _result = mock_store.push(test_data)

        # Then
        assert _result is None

    def test_mock_feast_result(self):
        """测试：Mock Feast结果"""
        # Given
        rows = [{"team_id": 1, "avg_goals": 1.5}, {"team_id": 2, "avg_goals": 2.0}]

        # When
        _result = _MockFeastResult(rows)

        # Then
        df = result.to_df()
        assert len(df) == 2
        assert list(df.columns) == ["team_id", "avg_goals"]
        assert df.iloc[0]["team_id"] == 1
        assert df.iloc[1]["avg_goals"] == 2.0

    def test_mock_feast_result_empty(self):
        """测试：空的Mock Feast结果"""
        # Given
        _result = _MockFeastResult([])

        # When
        df = result.to_df()

        # Then
        assert len(df) == 0

    def test_feature_types(self):
        """测试：特征类型"""
        # Then
        assert Float64 is not None
        assert Int64 is not None

    def test_complex_feature_scenarios(self, mock_store):
        """测试：复杂特征场景"""
        # Given
        features = [
            "team:avg_goals",
            "team:win_rate",
            "team:recent_form",
            "match:home_score",
            "match:away_score",
            "match:match_importance",
        ]
        entity_rows = [
            {"team_id": 1, "match_id": 100, "home_team_id": 1, "away_team_id": 2},
            {"team_id": 2, "match_id": 100, "home_team_id": 1, "away_team_id": 2},
        ]

        # When
        _result = mock_store.get_online_features(features, entity_rows)

        # Then
        df = result.to_df()
        assert len(df) == 2
        # 检查所有特征列都存在
        for feature in features:
            short_name = feature.split(":")[-1]
            assert short_name in df.columns

    def test_feature_store_with_config(self):
        """测试：使用配置创建特征存储"""
        # Given
        _config = {
            "offline_store": {"type": "postgres", "host": "localhost", "port": 5432},
            "online_store": {"type": "redis", "host": "localhost", "port": 6379},
        }

        # When
        store = FeatureStore(_config=config)

        # Then
        assert store is not None
        assert store.applied_objects == []
