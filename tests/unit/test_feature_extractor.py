"""
Feature Extractor 单元测试
测试BulletproofFeatureExtractor的各种边缘情况处理
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, Mock
from pathlib import Path

# 添加src路径
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from src.data_access.processors.bulletproof_feature_extractor import BulletproofFeatureExtractor
except ImportError:
    pytest.skip("BulletproofFeatureExtractor not available", allow_module_level=True)


@pytest.mark.unit
class TestBulletproofFeatureExtractor:
    """BulletproofFeatureExtractor测试类"""

    @pytest.fixture
    def extractor(self):
        """创建特征提取器实例"""
        return BulletproofFeatureExtractor()

    @pytest.fixture
    def standard_match_data(self, sample_match_data):
        """标准比赛数据"""
        return sample_match_data

    @pytest.fixture
    def edge_case_match_data(self, sample_match_data_edge_cases):
        """边缘情况比赛数据"""
        return sample_match_data_edge_cases

    def test_extract_basic_features_success(self, extractor, standard_match_data):
        """测试基本特征提取成功"""
        # 模拟标准JSON结构
        mock_json = standard_match_data

        result = extractor.extract_features(mock_json)

        # 验证返回结果
        assert isinstance(result, dict)
        assert 'home_xg' in result or 'xg_home' in result
        assert 'away_xg' in result or 'xg_away' in result
        assert 'home_possession' in result or 'possession_home' in result

    def test_extract_features_empty_stats(self, extractor, edge_case_match_data):
        """测试空统计数据的情况"""
        empty_data = edge_case_match_data[0]  # 空值情况

        result = extractor.extract_features(empty_data)

        # 应该返回默认值或处理后的值，不应崩溃
        assert isinstance(result, dict)
        # 所有值都应该是数值类型或None
        for value in result.values():
            assert isinstance(value, (int, float)) or value is None

    def test_extract_features_missing_fields(self, extractor, edge_case_match_data):
        """测试缺失字段的情况"""
        missing_data = edge_case_match_data[1]  # 缺失字段

        result = extractor.extract_features(missing_data)

        # 应该返回包含默认值的字典
        assert isinstance(result, dict)
        # 不应该抛出异常

    def test_extract_features_invalid_types(self, extractor, edge_case_match_data):
        """测试无效数据类型"""
        invalid_data = edge_case_match_data[2]  # 异常数据类型

        result = extractor.extract_features(invalid_data)

        # 应该优雅地处理异常类型
        assert isinstance(result, dict)

    def test_extract_features_extreme_values(self, extractor, edge_case_match_data):
        """测试极端数值"""
        extreme_data = edge_case_match_data[3]  # 极端数值

        result = extractor.extract_features(extreme_data)

        # 应该对极端值进行限制或处理
        assert isinstance(result, dict)
        for value in result.values():
            if isinstance(value, (int, float)):
                assert not np.isnan(value)
                assert abs(value) < 1e6  # 合理的数值范围

    def test_extract_xg_features(self, extractor, standard_match_data):
        """测试xG特征提取"""
        result = extractor.extract_features(standard_match_data)

        # 检查xG相关特征
        xg_features = [k for k in result.keys() if 'xg' in k.lower()]
        assert len(xg_features) > 0

        # 验证xG值的合理性
        for key in xg_features:
            value = result[key]
            if isinstance(value, (int, float)):
                assert 0 <= value <= 10  # xG值应该在合理范围内

    def test_extract_possession_features(self, extractor, standard_match_data):
        """测试控球率特征提取"""
        result = extractor.extract_features(standard_match_data)

        # 检查控球率相关特征
        possession_features = [k for k in result.keys() if 'possession' in k.lower()]
        assert len(possession_features) > 0

        # 验证控球率值的合理性
        for key in possession_features:
            value = result[key]
            if isinstance(value, (int, float)):
                assert 0 <= value <= 100  # 控球率应该在0-100之间

    def test_extract_shots_features(self, extractor, standard_match_data):
        """测试射门特征提取"""
        result = extractor.extract_features(standard_match_data)

        # 检查射门相关特征
        shots_features = [k for k in result.keys() if 'shot' in k.lower()]
        assert len(shots_features) > 0

        # 验证射门数的合理性
        for key in shots_features:
            value = result[key]
            if isinstance(value, (int, float)):
                assert 0 <= value <= 50  # 射门数应该在合理范围内

    def test_extract_cards_features(self, extractor, standard_match_data):
        """测试红黄牌特征提取"""
        result = extractor.extract_features(standard_match_data)

        # 检查红黄牌相关特征
        cards_features = [k for k in result.keys() if 'card' in k.lower() or 'yellow' in k.lower() or 'red' in k.lower()]
        assert len(cards_features) > 0

        # 验证牌数的合理性
        for key in cards_features:
            value = result[key]
            if isinstance(value, (int, float)):
                assert 0 <= value <= 10  # 牌数应该在合理范围内

    def test_extract_corners_features(self, extractor, standard_match_data):
        """测试角球特征提取"""
        result = extractor.extract_features(standard_match_data)

        # 检查角球相关特征
        corners_features = [k for k in result.keys() if 'corner' in k.lower()]
        assert len(corners_features) > 0

        # 验证角球数的合理性
        for key in corners_features:
            value = result[key]
            if isinstance(value, (int, float)):
                assert 0 <= value <= 20  # 角球数应该在合理范围内

    def test_derived_features_calculation(self, extractor, standard_match_data):
        """测试衍生特征计算"""
        result = extractor.extract_features(standard_match_data)

        # 检查是否存在衍生特征
        derived_features = [k for k in result.keys() if 'diff' in k.lower() or 'ratio' in k.lower() or 'total' in k.lower()]

        if derived_features:
            # 验证衍生特征的合理性
            for key in derived_features:
                value = result[key]
                if isinstance(value, (int, float)):
                    assert not np.isnan(value)
                    assert not np.isinf(value)

    def test_feature_names_consistency(self, extractor, standard_match_data):
        """测试特征名称一致性"""
        result1 = extractor.extract_features(standard_match_data)
        result2 = extractor.extract_features(standard_match_data)

        # 两次提取应该返回相同的特征名
        assert set(result1.keys()) == set(result2.keys())

    def test_feature_count_stability(self, extractor, standard_match_data):
        """测试特征数量稳定性"""
        result = extractor.extract_features(standard_match_data)

        # 特征数量应该是合理的
        assert len(result) >= 10  # 至少应该有10个特征
        assert len(result) <= 100  # 不应该超过100个特征

    def test_none_input_handling(self, extractor):
        """测试None输入处理"""
        result = extractor.extract_features(None)

        # 应该返回空字典或默认值字典
        assert isinstance(result, dict)

    def test_empty_dict_input_handling(self, extractor):
        """测试空字典输入处理"""
        result = extractor.extract_features({})

        # 应该返回空字典或默认值字典
        assert isinstance(result, dict)

    def test_malformed_json_handling(self, extractor):
        """测试格式错误的JSON处理"""
        malformed_data = {
            "content": {
                "stats": "not_a_dict"  # 应该是字典
            }
        }

        result = extractor.extract_features(malformed_data)

        # 应该优雅地处理错误
        assert isinstance(result, dict)

    @patch('time.sleep')
    def test_extraction_performance(self, mock_sleep, extractor, standard_match_data):
        """测试提取性能"""
        import time

        start_time = time.time()
        for _ in range(100):  # 执行100次提取
            extractor.extract_features(standard_match_data)
        end_time = time.time()

        # 平均每次提取应该很快
        avg_time = (end_time - start_time) / 100
        assert avg_time < 0.01  # 每次提取应该少于10ms

    def test_feature_value_types(self, extractor, standard_match_data):
        """测试特征值类型"""
        result = extractor.extract_features(standard_match_data)

        for key, value in result.items():
            # 所有特征值都应该是数值类型或None
            assert isinstance(value, (int, float)) or value is None

            # 如果是数值，应该是有限的
            if isinstance(value, (int, float)):
                assert not np.isnan(value)
                assert not np.isinf(value)