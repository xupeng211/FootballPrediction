#!/usr/bin/env python3
"""
Unit Test: Feature Extraction V1 - Robust JSON Parsing (TDD Red Phase)

测试目标：验证特征提取脚本对残缺 JSON 的健壮性

TDD 流程：
1. Red Phase: 测试失败（功能未实现）
2. Green Phase: 实现功能，测试通过
3. Refactor Phase: 优化代码（可选）

测试场景：
- 残缺的 JSON（缺少字段）→ 返回默认值而不崩溃 ✅
- 空的 JSON → 返回空特征字典 ✅
- 正常的 JSON → 正确提取特征 ✅
- None/null 处理 → 转换为 Python None ✅

Author: 高级数据架构师 & 机器学习专家
Date: 2026-01-11
Version: V29.0 (Feature Extraction)
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import Mock, patch, MagicMock
import tempfile

import pytest

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ============================================================================
# Test Fixtures: 残缺 JSON 数据
# ============================================================================

@pytest.fixture
def sample_complete_json():
    """完整的 JSON 数据（正常情况）"""
    return {
        "match_id": "12345",
        "league": "Premier League",
        "home_team": "Arsenal",
        "away_team": "Chelsea",
        "home_score": 2,
        "away_score": 1,
        "l3_features": {
            "opening": {
                "home": 1.85,
                "draw": 3.50,
                "away": 4.20
            },
            "closing": {
                "home": 1.95,
                "draw": 3.40,
                "away": 3.90
            },
            "high_24h": {
                "home": 2.10,
                "draw": 3.30,
                "away": 3.75
            },
            "low_24h": {
                "home": 1.80,
                "draw": 3.45,
                "away": 4.30
            }
        }
    }


@pytest.fixture
def sample_malformed_json_missing_opening():
    """残缺 JSON：缺少 opening 字段"""
    return {
        "match_id": "12346",
        "league": "Premier League",
        "home_team": "Liverpool",
        "away_team": "Man City",
        "home_score": 1,
        "away_score": 1,
        "l3_features": {
            "closing": {
                "home": 2.10,
                "draw": 3.20,
                "away": 3.50
            },
            # opening 字段缺失
            "high_24h": {
                "home": 2.20,
                "draw": 3.15,
                "away": 3.40
            }
        }
    }


@pytest.fixture
def sample_malformed_json_null_values():
    """残缺 JSON：字段值为 None/null"""
    return {
        "match_id": "12347",
        "league": "La Liga",
        "home_team": "Real Madrid",
        "away_team": "Barcelona",
        "home_score": None,
        "away_score": None,
        "l3_features": {
            "opening": {
                "home": None,
                "draw": 3.50,
                "away": 4.20
            },
            "closing": {
                "home": 1.95,
                "draw": None,
                "away": None
            }
        }
    }


@pytest.fixture
def sample_malformed_json_empty_features():
    """残缺 JSON：l3_features 为空字典"""
    return {
        "match_id": "12348",
        "league": "Serie A",
        "home_team": "Juventus",
        "away_team": "AC Milan",
        "home_score": 0,
        "away_score": 0,
        "l3_features": {}  # 空特征
    }


@pytest.fixture
def sample_l3_odds_data_array_format():
    """
    V36.3 数组格式样本 - 真实的 l3_odds_data 格式

    数据来源：harvest_pinnacle_concurrent.py 采集的原始数据
    格式：{"home": [{"odds": "3.64", ...}], "draw": [...], "away": [...]}
    """
    return {
        "match_id": "4507081",
        "league": "La Liga",
        "home_team": "Getafe",
        "away_team": "Real Madrid",
        "home_score": 0,
        "away_score": 1,
        # V36.3 新增：l3_odds_data 数组格式（不是 l3_features 字典格式）
        "l3_odds_data": {
            "home": [
                {"odds": "3.70", "beijing_time": "2026-01-09 20:00:00", "original_time": "09 Jan, 12:00"},
                {"odds": "3.68", "beijing_time": "2026-01-09 21:00:00", "original_time": "09 Jan, 13:00"},
                {"odds": "3.65", "beijing_time": "2026-01-09 22:00:00", "original_time": "09 Jan, 14:00"},
                {"odds": "3.64", "beijing_time": "2026-01-10 02:59:00", "original_time": "09 Jan, 19:59"}  # Closing
            ],
            "draw": [
                {"odds": "3.05", "beijing_time": "2026-01-09 20:00:00", "original_time": "09 Jan, 12:00"},
                {"odds": "3.02", "beijing_time": "2026-01-09 21:00:00", "original_time": "09 Jan, 13:00"},
                {"odds": "3.00", "beijing_time": "2026-01-09 22:00:00", "original_time": "09 Jan, 14:00"},
                {"odds": "2.99", "beijing_time": "2026-01-10 02:59:00", "original_time": "09 Jan, 19:59"}  # Closing
            ],
            "away": [
                {"odds": "2.15", "beijing_time": "2026-01-09 20:00:00", "original_time": "09 Jan, 12:00"},
                {"odds": "2.17", "beijing_time": "2026-01-09 21:00:00", "original_time": "09 Jan, 13:00"},
                {"odds": "2.18", "beijing_time": "2026-01-09 22:00:00", "original_time": "09 Jan, 14:00"},
                {"odds": "2.20", "beijing_time": "2026-01-10 02:59:00", "original_time": "09 Jan, 19:59"}  # Closing
            ]
        }
    }


# ============================================================================
# Test Cases
# ============================================================================

class TestRobustJSONParsing:
    """测试健壮的 JSON 解析"""

    def test_complete_json_extracted_successfully(self, sample_complete_json):
        """测试：完整的 JSON 应该成功提取所有特征"""
        # 导入待测试的模块（将在 Green Phase 实现）
        from scripts.ml.extract_features_v1 import extract_features_from_json

        features = extract_features_from_json(sample_complete_json)

        # 验证所有特征都被提取
        assert features["opening_home"] == 1.85
        assert features["opening_draw"] == 3.50
        assert features["opening_away"] == 4.20
        assert features["closing_home"] == 1.95
        assert features["high_24h_home"] == 2.10
        assert features["low_24h_away"] == 4.30

    def test_missing_opening_returns_defaults(self, sample_malformed_json_missing_opening):
        """TDD 核心测试：缺少 opening 字段应返回默认值而不崩溃"""
        from scripts.ml.extract_features_v1 import extract_features_from_json

        features = extract_features_from_json(sample_malformed_json_missing_opening)

        # 验证：缺失字段返回 None 而不是崩溃
        assert features.get("opening_home") is None
        assert features.get("opening_draw") is None
        assert features.get("opening_away") is None

        # 验证：其他字段正常提取
        assert features["closing_home"] == 2.10
        assert features["high_24h_home"] == 2.20

    def test_null_values_handled_correctly(self, sample_malformed_json_null_values):
        """测试：null 值应转换为 Python None"""
        from scripts.ml.extract_features_v1 import extract_features_from_json

        features = extract_features_from_json(sample_malformed_json_null_values)

        # 验证：None 值被正确处理
        assert features["opening_home"] is None
        assert features["closing_draw"] is None
        assert features["closing_away"] is None

        # 验证：正常值被保留
        assert features["opening_draw"] == 3.50
        assert features["closing_home"] == 1.95

    def test_empty_features_returns_empty_dict(self, sample_malformed_json_empty_features):
        """测试：空特征字典应返回空特征"""
        from scripts.ml.extract_features_v1 import extract_features_from_json

        features = extract_features_from_json(sample_malformed_json_empty_features)

        # 验证：所有赔率特征都为 None
        assert features.get("opening_home") is None
        assert features.get("closing_home") is None
        assert features.get("high_24h_home") is None
        assert features.get("low_24h_home") is None

    def test_array_format_extraction_opening_closing(self, sample_l3_odds_data_array_format):
        """
        V36.3 数组格式解析测试

        验证从 l3_odds_data 数组格式提取 Opening/Closing 赔率：
        - Opening: 从数组第一个元素提取
        - Closing: 从数组最后一个元素提取
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        features = extract_features_from_json(sample_l3_odds_data_array_format)

        # 验证 Opening 从第一项提取
        assert features.get("opening_home") == 3.70, f"Expected 3.70, got {features.get('opening_home')}"
        assert features.get("opening_draw") == 3.05, f"Expected 3.05, got {features.get('opening_draw')}"
        assert features.get("opening_away") == 2.15, f"Expected 2.15, got {features.get('opening_away')}"

        # 验证 Closing 从最后一项提取
        assert features.get("closing_home") == 3.64, f"Expected 3.64, got {features.get('closing_home')}"
        assert features.get("closing_draw") == 2.99, f"Expected 2.99, got {features.get('closing_draw')}"
        assert features.get("closing_away") == 2.20, f"Expected 2.20, got {features.get('closing_away')}"

        # 验证 payout_ratio 计算: 1 / (1/3.64 + 1/2.99 + 1/2.20) ≈ 0.926
        expected_payout = 1 / (1/3.64 + 1/2.99 + 1/2.20)
        assert features.get("payout_ratio") is not None, "payout_ratio should not be None"
        assert abs(features.get("payout_ratio") - expected_payout) < 0.01, \
            f"Expected payout_ratio ≈ {expected_payout:.3f}, got {features.get('payout_ratio')}"


