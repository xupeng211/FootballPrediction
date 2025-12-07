"""
Football Prediction Backtesting System

足球预测回测系统，提供完整的投注模拟和收益分析功能。
支持多种投注策略、风险管理、以及详细的收益分析。

Author: Football Prediction Team
Version: 1.0.0
"""

import json
import csv
import numpy as np
import pandas as pd
from typing import Optional, Union, Any
from collections.abc import Callable
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class BetType(Enum):
    """投注类型枚举"""

    HOME_WIN = "H"
    DRAW = "D"
    AWAY_WIN = "A"


@dataclass
class Bet:
    """单笔投注记录"""

    match_id: str
    date: str
    prediction: int  # 0=H, 1=D, 2=A
    predicted_proba: list[float]  # [P(H), P(D), P(A)]
    odds: list[float]  # [Odds(H), Odds(D), Odds(A)]
    stake: float
    bet_type: BetType
    actual_result: int  # 0=H, 1=D, 2=A
    won: bool
    profit: float
    ev: float  # 期望值
    confidence: float  # 预测置信度

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "match_id": self.match_id,
            "date": self.date,
            "prediction": self.prediction,
            "predicted_proba": self.predicted_proba,
            "odds": self.odds,
            "stake": self.stake,
            "bet_type": self.bet_type.value,
            "actual_result": self.actual_result,
            "won": self.won,
            "profit": self.profit,
            "ev": self.ev,
            "confidence": self.confidence,
        }


@dataclass
class BacktestResult:
    """回测结果"""

    initial_bankroll: float
    final_bankroll: float
    total_bets: int
    winning_bets: int
    losing_bets: int
    total_stake: float
    total_winnings: float
    net_profit: float
    roi: float  # 投资回报率
    win_rate: float
    avg_odds: float
    max_consecutive_losses: int
    max_consecutive_wins: int
    max_drawdown: float
    max_drawdown_percentage: float
    sharpe_ratio: float
    calmar_ratio: float
    profit_factor: float  # 盈利因子
    avg_profit_per_bet: float
    std_profit_per_bet: float
    bets: list[Bet]
    equity_curve: list[float]
    metadata: dict[str, Any]

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "initial_bankroll": self.initial_bankroll,
            "final_bankroll": self.final_bankroll,
            "total_bets": self.total_bets,
            "winning_bets": self.winning_bets,
            "losing_bets": self.losing_bets,
            "total_stake": self.total_stake,
            "total_winnings": self.total_winnings,
            "net_profit": self.net_profit,
            "roi": self.roi,
            "win_rate": self.win_rate,
            "avg_odds": self.avg_odds,
            "max_consecutive_losses": self.max_consecutive_losses,
            "max_consecutive_wins": self.max_consecutive_wins,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_percentage": self.max_drawdown_percentage,
            "sharpe_ratio": self.sharpe_ratio,
            "calmar_ratio": self.calmar_ratio,
            "profit_factor": self.profit_factor,
            "avg_profit_per_bet": self.avg_profit_per_bet,
            "std_profit_per_bet": self.std_profit_per_bet,
            "equity_curve": self.equity_curve,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """转换为JSON"""
        # 将bets转换为字典列表
        result_dict = self.to_dict()
        result_dict["bets"] = [bet.to_dict() for bet in self.bets]
        return json.dumps(result_dict, indent=2, ensure_ascii=False)


class StakingStrategy:
    """投注策略基类"""

    def calculate_stake(self, bankroll: float, **kwargs) -> float:
        """计算投注金额"""
        raise NotImplementedError("Subclasses must implement calculate_stake method")


class FlatStakingStrategy(StakingStrategy):
    """固定投注策略"""

    def __init__(self, stake_amount: float):
        """
        初始化固定投注策略

        Args:
            stake_amount: 每注固定金额
        """
        self.stake_amount = stake_amount

    def calculate_stake(self, bankroll: float, **kwargs) -> float:
        """返回固定投注金额"""
        return min(self.stake_amount, bankroll * 0.1)  # 最多投注10%资金


class PercentageStakingStrategy(StakingStrategy):
    """百分比投注策略"""

    def __init__(self, percentage: float):
        """
        初始化百分比投注策略

        Args:
            percentage: 投注百分比 (0.01 = 1%)
        """
        self.percentage = percentage

    def calculate_stake(self, bankroll: float, **kwargs) -> float:
        """按百分比计算投注金额"""
        return bankroll * self.percentage


