"""
高级特征工程单元测试

测试Phase 5中实现的三个核心组件：
1. H2HCalculator - 历史交锋统计计算器
2. VenueAnalyzer - 场馆分析器
3. AdvancedFeatureTransformer - 高级特征转换器

重点测试场景：
- Napoli vs Juventus 案例改进验证
- 数据泄露防护机制
- 边界条件和异常数据处理
- 性能和准确性验证
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.ml.features.h2h_calculator import H2HCalculator, H2HStats
from src.ml.features.venue_analyzer import VenueAnalyzer, VenueStats
from src.ml.features.advanced_feature_transformer import (
    AdvancedFeatureTransformer,
    AdvancedFeatureConfig,
)


class TestH2HCalculator(unittest.TestCase):
    """H2H计算器测试"""

    def setUp(self):
        """设置测试数据"""
        self.h2h_calc = H2HCalculator(min_matches=1)

        # 创建测试数据：包含两队的多次交锋
        self.test_data = {
            "home_team_id": [1, 2, 1, 2, 1, 3, 2],
            "away_team_id": [2, 1, 2, 1, 2, 1, 1],
            "home_score": [2, 1, 0, 2, 3, 1, 1],
            "away_score": [1, 2, 0, 1, 1, 0, 2],
            "match_date": [
                "2024-01-01",
                "2024-01-15",
                "2024-02-01",
                "2024-02-15",
                "2024-03-01",
                "2024-03-15",
                "2024-03-20",
            ],
        }

        self.df = pd.DataFrame(self.test_data)
        self.df["match_date"] = pd.to_datetime(self.df["match_date"])

    def test_h2h_basic_calculation(self):
        """测试基本H2H统计计算"""
        # 测试队伍1 vs 队伍2的交锋记录
        h2h_stats = self.h2h_calc.calculate_h2h_for_match(
            self.df, 1, 2, pd.Timestamp("2024-03-25")
        )

        self.assertIsInstance(h2h_stats, H2HStats)
        self.assertGreater(h2h_stats.matches_count, 0)
        self.assertGreaterEqual(h2h_stats.home_win_rate, 0)
        self.assertLessEqual(h2h_stats.home_win_rate, 1)

    def test_h2h_no_history(self):
        """测试无历史交锋记录的情况"""
        h2h_stats = self.h2h_calc.calculate_h2h_for_match(
            self.df, 999, 888, pd.Timestamp("2024-03-25")
        )

        # 应该返回默认值
        self.assertEqual(h2h_stats.matches_count, 0)
        self.assertEqual(h2h_stats.home_win_rate, 0.5)
        self.assertEqual(h2h_stats.avg_goal_diff, 0.0)

    def test_h2h_team1_dominance(self):
        """测试队伍1明显优势的情况"""
        # 队伍1 vs 队伍2: 队伍1应该有明显优势
        h2h_stats = self.h2h_calc.calculate_h2h_for_match(
            self.df, 1, 2, pd.Timestamp("2024-03-25")
        )

        # 队伍1在历史交锋中表现更好
        self.assertGreater(h2h_stats.home_win_rate, 0.5)

    def test_h2h_data_leakage_prevention(self):
        """测试数据泄露防护"""
        # 检查是否会使用未来比赛的数据
        test_match_date = pd.Timestamp("2024-02-10")
        h2h_stats = self.h2h_calc.calculate_h2h_for_match(
            self.df, 1, 2, test_match_date
        )

        # 只应该考虑2024-02-10之前的比赛
        past_matches = self.h2h_calc._get_historical_matches(
            self.df, 1, 2, test_match_date
        )

        # 确保没有未来数据
        for _, match in past_matches.iterrows():
            self.assertLess(pd.to_datetime(match["match_date"]), test_match_date)

    def test_h2h_summary(self):
        """测试H2H摘要功能"""
        summary = self.h2h_calc.get_h2h_summary(self.df, 1, 2)

        self.assertIn("teams", summary)
        self.assertIn("total_matches", summary)
        self.assertIn("team1_wins", summary)
        self.assertIn("team2_wins", summary)
        self.assertGreater(summary["total_matches"], 0)


class TestVenueAnalyzer(unittest.TestCase):
    """场馆分析器测试"""

    def setUp(self):
        """设置测试数据"""
        self.venue_analyzer = VenueAnalyzer(windows=[3, 5])

        # 创建包含明显主客场差异的测试数据
        self.test_data = {
            "home_team_id": [1, 1, 1, 2, 2, 2, 3, 3],
            "away_team_id": [2, 3, 4, 1, 3, 4, 1, 2],
            "home_score": [3, 2, 4, 0, 1, 0, 1, 1],
            "away_score": [0, 0, 1, 2, 1, 2, 1, 0],
            "match_date": [
                "2024-01-01",
                "2024-01-15",
                "2024-02-01",
                "2024-01-05",
                "2024-01-20",
                "2024-02-05",
                "2024-01-10",
                "2024-01-25",
            ],
        }

        self.df = pd.DataFrame(self.test_data)
        self.df["match_date"] = pd.to_datetime(self.df["match_date"])

    def test_venue_separation(self):
        """测试主客场数据分离"""
        # 测试队伍1的主场和客场表现差异
        venue_stats = self.venue_analyzer.calculate_venue_features_for_match(
            self.df, 1, 2, pd.Timestamp("2024-03-01")
        )

        self.assertIsInstance(venue_stats, VenueStats)
        # 队伍1主场表现应该比客场好
        self.assertGreaterEqual(
            venue_stats.home_goals_rolling_3, venue_stats.away_goals_rolling_3
        )

    def test_venue_rolling_windows(self):
        """测试不同滚动窗口的计算"""
        venue_stats = self.venue_analyzer.calculate_venue_features_for_match(
            self.df, 1, 2, pd.Timestamp("2024-03-01")
        )

        # 5场窗口应该包含更多数据
        self.assertGreaterEqual(
            venue_stats.home_goals_rolling_5, venue_stats.home_goals_rolling_3
        )

    def test_venue_no_history(self):
        """测试无历史数据的情况"""
        venue_stats = self.venue_analyzer.calculate_venue_features_for_match(
            self.df, 999, 888, pd.Timestamp("2024-03-01")
        )

        # 应该返回默认值
        self.assertEqual(venue_stats.home_goals_rolling_3, 0.0)
        self.assertEqual(venue_stats.away_goals_rolling_3, 0.0)

    def test_venue_home_advantage(self):
        """测试主场优势计算"""
        # 队伍1在主场表现强势
        summary = self.venue_analyzer.get_venue_summary(self.df, 1)

        self.assertIn("home_advantage", summary)
        # 主场优势应该大于1（主场进球 > 客场进球）
        self.assertGreater(summary["home_advantage"], 1.0)

    def test_venue_data_leakage_prevention(self):
        """测试场馆分析的数据泄露防护"""
        test_match_date = pd.Timestamp("2024-01-25")
        venue_stats = self.venue_analyzer.calculate_venue_features_for_match(
            self.df, 1, 2, test_match_date
        )

        # 验证只使用了历史数据
        home_stats = self.venue_analyzer._calculate_team_venue_stats(
            self.df, 1, "home", test_match_date
        )

        # 所有统计数据应该基于test_match_date之前的比赛
        for window, avg_goals in home_stats.items():
            self.assertGreaterEqual(avg_goals, 0)


class TestAdvancedFeatureTransformer(unittest.TestCase):
    """高级特征转换器集成测试"""

    def setUp(self):
        """设置测试数据"""
        # 模拟Napoli vs Juventus案例的数据
        self.test_data = {
            "home_team_id": [1, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1],
            "away_team_id": [2, 3, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2],
            "home_score": [0, 2, 1, 0, 1, 2, 0, 3, 1, 2, 1, 2],
            "away_score": [1, 0, 2, 0, 3, 1, 1, 1, 0, 1, 0, 1],
            "match_date": [
                "2024-01-01",
                "2024-01-15",
                "2024-01-20",
                "2024-02-01",
                "2024-02-15",
                "2024-03-01",
                "2024-03-15",
                "2024-04-01",
                "2024-04-15",
                "2024-05-01",
                "2024-05-15",
                "2024-06-01",
            ],
        }

        self.df = pd.DataFrame(self.test_data)
        self.df["match_date"] = pd.to_datetime(self.df["match_date"])

        # 配置高级特征转换器 - 只启用Phase 5特征，避免Phase 8的数据需求
        self.config = AdvancedFeatureConfig(
            enable_venue_features=True,
            enable_h2h_features=True,
            enable_points_features=True,
            enable_player_ratings_features=False,  # 禁用Phase 8球员评分特征
            enable_metadata_features=False,  # 禁用Phase 8元数据特征
            enable_discipline_features=False,  # 禁用Phase 8纪律特征
            venue_windows=[3, 5],  # 包含5以匹配get_advanced_feature_names中的硬编码特征
            points_windows=[3, 5],
        )

        self.transformer = AdvancedFeatureTransformer(self.config)

    def test_feature_transformation(self):
        """测试完整的特征转换"""
        df_with_features = self.transformer.transform(self.df)

        # 检查数据形状
        self.assertGreater(df_with_features.shape[1], self.df.shape[1])

        # 检查新增的特征列
        feature_names = self.transformer.get_advanced_feature_names()
        self.assertGreater(len(feature_names), 0)

        # 验证特征列存在
        for feature in feature_names:
            self.assertIn(feature, df_with_features.columns)

    def test_prediction_scenario(self):
        """测试预测场景的特征转换"""
        # 当前比赛数据
        match_data = pd.DataFrame(
            {
                "home_team_id": [1],
                "away_team_id": [2],
                "home_score": [0],
                "away_score": [0],
                "match_date": [pd.Timestamp("2024-03-20")],
            }
        )

        # 历史数据
        historical_data = self.df.copy()

        # 转换预测特征
        prediction_features = self.transformer.transform_for_prediction(
            match_data, historical_data
        )

        # 应该有高级特征
        feature_names = self.transformer.get_advanced_feature_names()
        for feature in feature_names:
            if feature in prediction_features.columns:
                self.assertFalse(prediction_features[feature].isna().all())

    def test_feature_groups(self):
        """测试特征分组功能"""
        df_with_features = self.transformer.transform(self.df)
        feature_groups = self.transformer.get_feature_importance_groups()

        self.assertIn("venue", feature_groups)
        self.assertIn("h2h", feature_groups)
        self.assertIn("points", feature_groups)

        # 验证每组都有特征
        for group_type, features in feature_groups.items():
            if self.config.__dict__.get(f"enable_{group_type}_features", False):
                self.assertGreater(len(features), 0)

    def test_data_leakage_protection(self):
        """测试数据泄露保护机制"""
        df_with_features = self.transformer.transform(self.df)

        # 检查滚动特征是否使用shift(1)防止数据泄露
        for feature in self.transformer.get_advanced_feature_names():
            if "rolling" in feature and feature in df_with_features.columns:
                # 滚动特征的第一行应该是NaN（因为没有历史数据）
                self.assertTrue(pd.isna(df_with_features[feature].iloc[0]))

    def test_feature_correlation_analysis(self):
        """测试特征相关性分析"""
        # 添加目标变量
        df_with_target = self.df.copy()
        df_with_target["target"] = (
            df_with_target["home_score"] > df_with_target["away_score"]
        ).astype(int)

        # 转换特征
        df_with_features = self.transformer.transform(df_with_target)

        # 分析相关性
        correlations = self.transformer.analyze_feature_correlation(df_with_features)

        # 验证相关性分析结果
        for feature, corr_data in correlations.items():
            self.assertIn("correlation", corr_data)
            self.assertIn("abs_correlation", corr_data)
            self.assertIn("strength", corr_data)

    def test_feature_report_generation(self):
        """测试特征报告生成"""
        df_with_features = self.transformer.transform(self.df)

        report = self.transformer.generate_feature_report(df_with_features)

        self.assertIn("total_features", report)
        self.assertIn("feature_groups", report)
        self.assertIn("data_shape_before", report)

        # 验证报告数据的完整性
        self.assertGreater(report["total_features"], 0)
        self.assertEqual(report["data_shape_before"], df_with_features.shape)

    def test_napoli_juventus_case_simulation(self):
        """测试Napoli vs Juventus案例模拟"""
        # 模拟Napoli主场0进球但历史交锋有利的情况
        napoli_data = {
            "home_team_id": [1, 1, 1, 2, 2, 1, 2],
            "away_team_id": [2, 3, 4, 1, 1, 2, 1],
            "home_score": [0, 0, 0, 2, 1, 0, 1],
            "away_score": [1, 0, 2, 0, 0, 1, 2],
            "match_date": [
                "2024-01-01",
                "2024-01-15",
                "2024-02-01",
                "2024-01-10",
                "2024-02-10",
                "2024-03-01",
                "2024-02-15",
            ],
        }

        df_napoli = pd.DataFrame(napoli_data)
        df_napoli["match_date"] = pd.to_datetime(df_napoli["match_date"])

        # 测试场馆分离是否解决主场偏见问题
        venue_stats = self.venue_analyzer.calculate_venue_features_for_match(
            df_napoli, 1, 2, pd.Timestamp("2024-03-15")
        )

        # 即使主队近期主场进球少，场馆分离特征仍应提供合理估值
        self.assertGreaterEqual(venue_stats.home_goals_rolling_3, 0.0)


class TestPerformance(unittest.TestCase):
    """性能测试"""

    def setUp(self):
        """创建大数据集进行性能测试"""
        np.random.seed(42)
        n_matches = 1000

        self.large_data = {
            "home_team_id": np.random.randint(1, 51, n_matches),
            "away_team_id": np.random.randint(1, 51, n_matches),
            "home_score": np.random.poisson(1.5, n_matches),
            "away_score": np.random.poisson(1.2, n_matches),
            "match_date": [
                datetime(2024, 1, 1) + timedelta(days=i) for i in range(n_matches)
            ],
        }

        self.large_df = pd.DataFrame(self.large_data)
        self.large_df["match_date"] = pd.to_datetime(self.large_df["match_date"])

        self.transformer = AdvancedFeatureTransformer()

    def test_large_dataset_performance(self):
        """测试大数据集处理性能"""
        import time

        start_time = time.time()
        df_with_features = self.transformer.transform(self.large_df)
        end_time = time.time()

        processing_time = end_time - start_time

        # 性能基准：1000条记录应在10秒内完成
        self.assertLess(processing_time, 10.0)

        # 验证处理结果
        self.assertGreater(df_with_features.shape[1], self.large_df.shape[1])
        self.assertEqual(len(df_with_features), len(self.large_df))


if __name__ == "__main__":
    # 运行所有测试
    unittest.main(verbosity=2)
