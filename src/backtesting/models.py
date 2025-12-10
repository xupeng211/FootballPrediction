"""
回测系统数据模型 (Backtesting Data Models)

定义回测过程中使用的核心数据结构。

作者: Backtesting Engineer (P2-4)
创建时间: 2025-12-06
版本: 1.0.0
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import dict, list, Optional, Any

import numpy as np


class BetOutcome(Enum):
    """下注结果枚举"""

    HOME_WIN = "home_win"  # 主队胜
    AWAY_WIN = "away_win"  # 客队胜
    DRAW = "draw"  # 平局
    PENDING = "pending"  # 待定（比赛未结束）


class BetType(Enum):
    """下注类型枚举"""

    HOME = "home"  # 下注主队胜
    AWAY = "away"  # 下注客队胜
    DRAW = "draw"  # 下注平局
    SKIP = "skip"  # 跳过（不下注）


@dataclass
class BetDecision:
    """下注决策"""

    match_id: int
    bet_type: BetType
    stake: Decimal
    confidence: float  # 0.0-1.0，策略的置信度
    implied_probability: float  # 市场隐含概率
    model_probability: float  # 模型预测概率
    odds: Decimal  # 赔率
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def expected_value(self) -> float:
        """期望价值计算"""
        if self.bet_type == BetType.SKIP:
            return 0.0

        # EV = (win_prob * win_amount) - (lose_prob * stake)
        win_prob = self.model_probability
        lose_prob = 1.0 - win_prob
        win_amount = self.stake * (self.odds - 1)

        return (win_prob * win_amount) - (lose_prob * self.stake)

    @property
    def value_edge(self) -> float:
        """价值边际（模型概率 vs 市场隐含概率）"""
        if self.bet_type == BetType.SKIP:
            return 0.0
        return self.model_probability - self.implied_probability


@dataclass
class BetResult:
    """下注结果"""

    decision: BetDecision
    actual_outcome: BetOutcome
    profit_loss: Decimal  # 盈亏（正数=盈利，负数=亏损）
    is_correct: bool  # 预测是否正确
    settled_at: datetime = field(default_factory=datetime.now)

    @property
    def roi(self) -> float:
        """投资回报率"""
        if self.decision.stake == 0:
            return 0.0
        return float(self.profit_loss / self.decision.stake)


@dataclass
class BacktestConfig:
    """回测配置"""

    initial_balance: Decimal = Decimal("10000.00")  # 初始资金
    max_stake_pct: float = 0.05  # 单次下注最大比例（5%）
    min_stake: Decimal = Decimal("100.00")  # 最小下注金额
    max_stake: Decimal = Decimal("5000.00")  # 最大下注金额
    value_threshold: float = 0.1  # 价值阈值（10%边际才下注）
    min_confidence: float = 0.3  # 最小置信度
    max_daily_bets: int = 10  # 每日最大下注次数


@dataclass
class BacktestResult:
    """回测结果统计"""

    config: BacktestConfig
    total_matches: int = 0
    total_bets: int = 0
    winning_bets: int = 0
    losing_bets: int = 0
    skipped_bets: int = 0

    # 资金统计
    initial_balance: Decimal = Decimal("0.00")
    final_balance: Decimal = Decimal("0.00")
    total_profit_loss: Decimal = Decimal("0.00")
    max_balance: Decimal = Decimal("0.00")
    min_balance: Decimal = Decimal("0.00")

    # 性能指标
    total_staked: Decimal = Decimal("0.00")
    win_rate: float = 0.0
    roi: float = 0.0
    avg_stake: Decimal = Decimal("0.00")
    avg_profit: Decimal = Decimal("0.00")

    # 高级统计
    max_consecutive_losses: int = 0
    max_consecutive_wins: int = 0
    profit_volatility: float = 0.0  # 盈亏波动率
    sharpe_ratio: float = 0.0  # 夏普比率

    # 详细记录
    bet_results: list[BetResult] = field(default_factory=list)
    daily_balances: dict[datetime, Decimal] = field(default_factory=dict)
    balance_history: list[Decimal] = field(default_factory=list)

    def calculate_metrics(self) -> None:
        """计算性能指标"""
        if self.total_bets == 0:
            return

        # 基础指标
        self.win_rate = self.winning_bets / self.total_bets
        self.total_profit_loss = self.final_balance - self.initial_balance
        self.roi = float(self.total_profit_loss / self.initial_balance * 100)
        self.avg_stake = (
            self.total_staked / self.total_bets
            if self.total_bets > 0
            else Decimal("0.00")
        )

        if self.winning_bets > 0:
            winning_profits = [
                r.profit_loss for r in self.bet_results if r.profit_loss > 0
            ]
            self.avg_profit = sum(winning_profits) / len(winning_profits)

        # 高级统计
        self._calculate_consecutive_results()
        self._calculate_volatility()
        self._calculate_sharpe_ratio()

    def _calculate_consecutive_results(self) -> None:
        """计算连续盈亏统计"""
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0

        for result in self.bet_results:
            if result.profit_loss > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            elif result.profit_loss < 0:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)

        self.max_consecutive_wins = max_wins
        self.max_consecutive_losses = max_losses

    def _calculate_volatility(self) -> None:
        """计算盈亏波动率"""
        if len(self.bet_results) < 2:
            self.profit_volatility = 0.0
            return

        profits = [float(r.profit_loss) for r in self.bet_results]
        self.profit_volatility = np.std(profits)

    def _calculate_sharpe_ratio(self) -> None:
        """计算夏普比率（年化）"""
        if self.profit_volatility == 0:
            self.sharpe_ratio = 0.0
            return

        # 假设无风险收益率为0，使用实际收益标准差
        expected_return = self.roi / 100  # 转换为小数
        self.sharpe_ratio = expected_return / (
            self.profit_volatility / abs(self.initial_balance)
        )

    def get_summary(self) -> str:
        """获取回测结果摘要"""
        return f"""
📊 回测结果摘要
================
总比赛场次: {self.total_matches}
下注场次: {self.total_bets} (跳过: {self.skipped_bets})
胜率: {self.win_rate:.2%}
总盈亏: {self.total_profit_loss:+,.2f}
投资回报率: {self.roi:+.2f}%
最大连胜: {self.max_consecutive_wins}
最大连败: {self.max_consecutive_losses}
平均下注: {self.avg_stake:,.2f}
盈亏波动率: {self.profit_volatility:.2f}
夏普比率: {self.sharpe_ratio:.3f}
================
        """.strip()


# 用于类型提示的Protocol导入
from typing import Protocol


class StrategyProtocol(Protocol):
    """策略接口协议"""

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
        ...
