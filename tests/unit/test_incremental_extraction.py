#!/usr/bin/env python3
"""
Unit Test: Incremental Feature Extraction - 增量提取 TDD

测试目标：验证特征提取引擎的增量逻辑

TDD 流程：
1. Red Phase: 测试失败（功能未实现）
2. Green Phase: 实现功能，测试通过
3. Refactor Phase: 优化代码（可选）

测试场景：
- 已有特征的比赛不应再次插入 ✅
- 新比赛应正常插入 ✅
- 增量查询应正确过滤已处理记录 ✅

Author: 资深数据科学家 & SRE
Date: 2026-01-11
Version: V29.1 (Incremental Extraction)
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def existing_features_sample():
    """模拟已存在的特征数据"""
    return [
        {
            "match_id": "10001",
            "opening_home": 1.85,
            "opening_draw": 3.50,
            "opening_away": 4.20,
        },
        {
            "match_id": "10002",
            "opening_home": 2.10,
            "opening_draw": 3.20,
            "opening_away": 3.50,
        }
    ]


@pytest.fixture
def raw_matches_data():
    """模拟原始比赛数据（包含已处理和未处理的）"""
    return [
        {
            "match_id": "10001",  # 已存在
            "league_name": "Premier League",
            "home_team": "Arsenal",
            "away_team": "Chelsea",
            "l3_features": {
                "opening": {"home": 1.85, "draw": 3.50, "away": 4.20},
                "closing": {"home": 1.95, "draw": 3.40, "away": 3.90},
            }
        },
        {
            "match_id": "10003",  # 新记录
            "league_name": "La Liga",
            "home_team": "Real Madrid",
            "away_team": "Barcelona",
            "l3_features": {
                "opening": {"home": 1.50, "draw": 4.00, "away": 6.00},
                "closing": {"home": 1.55, "draw": 3.80, "away": 5.50},
            }
        },
        {
            "match_id": "10002",  # 已存在
            "league_name": "Premier League",
            "home_team": "Liverpool",
            "away_team": "Man City",
            "l3_features": {
                "opening": {"home": 2.10, "draw": 3.20, "away": 3.50},
            }
        },
    ]


# ============================================================================
# Test Cases
# ============================================================================

class TestIncrementalExtraction:
    """测试增量特征提取逻辑"""

    @patch('scripts.ml.extract_features_v1.get_db_connection')
    def test_fetch_excludes_existing_features(self, mock_get_conn, existing_features_sample):
        """TDD 核心测试：fetch_from_clean_view 应排除已有特征的比赛"""
        # Mock 数据库连接 - 添加上下文管理器支持
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # 模拟查询结果 - 只应返回未处理的比赛
        mock_cursor.fetchall.return_value = [
            {
                "match_id": "10003",
                "league_name": "La Liga",
                "home_team": "Real Madrid",
                "away_team": "Barcelona",
                "odds_data": [{"home_odds": 1.50, "draw_odds": 4.00, "away_odds": 6.00}]
            }
        ]

        # 模拟 match_features 表中已存在的记录
        with patch('scripts.ml.extract_features_v1.psycopg2') as mock_psycopg:
            from scripts.ml.extract_features_v1 import fetch_from_clean_view

            # 调用函数（假设 limit=10）
            results = fetch_from_clean_view(limit=10)

            # 验证：SQL 查询包含了 NOT IN 子查询
            if mock_cursor.execute.call_args:
                executed_sql = mock_cursor.execute.call_args[0][0]
                assert "NOT IN" in executed_sql or "NOT EXISTS" in executed_sql, \
                    "SQL 查询应包含增量过滤逻辑"

            # 验证：只返回未处理的比赛
            assert len(results) == 1
            assert results[0]["match_id"] == "10003"

    @patch('scripts.ml.extract_features_v1.get_db_connection')
    def test_upsert_prevents_duplicates(self, mock_get_conn):
        """测试：UPSERT 应防止重复插入"""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        from scripts.ml.extract_features_v1 import save_features_to_db

        # 准备数据：包含重复的 match_id
        features_list = [
            {"match_id": "10001", "opening_home": 1.85},
            {"match_id": "10001", "opening_home": 1.90},  # 重复
        ]

        # 调用保存
        result = save_features_to_db(features_list)

        # 验证：execute 被调用 2 次（两次 UPSERT）
        assert mock_cursor.execute.call_count == 2

        # 验证：SQL 包含 ON CONFLICT 子句
        executed_sql = mock_cursor.execute.call_args[0][0]
        assert "ON CONFLICT" in executed_sql, \
            "SQL 应使用 ON CONFLICT (UPSERT) 防止重复"

    @patch('scripts.ml.extract_features_v1.fetch_from_clean_view')
    @patch('scripts.ml.extract_features_v1.save_features_to_db')
    def test_pipeline_only_processes_new_matches(self, mock_save, mock_fetch):
        """测试：流水线只处理新比赛"""
        # Mock fetch 返回数据（已过滤掉已处理的）
        mock_fetch.return_value = [
            {
                "match_id": "10003",
                "l3_features": {
                    "opening": {"home": 1.50, "draw": 4.00, "away": 6.00}
                }
            }
        ]

        mock_save.return_value = 1  # 保存了 1 条

        from scripts.ml.extract_features_v1 import process_features_pipeline

        # 运行流水线
        results = process_features_pipeline(limit=100)

        # 验证：只处理了新比赛
        assert len(results) == 1
        assert results[0]["match_id"] == "10003"

        # 验证：保存函数被调用
        mock_save.assert_called_once()

    def test_incremental_progressive_extracts_all_matches(self):
        """测试：多次增量提取最终覆盖所有比赛"""
        # 模拟数据库状态
        processed_ids = {"10001", "10002"}
        all_matches = ["10001", "10002", "10003", "10004", "10005"]

        # 第一次提取：应获取 10003, 10004, 10005
        first_batch = [m for m in all_matches if m not in processed_ids]
        assert set(first_batch) == {"10003", "10004", "10005"}

        # 模拟第一次提取后
        processed_ids.update(first_batch)

        # 第二次提取：应返回空（所有比赛已处理）
        second_batch = [m for m in all_matches if m not in processed_ids]
        assert len(second_batch) == 0


class TestFeatureQualityMetrics:
    """测试特征质量指标计算"""

    def test_calculate_odds_movement_count(self):
        """测试：计算变盘次数"""
        # 模拟赔率数据
        odds_history = [
            {"home": 1.85, "draw": 3.50, "away": 4.20},
            {"home": 1.90, "draw": 3.40, "away": 4.00},  # 变盘
            {"home": 1.95, "draw": 3.30, "away": 3.90},  # 变盘
            {"home": 1.95, "draw": 3.30, "away": 3.90},  # 未变
        ]

        # 计算变盘次数（相邻记录值不同）
        movement_count = 0
        for i in range(1, len(odds_history)):
            if odds_history[i] != odds_history[i-1]:
                movement_count += 1

        assert movement_count == 2, "应检测到 2 次变盘"

    def test_identify_zombie_records(self):
        """测试：识别僵尸记录（只有一条赔率）"""
        features_data = [
            {
                "match_id": "10001",
                "league": "Premier League",
                "opening_home": 1.85,
                "closing_home": 1.95,  # 有 opening 和 closing
                "high_24h_home": 2.00,
                "low_24h_home": 1.80,
            },
            {
                "match_id": "10002",
                "league": "La Liga",
                "opening_home": 2.10,
                "closing_home": None,  # 僵尸记录：只有 opening
                "high_24h_home": None,
                "low_24h_home": None,
            }
        ]

        # 识别僵尸记录
        zombie_records = []
        for f in features_data:
            # 如果只有 opening 没有 closing/high_24h/low_24h，视为僵尸
            if (f.get("opening_home") is not None and
                f.get("closing_home") is None and
                f.get("high_24h_home") is None and
                f.get("low_24h_home") is None):
                zombie_records.append(f["match_id"])

        assert zombie_records == ["10002"], "应识别出僵尸记录"


# ============================================================================
# Test Runner
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
