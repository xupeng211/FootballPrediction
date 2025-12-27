#!/usr/bin/env python3
"""
半凯利公式策略 - Fractional Kelly Criterion V2.0
Financial Logic Recovery - 降低风险，提高生存率

主要改进：
1. 使用半凯利 (0.5x) 策略降低波动
2. Edge < 5% 或 胜率 < 40% 禁止投注
3. 风险等级重新评估
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FractionalKellyRecommendation:
    """半凯利公式建议结果"""

    recommended_stake_percent: float  # 建议仓位百分比（已经是半凯利）
    edge: float  # 边缘优势
    implied_probability: float  # 隐含概率
    model_probability: float  # 模型概率
    odds: float  # 市场赔率
    risk_level: str  # 风险等级
    confidence: str  # 建议信心
    is_valid_bet: bool  # 是否有效投注
    reason: str  # 拒绝原因（如果无效）


class FractionalKellyCriterion:
    """半凯利公式计算器 V2.0"""

    def __init__(
        self,
        kelly_fraction: float = 0.5,  # 半凯利系数
        min_edge_percent: float = 7.0,  # 提高最小边缘优势: 5% -> 7%
        min_win_probability: float = 0.45,  # 提高最小胜率要求: 40% -> 45%
        max_stake_percent: float = 10.0,
    ):  # 降低最大仓位: 12.5% -> 10%
        """
        初始化半凯利公式计算器

        Args:
            kelly_fraction: 凯利系数 (默认0.5 = 半凯利)
            min_edge_percent: 最小边缘优势百分比 (默认5%)
            min_win_probability: 最小胜率要求 (默认40%)
            max_stake_percent: 最大建议仓位百分比
        """
        self.kelly_fraction = kelly_fraction
        self.min_edge_percent = min_edge_percent
        self.min_win_probability = min_win_probability
        self.max_stake_percent = max_stake_percent

        logger.info(f"🎰 半凯利公式初始化: {kelly_fraction}x系数, 最小边缘优势: {min_edge_percent}%")

    def calculate_fractional_kelly_stake(
        self, model_probability: float, market_odds: float, outcome: str = "win"
    ) -> FractionalKellyRecommendation:
        """
        计算半凯利公式建议仓位

        Args:
            model_probability: 模型预测概率 (0.0 - 1.0)
            market_odds: 市场赔率 (小数形式)
            outcome: 结果类型 ("win", "draw", "lose")

        Returns:
            FractionalKellyRecommendation: 半凯利公式建议结果
        """

        # 计算市场隐含概率
        implied_probability = 1.0 / market_odds

        # 计算边缘优势 (Edge = 模型概率 - 隐含概率)
        edge = model_probability - implied_probability
        edge_percent = edge * 100

        # 检查投注有效性
        is_valid_bet, reason = self._validate_bet_conditions(model_probability, market_odds, edge_percent)

        if not is_valid_bet:
            return FractionalKellyRecommendation(
                recommended_stake_percent=0.0,
                edge=edge_percent,
                implied_probability=implied_probability,
                model_probability=model_probability,
                odds=market_odds,
                risk_level="禁止投注",
                confidence="拒绝",
                is_valid_bet=False,
                reason=reason,
            )

        # 计算原始凯利公式仓位
        if market_odds > 0 and edge > 0:
            # 原始凯利公式: Stake = (Edge / Odds) * KellyFraction
            original_kelly_fraction = edge / market_odds
            recommended_stake_percent = original_kelly_fraction * self.kelly_fraction * 100

            # 限制最大仓位
            recommended_stake_percent = min(recommended_stake_percent, self.max_stake_percent)
        else:
            recommended_stake_percent = 0.0

        # 分类风险等级和信心度
        risk_level, confidence = self._classify_risk_and_confidence(
            recommended_stake_percent, edge_percent, model_probability
        )

        logger.info(
            f"🎰 [FRACTIONAL_KELLY] 半凯利计算: "
            f"模型概率={model_probability:.3f}, "
            f"市场赔率={market_odds:.2f}, "
            f"隐含概率={implied_probability:.3f}, "
            f"边缘优势={edge_percent:.1f}%, "
            f"建议仓位={recommended_stake_percent:.1f}%, "
            f"投注状态={'有效' if is_valid_bet else '无效'}"
        )

        return FractionalKellyRecommendation(
            recommended_stake_percent=recommended_stake_percent,
            edge=edge_percent,
            implied_probability=implied_probability,
            model_probability=model_probability,
            odds=market_odds,
            risk_level=risk_level,
            confidence=confidence,
            is_valid_bet=is_valid_bet,
            reason=reason if not is_valid_bet else "",
        )

    def _validate_bet_conditions(
        self, model_probability: float, market_odds: float, edge_percent: float
    ) -> tuple[bool, str]:
        """
        验证投注条件

        Returns:
            Tuple[bool, str]: (是否有效, 拒绝原因)
        """

        # 检查最小边缘优势
        if edge_percent < self.min_edge_percent:
            return False, f"边缘优势不足 ({edge_percent:.1f}% < {self.min_edge_percent}%)"

        # 检查最小胜率要求
        if model_probability < self.min_win_probability:
            return False, f"胜率过低 ({model_probability:.1%} < {self.min_win_probability:.0%})"

        # 检查赔率合理性
        if market_odds <= 1.0:
            return False, f"赔率无效 ({market_odds:.2f} <= 1.0)"

        # 检查模型概率合理性
        if model_probability > 0.95:
            return False, f"模型概率过高 ({model_probability:.1%} > 95%)"

        # 检查边缘优势是否过大（可能是市场定价错误）
        if edge_percent > 30.0:
            return False, f"边缘优势过大 ({edge_percent:.1f}% > 30%)，建议人工审核"

        return True, ""

    def _classify_risk_and_confidence(
        self, stake_percent: float, edge_percent: float, model_probability: float
    ) -> tuple[str, str]:
        """
        分类风险等级和信心度

        Returns:
            Tuple[str, str]: (风险等级, 信心度)
        """

        # 风险等级分类
        if stake_percent >= 10:
            risk_level = "高风险"
        elif stake_percent >= 5:
            risk_level = "中风险"
        elif stake_percent >= 2:
            risk_level = "中低风险"
        elif stake_percent >= 0.5:
            risk_level = "低风险"
        else:
            risk_level = "极低风险"

        # 信心度分类 - 基于多个因素
        confidence_score = 0
        if edge_percent >= 15:
            confidence_score += 2
        elif edge_percent >= 10:
            confidence_score += 1

        if model_probability >= 0.6:
            confidence_score += 1

        if stake_percent >= 5 and stake_percent <= 8:
            confidence_score += 1

        if confidence_score >= 3:
            confidence = "高信心"
        elif confidence_score >= 2:
            confidence = "中等信心"
        elif confidence_score >= 1:
            confidence = "谨慎信心"
        else:
            confidence = "低信心"

        return risk_level, confidence

    def calculate_multi_outcome_fractional_kelly(
        self, probabilities: dict[str, float], odds: dict[str, float]
    ) -> dict[str, FractionalKellyRecommendation]:
        """
        计算多结果半凯利公式建议

        Args:
            probabilities: 各结果概率 {"home": 0.6, "draw": 0.25, "away": 0.15}
            odds: 各结果赔率 {"home": 1.8, "draw": 3.2, "away": 5.5}

        Returns:
            Dict[str, FractionalKellyRecommendation]: 各结果的半凯利建议
        """

        recommendations = {}

        for outcome, prob in probabilities.items():
            if outcome in odds:
                rec = self.calculate_fractional_kelly_stake(prob, odds[outcome], outcome)
                recommendations[outcome] = rec

        return recommendations

    def validate_total_position_risk(self, recommendations: dict[str, FractionalKellyRecommendation]) -> bool:
        """
        验证总仓位风险

        Args:
            recommendations: 各结果的半凯利建议

        Returns:
            bool: 是否通过风险验证
        """

        # 只计算有效投注的总仓位
        total_stake = sum(
            rec.recommended_stake_percent
            for rec in recommendations.values()
            if rec.is_valid_bet and rec.recommended_stake_percent > 0
        )

        # 半凯利后的最大仓位应该是25%的一半，即12.5%
        max_total_stake = self.max_stake_percent

        if total_stake > max_total_stake:
            logger.warning(f"⚠️ [FRACTIONAL_KELLY] 总仓位过高: {total_stake:.1f}% > {max_total_stake}%")
            return False

        # 检查是否有足够的有效投注
        valid_bets = sum(1 for rec in recommendations.values() if rec.is_valid_bet)
        if valid_bets == 0:
            logger.warning("⚠️ [FRACTIONAL_KELLY] 没有有效的投注建议")
            return False

        logger.info(f"✅ [FRACTIONAL_KELLY] 总仓位风险通过: {total_stake:.1f}%")
        return True


def format_fractional_kelly_output(recommendation: FractionalKellyRecommendation, outcome: str = "") -> str:
    """格式化半凯利公式输出为日志格式"""

    status_emoji = "✅" if recommendation.is_valid_bet else "❌"

    output = []
    output.append(f"{status_emoji} [FRACTIONAL_KELLY] 半凯利风险管理建议:")
    output.append(f"   📊 结果: {outcome}")
    output.append(f"   🎯 模型概率: {recommendation.model_probability:.1%}")
    output.append(f"   💹 市场赔率: {recommendation.odds:.2f}")
    output.append(f"   🔍 隐含概率: {recommendation.implied_probability:.1%}")
    output.append(f"   ⚡ 边缘优势: {recommendation.edge:.1f}%")
    output.append(f"   💎 建议仓位: {recommendation.recommended_stake_percent:.1f}%")
    output.append(f"   📈 风险等级: {recommendation.risk_level}")
    output.append(f"   ⚠️ 投注状态: {'有效' if recommendation.is_valid_bet else '无效'}")

    if not recommendation.is_valid_bet:
        output.append(f"   🚫 拒绝原因: {recommendation.reason}")

    output.append(f"   🏆 信心等级: {recommendation.confidence}")

    return "\n".join(output)


# 全局半凯利公式实例
fractional_kelly_calculator = FractionalKellyCriterion()


def calculate_fractional_kelly_for_prediction(
    home_prob: float, draw_prob: float, away_prob: float, home_odds: float, draw_odds: float, away_odds: float
) -> dict[str, FractionalKellyRecommendation]:
    """
    为足球预测计算半凯利公式建议

    Args:
        home_prob, draw_prob, away_prob: 胜平负概率
        home_odds, draw_odds, away_odds: 胜平负赔率

    Returns:
        Dict[str, FractionalKellyRecommendation]: 各结果的半凯利建议
    """

    probabilities = {"home": home_prob, "draw": draw_prob, "away": away_prob}
    odds = {"home": home_odds, "draw": draw_odds, "away": away_odds}

    return fractional_kelly_calculator.calculate_multi_outcome_fractional_kelly(probabilities, odds)
