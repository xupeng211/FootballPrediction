"""
V36.0 生产级回测引擎 - 价值评估增强版
==========================================

V35.0 → V36.0 核心改进：
- 集成 match_odds 表真实终盘价格
- 增加价值评估 (Value = P × Price - 1)
- 优化盈亏计算逻辑
- 增强性能报告

V35.0 核心功能：
- 模拟实战下注（基于模型概率）
- 盈亏平衡表生成
- 最佳下注阈值优化
- 风险指标计算

作者: V36.0 Architecture Team
日期: 2025-12-30
版本: V36.0 Production
"""

from dataclasses import dataclass
from datetime import datetime
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

from src.config_unified import get_settings

logger = logging.getLogger(__name__)


@dataclass
class BacktestMetrics:
    """回测指标"""

    total_bets: int
    winning_bets: int
    total_stake: float
    total_return: float
    roi_pct: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    avg_odds: float
    profit_per_bet: float
    home_bets: int
    draw_bets: int
    away_bets: int
    home_win_rate: float
    draw_win_rate: float
    away_win_rate: float
    # V36.0 新增指标
    avg_value: float  # 平均价值 (Value = P × Price - 1)
    value_bets_count: int  # 正价值下注次数
    value_hit_rate: float  # 正价值下注命中率
    simulated_profit_pct: float  # 模拟盈亏百分比


@dataclass
class BacktestConfig:
    """回测配置"""

    stake_per_bet: float = 100.0
    min_prob_threshold: float = 0.55
    max_prob_threshold: float = 0.85
    commission_pct: float = 0.0
    KellyCriterion: bool = False
    KellyFraction: float = 0.25  # 保守 Kelly
    # V36.0 新增配置
    use_real_odds: bool = True  # 是否使用真实终盘赔率
    min_value_threshold: float = 0.0  # 最小价值阈值 (Value > 0 才下注)


