"""
资金管理类 (Portfolio)

负责跟踪资金、管理下注和计算盈亏。

作者: Backtesting Engineer (P2-4)
创建时间: 2025-12-06
版本: 1.0.0
"""

import logging
from decimal import Decimal, ROUND_DOWN
from typing import dict, list, Optional
from datetime import datetime

from .models import BetDecision, BetResult, BetOutcome, BacktestConfig

logger = logging.getLogger(__name__)


class Portfolio:
    """
    资金管理器

    负责跟踪账户余额、记录下注、计算盈亏和管理风险。
    """

    def __init__(self, config: BacktestConfig):
        """
        初始化资金管理器

        Args:
            config: 回测配置
        """
        self.config = config
        self.initial_balance = config.initial_balance
        self.current_balance = config.initial_balance
        self.max_balance = config.initial_balance
        self.min_balance = config.initial_balance

        # 下注记录
        self.bet_history: list[BetResult] = []
        self.pending_bets: dict[int, BetDecision] = {}  # match_id -> decision

        # 统计数据
        self.total_staked = Decimal("0.00")
        self.total_wins = 0
        self.total_losses = 0
        self.total_skips = 0
        self.daily_balance_history: dict[datetime, Decimal] = {}

        logger.info(f"Portfolio initialized with balance: {self.initial_balance}")

    def calculate_stake(self, decision: BetDecision) -> Decimal:
        """
        计算下注金额

        基于固定比例下注策略，考虑最大下注限制。

        Args:
            decision: 下注决策

        Returns:
            建议的下注金额
        """
        if decision.bet_type.value == "skip":
            return Decimal("0.00")

        # 基础下注金额（固定比例）
        base_stake = self.current_balance * Decimal(str(self.config.max_stake_pct))

        # 应用置信度调整
        confidence_adjusted = base_stake * Decimal(str(decision.confidence))

        # 价值边际调整（更高的价值边际 = 更高的下注比例）
        value_multiplier = 1.0 + min(decision.value_edge * 2, 1.0)  # 最多2倍
        value_adjusted = confidence_adjusted * Decimal(str(value_multiplier))

        # 应用限制
        final_stake = max(
            self.config.min_stake,
            min(
                value_adjusted,
                self.config.max_stake,
                self.current_balance,  # 不能超过当前余额
            ),
        )

        # 向下舍入到分
        final_stake = final_stake.quantize(Decimal("0.01"), rounding=ROUND_DOWN)

        logger.debug(
            f"Stake calculation: base={base_stake}, confidence={decision.confidence}, "
            f"value_edge={decision.value_edge}, final={final_stake}"
        )

        return final_stake

    def can_place_bet(self, decision: BetDecision, date: datetime) -> bool:
        """
        检查是否可以下注

        Args:
            decision: 下注决策
            date: 下注日期

        Returns:
            是否可以下注
        """
        # 检查下注类型
        if decision.bet_type.value == "skip":
            return True

        # 检查余额
        if self.current_balance <= 0:
            logger.warning(f"Insufficient balance: {self.current_balance}")
            return False

        # 检查价值边际
        if abs(decision.value_edge) < self.config.value_threshold:
            logger.debug(
                f"Value edge too small: {decision.value_edge} < {self.config.value_threshold}"
            )
            return False

        # 检查置信度
        if decision.confidence < self.config.min_confidence:
            logger.debug(
                f"Confidence too low: {decision.confidence} < {self.config.min_confidence}"
            )
            return False

        # 检查每日下注限制
        daily_bets = self._count_daily_bets(date)
        if daily_bets >= self.config.max_daily_bets:
            logger.debug(
                f"Daily bet limit reached: {daily_bets} >= {self.config.max_daily_bets}"
            )
            return False

        # 计算并检查下注金额
        stake = self.calculate_stake(decision)
        if stake > self.current_balance:
            logger.warning(f"Stake {stake} exceeds balance {self.current_balance}")
            return False

        return True

    def place_bet(self, decision: BetDecision, stake: Optional[Decimal] = None) -> bool:
        """
        下注

        Args:
            decision: 下注决策
            stake: 指定下注金额（可选，默认使用计算值）

        Returns:
            下注是否成功
        """
        if decision.bet_type.value == "skip":
            self.total_skips += 1
            logger.info(f"Skipped bet for match {decision.match_id}")
            return True

        if stake is None:
            stake = self.calculate_stake(decision)

        # 更新决策中的下注金额
        decision.stake = stake

        # 检查余额
        if stake > self.current_balance:
            logger.error(
                f"Insufficient balance for stake {stake}, current: {self.current_balance}"
            )
            return False

        # 扣除下注金额
        self.current_balance -= stake
        self.total_staked += stake
        self.pending_bets[decision.match_id] = decision

        logger.info(
            f"Bet placed: match={decision.match_id}, typing.Type={decision.bet_type.value}, "
            f"stake={stake}, odds={decision.odds}, balance={self.current_balance}"
        )

        return True

    def settle_bet(
        self,
        match_id: int,
        actual_outcome: BetOutcome,
        match_date: Optional[datetime] = None,
    ) -> Optional[BetResult]:
        """
        结算下注

        Args:
            match_id: 比赛ID
            actual_outcome: 实际比赛结果
            match_date: 比赛日期

        Returns:
            结算结果，如果找不到对应的下注则返回None
        """
        if match_id not in self.pending_bets:
            logger.warning(f"No pending bet found for match {match_id}")
            return None

        decision = self.pending_bets.pop(match_id)
        stake = decision.stake
        odds = decision.odds

        # 计算盈亏
        profit_loss = self._calculate_profit_loss(
            decision.bet_type, actual_outcome, stake, odds
        )
        is_correct = self._is_bet_correct(decision.bet_type, actual_outcome)

        # 更新余额
        self.current_balance += stake + profit_loss  # 返还本金 + 盈亏

        # 更新统计
        if profit_loss > 0:
            self.total_wins += 1
        elif profit_loss < 0:
            self.total_losses += 1

        # 更新最大最小余额
        self.max_balance = max(self.max_balance, self.current_balance)
        self.min_balance = min(self.min_balance, self.current_balance)

        # 创建结果记录
        result = BetResult(
            decision=decision,
            actual_outcome=actual_outcome,
            profit_loss=profit_loss,
            is_correct=is_correct,
            settled_at=match_date or datetime.now(),
        )

        self.bet_history.append(result)

        logger.info(
            f"Bet settled: match={match_id}, result={actual_outcome.value}, "
            f"profit_loss={profit_loss:+.2f}, balance={self.current_balance}"
        )

        return result

    def _calculate_profit_loss(
        self, bet_type: str, outcome: BetOutcome, stake: Decimal, odds: Decimal
    ) -> Decimal:
        """
        计算盈亏

        Args:
            bet_type: 下注类型
            outcome: 实际结果
            stake: 下注金额
            odds: 赔率

        Returns:
            盈亏（正数=盈利，负数=亏损）
        """
        # 检查是否中奖
        if self._is_bet_correct(bet_type, outcome):
            return stake * (odds - 1)  # 净盈利 = 本金 * (赔率 - 1)
        else:
            return -stake  # 输掉下注金额

    def _is_bet_correct(self, bet_type: str, outcome: BetOutcome) -> bool:
        """
        判断下注是否正确

        Args:
            bet_type: 下注类型
            outcome: 实际结果

        Returns:
            是否中奖
        """
        if bet_type == "home" and outcome == BetOutcome.HOME_WIN:
            return True
        elif bet_type == "away" and outcome == BetOutcome.AWAY_WIN:
            return True
        elif bet_type == "draw" and outcome == BetOutcome.DRAW:
            return True
        return False

    def _count_daily_bets(self, date: datetime) -> int:
        """
        计算指定日期的下注数量

        Args:
            date: 日期

        Returns:
            下注数量
        """
        date_key = date.date()
        count = 0
        for result in self.bet_history:
            if result.decision.timestamp.date() == date_key:
                count += 1

        for decision in self.pending_bets.values():
            if decision.timestamp.date() == date_key:
                count += 1

        return count

    def get_statistics(self) -> dict[str, any]:
        """
        获取资金统计信息

        Returns:
            统计信息字典
        """
        total_bets = self.total_wins + self.total_losses

        if total_bets > 0:
            win_rate = self.total_wins / total_bets
            avg_stake = self.total_staked / total_bets
        else:
            win_rate = 0.0
            avg_stake = Decimal("0.00")

        total_profit_loss = self.current_balance - self.initial_balance
        roi = (
            float(total_profit_loss / self.initial_balance * 100)
            if self.initial_balance > 0
            else 0.0
        )

        return {
            "initial_balance": self.initial_balance,
            "current_balance": self.current_balance,
            "total_profit_loss": total_profit_loss,
            "roi_percent": roi,
            "total_staked": self.total_staked,
            "total_bets": total_bets,
            "total_wins": self.total_wins,
            "total_losses": self.total_losses,
            "total_skips": self.total_skips,
            "win_rate": win_rate,
            "avg_stake": avg_stake,
            "max_balance": self.max_balance,
            "min_balance": self.min_balance,
            "max_drawdown": float(
                (self.initial_balance - self.min_balance) / self.initial_balance * 100
            ),
            "pending_bets": len(self.pending_bets),
        }

    def get_balance_history(self) -> list[dict[str, any]]:
        """
        获取余额历史

        Returns:
            余额历史列表
        """
        history = []

        # 添加初始余额
        history.append(
            {
                "timestamp": datetime.now(),
                "balance": self.initial_balance,
                "event": "initial",
            }
        )

        # 添加每次下注后的余额变化
        for result in self.bet_history:
            balance_at_time = self.initial_balance + sum(
                r.profit_loss
                for r in self.bet_history
                if r.settled_at <= result.settled_at
            )

            history.append(
                {
                    "timestamp": result.settled_at,
                    "balance": balance_at_time,
                    "event": f"bet_{result.decision.bet_type.value}_{'win' if result.profit_loss > 0 else 'lose'}",
                    "profit_loss": result.profit_loss,
                }
            )

        return sorted(history, key=lambda x: x["timestamp"])

    def reset(self) -> None:
        """重置资金管理器到初始状态"""
        self.current_balance = self.initial_balance
        self.max_balance = self.initial_balance
        self.min_balance = self.initial_balance
        self.bet_history.clear()
        self.pending_bets.clear()
        self.total_staked = Decimal("0.00")
        self.total_wins = 0
        self.total_losses = 0
        self.total_skips = 0
        self.daily_balance_history.clear()

        logger.info("Portfolio reset to initial state")
