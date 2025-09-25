"""
特征计算器测试

测试特征计算逻辑的正确性，包括：
- 近期战绩特征计算
- 历史对战特征计算
- 赔率特征计算
- 批量计算和并行计算
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.features.entities import MatchEntity, TeamEntity
from src.features.feature_calculator import FeatureCalculator
from src.features.feature_definitions import (
    AllMatchFeatures,
    HistoricalMatchupFeatures,
    OddsFeatures,
    RecentPerformanceFeatures,
)


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
def feature_calculator():
    """创建特征计算器实例"""
    return FeatureCalculator()


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


@pytest.fixture
def sample_team_entity():
    """示例球队实体"""
    return TeamEntity(team_id=1, team_name="测试球队", league_id=1, home_venue="测试球场")


class TestFeatureCalculator:
    """特征计算器测试类"""

    @pytest.mark.asyncio
    async def test_calculate_recent_performance_features(self, feature_calculator):
        """测试近期战绩特征计算"""
        # 模拟数据库查询结果
        mock_matches = [
            Mock(
                home_team_id=1,
                away_team_id=2,
                home_score=2,
                away_score=1,
                match_time=datetime(2025, 9, 10),
            ),
            Mock(
                home_team_id=3,
                away_team_id=1,
                home_score=0,
                away_score=2,
                match_time=datetime(2025, 9, 5),
            ),
            Mock(
                home_team_id=1,
                away_team_id=4,
                home_score=1,
                away_score=1,
                match_time=datetime(2025, 9, 1),
            ),
        ]

        # Mock数据库管理器的get_async_session方法
        mock_session = AsyncMock()

        # 创建正确的mock链
        mock_scalars = Mock()
        mock_scalars.all.return_value = mock_matches
        mock_result = Mock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch.object(
            feature_calculator.db_manager, "get_async_session"
        ) as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # 执行特征计算
            features = await feature_calculator.calculate_recent_performance_features(
                team_id=1, calculation_date=datetime(2025, 9, 15)
            )

            # 验证特征
            assert isinstance(features, RecentPerformanceFeatures)
            assert features.team_id == 1
            assert features.recent_5_wins == 2  # 主场胜利 + 客场胜利
            assert features.recent_5_draws == 1  # 平局
            assert features.recent_5_losses == 0
            assert features.recent_5_goals_for == 5  # 2 + 2 + 1
            assert features.recent_5_goals_against == 4  # 1 + 0 + 1
            assert features.recent_5_points == 7  # 3*2 + 1*1
            assert features.recent_5_win_rate == 2 / 3  # 2胜1平

    @pytest.mark.asyncio
    async def test_calculate_historical_matchup_features(self, feature_calculator):
        """测试历史对战特征计算"""
        # 模拟历史对战数据
        mock_h2h_matches = [
            Mock(
                home_team_id=1,
                away_team_id=2,
                home_score=2,
                away_score=1,
                match_time=datetime(2025, 8, 15),
            ),
            Mock(
                home_team_id=2,
                away_team_id=1,
                home_score=1,
                away_score=3,
                match_time=datetime(2025, 7, 10),
            ),
            Mock(
                home_team_id=1,
                away_team_id=2,
                home_score=0,
                away_score=0,
                match_time=datetime(2025, 6, 5),
            ),
            Mock(
                home_team_id=2,
                away_team_id=1,
                home_score=2,
                away_score=2,
                match_time=datetime(2025, 5, 1),
            ),
            Mock(
                home_team_id=1,
                away_team_id=2,
                home_score=1,
                away_score=2,
                match_time=datetime(2025, 4, 15),
            ),
        ]

        # Mock数据库管理器的get_async_session方法
        mock_session = AsyncMock()

        # 创建正确的mock链
        mock_scalars = Mock()
        mock_scalars.all.return_value = mock_h2h_matches
        mock_result = Mock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch.object(
            feature_calculator.db_manager, "get_async_session"
        ) as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # 执行历史对战特征计算
            features = await feature_calculator.calculate_historical_matchup_features(
                home_team_id=1, away_team_id=2, calculation_date=datetime(2025, 9, 15)
            )

            # 验证特征
            assert isinstance(features, HistoricalMatchupFeatures)
            assert features.home_team_id == 1
            assert features.away_team_id == 2
            assert features.h2h_total_matches == 5
            assert features.h2h_home_wins == 2  # 球队1作为主队赢2次
            assert features.h2h_away_wins == 1  # 球队1作为客队赢1次
            assert features.h2h_draws == 2  # 2次平局
            assert features.h2h_home_goals_total == 6  # 2+3+0+2+1
            assert features.h2h_away_goals_total == 6  # 1+1+0+2+2
            assert features.h2h_goals_avg == 2.4  # 12/5
            assert features.h2h_home_win_rate == 0.4  # 2/5

    @pytest.mark.asyncio
    async def test_calculate_odds_features(self, feature_calculator):
        """测试赔率特征计算"""
        # 模拟赔率数据
        mock_odds = [
            Mock(
                bookmaker="Bet365",
                home_odds=Decimal("2.10"),
                draw_odds=Decimal("3.20"),
                away_odds=Decimal("3.50"),
            ),
            Mock(
                bookmaker="William Hill",
                home_odds=Decimal("2.05"),
                draw_odds=Decimal("3.30"),
                away_odds=Decimal("3.60"),
            ),
            Mock(
                bookmaker="Pinnacle",
                home_odds=Decimal("2.15"),
                draw_odds=Decimal("3.15"),
                away_odds=Decimal("3.45"),
            ),
        ]

        # Mock数据库管理器的get_async_session方法
        mock_session = AsyncMock()

        # 创建正确的mock链
        mock_scalars = Mock()
        mock_scalars.all.return_value = mock_odds
        mock_result = Mock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch.object(
            feature_calculator.db_manager, "get_async_session"
        ) as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session

            # 执行赔率特征计算
            features = await feature_calculator.calculate_odds_features(
                match_id=1, calculation_date=datetime(2025, 9, 15)
            )

            # 验证特征
            assert isinstance(features, OddsFeatures)
            assert features.match_id == 1
            assert features.bookmaker_count == 3

            # 验证平均赔率（约等于）
            assert abs(float(features.home_odds_avg) - 2.10) < 0.01
            assert abs(float(features.draw_odds_avg) - 3.22) < 0.01
            assert abs(float(features.away_odds_avg) - 3.52) < 0.01

            # 验证隐含概率
            assert abs(features.home_implied_probability - 1 / 2.10) < 0.01
            assert abs(features.draw_implied_probability - 1 / 3.22) < 0.01
            assert abs(features.away_implied_probability - 1 / 3.52) < 0.01

            # 验证市场效率
            total_prob = (
                features.home_implied_probability
                + features.draw_implied_probability
                + features.away_implied_probability
            )
            assert 1.0 < total_prob < 1.1  # 正常的博彩公司抽水

    @pytest.mark.asyncio
    async def test_calculate_all_match_features(
        self, feature_calculator, sample_match_entity
    ):
        """测试计算比赛所有特征"""
        # 模拟所有相关数据
        mock_home_matches = [
            Mock(home_team_id=1, away_team_id=3, home_score=2, away_score=1),
            Mock(home_team_id=4, away_team_id=1, home_score=0, away_score=1),
        ]

        mock_away_matches = [
            Mock(home_team_id=2, away_team_id=5, home_score=1, away_score=0),
            Mock(home_team_id=6, away_team_id=2, home_score=2, away_score=2),
        ]

        mock_h2h_matches = [
            Mock(home_team_id=1, away_team_id=2, home_score=1, away_score=0)
        ]

        mock_odds = [
            Mock(
                bookmaker="Bet365",
                home_odds=Decimal("2.0"),
                draw_odds=Decimal("3.0"),
                away_odds=Decimal("3.5"),
            )
        ]

        # 模拟数据库查询，按调用顺序返回不同结果
        with patch.object(
            feature_calculator.db_manager, "get_async_session"
        ) as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.__aenter__.return_value = mock_session_instance

            # 配置多次查询的返回值
            mock_results = [
                # 主队近期表现查询
                Mock(
                    scalars=Mock(
                        return_value=Mock(all=Mock(return_value=mock_home_matches))
                    )
                ),
                # 客队近期表现查询
                Mock(
                    scalars=Mock(
                        return_value=Mock(all=Mock(return_value=mock_away_matches))
                    )
                ),
                # 历史对战查询
                Mock(
                    scalars=Mock(
                        return_value=Mock(all=Mock(return_value=mock_h2h_matches))
                    )
                ),
                # 赔率查询
                Mock(scalars=Mock(return_value=Mock(all=Mock(return_value=mock_odds)))),
            ]

            mock_session_instance.execute.side_effect = mock_results

            # 执行完整特征计算
            all_features = await feature_calculator.calculate_all_match_features(
                sample_match_entity
            )

            # 验证结果
            assert isinstance(all_features, AllMatchFeatures)
            assert all_features.match_entity == sample_match_entity
            assert isinstance(all_features.home_team_recent, RecentPerformanceFeatures)
            assert isinstance(all_features.away_team_recent, RecentPerformanceFeatures)
            assert isinstance(
                all_features.historical_matchup, HistoricalMatchupFeatures
            )
            assert isinstance(all_features.odds_features, OddsFeatures)

            # 验证主队特征
            assert all_features.home_team_recent.team_id == 1
            assert all_features.home_team_recent.recent_5_wins >= 0

            # 验证客队特征
            assert all_features.away_team_recent.team_id == 2
            assert all_features.away_team_recent.recent_5_wins >= 0

            # 验证历史对战特征
            assert all_features.historical_matchup.home_team_id == 1
            assert all_features.historical_matchup.away_team_id == 2

            # 验证赔率特征
            assert all_features.odds_features.match_id == 1
            assert all_features.odds_features.bookmaker_count == 1

    @pytest.mark.asyncio
    async def test_batch_calculate_team_features(self, feature_calculator):
        """测试批量计算球队特征"""
        team_ids = [1, 2, 3]
        calculation_date = datetime(2025, 9, 15)

        # 为每个球队模拟不同的比赛数据
        mock_team_matches = {
            1: [Mock(home_team_id=1, away_team_id=4, home_score=2, away_score=0)],
            2: [Mock(home_team_id=5, away_team_id=2, home_score=1, away_score=2)],
            3: [Mock(home_team_id=3, away_team_id=6, home_score=1, away_score=1)],
        }

        with patch.object(
            feature_calculator.db_manager, "get_async_session"
        ) as mock_session:
            mock_session_instance = AsyncMock()
            mock_session.__aenter__.return_value = mock_session_instance

            # 根据查询参数返回不同的结果
            def mock_execute(query):
                # 简化处理：假设每次查询都返回对应球队的数据
                result = Mock()
                if hasattr(query, "whereclause") and "team_id" in str(
                    query.whereclause
                ):
                    # 这里简化处理，实际应该解析查询条件
                    result.scalars.return_value.all.return_value = (
                        mock_team_matches.get(1, [])
                    )
                else:
                    result.scalars.return_value.all.return_value = []
                return result

            mock_session_instance.execute.side_effect = mock_execute

            # 执行批量计算
            results = await feature_calculator.batch_calculate_team_features(
                team_ids, calculation_date
            )

            # 验证结果
            assert len(results) == 3
            for team_id in team_ids:
                assert team_id in results
                assert isinstance(results[team_id], RecentPerformanceFeatures)
                assert results[team_id].team_id == team_id
                assert results[team_id].calculation_date == calculation_date

    def test_feature_property_calculations(self):
        """测试特征属性计算"""
        # 测试近期战绩特征的计算属性
        features = RecentPerformanceFeatures(
            team_id=1,
            calculation_date=datetime.now(),
            recent_5_wins=3,
            recent_5_draws=1,
            recent_5_losses=1,
            recent_5_goals_for=8,
            recent_5_goals_against=4,
        )

        assert features.recent_5_win_rate == 0.6  # 3/5
        assert features.recent_5_goals_per_game == 1.6  # 8/5

        # 测试历史对战特征的计算属性
        h2h_features = HistoricalMatchupFeatures(
            home_team_id=1,
            away_team_id=2,
            calculation_date=datetime.now(),
            h2h_total_matches=10,
            h2h_home_wins=4,
            h2h_away_wins=3,
            h2h_draws=3,
            h2h_home_goals_total=15,
            h2h_away_goals_total=12,
        )

        assert h2h_features.h2h_home_win_rate == 0.4  # 4/10
        assert h2h_features.h2h_goals_avg == 2.7  # 27/10
        assert h2h_features.h2h_home_goals_avg == 1.5  # 15/10

        # 测试赔率特征的计算属性
        odds_features = OddsFeatures(
            match_id=1,
            calculation_date=datetime.now(),
            home_implied_probability=0.45,
            draw_implied_probability=0.30,
            away_implied_probability=0.35,
            odds_variance_home=0.1,
            odds_variance_draw=0.15,
            odds_variance_away=0.12,
        )

        assert abs(odds_features.market_efficiency - 1.10) < 0.01
        assert (
            abs(odds_features.bookmaker_consensus - 0.877) < 0.01
        )  # 1 - (0.1+0.15+0.12)/3

    def test_feature_to_dict_serialization(
        self, sample_match_entity, sample_team_entity
    ):
        """测试特征对象序列化"""
        # 测试近期战绩特征序列化
        performance_features = RecentPerformanceFeatures(
            team_id=1,
            calculation_date=datetime(2025, 9, 15),
            recent_5_wins=3,
            recent_5_goals_for=8,
        )

        performance_dict = performance_features.to_dict()
        assert performance_dict["team_id"] == 1
        assert performance_dict["recent_5_wins"] == 3
        assert performance_dict["recent_5_goals_for"] == 8
        assert "calculation_date" in performance_dict
        assert "recent_5_win_rate" in performance_dict

        # 测试历史对战特征序列化
        h2h_features = HistoricalMatchupFeatures(
            home_team_id=1,
            away_team_id=2,
            calculation_date=datetime(2025, 9, 15),
            h2h_total_matches=5,
        )

        h2h_dict = h2h_features.to_dict()
        assert h2h_dict["home_team_id"] == 1
        assert h2h_dict["away_team_id"] == 2
        assert h2h_dict["h2h_total_matches"] == 5

        # 测试实体序列化
        match_dict = sample_match_entity.to_dict()
        assert match_dict["match_id"] == 1
        assert match_dict["home_team_id"] == 1
        assert match_dict["away_team_id"] == 2
        assert "match_time" in match_dict

        team_dict = sample_team_entity.to_dict()
        assert team_dict["team_id"] == 1
        assert team_dict["team_name"] == "测试球队"
