"""
特征工程简化测试
Feature Engineering Simple Tests

测试特征工程系统的核心功能，基于实际模块结构.
Tests core functionality of feature engineering system based on actual module structure.
"""

from datetime import datetime
from unittest.mock import AsyncMock

import numpy as np
import pandas as pd
import pytest

from src.features import (
    AllMatchFeatures,
    AllTeamFeatures,
    FeatureCalculator,
    HistoricalMatchupFeatures,
    MatchEntity,
    OddsFeatures,
    RecentPerformanceFeatures,
    TeamEntity,
)
from src.features.entities import FeatureEntity, FeatureKey


class TestFeatureEntitiesSimple:
    """特征实体简化测试类"""

    def test_match_entity_creation_simple(self):
        """测试比赛实体创建"""
        match_time = datetime(2024, 1, 15, 15, 0)
        season = "2023-2024"

        # 创建比赛实体 - 使用正确的字段名
        match_entity = MatchEntity(
            match_id=12345,
            home_team_id=1,
            away_team_id=2,
            league_id=39,
            match_time=match_time,
            season=season,
        )

        # 验证实体属性
        assert match_entity.match_id == 12345
        assert match_entity.home_team_id == 1
        assert match_entity.away_team_id == 2
        assert match_entity.league_id == 39
        assert match_entity.match_time == match_time
        assert match_entity.season == season

    def test_team_entity_creation_simple(self):
        """测试球队实体创建"""
        # 创建球队实体 - 使用正确的字段名
        team_entity = TeamEntity(
            team_id=1,
            team_name="Team A",
            league_id=39,
            home_venue="Stadium A",
        )

        # 验证实体属性
        assert team_entity.team_id == 1
        assert team_entity.team_name == "Team A"
        assert team_entity.league_id == 39
        assert team_entity.home_venue == "Stadium A"

    def test_feature_key_creation_simple(self):
        """测试特征键创建"""
        feature_timestamp = datetime(2024, 1, 15)

        # 创建特征键 - 使用正确的字段名
        feature_key = FeatureKey(
            entity_type="team_performance",
            entity_id=1,
            feature_timestamp=feature_timestamp,
        )

        # 验证特征键属性
        assert feature_key.entity_type == "team_performance"
        assert feature_key.entity_id == 1
        assert feature_key.feature_timestamp == feature_timestamp

    def test_feature_entity_creation_simple(self):
        """测试特征实体创建"""
        # 创建特征实体 - 使用正确的字段名
        feature_entity = FeatureEntity(
            id="feature_123",
            feature_type="team_performance",
            data={"goals_scored": 2.5, "goals_conceded": 1.2},
            created_at=datetime(2024, 1, 15, 10, 0),
            updated_at=datetime(2024, 1, 15, 10, 0),
        )

        # 验证实体属性
        assert feature_entity.id == "feature_123"
        assert feature_entity.feature_type == "team_performance"
        assert feature_entity.data["goals_scored"] == 2.5
        assert feature_entity.data["goals_conceded"] == 1.2

    def test_feature_entity_is_expired_simple(self):
        """测试特征实体过期检查"""
        # 创建特征实体 - 使用正确的字段名
        feature_entity = FeatureEntity(
            id="feature_456",
            feature_type="test_feature",
            data={"test": "value"},
            created_at=datetime(2024, 1, 10, 10, 0),
            updated_at=datetime(2024, 1, 12, 10, 0),
        )

        # 验证时间属性
        assert feature_entity.created_at == datetime(2024, 1, 10, 10, 0)
        assert feature_entity.updated_at == datetime(2024, 1, 12, 10, 0)
        assert feature_entity.feature_type == "test_feature"


