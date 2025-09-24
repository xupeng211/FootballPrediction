"""
Phase 3：特征计算器模块综合测试
目标：全面提升feature_calculator.py模块覆盖率到60%+
重点：测试特征计算核心功能、近期表现特征、历史对战特征、赔率特征和批量处理
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.feature_calculator import (
    AllMatchFeatures,
    FeatureCalculator,
    HistoricalMatchupFeatures,
    OddsFeatures,
    RecentPerformanceFeatures,
)


class TestFeatureCalculatorBasic:
    """特征计算器基础测试"""

    def setup_method(self):
        """设置测试环境"""
        self.calculator = FeatureCalculator()

    def test_calculator_initialization(self):
        """测试特征计算器初始化"""
        assert self.calculator is not None
        assert hasattr(self.calculator, "db_manager")
        assert hasattr(self.calculator, "feature_store")
        assert hasattr(self.calculator, "logger")
        assert hasattr(self.calculator, "cache_ttl")
        assert hasattr(self.calculator, "retries")
        assert self.calculator.cache_ttl > 0
        assert self.calculator.retries >= 0


class TestFeatureCalculatorRecentPerformance:
    """特征计算器近期表现特征测试"""

    def setup_method(self):
        """设置测试环境"""
        self.calculator = FeatureCalculator()

    @pytest.mark.asyncio
    async def test_calculate_recent_performance_features_success(self):
        """测试成功计算近期表现特征"""
        team_id = 1
        calculation_date = datetime(2023, 1, 15)

        with patch.object(self.calculator, "db_manager") as mock_db:
            mock_session = AsyncMock()

            # Mock查询结果：最近5场比赛
            mock_matches = [
                MagicMock(
                    home_team_id=1,
                    away_team_id=2,
                    home_score=2,
                    away_score=1,
                    match_time=datetime(2023, 1, 10),
                ),
                MagicMock(
                    home_team_id=3,
                    away_team_id=1,
                    home_score=1,
                    away_score=2,
                    match_time=datetime(2023, 1, 7),
                ),
                MagicMock(
                    home_team_id=1,
                    away_team_id=4,
                    home_score=3,
                    away_score=0,
                    match_time=datetime(2023, 1, 4),
                ),
                MagicMock(
                    home_team_id=5,
                    away_team_id=1,
                    home_score=2,
                    away_score=2,
                    match_time=datetime(2023, 1, 1),
                ),
                MagicMock(
                    home_team_id=1,
                    away_team_id=6,
                    home_score=1,
                    away_score=0,
                    match_time=datetime(2022, 12, 28),
                ),
            ]

            # Mock数据库查询
            mock_result = MagicMock()
            mock_result.all.return_value = mock_matches
            mock_session.execute.return_value = mock_result

            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session
            mock_context_manager.__aexit__.return_value = None
            mock_db.get_async_session.return_value = mock_context_manager

            features = await self.calculator.calculate_recent_performance_features(
                team_id, calculation_date
            )

            assert isinstance(features, RecentPerformanceFeatures)
            assert features.team_id == team_id
            assert features.calculation_date == calculation_date
            assert features.recent_5_wins == 3  # 3胜
            assert features.recent_5_draws == 1  # 1平
            assert features.recent_5_losses == 1  # 1负
            assert features.recent_5_goals_for == 8  # 进8球
            assert features.recent_5_goals_against == 4  # 失4球
            assert features.recent_5_points == 10  # 10分
            assert features.recent_5_home_wins == 2  # 2个主场胜利
            assert features.recent_5_away_wins == 1  # 1个客场胜利

    @pytest.mark.asyncio
    async def test_calculate_recent_performance_features_no_matches(self):
        """测试无比赛记录的近期表现特征计算"""
        team_id = 999
        calculation_date = datetime(2023, 1, 15)

        with patch.object(self.calculator, "db_manager") as mock_db:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.all.return_value = []  # 无比赛记录
            mock_session.execute.return_value = mock_result

            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session
            mock_context_manager.__aexit__.return_value = None
            mock_db.get_async_session.return_value = mock_context_manager

            features = await self.calculator.calculate_recent_performance_features(
                team_id, calculation_date
            )

            assert isinstance(features, RecentPerformanceFeatures)
            assert features.team_id == team_id
            assert features.recent_5_wins == 0
            assert features.recent_5_draws == 0
            assert features.recent_5_losses == 0
            assert features.recent_5_goals_for == 0
            assert features.recent_5_goals_against == 0
            assert features.recent_5_points == 0

    @pytest.mark.asyncio
    async def test_calculate_recent_performance_features_database_error(self):
        """测试数据库错误处理"""
        team_id = 1
        calculation_date = datetime(2023, 1, 15)

        with patch.object(self.calculator, "db_manager") as mock_db:
            mock_db.get_async_session.side_effect = Exception("Database error")

            with pytest.raises(Exception, match="Database error"):
                await self.calculator.calculate_recent_performance_features(
                    team_id, calculation_date
                )

    @pytest.mark.asyncio
    async def test_calculate_recent_performance_features_custom_session(self):
        """测试使用自定义数据库会话"""
        team_id = 1
        calculation_date = datetime(2023, 1, 15)
        custom_session = AsyncMock()

        # Mock查询结果
        mock_matches = [
            MagicMock(
                home_team_id=1,
                away_team_id=2,
                home_score=2,
                away_score=1,
                match_time=datetime(2023, 1, 10),
            ),
            MagicMock(
                home_team_id=3,
                away_team_id=1,
                home_score=1,
                away_score=0,
                match_time=datetime(2023, 1, 7),
            ),
        ]

        mock_result = MagicMock()
        mock_result.all.return_value = mock_matches
        custom_session.execute.return_value = mock_result

        features = await self.calculator.calculate_recent_performance_features(
            team_id, calculation_date, custom_session
        )

        assert isinstance(features, RecentPerformanceFeatures)
        assert features.recent_5_wins == 2
        assert features.recent_5_goals_for == 3


class TestFeatureCalculatorHistoricalMatchup:
    """特征计算器历史对战特征测试"""

    def setup_method(self):
        """设置测试环境"""
        self.calculator = FeatureCalculator()

    @pytest.mark.asyncio
    async def test_calculate_historical_matchup_features_success(self):
        """测试成功计算历史对战特征"""
        home_team_id = 1
        away_team_id = 2
        calculation_date = datetime(2023, 1, 15)

        with patch.object(self.calculator, "db_manager") as mock_db:
            mock_session = AsyncMock()

            # Mock历史对战记录
            mock_matches = [
                MagicMock(
                    home_team_id=1,
                    away_team_id=2,
                    home_score=2,
                    away_score=1,
                    match_time=datetime(2022, 12, 10),
                ),
                MagicMock(
                    home_team_id=2,
                    away_team_id=1,
                    home_score=1,
                    away_score=2,
                    match_time=datetime(2022, 9, 15),
                ),
                MagicMock(
                    home_team_id=1,
                    away_team_id=2,
                    home_score=3,
                    away_score=0,
                    match_time=datetime(2022, 6, 20),
                ),
                MagicMock(
                    home_team_id=1,
                    away_team_id=2,
                    home_score=1,
                    away_score=1,
                    match_time=datetime(2022, 3, 25),
                ),
                MagicMock(
                    home_team_id=2,
                    away_team_id=1,
                    home_score=2,
                    away_score=0,
                    match_time=datetime(2021, 12, 30),
                ),
                MagicMock(
                    home_team_id=1,
                    away_team_id=2,
                    home_score=0,
                    away_score=1,
                    match_time=datetime(2021, 9, 5),
                ),
            ]

            # Mock最近5次交锋
            mock_recent_matches = [
                MagicMock(
                    home_team_id=1,
                    away_team_id=2,
                    home_score=2,
                    away_score=1,
                    match_time=datetime(2022, 12, 10),
                ),
                MagicMock(
                    home_team_id=2,
                    away_team_id=1,
                    home_score=1,
                    away_score=2,
                    match_time=datetime(2022, 9, 15),
                ),
                MagicMock(
                    home_team_id=1,
                    away_team_id=2,
                    home_score=3,
                    away_score=0,
                    match_time=datetime(2022, 6, 20),
                ),
                MagicMock(
                    home_team_id=1,
                    away_team_id=2,
                    home_score=1,
                    away_score=1,
                    match_time=datetime(2022, 3, 25),
                ),
                MagicMock(
                    home_team_id=2,
                    away_team_id=1,
                    home_score=2,
                    away_score=0,
                    match_time=datetime(2021, 12, 30),
                ),
            ]

            # Mock数据库查询
            mock_result_all = MagicMock()
            mock_result_all.all.return_value = mock_matches
            mock_result_recent = MagicMock()
            mock_result_recent.all.return_value = mock_recent_matches

            # 设置不同的查询返回不同结果
            def mock_execute(query):
                if "LIMIT 5" in str(query):
                    return mock_result_recent
                return mock_result_all

            mock_session.execute.side_effect = mock_execute

            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session
            mock_context_manager.__aexit__.return_value = None
            mock_db.get_async_session.return_value = mock_context_manager

            features = await self.calculator.calculate_historical_matchup_features(
                home_team_id, away_team_id, calculation_date
            )

            assert isinstance(features, HistoricalMatchupFeatures)
            assert features.home_team_id == home_team_id
            assert features.away_team_id == away_team_id
            assert features.h2h_total_matches == 6
            assert features.h2h_home_wins == 2
            assert features.h2h_away_wins == 2
            assert features.h2h_draws == 2
            assert features.h2h_recent_5_home_wins == 2
            assert features.h2h_recent_5_away_wins == 1

    @pytest.mark.asyncio
    async def test_calculate_historical_matchup_features_no_history(self):
        """测试无历史对战记录的特征计算"""
        home_team_id = 999
        away_team_id = 1000
        calculation_date = datetime(2023, 1, 15)

        with patch.object(self.calculator, "db_manager") as mock_db:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.all.return_value = []  # 无历史对战
            mock_session.execute.return_value = mock_result

            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session
            mock_context_manager.__aexit__.return_value = None
            mock_db.get_async_session.return_value = mock_context_manager

            features = await self.calculator.calculate_historical_matchup_features(
                home_team_id, away_team_id, calculation_date
            )

            assert isinstance(features, HistoricalMatchupFeatures)
            assert features.h2h_total_matches == 0
            assert features.h2h_home_wins == 0
            assert features.h2h_away_wins == 0
            assert features.h2h_draws == 0
            assert features.h2h_recent_5_home_wins == 0
            assert features.h2h_recent_5_away_wins == 0


class TestFeatureCalculatorOddsFeatures:
    """特征计算器赔率特征测试"""

    def setup_method(self):
        """设置测试环境"""
        self.calculator = FeatureCalculator()

    @pytest.mark.asyncio
    async def test_calculate_odds_features_success(self):
        """测试成功计算赔率特征"""
        match_id = 12345
        calculation_date = datetime(2023, 1, 15)

        with patch.object(self.calculator, "db_manager") as mock_db:
            mock_session = AsyncMock()

            # Mock赔率数据
            mock_odds = [
                MagicMock(
                    bookmaker_id=1, home_odds=2.50, draw_odds=3.20, away_odds=2.80
                ),
                MagicMock(
                    bookmaker_id=2, home_odds=2.45, draw_odds=3.30, away_odds=2.85
                ),
                MagicMock(
                    bookmaker_id=3, home_odds=2.55, draw_odds=3.15, away_odds=2.75
                ),
            ]

            mock_result = MagicMock()
            mock_result.all.return_value = mock_odds
            mock_session.execute.return_value = mock_result

            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session
            mock_context_manager.__aexit__.return_value = None
            mock_db.get_async_session.return_value = mock_context_manager

            features = await self.calculator.calculate_odds_features(
                match_id, calculation_date
            )

            assert isinstance(features, OddsFeatures)
            assert features.match_id == match_id
            assert abs(features.home_odds_avg - 2.50) < 0.01  # (2.50 + 2.45 + 2.55) / 3
            assert abs(features.draw_odds_avg - 3.22) < 0.01  # (3.20 + 3.30 + 3.15) / 3
            assert abs(features.away_odds_avg - 2.80) < 0.01  # (2.80 + 2.85 + 2.75) / 3
            assert abs(features.home_implied_probability - 0.40) < 0.01  # 1/2.50
            assert abs(features.draw_implied_probability - 0.31) < 0.01  # 1/3.22
            assert abs(features.away_implied_probability - 0.36) < 0.01  # 1/2.80

    @pytest.mark.asyncio
    async def test_calculate_odds_features_no_odds(self):
        """测试无赔率数据的特征计算"""
        match_id = 99999
        calculation_date = datetime(2023, 1, 15)

        with patch.object(self.calculator, "db_manager") as mock_db:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.all.return_value = []  # 无赔率数据
            mock_session.execute.return_value = mock_result

            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session
            mock_context_manager.__aexit__.return_value = None
            mock_db.get_async_session.return_value = mock_context_manager

            features = await self.calculator.calculate_odds_features(
                match_id, calculation_date
            )

            assert isinstance(features, OddsFeatures)
            assert features.home_odds_avg == 0.0
            assert features.draw_odds_avg == 0.0
            assert features.away_odds_avg == 0.0
            assert features.home_implied_probability == 0.0
            assert features.draw_implied_probability == 0.0
            assert features.away_implied_probability == 0.0

    @pytest.mark.asyncio
    async def test_calculate_odds_features_single_bookmaker(self):
        """测试单个博彩公司的赔率特征计算"""
        match_id = 12345
        calculation_date = datetime(2023, 1, 15)

        with patch.object(self.calculator, "db_manager") as mock_db:
            mock_session = AsyncMock()

            mock_odds = [
                MagicMock(
                    bookmaker_id=1, home_odds=2.50, draw_odds=3.20, away_odds=2.80
                )
            ]

            mock_result = MagicMock()
            mock_result.all.return_value = mock_odds
            mock_session.execute.return_value = mock_result

            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__.return_value = mock_session
            mock_context_manager.__aexit__.return_value = None
            mock_db.get_async_session.return_value = mock_context_manager

            features = await self.calculator.calculate_odds_features(
                match_id, calculation_date
            )

            assert features.home_odds_avg == 2.50
            assert features.draw_odds_avg == 3.20
            assert features.away_odds_avg == 2.80


class TestFeatureCalculatorAllMatchFeatures:
    """特征计算器全比赛特征测试"""

    def setup_method(self):
        """设置测试环境"""
        self.calculator = FeatureCalculator()

    @pytest.mark.asyncio
    async def test_calculate_all_match_features_success(self):
        """测试成功计算全比赛特征"""
        from src.database.models import Match

        # 创建模拟的Match实体
        match_entity = Match(
            id=12345,
            home_team_id=1,
            away_team_id=2,
            league_id=1,
            match_time=datetime(2023, 1, 15),
            home_score=None,
            away_score=None,
            season=2023,
        )

        with patch.object(
            self.calculator, "calculate_recent_performance_features"
        ) as mock_recent, patch.object(
            self.calculator, "calculate_historical_matchup_features"
        ) as mock_h2h, patch.object(
            self.calculator, "calculate_odds_features"
        ) as mock_odds:
            # Mock各个特征计算结果
            mock_recent.return_value = RecentPerformanceFeatures(
                team_id=1,
                calculation_date=datetime(2023, 1, 15),
                recent_5_wins=3,
                recent_5_draws=1,
                recent_5_losses=1,
                recent_5_goals_for=8,
                recent_5_goals_against=4,
                recent_5_points=10,
                recent_5_home_wins=2,
                recent_5_away_wins=1,
            )

            mock_h2h.return_value = HistoricalMatchupFeatures(
                home_team_id=1,
                away_team_id=2,
                calculation_date=datetime(2023, 1, 15),
                h2h_total_matches=6,
                h2h_home_wins=2,
                h2h_away_wins=2,
                h2h_draws=2,
                h2h_recent_5_home_wins=2,
                h2h_recent_5_away_wins=1,
            )

            mock_odds.return_value = OddsFeatures(
                match_id=12345,
                calculation_date=datetime(2023, 1, 15),
                home_odds_avg=2.50,
                draw_odds_avg=3.20,
                away_odds_avg=2.80,
                home_implied_probability=0.40,
                draw_implied_probability=0.31,
                away_implied_probability=0.36,
            )

            features = await self.calculator.calculate_all_match_features(match_entity)

            assert isinstance(features, AllMatchFeatures)
            assert features.match_id == 12345
            assert features.home_team_id == 1
            assert features.away_team_id == 2
            assert features.calculation_date == datetime(2023, 1, 15)

            # 验证主队特征
            assert features.home_recent_5_wins == 3
            assert features.home_recent_5_goals_for == 8

            # 验证客队特征
            mock_recent.assert_called_with(2, datetime(2023, 1, 15), None)

            # 验证历史对战特征
            assert features.h2h_total_matches == 6
            assert features.h2h_home_wins == 2

            # 验证赔率特征
            assert features.home_odds_avg == 2.50
            assert features.draw_odds_avg == 3.20

    @pytest.mark.asyncio
    async def test_calculate_all_match_features_custom_date(self):
        """测试使用自定义日期计算全比赛特征"""
        from src.database.models import Match

        match_entity = Match(
            id=12345,
            home_team_id=1,
            away_team_id=2,
            league_id=1,
            match_time=datetime(2023, 1, 15),
            home_score=None,
            away_score=None,
            season=2023,
        )

        custom_date = datetime(2023, 1, 10)

        with patch.object(
            self.calculator, "calculate_recent_performance_features"
        ) as mock_recent, patch.object(
            self.calculator, "calculate_historical_matchup_features"
        ) as mock_h2h, patch.object(
            self.calculator, "calculate_odds_features"
        ) as mock_odds:
            mock_recent.return_value = RecentPerformanceFeatures(
                team_id=1,
                calculation_date=custom_date,
                recent_5_wins=2,
                recent_5_draws=1,
                recent_5_losses=2,
                recent_5_goals_for=5,
                recent_5_goals_against=6,
                recent_5_points=7,
                recent_5_home_wins=1,
                recent_5_away_wins=1,
            )

            mock_h2h.return_value = HistoricalMatchupFeatures(
                home_team_id=1,
                away_team_id=2,
                calculation_date=custom_date,
                h2h_total_matches=4,
                h2h_home_wins=1,
                h2h_away_wins=1,
                h2h_draws=2,
                h2h_recent_5_home_wins=1,
                h2h_recent_5_away_wins=1,
            )

            mock_odds.return_value = OddsFeatures(
                match_id=12345,
                calculation_date=custom_date,
                home_odds_avg=2.0,
                draw_odds_avg=3.0,
                away_odds_avg=3.5,
                home_implied_probability=0.5,
                draw_implied_probability=0.33,
                away_implied_probability=0.29,
            )

            features = await self.calculator.calculate_all_match_features(
                match_entity, custom_date
            )

            assert features.calculation_date == custom_date
            mock_recent.assert_called_with(1, custom_date, None)
            mock_h2h.assert_called_with(1, 2, custom_date, None)
            mock_odds.assert_called_with(12345, custom_date, None)


class TestFeatureCalculatorUtilityMethods:
    """特征计算器工具方法测试"""

    def setup_method(self):
        """设置测试环境"""
        self.calculator = FeatureCalculator()

    def test_calculate_implied_probability(self):
        """测试隐含概率计算"""
        prob = self.calculator._calculate_implied_probability(2.0)
        assert abs(prob - 0.5) < 0.001

        prob = self.calculator._calculate_implied_probability(3.0)
        assert abs(prob - 0.333) < 0.001

        prob = self.calculator._calculate_implied_probability(0.0)
        assert prob == 0.0

    def test_calculate_average_odds(self):
        """测试平均赔率计算"""
        odds_list = [2.5, 2.6, 2.4]
        avg = self.calculator._calculate_average_odds(odds_list)
        assert abs(avg - 2.5) < 0.001

        avg = self.calculator._calculate_average_odds([])
        assert avg == 0.0

    def test_filter_matches_by_date(self):
        """测试按日期过滤比赛"""
        matches = [
            MagicMock(match_time=datetime(2023, 1, 10)),
            MagicMock(match_time=datetime(2023, 1, 5)),
            MagicMock(match_time=datetime(2023, 1, 15)),
        ]

        filtered = self.calculator._filter_matches_by_date(
            matches, datetime(2023, 1, 8)
        )
        assert len(filtered) == 2  # 1月10日和1月5日的比赛

    def test_calculate_points_from_matches(self):
        """测试从比赛计算积分"""
        matches = [
            MagicMock(
                home_team_id=1, away_team_id=2, home_score=2, away_score=1
            ),  # 主队胜利
            MagicMock(
                home_team_id=3, away_team_id=1, home_score=1, away_score=2
            ),  # 客队胜利
            MagicMock(home_team_id=1, away_team_id=4, home_score=1, away_score=1),  # 平局
        ]

        points = self.calculator._calculate_points_from_matches(matches, 1)
        assert points == 7  # 3 + 3 + 1 = 7分


class TestFeatureCalculatorErrorHandling:
    """特征计算器错误处理测试"""

    def setup_method(self):
        """设置测试环境"""
        self.calculator = FeatureCalculator()

    @pytest.mark.asyncio
    async def test_feature_calculation_with_retries(self):
        """测试带重试的特征计算"""
        call_count = 0

        async def failing_calculation(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return RecentPerformanceFeatures(
                team_id=1,
                calculation_date=datetime(2023, 1, 15),
                recent_5_wins=1,
                recent_5_draws=1,
                recent_5_losses=1,
                recent_5_goals_for=3,
                recent_5_goals_against=3,
                recent_5_points=4,
                recent_5_home_wins=1,
                recent_5_away_wins=0,
            )

        with patch.object(self.calculator, "_query_recent_matches") as mock_query:
            mock_query.side_effect = failing_calculation

            with patch("asyncio.sleep", new_callable=AsyncMock):  # Mock sleep
                features = await self.calculator.calculate_recent_performance_features(
                    1, datetime(2023, 1, 15)
                )

                assert features.recent_5_wins == 1
                assert call_count == 3  # 应该重试3次

    @pytest.mark.asyncio
    async def test_concurrent_feature_calculations(self):
        """测试并发特征计算"""
        import asyncio

        async def mock_calculation(*args, **kwargs):
            await asyncio.sleep(0.1)  # 模拟计算延迟
            return RecentPerformanceFeatures(
                team_id=1,
                calculation_date=datetime(2023, 1, 15),
                recent_5_wins=1,
                recent_5_draws=1,
                recent_5_losses=1,
                recent_5_goals_for=3,
                recent_5_goals_against=3,
                recent_5_points=4,
                recent_5_home_wins=1,
                recent_5_away_wins=0,
            )

        with patch.object(
            self.calculator, "_query_recent_matches", side_effect=mock_calculation
        ):
            # 并发执行多个特征计算
            tasks = [
                self.calculator.calculate_recent_performance_features(
                    1, datetime(2023, 1, 15)
                )
                for _ in range(3)
            ]
            results = await asyncio.gather(*tasks)

            assert len(results) == 3
            for result in results:
                assert result.recent_5_wins == 1

    def test_feature_data_validation(self):
        """测试特征数据验证"""
        # 测试RecentPerformanceFeatures验证
        features = RecentPerformanceFeatures(
            team_id=1,
            calculation_date=datetime(2023, 1, 15),
            recent_5_wins=3,
            recent_5_draws=1,
            recent_5_losses=1,
            recent_5_goals_for=8,
            recent_5_goals_against=4,
            recent_5_points=10,
            recent_5_home_wins=2,
            recent_5_away_wins=1,
        )

        # 验证数据一致性
        total_matches = (
            features.recent_5_wins + features.recent_5_draws + features.recent_5_losses
        )
        assert total_matches <= 5  # 最多5场比赛

        total_points = features.recent_5_points
        expected_points = features.recent_5_wins * 3 + features.recent_5_draws * 1
        assert total_points == expected_points


class TestFeatureCalculatorIntegration:
    """特征计算器集成测试"""

    def setup_method(self):
        """设置测试环境"""
        self.calculator = FeatureCalculator()

    @pytest.mark.asyncio
    async def test_complete_feature_calculation_workflow(self):
        """测试完整的特征计算工作流"""
        from src.database.models import Match

        match_entity = Match(
            id=12345,
            home_team_id=1,
            away_team_id=2,
            league_id=1,
            match_time=datetime(2023, 1, 15),
            home_score=None,
            away_score=None,
            season=2023,
        )

        with patch.object(
            self.calculator, "calculate_recent_performance_features"
        ) as mock_recent, patch.object(
            self.calculator, "calculate_historical_matchup_features"
        ) as mock_h2h, patch.object(
            self.calculator, "calculate_odds_features"
        ) as mock_odds:
            # Mock特征计算结果
            mock_recent.side_effect = [
                RecentPerformanceFeatures(
                    team_id=1,
                    calculation_date=datetime(2023, 1, 15),
                    recent_5_wins=3,
                    recent_5_draws=1,
                    recent_5_losses=1,
                    recent_5_goals_for=8,
                    recent_5_goals_against=4,
                    recent_5_points=10,
                    recent_5_home_wins=2,
                    recent_5_away_wins=1,
                ),
                RecentPerformanceFeatures(
                    team_id=2,
                    calculation_date=datetime(2023, 1, 15),
                    recent_5_wins=2,
                    recent_5_draws=2,
                    recent_5_losses=1,
                    recent_5_goals_for=6,
                    recent_5_goals_against=5,
                    recent_5_points=8,
                    recent_5_home_wins=1,
                    recent_5_away_wins=1,
                ),
            ]

            mock_h2h.return_value = HistoricalMatchupFeatures(
                home_team_id=1,
                away_team_id=2,
                calculation_date=datetime(2023, 1, 15),
                h2h_total_matches=6,
                h2h_home_wins=2,
                h2h_away_wins=2,
                h2h_draws=2,
                h2h_recent_5_home_wins=2,
                h2h_recent_5_away_wins=1,
            )

            mock_odds.return_value = OddsFeatures(
                match_id=12345,
                calculation_date=datetime(2023, 1, 15),
                home_odds_avg=2.50,
                draw_odds_avg=3.20,
                away_odds_avg=2.80,
                home_implied_probability=0.40,
                draw_implied_probability=0.31,
                away_implied_probability=0.36,
            )

            features = await self.calculator.calculate_all_match_features(match_entity)

            # 验证特征完整性
            assert features.match_id == 12345
            assert features.home_team_id == 1
            assert features.away_team_id == 2

            # 验证主队特征
            assert features.home_recent_5_wins == 3
            assert features.home_recent_5_goals_for == 8

            # 验证客队特征
            assert features.away_recent_5_wins == 2
            assert features.away_recent_5_goals_for == 6

            # 验证历史对战特征
            assert features.h2h_total_matches == 6

            # 验证赔率特征
            assert features.home_odds_avg == 2.50

            # 验证计算日期
            assert features.calculation_date == datetime(2023, 1, 15)

    def test_feature_calculator_configuration(self):
        """测试特征计算器配置"""
        assert self.calculator.cache_ttl > 0
        assert self.calculator.retries >= 0
        assert hasattr(self.calculator, "db_manager")
        assert hasattr(self.calculator, "feature_store")
        assert hasattr(self.calculator, "logger")
