#!/usr/bin/env python3
"""
V41.186 SmartOddsFilter - 智能赔率过滤器 (The 71-Set Filter)
====================================================================

核心功能：
    - 从 V41.185 发现的 71 组数字中智能提取 Pinnacle 数据
    - 锁定带 "Pinnacle" 标识的行，按时间戳排序
    - 最早的一组为初盘 (Opening)，最晚的一组为终盘 (Closing)

Usage:
    from src.services.odds_filter import SmartOddsFilter

    filter = SmartOddsFilter()
    result = filter.extract_pinnacle_data(odds_sets)

Author: V41.186 Integration Team
Date: 2026-01-19
Version: V41.186 "终极缝合"
"""

from __future__ import annotations

import builtins
import contextlib
from dataclasses import dataclass, field
import logging
import re
from typing import Any

logger = logging.getLogger("V41.186")


# =============================================================================
# 数据模型
# =============================================================================


@dataclass
class OddsSet:
    """单组赔率数据"""

    h: float
    d: float
    a: float
    timestamp: str | None = None
    source: str = "unknown"
    bookmaker: str = "unknown"
    is_pinnacle: bool = False
    sequence: int = -1

    def calculate_payout(self) -> float:
        """计算返还率"""
        if self.h and self.d and self.a:
            return 1 / (1 / self.h + 1 / self.d + 1 / self.a) * 100
        return 0.0

    def is_valid(self) -> bool:
        """检查是否有效"""
        return (
            self.h >= 1.01
            and self.h <= 10.0
            and self.d >= 1.01
            and self.d <= 15.0
            and self.a >= 1.01
            and self.a <= 20.0
            and self.calculate_payout() >= 85
            and self.calculate_payout() <= 102
        )


@dataclass
class PinnacleHistory:
    """Pinnacle 完整历史"""

    opening: OddsSet | None = None
    closing: OddsSet | None = None
    movements: list[OddsSet] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "opening": {
                "h": self.opening.h if self.opening else None,
                "d": self.opening.d if self.opening else None,
                "a": self.opening.a if self.opening else None,
                "timestamp": self.opening.timestamp if self.opening else None,
                "payout": self.opening.calculate_payout() if self.opening else None,
            },
            "closing": {
                "h": self.closing.h if self.closing else None,
                "d": self.closing.d if self.closing else None,
                "a": self.closing.a if self.closing else None,
                "timestamp": self.closing.timestamp if self.closing else None,
                "payout": self.closing.calculate_payout() if self.closing else None,
            },
            "movements": [
                {"h": m.h, "d": m.d, "a": m.a, "timestamp": m.timestamp, "sequence": m.sequence}
                for m in self.movements
            ],
            "movement_count": len(self.movements),
        }


# =============================================================================
# SmartOddsFilter - 智能过滤器
# =============================================================================