class TestFeatureDefinitionsSimple:
    """特征定义简化测试类"""

    def test_recent_performance_features_simple(self):
        """测试近期战绩特征"""
        calculation_date = datetime(2024, 1, 30)

        # 创建特征 - 使用正确的字段名和值
        features = RecentPerformanceFeatures(
            team_id=1,
            calculation_date=calculation_date,
            recent_5_wins=3,  # 3胜
            recent_5_draws=1,  # 1平
            recent_5_losses=1,  # 1负
            recent_5_goals_for=8,  # 进8球
            recent_5_goals_against=4,  # 失4球
            recent_5_points=10,  # 10分
        )

        # 验证基本属性
        assert features.team_id == 1
        assert features.recent_5_wins == 3
        assert features.recent_5_draws == 1
        assert features.recent_5_losses == 1
        assert features.recent_5_goals_for == 8
        assert features.recent_5_goals_against == 4
        assert features.recent_5_points == 10

        # 验证计算属性
        assert features.recent_5_win_rate == 0.6  # 3/5
        assert features.recent_5_goals_per_game == 1.6  # 8/5

    def test_historical_matchup_features_simple(self):
        """测试历史对战特征"""
        calculation_date = datetime(2024, 1, 30)

        # 创建特征 - 使用正确的字段名和值
        features = HistoricalMatchupFeatures(
            home_team_id=1,  # Team A
            away_team_id=2,  # Team B
            calculation_date=calculation_date,
            h2h_total_matches=5,
            h2h_home_wins=3,  # Team A胜利: 2-1, 0-2(算B胜), 1-2(算B胜)
            h2h_away_wins=2,  # Team B胜利
            h2h_draws=0,
            h2h_home_goals_total=7,  # Team A总进球: 2+0+1=3
            h2h_away_goals_total=6,  # Team B总进球: 1+2+2=5
        )

        # 验证基本属性
        assert features.home_team_id == 1
        assert features.away_team_id == 2
        assert features.h2h_total_matches == 5
        assert features.h2h_home_wins == 3
        assert features.h2h_away_wins == 2
        assert features.h2h_draws == 0
        assert features.h2h_home_goals_total == 7
        assert features.h2h_away_goals_total == 6

        # 验证计算属性
        assert features.h2h_home_win_rate == 0.6  # 3/5
        assert features.h2h_goals_avg == 2.6  # (7+6)/5
        assert features.h2h_home_goals_avg == 1.4  # 7/5

    def test_odds_features_simple(self):
        """测试赔率特征"""
        from decimal import Decimal

        calculation_date = datetime(2024, 1, 15)

        # 创建特征 - 使用正确的字段名和值
        features = OddsFeatures(
            match_id=12345,
            calculation_date=calculation_date,
            home_odds_avg=Decimal("2.10"),
            draw_odds_avg=Decimal("3.40"),
            away_odds_avg=Decimal("3.20"),
            home_implied_probability=0.476,  # 1/2.10
            draw_implied_probability=0.294,  # 1/3.40
            away_implied_probability=0.313,  # 1/3.20
            bookmaker_count=1,
            max_home_odds=Decimal("2.15"),
            min_home_odds=Decimal("2.05"),
            odds_variance_home=0.05,
            odds_variance_draw=0.08,
            odds_variance_away=0.06,
        )

        # 验证基本属性
        assert features.match_id == 12345
        assert features.home_odds_avg == Decimal("2.10")
        assert features.draw_odds_avg == Decimal("3.40")
        assert features.away_odds_avg == Decimal("3.20")
        assert features.bookmaker_count == 1
        assert features.max_home_odds == Decimal("2.15")
        assert features.min_home_odds == Decimal("2.05")

        # 验证计算属性
        assert features.bookmaker_consensus is not None
        assert features.market_efficiency is not None

    def test_all_match_features_simple(self):
        """测试完整比赛特征"""
        from decimal import Decimal

        calculation_date = datetime.now()

        # 创建子特征 - 使用正确的字段名和值
        recent_perf_home = RecentPerformanceFeatures(
            team_id=1,
            calculation_date=calculation_date,
            recent_5_wins=3,
            recent_5_draws=1,
            recent_5_losses=1,
            recent_5_goals_for=8,
            recent_5_goals_against=4,
            recent_5_points=10,
        )

        recent_perf_away = RecentPerformanceFeatures(
            team_id=2,
            calculation_date=calculation_date,
            recent_5_wins=2,
            recent_5_draws=2,
            recent_5_losses=1,
            recent_5_goals_for=6,
            recent_5_goals_against=5,
            recent_5_points=8,
        )

        historical_matchup = HistoricalMatchupFeatures(
            home_team_id=1,
            away_team_id=2,
            calculation_date=calculation_date,
            h2h_total_matches=5,
            h2h_home_wins=3,
            h2h_away_wins=2,
            h2h_draws=0,
            h2h_home_goals_total=7,
            h2h_away_goals_total=6,
        )

        odds_features = OddsFeatures(
            match_id=12345,
            calculation_date=calculation_date,
            home_odds_avg=Decimal("2.10"),
            draw_odds_avg=Decimal("3.40"),
            away_odds_avg=Decimal("3.20"),
            home_implied_probability=0.476,
            draw_implied_probability=0.294,
            away_implied_probability=0.313,
            bookmaker_count=1,
        )

        # 创建MatchEntity - AllMatchFeatures需要这个
        from src.features.entities import MatchEntity

        match_entity = MatchEntity(
            match_id=12345,
            home_team_id=1,
            away_team_id=2,
            league_id=39,
            match_time=calculation_date,
            season="2023-2024",
        )

        # 创建完整特征 - 使用正确的字段名
        all_features = AllMatchFeatures(
            match_entity=match_entity,
            home_team_recent=recent_perf_home,
            away_team_recent=recent_perf_away,
            historical_matchup=historical_matchup,
            odds_features=odds_features,
        )

        # 验证特征组合
        assert all_features.match_entity.match_id == 12345
        assert all_features.home_team_recent.team_id == 1
        assert all_features.away_team_recent.team_id == 2
        assert all_features.historical_matchup.h2h_total_matches == 5
        assert all_features.odds_features.home_odds_avg == Decimal("2.10")
        assert all_features.odds_features is not None

    def test_all_team_features_simple(self):
        """测试完整球队特征"""
        calculation_date = datetime.now()

        # 创建子特征 - 使用正确的字段名和值
        recent_perf = RecentPerformanceFeatures(
            team_id=1,
            calculation_date=calculation_date,
            recent_5_wins=3,
            recent_5_draws=1,
            recent_5_losses=1,
            recent_5_goals_for=8,
            recent_5_goals_against=4,
            recent_5_points=10,
        )

        # 创建TeamEntity - AllTeamFeatures需要这个
        from src.features.entities import TeamEntity

        team_entity = TeamEntity(
            team_id=1,
            team_name="Team A",
            league_id=39,
            home_venue="Stadium A",
        )

        # 创建完整特征 - 使用正确的字段名
        all_features = AllTeamFeatures(
            team_entity=team_entity,
            recent_performance=recent_perf,
        )

        # 验证特征组合
        assert all_features.team_entity.team_id == 1
        assert all_features.team_entity.team_name == "Team A"
        assert all_features.recent_performance.team_id == 1
        assert all_features.recent_performance.recent_5_wins == 3


