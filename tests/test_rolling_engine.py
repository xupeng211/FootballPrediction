#!/usr/bin/env python3
"""
V17.0 滚动特征引擎回归测试
验证滚动均值计算的准确性和无数据泄露
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.pipeline import V17ProductionPipeline
from src.ml.engine import V17MLEngine


class TestRollingFeatureCalculation:
    """测试滚动特征计算的正确性"""

    @pytest.fixture
    def sample_match_history(self):
        """
        创建 3 场模拟比赛历史数据

        时间顺序:
        - Match 1 (2023-08-11): Arsenal vs Liverpool (1-1, Draw)
          Arsenal: xg=1.2, shots=5, possession=55, rating=6.8
          Liverpool: xg=0.9, shots=3, possession=45, rating=6.5

        - Match 2 (2023-08-12): Man City vs Arsenal (3-1, Home)
          Man City: xg=2.5, shots=8, possession=65, rating=7.5
          Arsenal: xg=0.8, shots=2, possession=35, rating=6.2

        - Match 3 (2023-08-13): Liverpool vs Chelsea (2-0, Home)
          Liverpool: xg=1.8, shots=6, possession=58, rating=7.1
          Chelsea: xg=0.5, shots=1, possession=42, rating=6.0

        用于测试: 预测 Match 4 (Arsenal vs Liverpool)
        """
        return pd.DataFrame(
            [
                {
                    "external_id": "4193450",
                    "home_team": "Arsenal",
                    "away_team": "Liverpool",
                    "match_time": "2023-08-11 15:00:00+00:00",
                    "home_score": 1,
                    "away_score": 1,
                    "actual_result": "D",
                    "parsed_stats": {
                        "home_xg": 1.2,
                        "away_xg": 0.9,
                        "home_shots_on_target": 5,
                        "away_shots_on_target": 3,
                        "home_possession": 55,
                        "away_possession": 45,
                        "home_team_rating": 6.8,
                        "away_team_rating": 6.5,
                    },
                },
                {
                    "external_id": "4193451",
                    "home_team": "Man City",
                    "away_team": "Arsenal",
                    "match_time": "2023-08-12 15:00:00+00:00",
                    "home_score": 3,
                    "away_score": 1,
                    "actual_result": "H",
                    "parsed_stats": {
                        "home_xg": 2.5,
                        "away_xg": 0.8,
                        "home_shots_on_target": 8,
                        "away_shots_on_target": 2,
                        "home_possession": 65,
                        "away_possession": 35,
                        "home_team_rating": 7.5,
                        "away_team_rating": 6.2,
                    },
                },
                {
                    "external_id": "4193452",
                    "home_team": "Liverpool",
                    "away_team": "Chelsea",
                    "match_time": "2023-08-13 15:00:00+00:00",
                    "home_score": 2,
                    "away_score": 0,
                    "actual_result": "H",
                    "parsed_stats": {
                        "home_xg": 1.8,
                        "away_xg": 0.5,
                        "home_shots_on_target": 6,
                        "away_shots_on_target": 1,
                        "home_possession": 58,
                        "away_possession": 42,
                        "home_team_rating": 7.1,
                        "away_team_rating": 6.0,
                    },
                },
            ]
        )

    @pytest.fixture
    def engine(self):
        """创建 ML 引擎实例"""
        return V17MLEngine()

    def test_team_history_building(self, sample_match_history, engine):
        """测试球队历史数据构建"""
        team_history = engine.build_team_history(sample_match_history)

        # 验证所有球队都被包含
        assert "Arsenal" in team_history
        assert "Liverpool" in team_history
        assert "Man City" in team_history
        assert "Chelsea" in team_history

        # 验证 Arsenal 的历史 (2 场比赛)
        arsenal_history = team_history["Arsenal"]
        assert len(arsenal_history) == 2
        assert arsenal_history.iloc[0]["external_id"] == "4193450"  # vs Liverpool
        assert arsenal_history.iloc[0]["is_home"] == True
        assert arsenal_history.iloc[1]["external_id"] == "4193451"  # vs Man City
        assert arsenal_history.iloc[1]["is_home"] == False

        # 验证数据按时间排序
        assert all(arsenal_history["match_time"].sort_values() == arsenal_history["match_time"])

    def test_rolling_feature_calculation_window_10(self, sample_match_history, engine):
        """测试滚动特征计算 (window=10，超过历史数据量)"""
        team_history = engine.build_team_history(sample_match_history)

        # 计算 Arsenal vs Liverpool 的滚动特征
        features = engine.calculate_single_rolling_feature(
            team_history, home_team="Arsenal", away_team="Liverpool", match_time="2023-08-14 15:00:00+00:00", window=10
        )

        # Arsenal 历史: 2 场 (vs Liverpool 主场, vs Man City 客场)
        # 主队统计: xg=1.2, shots=5, possession=55, rating=6.8
        # 客队统计: xg=0.8, shots=2, possession=35, rating=6.2
        # 均值: xg=1.0, shots=3.5, possession=45, rating=6.5
        assert features["home_matches_count"] == 2
        assert abs(features["home_rolling_xg"] - 1.0) < 0.01
        assert abs(features["home_rolling_shots_on_target"] - 3.5) < 0.01
        assert abs(features["home_rolling_possession"] - 45.0) < 0.01
        assert abs(features["home_rolling_team_rating"] - 6.5) < 0.01

        # Liverpool 历史: 2 场 (vs Arsenal 客场, vs Chelsea 主场)
        # 客队统计: xg=0.9, shots=3, possession=45, rating=6.5
        # 主队统计: xg=1.8, shots=6, possession=58, rating=7.1
        # 均值: xg=1.35, shots=4.5, possession=51.5, rating=6.8
        assert features["away_matches_count"] == 2
        assert abs(features["away_rolling_xg"] - 1.35) < 0.01
        assert abs(features["away_rolling_shots_on_target"] - 4.5) < 0.01
        assert abs(features["away_rolling_possession"] - 51.5) < 0.01
        assert abs(features["away_rolling_team_rating"] - 6.8) < 0.01

    def test_rolling_feature_calculation_window_1(self, sample_match_history, engine):
        """测试滚动特征计算 (window=1，只用最近一场)"""
        team_history = engine.build_team_history(sample_match_history)

        # 计算 Arsenal vs Liverpool 的滚动特征 (window=1)
        features = engine.calculate_single_rolling_feature(
            team_history, home_team="Arsenal", away_team="Liverpool", match_time="2023-08-14 15:00:00+00:00", window=1
        )

        # Arsenal 最近一场: vs Man City (客场)
        # xg=0.8, shots=2, possession=35, rating=6.2
        assert features["home_matches_count"] == 1
        assert abs(features["home_rolling_xg"] - 0.8) < 0.01
        assert abs(features["home_rolling_shots_on_target"] - 2.0) < 0.01
        assert abs(features["home_rolling_possession"] - 35.0) < 0.01
        assert abs(features["home_rolling_team_rating"] - 6.2) < 0.01

        # Liverpool 最近一场: vs Chelsea (主场)
        # xg=1.8, shots=6, possession=58, rating=7.1
        assert features["away_matches_count"] == 1
        assert abs(features["away_rolling_xg"] - 1.8) < 0.01
        assert abs(features["away_rolling_shots_on_target"] - 6.0) < 0.01
        assert abs(features["away_rolling_possession"] - 58.0) < 0.01
        assert abs(features["away_rolling_team_rating"] - 7.1) < 0.01

    def test_no_data_leakage(self, sample_match_history, engine):
        """测试无数据泄露：滚动特征不包含当前比赛数据"""
        team_history = engine.build_team_history(sample_match_history)

        # 添加第 4 场比赛
        match_4 = pd.DataFrame(
            [
                {
                    "external_id": "4193453",
                    "home_team": "Arsenal",
                    "away_team": "Liverpool",
                    "match_time": "2023-08-14 15:00:00+00:00",
                    "home_score": 2,
                    "away_score": 1,
                    "actual_result": "H",
                    "parsed_stats": {
                        "home_xg": 2.5,  # 当前比赛的 xG (高)
                        "away_xg": 0.7,  # 当前比赛的 xG (低)
                        "home_shots_on_target": 10,
                        "away_shots_on_target": 2,
                        "home_possession": 70,
                        "away_possession": 30,
                        "home_team_rating": 8.0,
                        "away_team_rating": 6.0,
                    },
                }
            ]
        )

        extended_history = pd.concat([sample_match_history, match_4], ignore_index=True)
        team_history = engine.build_team_history(extended_history)

        # 计算 Arsenal vs Liverpool 的滚动特征
        # 应该只使用前 3 场比赛的数据，不包含第 4 场
        features = engine.calculate_single_rolling_feature(
            team_history, home_team="Arsenal", away_team="Liverpool", match_time="2023-08-14 15:00:00+00:00", window=10
        )

        # 验证滚动特征不等于第 4 场的实际值
        assert features["home_rolling_xg"] != 2.5, "滚动特征不应包含当前比赛数据！"
        assert features["away_rolling_xg"] != 0.7, "滚动特征不应包含当前比赛数据！"

        # 验证滚动特征是基于历史数据计算的
        # Arsenal 历史 (前2场): xg均值 = 1.0
        assert abs(features["home_rolling_xg"] - 1.0) < 0.01, "滚动特征应基于历史数据"
        # Liverpool 历史 (前2场): xg均值 = 1.35
        assert abs(features["away_rolling_xg"] - 1.35) < 0.01, "滚动特征应基于历史数据"

    def test_std_calculation(self, sample_match_history, engine):
        """测试标准差计算"""
        team_history = engine.build_team_history(sample_match_history)

        features = engine.calculate_single_rolling_feature(
            team_history, home_team="Arsenal", away_team="Liverpool", match_time="2023-08-14 15:00:00+00:00", window=10
        )

        # Arsenal xG: [1.2, 0.8]
        # 均值 = 1.0, 标准差 = sqrt(((1.2-1)^2 + (0.8-1)^2) / 2) = sqrt(0.04) = 0.2
        expected_std = np.std([1.2, 0.8])
        assert abs(features["home_rolling_xg_std"] - expected_std) < 0.01

    def test_feature_names_completeness(self, engine):
        """测试特征名称完整性"""
        # 验证 16 个特征都存在
        expected_count = 16  # 4 metrics × home/away × mean/std
        assert len(engine.ROLLING_FEATURES) == expected_count

        # 验证特征命名规范
        for feature in engine.ROLLING_FEATURES:
            assert feature.startswith("home_rolling_") or feature.startswith("away_rolling_")

        # 验证所有核心指标都有均值和标准差
        for metric in engine.CORE_METRICS:
            assert f"home_rolling_{metric}" in engine.ROLLING_FEATURES
            assert f"home_rolling_{metric}_std" in engine.ROLLING_FEATURES
            assert f"away_rolling_{metric}" in engine.ROLLING_FEATURES
            assert f"away_rolling_{metric}_std" in engine.ROLLING_FEATURES

    def test_label_mapping(self, engine):
        """测试标签映射"""
        assert engine.label_mapping == {"A": 0, "D": 1, "H": 2}
        assert engine.reverse_mapping == {0: "A", 1: "D", 2: "H"}

    def test_prepare_dataset_filtering(self, sample_match_history, engine):
        """测试数据集准备时的过滤逻辑"""
        # 创建滚动特征
        team_history = engine.build_team_history(sample_match_history)
        rolling_features = []

        for idx, row in sample_match_history.iterrows():
            features = engine.calculate_single_rolling_feature(
                team_history, row["home_team"], row["away_team"], row["match_time"], window=10
            )
            features["match_id"] = row["external_id"]
            rolling_features.append(features)

        rolling_df = pd.DataFrame(rolling_features)

        # 测试过滤: min_history=1 应该过滤掉第一场比赛（双方都没有历史）
        X, y = engine.prepare_dataset(sample_match_history, rolling_df, min_history=1)

        # 第一场比赛应该被过滤
        assert len(X) < len(sample_match_history)

        # 验证特征列正确
        assert list(X.columns) == engine.ROLLING_FEATURES


class TestV17ProductionPipeline:
    """测试 V17.0 生产流水线"""

    @pytest.fixture
    def pipeline(self):
        """创建流水线实例"""
        return V17ProductionPipeline()

    def test_pipeline_initialization(self, pipeline):
        """测试流水线初始化"""
        assert pipeline.db_config is not None
        assert pipeline.label_mapping == {"A": 0, "D": 1, "H": 2}
        assert len(pipeline.ROLLING_FEATURES) == 16

    def test_default_xgb_params(self):
        """测试默认 XGBoost 参数"""
        from src.ml.engine import V17MLEngine

        engine = V17MLEngine()

        params = V17MLEngine.DEFAULT_XGB_PARAMS
        assert params["n_estimators"] == 200
        assert params["max_depth"] == 4
        assert params["learning_rate"] == 0.05
        assert params["reg_alpha"] == 0.5
        assert params["reg_lambda"] == 1.0


class TestDataLeakagePrevention:
    """测试数据泄露防护"""

    def test_time_strict_filtering(self):
        """测试时间严格过滤：只使用当前比赛之前的数据"""
        # 创建测试数据
        df = pd.DataFrame(
            [
                {
                    "external_id": "001",
                    "home_team": "TeamA",
                    "away_team": "TeamB",
                    "match_time": "2023-08-11 15:00:00+00:00",
                    "parsed_stats": {"home_xg": 1.0, "away_xg": 0.5},
                },
                {
                    "external_id": "002",
                    "home_team": "TeamA",
                    "away_team": "TeamC",
                    "match_time": "2023-08-12 15:00:00+00:00",
                    "parsed_stats": {"home_xg": 1.5, "away_xg": 0.8},
                },
                {
                    "external_id": "003",
                    "home_team": "TeamA",
                    "away_team": "TeamD",
                    "match_time": "2023-08-13 15:00:00+00:00",
                    "parsed_stats": {"home_xg": 2.0, "away_xg": 1.0},
                },
            ]
        )

        engine = V17MLEngine()
        team_history = engine.build_team_history(df)

        # 计算 003 号比赛的滚动特征
        features = engine.calculate_single_rolling_feature(
            team_history, home_team="TeamA", away_team="TeamD", match_time="2023-08-13 15:00:00+00:00", window=10
        )

        # TeamA 在 003 之前的比赛: 001 (xg=1.0), 002 (xg=1.5)
        # 均值 = 1.25，不应该包含 003 的 xg=2.0
        assert abs(features["home_rolling_xg"] - 1.25) < 0.01
        assert features["home_rolling_xg"] != 2.0, "不应包含当前比赛的 xG！"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
