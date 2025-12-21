#!/usr/bin/env python3
"""
特征提取器测试 - TDD驱动bulletproof特征提取质量
验证136维物理非空特征的提取完整性
"""

import pytest
import json
from datetime import datetime
from typing import Dict, List, Any

from src.data_access.processors.bulletproof_feature_extractor import (
    BulletproofFeatureExtractor, get_bulletproof_extractor
)
from src.schemas.match_features import MatchFeatures


class TestBulletproofFeatureExtractor:
    """防弹级特征提取器测试类"""

    @pytest.fixture(autouse=True)
    def setup_extractor(self):
        """提取器初始化"""
        self.extractor = BulletproofFeatureExtractor()

        # 模拟FotMob API数据
        self.mock_api_data = {
            "header": {
                "status": {
                    "scoreStr": "2-1",
                    "finished": True
                },
                "teams": [
                    {"name": "Manchester United"},
                    {"name": "Liverpool"}
                ]
            },
            "content": {
                "stats": {
                    "Periods": {
                        "All": {
                            "stats": [
                                {
                                    "stats": [
                                        {"key": "expected_goals", "value": 1.45},
                                        {"key": "BallPossesion", "value": 48}
                                    ]
                                },
                                {
                                    "stats": [
                                        {"key": "expected_goals", "value": 1.82},
                                        {"key": "BallPossesion", "value": 52}
                                    ]
                                }
                            ]
                        }
                    }
                },
                "general": {
                    "teamStats": [
                        {
                            "cornerKicks": 7,
                            "shotsTotal": 15,
                            "yellowCards": 2,
                            "redCards": 0,
                            "fouls": 12,
                            "offsides": 3
                        },
                        {
                            "cornerKicks": 5,
                            "shotsTotal": 18,
                            "yellowCards": 3,
                            "redCards": 1,
                            "fouls": 15,
                            "offsides": 2
                        }
                    ]
                }
            }
        }

    def test_extractor_initialization(self):
        """测试: 提取器初始化"""
        assert self.extractor is not None
        assert hasattr(self.extractor, 'keyword_mappings')
        assert len(self.extractor.keyword_mappings) > 0

    def test_xg_feature_extraction_accuracy(self):
        """测试: xG特征提取准确性"""
        # 提取主队xG
        home_xg = self.extractor.extract_feature_value(self.mock_api_data, 'xg', 'home')
        assert home_xg is not None, "必须提取到主队xG"
        assert isinstance(home_xg, float), "xG必须是浮点数"
        assert home_xg > 0, "xG必须为正值"

        # 提取客队xG
        away_xg = self.extractor.extract_feature_value(self.mock_api_data, 'xg', 'away')
        assert away_xg is not None, "必须提取到客队xG"
        assert isinstance(away_xg, float), "xG必须是浮点数"
        assert away_xg > 0, "xG必须为正值"

        logger.info(f"✅ xG提取测试: home={home_xg}, away={away_xg}")

    def test_possession_feature_extraction_accuracy(self):
        """测试: 控球率特征提取准确性"""
        home_possession = self.extractor.extract_feature_value(self.mock_api_data, 'possession', 'home')
        assert home_possession is not None, "必须提取到主队控球率"
        assert isinstance(home_possession, float), "控球率必须是数值"
        assert 0 <= home_possession <= 100, "控球率必须在0-100之间"

        away_possession = self.extractor.extract_feature_value(self.mock_api_data, 'possession', 'away')
        assert away_possession is not None, "必须提取到客队控球率"

        # 验证控球率逻辑一致性
        total_possession = home_possession + away_possession
        assert abs(total_possession - 100) < 5, f"控球率总和不合理: {total_possession}%"

        logger.info(f"✅ 控球率提取测试: home={home_possession}%, away={away_possession}%")

    def test_match_scores_extraction_accuracy(self):
        """测试: 比赛分数提取准确性"""
        home_score, away_score = self.extractor.extract_team_scores(self.mock_api_data)

        assert home_score is not None, "必须提取到主队分数"
        assert away_score is not None, "必须提取到客队分数"
        assert isinstance(home_score, int), "分数必须是整数"
        assert isinstance(away_score, int), "分数必须是整数"
        assert home_score >= 0 and away_score >= 0, "分数不能为负数"

        logger.info(f"✅ 比分提取测试: {home_score}-{away_score}")

    def test_team_names_extraction_accuracy(self):
        """测试: 队伍名称提取准确性"""
        home_team, away_team = self.extractor.extract_team_names(self.mock_api_data)

        assert home_team is not None, "必须提取到主队名称"
        assert away_team is not None, "必须提取到客队名称"
        assert isinstance(home_team, str), "队伍名称必须是字符串"
        assert isinstance(away_team, str), "队伍名称必须是字符串"
        assert len(home_team) > 0 and len(away_team) > 0, "队伍名称不能为空"

        logger.info(f"✅ 队伍名称提取测试: {home_team} vs {away_team}")

    def test_complete_feature_extraction_pipeline(self):
        """测试: 完整特征提取管线"""
        match_id = "test_match_123"

        # 执行完整特征提取
        features = self.extractor.bulletproof_extract_features(self.mock_api_data, match_id)

        # 验证特征对象
        assert isinstance(features, MatchFeatures), "必须返回MatchFeatures对象"
        assert features.external_id == match_id, "match_id必须正确设置"

        # 验证核心特征不为空
        assert features.home_xg is not None, "home_xg不能为空"
        assert features.away_xg is not None, "away_xg不能为空"
        assert features.home_possession is not None, "home_possession不能为空"
        assert features.away_possession is not None, "away_possession不能为空"

        # 验证派生特征
        assert features.xg_total is not None, "xg_total不能为空"
        assert features.xg_diff is not None, "xg_diff不能为空"
        assert features.possession_diff is not None, "possession_diff不能为空"

        # 验证派生特征计算正确性
        expected_xg_total = features.home_xg + features.away_xg
        assert abs(features.xg_total - expected_xg_total) < 0.001, "xg_total计算错误"

        expected_xg_diff = features.home_xg - features.away_xg
        assert abs(features.xg_diff - expected_xg_diff) < 0.001, "xg_diff计算错误"

        expected_possession_diff = features.home_possession - features.away_possession
        assert abs(features.possession_diff - expected_possession_diff) < 0.001, "possession_diff计算错误"

        logger.info(f"✅ 完整特征提取测试: 质量分数={features.feature_quality_score:.3f}")

    def test_feature_quality_score_calculation(self):
        """测试: 特征质量分数计算"""
        match_id = "quality_test_123"

        # 测试完整数据
        features = self.extractor.bulletproof_extract_features(self.mock_api_data, match_id)

        # 质量分数应该较高
        assert features.feature_quality_score is not None, "必须有质量分数"
        assert 0 <= features.feature_quality_score <= 1, "质量分数必须在0-1之间"
        assert features.feature_quality_score > 0.5, "完整数据质量分数应该>0.5"

        logger.info(f"✅ 质量分数测试: {features.feature_quality_score:.3f}")

    def test_extraction_statistics_tracking(self):
        """测试: 提取统计信息跟踪"""
        # 重置统计信息
        self.extractor.extraction_stats = {
            'total_searches': 0,
            'successful_extractions': 0,
            'confidence_sum': 0.0,
            'method_usage': {}
        }

        # 执行多次提取
        for i in range(5):
            self.extractor.extract_feature_value(self.mock_api_data, 'xg', 'home')
            self.extractor.extract_feature_value(self.mock_api_data, 'possession', 'away')

        # 获取统计信息
        stats = self.extractor.get_extraction_statistics()

        # 验证统计信息
        assert stats['total_searches'] >= 10, "搜索次数应该>=10"
        assert stats['successful_extractions'] > 0, "必须有成功提取"
        assert stats['success_rate'] > 0, "成功率应该>0"
        assert stats['average_confidence'] > 0, "平均置信度应该>0"
        assert len(stats['method_usage']) > 0, "必须记录方法使用情况"

        logger.info(f"✅ 统计信息测试: 成功率{stats['success_rate']:.1f}%, 平均置信度{stats['average_confidence']:.2f}")

    def test_invalid_data_handling(self):
        """测试: 无效数据处理"""
        # 测试空数据
        empty_result = self.extractor.extract_feature_value({}, 'xg', 'home')
        assert empty_result is None, "空数据应该返回None"

        # 测试无效数据类型
        invalid_result = self.extractor.extract_feature_value({"invalid": "data"}, 'xg', 'home')
        assert invalid_result is None, "无效数据应该返回None"

        # 测试格式错误的比分
        invalid_score_data = {
            "header": {"status": {"scoreStr": "invalid-score"}}
        }
        home_score, away_score = self.extractor.extract_team_scores(invalid_score_data)
        assert home_score is None and away_score is None, "无效比分应该返回None"

        logger.info("✅ 无效数据处理测试通过")

    def test_keyword_matching_robustness(self):
        """测试: 关键字匹配鲁棒性"""
        # 测试不同格式的关键字
        test_cases = [
            ({"expected_goals": 1.5}, 'xg', 'home'),
            ({"xg": 1.6}, 'xg', 'home'),
            ({"ExpectedGoals": 1.7}, 'xg', 'home'),
            ({"xGoals": 1.8}, 'xg', 'home'),
            ({"BallPossesion": 55}, 'possession', 'home'),
            ({"possession": 56}, 'possession', 'home'),
            ({"possessionpercentage": 57}, 'possession', 'home'),
        ]

        for data, feature_type, team_side in test_cases:
            result = self.extractor.extract_feature_value(data, feature_type, team_side)
            assert result is not None, f"关键字匹配失败: {data} -> {feature_type}"
            assert isinstance(result, (int, float)), f"结果必须是数值: {result}"

        logger.info("✅ 关键字匹配鲁棒性测试通过")

    def test_global_extractor_singleton(self):
        """测试: 全局提取器单例"""
        extractor1 = get_bulletproof_extractor()
        extractor2 = get_bulletproof_extractor()

        assert extractor1 is extractor2, "必须是同一个实例"
        assert isinstance(extractor1, BulletproofFeatureExtractor), "必须是BulletproofFeatureExtractor实例"

        logger.info("✅ 全局提取器单例测试通过")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])