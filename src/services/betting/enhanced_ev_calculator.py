from typing import Any

#!/usr/bin/env python3
"""
增强版EV计算器 - Issue #121优化版本
Enhanced EV Calculator for Issue #121 Optimization

主要优化:
1. 改进Kelly Criterion参数计算
2. 增强价值评级算法
3. 动态风险管理
4. 高级回测验证
5. 自适应参数调整

创建时间: 2025-10-29
Issue: #121 EV计算算法参数调优
"""

import logging
import math
import sys
from enum import Enum
from pathlib import Path

import numpy as np

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from src.services.betting.ev_calculator import (BettingOdds,
                                                    BettingStrategy, BetType,
                                                    EVCalculation,
                                                    PredictionProbabilities,
                                                    RiskLevel)
except ImportError as e:
    print(f"基础EV计算器导入错误: {e}")

    # 如果导入失败,使用备用定义
    # 定义基础类型以防导入失败
    class BetType(Enum):
        HOME_WIN = "home_win"
        DRAW = "draw"
        AWAY_WIN = "away_win"
        OVER_2_5 = "over_2_5"
        UNDER_2_5 = "under_2_5"
        BTTS = "btts"

    class RiskLevel(Enum):
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        VERY_HIGH = "very_high"

    @dataclass
    class BettingOdds:
        """投注赔率数据类"""

        match_id: int
        home_win: float
        draw: float
        away_win: float
        over_under: float | None = None
        asian_handicap: float | None = None
        home_win: float
        draw: float
        away_win: float
        over_2_5: float | None = None
        under_2_5: float | None = None
        btts_yes: float | None = None
        source: str = "unknown"

    @dataclass
    class PredictionProbabilities:
        """预测概率数据类"""

        home_win: float
        draw: float
        away_win: float
        over_2_5: float | None = None
        btts_yes: float | None = None
        over_2_5: float | None = None
        under_2_5: float | None = None
        btts_yes: float | None = None
        confidence: float = 1.0

    @dataclass
    class EVCalculation:
        """期望值计算结果"""

        bet_type: BetType
        probability: float
        odds: float
        ev: float
        kelly_fraction: float
        risk_level: RiskLevel
        recommendation: str
        confidence: float
        value_rating: float
        expected_roi: float
        bust_probability: float
        suggested_stake: float

    @dataclass
    class BettingStrategy:
        """投注策略配置"""

        name: str
        description: str
        max_kelly_fraction: float = 0.25
        min_ev_threshold: float = 0.05
        risk_tolerance: float = 0.5
        bankroll_percentage: float = 0.02
        max_daily_bets: int = 5
        value_threshold: float = 1.2


logger = logging.getLogger(__name__)


@dataclass
class KellyOptimizationResult:
    """类文档字符串"""

    pass  # 添加pass语句
    """Kelly准则优化结果"""

    optimal_fraction: float
    expected_growth: float
    risk_of_ruin: float
    confidence_interval: tuple[float, float]
    sensitivity_analysis: dict[str, float]
    recommended_adjustment: str


@dataclass
class EnhancedValueRating:
    """类文档字符串"""

    pass  # 添加pass语句
    """增强价值评级结果"""

    overall_rating: float
    ev_score: float
    probability_score: float
    odds_fairness_score: float
    market_efficiency_score: float
    risk_adjusted_score: float
    historical_performance_score: float
    rating_breakdown: dict[str, float]