class KellyStakingStrategy(StakingStrategy):
    """凯利投注策略"""

    def __init__(
        self,
        kelly_fraction: float = 0.25,
        min_stake: float = 1.0,
        max_stake_percentage: float = 0.05,
    ):
        """
        初始化凯利投注策略

        Args:
            kelly_fraction: 凯利分数（风险控制，通常0.25）
            min_stake: 最小投注金额
            max_stake_percentage: 最大投注百分比
        """
        self.kelly_fraction = kelly_fraction
        self.min_stake = min_stake
        self.max_stake_percentage = max_stake_percentage

    def calculate_stake(
        self,
        bankroll: float,
        predicted_proba: list[float],
        odds: list[float],
        prediction: int,
        **kwargs,
    ) -> float:
        """
        计算凯利投注金额

        Args:
            bankroll: 当前资金
            predicted_proba: 预测概率
            odds: 赔率
            prediction: 预测结果

        Returns:
            投注金额
        """
        prob = predicted_proba[prediction]
        odds_value = odds[prediction]

        # 凯利公式: f = (bp - q) / b
        # 其中: b = 赔率 - 1, p = 胜率, q = 败率 = 1-p
        b = odds_value - 1
        p = prob
        q = 1 - p

        if b <= 0:
            return 0.0  # 赔率小于等于1，不投注

        kelly_fraction = (b * p - q) / b

        # 应用风险控制
        kelly_fraction = max(0, kelly_fraction * self.kelly_fraction)

        # 如果期望值为负，不投注
        if kelly_fraction <= 0:
            return 0.0

        stake = bankroll * kelly_fraction

        # 应用最小和最大限制
        stake = max(stake, self.min_stake)
        stake = min(stake, bankroll * self.max_stake_percentage)

        return stake


class ValueBettingStrategy(StakingStrategy):
    """价值投注策略"""

    def __init__(
        self,
        min_ev_threshold: float = 0.1,
        base_stake: float = 10.0,
        max_stake_percentage: float = 0.05,
    ):
        """
        初始化价值投注策略

        Args:
            min_ev_threshold: 最小期望值阈值
            base_stake: 基础投注金额
            max_stake_percentage: 最大投注百分比
        """
        self.min_ev_threshold = min_ev_threshold
        self.base_stake = base_stake
        self.max_stake_percentage = max_stake_percentage

    def calculate_stake(
        self,
        bankroll: float,
        predicted_proba: list[float],
        odds: list[float],
        prediction: int,
        **kwargs,
    ) -> float:
        """
        计算价值投注金额

        Args:
            bankroll: 当前资金
            predicted_proba: 预测概率
            odds: 赔率
            prediction: 预测结果

        Returns:
            投注金额
        """
        prob = predicted_proba[prediction]
        odds_value = odds[prediction]

        # 计算期望值
        ev = (prob * odds_value) - 1

        if ev < self.min_ev_threshold:
            return 0.0  # 价值不足，不投注

        # 根据价值大小调整投注金额
        stake_multiplier = min(ev / self.min_ev_threshold, 2.0)  # 最多2倍基础投注
        stake = self.base_stake * stake_multiplier

        # 应用资金限制
        stake = min(stake, bankroll * self.max_stake_percentage)

        return stake


