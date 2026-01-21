#!/usr/bin/env python3
"""
V34.0 Feature Enrichment TDD Tests - 特征增强引擎测试

功能：验证新特征的计算逻辑

测试场景：
1. payout_ratio: 博彩公司返还率计算
   - 正常盘口 (0.90-0.98)
   - 冷门诱导盘 (>0.98)
   - 残缺数据处理

2. movement_velocity: 赛前 2 小时变盘速度
   - 极端场景: 10 分钟内跳动 5 次
   - 正常场景: 缓慢变动
   - 无变动场景

TDD 流程：
- Red Phase: 测试失败（功能未实现）
- Green Phase: 实现功能，测试通过
- Refactor Phase: 优化代码（可选）

Author: 高级数据治理专家 & 算法工程师
Date: 2026-01-12
Version: V34.0 (Feature Enrichment)
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestPayoutRatio:
    """测试 payout_ratio (博彩公司返还率)"""

    def test_normal_payout_ratio(self):
        """测试：正常盘口的返还率计算 (0.90-0.98)"""
        # 正常盘口示例
        home_odds, draw_odds, away_odds = 2.50, 3.20, 2.80

        # 手动计算预期值
        # payout = 1 / (1/2.50 + 1/3.20 + 1/2.80)
        expected_payout = 1 / (1/2.50 + 1/3.20 + 1/2.80)

        from scripts.ml.extract_features_v1 import calculate_payout_ratio
        payout = calculate_payout_ratio(home_odds, draw_odds, away_odds)

        assert payout is not None
        assert 0.90 <= payout <= 0.98, f"返还率 {payout} 应在正常范围 [0.90, 0.98]"
        assert abs(payout - expected_payout) < 0.001

    def test_high_payout_ratio_indicates_trap(self):
        """测试：高返还率 (>0.95) 可能是冷门诱导盘"""
        # 异常高返还率（可能是诱导盘）
        # 接近公平赔率，博彩公司抽取的水钱很少
        # 2.88, 3.25, 2.88 → payout ≈ 0.998
        home_odds, draw_odds, away_odds = 2.88, 3.25, 2.88

        from scripts.ml.extract_features_v1 import calculate_payout_ratio
        payout = calculate_payout_ratio(home_odds, draw_odds, away_odds)

        assert payout is not None
        assert payout > 0.95, f"高返还率 {payout} 应 > 0.95 (冷门诱导)"
        # 计算验证
        expected = 1 / (1/2.88 + 1/3.25 + 1/2.88)
        assert abs(payout - expected) < 0.001

    def test_payout_ratio_with_missing_odds(self):
        """测试：残缺赔率数据的处理"""
        from scripts.ml.extract_features_v1 import calculate_payout_ratio

        # 缺少客队赔率
        payout = calculate_payout_ratio(2.50, 3.20, None)
        assert payout is None, "缺少赔率时应返回 None"

        # 全部为 None
        payout = calculate_payout_ratio(None, None, None)
        assert payout is None

    def test_payout_ratio_with_zero_odds(self):
        """测试：零值或负值赔率的处理"""
        from scripts.ml.extract_features_v1 import calculate_payout_ratio

        # 包含零值
        payout = calculate_payout_ratio(2.50, 0.0, 2.80)
        assert payout is None, "零值赔率应返回 None"

        # 包含负值
        payout = calculate_payout_ratio(2.50, -1.0, 2.80)
        assert payout is None, "负值赔率应返回 None"


class TestMovementVelocity:
    """测试 movement_velocity (赛前 2 小时变盘速度)"""

    def test_extreme_velocity_5_changes_in_10_minutes(self):
        """TDD 核心测试：极端场景 - 10 分钟内跳动 5 次

        场景：
        - 比赛时间: 2024-01-15 15:00:00
        - 赔率采样时间: 14:50, 14:52, 14:54, 14:56, 14:58
        - 预期: 高变盘速度 (> 2.5 次/小时)
        """
        match_time = datetime(2024, 1, 15, 15, 0, 0)

        # 构造赔率历史（10 分钟内 5 次变动）
        odds_history = [
            {
                "home_odds": 2.50,
                "draw_odds": 3.20,
                "away_odds": 2.80,
                "collected_at": match_time - timedelta(minutes=10)  # 14:50
            },
            {
                "home_odds": 2.45,  # 变动
                "draw_odds": 3.20,
                "away_odds": 2.85,  # 变动
                "collected_at": match_time - timedelta(minutes=8)   # 14:52
            },
            {
                "home_odds": 2.48,  # 变动
                "draw_odds": 3.20,
                "away_odds": 2.82,  # 变动
                "collected_at": match_time - timedelta(minutes=6)   # 14:54
            },
            {
                "home_odds": 2.42,  # 变动
                "draw_odds": 3.25,  # 变动
                "away_odds": 2.88,  # 变动
                "collected_at": match_time - timedelta(minutes=4)   # 14:56
            },
            {
                "home_odds": 2.40,  # 变动
                "draw_odds": 3.20,  # 变动
                "away_odds": 2.90,  # 变动
                "collected_at": match_time - timedelta(minutes=2)   # 14:58
            },
        ]

        from scripts.ml.extract_features_v1 import calculate_movement_velocity
        velocity = calculate_movement_velocity(odds_history, match_time)

        # 验证：10 分钟内 5 次变动 = 30 次/小时
        assert velocity is not None
        assert velocity > 20, f"10 分钟内 5 次变动应产生高速度 > 20 次/小时, 实际: {velocity}"

    def test_normal_velocity_slow_changes(self):
        """测试：正常场景 - 缓慢变动"""
        match_time = datetime(2024, 1, 15, 15, 0, 0)

        # 2 小时内只有 3 次变动
        odds_history = [
            {
                "home_odds": 2.50,
                "collected_at": match_time - timedelta(hours=2)
            },
            {
                "home_odds": 2.48,
                "collected_at": match_time - timedelta(hours=1)
            },
            {
                "home_odds": 2.45,
                "collected_at": match_time - timedelta(minutes=30)
            },
        ]

        from scripts.ml.extract_features_v1 import calculate_movement_velocity
        velocity = calculate_movement_velocity(odds_history, match_time)

        # 验证：2 小时内 3 次变动 = 1.5 次/小时
        assert velocity is not None
        assert velocity < 5, f"缓慢变动应产生低速度 < 5 次/小时, 实际: {velocity}"

    def test_no_movement_velocity_zero(self):
        """测试：无变动场景"""
        match_time = datetime(2024, 1, 15, 15, 0, 0)

        # 赔率始终不变
        odds_history = [
            {
                "home_odds": 2.50,
                "draw_odds": 3.20,
                "away_odds": 2.80,
                "collected_at": match_time - timedelta(hours=1)
            },
            {
                "home_odds": 2.50,  # 无变动
                "draw_odds": 3.20,  # 无变动
                "away_odds": 2.80,  # 无变动
                "collected_at": match_time - timedelta(minutes=30)
            },
        ]

        from scripts.ml.extract_features_v1 import calculate_movement_velocity
        velocity = calculate_movement_velocity(odds_history, match_time)

        # 验证：无变动 = 0
        assert velocity == 0, "无变动时速度应为 0"

    def test_velocity_only_counts_pre_match_2h_window(self):
        """测试：只统计赛前 2 小时窗口内的变动"""
        match_time = datetime(2024, 1, 15, 15, 0, 0)

        # 包含 2 小时窗口外的数据
        odds_history = [
            {
                "home_odds": 2.40, "draw_odds": 3.20, "away_odds": 2.80,  # 窗口外，不应计入
                "collected_at": match_time - timedelta(hours=3)
            },
            {
                "home_odds": 2.45, "draw_odds": 3.20, "away_odds": 2.80,  # 窗口内（2 小时边界）
                "collected_at": match_time - timedelta(hours=2)
            },
            {
                "home_odds": 2.50, "draw_odds": 3.20, "away_odds": 2.80,  # 窗口内
                "collected_at": match_time - timedelta(hours=1)
            },
        ]

        from scripts.ml.extract_features_v1 import calculate_movement_velocity
        velocity = calculate_movement_velocity(odds_history, match_time)

        # 验证：只统计 2 小时窗口内的 1 次变动
        assert velocity is not None
        assert 0 < velocity < 2, "应只统计窗口内的变动"

    def test_velocity_with_empty_history(self):
        """测试：空历史数据处理"""
        from scripts.ml.extract_features_v1 import calculate_movement_velocity

        match_time = datetime(2024, 1, 15, 15, 0, 0)
        velocity = calculate_movement_velocity([], match_time)

        assert velocity == 0, "空历史数据应返回 0 速度"

    def test_velocity_with_missing_collected_at(self):
        """测试：缺少 collected_at 字段的处理"""
        match_time = datetime(2024, 1, 15, 15, 0, 0)

        odds_history = [
            {
                "home_odds": 2.50,
                # 缺少 collected_at
            },
        ]

        from scripts.ml.extract_features_v1 import calculate_movement_velocity
        velocity = calculate_movement_velocity(odds_history, match_time)

        assert velocity == 0, "缺少时间戳的数据应被忽略"


class TestFeatureIntegration:
    """集成测试：新特征与现有特征的兼容性"""

    def test_extract_features_with_enrichment(self):
        """测试：extract_features_from_json 应包含新特征"""
        match_data = {
            "match_id": "test_123",
            "l3_features": {
                "opening": {"home": 2.50, "draw": 3.20, "away": 2.80},
                "closing": {"home": 2.45, "draw": 3.20, "away": 2.85},
            },
            # V34.0 新增：赔率历史和时间
            "odds_history": [
                {"home_odds": 2.50, "draw_odds": 3.20, "away_odds": 2.80,
                 "collected_at": "2024-01-15T13:00:00"},
                {"home_odds": 2.45, "draw_odds": 3.20, "away_odds": 2.85,
                 "collected_at": "2024-01-15T14:00:00"},
            ],
            "match_time": "2024-01-15T15:00:00"
        }

        from scripts.ml.extract_features_v1 import extract_features_from_json
        features = extract_features_from_json(match_data)

        # 验证：包含原有特征
        assert "opening_home" in features
        assert "closing_home" in features

        # 验证：包含新特征 (V34.0)
        assert "payout_ratio" in features
        assert "movement_velocity" in features

        # 验证：新特征有有效值
        assert features["payout_ratio"] is not None
        assert features["payout_ratio"] > 0
        assert features["movement_velocity"] >= 0


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
