#!/usr/bin/env python3
"""
足球业务逻辑常量定义

金融级计算精度和业务规则常量集合，为足球预测系统提供统一的、
可维护的业务逻辑参数。所有硬编码数值都应该迁移到这里。

设计原则：
1. 金融级精度：使用 Decimal 类型进行高精度计算
2. 业务合理性：所有数值都基于足球行业标准和统计研究
3. 可维护性：每个常量都有详细的业务说明和来源
4. 可测试性：常量可以被独立测试和验证

Author: Advanced ML Engineer
Version: 1.0.0
Last Updated: 2025-12-18
"""

import sys
import logging
from decimal import Decimal, getcontext, Context, ROUND_HALF_UP, ROUND_HALF_EVEN
from typing import Dict, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# =============================================================================
# 金融级精度配置
# =============================================================================

# 设置 Decimal 高精度计算环境
# 金融计算通常要求小数点后4-6位精度
DECIMAL_PRECISION = 10
getcontext().prec = DECIMAL_PRECISION
getcontext().rounding = ROUND_HALF_UP  # 金融标准舍入方式


# 精度上下文，用于不同的计算场景
class PrecisionContext:
    """精度上下文管理器"""

    @staticmethod
    def high_precision():
        """高精度上下文 (10位小数) - 用于赔率计算"""
        ctx = Context()
        ctx.prec = 15
        ctx.rounding = ROUND_HALF_UP
        return ctx

    @staticmethod
    def medium_precision():
        """中精度上下文 (6位小数) - 用于概率计算"""
        ctx = Context()
        ctx.prec = 8
        ctx.rounding = ROUND_HALF_UP
        return ctx

    @staticmethod
    def low_precision():
        """低精度上下文 (4位小数) - 用于显示和输出"""
        ctx = Context()
        ctx.prec = 6
        ctx.rounding = ROUND_HALF_UP
        return ctx


# =============================================================================
# 足球业务基础常量
# =============================================================================


class FootballConstants:
    """足球业务基础常量"""

    # 比赛结果定义
    HOME_WIN = 2  # 主队胜利
    DRAW = 1  # 平局
    AWAY_WIN = 0  # 客队胜利

    RESULT_LABELS = {HOME_WIN: "HOME_WIN", DRAW: "DRAW", AWAY_WIN: "AWAY_WIN"}

    REVERSE_RESULT_LABELS = {v: k for k, v in RESULT_LABELS.items()}

    # 标准比赛时长
    REGULATION_TIME_MINUTES = 90  # 正规比赛时间(分钟)
    STANDARD_DURATION = Decimal("90")  # 标准时长

    # 球队人数
    PLAYERS_PER_TEAM = 11
    TOTAL_PLAYERS = 22


class ScoringConstants:
    """进球相关的业务常量"""

    # 历史交锋默认值 (基于全球足球统计数据)
    DEFAULT_H2H_WIN_RATE = Decimal("0.5")  # 默认50%胜率 (无历史数据时)
    DEFAULT_H2H_DRAW_RATE = Decimal("0.25")  # 默认25%平局率
    DEFAULT_H2H_LOSS_RATE = Decimal("0.25")  # 默认25%败率
    DEFAULT_AVG_GOAL_DIFF = Decimal("0.0")  # 默认0进球差
    DEFAULT_AVG_TOTAL_GOALS = Decimal("2.5")  # 默认平均2.5球 (英超历史均值)

    # 基于各大联赛统计数据的合理范围
    MIN_REASONABLE_TOTAL_GOALS = Decimal("0.5")  # 最低合理总进球
    MAX_REASONABLE_TOTAL_GOALS = Decimal("8.0")  # 最高合理总进球
    MIN_REASONABLE_GOAL_DIFF = Decimal("-5.0")  # 最大合理负进球差
    MAX_REASONABLE_GOAL_DIFF = Decimal("5.0")  # 最大合理正进球差

    # 平滑处理常量 (防止除零错误)
    SMOOTHING_EPSILON = Decimal("0.01")  # 极小值，用于数学平滑
    MIN_DIVISOR = Decimal("0.001")  # 最小除数，防止数值不稳定

    # 进球率转换常数
    GOALS_PER_90_MINUTES = Decimal("1.0")  # 每90分钟的进球基准

    # 场馆优势相关常数 (基于全球足球主场优势统计)
    HOME_ADVANTAGE_MULTIPLIER = Decimal("1.15")  # 主场优势倍数
    NEUTRAL_VENUE_MULTIPLIER = Decimal("1.0")  # 中立场地倍数


