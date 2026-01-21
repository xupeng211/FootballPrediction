#!/usr/bin/env python3
"""
V1.2.1 L3 特征提取器单元测试 (Golden Mocking)
===============================================

测试范围:
1. 防御性转换 - 缺失字段、异常类型、无效值
2. Periods 缺失处理
3. 数据质量评级 (full/partial/failed)
4. 警告信息生成
5. lineup 和 player_rating 提取

数据来源: 真实 FotMob API 数据样本 (match_id: 4535624)
"""

import sys
from pathlib import Path

import pytest

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.collectors.l3_feature_processor_v38_5_1 import (
    L3FeatureExtractor,
    L3MatchFeatures,
)


class TestDefensiveConversion:
    """防御性转换测试"""

    @pytest.fixture
    def extractor(self):
        """创建提取器实例"""
        return L3FeatureExtractor()

    def test_normal_case(self, extractor):
        """测试正常情况 - 基于 Golden Sample"""
        raw_json = {
            "raw_data": {
                "content": {
                    "stats": {
                        "Periods": {
                            "All": {
                                "stats": [
                                    {
                                        "key": "top_stats",
                                        "stats": [
                                            {
                                                "key": "BallPossesion",
                                                "type": "graph",
                                                "stats": [46, 54],
                                            },
                                            {
                                                "key": "expected_goals",
                                                "type": "text",
                                                "stats": ["0.61", "0.27"],
                                            },
                                            {
                                                "key": "shots_on_target",
                                                "type": "text",
                                                "stats": [4, 1],
                                            },
                                        ],
                                    }
                                ]
                            }
                        }
                    },
                    "lineup": {
                        "homeTeam": {
                            "starters": [
                                {"performance": {"rating": 6.4}},
                                {"performance": {"rating": 7.1}},
                                {"performance": {"rating": 6.9}},
                            ]
                        },
                        "awayTeam": {
                            "starters": [
                                {"performance": {"rating": 6.5}},
                                {"performance": {"rating": 6.8}},
                                {"performance": {"rating": 6.7}},
                            ]
                        },
                    },
                }
            }
        }

        features = extractor.process_json(
            raw_json=raw_json,
            match_id="test_001",
            league_id=47,
            season="24/25",
        )

        # 验证特征提取成功
        assert features.home_xg == 0.61
        assert features.away_xg == 0.27
        assert features.home_possession == 46
        assert features.away_possession == 54
        # 应该有球员评分
        assert features.home_avg_player_rating is not None
        assert features.away_avg_player_rating is not None
        # 至少是 partial
        assert features.extraction_quality in ["full", "partial"]

    def test_missing_periods(self, extractor):
        """测试 Periods 缺失"""
        raw_json = {
            "raw_data": {
                "content": {
                    "stats": {}  # 没有 Periods
                }
            }
        }

        features = extractor.process_json(
            raw_json=raw_json,
            match_id="test_002",
            league_id=47,
            season="24/25",
        )

        # 应该降级为 failed 质量
        assert features.extraction_quality == "failed"
        assert features.valid_feature_count == 0

    def test_empty_stats_array(self, extractor):
        """测试空 stats 数组"""
        raw_json = {
            "raw_data": {
                "content": {
                    "stats": {
                        "Periods": {
                            "All": {
                                "stats": []  # 空数组
                            }
                        }
                    }
                }
            }
        }

        features = extractor.process_json(
            raw_json=raw_json,
            match_id="test_003",
            league_id=47,
            season="24/25",
        )

        assert features.valid_feature_count == 0
        assert features.extraction_quality == "failed"

    def test_invalid_value_patterns(self, extractor):
        """测试无效值模式 (-, N/A, NA, --, null)"""
        raw_json = {
            "raw_data": {
                "content": {
                    "stats": {
                        "Periods": {
                            "All": {
                                "stats": [
                                    {
                                        "key": "top_stats",
                                        "stats": [
                                            {
                                                "key": "expected_goals",
                                                "stats": ["-", "--"],  # 无效值
                                            },
                                            {
                                                "key": "BallPossesion",
                                                "stats": ["N/A", "NA"],  # 无效值
                                            },
                                        ],
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        }

        features = extractor.process_json(
            raw_json=raw_json,
            match_id="test_004",
            league_id=47,
            season="24/25",
        )

        # 无效值应该被过滤，返回 None
        assert features.home_xg is None
        assert features.home_possession is None

    def test_type_safety_edge_cases(self, extractor):
        """测试类型安全边界情况"""
        raw_json = {
            "raw_data": {
                "content": {
                    "stats": {
                        "Periods": {
                            "All": {
                                "stats": [
                                    {
                                        "key": "top_stats",
                                        "stats": [
                                            {
                                                "key": "expected_goals",
                                                "stats": [None, ""],  # None 和空字符串
                                            },
                                            {
                                                "key": "BallPossesion",
                                                "stats": [
                                                    "invalid",
                                                    "123",
                                                ],  # 无效字符串 + 数字字符串
                                            },
                                        ],
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        }

        features = extractor.process_json(
            raw_json=raw_json,
            match_id="test_005",
            league_id=47,
            season="24/25",
        )

        # None 应该保持 None
        assert features.home_xg is None
        # 数字字符串应该被解析，但被限制在 100 以内
        assert features.away_possession == 100.0  # min(123, 100) = 100


class TestLineupAndPlayerRatings:
    """lineup 和 player_rating 提取测试"""

    @pytest.fixture
    def extractor(self):
        """创建提取器实例"""
        return L3FeatureExtractor()

    def test_lineup_missing(self, extractor):
        """测试 lineup 缺失"""
        raw_json = {
            "raw_data": {
                "content": {
                    "stats": {
                        "Periods": {
                            "All": {
                                "stats": [
                                    {
                                        "key": "top_stats",
                                        "stats": [
                                            {"key": "expected_goals", "stats": ["1.5", "1.2"]},
                                        ],
                                    }
                                ]
                            }
                        }
                    }
                    # 没有 lineup
                }
            }
        }

        features = extractor.process_json(
            raw_json=raw_json,
            match_id="test_lineup_missing",
            league_id=47,
            season="24/25",
        )

        # xG 应该能提取
        assert features.home_xg == 1.5
        # 球员评分应该缺失
        assert features.home_avg_player_rating is None
        assert features.away_avg_player_rating is None
        # 应该有警告
        assert len(features.warnings) > 0

    def test_lineup_empty_teams(self, extractor):
        """测试 lineup 中球队数据缺失"""
        raw_json = {
            "raw_data": {
                "content": {
                    "stats": {
                        "Periods": {
                            "All": {
                                "stats": [
                                    {
                                        "key": "top_stats",
                                        "stats": [
                                            {"key": "expected_goals", "stats": ["1.5", "1.2"]},
                                        ],
                                    }
                                ]
                            }
                        }
                    },
                    "lineup": {
                        # 缺少 awayTeam
                        "homeTeam": {
                            "starters": [
                                {"performance": {"rating": 7.2}},
                                {"performance": {"rating": 7.0}},
                            ]
                        }
                    },
                }
            }
        }

        features = extractor.process_json(
            raw_json=raw_json,
            match_id="test_lineup_partial",
            league_id=47,
            season="24/25",
        )

        # 主队评分应该能提取
        assert features.home_avg_player_rating is not None
        # 客队评分应该缺失
        assert features.away_avg_player_rating is None

    def test_player_ratings_extraction(self, extractor):
        """测试球员评分提取"""
        raw_json = {
            "raw_data": {
                "content": {
                    "stats": {
                        "Periods": {
                            "All": {
                                "stats": [
                                    {
                                        "key": "top_stats",
                                        "stats": [
                                            {"key": "expected_goals", "stats": ["1.5", "1.2"]},
                                        ],
                                    }
                                ]
                            }
                        }
                    },
                    "lineup": {
                        "homeTeam": {
                            "starters": [
                                {"performance": {"rating": 7.5}},
                                {"performance": {"rating": 7.0}},
                                {"performance": {"rating": 6.8}},
                                {"performance": {"rating": 7.2}},
                            ]
                        },
                        "awayTeam": {
                            "starters": [
                                {"performance": {"rating": 6.9}},
                                {"performance": {"rating": 6.5}},
                                {"performance": {"rating": 7.1}},
                                {"performance": {"rating": 6.7}},
                            ]
                        },
                    },
                }
            }
        }

        features = extractor.process_json(
            raw_json=raw_json,
            match_id="test_ratings",
            league_id=47,
            season="24/25",
        )

        # 验证评分提取
        assert features.home_avg_player_rating is not None
        assert features.away_avg_player_rating is not None
        # 计算平均值验证
        expected_home_avg = (7.5 + 7.0 + 6.8 + 7.2) / 4
        expected_away_avg = (6.9 + 6.5 + 7.1 + 6.7) / 4
        assert abs(features.home_avg_player_rating - expected_home_avg) < 0.01
        assert abs(features.away_avg_player_rating - expected_away_avg) < 0.01

    def test_player_ratings_missing_rating_field(self, extractor):
        """测试球员缺少 rating 字段"""
        raw_json = {
            "raw_data": {
                "content": {
                    "stats": {
                        "Periods": {
                            "All": {
                                "stats": [
                                    {
                                        "key": "top_stats",
                                        "stats": [
                                            {"key": "expected_goals", "stats": ["1.5", "1.2"]},
                                        ],
                                    }
                                ]
                            }
                        }
                    },
                    "lineup": {
                        "homeTeam": {
                            "starters": [
                                {"name": "Player1"},  # 缺少 performance
                                {"performance": {"rating": 7.0}},
                            ]
                        },
                        "awayTeam": {
                            "starters": [
                                {"performance": {"rating": 6.9}},
                            ]
                        },
                    },
                }
            }
        }

        features = extractor.process_json(
            raw_json=raw_json,
            match_id="test_ratings_missing",
            league_id=47,
            season="24/25",
        )

        # 有 rating 的球员应该被计算
        assert features.home_avg_player_rating == 7.0
        assert features.away_avg_player_rating == 6.9


class TestDataQualityRating:
    """数据质量评级测试"""

    @pytest.fixture
    def extractor(self):
        """创建提取器实例"""
        return L3FeatureExtractor()

    def test_full_quality_rating(self, extractor):
        """测试 FULL 质量评级 (≥10 特征)"""
        raw_json = {
            "raw_data": {
                "content": {
                    "stats": {
                        "Periods": {
                            "All": {
                                "stats": [
                                    {
                                        "key": "top_stats",
                                        "stats": [
                                            {"key": "expected_goals", "stats": ["1.5", "1.2"]},
                                            {"key": "BallPossesion", "stats": ["50", "50"]},
                                            {"key": "ShotsOnTarget", "stats": ["5", "3"]},
                                            {"key": "big_chance", "stats": ["3", "2"]},
                                        ],
                                    }
                                ]
                            }
                        }
                    },
                    "lineup": {
                        "homeTeam": {
                            "starters": [
                                {"performance": {"rating": 7.2}},
                                {"performance": {"rating": 7.0}},
                                {"performance": {"rating": 6.8}},
                                {"performance": {"rating": 7.1}},
                                {"performance": {"rating": 6.9}},
                            ]
                        },
                        "awayTeam": {
                            "starters": [
                                {"performance": {"rating": 6.7}},
                                {"performance": {"rating": 6.5}},
                                {"performance": {"rating": 6.9}},
                                {"performance": {"rating": 6.8}},
                                {"performance": {"rating": 6.6}},
                            ]
                        },
                    },
                }
            }
        }

        features = extractor.process_json(
            raw_json=raw_json,
            match_id="test_full",
            league_id=47,
            season="24/25",
        )

        # 应该是 full 质量
        assert features.extraction_quality == "full"

    def test_partial_quality_rating(self, extractor):
        """测试 PARTIAL 质量评级 (5-9 特征)"""
        raw_json = {
            "raw_data": {
                "content": {
                    "stats": {
                        "Periods": {
                            "All": {
                                "stats": [
                                    {
                                        "key": "top_stats",
                                        "stats": [
                                            {"key": "expected_goals", "stats": ["1.5", "1.2"]},
                                            {"key": "BallPossesion", "stats": ["50", "50"]},
                                            {"key": "ShotsOnTarget", "stats": ["5", "3"]},
                                        ],
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        }

        features = extractor.process_json(
            raw_json=raw_json,
            match_id="test_partial",
            league_id=47,
            season="24/25",
        )

        # 应该是 partial (有 6 个特征: home_xg, away_xg, home_poss, away_poss, home_sot, away_sot)
        assert features.extraction_quality == "partial"

    def test_failed_quality_rating(self, extractor):
        """测试 FAILED 质量评级 (<5 特征)"""
        raw_json = {
            "raw_data": {
                "content": {
                    "stats": {
                        "Periods": {
                            "All": {
                                "stats": [
                                    {
                                        "key": "top_stats",
                                        "stats": [
                                            {"key": "expected_goals", "stats": ["1.5", "1.2"]},
                                        ],
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        }

        features = extractor.process_json(
            raw_json=raw_json,
            match_id="test_failed",
            league_id=47,
            season="24/25",
        )

        # 只有 2 个特征，应该是 failed
        assert features.extraction_quality == "failed"


class TestL3MatchFeaturesDataclass:
    """L3MatchFeatures 数据类测试"""

    def test_quality_metrics_calculation(self):
        """测试质量指标自动计算"""
        features = L3MatchFeatures(
            match_id="test_001",
            league_id=47,
            season="24/25",
            home_xg=2.1,
            away_xg=1.8,
            home_possession=65,
            away_possession=35,
        )

        # 有效特征数应该自动计算
        assert features.valid_feature_count >= 4

    def test_extraction_quality_assignment(self):
        """测试质量等级自动分配"""
        # Full 质量 (≥10 特征)
        features_full = L3MatchFeatures(
            match_id="test_001",
            league_id=47,
            season="24/25",
            home_xg=2.1,
            away_xg=1.8,
            home_possession=65,
            away_possession=35,
            home_shots_on_target=7,
            away_shots_on_target=4,
            home_big_chances=3,
            away_big_chances=2,
            avg_player_rating=7.0,
            home_avg_player_rating=7.1,
            away_avg_player_rating=6.9,
        )
        assert features_full.extraction_quality == "full"

        # Failed 质量 (<5 特征)
        features_failed = L3MatchFeatures(
            match_id="test_002",
            league_id=47,
            season="24/25",
            home_xg=2.1,
        )
        assert features_failed.extraction_quality == "failed"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