class EnhancedKellyCalculator:
    """类文档字符串"""

    pass  # 添加pass语句
    """增强Kelly准则计算器"""

    def __init__(self):
        """函数文档字符串"""
        pass
        # 添加pass语句
        self.logger = logger
        # 优化后的Kelly参数
        self.fractional_kelly_multiplier = 0.25  # 分数Kelly乘数
        self.min_edge_threshold = 0.02  # 最小优势阈值
        self.max_drawdown_tolerance = 0.20  # 最大回撤容忍度
        self.volatility_adjustment = True  # 启用波动率调整
        self.confidence_weighting = True  # 启用置信度权重

    def calculate_fractional_kelly(
        self,
        true_probability: float,
        decimal_odds: float,
        confidence: float = 1.0,
        bankroll: float = 1000.0,
        historical_performance: dict[str, float] | None = None,
    ) -> KellyOptimizationResult:
        """
        计算优化的分数Kelly准则

        Args:
            true_probability: 真实概率
            decimal_odds: 小数赔率
            confidence: 预测置信度
            bankroll: 资金池
            historical_performance: 历史表现数据
        """

        # 基础Kelly计算
        b = decimal_odds - 1  # 净赔率
        p = true_probability
        q = 1 - p

        if b <= 0 or p <= 0 or p >= 1:
            return KellyOptimizationResult(
                optimal_fraction=0.0,
                expected_growth=0.0,
                risk_of_ruin=1.0,
                confidence_interval=(0.0, 0.0),
                sensitivity_analysis={},
                recommended_adjustment="avoid",
            )

        # 标准Kelly公式
        kelly_standard = (b * p - q) / b

        # 应用优化因子
        kelly_optimized = self._apply_kelly_optimizations(
            kelly_standard, p, b, confidence, historical_performance
        )

        # 计算风险指标
        expected_growth = self._calculate_expected_growth(kelly_optimized, p, b)
        risk_of_ruin = self._calculate_risk_of_ruin(kelly_optimized, p, b)

        # 置信区间计算
        confidence_interval = self._calculate_kelly_confidence_interval(
            kelly_optimized, p, b, confidence
        )

        # 敏感性分析
        sensitivity = self._perform_sensitivity_analysis(kelly_optimized, p, b)

        # 推荐调整
        recommendation = self._generate_kelly_recommendation(
            kelly_optimized, risk_of_ruin, expected_growth
        )

        return KellyOptimizationResult(
            optimal_fraction=kelly_optimized,
            expected_growth=expected_growth,
            risk_of_ruin=risk_of_ruin,
            confidence_interval=confidence_interval,
            sensitivity_analysis=sensitivity,
            recommended_adjustment=recommendation,
        )

    def _apply_kelly_optimizations(
        self,
        kelly_standard: float,
        probability: float,
        net_odds: float,
        confidence: float,
        historical_performance: dict[str, float] | None,
    ) -> float:
        """应用Kelly准则优化"""

        # 1. 分数Kelly调整
        kelly_fractional = kelly_standard * self.fractional_kelly_multiplier

        # 2. 置信度权重
        if self.confidence_weighting:
            confidence_factor = 0.5 + (confidence * 0.5)  # 0.5-1.0范围
            kelly_fractional *= confidence_factor

        # 3. 波动率调整
        if self.volatility_adjustment:
            volatility_penalty = self._calculate_volatility_penalty(
                probability, net_odds
            )
            kelly_fractional *= 1 - volatility_penalty

        # 4. 历史表现调整
        if historical_performance:
            performance_factor = self._calculate_performance_factor(
                historical_performance
            )
            kelly_fractional *= performance_factor

        # 5. 安全边界
        kelly_fractional = max(0, min(kelly_fractional, 0.25))  # 限制在0-25%

        return kelly_fractional

    def _calculate_volatility_penalty(
        self, probability: float, net_odds: float
    ) -> float:
        """计算波动率惩罚"""
        # 基于概率和赔率的方差计算波动率
        variance = probability * (net_odds**2) * (1 - probability)
        volatility = math.sqrt(variance)

        # 将波动率转换为惩罚因子 (0-0.5范围)
        penalty = min(volatility * 0.1, 0.5)
        return penalty

    def _calculate_performance_factor(self, historical: dict[str, float]) -> float:
        """基于历史表现计算调整因子"""
        if not historical:
            return 1.0

        # 关键指标权重
        weights = {"accuracy": 0.4, "roi": 0.3, "consistency": 0.2, "max_drawdown": 0.1}

        factors = []
        for metric, weight in weights.items():
            value = historical.get(metric, 0.0)

            if metric == "accuracy":
                # 准确率转换为因子 (0.5-1.5范围)
                factor = 0.5 + value
            elif metric == "roi":
                # ROI转换为因子 (0.8-1.2范围)
                factor = 0.8 + min(value * 0.4, 0.4)
            elif metric == "consistency":
                # 一致性转换为因子 (0.9-1.1范围)
                factor = 0.9 + value * 0.2
            elif metric == "max_drawdown":
                # 最大回撤转换为因子 (0.7-1.0范围)
                factor = max(0.7, 1.0 - value)

            factors.append(factor)

        # 加权平均
        performance_factor = sum(
            f * w for f, w in zip(factors, weights.values(), strict=False)
        )
        return max(0.5, min(performance_factor, 1.5))

    def _calculate_expected_growth(
        self, kelly_fraction: float, probability: float, net_odds: float
    ) -> float:
        """计算期望增长率"""
        if kelly_fraction <= 0:
            return 0.0

        # 期望增长率公式: G(f) = p*log(1+f*b) + q*log(1-f)
        f = kelly_fraction
        b = net_odds
        p = probability
        q = 1 - p

        if f * b > 1:  # 避免对数负数
            return 0.0

        growth_rate = p * math.log(1 + f * b) + q * math.log(1 - f)
        return growth_rate

    def _calculate_risk_of_ruin(
        self, kelly_fraction: float, probability: float, net_odds: float
    ) -> float:
        """计算破产风险"""
        if kelly_fraction <= 0:
            return 0.0

        # 简化的破产风险计算
        edge = probability * net_odds - (1 - probability)

        if edge <= 0:
            return 1.0  # 没有优势时破产风险为100%

        # 基于Kelly比例和优势的风险评估
        kelly_ratio = kelly_fraction / (
            (probability * net_odds - (1 - probability)) / net_odds
        )

        if kelly_ratio > 1:
            return 0.5  # 超过Kelly标准时风险较高

        # 风险随Kelly比例增加
        risk = min(kelly_ratio * 0.2, 0.3)  # 限制在30%以下
        return risk

    def _calculate_kelly_confidence_interval(
        self,
        kelly_fraction: float,
        probability: float,
        net_odds: float,
        confidence: float,
    ) -> tuple[float, float]:
        """计算Kelly分数的置信区间"""
        if kelly_fraction <= 0:
            return (0.0, 0.0)

        # 基于置信度计算区间宽度
        interval_width = (1 - confidence) * kelly_fraction * 2

        lower = max(0, kelly_fraction - interval_width)
        upper = min(kelly_fraction + interval_width, 0.25)

        return (lower, upper)

    def _perform_sensitivity_analysis(
        self, kelly_fraction: float, probability: float, net_odds: float
    ) -> dict[str, float]:
        """执行敏感性分析"""
        sensitivity = {}

        # 概率敏感性
        prob_delta = 0.01  # 1%变化
        kelly_plus = (
            (net_odds * (probability + prob_delta) - (1 - probability - prob_delta))
            / net_odds
        ) * self.fractional_kelly_multiplier
        kelly_minus = (
            (net_odds * (probability - prob_delta) - (1 - probability + prob_delta))
            / net_odds
        ) * self.fractional_kelly_multiplier

        sensitivity["probability_sensitivity"] = abs(kelly_plus - kelly_minus) / (
            2 * prob_delta
        )

        # 赔率敏感性
        odds_delta = 0.1  # 10%变化
        kelly_odds_plus = (
            ((net_odds + odds_delta) * probability - (1 - probability))
            / (net_odds + odds_delta)
            * self.fractional_kelly_multiplier
        )
        kelly_odds_minus = max(
            0,
            ((net_odds - odds_delta) * probability - (1 - probability))
            / max(net_odds - odds_delta, 0.01)
            * self.fractional_kelly_multiplier,
        )

        sensitivity["odds_sensitivity"] = abs(kelly_odds_plus - kelly_odds_minus) / (
            2 * odds_delta
        )

        return sensitivity

    def _generate_kelly_recommendation(
        self, kelly_fraction: float, risk_of_ruin: float, expected_growth: float
    ) -> str:
        """生成Kelly建议"""
        if kelly_fraction <= 0:
            return "avoid"
        elif risk_of_ruin > 0.25:
            return "reduce_stake"
        elif expected_growth > 0.05 and risk_of_ruin < 0.1:
            return "full_kelly"
        elif kelly_fraction > 0.15:
            return "fractional_kelly_conservative"
        else:
            return "standard"