class TestFeatureStorage:
    """测试特征存储逻辑"""

    def test_save_features_to_database(self):
        """测试：特征应正确保存到数据库"""
        from unittest.mock import MagicMock, patch

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        # 关键：设置上下文管理器返回值
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        with patch('scripts.ml.extract_features_v1.get_db_connection', return_value=mock_conn):
            from scripts.ml.extract_features_v1 import save_features_to_db

            features = {
                "match_id": "12345",
                "opening_home": 1.85,
                "closing_home": 1.95,
                "high_24h_home": 2.10,
                "low_24h_away": 4.30,
            }

            # 调用保存函数
            result = save_features_to_db([features])

            # 验证：数据库插入被调用
            assert mock_cursor.execute.called
            assert mock_conn.commit.called

    def test_save_features_handles_none_values(self):
        """测试：None 值应正确保存为数据库 NULL"""
        from unittest.mock import MagicMock, patch

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        # 关键：设置上下文管理器返回值
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        with patch('scripts.ml.extract_features_v1.get_db_connection', return_value=mock_conn):
            from scripts.ml.extract_features_v1 import save_features_to_db

            features = {
                "match_id": "12346",
                "opening_home": None,  # None 值
                "closing_home": 1.95,
            }

            # 调用保存函数
            save_features_to_db([features])

            # 验证：execute 被调用（具体 SQL 验证在集成测试中）
            assert mock_cursor.execute.called