class OddsConstants:
    """赔率计算相关常量"""

    # 赔率到概率转换的基础
    DECIMAL_ODDS_BASE = Decimal("1.0")  # 十进制赔率基值
    IMPLIED_PROBABILITY_BUFFER = Decimal("0.001")  # 隐含概率缓冲

    # 博彩公司利润率 (vigorish)
    BOOKMAKER_MARGIN_MIN = Decimal("0.02")  # 最低利润率 2%
    BOOKMAKER_MARGIN_TYPICAL = Decimal("0.05")  # 典型利润率 5%
    BOOKMAKER_MARGIN_MAX = Decimal("0.10")  # 最高利润率 10%

    # 极端赔率值限制 (防止计算溢出)
    MIN_DECIMAL_ODDS = Decimal("1.01")  # 最低十进制赔率 (极高概率)
    MAX_DECIMAL_ODDS = Decimal("1000.0")  # 最高十进制赔率 (极低概率)

    # 赔率转换精度
    ODDS_CONVERSION_PRECISION = Decimal("0.0001")  # 赔率转换精度

    # 凯利指数相关
    KELLY_CRITICAL_VALUE = Decimal("0.25")  # 凯利指数临界值
    MAX_KELLY_FRACTION = Decimal("0.25")  # 最大凯利分数


class ProbabilityConstants:
    """概率计算相关常量"""

    # 概率范围
    MIN_PROBABILITY = Decimal("0.0")  # 最小概率
    MAX_PROBABILITY = Decimal("1.0")  # 最大概率
    PROBABILITY_EPSILON = Decimal("0.0001")  # 概率精度

    # 概率分布阈值
    HIGH_PROBABILITY_THRESHOLD = Decimal("0.7")  # 高概率阈值 (>70%)
    LOW_PROBABILITY_THRESHOLD = Decimal("0.3")  # 低概率阈值 (<30%)

    # 概率平滑常数
    PROBABILITY_SMOOTHING_FACTOR = Decimal("0.01")  # 概率平滑因子

    # 置信区间常数 (基于正态分布)
    CONFIDENCE_95 = Decimal("1.96")  # 95%置信区间系数
    CONFIDENCE_99 = Decimal("2.58")  # 99%置信区间系数


class StatisticalConstants:
    """统计计算相关常量"""

    # 样本量要求
    MIN_H2H_SAMPLE_SIZE = 3  # 最小历史交锋样本量
    RECOMMENDED_H2H_SAMPLE_SIZE = 10  # 推荐历史交锋样本量
    MAX_RELIABLE_SAMPLE_SIZE = 100  # 最大可靠样本量

    # 滚动统计窗口
    SHORT_TERM_WINDOW = 3  # 短期窗口 (3场比赛)
    MEDIUM_TERM_WINDOW = 5  # 中期窗口 (5场比赛)
    LONG_TERM_WINDOW = 10  # 长期窗口 (10场比赛)

    # 趋势权重
    RECENT_WEIGHT_FACTOR = Decimal("0.6")  # 近期权重因子
    HISTORICAL_WEIGHT_FACTOR = Decimal("0.4")  # 历史权重因子

    # 相关性阈值
    CORRELATION_THRESHOLD_STRONG = Decimal("0.7")  # 强相关性阈值
    CORRELATION_THRESHOLD_MODERATE = Decimal("0.4")  # 中等相关性阈值
    CORRELATION_THRESHOLD_WEAK = Decimal("0.2")  # 弱相关性阈值


