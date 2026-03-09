#!/usr/bin/env python3
"""
共享常量加载器 - V1.0.0
======================

从 config/shared_constants.json 加载全局共享常量，确保 Python/Node.js 一致性。

使用方法:
    from src.constants.shared_constants import (
        MATCH_STATUS, MATCH_OUTCOME, DEFAULT_PROBABILITIES
    )

    # 比赛状态
    status = MATCH_STATUS.FINISHED  # "finished"

    # 比赛结果
    result = MATCH_OUTCOME.HOME_WIN  # 2

Author: Systems Architect
Version: V1.0.0
Date: 2026-03-07
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# 配置文件路径
SHARED_CONSTANTS_PATH = Path(__file__).parent.parent.parent / "config" / "shared_constants.json"


class MatchStatus(str, Enum):
    """比赛状态枚举"""

    FINISHED = "finished"
    LIVE = "live"
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    POSTPONED = "postponed"
    ABANDONED = "abandoned"

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        """检查状态是否为终态（不可变更）"""
        return status.lower() in (cls.FINISHED.value, cls.CANCELLED.value, cls.COMPLETED.value)

    @classmethod
    def is_active(cls, status: str) -> bool:
        """检查状态是否为活跃状态"""
        return status.lower() in (cls.LIVE.value, cls.SCHEDULED.value)


class MatchOutcome(int, Enum):
    """比赛结果枚举（整数，用于 ML 模型）"""

    AWAY_WIN = 0
    DRAW = 1
    HOME_WIN = 2

    @classmethod
    def from_scores(cls, home_score: int, away_score: int) -> MatchOutcome:
        """根据比分确定结果"""
        if home_score > away_score:
            return cls.HOME_WIN
        elif home_score < away_score:
            return cls.AWAY_WIN
        else:
            return cls.DRAW

    @classmethod
    def get_all_labels(cls) -> list[int]:
        """获取所有标签（按顺序）"""
        return [cls.AWAY_WIN, cls.DRAW, cls.HOME_WIN]

    @classmethod
    def get_label_names(cls) -> dict[int, str]:
        """获取标签名称映射"""
        return {cls.AWAY_WIN: "AWAY_WIN", cls.DRAW: "DRAW", cls.HOME_WIN: "HOME_WIN"}


@dataclass(frozen=True)
class DefaultProbabilities:
    """默认概率配置"""

    HOME_WIN: float = 0.46
    DRAW: float = 0.26
    AWAY_WIN: float = 0.28

    def to_dict(self) -> dict[str, float]:
        """转换为字典"""
        return {
            "HOME_WIN": self.HOME_WIN,
            "DRAW": self.DRAW,
            "AWAY_WIN": self.AWAY_WIN,
        }

    def to_list(self) -> list[float]:
        """转换为列表（按 AWAY_WIN, DRAW, HOME_WIN 顺序）"""
        return [self.AWAY_WIN, self.DRAW, self.HOME_WIN]


@dataclass(frozen=True)
class OddsLimits:
    """赔率限制配置"""

    MIN_ODDS: float = 1.01
    MAX_ODDS: float = 1000.0
    MIN_PAYOUT: float = 1.02
    MAX_PAYOUT: float = 1.08

    def is_valid_odds(self, odds: float) -> bool:
        """检查赔率是否在有效范围内"""
        return self.MIN_ODDS <= odds <= self.MAX_ODDS

    def is_valid_payout(self, payout: float) -> bool:
        """检查返还率是否在有效范围内"""
        return self.MIN_PAYOUT <= payout <= self.MAX_PAYOUT


@dataclass(frozen=True)
class ConfidenceThresholds:
    """置信度阈值配置"""

    HIGH: float = 0.70
    MEDIUM: float = 0.55
    LOW: float = 0.40

    def get_level(self, confidence: float) -> str:
        """根据置信度获取等级"""
        if confidence >= self.HIGH:
            return "HIGH"
        elif confidence >= self.MEDIUM:
            return "MEDIUM"
        elif confidence >= self.LOW:
            return "LOW"
        else:
            return "VERY_LOW"


@dataclass(frozen=True)
class StatisticalThresholds:
    """统计阈值配置"""

    MIN_SAMPLE_SIZE: int = 10
    RELIABLE_SAMPLE_SIZE: int = 30
    LARGE_SAMPLE_SIZE: int = 100

    def get_reliability(self, sample_size: int) -> str:
        """根据样本量获取可靠性等级"""
        if sample_size >= self.LARGE_SAMPLE_SIZE:
            return "HIGH"
        elif sample_size >= self.RELIABLE_SAMPLE_SIZE:
            return "MEDIUM"
        elif sample_size >= self.MIN_SAMPLE_SIZE:
            return "LOW"
        else:
            return "INSUFFICIENT"


def _load_shared_constants() -> dict[str, Any]:
    """加载共享常量 JSON 文件"""
    if not SHARED_CONSTANTS_PATH.exists():
        raise FileNotFoundError(f"Shared constants file not found: {SHARED_CONSTANTS_PATH}")

    with open(SHARED_CONSTANTS_PATH, encoding="utf-8") as f:
        return json.load(f)


# 全局实例（延迟加载）
_constants_cache: dict[str, Any] | None = None


def get_constants() -> dict[str, Any]:
    """获取共享常量（带缓存）"""
    global _constants_cache
    if _constants_cache is None:
        _constants_cache = _load_shared_constants()
    return _constants_cache


def reload_constants() -> dict[str, Any]:
    """重新加载常量（用于热更新）"""
    global _constants_cache
    _constants_cache = _load_shared_constants()
    return _constants_cache


# 导出的常量实例
# V4.46.2: Enum 类直接使用，dataclass 类需要实例化
MATCH_STATUS = MatchStatus  # Enum 类，直接使用
MATCH_OUTCOME = MatchOutcome  # Enum 类，直接使用
DEFAULT_PROBABILITIES = DefaultProbabilities()  # dataclass，实例化
ODDS_LIMITS = OddsLimits()  # dataclass，实例化
CONFIDENCE_THRESHOLDS = ConfidenceThresholds()  # dataclass，实例化
STATISTICAL_THRESHOLDS = StatisticalThresholds()  # dataclass，实例化

# 向后兼容的常量值
HOME_WIN = MatchOutcome.HOME_WIN  # 2
DRAW = MatchOutcome.DRAW  # 1
AWAY_WIN = MatchOutcome.AWAY_WIN  # 0

# 比赛状态常量（字符串）
STATUS_FINISHED = MatchStatus.FINISHED.value  # "finished"
STATUS_LIVE = MatchStatus.LIVE.value  # "live"
STATUS_SCHEDULED = MatchStatus.SCHEDULED.value  # "scheduled"
STATUS_CANCELLED = MatchStatus.CANCELLED.value  # "cancelled"

__all__ = [
    # 枚举类
    "MatchStatus",
    "MatchOutcome",
    # 配置类
    "DefaultProbabilities",
    "OddsLimits",
    "ConfidenceThresholds",
    "StatisticalThresholds",
    # 全局实例
    "MATCH_STATUS",
    "MATCH_OUTCOME",
    "DEFAULT_PROBABILITIES",
    "ODDS_LIMITS",
    "CONFIDENCE_THRESHOLDS",
    "STATISTICAL_THRESHOLDS",
    # 向后兼容常量
    "HOME_WIN",
    "DRAW",
    "AWAY_WIN",
    "STATUS_FINISHED",
    "STATUS_LIVE",
    "STATUS_SCHEDULED",
    "STATUS_CANCELLED",
    # 工具函数
    "get_constants",
    "reload_constants",
]
