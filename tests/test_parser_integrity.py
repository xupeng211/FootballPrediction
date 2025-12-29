#!/usr/bin/env python3
"""
V12.3 解析引擎完整性验证测试
验证parse_raw_json_to_db是否会"买椟还珠"，确保数据提取的准确性
"""

import json
import logging
from unittest.mock import MagicMock, patch

import pytest

from src.api.collectors.fotmob_core import FotMobCoreCollector

# 设置测试日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestParserIntegrity:
    """解析引擎完整性测试套件"""

    @pytest.fixture
    def collector(self):
        """初始化FotMob采集器实例"""
        return FotMobCoreCollector()

    @pytest.fixture
    def real_l2_json_sample(self):
        """构造真实的L2 JSON样本"""
        return {
            "header": {
                "teams": [{"name": "Manchester City", "id": 8456}, {"name": "Chelsea", "id": 8455}],
                "status": {"utcTime": "2024-12-22T15:00:00Z", "finished": True, "scoreStr": "3-1"},
                "league": {"name": "Premier League", "id": 2},
                "venue": {"name": "Etihad Stadium"},
            },
            "content": {
                "stats": {
                    "Periods": {
                        "All": {
                            "stats": [
                                {
                                    "stats": [
                                        {"key": "homeTeam", "value": {"name": "Manchester City"}},
                                        {"key": "awayTeam", "value": {"name": "Chelsea"}},
                                        {"key": "homeScore", "value": 3},
                                        {"key": "awayScore", "value": 1},
                                        {"key": "expected_goals", "value": {"home": 2.3, "away": 0.8}},
                                        {"key": "ball_possession", "value": {"home": 65, "away": 35}},
                                        {"key": "shots", "value": {"home": 18, "away": 12}},
                                        {"key": "shots_on_target", "value": {"home": 7, "away": 3}},
                                        {"key": "passes", "value": {"home": 580, "away": 320}},
                                        {"key": "passes_accuracy", "value": {"home": 88, "away": 82}},
                                        {"key": "aerial_duels_won", "value": {"home": 25, "away": 18}},
                                        {"key": "tackles", "value": {"home": 15, "away": 22}},
                                        {"key": "interceptions", "value": {"home": 12, "away": 18}},
                                        {"key": "clearances", "value": {"home": 8, "away": 15}},
                                        {"key": "blocks", "value": {"home": 5, "away": 8}},
                                        {"key": "key_passes", "value": {"home": 14, "away": 8}},
                                        {"key": "big_chances_created", "value": {"home": 4, "away": 1}},
                                    ]
                                }
                            ]
                        }
                    }
                },
                "playerStats": {
                    "home": [
                        {
                            "name": "Kevin De Bruyne",
                            "shirtNumber": 17,
                            "position": "Midfielder",
                            "stats": {
                                "shots": 3,
                                "shots_on_target": 2,
                                "expected_goals": 0.35,
                                "expected_assists": 0.6,
                                "key_passes": 5,
                                "passes": 85,
                                "pass_accuracy": 92,
                                "touches": 105,
                                "aerial_duels_won": 2,
                                "tackles": 3,
                                "interceptions": 2,
                                "clearances": 0,
                                "blocks": 1,
                                "big_chances_created": 2,
                                "dribbles_completed": 4,
                                "fouls": 1,
                            },
                        },
                        {
                            "name": "Erling Haaland",
                            "shirtNumber": 9,
                            "position": "Forward",
                            "stats": {
                                "shots": 6,
                                "shots_on_target": 3,
                                "expected_goals": 1.2,
                                "expected_assists": 0.1,
                                "key_passes": 1,
                                "passes": 22,
                                "pass_accuracy": 86,
                                "touches": 45,
                                "aerial_duels_won": 7,
                                "tackles": 0,
                                "interceptions": 1,
                                "clearances": 0,
                                "blocks": 0,
                                "big_chances_created": 2,
                                "dribbles_completed": 2,
                                "fouls": 2,
                            },
                        },
                    ],
                    "away": [
                        {
                            "name": "Enzo Fernández",
                            "shirtNumber": 8,
                            "position": "Midfielder",
                            "stats": {
                                "shots": 1,
                                "shots_on_target": 0,
                                "expected_goals": 0.05,
                                "expected_assists": 0.2,
                                "key_passes": 3,
                                "passes": 78,
                                "pass_accuracy": 89,
                                "touches": 95,
                                "aerial_duels_won": 3,
                                "tackles": 4,
                                "interceptions": 3,
                                "clearances": 2,
                                "blocks": 1,
                                "big_chances_created": 0,
                                "dribbles_completed": 1,
                                "fouls": 3,
                            },
                        }
                    ],
                },
            },
        }

    def test_parse_match_score_accuracy(self, collector, real_l2_json_sample):
        """测试: 比分提取准确性验证"""
        logger.info("🧪 测试比分提取准确性")

        # 创建模拟数据库记录
        mock_record = (1, 12345)  # id, external_id
        mock_record_dict = {"id": 1, "external_id": 12345, "l2_raw_json": json.dumps(real_l2_json_sample)}

        # 解析比分
        result = collector._parse_match_score(mock_record)

        # 验证比分提取准确性
        assert result is not None, "比分解析结果不应该为空"
        assert "result_score" in result, "应该包含result_score字段"
        assert "actual_result" in result, "应该包含actual_result字段"

        # 验证具体比分值
        expected_score = "3-1"
        expected_result = "H"  # Home win

        assert result["result_score"] == expected_score, f"比分应该是{expected_score}，实际是{result['result_score']}"
        assert result["actual_result"] == expected_result, (
            f"结果应该是{expected_result}，实际是{result['actual_result']}"
        )

        # 验证提取的原始数据
        assert "home_score" in result, "应该包含home_score字段"
        assert "away_score" in result, "应该包含away_score字段"
        assert result["home_score"] == 3, f"主队比分应该是3，实际是{result['home_score']}"
        assert result["away_score"] == 1, f"客队比分应该是1，实际是{result['away_score']}"

        logger.success(f"✅ 比分提取准确: {result['result_score']} ({result['actual_result']})")

    def test_technical_features_extraction(self, collector, real_l2_json_sample):
        """测试: 179维技术特征提取"""
        logger.info("🧪 测试179维技术特征提取")

        # 创建模拟数据库记录
        mock_record = (1, 12345)
        mock_record_dict = {"id": 1, "external_id": 12345, "l2_raw_json": json.dumps(real_l2_json_sample)}

        # 提取技术特征
        features = collector._parse_technical_features(mock_record)

        # 验证特征提取结果
        assert features is not None, "技术特征提取结果不应该为空"

        # 验证核心指标存在且非空
        core_metrics = [
            "home_shots",
            "away_shots",
            "total_shots",
            "diff_shots",
            "ratio_shots",
            "home_shotsontarget",
            "away_shotsontarget",
            "total_shotsontarget",
            "diff_shotsontarget",
            "ratio_shotsontarget",
            "home_xg",
            "away_xg",
            "total_xg",
            "diff_xg",
            "ratio_xg",
            "home_passes",
            "away_passes",
            "total_passes",
            "diff_passes",
            "ratio_passes",
            "home_possession",
            "away_possession",
            "total_possession",
            "diff_possession",
            "ratio_possession",
        ]

        for metric in core_metrics:
            assert metric in features, f"应该包含{metric}指标"
            assert features[metric] >= 0, f"{metric}应该是非负数，实际是{features[metric]}"

        # 验证主队指标与预期值一致
        assert features["home_shots"] == 18, f"主队射门应该是18，实际是{features['home_shots']}"
        assert features["away_shots"] == 12, f"客队射门应该是12，实际是{features['away_shots']}"
        assert features["home_xg"] == pytest.approx(2.3, rel=1e-2), f"主队xG应该是2.3，实际是{features['home_xg']}"
        assert features["away_xg"] == pytest.approx(0.8, rel=1e-2), f"客队xG应该是0.8，实际是{features['away_xg']}"
        assert features["home_possession"] == 65, f"主队控球率应该是65，实际是{features['home_possession']}"
        assert features["away_possession"] == 35, f"客队控球率应该是35，实际是{features['away_possession']}"

        # 验证衍生计算正确性
        assert features["total_shots"] == 30, f"总射门应该是30，实际是{features['total_shots']}"
        assert features["diff_shots"] == 6, f"射门差值应该是6，实际是{features['diff_shots']}"
        assert features["ratio_shots"] == pytest.approx(1.5, rel=1e-2), (
            f"射门比率应该是1.5，实际是{features['ratio_shots']}"
        )

        logger.success(f"✅ 技术特征提取成功: 提取了{len(features)}个维度指标")

    def test_player_stats_data_integrity(self, collector, real_l2_json_sample):
        """测试: 球员统计数据完整性"""
        logger.info("🧪 测试球员统计数据完整性")

        # 检查JSON中的球员统计数据结构
        player_stats = real_l2_json_sample["content"]["playerStats"]

        # 验证主客队数据存在
        assert "home" in player_stats, "应该包含主队球员统计"
        assert "away" in player_stats, "应该包含客队球员统计"
        assert len(player_stats["home"]) > 0, "主队球员数据不应该为空"
        assert len(player_stats["away"]) > 0, "客队球员数据不应该为空"

        # 验证球员数据结构完整性
        home_players = player_stats["home"]
        for player in home_players:
            assert "name" in player, "球员应该有姓名"
            assert "stats" in player, "球员应该有统计数据"
            assert isinstance(player["stats"], dict), "球员统计数据应该是字典类型"

            # 验证核心技术指标存在
            core_player_metrics = ["shots", "passes", "expected_goals", "touches", "tackles"]
            for metric in core_player_metrics:
                assert metric in player["stats"], f"球员统计应该包含{metric}"

        logger.success(f"✅ 球员统计数据完整: 主队{len(home_players)}名球员, 客队{len(player_stats['away'])}名球员")

    @patch("src.api.collectors.fotmob_core.psycopg2.connect")
    def test_parse_raw_json_to_db_integration(self, mock_connect, collector, real_l2_json_sample):
        """测试: parse_raw_json_to_db集成测试"""
        logger.info("🧪 测试parse_raw_json_to_db集成功能")

        # 设置模拟数据库连接
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        # 模拟查询返回未解析的记录
        mock_cursor.fetchall.return_value = [(1, 12345, json.dumps(real_l2_json_sample))]
        mock_cursor.fetchone.return_value = None  # ID冲突测试

        # 执行解析
        with patch.object(collector, "get_database_connection", return_value=mock_conn):
            processed_count = collector.parse_raw_json_to_db(limit=1)

        # 验证解析执行
        assert processed_count >= 0, "处理记录数应该大于等于0"

        # 验证数据库操作被调用
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()

        logger.success(f"✅ parse_raw_json_to_db集成测试通过: 处理了{processed_count}条记录")

    def test_feature_dimension_completeness(self, collector, real_l2_json_sample):
        """测试: 特征维度完整性验证"""
        logger.info("🧪 测试特征维度完整性")

        # 创建模拟记录
        mock_record = (1, 12345)
        mock_record_dict = {"id": 1, "external_id": 12345, "l2_raw_json": json.dumps(real_l2_json_sample)}

        # 提取特征
        features = collector._parse_technical_features(mock_record)

        # 验证特征维度数量合理
        feature_count = len(features)
        assert feature_count >= 50, f"特征维度应该至少50个，实际是{feature_count}"

        # 验证特征命名规范性
        feature_names = list(features.keys())

        # 检查是否包含预期的特征命名模式
        expected_patterns = [
            lambda name: name.startswith("home_"),
            lambda name: name.startswith("away_"),
            lambda name: name.startswith("total_"),
            lambda name: name.startswith("diff_"),
            lambda name: name.startswith("ratio_"),
        ]

        pattern_matches = 0
        for pattern in expected_patterns:
            matches = sum(1 for name in feature_names if pattern(name))
            if matches > 0:
                pattern_matches += 1
                logger.info(f"✅ 特征命名模式匹配: {matches}个特征")

        assert pattern_matches >= 4, f"应该匹配至少4种特征命名模式，实际匹配{pattern_matches}种"

        logger.success(f"✅ 特征维度完整验证通过: {feature_count}个维度，{pattern_matches}种命名模式")

    def test_data_type_consistency(self, collector, real_l2_json_sample):
        """测试: 数据类型一致性验证"""
        logger.info("🧪 测试数据类型一致性")

        # 创建模拟记录
        mock_record = (1, 12345)
        mock_record_dict = {"id": 1, "external_id": 12345, "l2_raw_json": json.dumps(real_l2_json_sample)}

        # 提取特征
        features = collector._parse_technical_features(mock_record)

        # 验证所有特征值都是数值类型
        for feature_name, feature_value in features.items():
            assert isinstance(feature_value, (int, float)), (
                f"特征{feature_name}应该是数值类型，实际是{type(feature_value)}"
            )
            assert not isinstance(feature_value, bool), f"特征{feature_name}不应该是布尔类型"
            assert not (isinstance(feature_value, float) and (feature_value != feature_value)), (
                f"特征{feature_name}不应该是NaN"
            )

        logger.success(f"✅ 数据类型一致性验证通过: {len(features)}个特征全部为数值类型")


if __name__ == "__main__":
    # 直接运行测试
    pytest.main([__file__, "-v", "-s"])
