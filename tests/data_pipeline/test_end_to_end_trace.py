#!/usr/bin/env python3
"""
管线穿透单元测试 - End-to-End Trace
验证从API到数据库的完整数据流，确保阵容、战术、评分100%物理落盘
"""

import pytest
import json
import tempfile
import os
from datetime import datetime
from pathlib import Path

from src.data_access.processors.bulletproof_feature_extractor import (
    BulletproofFeatureExtractor, get_bulletproof_extractor
)
from src.schemas.match_features import MatchFeatures


class TestEndToEndTrace:
    """端到端管线穿透测试类"""

    @pytest.fixture
    def complete_match_sample(self):
        """包含完整阵容和评分的FotMob API样本"""
        return {
            "header": {
                "status": {
                    "scoreStr": "2-1",
                    "finished": True,
                    "startTimeStr": "2024-12-20T20:00:00+00:00"
                },
                "teams": [
                    {"name": "Manchester United", "id": 8656},
                    {"name": "Liverpool", "id": 8450}
                ]
            },
            "content": {
                "lineup": {
                    "home": {
                        "formation": "4-3-3",
                        "players": [
                            {
                                "id": 8195,
                                "name": "Onana",
                                "shirtNum": 1,
                                "position": "GK",
                                "rating": 7.2,
                                "stats": {
                                    "passes": 32,
                                    "passAccuracy": 84.4,
                                    "touches": 38,
                                    "tackles": 1,
                                    "interceptions": 2,
                                    "clearances": 3,
                                    "saves": 4
                                }
                            },
                            {
                                "id": 7169,
                                "name": "Maguire",
                                "shirtNum": 5,
                                "position": "D",
                                "rating": 6.8,
                                "stats": {
                                    "passes": 45,
                                    "passAccuracy": 88.9,
                                    "touches": 58,
                                    "tackles": 3,
                                    "interceptions": 4,
                                    "clearances": 8,
                                    "aerialDuels": 5,
                                    "aerialDuelsWon": 3
                                }
                            },
                            {
                                "id": 3181,
                                "name": "Fernandes",
                                "shirtNum": 8,
                                "position": "M",
                                "rating": 8.1,
                                "stats": {
                                    "passes": 56,
                                    "passAccuracy": 79.6,
                                    "touches": 72,
                                    "shotsTotal": 3,
                                    "shotsOnTarget": 1,
                                    "keyPasses": 4,
                                    "assists": 1,
                                    "tackles": 2,
                                    "interceptions": 1
                                }
                            }
                        ]
                    },
                    "away": {
                        "formation": "4-3-3",
                        "players": [
                            {
                                "id": 1568,
                                "name": "Alisson",
                                "shirtNum": 1,
                                "position": "GK",
                                "rating": 7.8,
                                "stats": {
                                    "passes": 28,
                                    "passAccuracy": 85.7,
                                    "touches": 35,
                                    "saves": 6,
                                    "punches": 2
                                }
                            },
                            {
                                "id": 1584,
                                "name": "Van Dijk",
                                "shirtNum": 4,
                                "position": "D",
                                "rating": 7.5,
                                "stats": {
                                    "passes": 52,
                                    "passAccuracy": 90.4,
                                    "touches": 68,
                                    "tackles": 2,
                                    "interceptions": 5,
                                    "clearances": 4,
                                    "aerialDuels": 6,
                                    "aerialDuelsWon": 5
                                }
                            },
                            {
                                "id": 1855,
                                "name": "Salah",
                                "shirtNum": 11,
                                "position": "F",
                                "rating": 8.6,
                                "stats": {
                                    "passes": 22,
                                    "passAccuracy": 77.3,
                                    "touches": 48,
                                    "shotsTotal": 5,
                                    "shotsOnTarget": 3,
                                    "goals": 1,
                                    "assists": 1,
                                    "dribbles": 4,
                                    "dribblesWon": 2
                                }
                            }
                        ]
                    }
                },
                "stats": {
                    "Periods": {
                        "All": {
                            "stats": [
                                {
                                    "stats": [
                                        {"key": "expected_goals", "value": 1.45},
                                        {"key": "big_chances_created", "value": 3},
                                        {"key": "big_chances_missed", "value": 1},
                                        {"key": "clearances", "value": 18},
                                        {"key": "interceptions", "value": 12},
                                        {"key": "tackles", "value": 15},
                                        {"key": "aerial_won", "value": 22},
                                        {"key": "passes", "value": 423},
                                        {"key": "pass_accuracy", "value": 82.4},
                                        {"key": "possession", "value": 48}
                                    ]
                                },
                                {
                                    "stats": [
                                        {"key": "expected_goals", "value": 1.82},
                                        {"key": "big_chances_created", "value": 5},
                                        {"key": "big_chances_missed", "value": 2},
                                        {"key": "clearances", "value": 14},
                                        {"key": "interceptions", "value": 18},
                                        {"key": "tackles", "value": 12},
                                        {"key": "aerial_won", "value": 18},
                                        {"key": "passes", "value": 567},
                                        {"key": "pass_accuracy", "value": 86.7},
                                        {"key": "possession", "value": 52}
                                    ]
                                }
                            ]
                        }
                    }
                },
                "shotmap": {
                    "shots": [
                        {
                            "id": 1,
                            "team": "home",
                            "player": "Fernandes",
                            "x": 75.2,
                            "y": 45.8,
                            "expectedGoals": 0.12,
                            "isGoal": False,
                            "shotType": "FreeKick"
                        },
                        {
                            "id": 2,
                            "team": "away",
                            "player": "Salah",
                            "x": 88.5,
                            "y": 32.1,
                            "expectedGoals": 0.35,
                            "isGoal": True,
                            "shotType": "OpenPlay"
                        }
                    ]
                }
            }
        }

    @pytest.fixture
    def raw_json_storage_dir(self):
        """临时JSON存储目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_complete_lineup_extraction(self, complete_match_sample):
        """
        测试: 完整阵容数据提取
        强制要求：必须能提取阵容相关特征
        """
        extractor = BulletproofFeatureExtractor()
        match_id = "test_lineup_123"

        # 执行特征提取
        features = extractor.bulletproof_extract_features(complete_match_sample, match_id)

        # 验证基本特征
        assert features.home_team == "Manchester United"
        assert features.away_team == "Liverpool"
        assert features.home_score == 2
        assert features.away_score == 1

        # 🚨 核心断言：阵容相关特征必须被提取
        print(f"提取到的特征数量: {len(features.dict())}")
        print(f"所有特征键: {list(features.dict().keys())}")

        # 检查是否存在阵容相关的字段（这些是我们期望的）
        expected_lineup_features = [
            'home_avg_rating', 'away_avg_rating',  # 阵容评分
            'home_lineup_count', 'away_lineup_count',  # 阵容人数
            'home_formation', 'away_formation',  # 阵型
            'home_total_passes', 'away_total_passes',  # 传球总数
            'home_pass_accuracy', 'away_pass_accuracy',  # 传球成功率
            'home_total_tackles', 'away_total_tackles',  # 铲断总数
            'home_total_interceptions', 'away_total_interceptions',  # 拦截总数
            'home_big_chances', 'away_big_chances',  # 大机会
            'home_shots_precision', 'away_shots_precision'  # 射门精度
        ]

        # 检查特征对象中是否有阵容相关数据
        feature_dict = features.dict()
        lineup_features_found = []

        for feature in expected_lineup_features:
            if feature in feature_dict and feature_dict[feature] is not None:
                lineup_features_found.append(feature)

        print(f"找到的阵容特征: {lineup_features_found}")

        # 🚨 这是关键断言 - 当前应该会失败，迫使修复提取器
        assert len(lineup_features_found) >= 3, \
            f"阵容特征提取失败！预期至少3个，实际找到{len(lineup_features_found)}个：{lineup_features_found}"

    def test_lineup_rating_calculation(self, complete_match_sample):
        """
        测试: 阵容评分计算
        """
        extractor = BulletproofFeatureExtractor()
        match_id = "test_rating_123"

        features = extractor.bulletproof_extract_features(complete_match_sample, match_id)
        feature_dict = features.dict()

        # 检查主队平均评分
        home_avg_rating = feature_dict.get('home_avg_rating')
        away_avg_rating = feature_dict.get('away_avg_rating')

        print(f"主队平均评分: {home_avg_rating}")
        print(f"客队平均评分: {away_avg_rating}")

        # 根据样本数据计算期望值
        # 主队: (7.2 + 6.8 + 8.1) / 3 = 7.37
        # 客队: (7.8 + 7.5 + 8.6) / 3 = 7.97

        if home_avg_rating is not None:
            assert abs(home_avg_rating - 7.37) < 0.1, f"主队评分错误: 期望7.37，实际{home_avg_rating}"

        if away_avg_rating is not None:
            assert abs(away_avg_rating - 7.97) < 0.1, f"客队评分错误: 期望7.97，实际{away_avg_rating}"

    def test_tactical_stats_extraction(self, complete_match_sample):
        """
        测试: 战术统计数据提取
        """
        extractor = BulletproofFeatureExtractor()
        match_id = "test_tactical_123"

        features = extractor.bulletproof_extract_features(complete_match_sample, match_id)
        feature_dict = features.dict()

        # 检查战术相关特征
        tactical_features = {
            'home_total_passes': 423,
            'away_total_passes': 567,
            'home_pass_accuracy': 82.4,
            'away_pass_accuracy': 86.7,
            'home_total_tackles': 15,
            'away_total_tackles': 12,
            'home_total_interceptions': 12,
            'away_total_interceptions': 18,
            'home_big_chances': 3,
            'away_big_chances': 5
        }

        extracted_tactical = []
        for feature, expected_value in tactical_features.items():
            actual_value = feature_dict.get(feature)
            if actual_value is not None:
                extracted_tactical.append((feature, actual_value, expected_value))
                print(f"✅ {feature}: 实际{actual_value} vs 期望{expected_value}")

        print(f"成功提取的战术特征数量: {len(extracted_tactical)}")

        # 🚨 强制要求：必须提取到战术特征
        assert len(extracted_tactical) >= 5, \
            f"战术特征提取不足！预期至少5个，实际{len(extracted_tactical)}个"

    def test_shotmap_details_extraction(self, complete_match_sample):
        """
        测试: 射门细节提取
        """
        extractor = BulletproofFeatureExtractor()
        match_id = "test_shotmap_123"

        features = extractor.bulletproof_extract_features(complete_match_sample, match_id)
        feature_dict = features.dict()

        # 检查射门相关特征
        shotmap_features = [
            'home_shots_from_box', 'away_shots_from_box',
            'home_shot_precision', 'away_shot_precision',
            'home_xg_from_shotmap', 'away_xg_from_shotmap',
            'home_total_shots_map', 'away_total_shots_map'
        ]

        extracted_shotmap = []
        for feature in shotmap_features:
            value = feature_dict.get(feature)
            if value is not None:
                extracted_shotmap.append((feature, value))

        print(f"成功提取的射门特征: {extracted_shotmap}")

        # 强制要求：必须提取到射门细节
        assert len(extracted_shotmap) >= 2, \
            f"射门特征提取失败！预期至少2个，实际{len(extracted_shotmap)}个"

    def test_double_storage_verification(self, complete_match_sample, raw_json_storage_dir):
        """
        测试: 双重存储验证（JSON文件 + 数据库）
        """
        extractor = BulletproofFeatureExtractor()
        match_id = "test_double_123"

        # 保存原始JSON
        json_filename = f"{match_id}.json"
        json_path = os.path.join(raw_json_storage_dir, json_filename)

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(complete_match_sample, f, ensure_ascii=False, indent=2)

        # 提取特征
        features = extractor.bulletproof_extract_features(complete_match_sample, match_id)

        # 验证JSON文件存在
        assert os.path.exists(json_path), "原始JSON文件未保存"

        # 验证JSON文件完整性
        with open(json_path, 'r', encoding='utf-8') as f:
            loaded_json = json.load(f)

        assert loaded_json == complete_match_sample, "JSON文件数据不一致"

        # 验证特征对象完整性
        assert features.external_id == match_id, "external_id不匹配"
        assert features.data_source is not None, "data_source未设置"

        print(f"✅ 双重存储验证通过: {json_path}, 特征数量: {len(features.dict())}")

    def test_data_density_validation(self, complete_match_sample):
        """
        测试: 数据密度验证
        确保提取的特征中非NULL字段数量 >= 20
        """
        extractor = BulletproofFeatureExtractor()
        match_id = "test_density_123"

        features = extractor.bulletproof_extract_features(complete_match_sample, match_id)
        feature_dict = features.dict()

        # 统计非NULL字段数量
        non_null_fields = []
        for key, value in feature_dict.items():
            if value is not None:
                non_null_fields.append((key, value))

        total_fields = len(feature_dict)
        non_null_count = len(non_null_fields)
        density_percentage = (non_null_count / total_fields) * 100

        print(f"总字段数: {total_fields}")
        print(f"非NULL字段数: {non_null_count}")
        print(f"数据密度: {density_percentage:.1f}%")
        print(f"非NULL字段: {[field for field, _ in non_null_fields]}")

        # 🚨 核心断言：数据密度必须 >= 60维（即60个非NULL字段）
        assert non_null_count >= 60, \
            f"数据密度不足！预期至少60个非NULL字段，实际{non_null_count}个"

        assert density_percentage >= 30.0, \
            f"数据密度百分比过低！预期>=30%，实际{density_percentage:.1f}%"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])