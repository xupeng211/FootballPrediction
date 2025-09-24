"""
Phase 6: feature_store.py 补测用例
目标：提升覆盖率从 66% 到 70%+
重点：异常路径、边界值、未覆盖分支
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pandas as pd
import pytest


# 测试在无 Feast 环境下的行为
@patch("src.features.feature_store.HAS_FEAST", False)
class TestFeatureStoreWithoutFeast:
    """测试在没有安装 Feast 时的降级行为"""

    def test_initialization_without_feast(self):
        """测试无 Feast 时的初始化"""
        from src.features.feature_store import FootballFeatureStore

        store = FootballFeatureStore()
        assert store.store is None
        assert not store._initialized

    def test_mock_classes_creation(self):
        """测试 Mock 类的创建和行为"""
        from src.features.feature_store import (
            Entity,
            FeatureStore,
            FeatureView,
            Field,
            Float64,
            Int64,
            PostgreSQLSource,
        )

        # 测试 Mock 类可以正常实例化（Entity需要name参数）
        entity = Entity(name="test_entity")
        feature_store = FeatureStore()
        feature_view = FeatureView()
        field = Field()

        # 测试 Mock 方法返回默认值
        assert feature_store.get_online_features() == {"features": {}}
        assert feature_store.get_historical_features() == {}


class TestFeatureStoreErrorPaths:
    """测试 FeatureStore 的异常路径和边界条件"""

    def setup_method(self):
        """设置测试环境"""
        from src.features.feature_store import FootballFeatureStore

        self.feature_store = FootballFeatureStore()

    @patch("src.features.feature_store.HAS_FEAST", True)
    def test_initialize_feast_store_with_exception(self):
        """测试 Feast 存储初始化异常"""
        with patch("src.features.feature_store.FeatureStore") as mock_fs:
            mock_fs.side_effect = Exception("Feast initialization failed")

            result = self.feature_store._initialize_feast_store()
            assert not result
            assert self.feature_store.store is None

    @pytest.mark.asyncio
    async def test_get_online_features_store_not_initialized(self):
        """测试获取在线特征时存储未初始化"""
        self.feature_store.store = None

        with pytest.raises(ValueError, match="Feast 存储未初始化"):
            await self.feature_store.get_online_features(
                feature_refs=["test_feature"], entity_rows=[{"team_id": 1}]
            )

    @pytest.mark.asyncio
    async def test_get_online_features_with_exception(self):
        """测试获取在线特征时的异常处理"""
        mock_store = Mock()
        mock_store.get_online_features.side_effect = Exception("Network error")
        self.feature_store.store = mock_store

        result = await self.feature_store.get_online_features(
            feature_refs=["test_feature"], entity_rows=[{"team_id": 1}]
        )

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    @pytest.mark.asyncio
    async def test_get_historical_features_store_not_initialized(self):
        """测试获取历史特征时存储未初始化"""
        self.feature_store.store = None
        entity_df = pd.DataFrame({"team_id": [1, 2]})

        with pytest.raises(ValueError, match="Feast 存储未初始化"):
            await self.feature_store.get_historical_features(
                entity_df=entity_df, feature_refs=["test_feature"]
            )

    @pytest.mark.asyncio
    async def test_get_historical_features_with_exception(self):
        """测试获取历史特征时的异常处理"""
        mock_store = Mock()
        mock_store.get_historical_features.side_effect = Exception("Data error")
        self.feature_store.store = mock_store

        entity_df = pd.DataFrame({"team_id": [1, 2]})
        result = await self.feature_store.get_historical_features(
            entity_df=entity_df, feature_refs=["test_feature"]
        )

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    @pytest.mark.asyncio
    async def test_push_features_to_online_store_not_initialized(self):
        """测试推送特征时存储未初始化"""
        self.feature_store.store = None
        features_df = pd.DataFrame({"team_id": [1], "feature": [0.5]})

        with pytest.raises(ValueError, match="Feast 存储未初始化"):
            await self.feature_store.push_features_to_online_store(
                feature_view_name="test_view", df=features_df
            )

    @pytest.mark.asyncio
    async def test_push_features_with_exception(self):
        """测试推送特征时的异常处理"""
        mock_store = Mock()
        mock_store.push.side_effect = Exception("Push failed")
        self.feature_store.store = mock_store

        features_df = pd.DataFrame({"team_id": [1], "feature": [0.5]})
        result = await self.feature_store.push_features_to_online_store(
            feature_view_name="test_view", df=features_df
        )

        assert not result

    @pytest.mark.asyncio
    async def test_calculate_and_store_team_features_database_error(self):
        """测试计算和存储团队特征时的数据库错误"""
        with patch.object(self.feature_store, "db_manager") as mock_db:
            mock_db.execute_query.side_effect = Exception("Database connection failed")

            result = await self.feature_store.calculate_and_store_team_features(
                team_id=1, match_date=datetime.now()
            )

            assert isinstance(result, pd.DataFrame)
            assert result.empty

    @pytest.mark.asyncio
    async def test_calculate_and_store_team_features_calculator_error(self):
        """测试特征计算器错误"""
        # Mock 数据库返回空结果
        with patch.object(self.feature_store, "db_manager") as mock_db:
            mock_db.execute_query.return_value = []

            with patch.object(self.feature_store, "calculator") as mock_calc:
                mock_calc.calculate_team_features.side_effect = Exception(
                    "Calculation failed"
                )

                result = await self.feature_store.calculate_and_store_team_features(
                    team_id=1, match_date=datetime.now()
                )

                assert isinstance(result, pd.DataFrame)
                assert result.empty

    @pytest.mark.asyncio
    async def test_get_match_features_for_prediction_database_error(self):
        """测试获取比赛预测特征时的数据库错误"""
        with patch.object(self.feature_store, "db_manager") as mock_db:
            mock_db.execute_query.side_effect = Exception("Database error")

            result = await self.feature_store.get_match_features_for_prediction(
                home_team_id=1, away_team_id=2, match_date=datetime.now()
            )

            assert isinstance(result, dict)
            assert result == {}

    @pytest.mark.asyncio
    async def test_batch_calculate_features_partial_failure(self):
        """测试批量计算特征时的部分失败"""
        team_ids = [1, 2, 3]
        match_date = datetime.now()

        # Mock 部分成功，部分失败
        with patch.object(
            self.feature_store, "calculate_and_store_team_features"
        ) as mock_calc:

            async def side_effect(team_id, date):
                if team_id == 2:
                    raise Exception(f"Failed for team {team_id}")
                return pd.DataFrame({"team_id": [team_id], "feature": [0.5]})

            mock_calc.side_effect = side_effect

            result = await self.feature_store.batch_calculate_features(
                team_ids=team_ids, match_date=match_date
            )

            # 应该只有成功的结果
            assert isinstance(result, pd.DataFrame)
            assert len(result) == 2  # team 1 和 3 成功

    def test_register_features_without_store(self):
        """测试注册特征时存储未初始化"""
        self.feature_store.store = None

        result = self.feature_store.register_features()
        assert not result

    def test_register_features_with_exception(self):
        """测试注册特征时的异常处理"""
        mock_store = Mock()
        mock_store.apply.side_effect = Exception("Registration failed")
        self.feature_store.store = mock_store

        result = self.feature_store.register_features()
        assert not result


class TestFeatureStoreBoundaryConditions:
    """测试边界条件和特殊情况"""

    def setup_method(self):
        from src.features.feature_store import FootballFeatureStore

        self.feature_store = FootballFeatureStore()

    @pytest.mark.asyncio
    async def test_empty_entity_rows(self):
        """测试空实体行"""
        mock_store = Mock()
        mock_result = Mock()
        mock_result.to_df.return_value = pd.DataFrame()
        mock_store.get_online_features.return_value = mock_result
        self.feature_store.store = mock_store

        result = await self.feature_store.get_online_features(
            feature_refs=["test_feature"], entity_rows=[]  # 空列表
        )

        assert isinstance(result, pd.DataFrame)

    @pytest.mark.asyncio
    async def test_empty_feature_refs(self):
        """测试空特征引用"""
        mock_store = Mock()
        mock_result = Mock()
        mock_result.to_df.return_value = pd.DataFrame()
        mock_store.get_online_features.return_value = mock_result
        self.feature_store.store = mock_store

        result = await self.feature_store.get_online_features(
            feature_refs=[], entity_rows=[{"team_id": 1}]  # 空列表
        )

        assert isinstance(result, pd.DataFrame)

    @pytest.mark.asyncio
    async def test_historical_features_with_full_feature_names(self):
        """测试使用完整特征名称"""
        mock_store = Mock()
        mock_result = Mock()
        mock_result.to_df.return_value = pd.DataFrame({"full_feature_name": [1.0]})
        mock_store.get_historical_features.return_value = mock_result
        self.feature_store.store = mock_store

        entity_df = pd.DataFrame({"team_id": [1], "event_timestamp": [datetime.now()]})
        result = await self.feature_store.get_historical_features(
            entity_df=entity_df,
            feature_refs=["test_feature"],
            full_feature_names=True,  # 测试这个参数
        )

        assert isinstance(result, pd.DataFrame)
        mock_store.get_historical_features.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_calculate_with_empty_team_list(self):
        """测试空团队列表的批量计算"""
        result = await self.feature_store.batch_calculate_features(
            team_ids=[], match_date=datetime.now()  # 空列表
        )

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    @pytest.mark.asyncio
    async def test_calculate_features_with_past_date(self):
        """测试使用过去日期计算特征"""
        past_date = datetime.now() - timedelta(days=365)

        with patch.object(self.feature_store, "db_manager") as mock_db:
            mock_db.execute_query.return_value = []

            result = await self.feature_store.calculate_and_store_team_features(
                team_id=1, match_date=past_date
            )

            assert isinstance(result, pd.DataFrame)


class TestFeatureStoreIntegration:
    """测试集成场景"""

    def setup_method(self):
        from src.features.feature_store import FootballFeatureStore

        self.feature_store = FootballFeatureStore()

    def test_cache_manager_integration(self):
        """测试缓存管理器集成"""
        assert hasattr(self.feature_store, "cache_manager")
        assert self.feature_store.cache_manager is not None

    def test_database_manager_integration(self):
        """测试数据库管理器集成"""
        assert hasattr(self.feature_store, "db_manager")
        assert self.feature_store.db_manager is not None

    def test_feature_calculator_integration(self):
        """测试特征计算器集成"""
        assert hasattr(self.feature_store, "calculator")
        assert self.feature_store.calculator is not None

    @pytest.mark.asyncio
    async def test_redis_cache_error_handling(self):
        """测试 Redis 缓存错误处理"""
        with patch.object(self.feature_store.cache_manager, "aget") as mock_cache:
            mock_cache.side_effect = Exception("Redis connection failed")

            # 应该继续执行而不是崩溃
            result = await self.feature_store.get_match_features_for_prediction(
                home_team_id=1, away_team_id=2, match_date=datetime.now()
            )

            assert isinstance(result, dict)
