"""
策略接口和实现 (Strategy Interface and Implementation)

定义回测策略的接口和默认实现。

作者: Backtesting Engineer (P2-4)
创建时间: 2025-12-06
版本: 1.0.0
"""

import logging
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import , Any, Optional

from .models import BetDecision, BetType, StrategyProtocol

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    """
    策略基类

    提供策略实现的通用功能。
    """

    def __init__(self, name: str):
        """
        初始化策略

        Args:
            name: 策略名称
        """
        self.name = name
        self.logger = logging.getLogger(f"{__name__}.{name}")

    @abstractmethod
    async def decide(
        self, match_data: dict[str, Any], odds_data: dict[str, Any]
    ) -> BetDecision:
        """
        根据比赛数据和赔率做出下注决策

        Args:
            match_data: 比赛数据字典
            odds_data: 赔率数据字典

        Returns:
            下注决策
        """
        pass

    def _calculate_implied_probability(self, odds: Decimal) -> float:
        """
        计算赔率的隐含概率

        Args:
            odds: 赔率

        Returns:
            隐含概率 (0.0-1.0)
        """
        # 隐含概率 = 1 / 赔率
        try:
            return float(Decimal("1.0") / odds)
        except (ZeroDivisionError, ValueError):
            return 0.0

    def _decimal_from_value(
        self, value: Any, default: Decimal = Decimal("1.0")
    ) -> Decimal:
        """
        安全地将值转换为Decimal

        Args:
            value: 要转换的值
            default: 默认值

        Returns:
            Decimal值
        """
        try:
            if value is None:
                return default
            return Decimal(str(value))
        except (ValueError, typeError):
            self.logger.warning(
                f"Cannot convert {value} to Decimal, using default {default}"
            )
            return default


class SimpleValueStrategy(BaseStrategy):
    """
    简单价值投资策略

    如果模型预测概率存在至少10%的价值边际，则下注。
    """

    def __init__(self, value_threshold: float = 0.1, min_confidence: float = 0.3):
        """
        初始化简单价值策略

        Args:
            value_threshold: 价值阈值（默认10%）
            min_confidence: 最小置信度（默认30%）
        """
        super().__init__("SimpleValueStrategy")
        self.value_threshold = value_threshold
        self.min_confidence = min_confidence

    async def decide(
        self, match_data: dict[str, Any], odds_data: dict[str, Any]
    ) -> BetDecision:
        """
        做出下注决策

        Args:
            match_data: 比赛数据，应包含模型预测
            odds_data: 赔率数据

        Returns:
            下注决策
        """
        match_id = match_data.get("id", 0)

        # 提取模型预测概率
        model_probs = self._extract_model_probabilities(match_data)
        if not model_probs:
            return self._create_skip_decision(match_id, odds_data)

        # 提取赔率
        odds = self._extract_odds(odds_data)
        if not odds:
            return self._create_skip_decision(match_id, odds_data)

        # 计算价值边际并找到最佳下注选择
        best_decision = self._find_best_value_bet(match_id, model_probs, odds)

        self.logger.debug(
            f"Strategy decision for match {match_id}: {best_decision.bet_type.value}, "
            f"value_edge: {best_decision.value_edge:.3f}, confidence: {best_decision.confidence:.3f}"
        )

        return best_decision

    def _extract_model_probabilities(
        self, match_data: dict[str, Any]
    ) -> Optional[dict[str, float]]:
        """
        提取模型预测概率

        Args:
            match_data: 比赛数据

        Returns:
            概率字典或None
        """
        # 尝试从不同字段提取概率
        prob_sources = ["predictions", "model_probs", "probabilities"]  # 假设数据格式

        for source in prob_sources:
            if source in match_data and match_data[source]:
                probs = match_data[source]
                if isinstance(probs, dict) and all(
                    k in probs for k in ["home_win", "draw", "away_win"]
                ):
                    return probs

        # 如果没有找到标准格式，尝试从预测结果中提取
        if "home_win_prob" in match_data:
            return {
                "home_win": float(match_data.get("home_win_prob", 0)),
                "draw": float(match_data.get("draw_prob", 0)),
                "away_win": float(match_data.get("away_win_prob", 0)),
            }

        self.logger.warning(
            f"Cannot extract model probabilities from match data: {list(match_data.keys())}"
        )
        return None

    def _extract_odds(self, odds_data: dict[str, Any]) -> Optional[dict[str, Decimal]]:
        """
        提取赔率

        Args:
            odds_data: 赔率数据

        Returns:
            赔率字典或None
        """
        # 尝试从不同格式提取赔率
        odds_sources = ["odds", "betting_odds", "market_odds"]

        for source in odds_sources:
            if source in odds_data and odds_data[source]:
                odds = odds_data[source]
                if isinstance(odds, dict) and all(
                    k in odds for k in ["home", "draw", "away"]
                ):
                    return {
                        "home": self._decimal_from_value(odds["home"]),
                        "draw": self._decimal_from_value(odds["draw"]),
                        "away": self._decimal_from_value(odds["away"]),
                    }

        # 如果找到具体的赔率字段
        if any(key in odds_data for key in ["home_odds", "draw_odds", "away_odds"]):
            return {
                "home": self._decimal_from_value(odds_data.get("home_odds")),
                "draw": self._decimal_from_value(odds_data.get("draw_odds")),
                "away": self._decimal_from_value(odds_data.get("away_odds")),
            }

        self.logger.warning(f"Cannot extract odds from data: {list(odds_data.keys())}")
        return None

    def _find_best_value_bet(
        self, match_id: int, model_probs: dict[str, float], odds: dict[str, Decimal]
    ) -> BetDecision:
        """
        找到最有价值的下注选择

        Args:
            match_id: 比赛ID
            model_probs: 模型预测概率
            odds: 赔率

        Returns:
            最佳下注决策
        """
        best_decision = None
        best_value = 0.0

        # 检查每个选项的价值
        for outcome, model_prob in model_probs.items():
            if outcome == "home_win":
                bet_type = BetType.HOME
                odd = odds["home"]
            elif outcome == "draw":
                bet_type = BetType.DRAW
                odd = odds["draw"]
            elif outcome == "away_win":
                bet_type = BetType.AWAY
                odd = odds["away"]
            else:
                continue

            # 计算隐含概率
            implied_prob = self._calculate_implied_probability(odd)

            # 计算价值边际
            value_edge = model_prob - implied_prob

            # 计算置信度
            confidence = self._calculate_confidence(
                model_prob, implied_prob, value_edge
            )

            # 检查是否满足策略条件
            if (
                value_edge >= self.value_threshold
                and confidence >= self.min_confidence
                and value_edge > best_value
            ):

                best_decision = BetDecision(
                    match_id=match_id,
                    bet_type=bet_type,
                    stake=Decimal("0.00"),  # 将由Portfolio计算
                    confidence=confidence,
                    implied_probability=implied_prob,
                    model_probability=model_prob,
                    odds=odd,
                )
                best_value = value_edge

        # 如果没有找到有价值的下注，返回跳过
        if best_decision is None:
            return self._create_skip_decision(match_id, odds)

        return best_decision

    def _calculate_confidence(
        self, model_prob: float, implied_prob: float, value_edge: float
    ) -> float:
        """
        计算策略置信度

        Args:
            model_prob: 模型概率
            implied_prob: 隐含概率
            value_edge: 价值边际

        Returns:
            置信度 (0.0-1.0)
        """
        # 基础置信度来自模型概率
        base_confidence = model_prob

        # 价值边际增加置信度
        value_confidence = min(value_edge * 2, 0.5)  # 最多增加50%置信度

        # 模型与市场的分歧程度
        divergence_confidence = min(abs(model_prob - implied_prob), 0.3)

        return min(base_confidence + value_confidence + divergence_confidence, 1.0)

    def _create_skip_decision(
        self, match_id: int, odds_data: dict[str, Any]
    ) -> BetDecision:
        """
        创建跳过下注的决策

        Args:
            match_id: 比赛ID
            odds_data: 赔率数据

        Returns:
            跳过决策
        """
        # 使用平均赔率作为参考
        odds_values = []
        for odds_field in ["home_odds", "draw_odds", "away_odds", "odds"]:
            if odds_field in odds_data and odds_data[odds_field]:
                if isinstance(odds_data[odds_field], dict):
                    odds_values.extend(odds_data[odds_field].values())
                else:
                    odds_values.append(odds_data[odds_field])

        avg_odds = Decimal("2.0")  # 默认值
        if odds_values:
            # 过滤有效赔率并计算平均
            valid_odds = [
                Decimal(str(o)) for o in odds_values if o and Decimal(str(o)) > 1
            ]
            if valid_odds:
                avg_odds = sum(valid_odds) / len(valid_odds)

        return BetDecision(
            match_id=match_id,
            bet_type=BetType.SKIP,
            stake=Decimal("0.00"),
            confidence=0.0,
            implied_probability=0.5,
            model_probability=0.5,
            odds=avg_odds,
        )