class EnhancedValueRatingCalculator:
    """类文档字符串"""

    pass  # 添加pass语句
    """增强价值评级计算器"""

    def __init__(self):
        """函数文档字符串"""
        pass
        # 添加pass语句
        self.logger = logger
        # 评级权重配置
        self.weights = {
            "ev_score": 0.25,  # EV分数权重
            "probability_score": 0.20,  # 概率分数权重
            "odds_fairness": 0.20,  # 赔率公平性权重
            "market_efficiency": 0.15,  # 市场效率权重
            "risk_adjusted": 0.15,  # 风险调整权重
            "historical_performance": 0.05,  # 历史表现权重
        }

    def calculate_enhanced_value_rating(
        self,
        probability: float,
        odds: float,
        confidence: float,
        market_data: dict[str, Any] | None = None,
        historical_data: dict[str, Any] | None = None,
    ) -> EnhancedValueRating:
        """
        计算增强价值评级
        """

        # 1. EV分数
        ev = (probability * odds) - 1
        ev_score = self._calculate_ev_score(ev)

        # 2. 概率分数
        probability_score = self._calculate_probability_score(probability, confidence)

        # 3. 赔率公平性分数
        odds_fairness_score = self._calculate_odds_fairness_score(probability, odds)

        # 4. 市场效率分数
        market_efficiency_score = self._calculate_market_efficiency_score(
            probability, odds, market_data
        )

        # 5. 风险调整分数
        risk_adjusted_score = self._calculate_risk_adjusted_score(
            ev, probability, odds, confidence
        )

        # 6. 历史表现分数
        historical_performance_score = self._calculate_historical_performance_score(
            historical_data
        )

        # 计算综合评级
        overall_rating = (
            ev_score * self.weights["ev_score"]
            + probability_score * self.weights["probability_score"]
            + odds_fairness_score * self.weights["odds_fairness"]
            + market_efficiency_score * self.weights["market_efficiency"]
            + risk_adjusted_score * self.weights["risk_adjusted"]
            + historical_performance_score * self.weights["historical_performance"]
        )

        # 创建详细分解
        rating_breakdown = {
            "ev_score": ev_score,
            "probability_score": probability_score,
            "odds_fairness_score": odds_fairness_score,
            "market_efficiency_score": market_efficiency_score,
            "risk_adjusted_score": risk_adjusted_score,
            "historical_performance_score": historical_performance_score,
        }

        return EnhancedValueRating(
            overall_rating=min(overall_rating, 10.0),
            ev_score=ev_score,
            probability_score=probability_score,
            odds_fairness_score=odds_fairness_score,
            market_efficiency_score=market_efficiency_score,
            risk_adjusted_score=risk_adjusted_score,
            historical_performance_score=historical_performance_score,
            rating_breakdown=rating_breakdown,
        )

    def _calculate_ev_score(self, ev: float) -> float:
        """计算EV分数 (0-10)"""
        if ev <= 0:
            return 0.0

        # 使用对数函数映射EV到分数
        # EV=0.05 -> 6分, EV=0.1 -> 8分, EV=0.2 -> 9.5分, EV=0.5 -> 10分
        if ev < 0.05:
            score = ev * 120  # 线性映射
        else:
            score = 6 + math.log(ev / 0.05) * 3

        return min(score, 10.0)

    def _calculate_probability_score(
        self, probability: float, confidence: float
    ) -> float:
        """计算概率分数 (0-10)"""
        # 基于概率置信度的分数
        base_score = probability * 8  # 0-8分

        # 置信度加成
        confidence_bonus = confidence * 2  # 0-2分

        total_score = base_score + confidence_bonus
        return min(total_score, 10.0)

    def _calculate_odds_fairness_score(self, probability: float, odds: float) -> float:
        """计算赔率公平性分数 (0-10)"""
        fair_odds = 1 / probability if probability > 0 else float("inf")
        actual_odds = odds

        if fair_odds == 0:
            return 0.0

        # 计算赔率偏差百分比
        odds_deviation = abs(actual_odds - fair_odds) / fair_odds

        # 偏差越小分数越高
        if odds_deviation <= 0.05:  # 5%以内
            return 10.0
        elif odds_deviation <= 0.1:  # 10%以内
            return 8.0
        elif odds_deviation <= 0.2:  # 20%以内
            return 6.0
        elif odds_deviation <= 0.3:  # 30%以内
            return 4.0
        else:
            return max(0.0, 2.0 - odds_deviation)

    def _calculate_market_efficiency_score(
        self, probability: float, odds: float, market_data: dict[str, Any] | None
    ) -> float:
        """计算市场效率分数 (0-10)"""
        if not market_data:
            # 没有市场数据时给予基础分数
            return 6.0

        # 市场效率指标
        efficiency_factors = []

        # 1. 价格一致性
        if "market_odds" in market_data:
            market_odds = market_data["market_odds"]
            price_consistency = 1 - abs(odds - market_odds) / market_odds
            efficiency_factors.append(price_consistency * 10)

        # 2. 流动性指标
        if "liquidity_score" in market_data:
            liquidity_score = market_data["liquidity_score"]
            efficiency_factors.append(liquidity_score * 10)

        # 3. 市场深度
        if "market_depth" in market_data:
            depth_score = min(
                market_data["market_depth"] / 1000000, 1.0
            )  # 假设100万为满分
            efficiency_factors.append(depth_score * 10)

        # 4. 价差分析
        if "spread_percentage" in market_data:
            spread = market_data["spread_percentage"]
            spread_score = max(0, 10 - spread * 100)  # 价差越小分数越高
            efficiency_factors.append(spread_score)

        if efficiency_factors:
            return np.mean(efficiency_factors)
        else:
            return 6.0

    def _calculate_risk_adjusted_score(
        self, ev: float, probability: float, odds: float, confidence: float
    ) -> float:
        """计算风险调整分数 (0-10)"""
        if ev <= 0:
            return 0.0

        # 基础分数
        base_score = min(ev * 10, 8.0)

        # 风险调整因子
        risk_factors = []
        # 用于记录和调试各种风险因素
        logger.debug(
            f"Risk factors initialized for EV calculation: {len(risk_factors)} factors"
        )

        # 1. 概率风险
        if probability < 0.3:
            prob_risk = 0.5  # 低概率高风险
        elif probability < 0.5:
            prob_risk = 0.3
        elif probability < 0.7:
            prob_risk = 0.1
        else:
            prob_risk = 0.0

        # 2. 赔率风险
        if odds > 5.0:
            odds_risk = 0.3  # 高赔率高风险
        elif odds > 3.0:
            odds_risk = 0.2
        elif odds > 2.0:
            odds_risk = 0.1
        else:
            odds_risk = 0.0

        # 3. 置信度风险
        confidence_risk = (1 - confidence) * 0.2

        total_risk = prob_risk + odds_risk + confidence_risk
        risk_adjusted_score = base_score * (1 - total_risk)

        return max(0.0, min(risk_adjusted_score, 10.0))

    def _calculate_historical_performance_score(
        self, historical_data: dict[str, Any] | None
    ) -> float:
        """计算历史表现分数 (0-10)"""
        if not historical_data:
            return 5.0  # 默认中等分数

        # 关键历史指标
        performance_factors = []

        # 1. 历史准确率
        if "accuracy" in historical_data:
            accuracy = historical_data["accuracy"]
            performance_factors.append(accuracy * 10)

        # 2. 历史ROI
        if "roi" in historical_data:
            roi = historical_data["roi"]
            # ROI转换为分数 (正ROI加分,负ROI减分)
            roi_score = 5 + roi * 10
            performance_factors.append(max(0, min(roi_score, 10)))

        # 3. 连胜连败记录
        if "win_streak" in historical_data:
            streak = historical_data["win_streak"]
            streak_score = 5 + streak  # 连胜加分,连败减分
            performance_factors.append(max(0, min(streak_score, 10)))

        # 4. 波动率
        if "volatility" in historical_data:
            volatility = historical_data["volatility"]
            # 低波动率加分
            volatility_score = 10 - min(volatility * 20, 5)
            performance_factors.append(max(5, volatility_score))

        if performance_factors:
            return np.mean(performance_factors)
        else:
            return 5.0


