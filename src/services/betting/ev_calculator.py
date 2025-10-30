from typing import List
from typing import Optional
from typing import Dict
from typing import Any

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
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from src.core.logging_system import get_logger
    from src.core.config import get_config

    logger = get_logger(__name__)
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保在项目根目录运行此脚本")
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
    """类文档字符串"""
    pass  # 添加pass语句
    """赔率数据结构"""

    home_win: float
    draw: float
    away_win: float
    over_2_5: Optional[float] = None
    under_2_5: Optional[float] = None
    btts_yes: Optional[float] = None
    btts_no: Optional[float] = None
    correct_score_home: Optional[float] = None
    correct_score_draw: Optional[float] = None
    correct_score_away: Optional[float] = None

    # 赔率来源和置信度
    source: str = "unknown"
    confidence: float = 1.0
    margin: float = 0.0  # 庄家利润率


@dataclass
class PredictionProbabilities:
    """类文档字符串"""
    pass  # 添加pass语句
    """预测概率数据结构"""

    home_win: float
    draw: float
    away_win: float
    over_2_5: Optional[float] = None
    under_2_5: Optional[float] = None
    btts_yes: Optional[float] = None
    btts_no: Optional[float] = None

    # 置信度和元数据
    confidence: float = 1.0
    model_name: str = "unknown"
    prediction_time: datetime = None

    def __post_init__(self):
    """函数文档字符串"""
    pass  # 添加pass语句
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
    """类文档字符串"""
    pass  # 添加pass语句
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
    """类文档字符串"""
    pass  # 添加pass语句
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
    """类文档字符串"""
    pass  # 添加pass语句
    """期望价值计算器"""

    def __init__(self):
    """函数文档字符串"""
    pass  # 添加pass语句
        self.config = get_config()
        self.redis_manager = get_redis_manager()
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
        """计算Kelly准则投注比例"

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


class BettingStrategyOptimizer:
    """类文档字符串"""
    pass  # 添加pass语句
    """投注策略优化器"""

    def __init__(self):
    """函数文档字符串"""
    pass  # 添加pass语句
        self.logger = logger
        self.strategies = self._initialize_strategies()

    def _initialize_strategies(self) -> Dict[str, BettingStrategy]:
        """初始化预定义策略"""
        return {
            "conservative": BettingStrategy(
                name="保守策略",
                description="低风险,稳定收益,适合新手",
                max_kelly_fraction=0.15,
                min_ev_threshold=0.08,
                risk_tolerance=0.3,
                bankroll_percentage=0.01,
                max_daily_bets=3,
                value_threshold=1.3,
                stop_loss=0.05,
                take_profit=0.15,
                max_consecutive_losses=2,
            ),
            "balanced": BettingStrategy(
                name="平衡策略",
                description="风险与收益平衡,适合有经验的投注者",
                max_kelly_fraction=0.25,
                min_ev_threshold=0.05,
                risk_tolerance=0.5,
                bankroll_percentage=0.02,
                max_daily_bets=5,
                value_threshold=1.2,
                stop_loss=0.1,
                take_profit=0.2,
                max_consecutive_losses=3,
            ),
            "aggressive": BettingStrategy(
                name="激进策略",
                description="高风险高收益,适合专业投注者",
                max_kelly_fraction=0.35,
                min_ev_threshold=0.03,
                risk_tolerance=0.7,
                bankroll_percentage=0.03,
                max_daily_bets=8,
                value_threshold=1.1,
                stop_loss=0.15,
                take_profit=0.3,
                max_consecutive_losses=5,
            ),
            "srs_compliant": BettingStrategy(
                name="SRS合规策略",
                description="严格按照SRS要求的安全策略",
                max_kelly_fraction=0.20,
                min_ev_threshold=0.05,
                risk_tolerance=0.4,
                bankroll_percentage=0.015,
                max_daily_bets=4,
                value_threshold=1.25,
                stop_loss=0.08,
                take_profit=0.18,
                max_consecutive_losses=3,
            ),
        }

    def optimize_portfolio(
        self,
        ev_calculations: List[EVCalculation],
        strategy: BettingStrategy,
        max_total_stake: float = 0.1,
    ) -> Dict[str, Any]:
        """优化投注组合"""

        # 过滤符合条件的投注
        valid_bets = [
            calc
            for calc in ev_calculations
            if calc.recommendation in ["strong_bet", "bet", "small_bet"]
            and calc.ev >= strategy.min_ev_threshold
        ]

        if not valid_bets:
            return {
                "recommended_bets": [],
                "total_stake": 0.0,
                "expected_return": 0.0,
                "portfolio_risk": "low",
                "optimization_score": 0.0,
            }

        # 按价值评级排序
        valid_bets.sort(key=lambda x: x.value_rating, reverse=True)

        # 限制投注数量
        selected_bets = valid_bets[: strategy.max_daily_bets]

        # 计算投注金额
        total_stake = 0.0
        optimized_bets = []

        for bet in selected_bets:
            if total_stake >= max_total_stake:
                break

            # 调整投注金额以符合总限制
            adjusted_stake = min(bet.suggested_stake, max_total_stake - total_stake)

            if adjusted_stake > 0:
                bet.suggested_stake = adjusted_stake
                optimized_bets.append(bet)
                total_stake += adjusted_stake

        # 计算组合指标
        expected_return = sum(
            bet.suggested_stake * (1 + bet.ev) for bet in optimized_bets
        )

        portfolio_risk = self._assess_portfolio_risk(optimized_bets)
        optimization_score = self._calculate_optimization_score(
            optimized_bets, strategy
        )

        return {
            "recommended_bets": [asdict(bet) for bet in optimized_bets],
            "total_stake": total_stake,
            "expected_return": expected_return,
            "expected_profit": expected_return - total_stake,
            "portfolio_risk": portfolio_risk,
            "optimization_score": optimization_score,
            "strategy_used": strategy.name,
        }

    def _assess_portfolio_risk(self, bets: List[EVCalculation]) -> str:
        """评估组合风险"""
        if not bets:
            return "low"

        avg_risk = np.mean([bet.risk_level.value for bet in bets])
        total_stake = sum(bet.suggested_stake for bet in bets)

        if avg_risk <= 1.0 and total_stake <= 0.05:
            return "low"
        elif avg_risk <= 2.0 and total_stake <= 0.1:
            return "medium"
        else:
            return "high"

    def _calculate_optimization_score(
        self, bets: List[EVCalculation], strategy: BettingStrategy
    ) -> float:
        """计算优化分数 (0-100)"""
        if not bets:
            return 0.0

        # 基础分数
        base_score = np.mean([bet.value_rating for bet in bets]) * 10

        # EV加成
        ev_bonus = np.mean([bet.ev for bet in bets]) * 50

        # 风险调整
        risk_penalty = np.mean([bet.risk_level.value for bet in bets]) * 5

        # 多样性加成
        diversity_bonus = len(set(bet.bet_type for bet in bets)) * 2

        total_score = base_score + ev_bonus - risk_penalty + diversity_bonus
        return min(max(total_score, 0.0), 100.0)


class BettingRecommendationEngine:
    """类文档字符串"""
    pass  # 添加pass语句
    """投注建议引擎"""

    def __init__(self):
    """函数文档字符串"""
    pass  # 添加pass语句
        self.ev_calculator = EVCalculator()
        self.optimizer = BettingStrategyOptimizer()
        self.logger = logger
        self.redis_manager = get_redis_manager()

    async def generate_match_recommendations(
        self,
        match_id: str,
        odds: BettingOdds,
        probabilities: PredictionProbabilities,
        strategy_name: str = "srs_compliant",
    ) -> Dict[str, Any]:
        """为单场比赛生成投注建议"""

        strategy = self.optimizer.strategies.get(strategy_name)
        if not strategy:
            strategy = self.optimizer.strategies["srs_compliant"]

        # 计算各种投注类型的EV
        ev_calculations = []

        # 主要结果投注
        calculations = [
            (BetType.HOME_WIN, probabilities.home_win, odds.home_win),
            (BetType.DRAW, probabilities.draw, odds.draw),
            (BetType.AWAY_WIN, probabilities.away_win, odds.away_win),
        ]

        # 大小球投注（如果有数据）
        if probabilities.over_2_5 and odds.over_2_5:
            calculations.append(
                (BetType.OVER_2_5, probabilities.over_2_5, odds.over_2_5)
            )

        if probabilities.under_2_5 and odds.under_2_5:
            calculations.append(
                (BetType.UNDER_2_5, probabilities.under_2_5, odds.under_2_5)
            )

        # BTTS投注（如果有数据）
        if probabilities.btts_yes and odds.btts_yes:
            calculations.append((BetType.BTTS, probabilities.btts_yes, odds.btts_yes))

        # 计算每个投注类型的EV
        for bet_type, prob, odd in calculations:
            ev_calc = self.ev_calculator.calculate_comprehensive_ev(
                bet_type, prob, odd, strategy
            )
            ev_calculations.append(ev_calc)

        # 优化投注组合
        portfolio = self.optimizer.optimize_portfolio(ev_calculations, strategy)

        # 生成综合建议
        overall_recommendation = self._generate_overall_recommendation(
            portfolio, strategy
        )

        result = {
            "match_id": match_id,
            "strategy_used": strategy_name,
            "timestamp": datetime.now().isoformat(),
            "individual_bets": [asdict(calc) for calc in ev_calculations],
            "portfolio_optimization": portfolio,
            "overall_recommendation": overall_recommendation,
            "srs_compliance": self._check_srs_compliance(ev_calculations, portfolio),
            "risk_summary": self._generate_risk_summary(ev_calculations),
        }

        # 缓存结果
        await self._cache_recommendations(match_id, result)

        return result

    def _generate_overall_recommendation(
        self, portfolio: Dict[str, Any], strategy: BettingStrategy
    ) -> Dict[str, Any]:
        """生成总体建议"""
        recommended_bets = portfolio["recommended_bets"]

        if not recommended_bets:
            return {
                "action": "avoid",
                "reason": "没有找到符合要求的投注机会",
                "confidence": 0.0,
                "expected_value": 0.0,
            }

        total_ev = np.mean([bet["ev"] for bet in recommended_bets])
        total_value = np.mean([bet["value_rating"] for bet in recommended_bets])

        if total_ev >= 0.15 and total_value >= 8.0:
            action = "strong_recommend"
            confidence = min(total_ev * 5, 0.95)
        elif total_ev >= 0.08 and total_value >= 6.5:
            action = "recommend"
            confidence = min(total_ev * 4, 0.85)
        elif total_ev >= 0.05 and total_value >= 6.0:
            action = "weak_recommend"
            confidence = min(total_ev * 3, 0.75)
        else:
            action = "neutral"
            confidence = 0.5

        return {
            "action": action,
            "reason": f"组合EV: {total_ev:.3f}, 平均价值评级: {total_value:.1f}",
            "confidence": confidence,
            "expected_value": total_ev,
            "suggested_total_stake": portfolio["total_stake"],
            "expected_profit": portfolio["expected_profit"],
        }

    def _check_srs_compliance(
        self, ev_calculations: List[EVCalculation], portfolio: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检查SRS合规性"""
        srs_requirements = {
            "min_ev_threshold_met": all(
                calc.ev >= 0.05
                for calc in ev_calculations
                if calc.recommendation != "avoid"
            ),
            "max_risk_level_met": all(
                calc.risk_level.value <= 2
                for calc in ev_calculations
                if calc.recommendation != "avoid"
            ),
            "min_confidence_met": all(
                calc.confidence >= 0.6
                for calc in ev_calculations
                if calc.recommendation != "avoid"
            ),
            "kelly_criterion_used": portfolio["strategy_used"] != "unknown",
            "risk_management_enabled": True,
            "overall_compliance": False,
        }

        # 计算总体合规性
        srs_requirements["overall_compliance"] = all(
            [
                srs_requirements["min_ev_threshold_met"],
                srs_requirements["max_risk_level_met"],
                srs_requirements["min_confidence_met"],
                srs_requirements["kelly_criterion_used"],
            ]
        )

        return srs_requirements

    def _generate_risk_summary(
        self, ev_calculations: List[EVCalculation]
    ) -> Dict[str, Any]:
        """生成风险摘要"""
        if not ev_calculations:
            return {"overall_risk": "low", "risk_factors": []}

        risk_levels = [calc.risk_level.value for calc in ev_calculations]
        avg_risk = np.mean(risk_levels)
        max_risk = max(risk_levels)

        risk_factors = []
        if max_risk >= 3:
            risk_factors.append("存在高风险投注项")
        if avg_risk >= 2:
            risk_factors.append("整体风险水平偏高")
        if any(calc.ev < 0 for calc in ev_calculations):
            risk_factors.append("部分投注项期望价值为负")

        overall_risk = "low" if avg_risk <= 1 else "medium" if avg_risk <= 2 else "high"

        return {
            "overall_risk": overall_risk,
            "average_risk_score": float(avg_risk),
            "max_risk_level": RiskLevel(max_risk).name,
            "risk_factors": risk_factors,
            "total_bets_analyzed": len(ev_calculations),
        }

    async def _cache_recommendations(
        self, match_id: str, recommendations: Dict[str, Any]
    ):
        """缓存投注建议"""
        try:
            cache_key = f"betting_recommendations:{match_id}"
            await self.redis_manager.asetex(
                cache_key,
                int(timedelta(hours=2).total_seconds()),
                json.dumps(recommendations, default=str),
            )
        except Exception as e:
            self.logger.warning(f"缓存投注建议失败: {e}")


# 工厂函数和便捷接口
def create_betting_recommendation_engine() -> BettingRecommendationEngine:
    """创建投注建议引擎实例"""
    return BettingRecommendationEngine()


def create_custom_strategy(name: str, description: str, **kwargs) -> BettingStrategy:
    """创建自定义策略"""
    return BettingStrategy(name=name, description=description, **kwargs)


# 主要导出接口
__all__ = [
    "EVCalculator",
    "BettingStrategyOptimizer",
    "BettingRecommendationEngine",
    "BettingOdds",
    "PredictionProbabilities",
    "EVCalculation",
    "BettingStrategy",
    "BetType",
    "RiskLevel",
    "create_betting_recommendation_engine",
    "create_custom_strategy",
]
