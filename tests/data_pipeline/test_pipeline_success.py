#!/usr/bin/env python3
"""
管线成功验证测试
证明我们已经成功提取阵容、战术和射门细节特征
"""

import pytest
from src.data_access.processors.bulletproof_feature_extractor import BulletproofFeatureExtractor


class TestPipelineSuccess:
    """管线成功验证测试类"""

    def test_lineup_features_extraction_success(self):
        """测试: 阵容特征提取成功"""
        extractor = BulletproofFeatureExtractor()

        # 完整阵容数据
        test_data = {
            'content': {
                'lineup': {
                    'home': {
                        'formation': '4-3-3',
                        'players': [
                            {'name': 'Onana', 'rating': 7.2, 'stats': {'passes': 32, 'passAccuracy': 84.4, 'tackles': 1, 'interceptions': 2, 'clearances': 3}},
                            {'name': 'Maguire', 'rating': 6.8, 'stats': {'passes': 45, 'passAccuracy': 88.9, 'tackles': 3, 'interceptions': 4, 'clearances': 8}},
                            {'name': 'Fernandes', 'rating': 8.1, 'stats': {'passes': 56, 'passAccuracy': 79.6, 'tackles': 2, 'interceptions': 1, 'shotsTotal': 3}}
                        ]
                    },
                    'away': {
                        'formation': '4-3-3',
                        'players': [
                            {'name': 'Alisson', 'rating': 7.8, 'stats': {'passes': 28, 'passAccuracy': 85.7, 'saves': 6}},
                            {'name': 'Van Dijk', 'rating': 7.5, 'stats': {'passes': 52, 'passAccuracy': 90.4, 'tackles': 2, 'interceptions': 5}},
                            {'name': 'Salah', 'rating': 8.6, 'stats': {'passes': 22, 'passAccuracy': 77.3, 'shotsTotal': 5, 'goals': 1}}
                        ]
                    }
                }
            }
        }

        lineup_features = extractor.extract_lineup_features(test_data)

        # 🚨 核心断言：必须提取到阵容特征
        assert len(lineup_features) >= 15, f"阵容特征提取不足！预期>=15，实际{len(lineup_features)}"

        # 验证关键特征
        expected_features = [
            'home_lineup_count', 'away_lineup_count',
            'home_formation', 'away_formation',
            'home_avg_rating', 'away_avg_rating',
            'home_total_passes', 'away_total_passes',
            'home_pass_accuracy', 'away_pass_accuracy',
            'home_total_tackles', 'away_total_tackles',
            'home_total_interceptions', 'away_total_interceptions'
        ]

        found_features = [f for f in expected_features if f in lineup_features and lineup_features[f] is not None]

        print(f"✅ 阵容特征提取成功: {len(found_features)}/{len(expected_features)}个关键特征")
        print(f"📊 提取的特征: {list(lineup_features.keys())}")

        assert len(found_features) >= 10, f"关键阵容特征不足！预期>=10，实际{len(found_features)}"

        # 验证评分计算
        assert lineup_features['home_avg_rating'] == 7.37  # (7.2 + 6.8 + 8.1) / 3
        assert lineup_features['away_avg_rating'] == 7.97  # (7.8 + 7.5 + 8.6) / 3

        print(f"🎯 主队平均评分: {lineup_features['home_avg_rating']}")
        print(f"🎯 客队平均评分: {lineup_features['away_avg_rating']}")

    def test_tactical_features_extraction_success(self):
        """测试: 战术特征提取成功"""
        extractor = BulletproofFeatureExtractor()

        # 战术统计数据
        test_data = {
            'content': {
                'stats': {
                    'Periods': {
                        'All': {
                            'stats': [
                                {
                                    'stats': [
                                        {'key': 'big_chances_created', 'value': 3},
                                        {'key': 'big_chances_missed', 'value': 1},
                                        {'key': 'clearances', 'value': 18},
                                        {'key': 'interceptions', 'value': 12},
                                        {'key': 'tackles', 'value': 15},
                                        {'key': 'aerial_won', 'value': 22},
                                        {'key': 'passes', 'value': 423},
                                        {'key': 'pass_accuracy', 'value': 82.4}
                                    ]
                                },
                                {
                                    'stats': [
                                        {'key': 'big_chances_created', 'value': 5},
                                        {'key': 'big_chances_missed', 'value': 2},
                                        {'key': 'clearances', 'value': 14},
                                        {'key': 'interceptions', 'value': 18},
                                        {'key': 'tackles', 'value': 12},
                                        {'key': 'aerial_won', 'value': 18},
                                        {'key': 'passes', 'value': 567},
                                        {'key': 'pass_accuracy', 'value': 86.7}
                                    ]
                                }
                            ]
                        }
                    }
                }
            }
        }

        tactical_features = extractor.extract_tactical_features(test_data)

        # 🚨 核心断言：必须提取到战术特征
        assert len(tactical_features) >= 10, f"战术特征提取不足！预期>=10，实际{len(tactical_features)}"

        # 验证关键战术特征
        expected_tactical = [
            'home_big_chances', 'away_big_chances',
            'home_big_chances_missed', 'away_big_chances_missed',
            'home_clearances', 'away_clearances',
            'home_interceptions', 'away_interceptions',
            'home_tackles', 'away_tackles',
            'home_aerial_won', 'away_aerial_won',
            'home_passes', 'away_passes',
            'home_pass_accuracy', 'away_pass_accuracy'
        ]

        found_tactical = [f for f in expected_tactical if f in tactical_features and tactical_features[f] is not None]

        print(f"✅ 战术特征提取成功: {len(found_tactical)}/{len(expected_tactical)}个关键特征")
        print(f"📊 提取的特征: {list(tactical_features.keys())}")

        assert len(found_tactical) >= 8, f"关键战术特征不足！预期>=8，实际{len(found_tactical)}"

        # 验证数值
        assert tactical_features['home_big_chances'] == 3
        assert tactical_features['away_big_chances'] == 5
        assert tactical_features['home_clearances'] == 18
        assert tactical_features['away_clearances'] == 14

    def test_shotmap_features_extraction_success(self):
        """测试: Shotmap特征提取成功"""
        extractor = BulletproofFeatureExtractor()

        # 射门数据
        test_data = {
            'content': {
                'shotmap': {
                    'shots': [
                        {'team': 'home', 'player': 'Fernandes', 'expectedGoals': 0.12, 'isGoal': False, 'x': 75.2},
                        {'team': 'away', 'player': 'Salah', 'expectedGoals': 0.35, 'isGoal': True, 'x': 88.5},
                        {'team': 'home', 'player': 'Rashford', 'expectedGoals': 0.08, 'isGoal': False, 'x': 92.1},
                        {'team': 'away', 'player': 'Mane', 'expectedGoals': 0.22, 'isGoal': False, 'x': 70.3}
                    ]
                }
            }
        }

        shotmap_features = extractor.extract_shotmap_features(test_data)

        # 🚨 核心断言：必须提取到shotmap特征
        assert len(shotmap_features) >= 6, f"Shotmap特征提取不足！预期>=6，实际{len(shotmap_features)}"

        # 验证关键shotmap特征
        expected_shotmap = [
            'home_shots_from_shotmap', 'away_shots_from_shotmap',
            'home_xg_from_shotmap', 'away_xg_from_shotmap',
            'home_goals_shotmap', 'away_goals_shotmap',
            'home_shots_in_box', 'away_shots_in_box'
        ]

        found_shotmap = [f for f in expected_shotmap if f in shotmap_features and shotmap_features[f] is not None]

        print(f"✅ Shotmap特征提取成功: {len(found_shotmap)}/{len(expected_shotmap)}个关键特征")
        print(f"📊 提取的特征: {list(shotmap_features.keys())}")

        assert len(found_shotmap) >= 4, f"关键Shotmap特征不足！预期>=4，实际{len(found_shotmap)}"

        # 验证数值
        assert shotmap_features['home_shots_from_shotmap'] == 2
        assert shotmap_features['away_shots_from_shotmap'] == 2
        assert shotmap_features['home_xg_from_shotmap'] == 0.2  # 0.12 + 0.08
        assert shotmap_features['away_xg_from_shotmap'] == 0.57  # 0.35 + 0.22

    def test_total_feature_density_achievement(self):
        """测试: 总体特征密度达成目标"""
        extractor = BulletproofFeatureExtractor()

        # 完整测试数据
        complete_data = {
            'header': {
                'status': {'scoreStr': '2-1'},
                'teams': [{'name': 'Manchester United'}, {'name': 'Liverpool'}]
            },
            'content': {
                'lineup': {
                    'home': {
                        'formation': '4-3-3',
                        'players': [{'name': 'Test1', 'rating': 7.0, 'stats': {'passes': 30}}]
                    },
                    'away': {
                        'formation': '4-3-3',
                        'players': [{'name': 'Test2', 'rating': 7.5, 'stats': {'passes': 35}}]
                    }
                },
                'stats': {
                    'Periods': {
                        'All': {
                            'stats': [
                                {'stats': [{'key': 'big_chances_created', 'value': 3}]},
                                {'stats': [{'key': 'big_chances_created', 'value': 5}]}
                            ]
                        }
                    }
                },
                'shotmap': {
                    'shots': [
                        {'team': 'home', 'expectedGoals': 0.1, 'isGoal': False, 'x': 80},
                        {'team': 'away', 'expectedGoals': 0.2, 'isGoal': True, 'x': 90}
                    ]
                }
            }
        }

        # 提取所有特征类型
        lineup_features = extractor.extract_lineup_features(complete_data)
        tactical_features = extractor.extract_tactical_features(complete_data)
        shotmap_features = extractor.extract_shotmap_features(complete_data)

        # 合并所有特征
        all_features = {}
        all_features.update(lineup_features)
        all_features.update(tactical_features)
        all_features.update(shotmap_features)

        # 🚨 核心断言：总特征密度必须 >= 30
        total_features = len(all_features)
        non_null_features = len([v for v in all_features.values() if v is not None])

        print(f"🎯 总特征密度: {non_null_features}/{total_features} ({non_null_features/total_features*100:.1f}%)")
        print(f"📊 阵容特征: {len(lineup_features)}个")
        print(f"📊 战术特征: {len(tactical_features)}个")
        print(f"📊 Shotmap特征: {len(shotmap_features)}个")

        assert non_null_features >= 30, f"总特征密度不足！预期>=30，实际{non_null_features}"
        assert len(lineup_features) >= 10, f"阵容特征不足！预期>=10，实际{len(lineup_features)}"
        assert len(tactical_features) >= 2, f"战术特征不足！预期>=2，实际{len(tactical_features)}"
        assert len(shotmap_features) >= 4, f"Shotmap特征不足！预期>=4，实际{len(shotmap_features)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])