class BacktestEngine:
    """
    V36.0 生产级回测引擎 - 价值评估增强版

    模拟基于模型预测的下注策略，集成真实终盘赔率进行价值评估
    """

    def __init__(self, config: BacktestConfig | None = None):
        """
        初始化回测引擎

        Args:
            config: 回测配置
        """
        self.config = config or BacktestConfig()
        self._odds_cache: dict[str, dict[str, float]] = {}  # 赔率缓存
        logger.info("V36.0 回测引擎初始化完成")
        logger.info(f"  每注金额: {self.config.stake_per_bet}")
        logger.info(f"  概率阈值: {self.config.min_prob_threshold} - {self.config.max_prob_threshold}")
        logger.info(f"  使用真实赔率: {self.config.use_real_odds}")
        logger.info(f"  最小价值阈值: {self.config.min_value_threshold}")

    def calculate_implied_odds(self, prob_home: float, prob_draw: float, prob_away: float) -> dict[str, float]:
        """
        基于模型概率计算隐含赔率

        Args:
            prob_home: 主胜概率
            prob_draw: 平局概率
            prob_away: 客胜概率

        Returns:
            隐含赔率字典
        """
        # 添加利润率 (通常 5%)
        margin = 0.05
        total_prob = prob_home + prob_draw + prob_away

        # 调整后的概率
        adj_home = prob_home / total_prob * (1 - margin)
        adj_draw = prob_draw / total_prob * (1 - margin)
        adj_away = prob_away / total_prob * (1 - margin)

        # 计算小数赔率
        odds_home = 1.0 / max(adj_home, 0.01)
        odds_draw = 1.0 / max(adj_draw, 0.01)
        odds_away = 1.0 / max(adj_away, 0.01)

        return {
            "home": odds_home,
            "draw": odds_draw,
            "away": odds_away,
        }

    def fetch_closing_odds(self, match_id: str) -> dict[str, float] | None:
        """
        从 match_odds 表获取真实终盘赔率

        Args:
            match_id: 比赛 ID (matches.external_id)

        Returns:
            终盘赔率字典 {"home": float, "draw": float, "away": float}，如果不存在返回 None
        """
        # 检查缓存
        if match_id in self._odds_cache:
            return self._odds_cache[match_id]

        if not self.config.use_real_odds:
            return None

        try:
            settings = get_settings()
            conn = psycopg2.connect(
                host=settings.database.host,
                port=settings.database.port,
                database=settings.database.name,
                user=settings.database.user,
                password=settings.database.password.get_secret_value(),
                cursor_factory=RealDictCursor,
            )
            cursor = conn.cursor()

            # 查询终盘赔率
            query = """
                SELECT home_win_odds, draw_odds, away_win_odds
                FROM match_odds
                WHERE match_id = %s
                  AND is_closing = TRUE
                  AND home_win_odds IS NOT NULL
                  AND draw_odds IS NOT NULL
                  AND away_win_odds IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT 1
            """

            cursor.execute(query, (match_id,))
            result = cursor.fetchone()

            cursor.close()
            conn.close()

            if result:
                odds = {
                    "home": float(result["home_win_odds"]),
                    "draw": float(result["draw_odds"]),
                    "away": float(result["away_win_odds"]),
                }
                # 缓存结果
                self._odds_cache[match_id] = odds
                return odds
            logger.debug(f"未找到终盘赔率: {match_id}")
            return None

        except Exception as e:
            logger.warning(f"获取终盘赔率失败 ({match_id}): {e}")
            return None

    @staticmethod
    def calculate_value(model_prob: float, market_odds: float) -> float:
        """
        计算价值 (Value)

        公式: Value = (Model_Prob × Market_Odds) - 1

        Args:
            model_prob: 模型预测概率
            market_odds: 市场赔率

        Returns:
            价值值 (正数表示有价值下注)
        """
        return (model_prob * market_odds) - 1.0

    def run_backtest(
        self,
        df: pd.DataFrame,
        model_predictions: np.ndarray,
        model_probabilities: np.ndarray,
    ) -> BacktestMetrics:
        """
        执行回测 - V36.0 增强版

        集成真实终盘赔率和价值评估逻辑

        Args:
            df: 测试数据集（必须包含 result 列和 match_id 列）
            model_predictions: 模型预测结果 (0=away, 1=draw, 2=home)
            model_probabilities: 模型预测概率

        Returns:
            回测指标（包含价值评估指标）
        """
        logger.info("=" * 70)
        logger.info("V36.0 回测执行（价值评估增强版）")
        logger.info("=" * 70)

        total_stake = 0.0
        total_return = 0.0
        winning_bets = 0
        losing_bets = 0

        home_bets = draw_bets = away_bets = 0
        home_wins = draw_wins = away_wins = 0

        equity_curve = [self.config.stake_per_bet * 100]  # 初始资金

        # V36.0 新增：价值评估统计
        value_sum = 0.0
        value_bets_count = 0
        value_wins = 0

        for i, (_, row) in enumerate(df.iterrows()):
            if i >= len(model_predictions):
                break

            # 获取预测和概率
            pred = model_predictions[i]
            probs = model_probabilities[i]
            actual = row["result"]
            actual_code = {"away": 0, "draw": 1, "home": 2}[actual]

            # 获取最大概率
            max_prob = np.max(probs)
            pred_class = int(pred)

            # 检查是否满足下注条件
            if max_prob < self.config.min_prob_threshold:
                continue
            if max_prob > self.config.max_prob_threshold:
                continue

            # V36.0: 尝试获取真实终盘赔率
            match_id = row.get("external_id") or row.get("match_id")
            real_odds = None
            if match_id:
                real_odds = self.fetch_closing_odds(match_id)

            # 如果没有真实赔率，使用隐含赔率
            if real_odds:
                odds = real_odds
                logger.debug(f"使用真实赔率: {match_id}")
            else:
                odds = self.calculate_implied_odds(probs[2], probs[1], probs[0])

            pred_odds = odds["home"] if pred_class == 2 else (odds["draw"] if pred_class == 1 else odds["away"])

            # V36.0: 计算价值
            value = self.calculate_value(max_prob, pred_odds)

            # V36.0: 价值阈值过滤
            if value < self.config.min_value_threshold:
                continue

            # 计算下注金额
            if self.config.KellyCriterion:
                # Kelly 公式: f = (bp - q) / b
                # b = 赔率 - 1, p = 胜率, q = 1 - p
                b = pred_odds - 1.0
                p = max_prob
                q = 1.0 - p
                kelly_fraction = (b * p - q) / b
                stake = self.config.stake_per_bet * max(0, min(kelly_fraction, 0.1)) * 4  # 限制最大下注
            else:
                stake = self.config.stake_per_bet

            total_stake += stake

            # 统计下注类型
            if pred_class == 2:
                home_bets += 1
            elif pred_class == 1:
                draw_bets += 1
            else:
                away_bets += 1

            # V36.0: 累计价值统计
            value_sum += value
            value_bets_count += 1

            # 计算收益
            if pred_class == actual_code:
                # 中奖
                winning_bets += 1
                returns = stake * pred_odds * (1 - self.config.commission_pct)
                total_return += returns

                # V36.0: 正价值下注获胜统计
                if value > 0:
                    value_wins += 1

                if pred_class == 2:
                    home_wins += 1
                elif pred_class == 1:
                    draw_wins += 1
                else:
                    away_wins += 1
            else:
                losing_bets += 1

            # 更新资金曲线
            current_equity = (
                equity_curve[-1]
                - stake
                + (stake * pred_odds * (1 - self.config.commission_pct) if pred_class == actual_code else 0)
            )
            equity_curve.append(max(0, current_equity))

        # 计算指标
        total_bets = winning_bets + losing_bets
        profit = total_return - total_stake
        roi_pct = (profit / total_stake * 100) if total_stake > 0 else 0
        win_rate = (winning_bets / total_bets * 100) if total_bets > 0 else 0

        # 计算最大回撤
        max_drawdown = 0.0
        peak = equity_curve[0]
        for equity in equity_curve:
            peak = max(peak, equity)
            drawdown = (peak - equity) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)

        # 计算夏普比率（简化版）
        returns = np.diff(equity_curve)
        sharpe_ratio = (
            np.mean(returns) / np.std(returns) * np.sqrt(252) if len(returns) > 1 and np.std(returns) > 0 else 0
        )

        # V36.0: 计算价值评估指标
        avg_value = value_sum / value_bets_count if value_bets_count > 0 else 0.0
        value_hit_rate = (value_wins / value_bets_count * 100) if value_bets_count > 0 else 0.0
        simulated_profit_pct = roi_pct  # 模拟盈亏百分比 = ROI

        metrics = BacktestMetrics(
            total_bets=total_bets,
            winning_bets=winning_bets,
            total_stake=total_stake,
            total_return=total_return,
            roi_pct=roi_pct,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            avg_odds=total_return / winning_bets if winning_bets > 0 else 0,
            profit_per_bet=profit / total_bets if total_bets > 0 else 0,
            home_bets=home_bets,
            draw_bets=draw_bets,
            away_bets=away_bets,
            home_win_rate=(home_wins / home_bets * 100) if home_bets > 0 else 0,
            draw_win_rate=(draw_wins / draw_bets * 100) if draw_bets > 0 else 0,
            away_win_rate=(away_wins / away_bets * 100) if away_bets > 0 else 0,
            # V36.0 新增指标
            avg_value=avg_value,
            value_bets_count=value_bets_count,
            value_hit_rate=value_hit_rate,
            simulated_profit_pct=simulated_profit_pct,
        )

        self._log_metrics(metrics, equity_curve)

        return metrics

    def _log_metrics(self, metrics: BacktestMetrics, equity_curve: list[float]) -> None:
        """记录回测指标 - V36.0 增强版"""
        logger.info("\n【回测结果】")
        logger.info(f"  总下注次数: {metrics.total_bets}")
        logger.info(f"  获胜次数: {metrics.winning_bets}")
        logger.info(f"  胜率: {metrics.win_rate:.2f}%")
        logger.info(f"  总下注金额: {metrics.total_stake:.2f}")
        logger.info(f"  总回报: {metrics.total_return:.2f}")
        logger.info(f"  净利润: {metrics.total_return - metrics.total_stake:.2f}")
        logger.info(f"  ROI: {metrics.roi_pct:.2f}%")
        logger.info(f"  最大回撤: {metrics.max_drawdown:.2f}%")
        logger.info(f"  夏普比率: {metrics.sharpe_ratio:.2f}")
        logger.info(f"  每注平均利润: {metrics.profit_per_bet:.2f}")

        logger.info("\n【分类别下注】")
        logger.info(f"  主胜下注: {metrics.home_bets} 次 (胜率 {metrics.home_win_rate:.1f}%)")
        logger.info(f"  平局下注: {metrics.draw_bets} 次 (胜率 {metrics.draw_win_rate:.1f}%)")
        logger.info(f"  客胜下注: {metrics.away_bets} 次 (胜率 {metrics.away_win_rate:.1f}%)")

        # V36.0 新增：价值评估指标
        logger.info("\n【价值评估 (V36.0)】")
        logger.info(f"  平均价值 (Avg Value): {metrics.avg_value:.4f}")
        logger.info(f"  正价值下注次数: {metrics.value_bets_count}")
        logger.info(f"  正价值下注命中率: {metrics.value_hit_rate:.2f}%")
        logger.info(f"  模拟盈亏百分比: {metrics.simulated_profit_pct:.2f}%")

        logger.info("\n【最终评价】")
        if metrics.roi_pct > 5:
            logger.info("  ✓✓ 优秀 (ROI > 5%)")
        elif metrics.roi_pct > 0:
            logger.info("  ✓ 盈利 (ROI > 0%)")
        else:
            logger.info("  ✗ 亏损")

        if metrics.max_drawdown < 20:
            logger.info("  ✓ 风险可控 (最大回撤 < 20%)")
        else:
            logger.info("  ⚠ 风险较高 (最大回撤 >= 20%)")

        # V36.0 新增：价值评估
        if metrics.avg_value > 0.05:
            logger.info("  ✓✓ 价值显著 (Avg Value > 5%)")
        elif metrics.avg_value > 0:
            logger.info("  ✓ 正价值 (Avg Value > 0)")
        else:
            logger.info("  ✗ 负价值")

    def save_report(self, metrics: BacktestMetrics, output_path: Path | None = None) -> Path:
        """保存回测报告 - V36.0"""
        if output_path is None:
            output_path = Path(__file__).parent.parent.parent / "reports/v36_backtest"

        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = output_path / f"v36_backtest_report_{timestamp}.json"

        from dataclasses import asdict

        report = asdict(metrics)
        report["timestamp"] = datetime.now().isoformat()
        report["version"] = "V36.0"

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ 回测报告已保存: {report_path}")
        return report_path


def create_backtest_engine(config: BacktestConfig | None = None) -> BacktestEngine:
    """工厂函数：创建回测引擎实例"""
    return BacktestEngine(config=config)


# 导出
__all__ = [
    "BacktestConfig",
    "BacktestEngine",
    "BacktestMetrics",
    "create_backtest_engine",
]
