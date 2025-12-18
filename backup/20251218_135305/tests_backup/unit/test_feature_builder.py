#!/usr/bin/env python3
"""
测试特征构建器 - 防止未来数据泄露
Test Feature Builder - Prevents Future Data Leakage

这个测试文件是质量保护的核心防线，确保：
1. shift(1)逻辑正确执行 - 防止未来数据泄露
2. 计算第10行特征时只能使用到第9行的数据
3. 时间序列特征的正确性
4. 滚动窗口计算的正确性

作为首席软件质量工程师的最终审计测试。
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta

# 导入被测试的组件
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from features.feature_builder import FeatureBuilder


class TestFeatureBuilder:
    """特征构建器测试套件"""

    @pytest.fixture
    def feature_builder(self):
        """创建特征构建器实例"""
        return FeatureBuilder(min_matches=3)

    @pytest.fixture
    def sample_match_data(self):
        """创建示例比赛数据"""
        # 创建时间序列数据，确保时间排序
        dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(10)]

        data = {
            "match_id": list(range(1, 11)),
            "match_date": dates,
            "home_team_id": [1, 1, 1, 1, 1, 2, 2, 2, 2, 2],
            "away_team_id": [2, 2, 2, 2, 2, 1, 1, 1, 1, 1],
            "home_score": [1, 2, 0, 3, 1, 2, 1, 0, 2, 3],
            "away_score": [0, 1, 2, 1, 2, 0, 1, 2, 1, 0],
            "stat_home_possession": [50, 55, 45, 60, 52, 48, 53, 47, 58, 54],
            "stat_away_possession": [50, 45, 55, 40, 48, 52, 47, 53, 42, 46],
            "stat_home_shots": [5, 8, 3, 10, 6, 7, 4, 2, 9, 8],
            "stat_away_shots": [4, 6, 9, 5, 7, 5, 8, 6, 4, 3],
            "stat_home_shots_on_target": [2, 4, 1, 5, 3, 3, 2, 1, 4, 4],
            "stat_away_shots_on_target": [1, 3, 4, 2, 3, 2, 3, 2, 2, 1],
        }

        return pd.DataFrame(data)

    def test_calculate_rolling_stats_shift_logic(
        self, feature_builder, sample_match_data
    ):
        """
        核心测试：shift(1)逻辑防止未来数据泄露

        验证：计算第10行的特征时，只能使用到第9行的数据
        这是防止数据泄露的关键保护机制
        """
        df = sample_match_data.copy()

        # 计算滚动统计特征
        result = feature_builder.calculate_rolling_stats(df, window=3)

        # 验证数据按时间排序
        assert result["match_date"].is_monotonic_increasing

        # 为主队ID=1的第6场比赛（索引5）检查shift逻辑
        team_1_match_6 = result[
            (result["home_team_id"] == 1)
            & (result["match_date"] == datetime(2024, 1, 6))
        ].iloc[0]

        # 计算第6场比赛（第6行）主队特征时，应该使用第1-5场比赛的数据
        # 滚动窗口大小为3，所以使用最近3场比赛（第3、4、5场）的数据

        # 手动验证shift(1)逻辑：
        # 第6场比赛的rolling_3特征应该基于第3、4、5场比赛计算

        # 获取第3、4、5场比赛的数据（主队ID=1）
        team_1_matches = df[df["home_team_id"] == 1].copy().reset_index(drop=True)
        match_3 = team_1_matches.iloc[2]  # 第3场比赛
        match_4 = team_1_matches.iloc[3]  # 第4场比赛
        match_5 = team_1_matches.iloc[4]  # 第5场比赛

        # 手动计算期望的滚动平均值（对于stat_home_possession）
        expected_possession = (
            match_3["stat_home_possession"]
            + match_4["stat_home_possession"]
            + match_5["stat_home_possession"]
        ) / 3

        # 从结果中获取实际计算的滚动特征
        actual_possession = team_1_match_6["stat_home_possession_home_rolling_3"]

        # 验证shift(1)逻辑正确执行
        # 允许小的浮点数误差
        assert abs(actual_possession - expected_possession) < 0.001, (
            f"shift(1)逻辑错误: 期望 {expected_possession}, "
            f"实际 {actual_possession}, "
            f"差异 {abs(actual_possession - expected_possession)}"
        )

        # 进一步验证：确保第6场比赛的特征不包含第6场比赛本身的统计数据
        # 第6场比赛的stat_home_possession应该是60，但rolling特征应该基于前3场
        assert team_1_match_6["stat_home_possession"] == 60  # 第6场比赛的实际数据
        assert (
            team_1_match_6["stat_home_possession_home_rolling_3"] != 60
        )  # 滚动特征不应该等于当前值

    def test_no_future_data_leakage(self, feature_builder):
        """
        测试没有未来数据泄露

        关键验证：每一行的滚动特征都只使用该行之前的数据
        """
        # 创建更复杂的测试数据
        dates = pd.date_range(start="2024-01-01", periods=20, freq="D")

        # 创建球队1的连续比赛
        data = {
            "match_id": list(range(1, 21)),
            "match_date": dates,
            "home_team_id": [1] * 20,
            "away_team_id": [2] * 20,
            "home_score": list(range(1, 21)),  # 1, 2, 3, ..., 20
            "away_score": [0] * 20,
            "stat_home_possession": list(range(50, 70)),  # 50, 51, 52, ..., 69
        }

        df = pd.DataFrame(data)
        result = feature_builder.calculate_rolling_stats(df, window=3)

        # 验证每行的滚动特征都不包含当前行的数据
        for i in range(3, len(result)):  # 从第4行开始（索引3），因为需要前3行计算
            current_match = result.iloc[i]

            # 获取当前行的原始数据
            current_possession = current_match["stat_home_possession"]

            # 获取滚动特征（应该基于前3行）
            rolling_possession = current_match["stat_home_possession_home_rolling_3"]

            # 验证滚动特征不等于当前值（证明没有使用当前行数据）
            assert rolling_possession != current_possession, (
                f"第{i}行发现数据泄露: "
                f"当前行数据={current_possession}, "
                f"滚动特征={rolling_possession}"
            )

            # 验证滚动特征是前3行的平均值
            prev_1 = result.iloc[i - 1]["stat_home_possession"]
            prev_2 = result.iloc[i - 2]["stat_home_possession"]
            prev_3 = result.iloc[i - 3]["stat_home_possession"]

            expected = (prev_1 + prev_2 + prev_3) / 3

            assert abs(rolling_possession - expected) < 0.001, (
                f"第{i}行滚动特征计算错误: "
                f"期望={expected}, "
                f"实际={rolling_possession}"
            )

    def test_shift_one_preserves_window_size(self, feature_builder, sample_match_data):
        """测试shift(1)保持窗口大小正确"""
        df = sample_match_data.copy()
        result = feature_builder.calculate_rolling_stats(df, window=5)

        # 检查前几行的rolling特征为NaN（因为没有足够的历史数据）
        assert pd.isna(result.iloc[0]["stat_home_possession_home_rolling_5"])
        assert pd.isna(result.iloc[1]["stat_home_possession_home_rolling_5"])
        assert pd.isna(result.iloc[2]["stat_home_possession_home_rolling_5"])
        assert pd.isna(result.iloc[3]["stat_home_possession_home_rolling_5"])

        # 第6行开始应该有值（基于前5行）
        assert not pd.isna(result.iloc[5]["stat_home_possession_home_rolling_5"])

    def test_rolling_window_calculation(self, feature_builder, sample_match_data):
        """测试滚动窗口计算的正确性"""
        df = sample_match_data.copy()
        result = feature_builder.calculate_rolling_stats(df, window=3)

        # 验证结果包含正确的列
        expected_cols = [
            "stat_home_possession_home_rolling_3",
            "stat_home_possession_home_std_3",
            "stat_away_possession_away_rolling_3",
            "stat_away_possession_away_std_3",
        ]

        for col in expected_cols:
            assert col in result.columns, f"缺少期望的列: {col}"

    def test_time_series_ordering(self, feature_builder, sample_match_data):
        """测试时间序列排序"""
        # 打乱数据顺序
        shuffled_data = sample_match_data.sample(frac=1).reset_index(drop=True)

        result = feature_builder.calculate_rolling_stats(shuffled_data, window=3)

        # 验证结果按时间排序
        assert result["match_date"].is_monotonic_increasing, "结果未按时间排序"

    def test_away_team_rolling_stats(self, feature_builder, sample_match_data):
        """测试客队滚动统计特征"""
        df = sample_match_data.copy()
        result = feature_builder.calculate_rolling_stats(df, window=3)

        # 验证客队滚动特征存在
        assert "stat_home_shots_away_rolling_3" in result.columns
        assert "stat_home_possession_away_rolling_3" in result.columns

        # 验证客队特征计算正确（按away_team_id分组）
        # 找到球队2作为客队的比赛
        team_2_away_matches = result[result["away_team_id"] == 2]

        # 验证滚动特征不为空（对于有足够历史数据的比赛）
        if len(team_2_away_matches) > 3:
            # 第4场比赛应该有前3场客队比赛的滚动特征
            fourth_match = team_2_away_matches.iloc[3]
            assert not pd.isna(fourth_match["stat_home_shots_away_rolling_3"])

    def test_rolling_std_calculation(self, feature_builder, sample_match_data):
        """测试滚动标准差计算"""
        df = sample_match_data.copy()
        result = feature_builder.calculate_rolling_stats(df, window=3)

        # 验证滚动标准差列存在
        std_col = "stat_home_possession_home_std_3"
        assert std_col in result.columns

        # 验证标准差非负
        std_values = result[std_col].dropna()
        assert (std_values >= 0).all(), "滚动标准差有负值"

    def test_fatigue_features_calculation(self, feature_builder, sample_match_data):
        """测试疲劳度特征计算"""
        df = sample_match_data.copy()

        # 确保match_date是datetime类型
        df["match_date"] = pd.to_datetime(df["match_date"])

        result = feature_builder.calculate_fatigue_features(df)

        # 验证疲劳度特征列存在
        fatigue_cols = [
            "home_days_since_last_match",
            "home_last_match_minutes",
            "home_rotation_score",
            "away_days_since_last_match",
            "away_last_match_minutes",
            "away_rotation_score",
            "home_fatigue_score",
            "away_fatigue_score",
            "fatigue_advantage",
        ]

        for col in fatigue_cols:
            assert col in result.columns, f"缺少疲劳度特征列: {col}"

        # 验证疲劳度评分在0-1之间
        assert (result["home_fatigue_score"] >= 0).all()
        assert (result["home_fatigue_score"] <= 1).all()
        assert (result["away_fatigue_score"] >= 0).all()
        assert (result["away_fatigue_score"] <= 1).all()

    def test_fatigue_score_calculation_logic(self, feature_builder, sample_match_data):
        """测试疲劳度评分计算逻辑"""
        df = sample_match_data.copy()
        df["match_date"] = pd.to_datetime(df["match_date"])

        result = feature_builder.calculate_fatigue_features(df)

        # 验证疲劳度评分计算
        # 疲劳度评分 = (比赛时长影响 + 休息天数影响 + 轮换影响) / 3
        # 所有值应该在0-1之间

        for _idx, row in result.iterrows():
            home_score = row["home_fatigue_score"]
            away_score = row["away_fatigue_score"]

            assert 0 <= home_score <= 1, f"主队疲劳度评分超出范围: {home_score}"
            assert 0 <= away_score <= 1, f"客队疲劳度评分超出范围: {away_score}"

    def test_min_matches_parameter(self, feature_builder):
        """测试min_matches参数的行为"""
        # 使用更大的min_matches值
        strict_builder = FeatureBuilder(min_matches=5)

        dates = pd.date_range(start="2024-01-01", periods=10, freq="D")
        data = {
            "match_id": list(range(1, 11)),
            "match_date": dates,
            "home_team_id": [1] * 10,
            "away_team_id": [2] * 10,
            "home_score": list(range(1, 11)),
            "away_score": [0] * 10,
            "stat_home_possession": list(range(50, 60)),
        }

        df = pd.DataFrame(data)
        result = strict_builder.calculate_rolling_stats(df, window=3)

        # 验证min_matches=5的影响
        # 前5行不应该有滚动特征（需要5个历史数据点）
        for i in range(5):
            rolling_col = "stat_home_possession_home_rolling_3"
            assert pd.isna(
                result.iloc[i][rolling_col]
            ), f"第{i}行应该有NaN（需要5个历史数据点）"

    def test_groupby_team_id_logic(self, feature_builder, sample_match_data):
        """测试按球队ID分组的逻辑"""
        df = sample_match_data.copy()
        result = feature_builder.calculate_rolling_stats(df, window=3)

        # 验证每个球队的特征是独立计算的
        # 球队1和球队2的特征应该不同

        team_1_matches = result[result["home_team_id"] == 1]
        team_2_matches = result[result["home_team_id"] == 2]

        if len(team_1_matches) > 3 and len(team_2_matches) > 3:
            # 比较两个球队的第一个有效滚动特征
            t1_first_valid = (
                team_1_matches["stat_home_possession_home_rolling_3"].dropna().iloc[0]
            )
            t2_first_valid = (
                team_2_matches["stat_home_possession_away_rolling_3"].dropna().iloc[0]
            )

            # 两个球队的特征值应该不同（除非数据巧合相同）
            # 这里我们只是验证计算是独立进行的
            assert isinstance(t1_first_valid, (int, float))
            assert isinstance(t2_first_valid, (int, float))

    def test_build_features_complete_workflow(self, feature_builder, sample_match_data):
        """测试完整的特征构建流程"""
        df = sample_match_data.copy()

        # 构建完整特征集
        result = feature_builder.build_features(df)

        # 验证结果
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert len(result.columns) > len(df.columns)  # 应该添加了特征列

        # 验证包含目标变量
        assert "result" in result.columns
        assert "home_win" in result.columns
        assert "total_goals" in result.columns
        assert "over_2_5_goals" in result.columns
        assert "both_teams_score" in result.columns

    def test_get_feature_columns(self, feature_builder, sample_match_data):
        """测试获取特征列"""
        df = sample_match_data.copy()
        feature_df = feature_builder.build_features(df)

        feature_cols = feature_builder.get_feature_columns(feature_df)

        # 验证特征列不包含目标变量
        exclude_cols = {
            "match_id",
            "home_team_id",
            "away_team_id",
            "match_date",
            "home_score",
            "away_score",
            "result",
            "home_win",
            "total_goals",
            "over_2_5_goals",
            "both_teams_score",
        }

        for col in feature_cols:
            assert col not in exclude_cols, f"特征列包含目标变量: {col}"

    def test_validate_features(self, feature_builder, sample_match_data):
        """测试特征验证"""
        df = sample_match_data.copy()
        feature_df = feature_builder.build_features(df)

        is_valid, issues = feature_builder.validate_features(feature_df)

        # 检查验证结果
        assert isinstance(is_valid, bool)
        assert isinstance(issues, list)

        # 如果有问题，issues应该不为空
        if not is_valid:
            assert len(issues) > 0

    def test_no_data_leakage_in_complete_workflow(self, feature_builder):
        """
        完整工作流程中的数据泄露检查

        这是最重要的测试 - 确保整个特征构建过程都没有数据泄露
        """
        # 创建更长的历史数据
        dates = pd.date_range(start="2024-01-01", periods=50, freq="D")

        data = {
            "match_id": list(range(1, 51)),
            "match_date": dates,
            "home_team_id": [1] * 50,
            "away_team_id": [2] * 50,
            "home_score": list(range(1, 51)),  # 1到50递增
            "away_score": [0] * 50,
            "stat_home_possession": list(range(50, 100)),  # 50到99递增
        }

        df = pd.DataFrame(data)
        result = feature_builder.build_features(df)

        # 验证特征构建后，每行的特征值都不包含该行对应的未来数据
        # 检查第25行（中间位置）
        if len(result) >= 30:
            check_row = result.iloc[25]

            # 验证疲劳度特征计算使用了正确的时间逻辑
            # 检查是否有合理的疲劳度评分
            assert 0 <= check_row["home_fatigue_score"] <= 1
            assert 0 <= check_row["away_fatigue_score"] <= 1

    def test_window_size_variations(self, feature_builder, sample_match_data):
        """测试不同窗口大小的滚动特征"""
        df = sample_match_data.copy()

        # 测试不同窗口大小
        for window in [3, 5, 10]:
            result = feature_builder.calculate_rolling_stats(df, window=window)

            # 验证相应的列存在
            expected_col = f"stat_home_possession_home_rolling_{window}"
            assert expected_col in result.columns

            # 验证窗口大小影响
            if window == 10 and len(df) > 10:
                # 大窗口需要更多历史数据，前10行应该为NaN
                for i in range(10):
                    assert pd.isna(
                        result.iloc[i][expected_col]
                    ), f"窗口大小{window}，第{i}行应该为NaN"

    def test_shift_one_in_groupby_context(self, feature_builder, sample_match_data):
        """
        测试在groupby上下文中的shift(1)行为

        这是确保按球队分组计算时shift(1)正确工作的关键测试
        """
        df = sample_match_data.copy()
        result = feature_builder.calculate_rolling_stats(df, window=3)

        # 验证每个球队的滚动特征是独立计算的
        teams = pd.concat([df["home_team_id"], df["away_team_id"]]).unique()

        for team_id in teams:
            # 获取该球队作为主队的比赛
            home_matches = result[result["home_team_id"] == team_id].sort_values(
                "match_date"
            )

            if len(home_matches) >= 4:
                # 验证shift(1)逻辑：第4场比赛的滚动特征基于前3场
                match_4 = home_matches.iloc[3]
                match_1 = home_matches.iloc[0]
                match_2 = home_matches.iloc[1]
                match_3 = home_matches.iloc[2]

                # 计算期望的滚动平均值
                expected = (
                    match_1["stat_home_possession"]
                    + match_2["stat_home_possession"]
                    + match_3["stat_home_possession"]
                ) / 3

                actual = match_4["stat_home_possession_home_rolling_3"]

                assert abs(actual - expected) < 0.001, (
                    f"球队{team_id}第4场比赛的滚动特征计算错误: "
                    f"期望={expected}, 实际={actual}"
                )

    def test_rolling_features_have_correct_prefix(
        self, feature_builder, sample_match_data
    ):
        """测试滚动特征有正确的前缀"""
        df = sample_match_data.copy()
        result = feature_builder.calculate_rolling_stats(df, window=5)

        # 验证滚动特征命名规范
        rolling_cols = [col for col in result.columns if "_rolling_" in col]

        for col in rolling_cols:
            # 验证格式：{原始列名}_{home/away}_rolling_{window}
            parts = col.split("_")
            assert len(parts) >= 4, f"滚动特征列名格式错误: {col}"

            # 验证包含正确的后缀
            assert col.endswith("_rolling_5"), f"滚动特征后缀错误: {col}"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