class SmartOddsFilter:
    """V41.186 智能赔率过滤器 - 从 71 组数据中提取 Pinnacle"""

    # Pinnacle 识别关键词
    PINNACLE_KEYWORDS = ["pinnacle", "pinna", "pinn", "id-18"]

    # 赔率合理性范围
    VALID_RANGES = {"h": (1.1, 5.0), "d": (2.0, 6.0), "a": (1.5, 10.0)}

    def __init__(self, debug: bool = False):
        self.debug = debug

    def extract_pinnacle_data(
        self, odds_sets: list[dict] | list[tuple], page_text: str | None = None
    ) -> PinnacleHistory:
        """
        从赔率集合中提取 Pinnacle 数据

        参数:
            odds_sets: 赔率数据列表（来自 V41.185 的 71 组数据）
            page_text: 页面文本（用于识别 Pinnacle 标识）

        返回:
            PinnacleHistory 包含 opening/closing/movements
        """
        logger.info(f"🎯 开始处理 {len(odds_sets)} 组赔率数据...")

        # 步骤1: 解析所有赔率数据
        parsed_sets = self._parse_odds_sets(odds_sets, page_text)

        logger.info(f"  解析后: {len(parsed_sets)} 组有效数据")

        # 步骤2: 识别 Pinnacle 数据
        pinnacle_sets = self._identify_pinnacle(parsed_sets)

        logger.info(f"  识别出 {len(pinnacle_sets)} 组 Pinnacle 数据")

        # 步骤3: 排序（如果有时间戳）
        sorted_sets = self._sort_by_timestamp(pinnacle_sets)

        # 步骤4: 提取 opening/closing
        if sorted_sets:
            opening = sorted_sets[0]
            closing = sorted_sets[-1]

            # 检查是否有变盘历史
            movements = []
            if len(sorted_sets) > 2:
                movements = sorted_sets[1:-1]  # 排除首尾
            elif len(sorted_sets) == 2 and opening.h != closing.h:
                # 只有两组但不同，记录为变盘
                movements = [closing]

            logger.info("  ✅ 提取成功:")
            logger.info(f"     初盘: [{opening.h}, {opening.d}, {opening.a}]")
            logger.info(f"     终盘: [{closing.h}, {closing.d}, {closing.a}]")
            logger.info(f"     变盘: {len(movements)} 次")

            return PinnacleHistory(opening=opening, closing=closing, movements=movements)

        # 如果没有找到 Pinnacle 数据，使用最佳替代方案
        logger.warning("⚠️  未找到明确的 Pinnacle 数据，使用最佳替代")

        # 从所有数据中选择最合理的
        all_valid = [s for s in parsed_sets if s.is_valid()]

        if all_valid:
            # 选择主胜赔率最低的作为终盘（最看好主队）
            closing = min(all_valid, key=lambda x: x.h)
            # 选择主胜赔率最高的作为初盘
            opening = max(all_valid, key=lambda x: x.h)

            logger.info("  ⚡ 替代方案:")
            logger.info(f"     初盘: [{opening.h}, {opening.d}, {opening.a}]")
            logger.info(f"     终盘: [{closing.h}, {closing.d}, {closing.a}]")

            return PinnacleHistory(opening=opening, closing=closing)

        logger.error("❌ 没有找到任何有效赔率数据")
        return PinnacleHistory()

    def _parse_odds_sets(
        self, odds_sets: list[dict] | list[tuple], page_text: str | None = None
    ) -> list[OddsSet]:
        """解析赔率集合"""
        parsed = []

        for idx, item in enumerate(odds_sets):
            try:
                # 处理字典格式
                if isinstance(item, dict):
                    h = item.get("h")
                    d = item.get("d")
                    a = item.get("a")

                    if not all([h, d, a]):
                        # 尝试其他键名
                        h = item.get("home") or item.get("1")
                        d = item.get("draw") or item.get("x") or item.get("2")
                        a = item.get("away") or item.get("12")

                    if not all([h, d, a]):
                        continue

                    odds_set = OddsSet(
                        h=float(h),
                        d=float(d),
                        a=float(a),
                        timestamp=item.get("time") or item.get("timestamp"),
                        source=item.get("source", "unknown"),
                        bookmaker=item.get("bookmaker", "unknown"),
                        sequence=idx,
                    )

                # 处理元组格式
                elif isinstance(item, (list, tuple)) and len(item) >= 3:
                    odds_set = OddsSet(
                        h=float(item[0]), d=float(item[1]), a=float(item[2]), sequence=idx
                    )
                else:
                    continue

                # 验证数据
                if odds_set.is_valid():
                    parsed.append(odds_set)

            except (ValueError, TypeError) as e:
                logger.debug(f"跳过无效数据 {idx}: {e}")
                continue

        return parsed

    def _identify_pinnacle(self, odds_sets: list[OddsSet]) -> list[OddsSet]:
        """识别 Pinnacle 数据"""
        pinnacle = []

        for odds_set in odds_sets:
            # 检查是否标记为 Pinnacle
            if odds_set.bookmaker.lower() in ["pinnacle", "entity_p"]:
                odds_set.is_pinnacle = True
                pinnacle.append(odds_set)
                continue

            # 检查返还率（Pinnacle 通常有较高的返还率 ~97%）
            payout = odds_set.calculate_payout()
            if 96.5 <= payout <= 98.5:
                odds_set.is_pinnacle = True
                odds_set.source = "pinnacle_by_payout"
                pinnacle.append(odds_set)

        return pinnacle

    def _sort_by_timestamp(self, odds_sets: list[OddsSet]) -> list[OddsSet]:
        """按时间戳排序"""
        # 如果有时间戳，按时间排序
        with_timestamp = [s for s in odds_sets if s.timestamp]
        without_timestamp = [s for s in odds_sets if not s.timestamp]

        if with_timestamp:
            with contextlib.suppress(builtins.BaseException):
                with_timestamp.sort(key=lambda x: x.timestamp or "")

        # 按序列号排序没有时间戳的
        without_timestamp.sort(key=lambda x: x.sequence)

        return with_timestamp + without_timestamp

    # ========================================================================
    # 从页面文本直接提取
    # ========================================================================

    def extract_from_page_text(self, page_text: str) -> PinnacleHistory:
        """
        直接从页面文本中提取 Pinnacle 数据

        这是 V41.185 发现的 71 组数据的来源
        """
        # 提取所有赔率数字组合
        odds_pattern = r"\b([1-9]\.\d{2,3})[^\d]*([1-9]\.\d{2,3})[^\d]*([1-9]\.\d{2,3})\b"
        matches = re.findall(odds_pattern, page_text)

        odds_sets = []
        for match in matches:
            try:
                h, d, a = float(match[0]), float(match[1]), float(match[2])

                # 验证合理性
                if (
                    self.VALID_RANGES["h"][0] <= h <= self.VALID_RANGES["h"][1]
                    and self.VALID_RANGES["d"][0] <= d <= self.VALID_RANGES["d"][1]
                    and self.VALID_RANGES["a"][0] <= a <= self.VALID_RANGES["a"][1]
                ):
                    odds_sets.append({"h": h, "d": d, "a": a})

            except ValueError:
                continue

        return self.extract_pinnacle_data(odds_sets, page_text)


# =============================================================================
# 便捷函数
# =============================================================================


def extract_pinnacle_from_v41_185_result(v41_185_result: dict) -> PinnacleHistory:
    """
    从 V41.185 的结果中提取 Pinnacle 数据

    参数:
        v41_185_result: V41.185 返回的 all_combinations 数据

    返回:
        PinnacleHistory 对象
    """
    filter = SmartOddsFilter()

    all_combinations = v41_185_result.get("odds_data", {}).get("all_combinations", [])

    return filter.extract_pinnacle_data(all_combinations)


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)

    # 模拟 V41.185 的输出
    test_data = {
        "odds_data": {
            "closing": {"h": 1.62, "d": 3.97, "a": 6.16},
            "all_combinations": [
                {"h": 1.62, "d": 3.97, "a": 6.16},
                {"h": 1.59, "d": 3.88, "a": 6.00},
                {"h": 1.62, "d": 3.75, "a": 5.50},
                {"h": 1.60, "d": 3.90, "a": 5.60},
            ],
        }
    }

    filter = SmartOddsFilter(debug=True)
    result = extract_pinnacle_from_v41_185_result(test_data)

