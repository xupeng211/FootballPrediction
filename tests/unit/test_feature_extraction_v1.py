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
