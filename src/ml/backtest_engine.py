"""
BacktestEngine - 生产级回测引擎
================================

V4.46.3: 完整回测逻辑实现
- 投注计算 (Flat/Kelly/Fractional Kelly)
- 盈亏统计与 ROI 计算
- Sharpe Ratio 与最大回撤
- 完善的异常处理和日志记录

@module ml.backtest_engine
@version V4.46.3
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime
import logging
import math

# 配置日志
logger = logging.getLogger(__name__)


class BacktestStatus(Enum):
    """回测状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BetResult(Enum):
    """投注结果枚举"""
    WIN = "win"
    LOSS = "loss"
    PUSH = "push"
    PENDING = "pending"


@dataclass
class BacktestConfig:
    """回测配置"""
    name: str = "default"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_bankroll: float = 1000.0
    stake_type: str = "flat"  # flat, kelly, fractional_kelly
    stake_size: float = 10.0  # 固定投注金额 (flat 模式)
    kelly_fraction: float = 0.25  # Kelly 分数 (fractional_kelly 模式)
    min_odds: float = 1.5
    max_odds: float = 10.0
    min_confidence: float = 0.5
    leagues: List[str] = field(default_factory=list)
    model_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "initial_bankroll": self.initial_bankroll,
            "stake_type": self.stake_type,
            "stake_size": self.stake_size,
            "kelly_fraction": self.kelly_fraction,
            "min_odds": self.min_odds,
            "max_odds": self.max_odds,
            "min_confidence": self.min_confidence,
            "leagues": self.leagues,
            "model_ids": self.model_ids,
        }


@dataclass
class BacktestMetrics:
    """回测指标"""
    total_bets: int = 0
    wins: int = 0
    losses: int = 0
    pushes: int = 0
    total_stake: float = 0.0
    total_return: float = 0.0
    profit_loss: float = 0.0
    roi: float = 0.0
    win_rate: float = 0.0
    avg_odds: float = 0.0
    avg_confidence: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    final_bankroll: float = 0.0
    peak_bankroll: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_bets": self.total_bets,
            "wins": self.wins,
            "losses": self.losses,
            "pushes": self.pushes,
            "total_stake": round(self.total_stake, 2),
            "total_return": round(self.total_return, 2),
            "profit_loss": round(self.profit_loss, 2),
            "roi": round(self.roi, 4),
            "win_rate": round(self.win_rate, 4),
            "avg_odds": round(self.avg_odds, 2),
            "avg_confidence": round(self.avg_confidence, 4),
            "max_drawdown": round(self.max_drawdown, 4),
            "sharpe_ratio": round(self.sharpe_ratio, 4),
            "final_bankroll": round(self.final_bankroll, 2),
            "peak_bankroll": round(self.peak_bankroll, 2),
        }


@dataclass
class BetRecord:
    """单次投注记录"""
    match_id: str
    prediction: str  # home, draw, away
    odds: float
    confidence: float
    stake: float
    result: BetResult
    returns: float
    profit: float
    bankroll_after: float
    timestamp: Optional[datetime] = None


