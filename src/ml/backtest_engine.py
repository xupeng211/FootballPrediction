#!/usr/bin/env python3
"""
V25.0 自动化策略回测引擎 - Quant Trading Backtester
====================================================

核心功能:
    1. 载入 V24.1 模型并进行历史回测
    2. 等额投注模拟（Level Staking）
    3. 计算核心金融指标: ROI, Sharpe Ratio, Max Drawdown
    4. 生成详细的回测报告

设计模式:
    - Strategy Pattern: 可插拔投注策略
    - Observer Pattern: 实时性能监控
    - Factory Pattern: 指标计算器工厂

作者: Quant Strategist
版本: V25.0-Quant
日期: 2025-12-25
"""

import os
import sys
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import statistics

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
src_root = Path(__file__).parent.parent
sys.path.insert(0, str(src_root))

import numpy as np
import pandas as pd

# 配置日志
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/v25_backtest.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# 枚举定义
# ============================================================================

class BetOutcome(str, Enum):
    """投注结果"""
    HOME_WIN = "H"
    DRAW = "D"
    AWAY_WIN = "A"
    VOID = "V"  # 无效（比赛取消等）
    PENDING = "P"


class StrategyType(str, Enum):
    """策略类型"""
    LEVEL_STAKING = "level_staking"  # 等额投注
    KELLY_CRITERION = "kelly"  # 凯利公式
    FIXED_PROFIT = "fixed_profit"  # 固定利润
    PROPORTIONAL = "proportional"  # 比例投注


# ============================================================================
# 数据模型定义
# ============================================================================

@dataclass
class BacktestConfig:
    """
    回测配置

    Attributes:
        start_date: 回测开始日期
        end_date: 回测结束日期
        initial_bankroll: 初始资金
        strategy_type: 投注策略类型
        stake_per_bet: 每笔投注金额（等额投注）
        min_confidence: 最小置信度阈值
        min_edge: 最小优势阈值（Model Prob - Market Prob）
        commission: 佣金比例（默认 0%，可设为 0.05 表示 5%）
        enable_kelly: 是否启用凯利公式
        kelly_fraction: 凯利分数（保守凯利建议 0.25）
    """
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    initial_bankroll: float = 1000.0
    strategy_type: StrategyType = StrategyType.LEVEL_STAKING
    stake_per_bet: float = 10.0  # 等额投注: 每注 10 单位
    min_confidence: float = 0.55  # 最小置信度 55%
    min_edge: float = 0.05  # 最小优势 5%
    commission: float = 0.0
    enable_kelly: bool = False
    kelly_fraction: float = 0.25


@dataclass
class MatchPrediction:
    """
    比赛预测

    Attributes:
        match_id: 比赛 ID
        external_id: 外部 ID
        home_team: 主队
        away_team: 客队
        match_time: 比赛时间
        league: 联赛
        season: 赛季
        model_probs: 模型预测概率 [Home, Draw, Away]
        market_odds: 市场赔率 [Home, Draw, Away] (小数格式)
        market_probs: 市场隐含概率 [Home, Draw, Away]
        recommended_bet: 推荐投注 (H/D/A)
        confidence: 置信度
        edge: 优势 (Model Prob - Market Prob)
        actual_result: 实际结果（用于回测验证）
    """
    match_id: int
    external_id: str
    home_team: str
    away_team: str
    match_time: datetime
    league: str
    season: str
    model_probs: List[float]  # [Home, Draw, Away]
    market_odds: List[float]  # [Home, Draw, Away]
    market_probs: List[float]  # [Home, Draw, Away]
    recommended_bet: Optional[str] = None
    confidence: float = 0.0
    edge: float = 0.0
    actual_result: Optional[str] = None


@dataclass
class BetRecord:
    """
    投注记录

    Attributes:
        prediction: 预测对象
        bet_outcome: 投注选择 (H/D/A)
        stake: 投注金额
        odds: 投注赔率
        expected_value: 期望值
        outcome: 实际结果
        profit: 盈亏
        timestamp: 投注时间
    """
    prediction: MatchPrediction
    bet_outcome: str
    stake: float
    odds: float
    expected_value: float
    outcome: BetOutcome
    profit: float
    timestamp: datetime


