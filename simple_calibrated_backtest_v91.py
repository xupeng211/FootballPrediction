#!/usr/bin/env python3
"""
V9.1 简化校准回测器 - 直接应用 Platt Scaling 和去水逻辑
不依赖 181 维特征，使用启发式预测 + 校准 + 去水
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

from src.ml.probability_calibrator import MarginRemoval


class SimpleCalibratedBacktester:
    """简化校准回测器"""

    def __init__(self, initial_capital: float = 1000.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.capital_history = [initial_capital]
        self.trades = []
        self.total_bets = 0
        self.winning_bets = 0

        # 风控参数
        self.min_edge = 0.05
        self.kelly_fraction = 0.25
        self.max_single_bet_pct = 0.02
        self.confidence_threshold = 0.05
        self.margin_rate = 0.033  # 3.3% 庄家抽水

        # 去水器
        self.margin_remover = MarginRemoval(margin_rate=self.margin_rate)

    def apply_platt_scaling(self, raw_prob: float) -> float:
        """
        简化的 Platt Scaling 校准
        使用 sigmoid 函数校准概率

        Args:
            raw_prob: 原始预测概率

        Returns:
            校准后概率
        """
        # Platt Scaling 参数 (基于校准经验)
        # 这些参数应该通过验证集学习得到，这里使用经验值
        a = 2.0  # 斜率参数
        b = -1.0  # 截距参数

        # Sigmoid 函数
        scaled_prob = 1.0 / (1.0 + np.exp(a * (raw_prob - 0.5) + b))

        return scaled_prob

    def calculate_fair_probability(self, odds: float) -> float:
        """计算公平概率 (移除抽水)"""
        return self.margin_remover.calculate_fair_probability(odds)

    def calculate_sharpe_edge(self, model_prob: float, fair_prob: float) -> tuple:
        """计算 Sharpe-adjusted Edge"""
        return self.margin_remover.calculate_sharpe_edge(
            model_prob, fair_prob, self.confidence_threshold
        )

    def calculate_kelly_bet(self, model_prob: float, odds: float, edge: float) -> float:
        """计算凯利投注额"""
        return self.margin_remover.calculate_kelly_bet(
            model_prob, odds, self.capital, edge, self.kelly_fraction
        )

    def predict_match_probabilities(self, match_data: dict) -> dict:
        """
        预测比赛概率 (启发式 + 校准)

        Args:
            match_data: 比赛数据

        Returns:
            三种结果的校准概率
        """
        # 基础特征
        rating_diff = match_data.get('home_avg_rating', 6.5) - match_data.get('away_avg_rating', 6.0)
        xg_diff = match_data.get('home_avg_xg', 1.2) - match_data.get('away_avg_xg', 1.0)
        home_poss = match_data.get('home_avg_possession', 50)
        away_poss = match_data.get('away_avg_possession', 50)

        # 原始概率 (启发式)
        raw_home = 0.4 + 0.12 * rating_diff + 0.08 * xg_diff + 0.003 * (home_poss - 50)
        raw_away = 0.35 - 0.10 * rating_diff - 0.06 * xg_diff - 0.003 * (away_poss - 50)
        raw_draw = 0.25 + np.random.normal(0, 0.05)  # 平局概率有随机性

        # 边界处理
        raw_home = max(0.1, min(0.8, raw_home))
        raw_away = max(0.1, min(0.8, raw_away))
        raw_draw = max(0.1, min(0.6, raw_draw))

        # 归一化
        total = raw_home + raw_away + raw_draw
        raw_home /= total
        raw_away /= total
        raw_draw /= total

        # 应用 Platt Scaling
        calibrated_home = self.apply_platt_scaling(raw_home)
        calibrated_away = self.apply_platt_scaling(raw_away)
        calibrated_draw = self.apply_platt_scaling(raw_draw)

        # 再次归一化
        total_cal = calibrated_home + calibrated_away + calibrated_draw
        calibrated_home /= total_cal
        calibrated_away /= total_cal
        calibrated_draw /= total_cal

        return {
            'home_win': calibrated_home,
            'draw': calibrated_draw,
            'away_win': calibrated_away,
            'raw_home': raw_home,
            'raw_away': raw_away,
            'raw_draw': raw_draw
        }

    def backtest_match(self, match_data: dict, prediction: dict) -> dict:
        """回测单场比赛"""
        # 获取真实赔率
        home_odds = match_data.get('real_home_odds')
        draw_odds = match_data.get('real_draw_odds')
        away_odds = match_data.get('real_away_odds')

        if pd.isna(home_odds) or pd.isna(draw_odds) or pd.isna(away_odds):
            return {
                'bet_placed': False,
                'capital': self.capital,
                'p&l': 0
            }

        # 计算每种结果的公平 Edge
        edges = {}
        is_bets = {}

        outcomes = ['home_win', 'draw', 'away_win']
        odds_dict = {'home_win': home_odds, 'draw': draw_odds, 'away_win': away_odds}

        for outcome in outcomes:
            model_prob = prediction[outcome]
            market_odds = odds_dict[outcome]

            # 计算公平概率
            fair_prob = self.calculate_fair_probability(market_odds)

            # 计算调整后 Edge
            adjusted_edge, is_bet = self.calculate_sharpe_edge(model_prob, fair_prob)

            edges[outcome] = adjusted_edge
            is_bets[outcome] = is_bet

        # 找到最佳投注机会
        best_outcome = None
        best_edge = -999

        for outcome in edges:
            if is_bets[outcome] and edges[outcome] > best_edge:
                best_edge = edges[outcome]
                best_outcome = outcome

        # 如果没有优势，跳过
        if best_outcome is None:
            return {
                'bet_placed': False,
                'capital': self.capital,
                'p&l': 0
            }

        # 获取最佳结果的参数
        best_odds = odds_dict[best_outcome]
        best_prob = prediction[best_outcome]
        fair_prob = self.calculate_fair_probability(best_odds)

        # 计算投注额
        bet_amount = self.calculate_kelly_bet(best_prob, best_odds, best_edge)

        if bet_amount <= 0:
            return {
                'bet_placed': False,
                'capital': self.capital,
                'p&l': 0
            }

        # 记录交易
        self.total_bets += 1

        # 获取实际结果
        actual_result = match_data.get('actual_result', '')
        is_win = (best_outcome == 'home_win' and actual_result == 'H') or \
                 (best_outcome == 'draw' and actual_result == 'D') or \
                 (best_outcome == 'away_win' and actual_result == 'A')

        if is_win:
            winnings = bet_amount * (best_odds - 1)
            self.capital += winnings
            self.winning_bets += 1
            pnl = winnings
        else:
            self.capital -= bet_amount
            pnl = -bet_amount

        self.capital_history.append(self.capital)

        # 记录交易详情
        trade_record = {
            'match': f"{match_data['home_team']} vs {match_data['away_team']}",
            'bet_on': best_outcome,
            'odds': best_odds,
            'model_prob': best_prob,
            'raw_prob': prediction.get(f'raw_{best_outcome.split("_")[0]}', best_prob),
            'fair_prob': fair_prob,
            'edge': best_edge,
            'bet_amount': bet_amount,
            'result': 'WIN' if is_win else 'LOSS',
            'p&l': pnl,
            'capital_after': self.capital
        }

        self.trades.append(trade_record)

        return {
            'bet_placed': True,
            'capital': self.capital,
            'p&l': pnl,
            'trade': trade_record
        }

    def run_backtest(self, data_path: str) -> dict:
        """运行完整回测"""
        print("\n" + "=" * 60)
        print("🚀 V9.1 简化校准后回测")
        print("=" * 60)

        # 加载数据
        df = pd.read_csv(data_path)
        print(f"\n📊 加载数据: {len(df)} 场比赛")

        # 过滤有真实赔率的数据
        df_with_odds = df[
            df['real_home_odds'].notna() &
            df['real_draw_odds'].notna() &
            df['real_away_odds'].notna()
        ]
        print(f"  有真实赔率: {len(df_with_odds)} 场比赛")

        # 回测每场比赛
        print(f"\n🎯 开始回测...")
        for idx, (_, row) in enumerate(df_with_odds.iterrows()):
            match_data = row.to_dict()
            prediction = self.predict_match_probabilities(match_data)

            result = self.backtest_match(match_data, prediction)

            if result['bet_placed'] and (idx + 1) % 20 == 0:
                print(f"  进度: {idx + 1}/{len(df_with_odds)}, 资金: ${result['capital']:.0f}")

        # 计算指标
        metrics = self.calculate_metrics()

        return metrics

    def calculate_metrics(self) -> dict:
        """计算回测指标"""
        if not self.trades:
            return {}

        total_pnl = self.capital - self.initial_capital
        roi = (total_pnl / self.initial_capital) * 100

        # 最大回撤
        peak = self.initial_capital
        max_drawdown = 0
        for capital in self.capital_history:
            if capital > peak:
                peak = capital
            drawdown = (peak - capital) / peak
            max_drawdown = max(max_drawdown, drawdown)

        # 胜率
        win_rate = (self.winning_bets / self.total_bets) * 100 if self.total_bets > 0 else 0

        return {
            'total_bets': self.total_bets,
            'winning_bets': self.winning_bets,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'roi': roi,
            'max_drawdown': max_drawdown * 100,
            'final_capital': self.capital,
            'capital_history': self.capital_history
        }


def main():
    """主函数"""
    print("=" * 60)
    print("💰 V9.1 简化校准回测系统")
    print("=" * 60)

    backtester = SimpleCalibratedBacktester(initial_capital=1000)

    # 运行回测
    data_path = "/home/user/projects/FootballPrediction/data/merged_real_odds.csv"
    metrics = backtester.run_backtest(data_path)

    # 显示结果
    print("\n" + "=" * 60)
    print("📊 V9.1 简化校准回测结果")
    print("=" * 60)
    print(f"  💰 初始资金: ${backtester.initial_capital:,.0f}")
    print(f"  💰 最终资金: ${metrics['final_capital']:,.0f}")
    print(f"  📈 总收益: ${metrics['total_pnl']:,.0f}")
    print(f"  📊 ROI: {metrics['roi']:.2f}%")
    print(f"  📉 最大回撤: {metrics['max_drawdown']:.2f}%")
    print(f"  🎯 总投注次数: {metrics['total_bets']}")
    print(f"  ✅ 胜出次数: {metrics['winning_bets']}")
    print(f"  🏆 投注胜率: {metrics['win_rate']:.2f}%")

    # 对比 V9.0
    print("\n" + "=" * 60)
    print("📈 V9.0 vs V9.1 对比")
    print("=" * 60)
    v90_roi = -32.58
    print(f"  V9.0 ROI: {v90_roi:.2f}%")
    print(f"  V9.1 ROI: {metrics['roi']:.2f}%")
    improvement = metrics['roi'] - v90_roi
    print(f"  改进幅度: {improvement:.2f}%")
    print(f"  是否盈利: {'✅ 是' if metrics['roi'] > 0 else '❌ 否'}")

    if metrics['roi'] > 0:
        print(f"\n🎉 校准成功！从亏损 {v90_roi:.2f}% 转为盈利 {metrics['roi']:.2f}%")

    # 保存交易记录
    if backtester.trades:
        trades_df = pd.DataFrame(backtester.trades)
        trades_df.to_csv('/home/user/projects/FootballPrediction/simple_calibrated_trades_v91.csv', index=False)
        print(f"\n✅ 简化校准交易记录已保存: simple_calibrated_trades_v91.csv")

    return metrics


if __name__ == "__main__":
    main()
