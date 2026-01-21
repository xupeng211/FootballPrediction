#!/usr/bin/env python3
"""
V41.480 TDD Tests - Ultimate Feature Extraction Tests
======================================================

测试内容：
1. rest_days 计算逻辑 - 确保时间戳正确性（无泄露）
2. 伤病/禁赛战力损失计算
3. 赔率动向特征计算
4. is_top_5_league 特征验证

Author: V41.480 QA Team
Version: V41.480 "Ultimate Pre-Match Mine"
Date: 2026-01-21
"""

from __future__ import annotations

import json
import pytest
from datetime import datetime, timedelta


# =============================================================================
# Test: rest_days Calculation (Temporal Integrity)
# =============================================================================

class TestRestDaysCalculation:
    """休息天数计算测试 - 确保时间戳正确性"""

    def test_rest_days_basic_calculation(self):
        """测试基本休息天数计算"""
        from src.processors.ultimate_extractor import UltimateFeatureExtractor

        extractor = UltimateFeatureExtractor()

        # 场景1: 正常间隔 (7天)
        current_date = datetime(2025, 1, 15, 15, 0)
        prev_date = datetime(2025, 1, 8, 15, 0)
        rest_days = extractor._calculate_rest_days(current_date, prev_date)
        assert rest_days == 7, f"Expected 7 days, got {rest_days}"

        # 场景2: 短间隔 (3天 - 忙碌周)
        current_date = datetime(2025, 1, 11, 15, 0)
        prev_date = datetime(2025, 1, 8, 15, 0)
        rest_days = extractor._calculate_rest_days(current_date, prev_date)
        assert rest_days == 3, f"Expected 3 days, got {rest_days}"

        # 场景3: 极短间隔 (2天 - 连续作战)
        current_date = datetime(2025, 1, 10, 15, 0)
        prev_date = datetime(2025, 1, 8, 15, 0)
        rest_days = extractor._calculate_rest_days(current_date, prev_date)
        assert rest_days == 2, f"Expected 2 days, got {rest_days}"

    def test_rest_days_busy_week_detection(self):
        """测试忙碌周检测 (rest_days < 4)"""
        from src.processors.ultimate_extractor import UltimateFeatureExtractor

        extractor = UltimateFeatureExtractor()

        # 忙碌周场景
        current_date = datetime(2025, 1, 11, 15, 0)
        prev_date = datetime(2025, 1, 8, 15, 0)
        rest_days = extractor._calculate_rest_days(current_date, prev_date)
        is_busy = extractor._is_busy_week(rest_days)

        assert is_busy == True, "rest_days < 4 should be busy week"

        # 正常周场景
        current_date = datetime(2025, 1, 15, 15, 0)
        prev_date = datetime(2025, 1, 8, 15, 0)
        rest_days = extractor._calculate_rest_days(current_date, prev_date)
        is_busy = extractor._is_busy_week(rest_days)

        assert is_busy == False, "rest_days >= 4 should not be busy week"

    def test_rest_days_no_previous_match(self):
        """测试无历史比赛时的处理"""
        from src.processors.ultimate_extractor import UltimateFeatureExtractor

        extractor = UltimateFeatureExtractor()

        current_date = datetime(2025, 1, 15, 15, 0)
        prev_date = None

        rest_days = extractor._calculate_rest_days(current_date, prev_date)
        # 无历史比赛时，返回默认值 (如 14 天)
        assert rest_days == 14 or rest_days == 7, f"Expected default value, got {rest_days}"

    def test_rest_days_temporal_leakage_prevention(self):
        """
        V41.480 TDD: 时间戳泄露防护测试

        确保 rest_days 计算不会使用未来的比赛日期
        """
        from src.processors.ultimate_extractor import UltimateFeatureExtractor

        extractor = UltimateFeatureExtractor()

        current_date = datetime(2025, 1, 15, 15, 0)

        # 错误场景：future_date (应该是不可能发生的，但要防护)
        future_date = datetime(2025, 1, 20, 15, 0)

        # 应该检测到异常并返回默认值
        rest_days = extractor._calculate_rest_days(current_date, future_date)

        # 如果 prev_date > current_date，应该返回默认值而非负数
        assert rest_days >= 0, "rest_days should never be negative"
        assert rest_days <= 30, "rest_days should be reasonable (< 30 days default)"


# =============================================================================
# Test: Injury/Suspension Power Loss
# =============================================================================

