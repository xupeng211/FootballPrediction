"""
赔率领域模型
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class MarketType(Enum):
    """市场类型"""

    MATCH_RESULT = "1X2"  # 独赢
    HANDICAP = "HANDICAP"  # 让球
    OVER_UNDER = "OVER_UNDER"  # 大小球
    BOTH_TEAMS_SCORE = "BTTS"  # 双方进球
    CORRECT_SCORE = "CORRECT_SCORE"  # 正确比分
    HALF_TIME = "HT"  # 半场
    CORNER = "CORNER"  # 角球


class OddsFormat(Enum):
    """赔率格式"""

    DECIMAL = "decimal"  # 小数（欧洲）
    FRACTIONAL = "fractional"  # 分数（英国）
    AMERICAN = "american"  # 美式


class OddsMovement:
    """类文档字符串"""
    pass  # 添加pass语句
    """赔率变化"""

    def __init__(self, old_odds: float, new_odds: float, timestamp: datetime):
    """函数文档字符串"""
    pass  # 添加pass语句
        self.old_odds = old_odds
        self.new_odds = new_odds
        self.timestamp = timestamp
        self.change = new_odds - old_odds
        self.change_percent = (self.change / old_odds) * 100 if old_odds != 0 else 0

    def is_significant(self, threshold: float = 5.0) -> bool:
        """是否为显著变化"""
        return abs(self.change_percent) >= threshold


class ValueBet:
    """类文档字符串"""
    pass  # 添加pass语句
    """价值投注"""

    def __init__(self, odds: float, probability: float, threshold: float = 1.0):
    """函数文档字符串"""
    pass  # 添加pass语句
        self.odds = odds
        self.probability = probability
        self.threshold = threshold
        self.expected_value = (odds * probability) - 1

    def is_value(self) -> bool:
        """是否为价值投注"""
        return self.expected_value > self.threshold

    def get_confidence(self) -> float:
        """获取价值置信度"""
        if not self.is_value():
            return 0.0
        return min(1.0, self.expected_value / (self.threshold * 2))


class Odds:
    """类文档字符串"""
    pass  # 添加pass语句
    """赔率领域模型"""

    def __init__(
        self,
        id: Optional[int] = None,
        match_id: int = 0,
        market_type: MarketType = MarketType.MATCH_RESULT,
        bookmaker: str = "",
        home_odds: Optional[float] = None,
        draw_odds: Optional[float] = None,
        away_odds: Optional[float] = None,
    ):
        self.id = id
        self.match_id = match_id
        self.market_type = market_type
        self.bookmaker = bookmaker

        # 主赔率
        self.home_odds = home_odds
        self.draw_odds = draw_odds
        self.away_odds = away_odds

        # 扩展赔率（用于其他市场）
        self.over_odds: Optional[float] = None
        self.under_odds: Optional[float] = None
        self.handicap: Optional[float] = None
        self.handicap_home_odds: Optional[float] = None
        self.handicap_away_odds: Optional[float] = None

        # 历史变化
        self.movements: List[OddsMovement] = []

        # 状态
        self.is_active = True
        self.is_suspended = False

        # 时间戳
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.last_movement: Optional[datetime] = None

    def update_odds(
        self,
        home_odds: Optional[float] = None,
        draw_odds: Optional[float] = None,
        away_odds: Optional[float] = None,
    ) -> None:
        """更新赔率"""
        # 记录变化
        if home_odds and self.home_odds and home_odds != self.home_odds:
            self.movements.append(
                OddsMovement(self.home_odds, home_odds, datetime.now())
            )

        if draw_odds and self.draw_odds and draw_odds != self.draw_odds:
            self.movements.append(
                OddsMovement(self.draw_odds, draw_odds, datetime.now())
            )

        if away_odds and self.away_odds and away_odds != self.away_odds:
            self.movements.append(
                OddsMovement(self.away_odds, away_odds, datetime.now())
            )

        # 更新值
        if home_odds:
            self.home_odds = home_odds
        if draw_odds:
            self.draw_odds = draw_odds
        if away_odds:
            self.away_odds = away_odds

        self.updated_at = datetime.now()
        self.last_movement = datetime.now()

    def get_implied_probability(self) -> Dict[str, float]:
        """获取隐含概率"""
        probabilities = {}

        if self.home_odds and self.home_odds > 0:
            probabilities["home"] = (1 / self.home_odds) * 100

        if self.draw_odds and self.draw_odds > 0:
            probabilities["draw"] = (1 / self.draw_odds) * 100

        if self.away_odds and self.away_odds > 0:
            probabilities["away"] = (1 / self.away_odds) * 100

        return probabilities

    def get_vig_percentage(self) -> float:
        """获取抽水百分比"""
        probs = self.get_implied_probability()
        total_prob = sum(probs.values())

        if total_prob > 0:
            return total_prob - 100
        return 0.0

    def get_true_probability(self) -> Dict[str, float]:
        """获取真实概率（去除抽水）"""
        implied = self.get_implied_probability()
        vig = self.get_vig_percentage()

        if vig <= 0:
            return implied

        # 调整概率
        adjusted = {}
        for outcome, prob in implied.items():
            adjusted[outcome] = prob - (vig * (prob / 100))

        return adjusted

    def find_value_bets(
        self, predicted_probs: Dict[str, float], threshold: float = 1.0
    ) -> List[ValueBet]:
        """寻找价值投注"""
        value_bets = []

        if self.home_odds and "home" in predicted_probs:
            value_bet = ValueBet(
                self.home_odds, predicted_probs["home"] / 100, threshold
            )
            if value_bet.is_value():
                value_bets.append(value_bet)

        if self.draw_odds and "draw" in predicted_probs:
            value_bet = ValueBet(
                self.draw_odds, predicted_probs["draw"] / 100, threshold
            )
            if value_bet.is_value():
                value_bets.append(value_bet)

        if self.away_odds and "away" in predicted_probs:
            value_bet = ValueBet(
                self.away_odds, predicted_probs["away"] / 100, threshold
            )
            if value_bet.is_value():
                value_bets.append(value_bet)

        return value_bets

    def convert_format(self, target_format: OddsFormat) -> Dict[str, float]:
        """转换赔率格式"""
        result = {}

        if target_format == OddsFormat.DECIMAL:
            if self.home_odds:
                result["home"] = self.home_odds
            if self.draw_odds:
                result["draw"] = self.draw_odds
            if self.away_odds:
                result["away"] = self.away_odds

        elif target_format == OddsFormat.FRACTIONAL:
            if self.home_odds:
                result["home"] = self._decimal_to_fractional(self.home_odds)
            if self.draw_odds:
                result["draw"] = self._decimal_to_fractional(self.draw_odds)
            if self.away_odds:
                result["away"] = self._decimal_to_fractional(self.away_odds)

        elif target_format == OddsFormat.AMERICAN:
            if self.home_odds:
                result["home"] = self._decimal_to_american(self.home_odds)
            if self.draw_odds:
                result["draw"] = self._decimal_to_american(self.draw_odds)
            if self.away_odds:
                result["away"] = self._decimal_to_american(self.away_odds)

        return result

    def _decimal_to_fractional(self, decimal: float) -> str:
        """小数转分数"""
        if decimal <= 1:
            return "1/1"

        fraction = decimal - 1
        # 简化分数
        for i in range(1, 100):
            if abs(fraction * i - round(fraction * i)) < 0.01:
                numerator = round(fraction * i)
                denominator = i
                return f"{numerator}/{denominator}"

        return f"{fraction:.2f}/1"

    def _decimal_to_american(self, decimal: float) -> int:
        """小数转美式"""
        if decimal >= 2.0:
            return int((decimal - 1) * 100)
        else:
            return int(-100 / (decimal - 1))

    def suspend(self) -> None:
        """暂停赔率"""
        self.is_suspended = True
        self.is_active = False
        self.updated_at = datetime.now()

    def resume(self) -> None:
        """恢复赔率"""
        self.is_suspended = False
        self.is_active = True
        self.updated_at = datetime.now()

    def get_recent_movements(self, hours: int = 24) -> List[OddsMovement]:
        """获取最近的赔率变化"""
        cutoff = datetime.now().timestamp() - (hours * 3600)
        return [m for m in self.movements if m.timestamp.timestamp() > cutoff]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "match_id": self.match_id,
            "market_type": self.market_type.value,
            "bookmaker": self.bookmaker,
            "home_odds": self.home_odds,
            "draw_odds": self.draw_odds,
            "away_odds": self.away_odds,
            "over_odds": self.over_odds,
            "under_odds": self.under_odds,
            "handicap": self.handicap,
            "implied_probability": self.get_implied_probability(),
            "true_probability": self.get_true_probability(),
            "vig_percentage": self.get_vig_percentage(),
            "movements_count": len(self.movements),
            "is_active": self.is_active,
            "is_suspended": self.is_suspended,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_movement": (
                self.last_movement.isoformat() if self.last_movement else None
            ),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Odds":
        """从字典创建实例"""
        odds = cls(
            id=data.get("id"),
            match_id=data.get("match_id", 0),
            market_type=MarketType(data.get("market_type", "1X2")),
            bookmaker=data.get("bookmaker", ""),
            home_odds=data.get("home_odds"),
            draw_odds=data.get("draw_odds"),
            away_odds=data.get("away_odds"),
        )

        # 设置扩展赔率
        odds.over_odds = data.get("over_odds")
        odds.under_odds = data.get("under_odds")
        odds.handicap = data.get("handicap")

        # 设置状态
        odds.is_active = data.get("is_active", True)
        odds.is_suspended = data.get("is_suspended", False)

        # 设置时间戳
        if data.get("created_at"):
            odds.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            odds.updated_at = datetime.fromisoformat(data["updated_at"])
        if data.get("last_movement"):
            odds.last_movement = datetime.fromisoformat(data["last_movement"])

        return odds

    def __str__(self) -> str:
        return f"Odds({self.market_type.value}: {self.home_odds}/{self.draw_odds}/{self.away_odds})"

    def __repr__(self) -> str:
        return f"<Odds(id={self.id}, match_id={self.match_id}, bookmaker={self.bookmaker})>"
