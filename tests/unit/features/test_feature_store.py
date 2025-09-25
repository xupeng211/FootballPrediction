"""
足球特征存储测试
测试FootballFeatureStore类的所有功能
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.features.feature_store import FootballFeatureStore


@pytest.fixture
def mocked_feature_store(monkeypatch):
    """Provides a fully mocked FootballFeatureStore instance."""
    # Mock external dependencies
    mock_fs_instance = MagicMock()
    mock_db_manager_instance = MagicMock()
    mock_redis_manager_instance = MagicMock()
    mock_calculator_instance = MagicMock()

    # Patch the classes in the feature_store module
    monkeypatch.setattr(
        "src.features.feature_store.FeatureStore", lambda repo_path: mock_fs_instance
    )
    monkeypatch.setattr(
        "src.features.feature_store.DatabaseManager", lambda: mock_db_manager_instance
    )
    monkeypatch.setattr(
        "src.features.feature_store.RedisManager", lambda: mock_redis_manager_instance
    )
    monkeypatch.setattr(
        "src.features.feature_store.FeatureCalculator", lambda: mock_calculator_instance
    )

    # Mock the async session context manager
    mock_async_session = AsyncMock()
    mock_db_manager_instance.get_async_session.return_value.__aenter__.return_value = (
        mock_async_session
    )

    store = FootballFeatureStore(feature_store_path="/tmp/test_feature_store")

    # Attach mocks to the instance for easy access in tests
    store.mock_fs = mock_fs_instance
    store.mock_db = mock_async_session
    store.mock_redis = mock_redis_manager_instance
    store.mock_calculator = mock_calculator_instance

    return store


class TestFootballFeatureStore:
    """FootballFeatureStore测试类"""

    def test_init_creates_store(self, mocked_feature_store):
        """测试初始化创建存储"""
        assert mocked_feature_store is not None
        assert hasattr(mocked_feature_store, "feature_store_path")
        assert mocked_feature_store.feature_store_path == "/tmp/test_feature_store"

    def test_init_with_default_path(self):
        """测试使用默认路径初始化"""
        with patch.dict("os.environ", {}, clear=True):
            store = FootballFeatureStore()
            assert store.feature_store_path == "."

    def test_initialize_feast_store_success(self, mocked_feature_store):
        """测试成功初始化Feast存储"""
        assert mocked_feature_store.store is not None
        assert mocked_feature_store.store == mocked_feature_store.mock_fs

    @patch("src.features.feature_store.FeatureStore", side_effect=Exception("初始化失败"))
    def test_initialize_feast_store_failure(self, mock_feature_store_class):
        """测试初始化Feast存储失败"""
        store = FootballFeatureStore()
        assert store.store is None

    def test_get_entity_definitions(self, mocked_feature_store):
        """测试获取实体定义"""
        # This test is tricky because feast is an optional dependency.
        # We'll just ensure it returns a dict without errors in the mocked environment.
        try:
            entities = mocked_feature_store.get_entity_definitions()
            assert isinstance(entities, dict)
            # Basic check if feast was mocked correctly
            if hasattr(entities.get("match"), "name"):
                assert "match" in entities
                assert "team" in entities
                assert entities["match"].name == "match"
                assert entities["team"].name == "team"
        except Exception as e:
            pytest.fail(f"get_entity_definitions failed with {e}")

    def test_get_feature_view_definitions(self, mocked_feature_store):
        """测试获取特征视图定义"""
        try:
            feature_views = mocked_feature_store.get_feature_view_definitions()
            assert isinstance(feature_views, dict)
        except Exception as e:
            # This can fail if feast is not installed, but in a mocked env it should pass.
            pytest.fail(f"get_feature_view_definitions failed with {e}")

    async def test_register_features_success(self, mocked_feature_store):
        """测试成功注册特征"""
        mock_entities = {"match": MagicMock(), "team": MagicMock()}
        mock_feature_views = {"team_recent_performance": MagicMock()}

        with patch.object(
            mocked_feature_store, "get_entity_definitions", return_value=mock_entities
        ):
            with patch.object(
                mocked_feature_store,
                "get_feature_view_definitions",
                return_value=mock_feature_views,
            ):
                result = await mocked_feature_store.register_features()
                assert result is True
                assert mocked_feature_store.mock_fs.apply.call_count >= 2

    async def test_register_features_failure(self, mocked_feature_store):
        """测试注册特征失败"""
        mocked_feature_store.store = None
        result = await mocked_feature_store.register_features()
        assert result is False

    async def test_get_online_features_success(self, mocked_feature_store):
        """测试成功获取在线特征"""
        mock_result = MagicMock()
        mock_result.to_df.return_value = pd.DataFrame({"feature": [1]})
        mocked_feature_store.mock_fs.get_online_features.return_value = mock_result
        result = await mocked_feature_store.get_online_features([], [])
        assert not result.empty

    async def test_get_online_features_failure(self, mocked_feature_store):
        """测试获取在线特征失败"""
        mocked_feature_store.mock_fs.get_online_features.side_effect = Exception(
            "error"
        )
        result = await mocked_feature_store.get_online_features([], [])
        assert result.empty

    async def test_get_historical_features_success(self, mocked_feature_store):
        """测试成功获取历史特征"""
        mock_result = MagicMock()
        mock_result.to_df.return_value = pd.DataFrame({"feature": [1]})
        mocked_feature_store.mock_fs.get_historical_features.return_value = mock_result
        result = await mocked_feature_store.get_historical_features(pd.DataFrame(), [])
        assert not result.empty

    async def test_get_historical_features_failure(self, mocked_feature_store):
        """测试获取历史特征失败"""
        mocked_feature_store.store = None
        with pytest.raises(ValueError, match="Feast 存储未初始化"):
            await mocked_feature_store.get_historical_features(pd.DataFrame(), [])

    async def test_push_features_to_online_store_success(self, mocked_feature_store):
        """测试成功推送特征到在线存储"""
        # Ensure the mock doesn't raise an unexpected error
        mocked_feature_store.mock_fs.push = MagicMock()
        result = await mocked_feature_store.push_features_to_online_store(
            "team_recent_performance", pd.DataFrame()
        )
        assert result is True
        mocked_feature_store.mock_fs.push.assert_called_once()

    async def test_push_features_to_online_store_failure(self, mocked_feature_store):
        """测试推送特征到在线存储失败"""
        mocked_feature_store.mock_fs.push.side_effect = Exception("error")
        result = await mocked_feature_store.push_features_to_online_store(
            "team_recent_performance", pd.DataFrame()
        )
        assert result is False

    async def test_calculate_and_store_team_features_success(
        self, mocked_feature_store
    ):
        """测试成功计算并存储球队特征"""
        mocked_feature_store.mock_calculator.calculate_recent_performance_features = (
            AsyncMock(
                return_value=MagicMock(
                    team_id=10,
                    recent_5_wins=3,
                    recent_5_draws=1,
                    recent_5_losses=1,
                    recent_5_goals_for=5,
                    recent_5_goals_against=2,
                    recent_5_points=10,
                    recent_5_home_wins=2,
                    recent_5_away_wins=1,
                    recent_5_home_goals_for=3,
                    recent_5_away_goals_for=2,
                )
            )
        )
        with patch.object(
            mocked_feature_store,
            "push_features_to_online_store",
            new=AsyncMock(return_value=True),
        ) as mock_push:
            result = await mocked_feature_store.calculate_and_store_team_features(10)
            assert result is True
            mock_push.assert_called_once()

    async def test_calculate_and_store_team_features_failure(
        self, mocked_feature_store
    ):
        """测试计算并存储球队特征失败"""
        mocked_feature_store.mock_calculator.calculate_recent_performance_features = (
            AsyncMock(side_effect=Exception("calc error"))
        )
        result = await mocked_feature_store.calculate_and_store_team_features(10)
        assert result is False

    async def test_get_match_features_for_prediction_success(
        self, mocked_feature_store
    ):
        """测试成功获取比赛预测特征"""
        mocked_feature_store.mock_redis.aget = AsyncMock(
            return_value=None
        )  # Cache miss
        mocked_feature_store.mock_redis.aset = AsyncMock()  # Mock aset to be awaitable

        # Mock the internal call to get_online_features
        with patch.object(
            mocked_feature_store,
            "get_online_features",
            new=AsyncMock(return_value=pd.DataFrame([{"feature": 1}])),
        ) as mock_get_online:
            result = await mocked_feature_store.get_match_features_for_prediction(
                1, 10, 20
            )
            assert result is not None
            assert "team_features" in result
            mocked_feature_store.mock_redis.aset.assert_called_once()
            assert mock_get_online.call_count == 3

    async def test_get_match_features_for_prediction_failure(
        self, mocked_feature_store
    ):
        """测试获取比赛预测特征失败"""
        mocked_feature_store.mock_redis.aget = AsyncMock(
            return_value=None
        )  # Cache miss
        with patch.object(
            mocked_feature_store,
            "get_online_features",
            new=AsyncMock(side_effect=Exception("error")),
        ):
            result = await mocked_feature_store.get_match_features_for_prediction(
                1, 10, 20
            )
            assert result is None

    async def test_batch_calculate_features_success(self, mocked_feature_store):
        """测试成功批量计算特征"""
        mock_match = MagicMock(
            id=1,
            home_team_id=10,
            away_team_id=20,
            match_time=datetime.now(),
            season="2023",
        )

        # Correctly mock the async database call chain
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_match]
        mocked_feature_store.mock_db.execute = AsyncMock(return_value=mock_result)

        mocked_feature_store.calculate_and_store_match_features = AsyncMock(
            return_value=True
        )
        mocked_feature_store.calculate_and_store_team_features = AsyncMock(
            return_value=True
        )

        stats = await mocked_feature_store.batch_calculate_features(
            datetime.now(), datetime.now()
        )

        assert stats["errors"] == 0
        assert stats["matches_processed"] == 1

    async def test_batch_calculate_features_failure(self, mocked_feature_store):
        """测试批量计算特征失败"""
        mocked_feature_store.mock_db.execute = AsyncMock(
            side_effect=Exception("db error")
        )
        stats = await mocked_feature_store.batch_calculate_features(
            datetime.now(), datetime.now()
        )
        assert stats["errors"] > 0


# 如果直接运行此文件，则执行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