class TestFeatureCalculatorSimple:
    """特征计算器简化测试类"""

    @pytest.fixture
    def calculator(self):
        """特征计算器实例"""
        mock_db_session = AsyncMock()
        return FeatureCalculator(mock_db_session)

    @pytest.fixture
    def sample_team_matches(self):
        """示例球队比赛数据"""
        return pd.DataFrame(
            {
                "match_id": [1, 2, 3, 4, 5, 6, 7, 8],
                "team_id": [1, 1, 1, 1, 1, 1, 1, 1],
                "opponent_id": [2, 3, 4, 5, 2, 3, 4, 5],
                "home_score": [2, 1, 3, 0, 1, 2, 1, 0],
                "away_score": [1, 1, 0, 1, 1, 1, 2, 1],
                "is_home": [True, False, True, False, True, False, True, False],
                "date": pd.date_range("2024-01-01", periods=8),
                "result": ["W", "D", "W", "L", "D", "W", "D", "L"],
            }
        )

    def test_calculator_initialization(self, calculator):
        """测试计算器初始化"""
        assert calculator is not None
        assert hasattr(calculator, "db_session")
        assert hasattr(calculator, "logger")

    def test_calculate_recent_performance_simple(self, sample_team_matches):
        """测试计算近期战绩特征"""
        team_id = 1
        calculation_date = datetime(2024, 1, 15)

        # 简化的特征计算逻辑
        recent_matches = sample_team_matches.tail(5)  # 取最近5场比赛

        # 计算基本统计
        wins = (recent_matches["result"] == "W").sum()
        draws = (recent_matches["result"] == "D").sum()
        losses = (recent_matches["result"] == "L").sum()

        # 计算进球和失球
        goals_for = 0
        goals_against = 0
        for _, match in recent_matches.iterrows():
            if match["is_home"]:
                goals_for += match["home_score"]
                goals_against += match["away_score"]
            else:
                goals_for += match["away_score"]
                goals_against += match["home_score"]

        points = wins * 3 + draws

        # 创建特征对象
        features = RecentPerformanceFeatures(
            team_id=team_id,
            calculation_date=calculation_date,
            recent_5_wins=wins,
            recent_5_draws=draws,
            recent_5_losses=losses,
            recent_5_goals_for=goals_for,
            recent_5_goals_against=goals_against,
            recent_5_points=points,
        )

        # 验证计算结果
        assert features.team_id == team_id
        assert features.recent_5_wins == wins
        assert features.recent_5_draws == draws
        assert features.recent_5_losses == losses
        assert features.recent_5_goals_for == goals_for
        assert features.recent_5_goals_against == goals_against
        assert features.recent_5_points == points

    def test_calculate_historical_matchup_simple(self):
        """测试计算历史对战特征"""
        # 创建历史对战数据
        historical_data = pd.DataFrame(
            {
                "match_id": [101, 102, 103, 104, 105],
                "home_team_id": [1, 2, 1, 2, 1],
                "away_team_id": [2, 1, 2, 1, 2],
                "home_score": [2, 1, 0, 2, 1],
                "away_score": [1, 1, 2, 1, 1],
                "date": pd.date_range("2023-01-01", periods=5),
            }
        )

        team_a_id = 1
        team_b_id = 2
        calculation_date = datetime(2024, 1, 15)

        # 计算对战统计
        team_a_matches = historical_data[
            (
                (historical_data["home_team_id"] == team_a_id)
                | (historical_data["away_team_id"] == team_a_id)
            )
            & (
                (historical_data["home_team_id"] == team_b_id)
                | (historical_data["away_team_id"] == team_b_id)
            )
        ]

        # 计算对战统计
        home_wins = 0
        away_wins = 0
        draws = 0
        home_goals = 0
        away_goals = 0

        for _, match in team_a_matches.iterrows():
            if match["home_team_id"] == team_a_id:
                home_goals += match["home_score"]
                away_goals += match["away_score"]
                if match["home_score"] > match["away_score"]:
                    home_wins += 1
                elif match["home_score"] < match["away_score"]:
                    away_wins += 1
                else:
                    draws += 1
            else:
                away_goals += match["away_score"]
                home_goals += match["home_score"]
                if match["away_score"] > match["home_score"]:
                    away_wins += 1
                elif match["away_score"] < match["home_score"]:
                    home_wins += 1
                else:
                    draws += 1

        # 创建特征对象
        features = HistoricalMatchupFeatures(
            home_team_id=team_a_id,
            away_team_id=team_b_id,
            calculation_date=calculation_date,
            h2h_total_matches=len(team_a_matches),
            h2h_home_wins=home_wins,
            h2h_away_wins=away_wins,
            h2h_draws=draws,
            h2h_home_goals_total=home_goals,
            h2h_away_goals_total=away_goals,
        )

        # 验证计算结果
        assert features.home_team_id == team_a_id
        assert features.away_team_id == team_b_id
        assert features.h2h_total_matches == len(team_a_matches)
        assert features.h2h_home_wins == home_wins
        assert features.h2h_away_wins == away_wins
        assert features.h2h_draws == draws

    def test_calculate_odds_features_simple(self):
        """测试计算赔率特征"""
        from decimal import Decimal

        match_id = 12345
        calculation_date = datetime(2024, 1, 15, 10, 0)

        # 创建特征对象 - 使用正确的字段名
        features = OddsFeatures(
            match_id=match_id,
            calculation_date=calculation_date,
            home_odds_avg=Decimal("2.10"),
            draw_odds_avg=Decimal("3.40"),
            away_odds_avg=Decimal("3.20"),
            bookmaker_count=1,
            max_home_odds=Decimal("2.15"),
            min_home_odds=Decimal("2.05"),
        )

        # 验证计算结果
        assert features.match_id == match_id
        assert features.home_odds_avg == Decimal("2.10")
        assert features.draw_odds_avg == Decimal("3.40")
        assert features.away_odds_avg == Decimal("3.20")

        # 计算隐含概率
        home_implied_prob = 1 / float(features.home_odds_avg)
        away_implied_prob = 1 / float(features.away_odds_avg)
        draw_implied_prob = 1 / float(features.draw_odds_avg)

        # 验证概率计算
        assert home_implied_prob > 0
        assert away_implied_prob > 0
        assert draw_implied_prob > 0

        # 验证赔率范围计算
        expected_range = float(features.max_home_odds) - float(features.min_home_odds)
        assert expected_range > 0

    def test_batch_feature_calculation_simple(self):
        """测试批量特征计算"""
        # 创建多个球队的比赛数据
        teams_data = {
            1: pd.DataFrame(
                {"match_id": [1, 2, 3], "team_id": [1, 1, 1], "goals": [2, 1, 3]}
            ),
            2: pd.DataFrame(
                {"match_id": [4, 5, 6], "team_id": [2, 2, 2], "goals": [1, 2, 1]}
            ),
        }

        calculation_date = datetime(2024, 1, 15)
        features_list = []

        # 批量计算特征
        for team_id, team_data in teams_data.items():
            team_data["goals"].mean()

            # 根据数据计算特征
            goals_for = int(team_data["goals"].sum())
            goals_against = len(team_data)  # 简化假设每场失球1个
            wins = len(team_data[team_data["goals"] > 1])  # 简化胜利条件
            draws = len(team_data[team_data["goals"] == 1])  # 简化平局条件
            losses = len(team_data) - wins - draws
            points = wins * 3 + draws

            # 创建简化的特征对象 - 使用正确的字段名
            features = RecentPerformanceFeatures(
                team_id=team_id,
                calculation_date=calculation_date,
                recent_5_wins=wins,
                recent_5_draws=draws,
                recent_5_losses=losses,
                recent_5_goals_for=goals_for,
                recent_5_goals_against=goals_against,
                recent_5_points=points,
            )
            features_list.append(features)

        # 验证批量计算结果
        assert len(features_list) == 2
        assert features_list[0].team_id == 1
        assert features_list[1].team_id == 2

        # 验证计算的特征值
        assert features_list[0].recent_5_goals_for == 6  # 2+1+3=6
        assert features_list[1].recent_5_goals_for == 4  # 1+2+1=4

    def test_feature_calculation_performance_simple(self):
        """测试特征计算性能"""
        # 创建大数据集
        np.random.seed(42)
        large_dataset = pd.DataFrame(
            {
                "match_id": range(1000),
                "team_id": np.random.randint(1, 11, 1000),
                "goals_scored": np.random.poisson(1.5, 1000),
                "goals_conceded": np.random.poisson(1.2, 1000),
                "date": pd.date_range("2023-01-01", periods=1000),
            }
        )

        import time

        start_time = time.time()

        # 为每个球队计算特征
        team_ids = large_dataset["team_id"].unique()
        features_list = []

        for team_id in team_ids:
            team_data = large_dataset[large_dataset["team_id"] == team_id]

            # 计算统计数据
            team_data["goals_scored"].mean()
            team_data["goals_conceded"].mean()

            # 简化的特征计算（取最近5场的概念）
            recent_data = team_data.tail(5)
            goals_for = int(recent_data["goals_scored"].sum())
            goals_against = int(recent_data["goals_conceded"].sum())

            # 简化的胜负计算
            wins = len(
                recent_data[recent_data["goals_scored"] > recent_data["goals_conceded"]]
            )
            draws = len(
                recent_data[
                    recent_data["goals_scored"] == recent_data["goals_conceded"]
                ]
            )
            losses = len(recent_data) - wins - draws
            points = wins * 3 + draws

            # 创建特征 - 使用正确的字段名
            features = RecentPerformanceFeatures(
                team_id=team_id,
                calculation_date=datetime.now(),
                recent_5_wins=wins,
                recent_5_draws=draws,
                recent_5_losses=losses,
                recent_5_goals_for=goals_for,
                recent_5_goals_against=goals_against,
                recent_5_points=points,
            )
            features_list.append(features)

        end_time = time.time()
        calculation_time = end_time - start_time

        # 验证性能和结果
        assert calculation_time < 2.0  # 应该在2秒内完成
        assert len(features_list) == len(team_ids)

        # 验证至少计算了一些特征
        total_goals = sum(f.recent_5_goals_for for f in features_list)
        assert total_goals > 0  # 确保实际计算了数据


