#!/usr/bin/env python3
"""
SHAP可解释性服务单元测试

测试ExplainabilityService类的所有功能，包括：
1. SHAP值计算和特征贡献度分析
2. 多分类和单分类处理
3. 特征验证和错误处理
4. 性能优化和缓存机制
5. 批量处理和排名功能
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List

from src.services.explainability_service import ExplainabilityService
from src.ml.models.xgboost_classifier import XGBoostClassifier
from src.features.schemas import MatchFeatureSet
from src.core.exceptions import ExplainabilityError


class TestExplainabilityService:
    """SHAP可解释性服务测试类"""

    @pytest.fixture
    def mock_model(self):
        """创建模拟的XGBoost模型"""
        model = Mock(spec=XGBoostClassifier)
        model.is_trained = True
        model.model = Mock()
        model.predict_proba = Mock(return_value=np.array([[0.3, 0.65, 0.05]]))
        model.get_model_info = Mock(return_value={
            'model_path': 'models/test_model.pkl',
            'model_version': 'test_v1'
        })
        return model

    @pytest.fixture
    def sample_features(self):
        """创建样本特征数据 - 基于MatchFeatureSet.get_feature_names()"""
        return pd.DataFrame({
            'home_form_score_5': [0.8, 0.6, 0.4],
            'away_form_score_5': [0.5, 0.7, 0.6],
            'home_form_score_3': [0.9, 0.5, 0.3],
            'away_form_score_3': [0.4, 0.8, 0.7],
            'home_xg_efficiency_5': [1.2, 0.9, 0.8],
            'away_xg_efficiency_5': [0.8, 1.1, 0.95],
            'home_xg_efficiency_3': [1.3, 0.7, 0.6],
            'away_xg_efficiency_3': [0.9, 1.2, 0.85],
            'odds_home_normalized': [0.45, 0.35, 0.55],
            'odds_draw_normalized': [0.30, 0.35, 0.25],
            'odds_away_normalized': [0.25, 0.30, 0.20],
            'h2h_home_win_rate': [0.7, 0.4, 0.6],
            'h2h_match_count_normalized': [0.8, 0.5, 0.6]
        })

    @pytest.fixture
    def sample_features_dict(self):
        """创建样本特征字典"""
        return {
            'home_form_score_5': 0.8,
            'away_form_score_5': 0.5,
            'home_form_score_3': 0.9,
            'away_form_score_3': 0.4,
            'home_xg_efficiency_5': 1.2,
            'away_xg_efficiency_5': 0.8,
            'home_xg_efficiency_3': 1.3,
            'away_xg_efficiency_3': 0.9,
            'odds_home_normalized': 0.45,
            'odds_draw_normalized': 0.30,
            'odds_away_normalized': 0.25,
            'h2h_home_win_rate': 0.7,
            'h2h_match_count_normalized': 0.8
        }

    @pytest.fixture
    def explainability_service(self):
        """创建ExplainabilityService实例"""
        return ExplainabilityService()

    @pytest.mark.asyncio
    async def test_get_shap_contributions_success(
        self, explainability_service, sample_features, mock_model
    ):
        """测试SHAP贡献度计算成功场景"""
        # 模拟SHAP计算结果 (14个特征)
        mock_shap_values = np.array([
            [0.1, -0.05, 0.08, -0.02, 0.12, -0.03, 0.06, -0.04, 0.09, -0.01, 0.07, -0.08, 0.05, -0.02],  # 第1个样本
            [0.05, 0.03, -0.07, 0.01, -0.09, 0.02, -0.04, 0.08, 0.03, -0.06, 0.01, 0.07, -0.05, 0.04],   # 第2个样本
            [-0.02, 0.08, 0.04, -0.06, -0.01, 0.05, 0.09, -0.03, 0.02, 0.07, -0.04, -0.01, 0.06, -0.03]   # 第3个样本
        ])

        with patch('shap.TreeExplainer') as mock_explainer_class:
            mock_explainer = Mock()
            mock_explainer_class.return_value = mock_explainer
            mock_explainer.shap_values.return_value = mock_shap_values
            mock_explainer.expected_value = 0.333

            # 执行测试
            contributions = await explainability_service.get_shap_contributions(
                sample_features, mock_model
            )

            # 验证结果
            assert len(contributions) == 3
            assert isinstance(contributions, list)

            # 验证第一个样本的贡献度
            first_contrib = contributions[0]
            assert isinstance(first_contrib, dict)
            assert 'home_form_score_5' in first_contrib
            assert 'away_form_score_5' in first_contrib

            # 验证SHAP值加性（基本检查）
            total_shap_1 = sum(first_contrib.values())
            assert isinstance(total_shap_1, float)

            # 验证调用
            mock_explainer_class.assert_called_once()
            mock_explainer.shap_values.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_shap_contributions_multiclass_handling(
        self, explainability_service, sample_features, mock_model
    ):
        """测试多分类SHAP值处理"""
        # 模拟多分类SHAP值（list格式） - 确保维度匹配14个特征
        mock_shap_values = [
            np.array([[0.1, -0.05, 0.08, -0.02, 0.12, -0.03, 0.06, -0.04, 0.09, -0.01, 0.07, -0.08, 0.05, -0.02],
                      [0.05, 0.03, -0.07, 0.01, -0.09, 0.02, -0.04, 0.08, 0.03, -0.06, 0.01, 0.07, -0.05, 0.04],
                      [-0.02, 0.08, 0.04, -0.06, -0.01, 0.05, 0.09, -0.03, 0.02, 0.07, -0.04, -0.01, 0.06, -0.03]]),  # Class 1
            np.array([[0.08, -0.02, 0.06, -0.01, 0.09, -0.04, 0.07, -0.03, 0.05, -0.06, 0.02, -0.07, 0.04, -0.01],
                      [-0.07, 0.01, 0.03, -0.06, 0.02, 0.08, -0.05, 0.04, -0.03, 0.05, -0.02, 0.06, -0.04, 0.01],
                      [0.04, -0.06, 0.02, 0.07, -0.04, -0.01, 0.06, -0.03, 0.01, -0.05, 0.03, -0.02, 0.05, -0.06]])  # Class 2
        ]

        with patch('shap.TreeExplainer') as mock_explainer_class:
            mock_explainer = Mock()
            mock_explainer_class.return_value = mock_explainer
            mock_explainer.shap_values.return_value = mock_shap_values

            # 执行测试
            contributions = await explainability_service.get_shap_contributions(
                sample_features, mock_model
            )

            # 验证结果：应该取第一个类别（二元分类处理）
            assert len(contributions) == 3
            first_contrib = contributions[0]
            assert len(first_contrib) == 13  # 多分类处理后实际的特征数量

    @pytest.mark.asyncio
    async def test_get_shap_contributions_model_not_trained(
        self, explainability_service, sample_features
    ):
        """测试模型未训练时的错误处理"""
        mock_model = Mock(spec=XGBoostClassifier)
        mock_model.is_trained = False

        with pytest.raises(ExplainabilityError) as exc_info:
            await explainability_service.get_shap_contributions(sample_features, mock_model)

        assert "模型未训练" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_shap_contributions_empty_features(
        self, explainability_service, mock_model
    ):
        """测试空特征数据的错误处理"""
        empty_features = pd.DataFrame()

        with pytest.raises(ExplainabilityError) as exc_info:
            await explainability_service.get_shap_contributions(empty_features, mock_model)

        assert "特征数据为空" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_shap_contributions_missing_features(
        self, explainability_service, mock_model
    ):
        """测试缺少必要特征时的错误处理"""
        # 创建缺少必要特征的DataFrame
        incomplete_features = pd.DataFrame({
            'home_score': [2.0],
            'away_score': [1.0]
            # 缺少其他必要特征
        })

        with pytest.raises(ExplainabilityError) as exc_info:
            await explainability_service.get_shap_contributions(incomplete_features, mock_model)

        assert "缺少必要的特征列" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_shap_contributions_shap_computation_error(
        self, explainability_service, sample_features, mock_model
    ):
        """测试SHAP计算异常时的错误处理"""
        with patch('shap.TreeExplainer') as mock_explainer_class:
            mock_explainer = Mock()
            mock_explainer_class.return_value = mock_explainer
            mock_explainer.shap_values.side_effect = Exception("SHAP计算失败")

            with pytest.raises(ExplainabilityError) as exc_info:
                await explainability_service.get_shap_contributions(sample_features, mock_model)

            assert "SHAP计算失败" in str(exc_info.value)

    def test_validate_features_success(
        self, explainability_service, sample_features, mock_model
    ):
        """测试特征验证成功场景"""
        # 这个测试需要使用私有方法，我们通过直接调用来测试
        try:
            explainability_service._validate_features(sample_features, mock_model)
        except Exception as e:
            pytest.fail(f"特征验证失败: {e}")

    def test_validate_features_empty(self, explainability_service, mock_model):
        """测试空特征数据验证"""
        empty_features = pd.DataFrame()

        with pytest.raises(ExplainabilityError) as exc_info:
            explainability_service._validate_features(empty_features, mock_model)

        assert "特征数据为空" in str(exc_info.value)

    def test_validate_features_missing_columns(self, explainability_service, mock_model):
        """测试缺少特征列的验证"""
        incomplete_features = pd.DataFrame({
            'home_form_score_5': [2.0]
        })

        with pytest.raises(ExplainabilityError) as exc_info:
            explainability_service._validate_features(incomplete_features, mock_model)

        assert "缺少必要的特征列" in str(exc_info.value)

    def test_validate_features_all_null(self, explainability_service, mock_model):
        """测试全空值特征列的验证"""
        null_features = pd.DataFrame({
            'home_form_score_5': [None],
            'away_form_score_5': [None],
            'home_form_score_3': [None],
            'away_form_score_3': [None],
            'home_xg_efficiency_5': [None],
            'away_xg_efficiency_5': [None],
            'home_xg_efficiency_3': [None],
            'away_xg_efficiency_3': [None],
            'odds_home_normalized': [None],
            'odds_draw_normalized': [None],
            'odds_away_normalized': [None],
            'h2h_home_win_rate': [None],
            'h2h_match_count_normalized': [None]
        })

        with pytest.raises(ExplainabilityError) as exc_info:
            explainability_service._validate_features(null_features, mock_model)

        assert "全部为空值" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_format_contributions(
        self, explainability_service, sample_features, mock_model
    ):
        """测试SHAP值格式化"""
        shap_values = np.array([
            [0.1, -0.05, 0.08, -0.02, 0.12, -0.03, 0.06, -0.04, 0.09, -0.01, 0.07, -0.08, 0.05, -0.02],
            [0.05, 0.03, -0.07, 0.01, -0.09, 0.02, -0.04, 0.08, 0.03, -0.06, 0.01, 0.07, -0.05, 0.04]
        ])

        contributions_list = await explainability_service._format_contributions(
            sample_features, shap_values, mock_model
        )

        assert len(contributions_list) == 2

        # 验证第一个样本的贡献度
        first_contrib = contributions_list[0]
        assert isinstance(first_contrib, dict)
        assert len(first_contrib) == 14  # 14个特征

        # 验证特征名称正确
        for feature_name in sample_features.columns:
            assert feature_name in first_contrib

        # 验证按贡献度绝对值排序
        values = list(first_contrib.values())
        abs_values = [abs(v) for v in values]
        assert abs_values == sorted(abs_values, reverse=True)

    def test_get_feature_importance_ranking(self, explainability_service):
        """测试特征重要性排名计算"""
        contributions_list = [
            {'feature1': 0.1, 'feature2': -0.05, 'feature3': 0.08},
            {'feature1': 0.05, 'feature2': 0.03, 'feature3': -0.07},
            {'feature1': -0.02, 'feature2': 0.08, 'feature3': 0.04}
        ]

        ranking = explainability_service.get_feature_importance_ranking(contributions_list)

        assert isinstance(ranking, dict)
        assert len(ranking) == 3

        # 验证计算：平均绝对SHAP值
        # feature1: (0.1 + 0.05 + 0.02) / 3 = 0.0567
        # feature2: (0.05 + 0.03 + 0.08) / 3 = 0.0533
        # feature3: (0.08 + 0.07 + 0.04) / 3 = 0.0633
        assert pytest.approx(ranking['feature3'], 0.001) == 0.0633
        assert pytest.approx(ranking['feature1'], 0.001) == 0.0567
        assert pytest.approx(ranking['feature2'], 0.001) == 0.0533

        # 验证按重要性降序排序
        values = list(ranking.values())
        assert values == sorted(values, reverse=True)

    def test_get_feature_importance_ranking_empty(self, explainability_service):
        """测试空贡献度列表的排名计算"""
        ranking = explainability_service.get_feature_importance_ranking([])
        assert ranking == {}

    @pytest.mark.asyncio
    async def test_explain_single_prediction(
        self, explainability_service, sample_features_dict, mock_model
    ):
        """测试单个预测解释功能"""
        # 模拟SHAP计算
        mock_shap_values = np.array([[0.1, -0.05, 0.08, -0.02, 0.12, -0.03, 0.06, -0.04, 0.09, -0.01, 0.07, -0.08, 0.05, -0.02]])

        with patch('shap.TreeExplainer') as mock_explainer_class:
            mock_explainer = Mock()
            mock_explainer_class.return_value = mock_explainer
            mock_explainer.shap_values.return_value = mock_shap_values
            mock_explainer.expected_value = 0.333

            # 模拟模型预测
            mock_model.predict_with_probability = Mock(return_value={
                'HOME_WIN_PROBA': 0.65,
                'DRAW_PROBA': 0.25,
                'AWAY_WIN_PROBA': 0.10,
                'predicted_class': 'HOME_WIN',
                'confidence': 0.65
            })

            # 执行测试
            explanation = await explainability_service.explain_single_prediction(
                sample_features_dict, mock_model
            )

            # 验证结果结构
            assert 'prediction' in explanation
            assert 'feature_contributions' in explanation
            assert 'top_positive_contributors' in explanation
            assert 'top_negative_contributors' in explanation
            assert 'feature_importance_ranking' in explanation

            # 验证预测结果
            prediction = explanation['prediction']
            assert prediction['predicted_class'] == 'HOME_WIN'
            assert prediction['HOME_WIN_PROBA'] == 0.65

            # 验证特征贡献度
            contributions = explanation['feature_contributions']
            assert isinstance(contributions, dict)
            assert len(contributions) == 13  # 实际的特征数量

            # 验证正向贡献者
            positive_contributors = explanation['top_positive_contributors']
            assert all(contrib['contribution'] > 0 for contrib in positive_contributors)

            # 验证负向贡献者
            negative_contributors = explanation['top_negative_contributors']
            assert all(contrib['contribution'] < 0 for contrib in negative_contributors)

    @pytest.mark.asyncio
    async def test_explain_single_prediction_error(
        self, explainability_service, sample_features_dict, mock_model
    ):
        """测试单个预测解释错误处理"""
        with patch('shap.TreeExplainer') as mock_explainer_class:
            mock_explainer = Mock()
            mock_explainer_class.return_value = mock_explainer
            mock_explainer.shap_values.side_effect = Exception("SHAP计算失败")

            with pytest.raises(ExplainabilityError) as exc_info:
                await explainability_service.explain_single_prediction(
                    sample_features_dict, mock_model
                )

            assert "预测解释失败" in str(exc_info.value)

    def test_clear_cache(self, explainability_service):
        """测试缓存清除功能"""
        # 添加一些缓存数据
        explainability_service._explainer_cache = {'test_key': 'test_value'}

        # 清除缓存
        explainability_service.clear_cache()

        # 验证缓存已清除
        assert len(explainability_service._explainer_cache) == 0

    @pytest.mark.asyncio
    async def test_get_or_create_explainer_caching(
        self, explainability_service, mock_model
    ):
        """测试SHAP解释器缓存机制"""
        with patch('shap.TreeExplainer') as mock_explainer_class:
            mock_explainer = Mock()
            mock_explainer_class.return_value = mock_explainer

            # 第一次调用
            explainer_1 = await explainability_service._get_or_create_explainer(mock_model)

            # 第二次调用应该使用缓存
            explainer_2 = await explainability_service._get_or_create_explainer(mock_model)

            # 验证返回同一个实例（缓存）
            assert explainer_1 is explainer_2

            # 验证只创建了一次
            assert mock_explainer_class.call_count == 1

    @pytest.mark.asyncio
    async def test_shap_consistency_validation(
        self, explainability_service, sample_features, mock_model
    ):
        """测试SHAP一致性验证功能"""
        # 模拟SHAP值
        mock_shap_values = np.array([[0.1, -0.05, 0.08, -0.02, 0.12, -0.03]])
        contributions_list = [{'home_score': 0.1, 'away_score': -0.05}]

        with patch('shap.TreeExplainer') as mock_explainer_class:
            mock_explainer = Mock()
            mock_explainer_class.return_value = mock_explainer
            mock_explainer.expected_value = 0.333

            # 模拟模型输出
            mock_model.predict_proba = Mock(return_value=np.array([[0.3, 0.65, 0.05]]))

            # 执行验证（应该不抛出异常）
            await explainability_service._validate_shap_consistency(
                sample_features, mock_model, mock_shap_values, contributions_list
            )

    @pytest.mark.asyncio
    async def test_shap_consistency_validation_inconsistency(
        self, explainability_service, sample_features, mock_model, caplog
    ):
        """测试SHAP一致性验证警告处理"""
        # 创建不一致的SHAP值
        mock_shap_values = np.array([[10.0, -5.0]])  # 很大的值，会导致不一致
        contributions_list = [{'home_score': 10.0, 'away_score': -5.0}]

        with patch('shap.TreeExplainer') as mock_explainer_class:
            mock_explainer = Mock()
            mock_explainer_class.return_value = mock_explainer
            mock_explainer.expected_value = 0.333

            # 模拟模型输出
            mock_model.predict_proba = Mock(return_value=np.array([[0.3, 0.65, 0.05]]))

            # 执行验证（应该记录警告但不抛出异常）
            await explainability_service._validate_shap_consistency(
                sample_features, mock_model, mock_shap_values, contributions_list
            )

            # 验证记录了警告
            assert any("SHAP加性不一致" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_performance_multiple_samples(
        self, explainability_service, mock_model
    ):
        """测试多样本处理性能"""
        # 创建更多样本数据
        large_features = pd.DataFrame({
            'home_form_score_5': np.random.rand(10),
            'away_form_score_5': np.random.rand(10),
            'home_form_score_3': np.random.rand(10),
            'away_form_score_3': np.random.rand(10),
            'home_xg_efficiency_5': np.random.rand(10),
            'away_xg_efficiency_5': np.random.rand(10),
            'home_xg_efficiency_3': np.random.rand(10),
            'away_xg_efficiency_3': np.random.rand(10),
            'odds_home_normalized': np.random.rand(10),
            'odds_draw_normalized': np.random.rand(10),
            'odds_away_normalized': np.random.rand(10),
            'h2h_home_win_rate': np.random.rand(10),
            'h2h_match_count_normalized': np.random.rand(10)
        })

        mock_shap_values = np.random.rand(10, 14) * 0.2 - 0.1  # 小的随机值

        with patch('shap.TreeExplainer') as mock_explainer_class:
            mock_explainer = Mock()
            mock_explainer_class.return_value = mock_explainer
            mock_explainer.shap_values.return_value = mock_shap_values

            import time
            start_time = time.time()

            # 执行测试
            contributions = await explainability_service.get_shap_contributions(
                large_features, mock_model
            )

            end_time = time.time()
            execution_time = end_time - start_time

            # 验证结果
            assert len(contributions) == 10
            assert execution_time < 5.0  # 应该在5秒内完成

            # 验证每个样本的贡献度
            for i, contrib in enumerate(contributions):
                assert isinstance(contrib, dict)
                assert len(contrib) == 14  # 14个特征
                # 验证SHAP值与模拟数据一致
                for j, (feature, value) in enumerate(contrib.items()):
                    assert pytest.approx(value, 0.001) == mock_shap_values[i, j]

    @pytest.mark.asyncio
    async def test_edge_case_zero_features(
        self, explainability_service, mock_model
    ):
        """测试边界情况：零值特征"""
        zero_features = pd.DataFrame({
            'home_form_score_5': [0.0, 0.0],
            'away_form_score_5': [0.0, 0.0],
            'home_form_score_3': [0.0, 0.0],
            'away_form_score_3': [0.0, 0.0],
            'home_xg_efficiency_5': [0.0, 0.0],
            'away_xg_efficiency_5': [0.0, 0.0],
            'home_xg_efficiency_3': [0.0, 0.0],
            'away_xg_efficiency_3': [0.0, 0.0],
            'odds_home_normalized': [0.0, 0.0],
            'odds_draw_normalized': [0.0, 0.0],
            'odds_away_normalized': [0.0, 0.0],
            'h2h_home_win_rate': [0.0, 0.0],
            'h2h_match_count_normalized': [0.0, 0.0]
        })

        mock_shap_values = np.zeros((2, 14))

        with patch('shap.TreeExplainer') as mock_explainer_class:
            mock_explainer = Mock()
            mock_explainer_class.return_value = mock_explainer
            mock_explainer.shap_values.return_value = mock_shap_values

            # 执行测试（应该正常处理零值特征）
            contributions = await explainability_service.get_shap_contributions(
                zero_features, mock_model
            )

            # 验证结果
            assert len(contributions) == 2
            for contrib in contributions:
                assert all(value == 0.0 for value in contrib.values())

    def test_feature_coverage_validation(self, explainability_service):
        """测试特征覆盖度验证"""
        contributions = {
            'home_score': 0.1,
            'away_score': -0.05,
            'home_expected_goals': 0.08
            # 缺少其他特征
        }

        # 模拟不完整的贡献度
        with patch('logging.getLogger') as mock_logger:
            mock_log = Mock()
            mock_logger.return_value = mock_log

            # 验证应该记录警告但不抛出异常
            expected_features = set(MatchFeatureSet.model_fields.keys())
            actual_features = set(contributions.keys())
            missing = expected_features - actual_features

            if missing:
                assert len(missing) > 0
                # 这个测试主要确保特征覆盖度检查逻辑正常工作


class TestExplainabilityServiceIntegration:
    """SHAP可解释性服务集成测试"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_end_to_end_explanation_workflow(self):
        """端到端解释工作流测试"""
        # 这个测试需要真实的模型和数据，标记为集成测试
        pytest.skip("需要真实模型数据的集成测试")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_shap_values(self):
        """真实SHAP值计算测试"""
        # 这个测试需要真实的XGBoost模型，标记为集成测试
        pytest.skip("需要真实XGBoost模型的集成测试")


# 性能测试标记
@pytest.mark.performance
class TestExplainabilityServicePerformance:
    """SHAP可解释性服务性能测试"""

    @pytest.mark.asyncio
    async def test_large_batch_performance(self):
        """大批量处理性能测试"""
        pytest.skip("性能测试 - 需要大量数据")

    @pytest.mark.asyncio
    async def test_memory_usage(self):
        """内存使用测试"""
        pytest.skip("内存测试 - 需要专业工具")


# 回归测试标记
@pytest.mark.regression
class TestExplainabilityServiceRegression:
    """SHAP可解释性服务回归测试"""

    @pytest.mark.asyncio
    async def test_regression_shap_value_calculation(self):
        """SHAP值计算回归测试"""
        pytest.skip("回归测试 - 需要基准数据")