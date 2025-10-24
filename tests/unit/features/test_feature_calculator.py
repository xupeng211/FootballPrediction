# TODO: Consider creating a fixture for 14 repeated Mock creations

# TODO: Consider creating a fixture for 14 repeated Mock creations

from unittest.mock import Mock, patch, AsyncMock, MagicMock
"""
特征计算器测试
Tests for Feature Calculator
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.feature_calculator import FeatureCalculator


@pytest.mark.unit

class TestFeatureCalculator:
    """特征计算器测试"""

    @pytest.fixture
    def calculator(self):
        """创建特征计算器实例"""
        return FeatureCalculator()

    @pytest.fixture
    def sample_date(self):
        """示例日期"""
        return datetime(2024, 1, 1, 12, 0, 0)

    @pytest.fixture
    def mock_session(self):
        """Mock数据库会话"""
        return Mock(spec=AsyncSession)

    def test_initialization(self):
        """测试：初始化特征计算器"""
        # When
        calc = FeatureCalculator()

        # Then
        assert calc.db_manager is not None
        assert calc._config == {}
        assert calc.features == []

    def test_initialization_with_config(self):
        """测试：使用配置初始化特征计算器"""
        # Given
        _config = {"cache_size": 1000, "timeout": 30}

        # When
        calc = FeatureCalculator(_config=config)

        # Then
        assert calc._config == config

    @pytest.mark.asyncio
    async def test_calculate_recent_performance_features_with_no_matches(
        self, calculator, sample_date, mock_session
    ):
        """测试：计算近期战绩特征 - 无比赛记录"""
        # Given
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # When
        with patch.object(calculator, "db_manager") as mock_db:
            mock_db.get_async_session.return_value.__aenter__.return_value = (
                mock_session
            )
            features = await calculator.calculate_recent_performance_features(
                team_id=1, calculation_date=sample_date
            )

        # Then
        assert features is not None
        assert features.recent_5_wins == 0
        assert features.recent_5_draws == 0
        assert features.recent_5_losses == 0
        assert features.recent_5_goals_for == 0
        assert features.recent_5_goals_against == 0

    @pytest.mark.asyncio
    async def test_calculate_recent_performance_features_with_matches(
        self, calculator, sample_date, mock_session
    ):
        """测试：计算近期战绩特征 - 有比赛记录"""
        # Given
        mock_match1 = Mock()
        mock_match1.home_team_id = 1
        mock_match1.away_team_id = 2
        mock_match1.home_score = 2
        mock_match1.away_score = 1

        mock_match2 = Mock()
        mock_match2.home_team_id = 3
        mock_match2.away_team_id = 1
        mock_match2.home_score = 1
        mock_match2.away_score = 1

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_match1, mock_match2]
        mock_session.execute.return_value = mock_result

        # When
        with patch.object(calculator, "db_manager") as mock_db:
            mock_db.get_async_session.return_value.__aenter__.return_value = (
                mock_session
            )
            features = await calculator.calculate_recent_performance_features(
                team_id=1, calculation_date=sample_date
            )

        # Then
        assert features is not None
        assert features.recent_5_wins == 1  # 第一场赢
        assert features.recent_5_draws == 1  # 第二场平
        assert features.recent_5_losses == 0
        assert features.recent_5_goals_for == 3  # 2+1
        assert features.recent_5_goals_against == 2  # 1+1

    @pytest.mark.asyncio
    async def test_calculate_historical_matchup_features(
        self, calculator, sample_date, mock_session
    ):
        """测试：计算历史对战特征"""
        # Given
        mock_match = Mock()
        mock_match.home_team_id = 1
        mock_match.away_team_id = 2
        mock_match.home_score = 2
        mock_match.away_score = 1

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [mock_match]
        mock_session.execute.return_value = mock_result

        # When
        with patch.object(calculator, "db_manager") as mock_db:
            mock_db.get_async_session.return_value.__aenter__.return_value = (
                mock_session
            )
            features = await calculator.calculate_historical_matchup_features(
                home_team_id=1, away_team_id=2, calculation_date=sample_date
            )

        # Then
        assert features is not None

    @pytest.mark.asyncio
    async def test_calculate_features_with_session_provided(
        self, calculator, sample_date, mock_session
    ):
        """测试：使用提供的数据库会话计算特征"""
        # Given
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        # When
        features = await calculator.calculate_recent_performance_features(
            team_id=1, calculation_date=sample_date, session=mock_session
        )

        # Then
        assert features is not None

    def test_config_property(self):
        """测试：配置属性"""
        # Given
        _config = {"test": "value"}
        calc = FeatureCalculator(config)

        # When/Then
        assert calc._config["test"] == "value"

    @pytest.mark.asyncio
    async def test_database_manager_usage(self, calculator):
        """测试：数据库管理器的使用"""
        # When
        with patch.object(calculator, "db_manager") as mock_db:
            mock_db.get_async_session.return_value.__aenter__ = AsyncMock()
            mock_db.get_async_session.return_value.__aexit__ = AsyncMock()

            # Then
            async with calculator.db_manager.get_async_session() as session:
                assert session is not None

    @pytest.mark.asyncio
    async def test_calculate_features_with_different_dates(self, calculator):
        """测试：使用不同日期计算特征"""
        # Given
        dates = [
            datetime(2024, 1, 1),
            datetime(2024, 6, 15),
            datetime(2024, 12, 31),
        ]

        for date in dates:
            # When
            with patch.object(calculator, "db_manager") as mock_db:
                mock_session = AsyncMock()
                mock_result = AsyncMock()
                mock_result.scalars.return_value.all.return_value = []
                mock_session.execute.return_value = mock_result
                mock_db.get_async_session.return_value.__aenter__.return_value = (
                    mock_session
                )

                features = await calculator.calculate_recent_performance_features(
                    team_id=1, calculation_date=date
                )

                # Then
                assert features is not None
                assert features.calculation_date == date

    @pytest.mark.asyncio
    async def test_calculate_features_multiple_teams(self, calculator, sample_date):
        """测试：为多个球队计算特征"""
        # Given
        team_ids = [1, 2, 3, 4, 5]

        for team_id in team_ids:
            # When
            with patch.object(calculator, "db_manager") as mock_db:
                mock_session = AsyncMock()
                mock_result = AsyncMock()
                mock_result.scalars.return_value.all.return_value = []
                mock_session.execute.return_value = mock_result
                mock_db.get_async_session.return_value.__aenter__.return_value = (
                    mock_session
                )

                features = await calculator.calculate_recent_performance_features(
                    team_id=team_id, calculation_date=sample_date
                )

                # Then
                assert features is not None
                assert features.team_id == team_id