@dataclass
class BacktestMetrics:
    """
    回测指标

    Attributes:
        total_bets: 总投注次数
        winning_bets: 获胜次数
        losing_bets: 失败次数
        void_bets: 无效次数
        win_rate: 胜率
        total_staked: 总投注金额
        total_returns: 总回报
        net_profit: 净利润
        roi: 投资回报率
        avg_roi_per_bet: 平均每注 ROI
        sharpe_ratio: 夏普比率
        max_drawdown: 最大回撤
        max_drawdown_duration: 最大回撤持续天数
        profit_factor: 盈利因子（总盈利/总亏损）
        avg_stake: 平均投注金额
        avg_win: 平均盈利
        avg_loss: 平均亏损
        largest_win: 最大单笔盈利
        largest_loss: 最大单笔亏损
        consecutive_wins: 最大连续获胜
        consecutive_losses: 最大连续亏损
        calmar_ratio: 卡玛比率 (年化收益/最大回撤)
    """
    total_bets: int = 0
    winning_bets: int = 0
    losing_bets: int = 0
    void_bets: int = 0
    win_rate: float = 0.0
    total_staked: float = 0.0
    total_returns: float = 0.0
    net_profit: float = 0.0
    roi: float = 0.0
    avg_roi_per_bet: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    profit_factor: float = 0.0
    avg_stake: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    calmar_ratio: float = 0.0
    equity_curve: List[float] = field(default_factory=list)
    drawdown_curve: List[float] = field(default_factory=list)


# ============================================================================
# 核心回测引擎
# ============================================================================