class EnhancedEVCalculator:
    """类文档字符串"""

    pass  # 添加pass语句
    """增强EV计算器主类"""

    def __init__(self):
        """函数文档字符串"""
        pass
        # 添加pass语句
        self.kelly_calculator = EnhancedKellyCalculator()
        self.value_calculator = EnhancedValueRatingCalculator()
        self.logger = logger
        self.redis_manager = get_redis_manager()

        # 优化后的策略配置
        self.optimized_strategies = self._create_optimized_strategies()

    def _create_optimized_strategies(self) -> dict[str, BettingStrategy]:
        """创建优化后的策略"""
        return {
            "ultra_conservative": BettingStrategy(
                name="超级保守策略",
                description="最低风险,适合风险厌恶型投注者",
                max_kelly_fraction=0.10,
                min_ev_threshold=0.08,
                risk_tolerance=0.2,
                bankroll_percentage=0.005,
                max_daily_bets=2,
                value_threshold=1.4,
            ),
            "conservative_optimized": BettingStrategy(
                name="保守优化策略",
                description="使用增强Kelly的保守策略",
                max_kelly_fraction=0.15,
                min_ev_threshold=0.06,
                risk_tolerance=0.3,
                bankroll_percentage=0.01,
                max_daily_bets=3,
                value_threshold=1.3,
            ),
            "balanced_enhanced": BettingStrategy(
                name="平衡增强策略",
                description="使用完整优化算法的平衡策略",
                max_kelly_fraction=0.25,
                min_ev_threshold=0.04,
                risk_tolerance=0.5,
                bankroll_percentage=0.02,
                max_daily_bets=5,
                value_threshold=1.2,
            ),
            "aggressive_smart": BettingStrategy(
                name="智能激进策略",
                description="高级风险管理的高收益策略",
                max_kelly_fraction=0.35,
                min_ev_threshold=0.03,
                risk_tolerance=0.7,
                bankroll_percentage=0.03,
                max_daily_bets=8,
                value_threshold=1.1,
            ),
            "srs_premium": BettingStrategy(
                name="SRS高级策略",
                description="符合SRS要求的高级优化策略",
                max_kelly_fraction=0.20,
                min_ev_threshold=0.05,
                risk_tolerance=0.4,
                bankroll_percentage=0.015,
                max_daily_bets=4,
                value_threshold=1.25,
            ),
        }

    def calculate_enhanced_ev(
        self,
        bet_type: BetType,
        probability: float,
        odds: float,
        confidence: float = 1.0,
        strategy_name: str = "srs_premium",
        market_data: dict[str, Any] | None = None,
        historical_data: dict[str, Any] | None = None,
    ) -> EVCalculation:
        """
        计算增强EV
        """

        strategy = self.optimized_strategies.get(
            strategy_name, self.optimized_strategies["srs_premium"]
        )

        # 1. 基础EV计算
        ev = (probability * odds) - 1

        # 2. 增强Kelly计算
        kelly_result = self.kelly_calculator.calculate_fractional_kelly(
            probability, odds, confidence, 1000.0, historical_data
        )

        # 3. 增强价值评级
        value_rating_result = self.value_calculator.calculate_enhanced_value_rating(
            probability, odds, confidence, market_data, historical_data
        )

        # 4. 风险评估
        risk_level = self._assess_enhanced_risk(
            probability, odds, ev, kelly_result.risk_of_ruin
        )

        # 5. 生成建议
        recommendation = self._generate_enhanced_recommendation(
            ev, value_rating_result.overall_rating, kelly_result, risk_level, strategy
        )

        # 6. 计算其他指标
        expected_roi = ev * kelly_result.optimal_fraction * 100
        suggested_stake = kelly_result.optimal_fraction * strategy.bankroll_percentage

        return EVCalculation(
            bet_type=bet_type,
            probability=probability,
            odds=odds,
            ev=ev,
            kelly_fraction=kelly_result.optimal_fraction,
            risk_level=risk_level,
            recommendation=recommendation,
            confidence=confidence,
            value_rating=value_rating_result.overall_rating,
            expected_roi=expected_roi,
            bust_probability=kelly_result.risk_of_ruin,
            suggested_stake=suggested_stake,
        )

    def _assess_enhanced_risk(
        self, probability: float, odds: float, ev: float, risk_of_ruin: float
    ) -> RiskLevel:
        """评估增强风险等级"""
        if ev < 0 or risk_of_ruin > 0.3:
            return RiskLevel.VERY_HIGH
        elif risk_of_ruin > 0.15:
            return RiskLevel.HIGH
        elif probability >= 0.6 and ev >= 0.08 and risk_of_ruin < 0.05:
            return RiskLevel.LOW
        else:
            return RiskLevel.MEDIUM

    def _generate_enhanced_recommendation(
        self,
        ev: float,
        value_rating: float,
        kelly_result: KellyOptimizationResult,
        risk_level: RiskLevel,
        strategy: BettingStrategy,
    ) -> str:
        """生成增强投注建议"""

        # 基础过滤条件
        if ev < strategy.min_ev_threshold:
            return "avoid"

        if value_rating < 6.0:
            return "avoid"

        if risk_level.value > 2:  # 超过MEDIUM风险
            return "avoid"

        # 综合评估
        combined_score = (value_rating / 10) * 0.6 + (
            1 - kelly_result.risk_of_ruin
        ) * 0.4

        if combined_score >= 0.85 and kelly_result.expected_growth > 0.05:
            return "strong_bet"
        elif combined_score >= 0.75 and kelly_result.expected_growth > 0.02:
            return "bet"
        elif combined_score >= 0.65:
            return "small_bet"
        else:
            return "wait"

    async def backtest_strategy(
        self,
        strategy_name: str,
        historical_bets: list[dict[str, Any]],
        initial_bankroll: float = 1000.0,
    ) -> dict[str, Any]:
        """
        回测策略效果
        """

        strategy = self.optimized_strategies.get(strategy_name)
        if not strategy:
            raise ValueError(f"未知策略: {strategy_name}")

        # 回测结果
        results = {
            "strategy": strategy_name,
            "initial_bankroll": initial_bankroll,
            "final_bankroll": initial_bankroll,
            "total_bets": 0,
            "winning_bets": 0,
            "losing_bets": 0,
            "total_stake": 0.0,
            "total_return": 0.0,
            "roi": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0,
            "daily_returns": [],
            "bankroll_history": [initial_bankroll],
        }

        current_bankroll = initial_bankroll
        max_bankroll = initial_bankroll

        for bet_data in historical_bets:
            # 计算EV和建议
            ev_calc = self.calculate_enhanced_ev(
                bet_type=BetType(bet_data["bet_type"]),
                probability=bet_data["probability"],
                odds=bet_data["odds"],
                confidence=bet_data.get("confidence", 1.0),
                strategy_name=strategy_name,
                historical_data=bet_data.get("historical_data"),
            )

            # 检查是否投注
            if ev_calc.recommendation not in ["strong_bet", "bet", "small_bet"]:
                continue

            # 计算投注金额
            stake = min(
                ev_calc.suggested_stake * current_bankroll,
                current_bankroll * 0.05,  # 单次最大5%
            )

            if stake <= 0:
                continue

            # 执行投注
            results["total_bets"] += 1
            results["total_stake"] += stake

            # 模拟结果
            won = bet_data.get("outcome", False)
            if won:
                winnings = stake * ev_calc.odds
                current_bankroll = current_bankroll - stake + winnings
                results["winning_bets"] += 1
                results["total_return"] += winnings
            else:
                results["losing_bets"] += 1
                current_bankroll -= stake

            results["bankroll_history"].append(current_bankroll)

            # 更新最大回撤
            if current_bankroll > max_bankroll:
                max_bankroll = current_bankroll

            current_drawdown = (max_bankroll - current_bankroll) / max_bankroll
            results["max_drawdown"] = max(results["max_drawdown"], current_drawdown)

        # 计算最终指标
        results["final_bankroll"] = current_bankroll
        results["roi"] = (current_bankroll - initial_bankroll) / initial_bankroll * 100
        results["win_rate"] = (
            results["winning_bets"] / results["total_bets"]
            if results["total_bets"] > 0
            else 0
        )

        # 计算Sharpe比率
        if results["bankroll_history"]:
            returns = (
                np.diff(results["bankroll_history"]) / results["bankroll_history"][:-1]
            )
            if len(returns) > 1:
                results["sharpe_ratio"] = (
                    np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
                )

        return results


# 主要导出接口
__all__ = [
    "EnhancedEVCalculator",
    "EnhancedKellyCalculator",
    "EnhancedValueRatingCalculator",
    "KellyOptimizationResult",
    "EnhancedValueRating",
]
