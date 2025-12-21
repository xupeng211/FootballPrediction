#!/usr/bin/env python3
"""
凯利公式V1.0 - 金融风险控制模块
Kelly Criterion V1.0 - Financial Risk Control Module

基于Edge和赔率给出建议仓位，实现科学的资金管理
"""

import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class KellyRecommendation:
    """凯利公式建议结果"""

    recommended_stake_percent: float  # 建议仓位百分比
    edge: float  # 边缘优势
    implied_probability: float  # 隐含概率
    model_probability: float  # 模型概率
    odds: float  # 市场赔率
    stake_category: str  # 仓位分类
    risk_level: str  # 风险等级
    confidence: str  # 建议信心


class KellyCriterionV1:
    """凯利公式计算器 V1.0"""

    def __init__(self, max_stake_percent: float = 25.0, min_edge_percent: float = 5.0):
        """
        初始化凯利公式计算器

        Args:
            max_stake_percent: 最大建议仓位百分比 (默认25%)
            min_edge_percent: 最小边缘优势百分比 (默认5%)
        """
        self.max_stake_percent = max_stake_percent
        self.min_edge_percent = min_edge_percent

    def calculate_kelly_stake(
        self, model_probability: float, market_odds: float, outcome: str = "win"
    ) -> KellyRecommendation:
        """
        计算凯利公式建议仓位

        Args:
            model_probability: 模型预测概率 (0.0 - 1.0)
            market_odds: 市场赔率 (小数形式)
            outcome: 结果类型 ("win", "draw", "lose")

        Returns:
            KellyRecommendation: 凯利公式建议结果
        """

        # 计算市场隐含概率
        implied_probability = 1.0 / market_odds

        # 计算边缘优势 (Edge = 模型概率 - 隐含概率)
        edge = model_probability - implied_probability
        edge_percent = edge * 100

        # 计算凯利公式仓位: Stake = (Edge / Odds)
        if market_odds > 0 and edge > 0:
            # 简化凯利公式: Stake = (p - q/b) / 1
            # 其中 p = 胜率, q = 败率, b = 赔率-1
            # 简化为: Stake = (Edge / Odds)
            kelly_fraction = edge / market_odds

            # 转换为百分比
            recommended_stake_percent = kelly_fraction * 100

            # 限制最大仓位
            recommended_stake_percent = min(recommended_stake_percent, self.max_stake_percent)

        else:
            recommended_stake_percent = 0.0

        # 分类风险等级和仓位建议
        stake_category, risk_level, confidence = self._classify_recommendation(recommended_stake_percent, edge_percent)

        logger.info(
            f"🎰 [KELLY] 凯利公式计算: "
            f"模型概率={model_probability:.3f}, "
            f"市场赔率={market_odds:.2f}, "
            f"隐含概率={implied_probability:.3f}, "
            f"边缘优势={edge_percent:.1f}%, "
            f"建议仓位={recommended_stake_percent:.1f}%"
        )

        return KellyRecommendation(
            recommended_stake_percent=recommended_stake_percent,
            edge=edge_percent,
            implied_probability=implied_probability,
            model_probability=model_probability,
            odds=market_odds,
            stake_category=stake_category,
            risk_level=risk_level,
            confidence=confidence,
        )

    def _classify_recommendation(self, stake_percent: float, edge_percent: float) -> Tuple[str, str, str]:
        """分类建议的仓位、风险等级和信心度"""

        # 仓位分类
        if stake_percent >= 15:
            stake_category = "超大注"
        elif stake_percent >= 10:
            stake_category = "大注"
        elif stake_percent >= 5:
            stake_category = "中注"
        elif stake_percent >= 2:
            stake_category = "小注"
        elif stake_percent >= 0.5:
            stake_category = "微注"
        else:
            stake_category = "不建议投注"

        # 风险等级
        if stake_percent >= 20:
            risk_level = "极高风险"
        elif stake_percent >= 15:
            risk_level = "高风险"
        elif stake_percent >= 10:
            risk_level = "中高风险"
        elif stake_percent >= 5:
            risk_level = "中等风险"
        elif stake_percent >= 2:
            risk_level = "中低风险"
        else:
            risk_level = "低风险"

        # 信心度
        if edge_percent >= 20:
            confidence = "极高信心"
        elif edge_percent >= 15:
            confidence = "高信心"
        elif edge_percent >= 10:
            confidence = "中等信心"
        elif edge_percent >= 5:
            confidence = "谨慎信心"
        else:
            confidence = "缺乏信心"

        return stake_category, risk_level, confidence

    def calculate_multi_outcome_kelly(
        self, probabilities: Dict[str, float], odds: Dict[str, float]
    ) -> Dict[str, KellyRecommendation]:
        """
        计算多结果凯利公式建议 (如胜平负)

        Args:
            probabilities: 各结果概率 {"home": 0.6, "draw": 0.25, "away": 0.15}
            odds: 各结果赔率 {"home": 1.8, "draw": 3.2, "away": 5.5}

        Returns:
            Dict[str, KellyRecommendation]: 各结果的凯利建议
        """

        recommendations = {}

        for outcome, prob in probabilities.items():
            if outcome in odds:
                rec = self.calculate_kelly_stake(prob, odds[outcome], outcome)
                recommendations[outcome] = rec

        return recommendations

    def validate_kelly_assumptions(self, recommendations: Dict[str, KellyRecommendation]) -> bool:
        """
        验证凯利公式假设的合理性

        Args:
            recommendations: 各结果的凯利建议

        Returns:
            bool: 是否通过验证
        """

        # 检查总仓位是否合理 (凯利公式假设总仓位不应超过25%)
        total_stake = sum(rec.recommended_stake_percent for rec in recommendations.values())

        if total_stake > self.max_stake_percent:
            logger.warning(f"⚠️ [KELLY] 总仓位过高: {total_stake:.1f}% > {self.max_stake_percent}%")
            return False

        # 检查是否有正边缘优势
        positive_edge_count = sum(1 for rec in recommendations.values() if rec.edge > self.min_edge_percent)

        if positive_edge_count == 0:
            logger.warning(f"⚠️ [KELLY] 没有发现足够的边缘优势 (< {self.min_edge_percent}%)")
            return False

        return True


