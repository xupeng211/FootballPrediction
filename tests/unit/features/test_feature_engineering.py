from typing import Optional

"""
特征工程模块测试

测试特征计算器的核心功能
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.features.feature_definitions import (
    HistoricalMatchupFeatures,
    OddsFeatures,
    RecentPerformanceFeatures,
)
from src.features.features.feature_calculator_calculators import FeatureCalculator


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def feature_calculator(mock_db_session):
    """特征计算器实例"""
    return FeatureCalculator(mock_db_session)


@pytest.fixture
def sample_match():
    """示例比赛数据"""
    match = MagicMock()
    match.id = 1
    match.home_team_id = 100
    match.away_team_id = 200
    match.match_date = datetime.now()
    match.home_score = 2
    match.away_score = 1
    match.status = "FINISHED"
    return match


@pytest.fixture
def sample_team():
    """示例球队数据"""
    team = MagicMock()
    team.id = 100
    team.name = "Test Team"
    team.short_name = "TT"
    team.country = "Test Country"
    return team


class TestFeatureCalculator:
    """特征计算器测试"""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_calculate_recent_performance_features_success(
        self, feature_calculator, mock_db_session
    ):
        """测试成功计算近期战绩特征"""
        # 准备测试数据
        team_id = 100
        calculation_date = datetime.now()

        # 模拟比赛数据
        mock_matches = [
            MagicMock(
                home_team_id=team_id,
                away_team_id=200,
                home_score=2,
                away_score=1,
                status="FINISHED",
                match_date=calculation_date,
            ),
            MagicMock(
                home_team_id=200,
                away_team_id=team_id,
                home_score=0,
                away_score=3,
                status="FINISHED",
                match_date=calculation_date,
            ),
            MagicMock(
                home_team_id=team_id,
                away_team_id=300,
                home_score=1,
                away_score=1,
                status="FINISHED",
                match_date=calculation_date,
            ),
        ]

        # 模拟数据库查询结果
        mock_result = MagicMock()  # execute() 返回的是普通对象，已经被await过了
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_matches
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # 执行测试
        result = await feature_calculator.calculate_recent_performance_features(
            team_id, calculation_date
        )

        # 验证结果
        assert result is not None
        assert result.team_id == team_id
        assert result.recent_5_wins == 2  # 2胜1平
        assert result.recent_5_draws == 1
        assert result.recent_5_losses == 0
        assert result.recent_5_goals_for == 6  # 2+3+1
        assert result.recent_5_goals_against == 2  # 1+0+1
        assert result.recent_5_points == 7  # 3*2 + 1*1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_calculate_recent_performance_features_no_matches(
        self, feature_calculator, mock_db_session
    ):
        """测试没有比赛记录时的处理"""
        team_id = 100
        calculation_date = datetime.now()

        # 模拟空查询结果
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # 执行测试
        result = await feature_calculator.calculate_recent_performance_features(
            team_id, calculation_date
        )

        # 验证结果
        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_calculate_historical_matchup_features_success(
        self, feature_calculator, mock_db_session
    ):
        """测试成功计算历史对战特征"""
        home_team_id = 100
        away_team_id = 200
        calculation_date = datetime.now()

        # 模拟历史对战数据
        mock_matches = [
            MagicMock(
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                home_score=2,
                away_score=1,
            ),
            MagicMock(
                home_team_id=away_team_id,
                away_team_id=home_team_id,
                home_score=1,
                away_score=2,
            ),
        ]

        # 模拟数据库查询结果
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = mock_matches
        mock_result.scalars.return_value = mock_scalars
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # 执行测试
        result = await feature_calculator.calculate_historical_matchup_features(
            home_team_id, away_team_id, calculation_date
        )

        # 验证结果
        assert result is not None
        assert result.home_team_id == home_team_id
        assert result.away_team_id == away_team_id
        assert result.h2h_total_matches == 2
        assert (
            result.h2h_home_wins == 2
        )  # 第一场主队2:1胜，第二场客队1:2胜(实际是主队away win)
        assert result.h2h_away_wins == 0
        assert result.h2h_draws == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_calculate_odds_features_success(
        self, feature_calculator, mock_db_session
    ):
        """测试成功计算赔率特征"""
        match_id = 1
        calculation_date = datetime.now()

        # 模拟赔率数据
        mock_home_odds = MagicMock()
        mock_home_odds.odds_value = 2.5

        mock_draw_odds = MagicMock()
        mock_draw_odds.odds_value = 3.2

        mock_away_odds = MagicMock()
        mock_away_odds.odds_value = 2.8

        # 模拟查询结果
        mock_home_result = MagicMock()
        mock_home_result.scalar_one_or_none.return_value = mock_home_odds

        mock_draw_result = MagicMock()
        mock_draw_result.scalar_one_or_none.return_value = mock_draw_odds

        mock_away_result = MagicMock()
        mock_away_result.scalar_one_or_none.return_value = mock_away_odds

        # 设置execute方法的返回值序列
        mock_db_session.execute = AsyncMock(
            side_effect=[
                mock_home_result,
                mock_draw_result,
                mock_away_result,
            ]
        )

        # 执行测试
        result = await feature_calculator.calculate_odds_features(
            match_id, calculation_date
        )

        # 验证结果
        assert result is not None
        assert result.match_id == match_id
        assert float(result.home_odds_avg) == 2.5
        assert float(result.draw_odds_avg) == 3.2
        assert float(result.away_odds_avg) == 2.8
        assert result.home_implied_probability == 0.4  # 1/2.5
        assert result.draw_implied_probability == pytest.approx(0.3125)  # 1/3.2
        assert result.away_implied_probability == pytest.approx(0.3571428571)  # 1/2.8

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_calculate_odds_features_incomplete_data(
        self, feature_calculator, mock_db_session
    ):
        """测试赔率数据不完整的处理"""
        match_id = 1
        calculation_date = datetime.now()

        # 模拟部分赔率数据缺失
        mock_home_odds = MagicMock()
        mock_home_odds.odds_value = 2.5

        # 为不同的查询返回不同的结果
        async def mock_execute_side_effect(query):
            mock_result = MagicMock()
            # 只有主胜赔率查询返回数据，其他返回None（模拟缺失）
            if "home_win" in str(query):
                mock_result.scalar_one_or_none.return_value = mock_home_odds
            else:  # draw 或 away_win 查询
                mock_result.scalar_one_or_none.return_value = None
            return mock_result

        # 设置mock执行函数
        mock_db_session.execute = AsyncMock(side_effect=mock_execute_side_effect)

        # 执行测试
        result = await feature_calculator.calculate_odds_features(
            match_id, calculation_date
        )

        # 验证结果 - 应该返回None因为数据不完整
        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_calculate_all_match_features_success(
        self, feature_calculator, mock_db_session, sample_match
    ):
        """测试成功计算完整比赛特征"""
        match_id = 1
        calculation_date = datetime.now()

        # 模拟各种查询结果
        # 1. 比赛查询
        match_result = MagicMock()
        match_result.scalar_one_or_none.return_value = sample_match

        # 2. 特征查询结果
        home_recent = MagicMock()
        away_recent = MagicMock()
        h2h_features = MagicMock()
        odds_features = MagicMock()

        # 设置execute方法的返回值序列
        mock_db_session.execute = AsyncMock(
            side_effect=[
                match_result,  # 比赛查询
                MagicMock(
                    scalars=MagicMock(all=MagicMock(return_value=[MagicMock()]))
                ),  # 主队近期战绩
                MagicMock(
                    scalars=MagicMock(all=MagicMock(return_value=[MagicMock()]))
                ),  # 客队近期战绩
                MagicMock(
                    scalars=MagicMock(all=MagicMock(return_value=[MagicMock()]))
                ),  # 历史对战
                MagicMock(),  # 主胜赔率
                MagicMock(),  # 平局赔率
                MagicMock(),  # 客胜赔率
            ]
        )

        # 模拟各个特征计算方法
        feature_calculator.calculate_recent_performance_features = AsyncMock(
            side_effect=[home_recent, away_recent]
        )
        feature_calculator.calculate_historical_matchup_features = AsyncMock(
            return_value=h2h_features
        )
        feature_calculator.calculate_odds_features = AsyncMock(
            return_value=odds_features
        )

        # 执行测试
        result = await feature_calculator.calculate_all_match_features(
            match_id, calculation_date
        )

        # 验证结果
        assert result is not None
        assert result.match_entity.match_id == match_id
        assert result.home_team_recent == home_recent
        assert result.away_team_recent == away_recent
        assert result.historical_matchup == h2h_features
        assert result.odds_features == odds_features

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_batch_calculate_match_features(self, feature_calculator):
        """测试批量计算比赛特征"""
        match_ids = [1, 2, 3]
        calculation_date = datetime.now()

        # 模拟单个特征计算结果
        mock_features = {1: MagicMock(), 2: None, 3: MagicMock()}  # 模拟失败情况

        feature_calculator.calculate_all_match_features = AsyncMock(
            side_effect=[mock_features[1], mock_features[2], mock_features[3]]
        )

        # 执行测试
        result = await feature_calculator.batch_calculate_match_features(
            match_ids, calculation_date
        )

        # 验证结果
        assert len(result) == 3
        assert result[1] == mock_features[1]
        assert result[2] is None
        assert result[3] == mock_features[3]


@pytest.mark.unit
class TestFeatureDefinitions:
    """特征定义测试"""

    def test_recent_performance_features_win_rate_calculation(self):
        """测试胜率计算"""
        features = RecentPerformanceFeatures(
            team_id=100,
            calculation_date=datetime.now(),
            recent_5_wins=3,
            recent_5_draws=1,
            recent_5_losses=1,
            recent_5_goals_for=8,
            recent_5_goals_against=4,
            recent_5_points=10,
        )

        assert features.recent_5_win_rate == 0.6  # 3/5
        assert features.recent_5_goals_per_game == 1.6  # 8/5

    def test_historical_matchup_features_calculation(self):
        """测试历史对战特征计算"""
        features = HistoricalMatchupFeatures(
            home_team_id=100,
            away_team_id=200,
            calculation_date=datetime.now(),
            h2h_total_matches=10,
            h2h_home_wins=6,
            h2h_away_wins=2,
            h2h_draws=2,
            h2h_home_goals_total=15,
            h2h_away_goals_total=10,
        )

        assert features.h2h_home_win_rate == 0.6  # 6/10
        assert features.h2h_goals_avg == 2.5  # (15+10)/10
        assert features.h2h_home_goals_avg == 1.5  # 15/10

    def test_odds_features_implied_probability_calculation(self):
        """测试隐含概率计算"""
        features = OddsFeatures(
            match_id=1,
            calculation_date=datetime.now(),
            home_odds_avg=2.0,
            draw_odds_avg=3.0,
            away_odds_avg=4.0,
        )

        # 手动设置隐含概率来测试计算属性
        features.home_implied_probability = 0.5  # 1/2.0
        features.draw_implied_probability = 0.3333  # 1/3.0
        features.away_implied_probability = 0.25  # 1/4.0

        assert features.market_efficiency == pytest.approx(
            1.0833
        )  # 0.5 + 0.3333 + 0.25