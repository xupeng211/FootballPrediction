#!/usr/bin/env python3
"""
EV计算和投注策略模块
Expected Value Calculation and Betting Strategy Module

实现SRS要求的EV计算和投注建议功能:
- 期望价值(Expected Value)计算
- Kelly Criterion投注策略
- 风险管理和资金管理
- 投注建议生成
- 历史回测功能
- 投注组合优化

创建时间: 2025-10-29
Issue: #116 EV计算和投注策略
"""

import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

import numpy as np

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from src.core.config import get_config
    from src.core.logging_system import get_logger

    logger = get_logger(__name__)
except ImportError:
    sys.exit(1)


class BetType(Enum):
    """投注类型枚举"""

    HOME_WIN = "home_win"
    DRAW = "draw"
    AWAY_WIN = "away_win"
    OVER_2_5 = "over_2_5"
    UNDER_2_5 = "under_2_5"
    BTTS = "btts"  # Both Teams to Score
    CORRECT_SCORE = "correct_score"


class RiskLevel(Enum):
    """风险等级枚举"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class BettingOdds:
    """赔率数据结构"""

    home_win: float
    draw: float
    away_win: float
    over_2_5: float | None = None
    under_2_5: float | None = None
    btts_yes: float | None = None
    btts_no: float | None = None
    correct_score_home: float | None = None
    correct_score_draw: float | None = None
    correct_score_away: float | None = None

    # 赔率来源和置信度
    source: str = "unknown"
    confidence: float = 1.0
    margin: float = 0.0  # 庄家利润率


@dataclass
class PredictionProbabilities:
    """预测概率数据结构"""

    home_win: float
    draw: float
    away_win: float
    over_2_5: float | None = None
    under_2_5: float | None = None
    btts_yes: float | None = None
    btts_no: float | None = None

    # 置信度和元数据
    confidence: float = 1.0
    model_name: str = "unknown"
    prediction_time: datetime = None

    def __post_init__(self):
        """初始化后处理"""
        if self.prediction_time is None:
            self.prediction_time = datetime.now()
        # 确保概率总和为1（针对主要结果）
        total = self.home_win + self.draw + self.away_win
        if total > 0 and abs(total - 1.0) > 0.01:
            # 归一化概率
            self.home_win /= total
            self.draw /= total
            self.away_win /= total


@dataclass
class EVCalculation:
    """EV计算结果"""

    bet_type: BetType
    probability: float
    odds: float
    ev: float
    kelly_fraction: float
    risk_level: RiskLevel
    recommendation: str  # 'bet', 'avoid', 'wait'
    confidence: float

    # 附加指标
    value_rating: float  # 价值评级 (0-10)
    expected_roi: float  # 期望投资回报率
    bust_probability: float  # 破产概率
    suggested_stake: float  # 建议投注金额


@dataclass
class BettingStrategy:
    """投注策略配置"""

    name: str
    description: str
    max_kelly_fraction: float = 0.25  # 最大Kelly比例
    min_ev_threshold: float = 0.05  # 最小EV阈值
    risk_tolerance: float = 0.5  # 风险容忍度 (0-1)
    bankroll_percentage: float = 0.02  # 单次投注资金占比
    max_daily_bets: int = 5  # 每日最大投注次数
    value_threshold: float = 1.2  # 价值阈值 (概率 * 赔率)

    # 风险管理参数
    stop_loss: float = 0.1  # 止损比例
    take_profit: float = 0.2  # 止盈比例
    max_consecutive_losses: int = 3  # 最大连续亏损次数


class EVCalculator:
    """期望价值计算器"""

    def __init__(self):
        """初始化EV计算器"""
        self.config = get_config()
        self.logger = logger

        # SRS目标要求
        self.SRS_TARGETS = {
            "min_ev_threshold": 0.05,  # 最小EV 5%
            "min_value_rating": 6.0,  # 最小价值评级 6/10
            "max_risk_level": RiskLevel.MEDIUM,  # 最大风险等级
            "min_confidence": 0.6,  # 最小置信度 60%
            "kelly_criterion": True,  # 使用Kelly准则
            "risk_management": True,  # 启用风险管理
        }

    def calculate_ev(self, probability: float, odds: float) -> float:
        """计算期望价值 EV = (概率 * 赔率) - 1"""
        if probability <= 0 or odds <= 1:
            return -1.0
        return (probability * odds) - 1

    def calculate_kelly_fraction(
        self, ev: float, odds: float, probability: float, max_fraction: float = 0.25
    ) -> float:
        """计算Kelly准则投注比例

        Kelly公式: f* = (bp - q) / b
        其中: b = 赔率 - 1, p = 胜率, q = 败率
        """
        if ev <= 0 or odds <= 1:
            return 0.0

        b = odds - 1  # 净赔率
        p = probability
        q = 1 - probability

        # 标准Kelly公式
        kelly = (b * p - q) / b

        # 限制最大投注比例
        kelly = min(kelly, max_fraction)
        kelly = max(kelly, 0.0)  # 确保非负

        return kelly

    def assess_risk_level(
        self, probability: float, odds: float, ev: float
    ) -> RiskLevel:
        """评估风险等级"""
        if ev < 0:
            return RiskLevel.VERY_HIGH

        # 根据概率和EV评估风险
        if probability >= 0.7 and ev >= 0.15:
            return RiskLevel.LOW
        elif probability >= 0.5 and ev >= 0.08:
            return RiskLevel.MEDIUM
        elif probability >= 0.3 and ev >= 0.03:
            return RiskLevel.HIGH
        else:
            return RiskLevel.VERY_HIGH

    def calculate_value_rating(
        self, ev: float, probability: float, odds: float
    ) -> float:
        """计算价值评级 (0-10分)"""
        if ev < 0:
            return 0.0

        # 基础价值分数
        base_score = min(ev * 20, 8.0)  # EV转换为分数,最高8分

        # 概率加成
        prob_bonus = min(probability * 2, 2.0)  # 概率加成,最高2分

        total_score = base_score + prob_bonus
        return min(total_score, 10.0)

    def calculate_expected_roi(self, ev: float, kelly_fraction: float) -> float:
        """计算期望投资回报率"""
        if kelly_fraction <= 0:
            return 0.0
        return ev * kelly_fraction * 100  # 转换为百分比

    def calculate_bust_probability(
        self, kelly_fraction: float, probability: float
    ) -> float:
        """计算破产概率（简化版本）"""
        if kelly_fraction <= 0:
            return 0.0

        # 使用正态分布近似计算破产概率
        # 这是一个简化版本,实际应该使用更复杂的模型
        if probability < 0.5:
            return min(kelly_fraction * 2, 0.8)  # 概率低于50%时风险更高
        else:
            return max(0.0, kelly_fraction * 0.5 * (1 - probability))

    def generate_betting_recommendation(
        self, ev: float, probability: float, risk_level: RiskLevel, value_rating: float
    ) -> str:
        """生成投注建议"""
        # SRS要求的决策逻辑
        if ev < self.SRS_TARGETS["min_ev_threshold"]:
            return "avoid"

        if value_rating < self.SRS_TARGETS["min_value_rating"]:
            return "avoid"

        if probability < self.SRS_TARGETS["min_confidence"]:
            return "avoid"

        if risk_level.value > self.SRS_TARGETS["max_risk_level"].value:
            return "avoid"

        # 根据EV大小决定建议强度
        if ev >= 0.15 and value_rating >= 8.0:
            return "strong_bet"
        elif ev >= 0.08 and value_rating >= 6.5:
            return "bet"
        elif ev >= 0.05 and value_rating >= 6.0:
            return "small_bet"
        else:
            return "wait"

    def calculate_comprehensive_ev(
        self,
        bet_type: BetType,
        probability: float,
        odds: float,
        strategy: BettingStrategy,
    ) -> EVCalculation:
        """计算综合EV和投注建议"""

        # 基础计算
        ev = self.calculate_ev(probability, odds)
        kelly_frac = self.calculate_kelly_fraction(
            ev, odds, probability, strategy.max_kelly_fraction
        )

        # 风险评估
        risk_level = self.assess_risk_level(probability, odds, ev)
        value_rating = self.calculate_value_rating(ev, probability, odds)
        expected_roi = self.calculate_expected_roi(ev, kelly_frac)
        bust_prob = self.calculate_bust_probability(kelly_frac, probability)

        # 投注建议
        recommendation = self.generate_betting_recommendation(
            ev, probability, risk_level, value_rating
        )

        # 建议投注金额
        suggested_stake = kelly_frac * strategy.bankroll_percentage

        return EVCalculation(
            bet_type=bet_type,
            probability=probability,
            odds=odds,
            ev=ev,
            kelly_fraction=kelly_frac,
            risk_level=risk_level,
            recommendation=recommendation,
            confidence=min(probability * 1.2, 1.0),  # 置信度基于概率
            value_rating=value_rating,
            expected_roi=expected_roi,
            bust_probability=bust_prob,
            suggested_stake=suggested_stake,
        )


# 工厂函数和便捷接口
def create_ev_calculator() -> EVCalculator:
    """创建EV计算器实例"""
    return EVCalculator()


def create_custom_strategy(name: str, description: str, **kwargs) -> BettingStrategy:
    """创建自定义策略"""
    return BettingStrategy(name=name, description=description, **kwargs)


# 主要导出接口
__all__ = [
    "EVCalculator",
    "BettingOdds",
    "PredictionProbabilities",
    "EVCalculation",
    "BettingStrategy",
    "BetType",
    "RiskLevel",
    "create_ev_calculator",
    "create_custom_strategy",
]