def format_kelly_output(recommendation: KellyRecommendation, outcome: str = "") -> str:
    """格式化凯利公式输出为日志格式"""

    output = []
    output.append("💰 [KELLY] 金融风险控制建议:")
    output.append(f"   📊 结果: {outcome}")
    output.append(f"   🎯 模型概率: {recommendation.model_probability:.1%}")
    output.append(f"   💹 市场赔率: {recommendation.odds:.2f}")
    output.append(f"   🔍 隐含概率: {recommendation.implied_probability:.1%}")
    output.append(f"   ⚡ 边缘优势: {recommendation.edge:.1f}%")
    output.append(f"   💎 建议仓位: {recommendation.recommended_stake_percent:.1f}%")
    output.append(f"   📈 仓位分类: {recommendation.stake_category}")
    output.append(f"   ⚠️ 风险等级: {recommendation.risk_level}")
    output.append(f"   🏆 建议信心: {recommendation.confidence}")

    return "\n".join(output)


# 全局凯利公式实例
kelly_calculator = KellyCriterionV1()


def calculate_kelly_for_prediction(
    home_prob: float, draw_prob: float, away_prob: float, home_odds: float, draw_odds: float, away_odds: float
) -> Dict[str, KellyRecommendation]:
    """
    为足球预测计算凯利公式建议

    Args:
        home_prob, draw_prob, away_prob: 胜平负概率
        home_odds, draw_odds, away_odds: 胜平负赔率

    Returns:
        Dict[str, KellyRecommendation]: 各结果的凯利建议
    """

    probabilities = {"home": home_prob, "draw": draw_prob, "away": away_prob}
    odds = {"home": home_odds, "draw": draw_odds, "away": away_odds}

    return kelly_calculator.calculate_multi_outcome_kelly(probabilities, odds)
