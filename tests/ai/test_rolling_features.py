#!/usr/bin/env python3
"""
V41.420 Rolling Features TDD Test
===================================

历史滚动特征测试驱动开发：
- 验证滚动均值计算不包含当前比赛
- 验证时空隔离：只使用赛前已知历史数据
- 验证 xG 和 Rating 滚动均值正确性

Author: V41.420 ML Team
Version: V41.420 "Historical Awakening"
Date: 2026-01-21
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta
from typing import Any

import numpy as np


# =============================================================================
# Test Fixtures - 模拟比赛数据
# =============================================================================

@pytest.fixture
def sample_matches():
    """
    模拟比赛序列

    时间顺序:
    - Match 1: 2024-01-01 (earliest)
    - Match 2: 2024-01-08
    - Match 3: 2024-01-15
    - Match 4: 2024-01-22 (target - 计算其滚动特征)
    - Match 5: 2024-01-29 (future - 不应被使用)
    """
    return [
        {
            "match_id": "1",
            "match_date": datetime(2024, 1, 1),
            "team_id": "team_abc",
            "opponent_id": "team_xyz",
            "home_xg": 1.2,
            "away_xg": 0.8,
            "team_rating": 6.5,
        },
        {
            "match_id": "2",
            "match_date": datetime(2024, 1, 8),
            "team_id": "team_abc",
            "opponent_id": "team_def",
            "home_xg": 1.5,
            "away_xg": 1.0,
            "team_rating": 6.8,
        },
        {
            "match_id": "3",
            "match_date": datetime(2024, 1, 15),
            "team_id": "team_abc",
            "opponent_id": "team_ghi",
            "home_xg": 0.9,
            "away_xg": 1.3,
            "team_rating": 6.3,
        },
        {
            "match_id": "4",  # Target match - 计算其滚动特征
            "match_date": datetime(2024, 1, 22),
            "team_id": "team_abc",
            "opponent_id": "team_jkl",
            "home_xg": None,  # 赛前未知
            "away_xg": None,
            "team_rating": None,
        },
        {
            "match_id": "5",
            "match_date": datetime(2024, 1, 29),  # Future match
            "team_id": "team_abc",
            "opponent_id": "team_mno",
            "home_xg": 1.1,
            "away_xg": 0.7,
            "team_rating": 6.6,
        },
    ]


# =============================================================================
# Rolling Feature Calculator (待实现)
# =============================================================================

class RollingFeatureCalculator:
    """
    V41.420 滚动特征计算器

    严格时空隔离：
    - 只使用 target_match_date 之前的历史数据
    - 滚动窗口不包含当前比赛
    """

    def __init__(self, window_size: int = 5):
        self.window_size = window_size

    def calculate_rolling_xg(
        self,
        matches: list[dict[str, Any]],
        target_match_date: datetime,
        team_id: str,
        is_home: bool = True
    ) -> dict[str, float]:
        """
        计算滚动 xG 均值

        Args:
            matches: 历史比赛列表
            target_match_date: 目标比赛日期
            team_id: 球队ID
            is_home: 是否主队

        Returns:
            {"rolling_avg_xg_5": float, "rolling_total_xg_5": float}
        """
        # 过滤：只取目标比赛前的历史数据
        historical_matches = [
            m for m in matches
            if m["match_date"] < target_match_date
            and m["team_id"] == team_id
        ]

        # 按日期倒序，取最近 window_size 场
        historical_matches.sort(key=lambda x: x["match_date"], reverse=True)
        recent_matches = historical_matches[:self.window_size]

        if not recent_matches:
            return {"rolling_avg_xg_5": 0.0, "rolling_total_xg_5": 0.0}

        # 计算 xG (根据主客场)
        xg_values = []
        for match in recent_matches:
            xg_key = "home_xg" if is_home else "away_xg"
            xg = match.get(xg_key, 0)
            if xg is not None and xg > 0:
                xg_values.append(xg)

        if not xg_values:
            return {"rolling_avg_xg_5": 0.0, "rolling_total_xg_5": 0.0}

        return {
            "rolling_avg_xg_5": np.mean(xg_values),
            "rolling_total_xg_5": np.sum(xg_values),
        }

    def calculate_rolling_rating(
        self,
        matches: list[dict[str, Any]],
        target_match_date: datetime,
        team_id: str
    ) -> dict[str, float]:
        """
        计算滚动评分均值

        Returns:
            {"rolling_avg_rating_5": float}
        """
        historical_matches = [
            m for m in matches
            if m["match_date"] < target_match_date
            and m["team_id"] == team_id
        ]

        historical_matches.sort(key=lambda x: x["match_date"], reverse=True)
        recent_matches = historical_matches[:self.window_size]

        if not recent_matches:
            return {"rolling_avg_rating_5": 0.0}

        rating_values = []
        for match in recent_matches:
            rating = match.get("team_rating", 0)
            if rating is not None and rating > 0:
                rating_values.append(rating)

        if not rating_values:
            return {"rolling_avg_rating_5": 0.0}

        return {
            "rolling_avg_rating_5": np.mean(rating_values),
        }


# =============================================================================
# Test Cases
# =============================================================================

class TestRollingFeaturesTemporalIntegrity:
    """滚动特征时空完整性测试"""

    def test_no_future_data_leakage(self, sample_matches):
        """
        测试：未来比赛数据不能泄露到滚动特征中

        Match 4 的滚动特征只能使用 Match 1, 2, 3
        Match 5 (未来) 绝不能被使用
        """
        calculator = RollingFeatureCalculator(window_size=5)

        target_match = sample_matches[3]  # Match 4: 2024-01-22
        future_match = sample_matches[4]   # Match 5: 2024-01-29

        # 计算 Match 4 的滚动 xG
        result = calculator.calculate_rolling_xg(
            sample_matches,
            target_match["match_date"],
            target_match["team_id"],
            is_home=True
        )

        # 验证：结果应该基于 Match 1, 2, 3
        # Match 1: home_xg = 1.2
        # Match 2: home_xg = 1.5
        # Match 3: home_xg = 0.9
        # 平均值 = (1.2 + 1.5 + 0.9) / 3 = 1.2
        expected_avg = (1.2 + 1.5 + 0.9) / 3

        assert result["rolling_avg_xg_5"] == pytest.approx(expected_avg, 0.01), \
            f"Expected {expected_avg}, got {result['rolling_avg_xg_5']}"

        # 验证：Match 5 的数据 (未来) 不应被使用
        # 如果使用了 Match 5，结果会不同
        # Match 5 home_xg = 1.1，但它是未来比赛，不应计入
        print(f"\n  ✅ Match 4 滚动 xG: {result['rolling_avg_xg_5']:.3f}")
        print(f"     基于 Match 1-3，未使用未来 Match 5")

    def test_no_self_match_leakage(self, sample_matches):
        """
        测试：当前比赛自身不能计入滚动特征

        即使 Match 4 有 xG 数据，也不应被使用（因为是赛前预测）
        """
        calculator = RollingFeatureCalculator(window_size=5)

        # 手动给 Match 4 加上 xG（模拟赛后数据）
        sample_matches[3]["home_xg"] = 2.5

        target_match = sample_matches[3]

        result = calculator.calculate_rolling_xg(
            sample_matches,
            target_match["match_date"],
            target_match["team_id"],
            is_home=True
        )

        # 验证：Match 4 的 xG (2.5) 不应被计入
        # 应该只使用 Match 1, 2, 3
        expected_avg = (1.2 + 1.5 + 0.9) / 3

        assert result["rolling_avg_xg_5"] == pytest.approx(expected_avg, 0.01), \
            f"Current match leaked into rolling average! Expected {expected_avg}, got {result['rolling_avg_xg_5']}"

        print(f"\n  ✅ Match 4 自身数据被正确排除")
        print(f"     滚动均值基于历史数据: {result['rolling_avg_xg_5']:.3f}")

    def test_rolling_rating_calculation(self, sample_matches):
        """测试滚动评分计算"""
        calculator = RollingFeatureCalculator(window_size=5)

        target_match = sample_matches[3]  # Match 4

        result = calculator.calculate_rolling_rating(
            sample_matches,
            target_match["match_date"],
            target_match["team_id"]
        )

        # Match 1: rating = 6.5
        # Match 2: rating = 6.8
        # Match 3: rating = 6.3
        # 平均值 = (6.5 + 6.8 + 6.3) / 3 = 6.53
        expected_avg = (6.5 + 6.8 + 6.3) / 3

        assert result["rolling_avg_rating_5"] == pytest.approx(expected_avg, 0.01), \
            f"Expected {expected_avg}, got {result['rolling_avg_rating_5']}"

        print(f"\n  ✅ Match 4 滚动评分: {result['rolling_avg_rating_5']:.3f}")

    def test_window_size_respect(self, sample_matches):
        """测试滚动窗口大小限制"""
        calculator = RollingFeatureCalculator(window_size=2)

        target_match = sample_matches[3]  # Match 4

        result = calculator.calculate_rolling_xg(
            sample_matches,
            target_match["match_date"],
            target_match["team_id"],
            is_home=True
        )

        # 窗口大小 = 2，应该只取 Match 2, 3（最近的2场）
        # Match 2: home_xg = 1.5
        # Match 3: home_xg = 0.9
        # 平均值 = (1.5 + 0.9) / 2 = 1.2
        expected_avg = (1.5 + 0.9) / 2

        assert result["rolling_avg_xg_5"] == pytest.approx(expected_avg, 0.01), \
            f"Window size not respected! Expected {expected_avg}, got {result['rolling_avg_xg_5']}"

        print(f"\n  ✅ 窗口大小 = 2, 滚动均值: {result['rolling_avg_xg_5']:.3f}")

    def test_no_historical_data(self):
        """测试：没有历史数据时返回默认值"""
        calculator = RollingFeatureCalculator(window_size=5)

        target_date = datetime(2024, 1, 22)
        team_id = "new_team"

        result = calculator.calculate_rolling_xg(
            [],  # 空历史
            target_date,
            team_id,
            is_home=True
        )

        assert result["rolling_avg_xg_5"] == 0.0
        assert result["rolling_total_xg_5"] == 0.0

        print(f"\n  ✅ 无历史数据时返回默认值 0.0")

    def test_date_boundary_condition(self, sample_matches):
        """测试日期边界条件：同一天的比赛应该被排除"""
        # 添加同一天的比赛
        same_day_match = {
            "match_id": "4b",
            "match_date": datetime(2024, 1, 22),  # 同 Match 4 同一天
            "team_id": "team_abc",
            "opponent_id": "other_team",
            "home_xg": 3.0,
            "team_rating": 7.5,
        }

        calculator = RollingFeatureCalculator(window_size=5)

        target_match = sample_matches[3]
        extended_matches = sample_matches + [same_day_match]

        result = calculator.calculate_rolling_xg(
            extended_matches,
            target_match["match_date"],
            target_match["team_id"],
            is_home=True
        )

        # 同一天的比赛不应被计入
        # 仍应基于 Match 1, 2, 3
        expected_avg = (1.2 + 1.5 + 0.9) / 3

        assert result["rolling_avg_xg_5"] == pytest.approx(expected_avg, 0.01), \
            f"Same-day match leaked into rolling average!"

        print(f"\n  ✅ 同一天比赛被正确排除")


class TestRollingFeaturesIntegration:
    """集成测试：完整滚动特征计算"""

    def test_full_rolling_features_calculation(self, sample_matches):
        """
        测试完整滚动特征计算

        为每场比赛计算滚动特征，验证：
        1. 第一场比赛没有历史数据
        2. 后续比赛使用正确的历史窗口
        """
        calculator = RollingFeatureCalculator(window_size=5)

        results = []
        for match in sample_matches[:4]:  # 跳过 Match 5（未来）
            xg_result = calculator.calculate_rolling_xg(
                sample_matches,
                match["match_date"],
                match["team_id"],
                is_home=True
            )
            rating_result = calculator.calculate_rolling_rating(
                sample_matches,
                match["match_date"],
                match["team_id"]
            )

            results.append({
                "match_id": match["match_id"],
                "match_date": match["match_date"],
                "rolling_xg": xg_result["rolling_avg_xg_5"],
                "rolling_rating": rating_result["rolling_avg_rating_5"],
            })

        # 验证
        # Match 1: 无历史 -> 0.0
        assert results[0]["rolling_xg"] == 0.0
        assert results[0]["rolling_rating"] == 0.0

        # Match 2: 只有 Match 1 历史 -> 1.2
        assert results[1]["rolling_xg"] == pytest.approx(1.2, 0.01)

        # Match 3: Match 1, 2 -> (1.2 + 1.5) / 2 = 1.35
        assert results[2]["rolling_xg"] == pytest.approx(1.35, 0.01)

        # Match 4: Match 1, 2, 3 -> (1.2 + 1.5 + 0.9) / 3 = 1.2
        assert results[3]["rolling_xg"] == pytest.approx(1.2, 0.01)

        print("\n" + "=" * 70)
        print("  📊 滚动特征计算结果:")
        print("=" * 70)
        for r in results:
            print(f"    Match {r['match_id']}: xG={r['rolling_xg']:.3f}, rating={r['rolling_rating']:.3f}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