class Backtester:
    """足球预测回测器"""

    def __init__(self, initial_bankroll: float = 1000.0, random_seed: int = 42):
        """
        初始化回测器

        Args:
            initial_bankroll: 初始资金
            random_seed: 随机种子（确保可复现性）
        """
        self.initial_bankroll = initial_bankroll
        self.random_seed = random_seed
        self.bets: list[Bet] = []
        self.equity_curve: list[float] = []

        # 设置随机种子
        np.random.seed(random_seed)

    def calculate_expected_value(
        self, predicted_proba: list[float], odds: list[float]
    ) -> list[float]:
        """
        计算期望值

        Args:
            predicted_proba: 预测概率
            odds: 赔率

        Returns:
            每个选项的期望值
        """
        ev_values = []
        for prob, odds_value in zip(predicted_proba, odds, strict=False):
            ev = (prob * odds_value) - 1
            ev_values.append(ev)
        return ev_values

    def should_bet(
        self,
        predicted_proba: list[float],
        odds: list[float],
        strategy: str = "value",
        threshold: float = 0.1,
    ) -> bool:
        """
        判断是否应该下注

        Args:
            predicted_proba: 预测概率
            odds: 赔率
            strategy: 投注策略
            threshold: 阈值

        Returns:
            是否应该下注
        """
        if strategy == "value":
            ev_values = self.calculate_expected_value(predicted_proba, odds)
            max_ev = max(ev_values)
            return max_ev > threshold
        elif strategy == "confidence":
            max_confidence = max(predicted_proba)
            return max_confidence > threshold
        else:
            return True  # 默认都下注

    def get_best_bet(
        self, predicted_proba: list[float], odds: list[float], strategy: str = "ev"
    ) -> tuple[int, float]:
        """
        获取最佳投注选择

        Args:
            predicted_proba: 预测概率
            odds: 赔率
            strategy: 选择策略 ("ev", "prob", "combined")

        Returns:
            (最佳选择索引, 对应值)
        """
        if strategy == "ev":
            ev_values = self.calculate_expected_value(predicted_proba, odds)
            best_idx = np.argmax(ev_values)
            return best_idx, ev_values[best_idx]
        elif strategy == "prob":
            best_idx = np.argmax(predicted_proba)
            return best_idx, predicted_proba[best_idx]
        elif strategy == "combined":
            ev_values = self.calculate_expected_value(predicted_proba, odds)
            # 组合概率和期望值
            combined_scores = [
                p * max(0, ev)
                for p, ev in zip(predicted_proba, ev_values, strict=False)
            ]
            best_idx = np.argmax(combined_scores)
            return best_idx, combined_scores[best_idx]
        else:
            best_idx = np.argmax(predicted_proba)
            return best_idx, predicted_proba[best_idx]

    def simulate_bet(
        self,
        match_id: str,
        date: str,
        predicted_proba: list[float],
        odds: list[float],
        actual_result: int,
        stake_strategy: StakingStrategy,
        bet_selection_strategy: str = "ev",
        bankroll: float = None,
    ) -> Optional[Bet]:
        """
        模拟单笔投注

        Args:
            match_id: 比赛ID
            date: 比赛日期
            predicted_proba: 预测概率
            odds: 赔率
            actual_result: 实际结果
            stake_strategy: 投注策略
            bet_selection_strategy: 投注选择策略
            bankroll: 当前资金

        Returns:
            投注记录
        """
        if bankroll is None:
            bankroll = self.initial_bankroll if not self.bets else self.equity_curve[-1]

        # 判断是否应该下注
        if not self.should_bet(predicted_proba, odds):
            return None

        # 选择最佳投注选项
        prediction, selection_value = self.get_best_bet(
            predicted_proba, odds, bet_selection_strategy
        )

        # 计算投注金额
        stake_kwargs = {
            "bankroll": bankroll,
            "predicted_proba": predicted_proba,
            "odds": odds,
            "prediction": prediction,
        }

        stake = stake_strategy.calculate_stake(**stake_kwargs)

        if stake <= 0 or stake > bankroll:
            return None  # 投注金额无效

        # 计算期望值
        ev_values = self.calculate_expected_value(predicted_proba, odds)
        ev = ev_values[prediction]

        # 判断是否获胜
        won = prediction == actual_result

        # 计算收益
        if won:
            winnings = stake * odds[prediction]
            profit = winnings - stake
        else:
            profit = -stake

        # 计算置信度
        confidence = max(predicted_proba)

        # 创建投注记录
        bet = Bet(
            match_id=match_id,
            date=date,
            prediction=prediction,
            predicted_proba=predicted_proba,
            odds=odds,
            stake=stake,
            bet_type=BetType(["H", "D", "A"][prediction]),
            actual_result=actual_result,
            won=won,
            profit=profit,
            ev=ev,
            confidence=confidence,
        )

        return bet

    def simulate(
        self,
        predictions: pd.DataFrame,
        odds: pd.DataFrame,
        stake_strategy: StakingStrategy,
        bet_selection_strategy: str = "ev",
        min_confidence: float = 0.5,
        min_odds: float = 1.5,
        max_odds: float = 10.0,
    ) -> BacktestResult:
        """
        执行回测模拟

        Args:
            predictions: 预测结果DataFrame (包含prob_H, prob_D, prob_A, predicted_class)
            odds: 赔率DataFrame (包含odds_H, odds_D, odds_A)
            stake_strategy: 投注策略
            bet_selection_strategy: 投注选择策略
            min_confidence: 最小置信度
            min_odds: 最小赔率
            max_odds: 最大赔率

        Returns:
            回测结果
        """
        # 重置状态
        self.bets = []
        self.equity_curve = [self.initial_bankroll]

        current_bankroll = self.initial_bankroll

        # 确保数据对齐
        common_matches = list(set(predictions.index) & set(odds.index))
        predictions = predictions.loc[common_matches]
        odds = odds.loc[common_matches]

        logger.info(f"Starting backtest with {len(common_matches)} matches")

        for i, (match_id, pred_row) in enumerate(predictions.iterrows()):
            if match_id not in odds.index:
                continue

            odds_row = odds.loc[match_id]

            try:
                # 提取预测概率
                predicted_proba = [
                    pred_row.get("prob_H", pred_row.get("prob_0", 0)),
                    pred_row.get("prob_D", pred_row.get("prob_1", 0)),
                    pred_row.get("prob_A", pred_row.get("prob_2", 0)),
                ]

                # 提取赔率
                match_odds = [
                    odds_row.get("odds_H", odds_row.get("odds_0", 1.0)),
                    odds_row.get("odds_D", odds_row.get("odds_1", 1.0)),
                    odds_row.get("odds_A", odds_row.get("odds_2", 1.0)),
                ]

                # 检查赔率范围
                if any(odd < min_odds or odd > max_odds for odd in match_odds):
                    continue

                # 检查置信度
                confidence = max(predicted_proba)
                if confidence < min_confidence:
                    continue

                # 获取实际结果（如果有的话）
                actual_result = pred_row.get(
                    "actual_result", pred_row.get("predicted_class", -1)
                )
                if actual_result == -1:
                    continue  # 没有实际结果，跳过

                # 获取比赛日期
                date = pred_row.get(
                    "date", pred_row.get("match_date", f"2024-01-{i+1:02d}")
                )

                # 模拟投注
                bet = self.simulate_bet(
                    match_id=str(match_id),
                    date=date,
                    predicted_proba=predicted_proba,
                    odds=match_odds,
                    actual_result=int(actual_result),
                    stake_strategy=stake_strategy,
                    bet_selection_strategy=bet_selection_strategy,
                    bankroll=current_bankroll,
                )

                if bet:
                    self.bets.append(bet)
                    current_bankroll += bet.profit
                    self.equity_curve.append(current_bankroll)

                    if i % 100 == 0:
                        logger.info(
                            f"Processed {i} matches, current bankroll: {current_bankroll:.2f}"
                        )

            except Exception as e:
                logger.warning(f"Error processing match {match_id}: {e}")
                continue

        # 计算回测结果
        result = self._calculate_backtest_result(stake_strategy)
        logger.info(
            f"Backtest completed. Final bankroll: {result.final_bankroll:.2f}, ROI: {result.roi:.2f}%"
        )

        return result

    def _calculate_backtest_result(
        self, stake_strategy: StakingStrategy
    ) -> BacktestResult:
        """计算回测统计结果"""
        if not self.bets:
            return BacktestResult(
                initial_bankroll=self.initial_bankroll,
                final_bankroll=self.initial_bankroll,
                total_bets=0,
                winning_bets=0,
                losing_bets=0,
                total_stake=0.0,
                total_winnings=0.0,
                net_profit=0.0,
                roi=0.0,
                win_rate=0.0,
                avg_odds=0.0,
                max_consecutive_losses=0,
                max_consecutive_wins=0,
                max_drawdown=0.0,
                max_drawdown_percentage=0.0,
                sharpe_ratio=0.0,
                calmar_ratio=0.0,
                profit_factor=0.0,
                avg_profit_per_bet=0.0,
                std_profit_per_bet=0.0,
                bets=[],
                equity_curve=self.equity_curve,
                metadata={"message": "No bets placed"},
            )

        # 基本统计
        total_bets = len(self.bets)
        winning_bets = sum(1 for bet in self.bets if bet.won)
        losing_bets = total_bets - winning_bets

        total_stake = sum(bet.stake for bet in self.bets)
        total_winnings = sum(
            bet.stake * bet.odds[bet.prediction] for bet in self.bets if bet.won
        )
        net_profit = total_winnings - total_stake

        final_bankroll = self.initial_bankroll + net_profit
        roi = (net_profit / total_stake) * 100 if total_stake > 0 else 0.0
        win_rate = (winning_bets / total_bets) * 100 if total_bets > 0 else 0.0

        # 平均赔率
        avg_odds = np.mean([bet.odds[bet.prediction] for bet in self.bets])

        # 连续统计
        max_consecutive_wins, max_consecutive_losses = (
            self._calculate_consecutive_streaks()
        )

        # 最大回撤
        max_drawdown, max_drawdown_percentage = self._calculate_max_drawdown()

        # 风险指标
        profits = [bet.profit for bet in self.bets]
        avg_profit_per_bet = np.mean(profits)
        std_profit_per_bet = np.std(profits)

        # 夏普比率 (假设无风险利率为0)
        sharpe_ratio = (
            avg_profit_per_bet / std_profit_per_bet if std_profit_per_bet > 0 else 0.0
        )

        # Calmar比率 (年化收益/最大回撤)
        annualized_return = roi * 52  # 假设一年52周
        calmar_ratio = (
            annualized_return / abs(max_drawdown_percentage)
            if max_drawdown_percentage != 0
            else 0.0
        )

        # 盈利因子
        total_wins = sum(bet.profit for bet in self.bets if bet.profit > 0)
        total_losses = abs(sum(bet.profit for bet in self.bets if bet.profit < 0))
        profit_factor = total_wins / total_losses if total_losses > 0 else float("inf")

        return BacktestResult(
            initial_bankroll=self.initial_bankroll,
            final_bankroll=final_bankroll,
            total_bets=total_bets,
            winning_bets=winning_bets,
            losing_bets=losing_bets,
            total_stake=total_stake,
            total_winnings=total_winnings,
            net_profit=net_profit,
            roi=roi,
            win_rate=win_rate,
            avg_odds=avg_odds,
            max_consecutive_losses=max_consecutive_losses,
            max_consecutive_wins=max_consecutive_wins,
            max_drawdown=max_drawdown,
            max_drawdown_percentage=max_drawdown_percentage,
            sharpe_ratio=sharpe_ratio,
            calmar_ratio=calmar_ratio,
            profit_factor=profit_factor,
            avg_profit_per_bet=avg_profit_per_bet,
            std_profit_per_bet=std_profit_per_bet,
            bets=self.bets,
            equity_curve=self.equity_curve,
            metadata={
                "random_seed": self.random_seed,
                "backtest_date": datetime.now().isoformat(),
                "strategy_type": type(stake_strategy).__name__,
            },
        )

    def _calculate_consecutive_streaks(self) -> tuple[int, int]:
        """计算最大连胜和连败次数"""
        if not self.bets:
            return 0, 0

        max_consecutive_wins = 0
        max_consecutive_losses = 0
        current_wins = 0
        current_losses = 0

        for bet in self.bets:
            if bet.won:
                current_wins += 1
                current_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, current_losses)

        return max_consecutive_wins, max_consecutive_losses

    def _calculate_max_drawdown(self) -> tuple[float, float]:
        """计算最大回撤"""
        if len(self.equity_curve) < 2:
            return 0.0, 0.0

        equity_array = np.array(self.equity_curve)
        peak = np.maximum.accumulate(equity_array)
        drawdown = peak - equity_array
        max_drawdown = np.max(drawdown)

        # 计算百分比回撤
        max_drawdown_percentage = (
            (max_drawdown / np.max(equity_array)) * 100
            if np.max(equity_array) > 0
            else 0.0
        )

        return max_drawdown, max_drawdown_percentage

    def save_results(
        self, result: BacktestResult, filepath: Union[str, Path], save_csv: bool = True
    ) -> None:
        """
        保存回测结果

        Args:
            result: 回测结果
            filepath: 保存路径
            save_csv: 是否保存详细CSV
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # 保存JSON结果
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(result.to_json())

        # 保存详细CSV
        if save_csv and result.bets:
            csv_path = filepath.with_suffix(".csv")
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                if result.bets:
                    fieldnames = result.bets[0].to_dict().keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    for bet in result.bets:
                        writer.writerow(bet.to_dict())

            logger.info(f"Backtest results saved to {filepath} and {csv_path}")
        else:
            logger.info(f"Backtest results saved to {filepath}")

    @classmethod
    def load_results(cls, filepath: Union[str, Path]) -> BacktestResult:
        """
        加载回测结果

        Args:
            filepath: 文件路径

        Returns:
            回测结果
        """
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        # 重建Bet对象
        bets = []
        for bet_data in data.get("bets", []):
            bet = Bet(
                match_id=bet_data["match_id"],
                date=bet_data["date"],
                prediction=bet_data["prediction"],
                predicted_proba=bet_data["predicted_proba"],
                odds=bet_data["odds"],
                stake=bet_data["stake"],
                bet_type=BetType(bet_data["bet_type"]),
                actual_result=bet_data["actual_result"],
                won=bet_data["won"],
                profit=bet_data["profit"],
                ev=bet_data["ev"],
                confidence=bet_data["confidence"],
            )
            bets.append(bet)

        return BacktestResult(
            initial_bankroll=data["initial_bankroll"],
            final_bankroll=data["final_bankroll"],
            total_bets=data["total_bets"],
            winning_bets=data["winning_bets"],
            losing_bets=data["losing_bets"],
            total_stake=data["total_stake"],
            total_winnings=data["total_winnings"],
            net_profit=data["net_profit"],
            roi=data["roi"],
            win_rate=data["win_rate"],
            avg_odds=data["avg_odds"],
            max_consecutive_losses=data["max_consecutive_losses"],
            max_consecutive_wins=data["max_consecutive_wins"],
            max_drawdown=data["max_drawdown"],
            max_drawdown_percentage=data["max_drawdown_percentage"],
            sharpe_ratio=data["sharpe_ratio"],
            calmar_ratio=data["calmar_ratio"],
            profit_factor=data["profit_factor"],
            avg_profit_per_bet=data["avg_profit_per_bet"],
            std_profit_per_bet=data["std_profit_per_bet"],
            bets=bets,
            equity_curve=data["equity_curve"],
            metadata=data["metadata"],
        )


# 便捷函数
def run_backtest(
    predictions_file: Union[str, Path],
    odds_file: Union[str, Path],
    stake_strategy: str = "flat",
    initial_bankroll: float = 1000.0,
    **kwargs,
) -> BacktestResult:
    """
    便捷的回测函数

    Args:
        predictions_file: 预测结果文件路径
        odds_file: 赔率文件路径
        stake_strategy: 投注策略类型
        initial_bankroll: 初始资金
        **kwargs: 其他参数

    Returns:
        回测结果
    """
    # 加载数据
    predictions = pd.read_csv(predictions_file, index_col=0)
    odds = pd.read_csv(odds_file, index_col=0)

    # 创建投注策略
    if stake_strategy == "flat":
        strategy = FlatStakingStrategy(stake_amount=kwargs.get("stake_amount", 10.0))
    elif stake_strategy == "percentage":
        strategy = PercentageStakingStrategy(percentage=kwargs.get("percentage", 0.01))
    elif stake_strategy == "kelly":
        strategy = KellyStakingStrategy(
            kelly_fraction=kwargs.get("kelly_fraction", 0.25),
            min_stake=kwargs.get("min_stake", 1.0),
            max_stake_percentage=kwargs.get("max_stake_percentage", 0.05),
        )
    elif stake_strategy == "value":
        strategy = ValueBettingStrategy(
            min_ev_threshold=kwargs.get("min_ev_threshold", 0.1),
            base_stake=kwargs.get("base_stake", 10.0),
            max_stake_percentage=kwargs.get("max_stake_percentage", 0.05),
        )
    else:
        raise ValueError(f"Unknown staking strategy: {stake_strategy}")

    # 创建回测器并运行
    backtester = Backtester(initial_bankroll=initial_bankroll)
    result = backtester.simulate(
        predictions=predictions, odds=odds, stake_strategy=strategy, **kwargs
    )

    return result
