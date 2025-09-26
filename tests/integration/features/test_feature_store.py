"""
特征存储测试

测试 Feast 特征存储集成的功能：
- 特征视图定义
- 在线特征查询
- 离线特征查询
- 特征注册和管理
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from src.features.entities import MatchEntity
from src.features.feature_definitions import RecentPerformanceFeatures
from src.features.feature_store import FootballFeatureStore


def pytest_db_available():
    """检查数据库是否可用以及表结构是否存在"""
    try:
        import sqlalchemy as sa

        from src.database.connection import get_database_manager

        # 检查数据库连接
        db_manager = get_database_manager()

        # 检查关键表是否存在
        with db_manager.get_session() as session:
            result = session.execute(
                sa.text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'matches')"
                )
            )
            matches_exists = result.scalar()

            result = session.execute(
                sa.text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'teams')"
                )
            )
            teams_exists = result.scalar()

            return matches_exists and teams_exists

    except Exception:
        return False


# 跳过需要数据库的测试，如果数据库不可用
pytestmark = pytest.mark.skipif(
    not pytest_db_available(), reason="Database connection not available"
)


@pytest.fixture
def feature_store():
    """创建特征存储实例"""
    with patch("src.features.feature_store.FeatureStore"):
        store = FootballFeatureStore()
        store.store = Mock()  # 模拟 Feast 存储
        return store


@pytest.fixture
def sample_match_entity():
    """示例比赛实体"""
    return MatchEntity(
        match_id=1,
        home_team_id=1,
        away_team_id=2,
        league_id=1,
        match_time=datetime(2025, 9, 15, 15, 0),
        season="2024-25",
    )


class TestFootballFeatureStore:
    """特征存储测试类"""

    def test_entity_definitions(self, feature_store):
        """测试实体定义"""
        entities = feature_store.get_entity_definitions()

    assert "match" in entities
    assert "team" in entities

        match_entity = entities["match"]
    assert match_entity.name == "match"
        # 新版本Feast不再使用join_keys属性

        team_entity = entities["team"]
    assert team_entity.name == "team"
        # 新版本Feast不再使用join_keys属性

    def test_feature_view_definitions(self, feature_store):
        """测试特征视图定义"""
        feature_views = feature_store.get_feature_view_definitions()

    assert "team_recent_performance" in feature_views
    assert "historical_matchup" in feature_views
    assert "odds_features" in feature_views

        # 测试球队近期表现特征视图
        team_fv = feature_views["team_recent_performance"]
    assert team_fv.name == "team_recent_performance"
    assert team_fv.entities == ["team"]
    assert team_fv.ttl == timedelta(days=7)

        # 验证schema字段
        field_names = [field.name for field in team_fv.schema]
        expected_fields = [
            "recent_5_wins",
            "recent_5_draws",
            "recent_5_losses",
            "recent_5_goals_for",
            "recent_5_goals_against",
            "recent_5_points",
            "recent_5_home_wins",
            "recent_5_away_wins",
        ]
        for field in expected_fields:
    assert field in field_names

        # 测试历史对战特征视图
        h2h_fv = feature_views["historical_matchup"]
    assert h2h_fv.name == "historical_matchup"
    assert h2h_fv.entities == ["match"]
    assert h2h_fv.ttl == timedelta(days=30)

        # 测试赔率特征视图
        odds_fv = feature_views["odds_features"]
    assert odds_fv.name == "odds_features"
    assert odds_fv.entities == ["match"]
    assert odds_fv.ttl == timedelta(hours=6)

    @pytest.mark.asyncio
    async def test_register_features(self, feature_store):
        """测试特征注册"""
        # 模拟 Feast store apply 方法
        feature_store.store.apply = Mock()

        # 执行特征注册
        success = await feature_store.register_features()

        # 验证注册调用
    assert success is True
    assert feature_store.store.apply.call_count >= 5  # 2个实体 + 3个特征视图

    @pytest.mark.asyncio
    async def test_get_online_features(self, feature_store):
        """测试在线特征查询"""
        # 模拟 Feast 返回结果
        mock_result = Mock()
        mock_df = pd.DataFrame(
            {"team_id": [1, 2], "recent_5_wins": [3, 2], "recent_5_goals_for": [8, 6]}
        )
        mock_result.to_df.return_value = mock_df

        feature_store.store.get_online_features.return_value = mock_result

        # 执行在线特征查询
        feature_refs = ["team_recent_performance:recent_5_wins"]
        entity_rows = [{"team_id": 1}, {"team_id": 2}]

        result_df = await feature_store.get_online_features(feature_refs, entity_rows)

        # 验证结果
    assert len(result_df) == 2
    assert "team_id" in result_df.columns
    assert "recent_5_wins" in result_df.columns
    assert result_df.iloc[0]["team_id"] == 1
    assert result_df.iloc[0]["recent_5_wins"] == 3

        # 验证调用参数
        feature_store.store.get_online_features.assert_called_once_with(
            features=feature_refs, entity_rows=entity_rows
        )

    @pytest.mark.asyncio
    async def test_get_historical_features(self, feature_store):
        """测试历史特征查询"""
        # 准备实体数据框
        entity_df = pd.DataFrame(
            [
                {"match_id": 1, "team_id": 1, "event_timestamp": datetime(2025, 9, 15)},
                {"match_id": 2, "team_id": 2, "event_timestamp": datetime(2025, 9, 16)},
            ]
        )

        # 模拟 Feast 返回结果
        mock_training_df = pd.DataFrame(
            {
                "match_id": [1, 2],
                "team_id": [1, 2],
                "recent_5_wins": [3, 2],
                "recent_5_goals_for": [8, 6],
                "event_timestamp": [datetime(2025, 9, 15), datetime(2025, 9, 16)],
            }
        )

        mock_result = Mock()
        mock_result.to_df.return_value = mock_training_df
        feature_store.store.get_historical_features.return_value = mock_result

        # 执行历史特征查询
        feature_refs = ["team_recent_performance:recent_5_wins"]
        result_df = await feature_store.get_historical_features(
            entity_df, feature_refs, full_feature_names=True
        )

        # 验证结果
    assert len(result_df) == 2
    assert "match_id" in result_df.columns
    assert "recent_5_wins" in result_df.columns

        # 验证调用参数
        feature_store.store.get_historical_features.assert_called_once()
        call_args = feature_store.store.get_historical_features.call_args
    assert call_args[1]["full_feature_names"] is True

    @pytest.mark.asyncio
    async def test_push_features_to_online_store(self, feature_store):
        """测试推送特征到在线存储"""
        # 准备特征数据
        df = pd.DataFrame(
            {
                "team_id": [1, 2],
                "recent_5_wins": [3, 2],
                "recent_5_goals_for": [8, 6],
                "event_timestamp": [datetime.now(), datetime.now()],
            }
        )

        # 模拟 push 方法
        feature_store.store.push = Mock()

        # 执行推送
        success = await feature_store.push_features_to_online_store(
            "team_recent_performance", df
        )

        # 验证结果
    assert success is True
        feature_store.store.push.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_and_store_team_features(self, feature_store):
        """测试计算并存储球队特征"""
        # 模拟特征计算器
        mock_features = RecentPerformanceFeatures(
            team_id=1,
            calculation_date=datetime(2025, 9, 15),
            recent_5_wins=3,
            recent_5_goals_for=8,
        )

        with patch.object(
            feature_store.calculator, "calculate_recent_performance_features"
        ) as mock_calc:
            mock_calc.return_value = mock_features

            # 模拟推送成功
            feature_store.store.push = Mock()

            # 执行计算和存储
            success = await feature_store.calculate_and_store_team_features(
                team_id=1, calculation_date=datetime(2025, 9, 15)
            )

            # 验证结果
    assert success is True
            mock_calc.assert_called_once_with(1, datetime(2025, 9, 15))
            feature_store.store.push.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_and_store_match_features(
        self, feature_store, sample_match_entity
    ):
        """测试计算并存储比赛特征"""
        # 模拟历史对战特征
        from src.features.feature_definitions import (
            HistoricalMatchupFeatures,
            OddsFeatures,
        )

        mock_h2h_features = HistoricalMatchupFeatures(
            home_team_id=1,
            away_team_id=2,
            calculation_date=datetime(2025, 9, 15),
            h2h_total_matches=5,
        )

        mock_odds_features = OddsFeatures(
            match_id=1, calculation_date=datetime(2025, 9, 15), bookmaker_count=3
        )

        with patch.object(
            feature_store.calculator, "calculate_historical_matchup_features"
        ) as mock_h2h, patch.object(
            feature_store.calculator, "calculate_odds_features"
        ) as mock_odds:
            mock_h2h.return_value = mock_h2h_features
            mock_odds.return_value = mock_odds_features

            # 模拟推送成功
            feature_store.store.push = Mock()

            # 执行计算和存储
            success = await feature_store.calculate_and_store_match_features(
                sample_match_entity
            )

            # 验证结果
    assert success is True
            mock_h2h.assert_called_once()
            mock_odds.assert_called_once()
    assert feature_store.store.push.call_count == 2  # h2h + odds

    @pytest.mark.asyncio
    async def test_get_match_features_for_prediction(self, feature_store):
        """测试获取用于预测的比赛特征"""
        # 模拟不同类型的特征查询结果
        team_features_df = pd.DataFrame(
            {"team_id": [1, 2], "recent_5_wins": [3, 2], "recent_5_goals_for": [8, 6]}
        )

        h2h_features_df = pd.DataFrame(
            {"match_id": [1], "h2h_total_matches": [5], "h2h_home_wins": [2]}
        )

        odds_features_df = pd.DataFrame(
            {
                "match_id": [1],
                "home_implied_probability": [0.45],
                "bookmaker_consensus": [0.82],
            }
        )

        # 模拟多次在线特征查询
        def mock_get_online_features(features, entity_rows):
            result = Mock()
            if "team_recent_performance" in features[0]:
                result.to_df.return_value = team_features_df
            elif "historical_matchup" in features[0]:
                result.to_df.return_value = h2h_features_df
            elif "odds_features" in features[0]:
                result.to_df.return_value = odds_features_df
            else:
                result.to_df.return_value = pd.DataFrame()
            return result

        feature_store.store.get_online_features.side_effect = mock_get_online_features

        # 执行预测特征获取
        features = await feature_store.get_match_features_for_prediction(
            match_id=1, home_team_id=1, away_team_id=2
        )

        # 验证结果结构
    assert features is not None
    assert "team_features" in features
    assert "h2h_features" in features
    assert "odds_features" in features

    assert len(features["team_features"]) == 2  # 主队 + 客队
    assert features["h2h_features"]["h2h_total_matches"] == 5
    assert features["odds_features"]["home_implied_probability"] == 0.45

    @pytest.mark.asyncio
    async def test_batch_calculate_features(self, feature_store):
        """测试批量计算特征"""
        start_date = datetime(2025, 9, 10)
        end_date = datetime(2025, 9, 17)

        # 模拟数据库查询返回比赛列表
        mock_matches = [
            Mock(
                id=1,
                home_team_id=1,
                away_team_id=2,
                league_id=1,
                match_time=datetime(2025, 9, 15),
                season="2024-25",
            ),
            Mock(
                id=2,
                home_team_id=3,
                away_team_id=4,
                league_id=1,
                match_time=datetime(2025, 9, 16),
                season="2024-25",
            ),
        ]

        with patch.object(
            feature_store.db_manager, "get_async_session"
        ) as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.__aenter__.return_value = mock_session_instance

            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = mock_matches
            mock_session_instance.execute.return_value = mock_result

            # 模拟特征计算和存储成功
            with patch.object(
                feature_store, "calculate_and_store_match_features", return_value=True
            ) as mock_match_calc, patch.object(
                feature_store, "calculate_and_store_team_features", return_value=True
            ) as mock_team_calc:
                # 执行批量计算
                stats = await feature_store.batch_calculate_features(
                    start_date, end_date
                )

                # 验证结果
    assert stats["matches_processed"] == 2
    assert stats["teams_processed"] == 4  # 每场比赛2支球队
    assert stats["features_stored"] == 2
    assert stats["errors"] == 0

                # 验证调用次数
    assert mock_match_calc.call_count == 2
    assert mock_team_calc.call_count == 4

    @pytest.mark.asyncio
    async def test_error_handling(self, feature_store):
        """测试错误处理"""
        # 测试存储未初始化的情况
        feature_store.store = None

        with pytest.raises(ValueError, match="Feast 存储未初始化"):
            await feature_store.get_online_features([], [])

        with pytest.raises(ValueError, match="Feast 存储未初始化"):
            await feature_store.get_historical_features(pd.DataFrame(), [])

        # 测试推送特征时特征视图不存在
        feature_store.store = Mock()
        success = await feature_store.push_features_to_online_store(
            "non_existent_view", pd.DataFrame()
        )
    assert success is False

    @pytest.mark.asyncio
    async def test_feature_store_initialization(self):
        """测试特征存储初始化"""
        # 测试正常初始化
        with patch("src.features.feature_store.FeatureStore") as mock_feast_store:
            mock_feast_instance = Mock()
            mock_feast_store.return_value = mock_feast_instance

            store = FootballFeatureStore("test_path")
    assert store.feature_store_path == "test_path"
    assert store.store == mock_feast_instance
            mock_feast_store.assert_called_once_with(repo_path="test_path")

        # 测试初始化失败
        with patch(
            "src.features.feature_store.FeatureStore",
            side_effect=Exception("初始化失败"),
        ):
            store = FootballFeatureStore()
    assert store.store is None
