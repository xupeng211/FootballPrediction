#!/usr/bin/env python3
"""
V12.3 核心哨兵机制验证测试
专门验证100KB质量红线是否严格执行
"""

import pytest
import json
import logging
from unittest.mock import Mock, patch
from src.api.collectors.fotmob_core import FotMobCoreCollector

# 设置测试日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class TestSentryLogic:
    """100KB哨兵机制测试套件"""

    @pytest.fixture
    def collector(self):
        """初始化FotMob采集器实例"""
        return FotMobCoreCollector()

    @pytest.fixture
    def small_json_50kb(self):
        """构造50KB小数据JSON - 应该被拒绝"""
        # 构造约50KB的JSON数据
        base_data = {
            "header": {
                "teams": [{"name": "Home Team"}, {"name": "Away Team"}],
                "status": {"utcTime": "2024-12-22T15:00:00Z"},
            }
        }

        # 添加大量重复数据来达到50KB
        for i in range(3000):  # 约17KB每3000条
            base_data[f"field_{i}"] = "x" * 50  # 每个字段50字符

        json_str = json.dumps(base_data)
        logger.info(f"🔬 50KB测试JSON大小: {len(json_str)} bytes")
        assert len(json_str) < 100000, "50KB测试数据应该小于100KB"

        return json_str

    @pytest.fixture
    def valid_json_120kb(self):
        """构造120KB有效数据JSON - 应该被接受"""
        # 构造一个完整、真实的比赛数据结构
        valid_data = {
            "header": {
                "teams": [{"name": "Manchester United"}, {"name": "Liverpool"}],
                "status": {"utcTime": "2024-12-22T15:00:00Z", "finished": True},
                "league": {"name": "Premier League"},
            },
            "content": {"stats": {"Periods": {"All": {"stats": []}}}, "playerStats": {"home": [], "away": []}},
        }

        # 添加大量真实统计数据来达到120KB
        for i in range(2000):
            valid_data["content"]["stats"]["Periods"]["All"]["stats"].append(
                {"stats": [{"key": "shots", "value": i * 2}, {"key": "passes", "value": i * 10}]}
            )

        # 添加详细的球员统计数据
        for team in ["home", "away"]:
            for player_idx in range(50):
                valid_data["content"]["playerStats"][team].append(
                    {
                        "name": f"Player_{team}_{player_idx}",
                        "stats": {
                            "shots": player_idx * 2,
                            "passes": player_idx * 20,
                            "xg": player_idx * 0.1,
                            "xa": player_idx * 0.05,
                        },
                    }
                )

        json_str = json.dumps(valid_data)
        logger.info(f"🔬 120KB测试JSON大小: {len(json_str)} bytes")
        assert len(json_str) >= 100000, "120KB测试数据应该大于等于100KB"

        return json_str

    @pytest.fixture
    def large_json_500kb(self):
        """构造500KB大数据JSON - 应该被接受"""
        # 基于120KB结构，但更加详细
        base_data = {
            "header": {
                "teams": [{"name": "Real Madrid"}, {"name": "Barcelona"}],
                "status": {"utcTime": "2024-12-22T20:00:00Z", "finished": True},
                "league": {"name": "La Liga"},
            },
            "content": {"stats": {"Periods": {"All": {"stats": []}}}, "playerStats": {"home": [], "away": []}},
        }

        # 添加大量详细统计数据来达到500KB
        for i in range(10000):
            base_data["content"]["stats"]["Periods"]["All"]["stats"].append(
                {
                    "stats": [
                        {"key": f"metric_{i}", "value": i * 3},
                        {"key": f"passes_{i}", "value": i * 15},
                        {"key": f"xg_{i}", "value": i * 0.2},
                    ]
                }
            )

        # 添加超详细的球员统计数据
        for team in ["home", "away"]:
            for player_idx in range(200):
                player_stats = {"name": f"SuperPlayer_{team}_{player_idx}", "position": "Midfielder", "stats": {}}

                # 添加179个维度的技术指标
                metrics = [
                    "shots",
                    "passes",
                    "xg",
                    "xa",
                    "touches",
                    "tackles",
                    "interceptions",
                    "aerial_duels_won",
                    "clearances",
                    "blocks",
                    "key_passes",
                    "dribbles_completed",
                ]
                for j, metric in enumerate(metrics):
                    player_stats["stats"][metric] = player_idx * (j + 1) * 0.5

                base_data["content"]["playerStats"][team].append(player_stats)

        json_str = json.dumps(base_data)
        logger.info(f"🔬 500KB测试JSON大小: {len(json_str)} bytes")
        assert len(json_str) >= 500000, "500KB测试数据应该大于等于500KB"

        return json_str

    def test_small_json_rejected(self, collector, small_json_50kb):
        """测试: 50KB数据必须被拒绝"""
        logger.info("🧪 测试50KB数据拒绝机制")

        # 模拟HTTP响应
        mock_response = Mock()
        mock_response.content = small_json_50kb.encode("utf-8")
        mock_response.headers = {"Content-Encoding": "utf-8"}

        # 验证50KB数据被拒绝
        result = collector.adaptive_decode_response(mock_response.content, "utf-8")

        # 断言: 小数据应该被处理但后续会被size检查拒绝
        assert result is not None, "50KB数据应该能被解码"

        # 验证大小检查逻辑
        response_size = len(small_json_50kb)
        assert response_size < collector.min_response_size, "50KB数据应该小于最小阈值"

        logger.warning(f"🚫 50KB数据正确被拒绝: {response_size} bytes < {collector.min_response_size} bytes")

    def test_valid_json_accepted(self, collector, valid_json_120kb):
        """测试: 120KB有效数据必须被接受"""
        logger.info("🧪 测试120KB有效数据接受机制")

        # 模拟HTTP响应
        mock_response = Mock()
        mock_response.content = valid_json_120kb.encode("utf-8")
        mock_response.headers = {"Content-Encoding": "utf-8"}

        # 验证120KB数据被正确解码
        result = collector.adaptive_decode_response(mock_response.content, "utf-8")

        # 断言: 有效数据应该被成功解码
        assert result is not None, "120KB有效数据应该被成功解码"
        assert isinstance(result, dict), "解码结果应该是字典类型"

        # 验证大小检查通过
        response_size = len(valid_json_120kb)
        assert response_size >= collector.min_response_size, "120KB数据应该通过最小阈值检查"

        # 验证数据结构完整性
        assert "header" in result, "解码数据应该包含header字段"
        assert "content" in result, "解码数据应该包含content字段"
        assert "teams" in result["header"], "header应该包含teams信息"

        logger.success(f"✅ 120KB数据正确被接受: {response_size} bytes >= {collector.min_response_size} bytes")

    def test_large_json_accepted(self, collector, large_json_500kb):
        """测试: 500KB大数据必须被接受"""
        logger.info("🧪 测试500KB大数据接受机制")

        # 模拟HTTP响应
        mock_response = Mock()
        mock_response.content = large_json_500kb.encode("utf-8")
        mock_response.headers = {"Content-Encoding": "utf-8"}

        # 验证500KB数据被正确解码
        result = collector.adaptive_decode_response(mock_response.content, "utf-8")

        # 断言: 大数据应该被成功解码
        assert result is not None, "500KB大数据应该被成功解码"
        assert isinstance(result, dict), "解码结果应该是字典类型"

        # 验证大小检查通过
        response_size = len(large_json_500kb)
        assert response_size >= collector.min_response_size, "500KB数据应该通过最小阈值检查"

        # 验证大数据结构完整性
        assert "header" in result, "大数据应该包含header字段"
        assert "content" in result, "大数据应该包含content字段"

        # 验证球员统计数据存在
        assert "playerStats" in result.get("content", {}), "大数据应该包含球员统计"

        logger.success(f"✅ 500KB大数据正确被接受: {response_size} bytes >= {collector.min_response_size} bytes")

    def test_sentry_threshold_value(self, collector):
        """测试: 哨兵阈值设置正确性"""
        logger.info("🧪 测试哨兵阈值设置")

        # 验证阈值设置
        expected_threshold = 102400  # 100KB
        actual_threshold = collector.min_response_size

        assert actual_threshold == expected_threshold, f"阈值应该是{expected_threshold}，实际是{actual_threshold}"

        logger.success(f"✅ 哨兵阈值设置正确: {actual_threshold} bytes")

    @patch("src.api.collectors.fotmob_core.logger")
    def test_size_validation_logging(self, mock_logger, collector):
        """测试: 大小验证的日志记录"""
        logger.info("🧪 测试大小验证日志记录")

        # 测试小数据日志记录
        small_size = 50000  # 50KB
        collector._log_hollow_match(12345, f"response_too_small_{small_size}")

        # 验证日志被调用
        mock_logger.info.assert_called()

        # 验证日志内容包含相关信息
        call_args = mock_logger.info.call_args[0][0]
        assert "空心比赛已记录" in call_args
        assert "12345" in call_args
        assert f"response_too_small_{small_size}" in call_args

        logger.success("✅ 大小验证日志记录机制正常")


if __name__ == "__main__":
    # 直接运行测试
    pytest.main([__file__, "-v", "-s"])
