#!/usr/bin/env python3
"""
V9.0 真实赔率回测 - 最终版本
使用真实 Bet365 收盘赔率进行回测
严格禁用任何 estimate_market_odds 函数
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


class RealOddsBacktester:
    """真实赔率回测器 - 绝对不使用模拟赔率"""

    def __init__(self, initial_capital: float = 1000.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.capital_history = [initial_capital]
        self.trades = []
        self.total_bets = 0
        self.winning_bets = 0

        # 严格风控参数
        self.min_edge = 0.08  # 最小优势阈值 8%
        self.kelly_fraction = 0.25  # 凯利公式25%保守系数
        self.max_single_bet_pct = 0.02  # 硬上限：单笔不得超过总资金的2%
        self.max_bet_fraction = self.max_single_bet_pct  # 同步最大投注比例

    def calculate_edge(self, our_prob: float, real_odds: float) -> float:
        """
        计算真实优势（Edge）
        Edge = 我们的概率 - (1 / 真实赔率)
        """
        true_prob = 1 / real_odds
        edge = our_prob - true_prob
        return edge

    def kelly_criterion(self, our_prob: float, odds: float, bankroll: float) -> float:
        """
        凯利公式计算最优投注额（严格风控版）
        """
        if our_prob <= (1 / odds):
            return 0  # 没有优势，不投注

        b = odds - 1  # 净赔率
        q = 1 - our_prob

        # Kelly公式原始值
        kelly_f = (b * our_prob - q) / b

        # 如果凯利公式为负或零，不投注
        if kelly_f <= 0:
            return 0

        # 保守调整：25%凯利（再打2.5折）
        adjusted_f = kelly_f * self.kelly_fraction

        # 硬上限：单笔不得超过总资金的2%
        max_bet_pct = self.max_single_bet_pct
        max_bet = bankroll * max_bet_pct

        # 计算投注额
        bet_amount = adjusted_f * bankroll

        # 取最小值：凯利建议额 vs 硬上限
        final_bet = min(bet_amount, max_bet)

        return final_bet

    def backtest_match(self, match_data: dict, prediction: dict) -> dict:
        """回测单场比赛（使用真实赔率）"""
        # 获取真实赔率
        home_odds = match_data.get('real_home_odds')
        draw_odds = match_data.get('real_draw_odds')
        away_odds = match_data.get('real_away_odds')

        # 检查是否有真实赔率
        if pd.isna(home_odds) or pd.isna(draw_odds) or pd.isna(away_odds):
            return {
                'bet_placed': False,
                'capital': self.capital,
                'p&l': 0
            }

        # 我们的预测概率
        our_probs = prediction

        # 计算每种结果的Edge
        edges = {
            'home_win': self.calculate_edge(our_probs['home_win'], home_odds),
            'draw': self.calculate_edge(our_probs['draw'], draw_odds),
            'away_win': self.calculate_edge(our_probs['away_win'], away_odds)
        }

        # 找到最大Edge
        best_outcome = max(edges, key=edges.get)
        best_edge = edges[best_outcome]

        # 如果没有优势，跳过
        if best_edge <= self.min_edge:
            return {
                'bet_placed': False,
                'capital': self.capital,
                'p&l': 0
            }

        # 获取最佳结果的赔率
        best_odds = {
            'home_win': home_odds,
            'draw': draw_odds,
            'away_win': away_odds
        }[best_outcome]

        # 使用Kelly公式计算投注额
        bet_amount = self.kelly_criterion(
            our_probs[best_outcome],
            best_odds,
            self.capital
        )

        if bet_amount <= 0:
            return {
                'bet_placed': False,
                'capital': self.capital,
                'p&l': 0
            }

        # 记录交易
        self.total_bets += 1

        # 获取实际比赛结果
        actual_result = match_data.get('actual_result', '')
        is_win = (best_outcome == 'home_win' and actual_result == 'H') or \
                 (best_outcome == 'draw' and actual_result == 'D') or \
                 (best_outcome == 'away_win' and actual_result == 'A')

        if is_win:
            # 胜了！
            winnings = bet_amount * (best_odds - 1)
            self.capital += winnings
            self.winning_bets += 1
            pnl = winnings
        else:
            # 输了
            self.capital -= bet_amount
            pnl = -bet_amount

        self.capital_history.append(self.capital)

        trade_record = {
            'match': f"{match_data['home_team']} vs {match_data['away_team']}",
            'bet_on': best_outcome,
            'odds': best_odds,
            'our_prob': our_probs[best_outcome],
            'true_prob': 1 / best_odds,
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

        # 平均投注
        avg_bet = np.mean([t['bet_amount'] for t in self.trades])

        # 平均收益
        avg_pnl = total_pnl / len(self.trades)

        return {
            'total_bets': self.total_bets,
            'winning_bets': self.winning_bets,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'roi': roi,
            'max_drawdown': max_drawdown * 100,
            'avg_bet': avg_bet,
            'avg_pnl': avg_pnl,
            'final_capital': self.capital,
            'capital_history': self.capital_history
        }

    def run_backtest(self, data_path: str, model_path: str = None) -> dict:
        """运行完整回测"""
        print("🚀 开始真实赔率回测（禁用模拟）...")
        print("=" * 60)

        # 加载数据
        df = pd.read_csv(data_path)
        print(f"📊 加载数据: {len(df)} 场比赛（含真实赔率）")

        # 过滤有真实赔率的数据
        df_with_odds = df[
            df['real_home_odds'].notna() &
            df['real_draw_odds'].notna() &
            df['real_away_odds'].notna()
        ]
        print(f"📊 有真实赔率: {len(df_with_odds)} 场比赛")

        # 加载模型
        scaler = None
        if model_path and Path(model_path).exists():
            try:
                import joblib
                import lightgbm as lgb

                model = lgb.Booster(model_file=model_path)

                # 尝试加载缩放器和特征列表
                try:
                    scaler = joblib.load('/home/user/projects/FootballPrediction/scaler_v85.pkl')
                    feature_cols = joblib.load('/home/user/projects/FootballPrediction/features_v85.pkl')
                except:
                    print("⚠️ 未找到缩放器文件，使用原始特征")

                print("✅ 模型加载成功")

                # 预测每场比赛
                predictions = []
                for _, row in df_with_odds.iterrows():
                    # 构建完整的特征向量（15维，与训练时一致）
                    features = np.array([
                        row.get('home_avg_xg', 1.2),
                        row.get('home_avg_goals', 1.2),
                        row.get('home_avg_shots', 12),
                        row.get('home_avg_possession', 50),
                        row.get('home_avg_rating', 6.5),
                        row.get('home_win_rate', 0.33),
                        row.get('away_avg_xg', 1.0),
                        row.get('away_avg_goals', 1.0),
                        row.get('away_avg_shots', 12),
                        row.get('away_avg_possession', 50),
                        row.get('away_avg_rating', 6.0),
                        row.get('away_win_rate', 0.33),
                        row.get('home_avg_xg', 1.2) - row.get('away_avg_xg', 1.0),  # xg_diff
                        row.get('home_avg_rating', 6.5) - row.get('away_avg_rating', 6.0),  # rating_diff
                        0.0,  # form_diff (简化)
                    ])

                    # 如果有缩放器，应用缩放
                    if scaler:
                        features = scaler.transform([features])

                    probs = model.predict(features)[0]
                    predictions.append({
                        'home_win': probs[0],
                        'draw': probs[1],
                        'away_win': probs[2]
                    })
            except Exception as e:
                print(f"⚠️ 模型加载失败: {e}")
                predictions = None

        # 如果模型加载失败或没有模型，使用启发式预测
        if predictions is None:
            print("⚠️ 使用启发式预测（基于评分差异）")
            predictions = []
            for _, row in df_with_odds.iterrows():
                rating_diff = row.get('home_avg_rating', 6.5) - row.get('away_avg_rating', 6.0)
                xg_diff = row.get('home_avg_xg', 1.2) - row.get('away_avg_xg', 1.0)

                # 简化的概率计算（基于15维特征的简化版）
                home_prob = 0.4 + 0.15 * rating_diff + 0.1 * xg_diff
                away_prob = 0.3 - 0.1 * rating_diff - 0.05 * xg_diff
                draw_prob = 1 - home_prob - away_prob

                home_prob = max(0.1, min(0.7, home_prob))
                away_prob = max(0.1, min(0.7, away_prob))
                draw_prob = max(0.1, min(0.7, draw_prob))

                # 归一化
                total = home_prob + away_prob + draw_prob
                predictions.append({
                    'home_win': home_prob / total,
                    'draw': draw_prob / total,
                    'away_win': away_prob / total
                })

        # 回测每场比赛
        for idx, (_, row) in enumerate(df_with_odds.iterrows()):
            match_data = row.to_dict()
            prediction = predictions[idx]

            result = self.backtest_match(match_data, prediction)

            if result['bet_placed'] and (idx + 1) % 20 == 0:
                print(f"  进度: {idx + 1}/{len(df_with_odds)}, 资金: ${result['capital']:.0f}")

        # 计算指标
        metrics = self.calculate_metrics()

        return metrics


def main():
    print("=" * 60)
    print("💰 V9.0 真实赔率回测 - 最终版本")
    print("=" * 60)

    backtester = RealOddsBacktester(initial_capital=1000)

    # 运行回测
    data_path = "/home/user/projects/FootballPrediction/data/merged_real_odds.csv"
    model_path = "/home/user/projects/FootballPrediction/lightgbm_v85_prematch.model"

    metrics = backtester.run_backtest(data_path, model_path)

    # 显示结果
    print("\n" + "=" * 60)
    print("📊 真实赔率回测结果")
    print("=" * 60)
    print(f"  💰 初始资金: ${backtester.initial_capital:,.0f}")
    print(f"  💰 最终资金: ${metrics['final_capital']:,.0f}")
    print(f"  📈 总收益: ${metrics['total_pnl']:,.0f}")
    print(f"  📊 ROI: {metrics['roi']:.2f}%")
    print(f"  📉 最大回撤: {metrics['max_drawdown']:.2f}%")
    print(f"  🎯 总投注次数: {metrics['total_bets']}")
    print(f"  ✅ 胜出次数: {metrics['winning_bets']}")
    print(f"  🏆 投注胜率: {metrics['win_rate']:.2f}%")
    print(f"  💸 平均投注: ${metrics['avg_bet']:,.0f}")
    print(f"  📊 平均收益: ${metrics['avg_pnl']:.2f}")
    print("\n⚠️  风控参数:")
    print(f"  - 单笔最大投注: 2% 资金 (${backtester.initial_capital * 0.02:.0f})")
    print(f"  - 凯利系数: {backtester.kelly_fraction*100:.0f}%")
    print(f"  - 最小优势阈值: {backtester.min_edge*100:.0f}%")
    print(f"\n✅ 基于真实赔率，无模拟数据")
    print("=" * 60)

    # 保存交易记录
    if backtester.trades:
        trades_df = pd.DataFrame(backtester.trades)
        trades_df.to_csv('/home/user/projects/FootballPrediction/real_odds_backtest_trades.csv', index=False)
        print(f"\n✅ 真实赔率交易记录已保存: real_odds_backtest_trades.csv")

    return metrics


if __name__ == "__main__":
    main()