class ValidationConstants:
    """数据验证相关常量"""

    # 特征值范围检查
    MAX_FEATURE_VALUE = Decimal("1000.0")  # 最大特征值
    MIN_FEATURE_VALUE = Decimal("-1000.0")  # 最小特征值

    # 数值稳定性检查
    STABILITY_THRESHOLD = Decimal("1e10")  # 数值稳定性阈值
    OVERFLOW_THRESHOLD = Decimal("1e50")  # 溢出阈值

    # 比赛数据验证
    MAX_GOALS_PER_TEAM = Decimal("15")  # 单队最大进球数
    MAX_TOTAL_GOALS = Decimal("30")  # 最大总进球数

    # 赔率合理性检查
    MIN_REASONABLE_PROB = Decimal("0.001")  # 最小合理概率
    MAX_REASONABLE_PROB = Decimal("0.999")  # 最大合理概率


@dataclass
class CalculationThresholds:
    """计算阈值配置"""

    # 极端值检测阈值
    extreme_probability_threshold: float = 0.99  # 极端概率阈值
    extreme_odds_threshold: float = 1000.0  # 极端赔率阈值

    # 数值稳定性阈值
    precision_threshold: float = 1e-10  # 精度阈值
    stability_threshold: float = 1e6  # 稳定性阈值

    # 业务逻辑阈值
    max_confidence_score: float = 0.95  # 最大置信度
    min_prediction_confidence: float = 0.1  # 最小预测置信度


# =============================================================================
# 数学工具函数
# =============================================================================


class FinancialMath:
    """金融级数学计算工具"""

    @staticmethod
    def safe_divide(dividend: Decimal, divisor: Decimal, default: Decimal = None) -> Decimal:
        """
        安全除法运算，防止除零错误

        Args:
            dividend: 被除数
            divisor: 除数
            default: 默认值 (当除数为0时使用)

        Returns:
            Decimal: 除法结果

        数学依据:
        当除数接近零时，使用极小值进行平滑处理，这是金融计算中的标准做法。
        0.01 是经验值，既能防止除零错误，又不会对结果产生显著影响。
        """
        if divisor == 0 or abs(divisor) < ScoringConstants.MIN_DIVISOR:
            logger.warning(f"除数过小: {divisor}, 使用默认值 {default}")
            return default if default is not None else Decimal("0")

        try:
            result = dividend / divisor
            return result
        except Exception as e:
            logger.error(f"除法计算错误: {e}")
            return default if default is not None else Decimal("0")

    @staticmethod
    def odds_to_probability(odds: Decimal) -> Decimal:
        """
        十进制赔率转换为隐含概率

        Args:
            odds: 十进制赔率 (如 2.0)

        Returns:
            Decimal: 隐含概率 (0-1之间)

        数学依据:
        概率 = 1 / 赔率
        这是博彩业的标准计算公式，反映了市场对事件发生可能性的预期。
        """
        if odds <= 0:
            raise ValueError("赔率必须大于0")

        if odds < OddsConstants.MIN_DECIMAL_ODDS:
            odds = OddsConstants.MIN_DECIMAL_ODDS
            logger.warning(f"赔率过小，调整为: {odds}")

        try:
            probability = Decimal("1") / odds
            return probability
        except Exception as e:
            logger.error(f"赔率转换错误: {e}")
            return ProbabilityConstants.MIN_PROBABILITY

    @staticmethod
    def probability_to_odds(probability: Decimal) -> Decimal:
        """
        概率转换为十进制赔率

        Args:
            probability: 概率值 (0-1之间)

        Returns:
            Decimal: 十进制赔率

        数学依据:
        赔率 = 1 / 概率
        需要确保概率在有效范围内，避免除零错误。
        """
        if probability <= 0:
            return OddsConstants.MAX_DECIMAL_ODDS
        if probability >= 1:
            return OddsConstants.MIN_DECIMAL_ODDS

        try:
            odds = Decimal("1") / probability
            return odds
        except Exception as e:
            logger.error(f"概率转换错误: {e}")
            return OddsConstants.MAX_DECIMAL_ODDS

    @staticmethod
    def normalize_probabilities(probabilities: list[Decimal]) -> list[Decimal]:
        """
        概率归一化处理，确保总概率为1

        Args:
            probabilities: 原始概率列表

        Returns:
            list[Decimal]: 归一化后的概率列表

        数学依据:
        归一化公式: p_i_normalized = p_i / Σ(p_j)
        这确保了概率分布的有效性，是概率论的基本要求。
        """
        if not probabilities:
            return [Decimal("0"), Decimal("0"), Decimal("0")]

        total = sum(probabilities)

        if total == 0:
            # 如果总概率为0，返回均匀分布
            uniform_prob = Decimal("1") / Decimal(len(probabilities))
            return [uniform_prob] * len(probabilities)

        # 使用金融精度进行归一化
        normalized = []
        with PrecisionContext.medium_precision():
            for prob in probabilities:
                normalized_prob = prob / total
                normalized.append(normalized_prob)

        # 确保归一化后的概率总和为1 (允许小的舍入误差)
        total_normalized = sum(normalized)
        if abs(total_normalized - Decimal("1")) > ProbabilityConstants.PROBABILITY_EPSILON:
            logger.warning(f"归一化后总概率不为1: {total_normalized}")

        return normalized