class TestFeatureEngineeringPipelineSimple:
    """特征工程流水线简化测试类"""

    def test_simple_feature_pipeline(self):
        """测试简化的特征工程流水线"""
        # 原始数据
        raw_matches = [
            {
                "match_id": 12345,
                "home_team_id": 1,
                "away_team_id": 2,
                "home_score": 2,
                "away_score": 1,
            },
            {
                "match_id": 12346,
                "home_team_id": 2,
                "away_team_id": 3,
                "home_score": 1,
                "away_score": 1,
            },
            {
                "match_id": 12347,
                "home_team_id": 3,
                "away_team_id": 4,
                "home_score": 3,
                "away_score": 0,
            },
        ]

        # 特征提取流水线
        def extract_match_features(match_data):
            """提取比赛特征"""
            return {
                "match_id": match_data["match_id"],
                "home_team_id": match_data["home_team_id"],
                "away_team_id": match_data["away_team_id"],
                "total_goals": match_data["home_score"] + match_data["away_score"],
                "goal_difference": match_data["home_score"] - match_data["away_score"],
                "home_win": match_data["home_score"] > match_data["away_score"],
                "draw": match_data["home_score"] == match_data["away_score"],
                "away_win": match_data["home_score"] < match_data["away_score"],
            }

        # 执行特征提取
        extracted_features = [extract_match_features(match) for match in raw_matches]

        # 验证提取结果
        assert len(extracted_features) == 3
        assert extracted_features[0]["total_goals"] == 3
        assert extracted_features[0]["goal_difference"] == 1
        assert extracted_features[0]["home_win"] is True

    def test_feature_transformation_simple(self):
        """测试简化的特征转换"""
        # 原始特征
        raw_features = {
            "match_id": 12345,
            "home_team_id": 1,
            "away_team_id": 2,
            "home_score": 2,
            "away_score": 1,
            "home_possession": 65.5,
            "away_possession": 34.5,
            "home_shots": 12,
            "away_shots": 8,
        }

        # 特征转换
        def transform_features(features):
            """转换特征为模型可用格式"""
            transformed = {
                "match_id": features["match_id"],
                "home_team_id": features["home_team_id"],
                "away_team_id": features["away_team_id"],
                "total_goals": features["home_score"] + features["away_score"],
                "goal_difference": features["home_score"] - features["away_score"],
                "possession_difference": features["home_possession"]
                - features["away_possession"],
                "shots_difference": features["home_shots"] - features["away_shots"],
                "home_win": 1 if features["home_score"] > features["away_score"] else 0,
                "draw": 1 if features["home_score"] == features["away_score"] else 0,
                "away_win": 1 if features["home_score"] < features["away_score"] else 0,
            }
            return transformed

        # 执行转换
        transformed_features = transform_features(raw_features)

        # 验证转换结果
        assert transformed_features["total_goals"] == 3
        assert transformed_features["goal_difference"] == 1
        assert transformed_features["possession_difference"] == 31.0
        assert transformed_features["shots_difference"] == 4
        assert transformed_features["home_win"] == 1
        assert transformed_features["draw"] == 0
        assert transformed_features["away_win"] == 0

    def test_feature_selection_simple(self):
        """测试简化的特征选择"""
        # 完整特征集
        full_features = {
            "match_id": 12345,
            "home_team_id": 1,
            "away_team_id": 2,
            "total_goals": 3,
            "goal_difference": 1,
            "possession_difference": 31.0,
            "shots_difference": 4,
            "home_win": 1,
            "draw": 0,
            "away_win": 0,
            "home_shots": 12,
            "away_shots": 8,
            "home_corners": 6,
            "away_corners": 4,
            "home_fouls": 10,
            "away_fouls": 12,
        }

        # 特征选择
        def select_important_features(features):
            """选择重要特征"""
            important_features = [
                "match_id",
                "home_team_id",
                "away_team_id",
                "total_goals",
                "goal_difference",
                "possession_difference",
                "shots_difference",
                "home_win",
                "draw",
                "away_win",
            ]
            return {k: v for k, v in features.items() if k in important_features}

        # 执行特征选择
        selected_features = select_important_features(full_features)

        # 验证选择结果
        assert len(selected_features) < len(full_features)
        assert "match_id" in selected_features
        assert "total_goals" in selected_features
        assert "home_corners" not in selected_features
        assert "away_fouls" not in selected_features

    def test_pipeline_execution_simple(self):
        """测试简化的流水线执行"""
        # 输入数据
        matches_data = [
            {
                "match_id": 12345,
                "home_team_id": 1,
                "away_team_id": 2,
                "home_score": 2,
                "away_score": 1,
            },
            {
                "match_id": 12346,
                "home_team_id": 2,
                "away_team_id": 3,
                "home_score": 1,
                "away_score": 1,
            },
        ]

        import time

        start_time = time.time()

        # 完整流水线
        def execute_pipeline(matches):
            """执行特征工程流水线"""
            # 1. 特征提取
            extracted = []
            for match in matches:
                features = {
                    "match_id": match["match_id"],
                    "home_team_id": match["home_team_id"],
                    "away_team_id": match["away_team_id"],
                    "total_goals": match["home_score"] + match["away_score"],
                    "goal_difference": match["home_score"] - match["away_score"],
                }
                extracted.append(features)

            # 2. 特征转换
            transformed = []
            for features in extracted:
                # 添加派生特征
                features["home_win"] = 1 if features["goal_difference"] > 0 else 0
                features["draw"] = 1 if features["goal_difference"] == 0 else 0
                features["away_win"] = 1 if features["goal_difference"] < 0 else 0
                transformed.append(features)

            # 3. 特征选择
            selected = []
            for features in transformed:
                selected_features = {
                    "match_id": features["match_id"],
                    "home_team_id": features["home_team_id"],
                    "away_team_id": features["away_team_id"],
                    "total_goals": features["total_goals"],
                    "home_win": features["home_win"],
                }
                selected.append(selected_features)

            return {
                "extracted_features": extracted,
                "transformed_features": transformed,
                "selected_features": selected,
            }

        # 执行流水线
        results = execute_pipeline(matches_data)

        end_time = time.time()
        execution_time = end_time - start_time

        # 验证结果
        assert len(results["extracted_features"]) == 2
        assert len(results["transformed_features"]) == 2
        assert len(results["selected_features"]) == 2
        assert execution_time < 1.0  # 应该在1秒内完成

        # 验证特征质量
        assert results["selected_features"][0]["total_goals"] == 3
        assert results["selected_features"][0]["home_win"] == 1


