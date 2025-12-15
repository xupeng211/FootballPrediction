"""
特征工程模块的单元测试
Feature Engineering Module Unit Tests

测试 FeatureTransformer 类的核心功能，包括：
- 隐含概率计算
- 赔率熵计算
- 平均进球差计算
- 输入验证和错误处理

作者: Football Prediction Team
创建时间: 2024-12-11
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# 添加src目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from ml.feature_engineering import FeatureTransformer


class TestFeatureTransformer:
    """FeatureTransformer 类的测试套件"""

    def setup_method(self):
        """每个测试方法执行前的设置"""
        self.transformer = FeatureTransformer()

        # 创建有效的测试数据
        self.valid_data = pd.DataFrame({
            'match_id': [1, 2, 3, 4, 5],
            'home_odds': [2.50, 1.80, 3.20, 1.45, 2.10],
            'away_odds': [2.80, 4.50, 2.30, 6.80, 3.40],
            'draw_odds': [3.20, 3.60, 2.90, 4.20, 3.15],
            'home_goals_last_5': [8, 12, 6, 15, 9],
            'away_goals_last_5': [7, 5, 8, 4, 11]
        })

        # 创建无效的测试数据（包含负赔率）
        self.invalid_data = pd.DataFrame({
            'match_id': [1, 2],
            'home_odds': [2.50, -1.80],  # 包含负值
            'away_odds': [2.80, 4.50],
            'draw_odds': [3.20, 3.60],
            'home_goals_last_5': [8, 12],
            'away_goals_last_5': [7, 5]
        })

        # 创建包含缺失值的数据
        self.missing_data = pd.DataFrame({
            'match_id': [1, 2, 3],
            'home_odds': [2.50, np.nan, 3.20],  # 包含缺失值
            'away_odds': [2.80, 4.50, 2.30],
            'draw_odds': [3.20, 3.60, 2.90],
            'home_goals_last_5': [8, 12, 6],
            'away_goals_last_5': [7, 5, 8]
        })

    def test_initialization(self):
        """测试 FeatureTransformer 的初始化"""
        assert self.transformer is not None
        assert hasattr(self.transformer, 'transform')
        assert hasattr(self.transformer, '_validate_input')

    def test_input_validation_missing_columns(self):
        """测试缺少必需列的情况"""
        incomplete_data = pd.DataFrame({
            'match_id': [1, 2],
            'home_odds': [2.50, 1.80],
            # 缺少其他必需列
        })

        with pytest.raises(ValueError, match="缺少必需的列"):
            self.transformer._validate_input(incomplete_data)

    def test_input_validation_empty_dataframe(self):
        """测试空数据框的情况"""
        empty_df = pd.DataFrame(columns=[
            'match_id', 'home_odds', 'away_odds', 'draw_odds',
            'home_goals_last_5', 'away_goals_last_5'
        ])

        with pytest.raises(ValueError, match="输入数据框不能为空"):
            self.transformer._validate_input(empty_df)

    def test_input_validation_negative_odds(self):
        """测试包含负赔率的情况"""
        with pytest.raises(ValueError, match="赔率不能为负数或零"):
            self.transformer._validate_input(self.invalid_data)

    def test_input_validation_missing_values(self):
        """测试包含缺失值的情况"""
        with pytest.raises(ValueError, match="输入数据包含缺失值"):
            self.transformer._validate_input(self.missing_data)

    def test_valid_input_validation(self):
        """测试有效输入数据的验证"""
        # 不应该抛出异常
        try:
            self.transformer._validate_input(self.valid_data)
        except ValueError:
            pytest.fail("有效数据不应该抛出验证异常")

    def test_calculate_implied_probability(self):
        """测试隐含概率计算"""
        # 测试单个赔率
        home_prob = self.transformer._calculate_implied_probability(2.50)
        assert home_prob == 0.40  # 1 / 2.50

        away_prob = self.transformer._calculate_implied_probability(4.50)
        assert away_prob == pytest.approx(0.2222, rel=1e-4)  # 1 / 4.50

    def test_calculate_implied_probability_invalid_input(self):
        """测试无效赔率的隐含概率计算"""
        with pytest.raises(ValueError, match="赔率必须大于0"):
            self.transformer._calculate_implied_probability(0)

        with pytest.raises(ValueError, match="赔率必须大于0"):
            self.transformer._calculate_implied_probability(-2.50)

    def test_calculate_odds_entropy(self):
        """测试赔率熵计算"""
        # 创建已知的概率分布
        probs = [0.4, 0.3, 0.3]  # home, draw, away
        entropy = self.transformer._calculate_odds_entropy(probs)

        # 手动计算期望的熵值
        expected_entropy = -sum(p * np.log2(p) for p in probs)
        assert entropy == pytest.approx(expected_entropy, rel=1e-10)

    def test_calculate_odds_entropy_invalid_probabilities(self):
        """测试无效概率分布的熵计算"""
        # 概率和不等于1
        with pytest.raises(ValueError, match="概率之和必须等于1"):
            self.transformer._calculate_odds_entropy([0.4, 0.3, 0.4])  # 和为1.1

        # 包含负概率
        with pytest.raises(ValueError, match="概率必须在0和1之间"):
            self.transformer._calculate_odds_entropy([0.4, -0.1, 0.7])

    def test_calculate_avg_goals_diff_l5(self):
        """测试平均进球差计算"""
        # 使用测试数据中的第一行
        home_goals = 8
        away_goals = 7
        expected_diff = home_goals - away_goals  # 8 - 7 = 1

        result = self.transformer._calculate_avg_goals_diff_l5(home_goals, away_goals)
        assert result == expected_diff

    def test_transform_basic_functionality(self):
        """测试基本的转换功能"""
        result = self.transformer.transform(self.valid_data)

        # 验证输出结构
        assert isinstance(result, pd.DataFrame)
        assert len(result) == len(self.valid_data)  # 行数应该相同

        # 验证新特征列是否存在
        expected_columns = [
            'Implied_Prob_Home', 'Implied_Prob_Away', 'Odds_Entropy',
            'Avg_Goals_Diff_L5'
        ]
        for col in expected_columns:
            assert col in result.columns, f"缺少列: {col}"

    def test_transform_implied_probabilities(self):
        """测试隐含概率计算的正确性"""
        result = self.transformer.transform(self.valid_data)

        # 检查第一行的隐含概率
        first_row = result.iloc[0]
        expected_home_prob = 1 / 2.50  # 0.40
        expected_away_prob = 1 / 2.80  # 约0.3571

        assert first_row['Implied_Prob_Home'] == pytest.approx(expected_home_prob, rel=1e-10)
        assert first_row['Implied_Prob_Away'] == pytest.approx(expected_away_prob, rel=1e-4)

    def test_transform_odds_entropy_calculation(self):
        """测试赔率熵计算的正确性"""
        result = self.transformer.transform(self.valid_data)

        # 手动计算第一行的期望熵值
        first_row_data = self.valid_data.iloc[0]
        home_prob = 1 / first_row_data['home_odds']      # 1/2.50 = 0.40
        draw_prob = 1 / first_row_data['draw_odds']      # 1/3.20 = 0.3125
        away_prob = 1 / first_row_data['away_odds']      # 1/2.80 ≈ 0.3571

        # 归一化概率（使其和为1）
        total_prob = home_prob + draw_prob + away_prob
        home_prob_norm = home_prob / total_prob
        draw_prob_norm = draw_prob / total_prob
        away_prob_norm = away_prob / total_prob

        expected_entropy = -sum(
            p * np.log2(p) for p in [home_prob_norm, draw_prob_norm, away_prob_norm]
        )

        actual_entropy = result.iloc[0]['Odds_Entropy']
        assert actual_entropy == pytest.approx(expected_entropy, rel=1e-4)

    def test_transform_goals_diff_calculation(self):
        """测试进球差计算的正确性"""
        result = self.transformer.transform(self.valid_data)

        # 检查第一行的进球差
        first_row_data = self.valid_data.iloc[0]
        expected_diff = first_row_data['home_goals_last_5'] - first_row_data['away_goals_last_5']

        actual_diff = result.iloc[0]['Avg_Goals_Diff_L5']
        assert actual_diff == expected_diff

    def test_transform_preserves_original_columns(self):
        """测试转换是否保留原始列"""
        result = self.transformer.transform(self.valid_data)

        original_columns = set(self.valid_data.columns)
        result_columns = set(result.columns)

        # 原始列应该都在结果中
        assert original_columns.issubset(result_columns)

    def test_transform_edge_cases(self):
        """测试边界情况"""
        # 创建极小赔率的数据（高概率）
        extreme_data = pd.DataFrame({
            'match_id': [1],
            'home_odds': [1.01],  # 极低赔率
            'away_odds': [10.0],  # 极高赔率
            'draw_odds': [5.0],
            'home_goals_last_5': [10],
            'away_goals_last_5': [2]
        })

        result = self.transformer.transform(extreme_data)

        # 验证计算仍然正常
        assert len(result) == 1
        assert result.iloc[0]['Implied_Prob_Home'] == pytest.approx(0.9901, rel=1e-4)
        assert result.iloc[0]['Implied_Prob_Away'] == 0.1

    def test_transform_single_row(self):
        """测试单行数据的转换"""
        single_row_data = self.valid_data.iloc[0:1].copy()
        result = self.transformer.transform(single_row_data)

        assert len(result) == 1
        assert all(col in result.columns for col in [
            'Implied_Prob_Home', 'Implied_Prob_Away', 'Odds_Entropy', 'Avg_Goals_Diff_L5'
        ])

    def test_feature_value_ranges(self):
        """测试特征值的合理范围"""
        result = self.transformer.transform(self.valid_data)

        # 隐含概率应该在 (0, 1] 范围内
        assert all(result['Implied_Prob_Home'] > 0) and all(result['Implied_Prob_Home'] <= 1)
        assert all(result['Implied_Prob_Away'] > 0) and all(result['Implied_Prob_Away'] <= 1)

        # 熵应该为正数
        assert all(result['Odds_Entropy'] > 0)

        # 进球差可以是任何实数
        assert isinstance(result['Avg_Goals_Diff_L5'].dtype, (np.int64, np.float64))

    @pytest.mark.parametrize("home_odds,away_odds,draw_odds,expected_diff", [
        (2.0, 3.0, 4.0, 1),    # 正进球差
        (3.0, 2.0, 4.0, -1),   # 负进球差
        (2.5, 2.5, 3.0, 0),    # 零进球差
        (5.0, 1.8, 3.5, 3),    # 大进球差
    ])
    def test_goals_diff_parameterized(self, home_odds, away_odds, draw_odds, expected_diff):
        """参数化测试进球差计算"""
        test_data = pd.DataFrame({
            'match_id': [1],
            'home_odds': [home_odds],
            'away_odds': [away_odds],
            'draw_odds': [draw_odds],
            'home_goals_last_5': [10 + expected_diff],
            'away_goals_last_5': [10]
        })

        result = self.transformer.transform(test_data)
        actual_diff = result.iloc[0]['Avg_Goals_Diff_L5']

        assert actual_diff == expected_diff