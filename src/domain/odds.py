"""
赔率领域模型

封装赔率相关的业务逻辑和规则。
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field


class MarketType(Enum):
    """市场类型枚举"""

    MATCH_WINNER = "match_winner"  # 比赛胜者
    OVER_UNDER = "over_under"  # 大小球
    ASIAN_HANDICAP = "asian_handicap"  # 亚盘
    BOTH_TEAMS_SCORE = "both_teams_score"  # 双方进球
    CORRECT_SCORE = "correct_score"  # 精确比分
    FIRST_GOAL_SCORER = "first_goal_scorer"  # 首个进球者
    HALF_TIME_RESULT = "half_time_result"  # 半场结果
    DRAW_NO_BET = "draw_no_bet"  # 无平局
    DOUBLE_CHANCE = "double_chance"  # 双重机会


class OddsFormat(Enum):
    """赔率格式枚举"""

    DECIMAL = "decimal"  # 小数赔率（欧洲）
    FRACTIONAL = "fractional"  # 分数赔率（英国）
    AMERICAN = "american"  # 美式赔率
    HONG_KONG = "hong_kong"  # 香港赔率
    MALAY = "malay"  # 马来赔率
    INDONESIAN = "indonesian"  # 印尼赔率


class BookmakerStatus(Enum):
    """博彩公司状态枚举"""

    ACTIVE = "active"  # 活跃
    INACTIVE = "inactive"  # 不活跃
    SUSPENDED = "suspended"  # 暂停


@dataclass
class OddsMovement:
    """赔率变动记录"""

    timestamp: datetime
    home_odds: float
    draw_odds: float
    away_odds: float
    volume: Optional[float] = None
    bookmaker_id: Optional[int] = None


@dataclass
class OddsComparison:
    """赔率比较"""

    highest_home_odds: float
    highest_draw_odds: float
    highest_away_odds: float
    lowest_home_odds: float
    lowest_draw_odds: float
    lowest_away_odds: float
    average_home_odds: float
    average_draw_odds: float
    average_away_odds: float
    bookmaker_count: int

    @property
    def home_odds_range(self) -> float:
        """主胜赔率范围"""
        return self.highest_home_odds - self.lowest_home_odds

    @property
    def draw_odds_range(self) -> float:
        """平局赔率范围"""
        return self.highest_draw_odds - self.lowest_draw_odds

    @property
    def away_odds_range(self) -> float:
        """客胜赔率范围"""
        return self.highest_away_odds - self.lowest_away_odds


class Odds:
    """赔率领域模型

    封装赔率的核心业务逻辑和计算方法。
    """

    def __init__(
        self,
        id: Optional[int] = None,
        match_id: Optional[int] = None,
        bookmaker_id: Optional[int] = None,
        bookmaker_name: Optional[str] = None,
        market_type: MarketType = MarketType.MATCH_WINNER,
        home_odds: Optional[float] = None,
        draw_odds: Optional[float] = None,
        away_odds: Optional[float] = None,
        over_odds: Optional[float] = None,
        under_odds: Optional[float] = None,
        handicap: Optional[float] = None,
        handicap_home_odds: Optional[float] = None,
        handicap_away_odds: Optional[float] = None,
        both_teams_score_yes: Optional[float] = None,
        both_teams_score_no: Optional[float] = None,
        timestamp: Optional[datetime] = None,
        is_live: bool = False,
        volume: Optional[float] = None,
    ):
        self.id = id
        self.match_id = match_id
        self.bookmaker_id = bookmaker_id
        self.bookmaker_name = bookmaker_name
        self.market_type = market_type
        self.home_odds = home_odds
        self.draw_odds = draw_odds
        self.away_odds = away_odds
        self.over_odds = over_odds
        self.under_odds = under_odds
        self.handicap = handicap
        self.handicap_home_odds = handicap_home_odds
        self.handicap_away_odds = handicap_away_odds
        self.both_teams_score_yes = both_teams_score_yes
        self.both_teams_score_no = both_teams_score_no
        self.timestamp = timestamp or datetime.now()
        self.is_live = is_live
        self.volume = volume

        # 赔率变动历史
        self.movements: List[OddsMovement] = []

        # 元数据
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

        # 业务规则验证
        self._validate_initialization()

    def _validate_initialization(self):
        """验证初始化数据"""
        if self.market_type == MarketType.MATCH_WINNER:
            if not all([self.home_odds, self.draw_odds, self.away_odds]):
                raise ValueError("比赛胜者市场必须提供主胜、平局、客胜赔率")

        if self.market_type == MarketType.OVER_UNDER:
            if not all([self.over_odds, self.under_odds]):
                raise ValueError("大小球市场必须提供大小球赔率")

        # 验证赔率值
        for odds_name, odds_value in [
            ("home_odds", self.home_odds),
            ("draw_odds", self.draw_odds),
            ("away_odds", self.away_odds),
            ("over_odds", self.over_odds),
            ("under_odds", self.under_odds),
        ]:
            if odds_value is not None and odds_value <= 1.0:
                raise ValueError(f"{odds_name} 必须大于 1.0")

    # ==================== 赔率格式转换 ====================

    def to_format(self, target_format: OddsFormat, odds_value: float) -> float:
        """将赔率转换为目标格式"""
        if target_format == OddsFormat.DECIMAL:
            return odds_value
        elif target_format == OddsFormat.FRACTIONAL:
            return self._decimal_to_fractional(odds_value)
        elif target_format == OddsFormat.AMERICAN:
            return self._decimal_to_american(odds_value)
        elif target_format == OddsFormat.HONG_KONG:
            return odds_value - 1.0
        elif target_format == OddsFormat.MALAY:
            return self._decimal_to_malay(odds_value)
        elif target_format == OddsFormat.INDONESIAN:
            return self._decimal_to_indonesian(odds_value)
        else:
            return odds_value

    def _decimal_to_fractional(self, decimal: float) -> str:
        """小数赔率转分数赔率"""
        fractional = decimal - 1.0
        if fractional == int(fractional):
            return f"{int(fractional)}/1"
        else:
            # 近似分数
            for denominator in range(2, 21):
                numerator = round(fractional * denominator)
                if abs(fractional - numerator / denominator) < 0.01:
                    return f"{numerator}/{denominator}"
            return f"{round(fractional*10)}/10"

    def _decimal_to_american(self, decimal: float) -> str:
        """小数赔率转美式赔率"""
        if decimal >= 2.0:
            return f"+{int((decimal - 1) * 100)}"
        else:
            return f"-{int(100 / (decimal - 1))}"

    def _decimal_to_malay(self, decimal: float) -> float:
        """小数赔率转马来赔率"""
        if decimal > 2.0:
            return (decimal - 1.0) / -1.0
        else:
            return decimal - 1.0

    def _decimal_to_indonesian(self, decimal: float) -> float:
        """小数赔率转印尼赔率"""
        if decimal > 2.0:
            return decimal - 1.0
        else:
            return (decimal - 1.0) / -1.0

    # ==================== 概率计算 ====================

    def get_implied_probability(self, odds: float) -> float:
        """获取隐含概率"""
        if odds <= 1.0:
            return 0.0
        return 1.0 / odds

    def get_vigorish(self) -> float:
        """计算抽水比例"""
        if not all([self.home_odds, self.draw_odds, self.away_odds]):
            return 0.0

        prob_home = self.get_implied_probability(self.home_odds)
        prob_draw = self.get_implied_probability(self.draw_odds)
        prob_away = self.get_implied_probability(self.away_odds)

        total_prob = prob_home + prob_draw + prob_away
        return max(0, total_prob - 1.0)

    def get_true_probabilities(self) -> Dict[str, float]:
        """获取真实概率（去除抽水）"""
        if not all([self.home_odds, self.draw_odds, self.away_odds]):
            return {}

        vigorish = self.get_vigorish()
        if vigorish == 0:
            return {
                "home": self.get_implied_probability(self.home_odds),
                "draw": self.get_implied_probability(self.draw_odds),
                "away": self.get_implied_probability(self.away_odds),
            }

        # 按比例分配
        total_without_vig = 1.0 - vigorish
        prob_home = self.get_implied_probability(self.home_odds) / (1.0 + vigorish)
        prob_draw = self.get_implied_probability(self.draw_odds) / (1.0 + vigorish)
        prob_away = self.get_implied_probability(self.away_odds) / (1.0 + vigorish)

        return {
            "home": prob_home * total_without_vig,
            "draw": prob_draw * total_without_vig,
            "away": prob_away * total_without_vig,
        }

    # ==================== 价值分析 ====================

    def find_value_bets(
        self, predicted_probs: Dict[str, float], threshold: float = 0.05
    ) -> Dict[str, float]:
        """寻找价值投注"""
        if not all([self.home_odds, self.draw_odds, self.away_odds]):
            return {}

        true_probs = self.get_true_probabilities()
        value_bets = {}

        for outcome in ["home", "draw", "away"]:
            if outcome in predicted_probs and outcome in true_probs:
                odds = getattr(self, f"{outcome}_odds")
                if odds:
                    expected_value = (predicted_probs[outcome] * odds) - 1.0
                    if expected_value > threshold:
                        value_bets[outcome] = expected_value

        return value_bets

    def calculate_kelly_criterion(self, predicted_prob: float, odds: float) -> float:
        """计算凯利准则投注比例"""
        if odds <= 1.0:
            return 0.0

        b = odds - 1.0  # 净赔率
        p = predicted_prob  # 预测概率
        q = 1.0 - p  # 失败概率

        kelly = (b * p - q) / b
        return max(0, kelly)  # 不允许负投注

    # ==================== 赔率变动分析 ====================

    def add_movement(
        self,
        home_odds: float,
        draw_odds: float,
        away_odds: float,
        volume: Optional[float] = None,
    ):
        """添加赔率变动记录"""
        movement = OddsMovement(
            timestamp=datetime.now(),
            home_odds=home_odds,
            draw_odds=draw_odds,
            away_odds=away_odds,
            volume=volume,
            bookmaker_id=self.bookmaker_id,
        )
        self.movements.append(movement)
        self.updated_at = datetime.now()

    def get_movement_trend(self, hours: int = 24) -> Dict[str, float]:
        """获取赔率变动趋势"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_movements = [m for m in self.movements if m.timestamp > cutoff_time]

        if len(recent_movements) < 2:
            return {"home": 0.0, "draw": 0.0, "away": 0.0}

        first = recent_movements[0]
        last = recent_movements[-1]

        return {
            "home": self._calculate_change(first.home_odds, last.home_odds),
            "draw": self._calculate_change(first.draw_odds, last.draw_odds),
            "away": self._calculate_change(first.away_odds, last.away_odds),
        }

    def _calculate_change(self, old_odds: float, new_odds: float) -> float:
        """计算赔率变化百分比"""
        if old_odds == 0:
            return 0.0
        return ((new_odds - old_odds) / old_odds) * 100

    def get_volatility(self, hours: int = 24) -> float:
        """获取赔率波动率"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_movements = [m for m in self.movements if m.timestamp > cutoff_time]

        if len(recent_movements) < 2:
            return 0.0

        # 计算标准差
        changes = []
        for i in range(1, len(recent_movements)):
            change = abs(
                self._calculate_change(
                    recent_movements[i - 1].home_odds, recent_movements[i].home_odds
                )
            )
            changes.append(change)

        if not changes:
            return 0.0

        avg_change = sum(changes) / len(changes)
        variance = sum((c - avg_change) ** 2 for c in changes) / len(changes)
        return variance**0.5

    # ==================== 市场分析 ====================

    def compare_with_market_average(self, market_average: "Odds") -> Dict[str, float]:
        """与市场平均赔率比较"""
        if not market_average:
            return {}

        comparison = {}
        for outcome in ["home", "draw", "away"]:
            my_odds = getattr(self, f"{outcome}_odds")
            avg_odds = getattr(market_average, f"{outcome}_odds")

            if my_odds and avg_odds:
                comparison[f"{outcome}_difference"] = (
                    (my_odds - avg_odds) / avg_odds
                ) * 100

        return comparison

    def is_best_value(self, all_odds: List["Odds"]) -> Dict[str, bool]:
        """检查是否为最优赔率"""
        best_values = {"home": True, "draw": True, "away": True}

        for other_odds in all_odds:
            if other_odds.id == self.id:
                continue

            for outcome in ["home", "draw", "away"]:
                my_odds = getattr(self, f"{outcome}_odds")
                other_odds_value = getattr(other_odds, f"{outcome}_odds")

                if my_odds and other_odds_value and other_odds_value > my_odds:
                    best_values[outcome] = False

        return best_values

    # ==================== 导出和序列化 ====================

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "match_id": self.match_id,
            "bookmaker_id": self.bookmaker_id,
            "bookmaker_name": self.bookmaker_name,
            "market_type": self.market_type.value,
            "home_odds": self.home_odds,
            "draw_odds": self.draw_odds,
            "away_odds": self.away_odds,
            "over_odds": self.over_odds,
            "under_odds": self.under_odds,
            "handicap": self.handicap,
            "handicap_home_odds": self.handicap_home_odds,
            "handicap_away_odds": self.handicap_away_odds,
            "both_teams_score_yes": self.both_teams_score_yes,
            "both_teams_score_no": self.both_teams_score_no,
            "timestamp": self.timestamp.isoformat(),
            "is_live": self.is_live,
            "volume": self.volume,
            "vigorish": self.get_vigorish(),
            "true_probabilities": self.get_true_probabilities(),
            "movements_count": len(self.movements),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Odds":
        """从字典创建实例"""
        odds = cls(
            id=data.get("id"),
            match_id=data.get("match_id"),
            bookmaker_id=data.get("bookmaker_id"),
            bookmaker_name=data.get("bookmaker_name"),
            market_type=MarketType(data.get("market_type", "match_winner")),
            home_odds=data.get("home_odds"),
            draw_odds=data.get("draw_odds"),
            away_odds=data.get("away_odds"),
            over_odds=data.get("over_odds"),
            under_odds=data.get("under_odds"),
            handicap=data.get("handicap"),
            handicap_home_odds=data.get("handicap_home_odds"),
            handicap_away_odds=data.get("handicap_away_odds"),
            both_teams_score_yes=data.get("both_teams_score_yes"),
            both_teams_score_no=data.get("both_teams_score_no"),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if data.get("timestamp")
            else None,
            is_live=data.get("is_live", False),
            volume=data.get("volume"),
        )

        # 恢复时间戳
        if data.get("created_at"):
            odds.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            odds.updated_at = datetime.fromisoformat(data["updated_at"])

        return odds

    # ==================== 比较和哈希 ====================

    def __eq__(self, other) -> bool:
        """比较两个赔率是否相同"""
        if not isinstance(other, Odds):
            return False
        return (
            self.id == other.id
            if self.id and other.id
            else (
                self.match_id == other.match_id
                and self.bookmaker_id == other.bookmaker_id
                and self.market_type == other.market_type
            )
        )

    def __hash__(self) -> int:
        """生成哈希值"""
        if self.id:
            return hash(self.id)
        return hash((self.match_id, self.bookmaker_id, self.market_type))

    def __str__(self) -> str:
        """字符串表示"""
        if self.home_odds and self.draw_odds and self.away_odds:
            return f"{self.home_odds:.2f}-{self.draw_odds:.2f}-{self.away_odds:.2f}"
        return f"Odds {self.id}"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return (
            f"Odds(id={self.id}, match_id={self.match_id}, "
            f"bookmaker='{self.bookmaker_name}', type={self.market_type.value})"
        )


# 注意：需要在文件顶部添加缺少的导入
from datetime import timedelta
