"""
FeatureStore 单元测试.

测试 FeatureStore 的核心功能，包括保存、加载、批量操作等。
使用 mock 数据库连接，确保测试的独立性和速度。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_mock import MockerFixture

from src.features.feature_store import FootballFeatureStore
from src.features.feature_store_interface import (
    FeatureData,
    FeatureNotFoundError,
    FeatureValidationError,
    StorageError,
)


class TestFootballFeatureStore:
    """FootballFeatureStore 单元测试类。"""

    @pytest.fixture
    def feature_store(self) -> FootballFeatureStore:
        """创建 FeatureStore 实例用于测试。"""
        return FootballFeatureStore(
            max_batch_size=10,
            retry_attempts=1,
            enable_logging=False
        )

    @pytest.fixture
    def mock_session(self):
        """创建 mock 数据库会话。"""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.fetchone = MagicMock()
        session.fetchall = MagicMock()
        return session

    @pytest.fixture
    def sample_features(self) -> dict:
        """示例特征数据。"""
        return {
            "home_recent_5_wins": 3,
            "home_recent_5_win_rate": 0.6,
            "away_recent_5_wins": 2,
            "away_recent_5_win_rate": 0.4,
            "h2h_total_matches": 10,
            "h2h_home_win_rate": 0.7,
            "home_xg": 1.5,
            "away_xg": 1.2,
            "home_win_odds": 2.1,
            "home_implied_probability": 0.476
        }

    @pytest.mark.asyncio
    async def test_initialize_success(self, feature_store: FootballFeatureStore, mock_session):
        """测试成功初始化。"""
        with patch('src.features.feature_store.get_db_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            await feature_store.initialize()

            assert feature_store._initialized is True
            mock_session.execute.assert_called()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, feature_store: FootballFeatureStore):
        """测试重复初始化。"""
        feature_store._initialized = True

        with patch('src.features.feature_store.get_db_session') as mock_get_session:
            await feature_store.initialize()

            # 不应该再次调用数据库操作
            mock_get_session.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_features_success(
        self,
        feature_store: FootballFeatureStore,
        mock_session,
        sample_features: dict
    ):
        """测试成功保存特征。"""
        feature_store._initialized = True

        with patch('src.features.feature_store.get_db_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            await feature_store.save_features(12345, sample_features)

            # 验证 SQL 查询
            mock_session.execute.assert_called_once()
            call_args = mock_session.execute.call_args[0][0]
            assert "INSERT INTO feature_store" in call_args
            assert "ON CONFLICT" in call_args

            # 验证参数
            call_args_list = mock_session.execute.call_args[0][1]
            assert call_args_list[0] == 12345  # match_id
            assert json.loads(call_args_list[2]) == sample_features  # features

            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_features_invalid_match_id(
        self,
        feature_store: FootballFeatureStore,
        sample_features: dict
    ):
        """测试无效的 match_id。"""
        feature_store._initialized = True

        with pytest.raises(FeatureValidationError, match="Invalid match_id"):
            await feature_store.save_features(-1, sample_features)

    @pytest.mark.asyncio
    async def test_save_features_empty_features(
        self,
        feature_store: FootballFeatureStore
    ):
        """测试空的特征字典。"""
        feature_store._initialized = True

        with pytest.raises(FeatureValidationError, match="cannot be empty"):
            await feature_store.save_features(12345, {})

    @pytest.mark.asyncio
    async def test_save_features_invalid_feature_names(
        self,
        feature_store: FootballFeatureStore
    ):
        """测试无效的特征名。"""
        feature_store._initialized = True

        invalid_features = {"": 1.0, "valid_feature": 2.0}

        with pytest.raises(FeatureValidationError, match="Invalid feature name"):
            await feature_store.save_features(12345, invalid_features)

    @pytest.mark.asyncio
    async def test_load_features_success(
        self,
        feature_store: FootballFeatureStore,
        mock_session,
        sample_features: dict
    ):
        """测试成功加载特征。"""
        feature_store._initialized = True

        # 模拟数据库返回结果
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: {
            0: 12345,  # match_id
            1: json.dumps(sample_features),  # features
            2: "latest",  # version
            3: None,  # metadata
            4: datetime.now(timezone.utc),  # created_at
            5: datetime.now(timezone.utc),  # updated_at
        }[key]

        mock_session.fetchone.return_value = mock_row

        with patch('src.features.feature_store.get_db_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await feature_store.load_features(12345)

            assert result is not None
            assert result["match_id"] == 12345
            assert result["features"] == sample_features
            assert result["version"] == "latest"

    @pytest.mark.asyncio
    async def test_load_features_not_found(
        self,
        feature_store: FootballFeatureStore,
        mock_session
    ):
        """测试加载不存在的特征。"""
        feature_store._initialized = True
        mock_session.fetchone.return_value = None

        with patch('src.features.feature_store.get_db_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await feature_store.load_features(99999)

            assert result is None

    @pytest.mark.asyncio
    async def test_load_batch_success(
        self,
        feature_store: FootballFeatureStore,
        mock_session,
        sample_features: dict
    ):
        """测试批量加载成功。"""
        feature_store._initialized = True
        match_ids = [12345, 12346, 12347]

        # 模拟数据库返回结果
        mock_rows = []
        for i, match_id in enumerate(match_ids):
            mock_row = MagicMock()
            mock_row.__getitem__ = lambda self, key, match_id=match_id, i=i: {
                0: match_id,  # match_id
                1: json.dumps({**sample_features, "match_specific": i}),  # features
                2: "latest",  # version
                3: None,  # metadata
                4: datetime.now(timezone.utc),  # created_at
                5: datetime.now(timezone.utc),  # updated_at
            }[key]
            mock_rows.append(mock_row)

        mock_session.fetchall.return_value = mock_rows

        with patch('src.features.feature_store.get_db_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await feature_store.load_batch(match_ids)

            assert len(result) == 3
            assert 12345 in result
            assert 12346 in result
            assert 12347 in result

            # 验证特征数据
            for i, match_id in enumerate(match_ids):
                assert result[match_id]["match_id"] == match_id
                assert result[match_id]["features"]["match_specific"] == i

    @pytest.mark.asyncio
    async def test_load_batch_empty_list(self, feature_store: FootballFeatureStore):
        """测试批量加载空列表。"""
        feature_store._initialized = True

        result = await feature_store.load_batch([])

        assert result == {}

    @pytest.mark.asyncio
    async def test_load_batch_exceeds_max_size(
        self,
        feature_store: FootballFeatureStore
    ):
        """测试批量加载超过最大大小。"""
        feature_store._initialized = True
        large_list = list(range(100))  # 超过默认的 max_batch_size=10

        with pytest.raises(FeatureValidationError, match="exceeds maximum"):
            await feature_store.load_batch(large_list)

    @pytest.mark.asyncio
    async def test_query_features_with_names(
        self,
        feature_store: FootballFeatureStore,
        mock_session,
        sample_features: dict
    ):
        """测试查询特定特征名。"""
        feature_store._initialized = True
        match_ids = [12345, 12346]
        feature_names = ["home_recent_5_wins", "away_recent_5_wins"]

        # 模拟数据库返回结果
        mock_rows = []
        for match_id in match_ids:
            mock_row = MagicMock()
            filtered_features = {k: v for k, v in sample_features.items() if k in feature_names}
            mock_row.__getitem__ = lambda self, key, match_id=match_id, features=filtered_features: {
                0: match_id,  # match_id
                1: json.dumps(features),  # features
                2: "latest",  # version
                3: datetime.now(timezone.utc),  # updated_at
            }[key]
            mock_rows.append(mock_row)

        mock_session.fetchall.return_value = mock_rows

        with patch('src.features.feature_store.get_db_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            results = await feature_store.query_features(match_ids, feature_names)

            assert len(results) == 2
            for result in results:
                assert len(result["features"]) == 2  # 只返回请求的特征
                assert "home_recent_5_wins" in result["features"]
                assert "away_recent_5_wins" in result["features"]
                assert "h2h_total_matches" not in result["features"]  # 未请求的特征

    @pytest.mark.asyncio
    async def test_delete_features_success(
        self,
        feature_store: FootballFeatureStore,
        mock_session
    ):
        """测试删除特征成功。"""
        feature_store._initialized = True

        with patch('src.features.feature_store.get_db_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await feature_store.delete_features(12345)

            assert result is True
            mock_session.execute.assert_called_once()
            mock_session.commit.assert_called_once()

            # 验证 SQL 查询
            call_args = mock_session.execute.call_args[0][0]
            assert "DELETE FROM feature_store" in call_args
            assert "WHERE match_id = %s" in call_args

    @pytest.mark.asyncio
    async def test_delete_features_with_version(
        self,
        feature_store: FootballFeatureStore,
        mock_session
    ):
        """测试删除特定版本的特征。"""
        feature_store._initialized = True

        with patch('src.features.feature_store.get_db_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await feature_store.delete_features(12345, "v1.0")

            assert result is True

            # 验证 SQL 查询包含版本条件
            call_args = mock_session.execute.call_args[0][0]
            assert "version = %s" in call_args

    @pytest.mark.asyncio
    async def test_latest_feature_timestamp(
        self,
        feature_store: FootballFeatureStore,
        mock_session
    ):
        """测试获取最新特征时间戳。"""
        feature_store._initialized = True

        test_timestamp = datetime.now(timezone.utc)
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key, timestamp=test_timestamp: {
            0: timestamp
        }[key]
        mock_session.fetchone.return_value = mock_row

        with patch('src.features.feature_store.get_db_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await feature_store.latest_feature_timestamp()

            assert result == test_timestamp

    @pytest.mark.asyncio
    async def test_latest_feature_timestamp_no_data(
        self,
        feature_store: FootballFeatureStore,
        mock_session
    ):
        """测试没有特征数据时的时间戳。"""
        feature_store._initialized = True
        mock_session.fetchone.return_value = None

        with patch('src.features.feature_store.get_db_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await feature_store.latest_feature_timestamp()

            assert result is None

    @pytest.mark.asyncio
    async def test_stats_success(
        self,
        feature_store: FootballFeatureStore,
        mock_session
    ):
        """测试获取统计信息成功。"""
        feature_store._initialized = True

        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: {
            0: 100,  # total_matches
            1: 500,  # total_features
            2: "latest,v1.0",  # feature_versions
            3: datetime.now(timezone.utc),  # latest_timestamp
            4: "10 MB"  # storage_size
        }[key]
        mock_session.fetchone.return_value = mock_row

        with patch('src.features.feature_store.get_db_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            result = await feature_store.stats()

            assert result["total_features"] == 500
            assert result["total_matches"] == 100
            assert "latest" in result["feature_versions"]
            assert "v1.0" in result["feature_versions"]
            assert result["latest_timestamp"] is not None
            assert result["storage_size_mb"] == 10.0

    @pytest.mark.asyncio
    async def test_list_feature_versions(
        self,
        feature_store: FootballFeatureStore,
        mock_session
    ):
        """测试列出特征版本。"""
        feature_store._initialized = True

        mock_rows = [
            MagicMock(__getitem__=lambda self, key: "latest" if key == 0 else None),
            MagicMock(__getitem__=lambda self, key: "v1.0" if key == 0 else None),
            MagicMock(__getitem__=lambda self, key: "v2.0" if key == 0 else None),
        ]
        mock_session.fetchall.return_value = mock_rows

        with patch('src.features.feature_store.get_db_session') as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            versions = await feature_store.list_feature_versions(12345)

            assert len(versions) == 3
            assert "latest" in versions
            assert "v1.0" in versions
            assert "v2.0" in versions

    @pytest.mark.asyncio
    async def test_health_check_healthy(
        self,
        feature_store: FootballFeatureStore,
        mock_session
    ):
        """测试健康检查 - 健康状态。"""
        feature_store._initialized = True

        # Mock stats 和 latest_timestamp 方法
        with patch.object(feature_store, 'stats', return_value={
            "total_features": 100,
            "total_matches": 50,
            "storage_size_mb": 5.0
        }), patch.object(feature_store, 'latest_feature_timestamp', return_value=datetime.now(timezone.utc)):

            result = await feature_store.health_check()

            assert result["status"] == "healthy"
            assert result["initialized"] is True
            assert result["total_features"] == 100
            assert result["total_matches"] == 50
            assert result["storage_size"] == 5.0
            assert "data_age_seconds" in result

    @pytest.mark.asyncio
    async def test_health_check_uninitialized(self, feature_store: FootballFeatureStore):
        """测试健康检查 - 未初始化状态。"""
        feature_store._initialized = False

        result = await feature_store.health_check()

        assert result["status"] == "uninitialized"
        assert result["initialized"] is False

    @pytest.mark.asyncio
    async def test_health_check_error(
        self,
        feature_store: FootballFeatureStore
    ):
        """测试健康检查 - 错误状态。"""
        feature_store._initialized = True

        with patch.object(feature_store, 'stats', side_effect=Exception("Database error")):
            result = await feature_store.health_check()

            assert result["status"] == "unhealthy"
            assert "error" in result

    def test_validate_match_id_valid(self, feature_store: FootballFeatureStore):
        """测试有效的 match_id 验证。"""
        # 不应该抛出异常
        feature_store._validate_match_id(12345)

    def test_validate_match_id_invalid_negative(self, feature_store: FootballFeatureStore):
        """测试无效的负数 match_id。"""
        with pytest.raises(FeatureValidationError, match="Invalid match_id"):
            feature_store._validate_match_id(-1)

    def test_validate_match_id_invalid_zero(self, feature_store: FootballFeatureStore):
        """测试无效的零值 match_id。"""
        with pytest.raises(FeatureValidationError, match="Invalid match_id"):
            feature_store._validate_match_id(0)

    def test_validate_features_valid(self, feature_store: FootballFeatureStore, sample_features: dict):
        """测试有效的特征验证。"""
        # 不应该抛出异常
        feature_store._validate_features(sample_features)

    def test_validate_features_invalid_type(self, feature_store: FootballFeatureStore):
        """测试无效的特征类型。"""
        with pytest.raises(FeatureValidationError, match="must be a dictionary"):
            feature_store._validate_features("not a dict")

    def test_validate_features_empty(self, feature_store: FootballFeatureStore):
        """测试空特征字典。"""
        with pytest.raises(FeatureValidationError, match="cannot be empty"):
            feature_store._validate_features({})

    def test_validate_features_invalid_key(self, feature_store: FootballFeatureStore):
        """测试无效的特征键。"""
        with pytest.raises(FeatureValidationError, match="Invalid feature name"):
            feature_store._validate_features({"": 1.0})

    def test_validate_version_valid(self, feature_store: FootballFeatureStore):
        """测试有效的版本验证。"""
        # 不应该抛出异常
        feature_store._validate_version("latest")
        feature_store._validate_version("v1.0")

    def test_validate_version_invalid_empty(self, feature_store: FootballFeatureStore):
        """测试无效的空版本。"""
        with pytest.raises(FeatureValidationError, match="Invalid version"):
            feature_store._validate_version("")

    def test_validate_version_invalid_whitespace(self, feature_store: FootballFeatureStore):
        """测试包含空白字符的版本。"""
        with pytest.raises(FeatureValidationError, match="Invalid version"):
            feature_store._validate_version("   ")

    def test_parse_storage_size_valid(self, feature_store: FootballFeatureStore):
        """测试解析有效的存储大小。"""
        assert feature_store._parse_storage_size("10 MB") == 10.0
        assert feature_store._parse_storage_size("1024 KB") == 1.0
        assert feature_store._parse_storage_size("1 GB") == 1024.0
        assert feature_store._parse_storage_size("500") == 500.0

    def test_parse_storage_size_invalid(self, feature_store: FootballFeatureStore):
        """测试解析无效的存储大小。"""
        assert feature_store._parse_storage_size(None) is None
        assert feature_store._parse_storage_size("") is None
        assert feature_store._parse_storage_size("invalid") is None

    def test_parse_storage_size_case_insensitive(self, feature_store: FootballFeatureStore):
        """测试大小写不敏感的存储大小解析。"""
        assert feature_store._parse_storage_size("10 mb") == 10.0
        assert feature_store._parse_storage_size("1 GB") == 1024.0
        assert feature_store._parse_storage_size("1024 kb") == 1.0