class BacktestEngine:
    """
    生产级回测引擎

    功能:
    - 多种投注策略 (Flat/Kelly/Fractional Kelly)
    - 完整盈亏统计
    - Sharpe Ratio 与最大回撤计算
    - 详细的投注记录追踪
    """

    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()
        self.status = BacktestStatus.PENDING
        self.metrics = BacktestMetrics()
        self._results: List[BetRecord] = []
        self._bankroll_history: List[float] = []
        self._returns_history: List[float] = []
        self._current_bankroll = self.config.initial_bankroll
        self._peak_bankroll = self.config.initial_bankroll

        logger.info(f"BacktestEngine 初始化: {self.config.name}")
        logger.debug(f"配置: {self.config.to_dict()}")

    async def run(self, predictions: List[Dict[str, Any]]) -> BacktestMetrics:
        """
        执行回测

        @param predictions: 预测结果列表，每个元素需包含:
            - match_id: 比赛 ID
            - prediction: 预测结果 (home/draw/away)
            - odds: 赔率
            - confidence: 置信度
            - actual_result: 实际结果 (home/draw/away/unknown)
        @returns 回测指标
        """
        self.status = BacktestStatus.RUNNING
        logger.info(f"开始回测: {len(predictions)} 条预测")

        try:
            # 重置状态
            self._reset_state()

            # 过滤有效预测
            valid_predictions = self._filter_predictions(predictions)
            logger.info(f"有效预测: {len(valid_predictions)}/{len(predictions)}")

            if len(valid_predictions) == 0:
                logger.warning("没有有效的预测数据")
                self.status = BacktestStatus.COMPLETED
                return self.metrics

            # 执行投注模拟
            for pred in valid_predictions:
                try:
                    record = self._process_bet(pred)
                    if record:
                        self._results.append(record)
                        self._bankroll_history.append(self._current_bankroll)
                except Exception as e:
                    logger.error(f"处理投注失败 {pred.get('match_id')}: {e}")
                    continue

            # 计算最终指标
            self._calculate_metrics()

            self.status = BacktestStatus.COMPLETED
            logger.info(f"回测完成: {self.metrics.to_dict()}")

            return self.metrics

        except Exception as e:
            self.status = BacktestStatus.FAILED
            logger.error(f"回测失败: {e}")
            raise

    def _reset_state(self) -> None:
        """重置回测状态"""
        self._results = []
        self._bankroll_history = []
        self._returns_history = []
        self._current_bankroll = self.config.initial_bankroll
        self._peak_bankroll = self.config.initial_bankroll
        self.metrics = BacktestMetrics()

    def _filter_predictions(self, predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤符合条件的预测"""
        valid = []

        for pred in predictions:
            # 基础字段检查
            if not all(k in pred for k in ['match_id', 'prediction', 'odds', 'confidence']):
                continue

            # 赔率范围过滤
            odds = pred.get('odds', 0)
            if odds < self.config.min_odds or odds > self.config.max_odds:
                continue

            # 置信度过滤
            confidence = pred.get('confidence', 0)
            if confidence < self.config.min_confidence:
                continue

            # 联赛过滤
            if self.config.leagues:
                league = pred.get('league', '')
                if league and league not in self.config.leagues:
                    continue

            # 模型过滤
            if self.config.model_ids:
                model_id = pred.get('model_id', '')
                if model_id and model_id not in self.config.model_ids:
                    continue

            valid.append(pred)

        return valid

    def _process_bet(self, pred: Dict[str, Any]) -> Optional[BetRecord]:
        """处理单次投注"""
        match_id = pred['match_id']
        prediction = pred['prediction']
        odds = pred['odds']
        confidence = pred['confidence']
        actual_result = pred.get('actual_result', 'unknown')

        # 计算投注金额
        stake = self._calculate_stake(odds, confidence)
        if stake <= 0 or stake > self._current_bankroll:
            return None

        # 判断投注结果
        result = self._determine_result(prediction, actual_result)

        # 计算收益
        if result == BetResult.WIN:
            returns = stake * odds
            profit = returns - stake
        elif result == BetResult.PUSH:
            returns = stake
            profit = 0
        else:  # LOSS
            returns = 0
            profit = -stake

        # 更新资金
        self._current_bankroll += profit
        self._peak_bankroll = max(self._peak_bankroll, self._current_bankroll)

        # 记录收益历史 (用于 Sharpe Ratio)
        return_rate = profit / stake if stake > 0 else 0
        self._returns_history.append(return_rate)

        return BetRecord(
            match_id=match_id,
            prediction=prediction,
            odds=odds,
            confidence=confidence,
            stake=stake,
            result=result,
            returns=returns,
            profit=profit,
            bankroll_after=self._current_bankroll,
            timestamp=datetime.now()
        )

    def _calculate_stake(self, odds: float, confidence: float) -> float:
        """计算投注金额"""
        if self.config.stake_type == "flat":
            return min(self.config.stake_size, self._current_bankroll * 0.1)

        elif self.config.stake_type == "kelly":
            # Kelly Criterion: f* = (bp - q) / b
            # b = odds - 1, p = confidence, q = 1 - confidence
            b = odds - 1
            p = confidence
            q = 1 - confidence
            kelly_fraction = (b * p - q) / b if b > 0 else 0
            kelly_fraction = max(0, min(kelly_fraction, 0.25))  # 限制最大 25%
            return self._current_bankroll * kelly_fraction

        elif self.config.stake_type == "fractional_kelly":
            b = odds - 1
            p = confidence
            q = 1 - confidence
            kelly_fraction = (b * p - q) / b if b > 0 else 0
            kelly_fraction = max(0, min(kelly_fraction * self.config.kelly_fraction, 0.1))
            return self._current_bankroll * kelly_fraction

        return self.config.stake_size

    def _determine_result(self, prediction: str, actual: str) -> BetResult:
        """判断投注结果"""
        if actual == 'unknown' or not actual:
            return BetResult.PENDING

        if actual == prediction:
            return BetResult.WIN
        elif actual in ('push', 'draw') and prediction == 'draw':
            return BetResult.PUSH
        elif actual == 'draw':
            return BetResult.PUSH
        else:
            return BetResult.LOSS

    def _calculate_metrics(self) -> None:
        """计算最终回测指标"""
        if not self._results:
            return

        # 基础统计
        self.metrics.total_bets = len(self._results)
        self.metrics.wins = sum(1 for r in self._results if r.result == BetResult.WIN)
        self.metrics.losses = sum(1 for r in self._results if r.result == BetResult.LOSS)
        self.metrics.pushes = sum(1 for r in self._results if r.result == BetResult.PUSH)

        # 金额统计
        self.metrics.total_stake = sum(r.stake for r in self._results)
        self.metrics.total_return = sum(r.returns for r in self._results)
        self.metrics.profit_loss = self.metrics.total_return - self.metrics.total_stake

        # 比率计算
        if self.metrics.total_stake > 0:
            self.metrics.roi = self.metrics.profit_loss / self.metrics.total_stake

        if self.metrics.total_bets > 0:
            self.metrics.win_rate = self.metrics.wins / self.metrics.total_bets
            self.metrics.avg_odds = sum(r.odds for r in self._results) / self.metrics.total_bets
            self.metrics.avg_confidence = sum(r.confidence for r in self._results) / self.metrics.total_bets

        # 资金统计
        self.metrics.final_bankroll = self._current_bankroll
        self.metrics.peak_bankroll = self._peak_bankroll

        # 最大回撤
        self._calculate_max_drawdown()

        # Sharpe Ratio
        self._calculate_sharpe_ratio()

    def _calculate_max_drawdown(self) -> None:
        """计算最大回撤"""
        if len(self._bankroll_history) < 2:
            self.metrics.max_drawdown = 0
            return

        peak = self._bankroll_history[0]
        max_dd = 0

        for value in self._bankroll_history:
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)

        self.metrics.max_drawdown = max_dd

    def _calculate_sharpe_ratio(self) -> None:
        """计算 Sharpe Ratio (假设无风险利率为 0)"""
        if len(self._returns_history) < 2:
            self.metrics.sharpe_ratio = 0
            return

        returns = self._returns_history
        avg_return = sum(returns) / len(returns)

        # 计算标准差
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = math.sqrt(variance)

        if std_dev > 0:
            self.metrics.sharpe_ratio = avg_return / std_dev
        else:
            self.metrics.sharpe_ratio = 0

    def get_results(self) -> List[Dict[str, Any]]:
        """获取回测结果详情"""
        return [
            {
                "match_id": r.match_id,
                "prediction": r.prediction,
                "odds": r.odds,
                "confidence": r.confidence,
                "stake": r.stake,
                "result": r.result.value,
                "returns": r.returns,
                "profit": r.profit,
                "bankroll_after": r.bankroll_after,
                "timestamp": r.timestamp.isoformat() if r.timestamp else None
            }
            for r in self._results
        ]

    def get_summary(self) -> Dict[str, Any]:
        """获取回测摘要"""
        return {
            "config": self.config.to_dict(),
            "status": self.status.value,
            "metrics": self.metrics.to_dict(),
            "bankroll_history": self._bankroll_history[-100:] if self._bankroll_history else [],
        }


# 便捷函数
def create_backtest_engine(**kwargs) -> BacktestEngine:
    """创建回测引擎实例"""
    config = BacktestConfig(**kwargs)
    return BacktestEngine(config)


__all__ = [
    "BacktestConfig",
    "BacktestEngine",
    "BacktestMetrics",
    "BacktestStatus",
    "BetResult",
    "BetRecord",
    "create_backtest_engine",
]