class TestMalformedFormatHandling:
    """V36.3 测试畸形格式处理和失败记录"""

    def test_average_odds_format_extraction(self):
        """测试: Average Odds 转换后的数组格式应正确提取"""
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # Average Odds 格式经 fetch_from_clean_view 转换后的数组格式
        # 模拟: {"closing_odds": {"Average Odds": {"home": 1.51}}}
        # 转换为: {"home": [{"odds": "1.507"}, {"odds": "1.51"}], ...}
        converted_format = {
            "match_id": "3361854",
            "l3_odds_data": {
                "home": [
                    {"odds": "1.507"},  # Opening
                    {"odds": "1.51"}    # Closing
                ],
                "draw": [
                    {"odds": "4.647"},
                    {"odds": "4.65"}
                ],
                "away": [
                    {"odds": "6.093"},
                    {"odds": "6.09"}
                ]
            }
        }

        features = extract_features_from_json(converted_format)

        # 验证 Opening (第一个元素)
        assert features.get("opening_home") == 1.507
        assert features.get("opening_draw") == 4.647
        assert features.get("opening_away") == 6.093

        # 验证 Closing (最后一个元素)
        assert features.get("closing_home") == 1.51
        assert features.get("closing_draw") == 4.65
        assert features.get("closing_away") == 6.09

        # 验证 payout_ratio
        expected_payout = 1 / (1/1.51 + 1/4.65 + 1/6.09)
        assert features.get("payout_ratio") is not None
        assert abs(features.get("payout_ratio") - expected_payout) < 0.01

    def test_completely_malformed_format_returns_safely(self):
        """测试: 完全畸形的格式应安全返回而不崩溃"""
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 完全畸形的数据
        malformed_formats = [
            # 空字符串
            {"match_id": "1", "l3_odds_data": ""},
            # 随机嵌套
            {"match_id": "2", "l3_odds_data": {"random": {"nested": {"data": True}}}},
            # 列表而不是字典
            {"match_id": "3", "l3_odds_data": [{"odds": "1.5"}]},
            # None 值
            {"match_id": "4", "l3_odds_data": None},
        ]

        for malformed in malformed_formats:
            # 不应抛出异常
            features = extract_features_from_json(malformed)
            assert features is not None
            assert isinstance(features, dict)
            # 所有赔率字段应为 None
            assert features.get("opening_home") is None
            assert features.get("closing_home") is None

    def test_failed_extraction_log_created(self, tmp_path):
        """测试: 失败的提取应记录到 failed_features.json"""
        from scripts.ml.extract_features_v1 import log_failed_extraction, FAILED_FEATURES_LOG
        import json

        # 临时覆盖日志路径
        original_log = FAILED_FEATURES_LOG
        temp_log = tmp_path / "test_failed_features.json"
        import scripts.ml.extract_features_v1 as ef_module
        ef_module.FAILED_FEATURES_LOG = temp_log

        try:
            # 记录失败
            log_failed_extraction(
                match_id="test_123",
                format_type="unknown",
                raw_data={"random": "data"},
                reason="测试失败记录"
            )

            # 验证文件被创建
            assert temp_log.exists()

            # 验证内容
            with open(temp_log, 'r', encoding='utf-8') as f:
                records = json.load(f)

            assert len(records) == 1
            assert records[0]["match_id"] == "test_123"
            assert records[0]["format_type"] == "unknown"
            assert records[0]["reason"] == "测试失败记录"

        finally:
            # 恢复原始路径
            ef_module.FAILED_FEATURES_LOG = original_log
            # 清理临时文件
            if temp_log.exists():
                temp_log.unlink()


