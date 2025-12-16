#!/usr/bin/env python3
"""
M4模块: 数据集生成器单元测试

严格遵循TDD原则，在实现之前编写测试用例。
验证ClassificationDatasetGenerator的核心功能和边界条件。

测试覆盖:
1. 标签转换函数的正确性
2. 数据过滤逻辑的准确性
3. 特征完整性阈值验证
4. 异常情况处理
5. Mock数据测试场景

设计原则:
- 测试驱动: 先写测试，后写实现
- 边界测试: 覆盖各种边界条件和异常
- Mock隔离: 使用Mock对象隔离外部依赖
- 断言明确: 清晰的成功/失败标准
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

# 导入待测试的模块（这些将在Step 3中实现）
from src.ml.dataset.target_labels import MatchOutcome, score_to_label, label_to_numeric, numeric_to_label
from src.ml.dataset.dataset_generator import ClassificationDatasetGenerator

# 导入依赖模块的Mock
from src.features.schemas import MatchFeatureSet, TeamFormFeatures, XGFeatures, OddsFeatures


class TestTargetLabels:
    """测试目标标签功能"""

    def test_score_to_label_home_win(self):
        """测试主胜标签转换"""
        # 标准主胜
        assert score_to_label(2, 1) == MatchOutcome.HOME_WIN
        assert score_to_label(1, 0) == MatchOutcome.HOME_WIN
        assert score_to_label(5, 3) == MatchOutcome.HOME_WIN

    def test_score_to_label_draw(self):
        """测试平局标签转换"""
        assert score_to_label(0, 0) == MatchOutcome.DRAW
        assert score_to_label(1, 1) == MatchOutcome.DRAW
        assert score_to_label(3, 3) == MatchOutcome.DRAW

    def test_score_to_label_away_win(self):
        """测试客胜标签转换"""
        assert score_to_label(1, 2) == MatchOutcome.AWAY_WIN
        assert score_to_label(0, 1) == MatchOutcome.AWAY_WIN
        assert score_to_label(2, 4) == MatchOutcome.AWAY_WIN

    def test_score_to_label_string_input(self):
        """测试字符串输入转换"""
        assert score_to_label("2", "1") == MatchOutcome.HOME_WIN
        assert score_to_label("0", "0") == MatchOutcome.DRAW
        assert score_to_label("1", "3") == MatchOutcome.AWAY_WIN

    def test_score_to_label_float_input(self):
        """测试浮点数输入转换"""
        assert score_to_label(2.0, 1.0) == MatchOutcome.HOME_WIN
        assert score_to_label(0.0, 0.0) == MatchOutcome.DRAW
        assert score_to_label(1.5, 2.5) == MatchOutcome.AWAY_WIN

    def test_score_to_label_invalid_negative_scores(self):
        """测试负分输入（应该失败）"""
        with pytest.raises(ValueError, match="比分不能为负数"):
            score_to_label(-1, 0)
        with pytest.raises(ValueError, match="比分不能为负数"):
            score_to_label(0, -1)
        with pytest.raises(ValueError, match="比分不能为负数"):
            score_to_label(-1, -1)

    def test_score_to_label_invalid_non_numeric(self):
        """测试非数字输入（应该失败）"""
        with pytest.raises(ValueError):
            score_to_label("abc", 1)
        with pytest.raises(ValueError):
            score_to_label(1, "xyz")
        with pytest.raises(ValueError):
            score_to_label("", "")

    def test_label_numeric_conversion(self):
        """测试标签与数值的相互转换"""
        # 标签到数值
        assert label_to_numeric(MatchOutcome.HOME_WIN) == 2
        assert label_to_numeric(MatchOutcome.DRAW) == 1
        assert label_to_numeric(MatchOutcome.AWAY_WIN) == 0

        # 数值到标签
        assert numeric_to_label(2) == MatchOutcome.HOME_WIN
        assert numeric_to_label(1) == MatchOutcome.DRAW
        assert numeric_to_label(0) == MatchOutcome.AWAY_WIN

    def test_numeric_to_label_invalid_value(self):
        """测试无效数值输入"""
        with pytest.raises(ValueError, match="无效的数值标签"):
            numeric_to_label(-1)
        with pytest.raises(ValueError, match="无效的数值标签"):
            numeric_to_label(3)
        with pytest.raises(ValueError, match="无效的数值标签"):
            numeric_to_label(100)

    def test_matchoutcome_enum_properties(self):
        """测试MatchOutcome枚举属性"""
        # 测试get_all_outcomes
        all_outcomes = MatchOutcome.get_all_outcomes()
        assert len(all_outcomes) == 3
        assert MatchOutcome.HOME_WIN.value in all_outcomes
        assert MatchOutcome.DRAW.value in all_outcomes
        assert MatchOutcome.AWAY_WIN.value in all_outcomes

        # 测试get_description
        assert MatchOutcome.HOME_WIN.get_description() == "主队获胜"
        assert MatchOutcome.DRAW.get_description() == "平局"
        assert MatchOutcome.AWAY_WIN.get_description() == "客队获胜"

        # 测试is_win
        assert MatchOutcome.HOME_WIN.is_win("home") is True
        assert MatchOutcome.HOME_WIN.is_win("away") is False
        assert MatchOutcome.AWAY_WIN.is_win("away") is True
        assert MatchOutcome.AWAY_WIN.is_win("home") is False
        assert MatchOutcome.DRAW.is_win("home") is False
        assert MatchOutcome.DRAW.is_win("away") is False


class TestClassificationDatasetGenerator:
    """测试数据集生成器"""

    @pytest.fixture
    def mock_feature_extractor(self):
        """创建Mock特征提取器"""
        extractor = AsyncMock()

        # 创建模拟特征集
        def create_mock_feature_set(match_id: str, completeness: float = 0.9):
            return MatchFeatureSet(
                match_id=match_id,
                home_team_id=f"home_{match_id}",
                away_team_id=f"away_{match_id}",
                match_date=datetime.now() - timedelta(days=1),
                home_form_last5=TeamFormFeatures(matches_played=5, wins=3, draws=1, losses=1, goals_scored=8, goals_conceded=4, goal_difference=4, points=10, weighted_points=8.5, avg_goals_scored=1.6, avg_goals_conceded=0.8, clean_sheets=1, failed_to_score=1, current_win_streak=1, current_unbeaten_streak=3),
                away_form_last5=TeamFormFeatures(matches_played=5, wins=2, draws=2, losses=1, goals_scored=6, goals_conceded=5, goal_difference=1, points=8, weighted_points=7.2, avg_goals_scored=1.2, avg_goals_conceded=1.0, clean_sheets=2, failed_to_score=2, current_win_streak=0, current_unbeaten_streak=2),
                home_form_last3=TeamFormFeatures(matches_played=3, wins=2, draws=0, losses=1, goals_scored=5, goals_conceded=3, goal_difference=2, points=6, weighted_points=5.5, avg_goals_scored=1.67, avg_goals_conceded=1.0, clean_sheets=1, failed_to_score=0, current_win_streak=1, current_unbeaten_streak=2),
                away_form_last3=TeamFormFeatures(matches_played=3, wins=1, draws=1, losses=1, goals_scored=4, goals_conceded=4, goal_difference=0, points=4, weighted_points=3.8, avg_goals_scored=1.33, avg_goals_conceded=1.33, clean_sheets=1, failed_to_score=1, current_win_streak=0, current_unbeaten_streak=1),
                home_xg_last5=XGFeatures(total_xg=8.5, total_goals=8, xg_efficiency=0.94, avg_xg_per_match=1.7, avg_goals_per_match=1.6, big_chances_created=12, big_chances_converted=8, big_chance_conversion_rate=0.67, xg_trend_5=0.1, xg_trend_3=0.2),
                away_xg_last5=XGFeatures(total_xg=7.2, total_goals=6, xg_efficiency=0.83, avg_xg_per_match=1.44, avg_goals_per_match=1.2, big_chances_created=10, big_chances_converted=6, big_chance_conversion_rate=0.6, xg_trend_5=-0.05, xg_trend_3=0.1),
                home_xg_last3=XGFeatures(total_xg=5.1, total_goals=5, xg_efficiency=0.98, avg_xg_per_match=1.7, avg_goals_per_match=1.67, big_chances_created=7, big_chances_converted=5, big_chance_conversion_rate=0.71, xg_trend_5=0.1, xg_trend_3=0.2),
                away_xg_last3=XGFeatures(total_xg=4.2, total_goals=4, xg_efficiency=0.95, avg_xg_per_match=1.4, avg_goals_per_match=1.33, big_chances_created=6, big_chances_converted=4, big_chance_conversion_rate=0.67, xg_trend_5=-0.05, xg_trend_3=0.1),
                odds=OddsFeatures(home_win_odds=2.1, draw_odds=3.4, away_win_odds=3.8, home_win_implied_prob=0.48, draw_implied_prob=0.29, away_win_implied_prob=0.26, home_win_normalized=0.48, draw_normalized=0.29, away_win_normalized=0.26),
                h2h_total_matches=10,
                h2h_home_wins=6,
                h2h_away_wins=2,
                h2h_draws=2,
                h2h_home_win_rate=0.6,
                result=MatchOutcome.HOME_WIN,
                final_home_score=2,
                final_away_score=1,
                feature_completeness_score=completeness,
                data_quality_flag="HIGH" if completeness >= 0.8 else ("MEDIUM" if completeness >= 0.5 else "LOW")
            )

        extractor.extract_features = AsyncMock(side_effect=create_mock_feature_set)
        return extractor

    @pytest.fixture
    def mock_db_pool(self):
        """创建Mock数据库连接池"""
        pool = AsyncMock()

        # 模拟查询结果
        mock_records = [
            {
                'match_id': 'match_001',
                'home_team_id': 'team_home_1',
                'away_team_id': 'team_away_1',
                'match_date': datetime.now() - timedelta(days=1),
                'home_score': 2,
                'away_score': 1,
                'status': 'FINISHED'
            },
            {
                'match_id': 'match_002',
                'home_team_id': 'team_home_2',
                'away_team_id': 'team_away_2',
                'match_date': datetime.now() - timedelta(days=2),
                'home_score': 0,
                'away_score': 0,
                'status': 'FINISHED'
            },
            {
                'match_id': 'match_003',
                'home_team_id': 'team_home_3',
                'away_team_id': 'team_away_3',
                'match_date': datetime.now() - timedelta(days=3),
                'home_score': 1,
                'away_score': 3,
                'status': 'FINISHED'
            },
            {
                'match_id': 'match_004',  # 这个将被过滤掉（低完整性）
                'home_team_id': 'team_home_4',
                'away_team_id': 'team_away_4',
                'match_date': datetime.now() - timedelta(days=4),
                'home_score': 1,
                'away_score': 2,
                'status': 'FINISHED'
            }
        ]

        pool.fetch = AsyncMock(return_value=mock_records)
        return pool

    @pytest.fixture
    def dataset_generator(self, mock_feature_extractor, mock_db_pool):
        """创建数据集生成器实例"""
        return ClassificationDatasetGenerator(
            feature_extractor=mock_feature_extractor,
            db_pool=mock_db_pool
        )

    @pytest.mark.asyncio
    async def test_generate_dataset_success(self, dataset_generator):
        """测试成功生成数据集"""
        # 生成数据集
        result_df = await dataset_generator.generate_dataset(
            league_id="premier_league",
            start_date="2024-01-01"
        )

        # 验证结果
        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == 3  # 4个输入，1个被过滤（低完整性）

        # 验证列存在
        expected_columns = [
            'match_id', 'home_team_id', 'away_team_id', 'match_date',
            'final_home_score', 'final_away_score', 'target_label',
            'target_numeric', 'feature_completeness_score', 'data_quality_flag'
        ]
        for col in expected_columns:
            assert col in result_df.columns

        # 验证标签正确性
        assert result_df['target_label'].iloc[0] == MatchOutcome.HOME_WIN
        assert result_df['target_label'].iloc[1] == MatchOutcome.DRAW
        assert result_df['target_label'].iloc[2] == MatchOutcome.AWAY_WIN

        # 验证数值标签
        assert result_df['target_numeric'].iloc[0] == 2  # HOME_WIN
        assert result_df['target_numeric'].iloc[1] == 1  # DRAW
        assert result_df['target_numeric'].iloc[2] == 0  # AWAY_WIN

        # 验证完整性过滤
        assert all(result_df['feature_completeness_score'] >= 0.8)

    @pytest.mark.asyncio
    async def test_generate_dataset_filter_low_completeness(self, dataset_generator):
        """测试过滤低完整性数据"""
        # 这个测试验证特征完整性低于0.8的数据被过滤掉
        result_df = await dataset_generator.generate_dataset(
            league_id="test_league",
            start_date="2024-01-01"
        )

        # 验证没有低完整性数据
        assert all(result_df['feature_completeness_score'] >= 0.8)
        assert all(result_df['data_quality_flag'].isin(['HIGH', 'MEDIUM']))

    @pytest.mark.asyncio
    async def test_generate_database_error(self, dataset_generator):
        """测试数据库错误处理"""
        # 模拟数据库错误
        dataset_generator.db_pool.fetch.side_effect = Exception("数据库连接失败")

        with pytest.raises(Exception, match="数据库连接失败"):
            await dataset_generator.generate_dataset("test_league", "2024-01-01")

    @pytest.mark.asyncio
    async def test_generate_feature_extraction_error(self, dataset_generator):
        """测试特征提取错误处理"""
        # 模拟特征提取失败
        dataset_generator.feature_extractor.extract_features.side_effect = Exception("特征提取失败")

        # 应该跳过失败的比赛，不抛出异常
        result_df = await dataset_generator.generate_dataset("test_league", "2024-01-01")
        assert isinstance(result_df, pd.DataFrame)
        # 可能返回空DataFrame或只包含成功提取的比赛

    def test_apply_filters_high_completeness(self):
        """测试高完整性数据保留"""
        # 这个测试需要在实际实现后调整
        generator = ClassificationDatasetGenerator()

        # 创建测试数据
        test_data = pd.DataFrame({
            'match_id': ['match_1', 'match_2'],
            'feature_completeness_score': [0.9, 0.85],
            'data_quality_flag': ['HIGH', 'MEDIUM'],
            'target_label': [MatchOutcome.HOME_WIN, MatchOutcome.DRAW]
        })

        filtered = generator._apply_filters(test_data)
        assert len(filtered) == 2  # 两个都保留

    def test_apply_filters_low_completeness(self):
        """测试低完整性数据过滤"""
        generator = ClassificationDatasetGenerator()

        # 创建测试数据
        test_data = pd.DataFrame({
            'match_id': ['match_1', 'match_2', 'match_3'],
            'feature_completeness_score': [0.9, 0.7, 0.3],  # 最后两个会被过滤
            'data_quality_flag': ['HIGH', 'MEDIUM', 'LOW'],
            'target_label': [MatchOutcome.HOME_WIN, MatchOutcome.DRAW, MatchOutcome.AWAY_WIN]
        })

        filtered = generator._apply_filters(test_data)
        assert len(filtered) == 1  # 只有第一个保留
        assert filtered.iloc[0]['match_id'] == 'match_1'

    def test_apply_filters_missing_labels(self):
        """测试缺失标签的过滤"""
        generator = ClassificationDatasetGenerator()

        # 创建测试数据（包含缺失标签）
        test_data = pd.DataFrame({
            'match_id': ['match_1', 'match_2'],
            'feature_completeness_score': [0.9, 0.9],
            'data_quality_flag': ['HIGH', 'HIGH'],
            'target_label': [MatchOutcome.HOME_WIN, None]  # 第二个缺失标签
        })

        filtered = generator._apply_filters(test_data)
        assert len(filtered) == 1  # 只有第一个保留

    def test_calculate_target_labels(self):
        """测试标签计算逻辑"""
        generator = ClassificationDatasetGenerator()

        # 创建测试数据
        test_data = pd.DataFrame({
            'match_id': ['match_1', 'match_2', 'match_3'],
            'final_home_score': [2, 0, 1],
            'final_away_score': [1, 0, 3]
        })

        generator._calculate_target_labels(test_data)

        # 验证标签
        assert test_data['target_label'].iloc[0] == MatchOutcome.HOME_WIN
        assert test_data['target_label'].iloc[1] == MatchOutcome.DRAW
        assert test_data['target_label'].iloc[2] == MatchOutcome.AWAY_WIN

        # 验证数值标签
        assert test_data['target_numeric'].iloc[0] == 2
        assert test_data['target_numeric'].iloc[1] == 1
        assert test_data['target_numeric'].iloc[2] == 0

    def test_save_dataset_to_parquet(self, tmp_path):
        """测试保存为Parquet格式"""
        generator = ClassificationDatasetGenerator()

        # 创建测试数据
        test_data = pd.DataFrame({
            'match_id': ['match_1', 'match_2'],
            'feature_vector': [np.array([1.0, 2.0]), np.array([2.0, 3.0])],
            'target_label': [MatchOutcome.HOME_WIN, MatchOutcome.DRAW]
        })

        # 保存文件
        output_path = tmp_path / "test_dataset.parquet"
        generator._save_to_parquet(test_data, str(output_path))

        # 验证文件存在
        assert output_path.exists()

        # 验证可以读取
        loaded_data = pd.read_parquet(str(output_path))
        assert len(loaded_data) == 2
        assert list(loaded_data['match_id']) == ['match_1', 'match_2']


class TestIntegrationScenarios:
    """集成测试场景"""

    @pytest.mark.asyncio
    async def test_end_to_end_dataset_generation(self):
        """端到端数据集生成测试"""
        # 这个测试会在实际实现时进一步完善
        # 模拟完整的数据流：从数据库读取 -> 特征提取 -> 标签计算 -> 过滤 -> 保存

        # 创建完整的Mock设置
        mock_db_pool = AsyncMock()
        mock_feature_extractor = AsyncMock()

        # 模拟数据库数据
        mock_records = [{
            'match_id': 'match_001',
            'home_team_id': 'team_1',
            'away_team_id': 'team_2',
            'match_date': datetime.now() - timedelta(days=1),
            'home_score': 2,
            'away_score': 1,
            'status': 'FINISHED'
        }]

        mock_db_pool.fetch.return_value = mock_records

        # 模拟特征提取
        mock_features = MagicMock()
        mock_features.feature_completeness_score = 0.9
        mock_features.data_quality_flag = "HIGH"
        mock_features.get_feature_vector.return_value = np.array([1.0, 2.0, 3.0])
        mock_features.get_feature_names.return_value = ['feature1', 'feature2', 'feature3']

        mock_feature_extractor.extract_features.return_value = mock_features

        # 创建生成器并测试
        generator = ClassificationDatasetGenerator(
            feature_extractor=mock_feature_extractor,
            db_pool=mock_db_pool
        )

        result = await generator.generate_dataset("test_league", "2024-01-01")

        # 验证结果
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert 'match_id' in result.columns
        assert 'target_label' in result.columns


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])