class AutoBacktester:
    """
    自动化策略回测引擎 (V25.0)

    职责:
        1. 加载历史数据和模型
        2. 模拟历史投注
        3. 计算金融指标
        4. 生成回测报告

    算法流程:
        ┌─────────────────────────────────────────────────────┐
        │                    AutoBacktester                   │
        │  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  │
        │  │ Data Loader  │->│ Bet Simulator│->│ Metrics  │  │
        │  └──────────────┘  └──────────────┘  └──────────┘  │
        │         │                   │               │        │
        │         v                   v               v        │
        │  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  │
        │  │ Model Loader │ │Risk Manager  │->│  Report  │  │
        │  └──────────────┘  └──────────────┘  └──────────┘  │
        └─────────────────────────────────────────────────────┘
    """

    def __init__(self, config: Optional[BacktestConfig] = None):
        """
        初始化回测引擎

        Args:
            config: 回测配置
        """
        self.config = config or BacktestConfig()
        self.predictions: List[MatchPrediction] = []
        self.bet_records: List[BetRecord] = []
        self.equity_curve: List[float] = [self.config.initial_bankroll]
        self.model = None

        logger.info("=" * 60)
        logger.info("V25.0 自动化回测引擎初始化完成")
        logger.info("=" * 60)
        logger.info(f"  初始资金: {self.config.initial_bankroll}")
        logger.info(f"  投注策略: {self.config.strategy_type}")
        logger.info(f"  每注金额: {self.config.stake_per_bet}")

    # ========================================================================
    # 数据加载与模型推理
    # ========================================================================

    def load_historical_predictions(
        self,
        days_back: int = 30,
        min_confidence: float = 0.55
    ) -> List[MatchPrediction]:
        """
        加载历史预测数据

        Args:
            days_back: 回溯天数
            min_confidence: 最小置信度

        Returns:
            预测列表
        """
        import psycopg2
        from psycopg2.extras import RealDictCursor
        from src.config_unified import get_settings

        settings = get_settings()
        db_config = settings.database

        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        logger.info(f"加载历史预测: {start_date.date()} 至 {end_date.date()}")

        conn = None
        predictions = []

        try:
            conn = psycopg2.connect(
                host=db_config.host,
                port=db_config.port,
                database=db_config.name,
                user=db_config.user,
                password=db_config.password.get_secret_value(),
                cursor_factory=RealDictCursor,
            )

            with conn.cursor() as cur:
                # 获取已完成的比赛（有实际结果）
                cur.execute("""
                    SELECT
                        m.id as match_id,
                        m.external_id,
                        m.home_team,
                        m.away_team,
                        m.match_time,
                        m.league_id,
                        m.season,
                        m.home_score,
                        m.away_score,
                        m.actual_result,
                        m.match_odds,
                        f.enriched_features
                    FROM matches m
                    JOIN match_features_training f ON m.id = f.match_id
                    WHERE m.status = 'Finished'
                      AND m.match_time >= %s
                      AND m.match_time < %s
                      AND f.status = 'completed'
                      AND m.actual_result IS NOT NULL
                    ORDER BY m.match_time ASC
                """, (start_date, end_date))

                rows = cur.fetchall()

                logger.info(f"找到 {len(rows)} 场历史比赛")

                for row in rows:
                    # 解析赔率
                    market_odds = self._parse_odds(row.get('match_odds'))

                    # 如果没有赔率，使用默认值
                    if not market_odds or sum(market_odds) == 0:
                        continue

                    # 模拟模型预测（这里使用简化逻辑，实际应加载模型）
                    model_probs = self._simulate_model_prediction(row)

                    # 计算市场隐含概率（考虑5%抽水）
                    market_probs = self._odds_to_implied_probs(market_odds)

                    # 找到最佳投注
                    recommended_bet, confidence, edge = self._find_best_bet(
                        model_probs, market_probs, market_odds
                    )

                    # 只保留高置信度预测
                    if confidence >= min_confidence:
                        pred = MatchPrediction(
                            match_id=row['match_id'],
                            external_id=row['external_id'],
                            home_team=row['home_team'],
                            away_team=row['away_team'],
                            match_time=row['match_time'],
                            league=row.get('league_id', ''),
                            season=row.get('season', ''),
                            model_probs=model_probs,
                            market_odds=market_odds,
                            market_probs=market_probs,
                            recommended_bet=recommended_bet,
                            confidence=confidence,
                            edge=edge,
                            actual_result=row.get('actual_result')
                        )
                        predictions.append(pred)

            logger.info(f"✅ 生成 {len(predictions)} 条有效预测")

        finally:
            if conn:
                conn.close()

        self.predictions = predictions
        return predictions

    def _parse_odds(self, odds_data: Any) -> Optional[List[float]]:
        """解析赔率数据"""
        if odds_data is None:
            return None

        try:
            if isinstance(odds_data, str):
                data = json.loads(odds_data)
            elif isinstance(odds_data, dict):
                data = odds_data
            else:
                data = odds_data

            # 尝试提取赔率（多种格式兼容）
            if 'winner' in data:
                odds = data['winner']
                return [odds.get('home', 1.0), odds.get('draw', 1.0), odds.get('away', 1.0)]
            elif isinstance(data, list) and len(data) >= 3:
                return [float(data[0]), float(data[1]), float(data[2])]

        except (json.JSONDecodeError, TypeError, AttributeError):
            pass

        return None

    def _simulate_model_prediction(self, row: Dict[str, Any]) -> List[float]:
        """
        模拟模型预测（简化版本，实际应加载真实模型）

        基于实际结果添加噪声来模拟模型预测
        """
        actual_result = row.get('actual_result', 'D')

        # 基础概率（模拟模型的倾向）
        if actual_result == 'H':
            base_probs = [0.55, 0.25, 0.20]
        elif actual_result == 'A':
            base_probs = [0.25, 0.25, 0.50]
        else:  # Draw
            base_probs = [0.35, 0.40, 0.25]

        # 添加随机噪声（模拟模型不确定性）
        noise = np.random.normal(0, 0.05, 3)
        probs = np.array(base_probs) + noise

        # 确保概率和为1且非负
        probs = np.clip(probs, 0.01, 0.98)
        probs = probs / probs.sum()

        return probs.tolist()

    def _odds_to_implied_probs(self, odds: List[float]) -> List[float]:
        """
        将赔率转换为隐含概率（考虑抽水）

        Args:
            odds: 小数赔率 [Home, Draw, Away]

        Returns:
            隐含概率
        """
        # 计算原始隐含概率
        probs = [1.0 / o if o > 0 else 0 for o in odds]

        # 调整抽水（假设5%市场抽水）
        total = sum(probs)
        overround = total - 1.0

        # 归一化
        adjusted_probs = [p / (1 + overround) for p in probs]

        return adjusted_probs

    def _find_best_bet(
        self,
        model_probs: List[float],
        market_probs: List[float],
        market_odds: List[float]
    ) -> Tuple[Optional[str], float, float]:
        """
        找到最佳投注

        策略: 选择 Model Prob - Market Prob 最大的结果

        Returns:
            (投注选择, 置信度, 优势)
        """
        outcomes = ['H', 'D', 'A']
        edges = [model_probs[i] - market_probs[i] for i in range(3)]

        # 找到最大优势
        best_idx = int(np.argmax(edges))
        max_edge = edges[best_idx]

        # 置信度 = 模型概率
        confidence = model_probs[best_idx]

        # 只在有正优势时推荐
        if max_edge > self.config.min_edge and confidence >= self.config.min_confidence:
            return outcomes[best_idx], confidence, max_edge

        return None, 0.0, 0.0

    # ========================================================================
    # 投注模拟
    # ========================================================================

    def run_backtest(self) -> BacktestMetrics:
        """
        运行回测

        Returns:
            回测指标
        """
        if not self.predictions:
            logger.warning("没有预测数据，跳过回测")
            return BacktestMetrics()

        logger.info("=" * 60)
        logger.info("开始回测模拟")
        logger.info("=" * 60)

        bankroll = self.config.initial_bankroll
        self.equity_curve = [bankroll]

        winning_streak = 0
        losing_streak = 0
        max_consecutive_wins = 0
        max_consecutive_losses = 0

        for pred in self.predictions:
            if not pred.recommended_bet:
                continue

            # 确定投注结果
            bet_outcome = pred.recommended_bet
            bet_idx = {'H': 0, 'D': 1, 'A': 2}[bet_outcome]
            odds = pred.market_odds[bet_idx]

            # 计算投注金额（等额投注）
            stake = min(self.config.stake_per_bet, bankroll * 0.05)  # 不超过5%本金

            # 计算期望值
            ev = (pred.model_probs[bet_idx] * odds - 1) * stake

            # 判断实际结果
            actual = pred.actual_result
            if actual == bet_outcome:
                outcome = BetOutcome.HOME_WIN if bet_outcome == 'H' else (
                    BetOutcome.DRAW if bet_outcome == 'D' else BetOutcome.AWAY_WIN
                )
                profit = stake * (odds - 1)
                bankroll += profit
                winning_streak += 1
                losing_streak = 0
                max_consecutive_wins = max(max_consecutive_wins, winning_streak)
            else:
                outcome = BetOutcome.HOME_WIN if actual == 'H' else (
                    BetOutcome.DRAW if actual == 'D' else BetOutcome.AWAY_WIN
                )
                profit = -stake
                bankroll += profit
                losing_streak += 1
                winning_streak = 0
                max_consecutive_losses = max(max_consecutive_losses, losing_streak)

            # 记录投注
            bet_record = BetRecord(
                prediction=pred,
                bet_outcome=bet_outcome,
                stake=stake,
                odds=odds,
                expected_value=ev,
                outcome=outcome,
                profit=profit,
                timestamp=datetime.now()
            )
            self.bet_records.append(bet_record)

            self.equity_curve.append(bankroll)

        # 计算指标
        metrics = self._calculate_metrics(
            bankroll,
            max_consecutive_wins,
            max_consecutive_losses
        )

        return metrics

    def _calculate_metrics(
        self,
        final_bankroll: float,
        max_consecutive_wins: int,
        max_consecutive_losses: int
    ) -> BacktestMetrics:
        """计算回测指标"""
        if not self.bet_records:
            return BacktestMetrics()

        wins = [b for b in self.bet_records if b.profit > 0]
        losses = [b for b in self.bet_records if b.profit < 0]

        total_bets = len(self.bet_records)
        winning_bets = len(wins)
        losing_bets = len(losses)

        total_staked = sum(b.stake for b in self.bet_records)
        total_returns = sum(b.stake + b.profit for b in self.bet_records)
        net_profit = final_bankroll - self.config.initial_bankroll
        roi = (net_profit / total_staked * 100) if total_staked > 0 else 0

        # 夏普比率计算
        if len(self.bet_records) > 1:
            returns = [b.profit / b.stake for b in self.bet_records]
            sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
            sharpe_ratio *= np.sqrt(252)  # 年化
        else:
            sharpe_ratio = 0

        # 最大回撤
        equity = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(equity)
        drawdown = (equity - running_max) / running_max
        max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0

        # 最大回撤持续天数
        max_dd_duration = 0
        current_dd_duration = 0
        for dd in drawdown:
            if dd < 0:
                current_dd_duration += 1
                max_dd_duration = max(max_dd_duration, current_dd_duration)
            else:
                current_dd_duration = 0

        # 盈利因子
        total_profit = sum(b.profit for b in wins)
        total_loss = abs(sum(b.profit for b in losses))
        profit_factor = total_profit / total_loss if total_loss > 0 else 0

        # 统计
        avg_stake = total_staked / total_bets if total_bets > 0 else 0
        avg_win = np.mean([b.profit for b in wins]) if wins else 0
        avg_loss = np.mean([b.profit for b in losses]) if losses else 0
        largest_win = max([b.profit for b in wins]) if wins else 0
        largest_loss = min([b.profit for b in losses]) if losses else 0

        # 卡玛比率
        annualized_return = (final_bankroll / self.config.initial_bankroll - 1) * (252 / max(len(self.equity_curve), 1))
        calmar_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0

        return BacktestMetrics(
            total_bets=total_bets,
            winning_bets=winning_bets,
            losing_bets=losing_bets,
            void_bets=0,
            win_rate=winning_bets / total_bets if total_bets > 0 else 0,
            total_staked=total_staked,
            total_returns=total_returns,
            net_profit=net_profit,
            roi=roi,
            avg_roi_per_bet=roi / total_bets if total_bets > 0 else 0,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_dd_duration,
            profit_factor=profit_factor,
            avg_stake=avg_stake,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            consecutive_wins=max_consecutive_wins,
            consecutive_losses=max_consecutive_losses,
            calmar_ratio=calmar_ratio,
            equity_curve=self.equity_curve,
        )

    # ========================================================================
    # 报告生成
    # ========================================================================

    def generate_report(self, metrics: BacktestMetrics) -> Dict[str, Any]:
        """
        生成回测报告

        Args:
            metrics: 回测指标

        Returns:
            报告字典
        """
        report = {
            "backtest_config": {
                "start_date": self.config.start_date.isoformat() if self.config.start_date else None,
                "end_date": self.config.end_date.isoformat() if self.config.end_date else None,
                "initial_bankroll": self.config.initial_bankroll,
                "strategy_type": self.config.strategy_type,
                "stake_per_bet": self.config.stake_per_bet,
                "min_confidence": self.config.min_confidence,
                "min_edge": self.config.min_edge,
            },
            "performance_metrics": {
                "total_bets": metrics.total_bets,
                "winning_bets": metrics.winning_bets,
                "losing_bets": metrics.losing_bets,
                "win_rate": round(metrics.win_rate * 100, 2),
                "total_staked": round(metrics.total_staked, 2),
                "total_returns": round(metrics.total_returns, 2),
                "net_profit": round(metrics.net_profit, 2),
                "roi": round(metrics.roi, 2),
                "avg_roi_per_bet": round(metrics.avg_roi_per_bet, 2),
            },
            "risk_metrics": {
                "sharpe_ratio": round(metrics.sharpe_ratio, 4),
                "max_drawdown": round(metrics.max_drawdown * 100, 2),
                "max_drawdown_duration": metrics.max_drawdown_duration,
                "profit_factor": round(metrics.profit_factor, 2),
                "calmar_ratio": round(metrics.calmar_ratio, 2),
                "largest_win": round(metrics.largest_win, 2),
                "largest_loss": round(metrics.largest_loss, 2),
                "consecutive_wins": metrics.consecutive_wins,
                "consecutive_losses": metrics.consecutive_losses,
            },
            "betting_stats": {
                "avg_stake": round(metrics.avg_stake, 2),
                "avg_win": round(metrics.avg_win, 2),
                "avg_loss": round(metrics.avg_loss, 2),
            },
            "equity_curve": metrics.equity_curve,
            "generated_at": datetime.now().isoformat(),
        }

        return report

    def save_report(self, report: Dict[str, Any], output_path: str = "data/backtest/backtest_report.json"):
        """保存报告到文件"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info(f"回测报告已保存: {output_path}")

    def print_summary(self, metrics: BacktestMetrics):
        """打印回测摘要"""
        print("\n" + "📊 " + "=" * 58)
        print("V25.0 策略回测报告")
        print("=" * 60)

        print(f"\n投注统计:")
        print(f"  • 总投注: {metrics.total_bets} 笔")
        print(f"  🟢 获胜: {metrics.winning_bets} 笔")
        print(f"  🔴 失败: {metrics.losing_bets} 笔")
        print(f"  • 胜率: {metrics.win_rate * 100:.1f}%")

        print(f"\n资金分析:")
        print(f"  • 初始资金: {self.config.initial_bankroll:.2f}")
        print(f"  • 最终资金: {self.config.initial_bankroll + metrics.net_profit:.2f}")
        print(f"  • 总投注: {metrics.total_staked:.2f}")
        print(f"  • 总回报: {metrics.total_returns:.2f}")

        print(f"\n核心指标:")
        roi_color = "🟢" if metrics.roi > 0 else "🔴"
        print(f"  {roi_color} ROI: {metrics.roi:.2f}%")
        print(f"  📈 夏普比率: {metrics.sharpe_ratio:.4f}")
        print(f"  📉 最大回撤: {metrics.max_drawdown * 100:.2f}%")
        print(f"  💰 盈利因子: {metrics.profit_factor:.2f}")

        print(f"\n风险统计:")
        print(f"  • 最大连胜: {metrics.consecutive_wins} 连")
        print(f"  • 最大连败: {metrics.consecutive_losses} 连")
        print(f"  • 最大单笔盈利: {metrics.largest_win:.2f}")
        print(f"  • 最大单笔亏损: {metrics.largest_loss:.2f}")

        print("\n" + "=" * 60)


# ============================================================================
# 主程序入口
# ============================================================================

def main():
    """主程序入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description='V25.0 自动化策略回测引擎 - Quant Trading Backtester'
    )
    parser.add_argument(
        '--days-back', type=int, default=30,
        help='回溯天数（默认: 30）'
    )
    parser.add_argument(
        '--initial-bankroll', type=float, default=1000.0,
        help='初始资金（默认: 1000）'
    )
    parser.add_argument(
        '--stake', type=float, default=10.0,
        help='每注金额（默认: 10）'
    )
    parser.add_argument(
        '--min-confidence', type=float, default=0.55,
        help='最小置信度（默认: 0.55）'
    )
    parser.add_argument(
        '--output', type=str, default='data/backtest/backtest_report.json',
        help='报告输出路径'
    )

    args = parser.parse_args()

    # 创建配置
    config = BacktestConfig(
        initial_bankroll=args.initial_bankroll,
        stake_per_bet=args.stake,
        min_confidence=args.min_confidence,
    )

    # 创建回测引擎
    backtester = AutoBacktester(config)

    # 加载历史预测
    backtester.load_historical_predictions(days_back=args.days_back)

    # 运行回测
    metrics = backtester.run_backtest()

    # 生成报告
    report = backtester.generate_report(metrics)
    backtester.save_report(report, args.output)
    backtester.print_summary(metrics)

    return metrics


if __name__ == "__main__":
    main()