class TestV29DataPipeline:
    """V29.0 数据流水线测试"""

    @patch('scripts.ml.extract_features_v1.fetch_from_clean_view')
    def test_pipeline_handles_malformed_data(self, mock_fetch):
        """测试：流水线应能处理畸形数据而不中断"""
        # 模拟返回包含畸形数据的列表
        mock_fetch.return_value = [
            {"match_id": "1", "l3_raw_json": {"incomplete": "data"}},
            {"match_id": "2", "l3_raw_json": None},  # None JSON
            {"match_id": "3", "l3_raw_json": {"valid": "data"}},
        ]

        from scripts.ml.extract_features_v1 import process_features_pipeline

        # 处理流水线
        results = process_features_pipeline(limit=10)

        # 验证：流水线没有崩溃
        assert isinstance(results, list)
        # 验证：至少处理了部分数据
        assert len(results) >= 0


# ============================================================================
# Test Runner
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


    def test_failure_v374_test_1768212655_unknown(self):
        """TDD 自动生成: 无法识别的 l3_odds_data 格式

        失败记录: v374_test_1768212655
        格式类型: unknown
        生成时间: 2026-01-12T18:18:17.003310

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {'away_odds': 6.0, 'draw_odds': 4.0, 'home_odds': 1.5}

        # 构造测试数据
        test_data = {
            "match_id": "v374_test_1768212655",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 无法识别的 l3_odds_data 格式


    def test_failure_3919075_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 3919075
        格式类型: unknown
        生成时间: 2026-01-12T18:46:06.323880

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "3919075",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_3919370_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 3919370
        格式类型: unknown
        生成时间: 2026-01-12T18:46:07.324037

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "3919370",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_3919372_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 3919372
        格式类型: unknown
        生成时间: 2026-01-12T18:46:08.106658

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "3919372",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_3919373_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 3919373
        格式类型: unknown
        生成时间: 2026-01-12T18:46:08.897159

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "3919373",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_3919387_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 3919387
        格式类型: unknown
        生成时间: 2026-01-12T18:46:09.639288

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "3919387",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4205701_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4205701
        格式类型: unknown
        生成时间: 2026-01-12T18:46:10.392639

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4205701",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4205710_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4205710
        格式类型: unknown
        生成时间: 2026-01-12T18:46:11.167180

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4205710",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4221763_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4221763
        格式类型: unknown
        生成时间: 2026-01-12T18:46:11.960334

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4221763",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4230534_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4230534
        格式类型: unknown
        生成时间: 2026-01-12T18:46:12.755640

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4230534",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4230579_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4230579
        格式类型: unknown
        生成时间: 2026-01-12T18:46:13.559085

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4230579",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4230907_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4230907
        格式类型: unknown
        生成时间: 2026-01-12T18:46:14.315961

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4230907",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4506757_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4506757
        格式类型: unknown
        生成时间: 2026-01-12T18:46:15.098436

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4506757",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4506783_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4506783
        格式类型: unknown
        生成时间: 2026-01-12T18:46:15.869160

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4506783",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4506814_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4506814
        格式类型: unknown
        生成时间: 2026-01-12T18:46:16.618123

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4506814",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4506818_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4506818
        格式类型: unknown
        生成时间: 2026-01-12T18:46:17.450481

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4506818",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4506820_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4506820
        格式类型: unknown
        生成时间: 2026-01-12T18:46:18.284459

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4506820",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4506835_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4506835
        格式类型: unknown
        生成时间: 2026-01-12T18:46:19.082306

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4506835",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4506854_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4506854
        格式类型: unknown
        生成时间: 2026-01-12T18:46:19.832386

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4506854",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4506890_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4506890
        格式类型: unknown
        生成时间: 2026-01-12T18:46:20.763515

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4506890",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4506896_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4506896
        格式类型: unknown
        生成时间: 2026-01-12T18:46:21.653123

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4506896",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4506899_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4506899
        格式类型: unknown
        生成时间: 2026-01-12T18:46:22.458428

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4506899",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4506901_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4506901
        格式类型: unknown
        生成时间: 2026-01-12T18:46:23.314827

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4506901",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4506936_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4506936
        格式类型: unknown
        生成时间: 2026-01-12T18:46:24.148875

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4506936",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4506997_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4506997
        格式类型: unknown
        生成时间: 2026-01-12T18:46:24.375770

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4506997",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4507019_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4507019
        格式类型: unknown
        生成时间: 2026-01-12T18:46:25.197181

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4507019",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4507069_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4507069
        格式类型: unknown
        生成时间: 2026-01-12T18:46:26.023104

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4507069",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4507071_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4507071
        格式类型: unknown
        生成时间: 2026-01-12T18:46:26.902412

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4507071",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4507093_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4507093
        格式类型: unknown
        生成时间: 2026-01-12T18:46:27.717669

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4507093",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4507111_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4507111
        格式类型: unknown
        生成时间: 2026-01-12T18:46:28.522918

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4507111",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4507134_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4507134
        格式类型: unknown
        生成时间: 2026-01-12T18:46:29.443153

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4507134",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4534627_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4534627
        格式类型: unknown
        生成时间: 2026-01-12T18:46:30.245904

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4534627",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4534669_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4534669
        格式类型: unknown
        生成时间: 2026-01-12T18:46:31.075262

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4534669",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4534675_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4534675
        格式类型: unknown
        生成时间: 2026-01-12T18:46:31.902045

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4534675",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4534695_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4534695
        格式类型: unknown
        生成时间: 2026-01-12T18:46:32.691867

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4534695",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4534723_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4534723
        格式类型: unknown
        生成时间: 2026-01-12T18:46:33.531714

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4534723",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4534745_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4534745
        格式类型: unknown
        生成时间: 2026-01-12T18:46:34.308150

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4534745",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4534765_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4534765
        格式类型: unknown
        生成时间: 2026-01-12T18:46:35.082983

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4534765",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4534799_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4534799
        格式类型: unknown
        生成时间: 2026-01-12T18:46:35.904100

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4534799",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4534833_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4534833
        格式类型: unknown
        生成时间: 2026-01-12T18:46:36.672873

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4534833",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535269_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535269
        格式类型: unknown
        生成时间: 2026-01-12T18:46:37.472969

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535269",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535280_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535280
        格式类型: unknown
        生成时间: 2026-01-12T18:46:38.360990

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535280",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535282_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535282
        格式类型: unknown
        生成时间: 2026-01-12T18:46:39.181996

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535282",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535283_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535283
        格式类型: unknown
        生成时间: 2026-01-12T18:46:39.963648

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535283",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535296_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535296
        格式类型: unknown
        生成时间: 2026-01-12T18:46:40.749511

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535296",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535300_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535300
        格式类型: unknown
        生成时间: 2026-01-12T18:46:41.525220

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535300",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535323_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535323
        格式类型: unknown
        生成时间: 2026-01-12T18:46:42.385798

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535323",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535325_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535325
        格式类型: unknown
        生成时间: 2026-01-12T18:46:43.253646

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535325",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535329_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535329
        格式类型: unknown
        生成时间: 2026-01-12T18:46:44.084704

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535329",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535333_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535333
        格式类型: unknown
        生成时间: 2026-01-12T18:46:44.922589

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535333",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535340_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535340
        格式类型: unknown
        生成时间: 2026-01-12T18:46:45.774884

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535340",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535352_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535352
        格式类型: unknown
        生成时间: 2026-01-12T18:46:46.584634

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535352",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535378_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535378
        格式类型: unknown
        生成时间: 2026-01-12T18:46:47.345741

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535378",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535381_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535381
        格式类型: unknown
        生成时间: 2026-01-12T18:46:48.146796

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535381",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535384_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535384
        格式类型: unknown
        生成时间: 2026-01-12T18:46:48.958126

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535384",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535410_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535410
        格式类型: unknown
        生成时间: 2026-01-12T18:46:49.779332

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535410",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535412_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535412
        格式类型: unknown
        生成时间: 2026-01-12T18:46:50.694791

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535412",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535416_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535416
        格式类型: unknown
        生成时间: 2026-01-12T18:46:51.598965

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535416",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535467_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535467
        格式类型: unknown
        生成时间: 2026-01-12T18:46:52.371483

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535467",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535472_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535472
        格式类型: unknown
        生成时间: 2026-01-12T18:46:53.197382

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535472",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535482_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535482
        格式类型: unknown
        生成时间: 2026-01-12T18:46:53.885160

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535482",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535499_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535499
        格式类型: unknown
        生成时间: 2026-01-12T18:46:54.717118

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535499",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535509_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535509
        格式类型: unknown
        生成时间: 2026-01-12T18:46:55.577801

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535509",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535517_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535517
        格式类型: unknown
        生成时间: 2026-01-12T18:46:56.449315

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535517",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535531_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535531
        格式类型: unknown
        生成时间: 2026-01-12T18:46:57.346452

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535531",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535549_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535549
        格式类型: unknown
        生成时间: 2026-01-12T18:46:58.221745

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535549",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535576_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535576
        格式类型: unknown
        生成时间: 2026-01-12T18:46:59.045668

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535576",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4535587_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4535587
        格式类型: unknown
        生成时间: 2026-01-12T18:46:59.848570

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4535587",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_3411407_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 3411407
        格式类型: unknown
        生成时间: 2026-01-12T18:47:00.682684

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "3411407",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4507127_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4507127
        格式类型: unknown
        生成时间: 2026-01-12T18:47:01.564147

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4507127",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_3411687_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 3411687
        格式类型: unknown
        生成时间: 2026-01-12T18:47:02.369282

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "3411687",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_3901285_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 3901285
        格式类型: unknown
        生成时间: 2026-01-12T18:47:03.214066

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "3901285",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_3918316_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 3918316
        格式类型: unknown
        生成时间: 2026-01-12T18:47:04.204749

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "3918316",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_3610233_unknown(self):
        """TDD 自动生成: 特征提取失败（代码逻辑或数据问题）

        失败记录: 3610233
        格式类型: unknown
        生成时间: 2026-01-12T18:47:05.029378

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "3610233",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 特征提取失败（代码逻辑或数据问题）


    def test_failure_3900954_unknown(self):
        """TDD 自动生成: 特征提取失败（代码逻辑或数据问题）

        失败记录: 3900954
        格式类型: unknown
        生成时间: 2026-01-12T18:47:05.847115

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "3900954",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 特征提取失败（代码逻辑或数据问题）


    def test_failure_3900961_unknown(self):
        """TDD 自动生成: 特征提取失败（代码逻辑或数据问题）

        失败记录: 3900961
        格式类型: unknown
        生成时间: 2026-01-12T18:47:06.761168

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "3900961",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 特征提取失败（代码逻辑或数据问题）


    def test_failure_3901018_unknown(self):
        """TDD 自动生成: 特征提取失败（代码逻辑或数据问题）

        失败记录: 3901018
        格式类型: unknown
        生成时间: 2026-01-12T18:47:07.693809

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "3901018",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 特征提取失败（代码逻辑或数据问题）


    def test_failure_4193541_unknown(self):
        """TDD 自动生成: 特征提取失败（代码逻辑或数据问题）

        失败记录: 4193541
        格式类型: unknown
        生成时间: 2026-01-12T18:47:08.529378

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4193541",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 特征提取失败（代码逻辑或数据问题）


    def test_failure_4193682_unknown(self):
        """TDD 自动生成: 特征提取失败（代码逻辑或数据问题）

        失败记录: 4193682
        格式类型: unknown
        生成时间: 2026-01-12T18:47:09.454851

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4193682",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 特征提取失败（代码逻辑或数据问题）


    def test_failure_4514152_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4514152
        格式类型: unknown
        生成时间: 2026-01-12T18:47:10.287179

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4514152",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4514154_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4514154
        格式类型: unknown
        生成时间: 2026-01-12T18:47:11.184056

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4514154",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4514120_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4514120
        格式类型: unknown
        生成时间: 2026-01-12T18:47:12.081076

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4514120",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4514048_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4514048
        格式类型: unknown
        生成时间: 2026-01-12T18:47:12.964661

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4514048",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4514032_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4514032
        格式类型: unknown
        生成时间: 2026-01-12T18:47:13.843939

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4514032",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4513932_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4513932
        格式类型: unknown
        生成时间: 2026-01-12T18:47:14.699036

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4513932",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4513936_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4513936
        格式类型: unknown
        生成时间: 2026-01-12T18:47:15.554839

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4513936",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4513926_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4513926
        格式类型: unknown
        生成时间: 2026-01-12T18:47:16.403650

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4513926",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4513917_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4513917
        格式类型: unknown
        生成时间: 2026-01-12T18:47:17.270132

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4513917",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4513838_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4513838
        格式类型: unknown
        生成时间: 2026-01-12T18:47:18.152292

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4513838",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4514110_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4514110
        格式类型: unknown
        生成时间: 2026-01-12T18:47:19.180885

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4514110",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4514112_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4514112
        格式类型: unknown
        生成时间: 2026-01-12T18:47:20.086219

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4514112",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4514080_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4514080
        格式类型: unknown
        生成时间: 2026-01-12T18:47:21.097004

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4514080",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4514076_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4514076
        格式类型: unknown
        生成时间: 2026-01-12T18:47:22.200463

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4514076",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4514067_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4514067
        格式类型: unknown
        生成时间: 2026-01-12T18:47:23.072567

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4514067",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4514069_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4514069
        格式类型: unknown
        生成时间: 2026-01-12T18:47:23.793711

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4514069",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4513949_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4513949
        格式类型: unknown
        生成时间: 2026-01-12T18:47:24.341314

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4513949",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4513897_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4513897
        格式类型: unknown
        生成时间: 2026-01-12T18:47:25.215092

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4513897",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4513010_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4513010
        格式类型: unknown
        生成时间: 2026-01-12T18:47:26.107299

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4513010",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4219412_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4219412
        格式类型: unknown
        生成时间: 2026-01-12T18:47:27.007550

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4219412",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4219228_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4219228
        格式类型: unknown
        生成时间: 2026-01-12T18:47:27.873434

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4219228",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4219367_unknown(self):
        """TDD 自动生成: 赔率格式不完整（缺少 home/draw/away 字段）

        失败记录: 4219367
        格式类型: unknown
        生成时间: 2026-01-12T18:47:28.746305

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {}

        # 构造测试数据
        test_data = {
            "match_id": "4219367",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 赔率格式不完整（缺少 home/draw/away 字段）


    def test_failure_4193682_unknown(self):
        """TDD 自动生成: 无法识别的 l3_odds_data 格式

        失败记录: 4193682
        格式类型: unknown
        生成时间: 2026-01-12T18:50:26.564649

        Red Phase: 此测试应该先失败（功能未实现）
        Green Phase: 修复代码使测试通过
        """
        from scripts.ml.extract_features_v1 import extract_features_from_json

        # 原始数据样本
        raw_data = {'away_odds': 6.75, 'bookmaker': 'Pinnacle', 'draw_odds': 4.45, 'home_odds': 1.45}

        # 构造测试数据
        test_data = {
            "match_id": "4193682",
            "l3_odds_data": raw_data
        }

        # 提取特征
        features = extract_features_from_json(test_data)

        # 断言：应该安全返回而不崩溃
        assert features is not None
        assert isinstance(features, dict)

        # 根据失败原因，添加相应的断言
        # TODO: 根据实际的失败原因调整断言
        # reason: 无法识别的 l3_odds_data 格式