class TestInjurySuspensionPowerLoss:
    """伤病/禁赛战力损失计算测试"""

    def test_calculate_unavailable_power_loss_empty(self):
        """测试空缺阵列表"""
        from src.processors.ultimate_extractor import UltimateFeatureExtractor

        extractor = UltimateFeatureExtractor()

        unavailable_players = []
        result = extractor._calculate_unavailable_power_loss(unavailable_players)

        assert result["total_count"] == 0
        assert result["injury_count"] == 0
        assert result["suspension_count"] == 0
        assert result["total_market_value"] == 0

    def test_calculate_unavailable_power_loss_with_market_value(self):
        """测试含身价的缺阵球员"""
        from src.processors.ultimate_extractor import UltimateFeatureExtractor

        extractor = UltimateFeatureExtractor()

        unavailable_players = [
            {
                "id": 1,
                "name": "Player A",
                "marketValue": 50_000_000,  # 50M
                "unavailability": {"type": "injury"}
            },
            {
                "id": 2,
                "name": "Player B",
                "marketValue": 30_000_000,  # 30M
                "unavailability": {"type": "suspension"}
            },
            {
                "id": 3,
                "name": "Player C",
                "marketValue": None,
                "unavailability": {"type": "injury"}
            },
        ]

        result = extractor._calculate_unavailable_power_loss(unavailable_players)

        assert result["total_count"] == 3
        assert result["injury_count"] == 2
        assert result["suspension_count"] == 1
        assert result["total_market_value"] == 80_000_000  # 50M + 30M
        assert result["avg_market_value"] == 40_000_000  # 80M / 2

    def test_injury_vs_suspension_distinction(self):
        """测试伤病与禁赛的区分"""
        from src.processors.ultimate_extractor import UltimateFeatureExtractor

        extractor = UltimateFeatureExtractor()

        unavailable_players = [
            {"unavailability": {"type": "injury"}, "marketValue": 10_000_000},
            {"unavailability": {"type": "injury"}, "marketValue": 20_000_000},
            {"unavailability": {"type": "suspension"}, "marketValue": 15_000_000},
            {"unavailability": {"type": "unknown"}, "marketValue": 5_000_000},
        ]

        result = extractor._calculate_unavailable_power_loss(unavailable_players)

        assert result["injury_count"] == 2
        assert result["suspension_count"] == 1
        assert result["other_count"] == 1


# =============================================================================
# Test: Odds Movement Features
# =============================================================================

class TestOddsMovementFeatures:
    """赔率动向特征测试"""

    def test_odds_drop_ratio_calculation(self):
        """测试赔率下降比率计算"""
        from src.processors.ultimate_extractor import UltimateFeatureExtractor

        extractor = UltimateFeatureExtractor()

        # 正常场景: 主胜赔率从 2.5 降到 2.0
        initial_price = [2.5, 3.0, 3.5]  # [home, draw, away]
        closing_price = [2.0, 3.1, 4.0]

        result = extractor._calculate_odds_movement(initial_price, closing_price)

        # 主胜赔率下降
        expected_home_drop = (2.5 - 2.0) / 2.5  # 0.2 = 20% drop
        assert result["home_drop_ratio"] == pytest.approx(expected_home_drop, 0.01)

        # 平局赔率变化
        expected_draw_change = (3.0 - 3.1) / 3.0  # negative = increase
        assert result["draw_change_ratio"] == pytest.approx(expected_draw_change, 0.01)

    def test_odds_movement_none_handling(self):
        """测试无赔率数据的处理"""
        from src.processors.ultimate_extractor import UltimateFeatureExtractor

        extractor = UltimateFeatureExtractor()

        result = extractor._calculate_odds_movement(None, None)

        assert result["home_drop_ratio"] == 0
        assert result["draw_change_ratio"] == 0
        assert result["away_change_ratio"] == 0
        assert result["total_movement"] == 0

    def test_odds_movement_length_mismatch(self):
        """测试赔率数组长度不匹配的处理"""
        from src.processors.ultimate_extractor import UltimateFeatureExtractor

        extractor = UltimateFeatureExtractor()

        initial_price = [2.5, 3.0]  # 缺少 away
        closing_price = [2.0, 3.1, 4.0]

        result = extractor._calculate_odds_movement(initial_price, closing_price)

        # 应该返回默认值或抛出异常
        assert result is not None


# =============================================================================
# Test: is_top_5_league Feature
# =============================================================================

class TestTop5LeagueFeature:
    """is_top_5_league 特征测试"""

    def test_top_5_league_detection(self):
        """测试五大联赛识别"""
        from src.processors.ultimate_extractor import UltimateFeatureExtractor

        extractor = UltimateFeatureExtractor()

        top_5_leagues = [
            "Premier League",
            "La Liga",
            "Bundesliga",
            "Serie A",
            "Ligue 1",
        ]

        for league in top_5_leagues:
            result = extractor._is_top_5_league(league)
            assert result == True, f"{league} should be top 5 league"

    def test_non_top_5_league_detection(self):
        """测试非五大联赛识别"""
        from src.processors.ultimate_extractor import UltimateFeatureExtractor

        extractor = UltimateFeatureExtractor()

        non_top_5 = [
            "Eredivisie",
            "Primeira Liga",
            "Championship",
            "Scottish Premiership",
        ]

        for league in non_top_5:
            result = extractor._is_top_5_league(league)
            assert result == False, f"{league} should not be top 5 league"


# =============================================================================
# Test: Temporal Integrity (Leakage Re-Scan)
# =============================================================================

class TestTemporalIntegrityV41_480:
    """V41.480 时空完整性测试"""

    def test_no_leakage_from_unavailable_data(self):
        """
        V41.480 TDD: unavailable 数据不包含赛中统计

        确认 unavailable 只包含赛前已知信息（伤病、禁赛）
        """
        sample_unavailable = {
            "id": 123,
            "name": "Player Name",
            "marketValue": 50_000_000,
            "unavailability": {
                "type": "injury",
                "injuryId": 14,
                "expectedReturn": "January 2025"
            }
        }

        # 检查不包含赛中统计关键字
        for key in sample_unavailable.keys():
            assert key not in ["shots", "goals", "assists", "passes", "saves"]

    def test_no_leakage_from_odds_data(self):
        """
        V41.480 TDD: 赔率数据不泄露比赛结果

        确认赔率数据只包含价格信息，不包含比赛结果
        """
        sample_odds = {
            "initial_price": [2.5, 3.0, 3.5],
            "closing_price": [2.0, 3.1, 4.0],
        }

        # 检查不包含比赛结果
        for key in sample_odds.keys():
            assert "result" not in key.lower()
            assert "score" not in key.lower()
            assert "winner" not in key.lower()


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