# =============================================================================
# 业务规则验证器
# =============================================================================


class BusinessRuleValidator:
    """业务规则验证器"""

    @staticmethod
    def validate_probability_distribution(probabilities: list[Decimal]) -> bool:
        """
        验证概率分布的有效性

        Args:
            probabilities: 概率列表

        Returns:
            bool: 是否有效

        验证规则:
        1. 概率值必须在 [0, 1] 范围内
        2. 概率总和必须接近 1 (允许小的舍入误差)
        3. 不应该有极端值 (如 0.9999)
        """
        # 检查范围
        for prob in probabilities:
            if prob < ProbabilityConstants.MIN_PROBABILITY or prob > ProbabilityConstants.MAX_PROBABILITY:
                logger.error(f"概率超出范围: {prob}")
                return False

        # 检查总和
        total = sum(probabilities)
        if abs(total - Decimal("1")) > ProbabilityConstants.PROBABILITY_EPSILON * 10:
            logger.error(f"概率总和不为1: {total}")
            return False

        # 检查极端值
        for prob in probabilities:
            if prob > Decimal("0.999"):
                logger.warning(f"检测到极端概率值: {prob}")

        return True

    @staticmethod
    def validate_odds_value(odds: Decimal) -> bool:
        """
        验证赔率值的合理性

        Args:
            odds: 十进制赔率

        Returns:
            bool: 是否合理

        验证规则:
        1. 赔率必须为正数
        2. 赔率必须在合理范围内 (1.01 - 1000)
        """
        if odds <= 0:
            logger.error(f"赔率不能为负数: {odds}")
            return False

        if odds < OddsConstants.MIN_DECIMAL_ODDS or odds > OddsConstants.MAX_DECIMAL_ODDS:
            logger.warning(f"赔率超出合理范围: {odds}")
            return False

        return True


# =============================================================================
# 导出接口
# =============================================================================

# 主要常量类实例
FOOTBALL = FootballConstants()
SCORING = ScoringConstants()
ODDS = OddsConstants()
PROBABILITY = ProbabilityConstants()
STATISTICAL = StatisticalConstants()
VALIDATION = ValidationConstants()

# 工具类实例
MATH = FinancialMath()
VALIDATOR = BusinessRuleValidator()

# 常用常量组合
DEFAULT_H2H_STATS = {
    "home_win_rate": SCORING.DEFAULT_H2H_WIN_RATE,
    "avg_goal_diff": SCORING.DEFAULT_AVG_GOAL_DIFF,
    "avg_total_goals": SCORING.DEFAULT_AVG_TOTAL_GOALS,
    "matches_count": 0,
}

# 模块信息
__version__ = "1.0.0"
__author__ = "Advanced ML Engineer"
__description__ = "足球业务逻辑常量定义 - 金融级精度计算"

# 导出的公共接口
__all__ = [
    # 主要常量类
    "FootballConstants",
    "ScoringConstants",
    "OddsConstants",
    "ProbabilityConstants",
    "StatisticalConstants",
    "ValidationConstants",
    # 工具类
    "FinancialMath",
    "BusinessRuleValidator",
    "PrecisionContext",
    # 实例
    "FOOTBALL",
    "SCORING",
    "ODDS",
    "PROBABILITY",
    "STATISTICAL",
    "VALIDATION",
    "MATH",
    "VALIDATOR",
    # 配置
    "DEFAULT_H2H_STATS",
    "DECIMAL_PRECISION",
    "CalculationThresholds",
]