class ConservativeStrategy(SimpleValueStrategy):
    """
    保守策略

    需要更高的价值边际和置信度才下注。
    """

    def __init__(self, value_threshold: float = 0.15, min_confidence: float = 0.5):
        """
        初始化保守策略

        Args:
            value_threshold: 价值阈值（默认15%）
            min_confidence: 最小置信度（默认50%）
        """
        super().__init__(value_threshold, min_confidence)
        self.name = "ConservativeStrategy"


class AggressiveStrategy(SimpleValueStrategy):
    """
    激进策略

    较低的价值边际和置信度要求，下注更频繁。
    """

    def __init__(self, value_threshold: float = 0.05, min_confidence: float = 0.2):
        """
        初始化激进策略

        Args:
            value_threshold: 价值阈值（默认5%）
            min_confidence: 最小置信度（默认20%）
        """
        super().__init__(value_threshold, min_confidence)
        self.name = "AggressiveStrategy"


# 策略工厂
class StrategyFactory:
    """
    策略工厂类

    用于创建不同类型的策略实例。
    """

    _strategies = {
        "simple_value": SimpleValueStrategy,
        "conservative": ConservativeStrategy,
        "aggressive": AggressiveStrategy,
    }

    @classmethod
    def create_strategy(cls, strategy_type: str, **kwargs) -> BaseStrategy:
        """
        创建策略实例

        Args:
            strategy_type: 策略类型
            **kwargs: 策略参数

        Returns:
            策略实例
        """
        if strategy_type not in cls._strategies:
            raise ValueError(
                f"Unknown strategy typing.Type: {strategy_type}. Available: {list(cls._strategies.keys())}"
            )

        strategy_class = cls._strategies[strategy_type]
        return strategy_class(**kwargs)

    @classmethod
    def list_strategies(cls) -> list:
        """
        获取可用策略列表

        Returns:
            策略类型列表
        """
        return list(cls._strategies.keys())