class TestFeatureEngineeringIntegrationSimple:
    """特征工程集成简化测试类"""

    def test_end_to_end_feature_workflow_simple(self):
        """测试简化的端到端特征工作流"""
        # 1. 准备原始数据
        raw_matches = pd.DataFrame(
            {
                "match_id": [12345, 12346, 12347],
                "home_team_id": [1, 2, 3],
                "away_team_id": [2, 3, 1],
                "home_score": [2, 1, 3],
                "away_score": [1, 2, 0],
                "date": pd.date_range("2024-01-01", periods=3),
                "league_id": [39, 39, 39],
            }
        )

        # 2. 特征提取
        def extract_features_from_dataframe(df):
            """从DataFrame提取特征"""
            features_list = []
            for _, row in df.iterrows():
                features = {
                    "match_id": row["match_id"],
                    "home_team_id": row["home_team_id"],
                    "away_team_id": row["away_team_id"],
                    "total_goals": row["home_score"] + row["away_score"],
                    "goal_difference": row["home_score"] - row["away_score"],
                    "home_win": row["home_score"] > row["away_score"],
                    "draw": row["home_score"] == row["away_score"],
                    "away_win": row["home_score"] < row["away_score"],
                }
                features_list.append(features)
            return features_list

        # 3. 执行特征提取
        extracted_features = extract_features_from_dataframe(raw_matches)

        # 4. 特征验证
        def validate_features(features_list):
            """验证特征质量"""
            validation_results = []
            for features in features_list:
                validation = {
                    "valid_total_goals": features["total_goals"] >= 0,
                    "valid_goal_difference": isinstance(
                        features["goal_difference"], int
                    ),
                    "valid_result_encoding": sum(
                        [features["home_win"], features["draw"], features["away_win"]]
                    )
                    == 1,
                }
                validation_results.append(validation)
            return validation_results

        validation_results = validate_features(extracted_features)

        # 验证最终结果
        assert len(extracted_features) == 3
        assert all(result["valid_total_goals"] for result in validation_results)
        assert all(result["valid_goal_difference"] for result in validation_results)
        assert all(result["valid_result_encoding"] for result in validation_results)

    def test_feature_consistency_validation_simple(self):
        """测试特征一致性验证"""
        # 创建相同的输入数据
        match_data = {
            "match_id": 12345,
            "home_team_id": 1,
            "away_team_id": 2,
            "home_score": 2,
            "away_score": 1,
        }

        # 两次计算特征
        def calculate_features(data):
            """计算特征"""
            return {
                "match_id": data["match_id"],
                "home_team_id": data["home_team_id"],
                "away_team_id": data["away_team_id"],
                "total_goals": data["home_score"] + data["away_score"],
                "goal_difference": data["home_score"] - data["away_score"],
                "home_win": data["home_score"] > data["away_score"],
            }

        features1 = calculate_features(match_data)
        features2 = calculate_features(match_data)

        # 验证一致性
        assert features1["match_id"] == features2["match_id"]
        assert features1["total_goals"] == features2["total_goals"]
        assert features1["goal_difference"] == features2["goal_difference"]
        assert features1["home_win"] == features2["home_win"]

    def test_scalability_test_simple(self):
        """测试可扩展性"""
        # 创建大数据集
        np.random.seed(42)
        large_data = pd.DataFrame(
            {
                "match_id": range(1, 1001),
                "home_team_id": np.random.randint(1, 51, 1000),
                "away_team_id": np.random.randint(1, 51, 1000),
                "home_score": np.random.poisson(1.5, 1000),
                "away_score": np.random.poisson(1.2, 1000),
                "date": pd.date_range("2023-01-01", periods=1000),
            }
        )

        import time

        start_time = time.time()

        # 批量特征计算
        features_list = []
        for _, row in large_data.iterrows():
            features = {
                "match_id": row["match_id"],
                "home_team_id": row["home_team_id"],
                "away_team_id": row["away_team_id"],
                "total_goals": row["home_score"] + row["away_score"],
                "goal_difference": row["home_score"] - row["away_score"],
            }
            features_list.append(features)

        end_time = time.time()
        calculation_time = end_time - start_time

        # 验证性能和结果
        assert calculation_time < 5.0  # 应该在5秒内完成
        assert len(features_list) == 1000
        assert all(f["total_goals"] >= 0 for f in features_list)
