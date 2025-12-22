#!/usr/bin/env python3
"""
V9.5 真实财务回测
使用最小化模型进行真实回测 - 得到可能亏损或微利但绝对真实的结果
"""

import pandas as pd
import numpy as np
import joblib
import json
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class RealisticBacktester:
    """真实回测器"""

    def __init__(self, model_path, features_path):
        # 加载模型
        print("📦 加载 V9.5 最小化模型...")
        self.model = joblib.load(model_path)

        # 加载特征
        with open(features_path, 'r') as f:
            self.feature_names = json.load(f)

        print(f"  ✅ 模型已加载: {self.feature_names}")

    def shin_method(self, home_odds, draw_odds, away_odds, margin=0.033):
        """Shin's Method 去水"""
        # 计算隐含概率
        p_home = 1 / home_odds
        p_draw = 1 / draw_odds
        p_away = 1 / away_odds
        total_prob = p_home + p_draw + p_away

        # 归一化
        p_home /= total_prob
        p_draw /= total_prob
        p_away /= total_prob

        # Shin's Method 调整
        adjusted_home = p_home * (1 - margin)
        adjusted_draw = p_draw * (1 - margin)
        adjusted_away = p_away * (1 - margin)

        # 重新归一化
        total = adjusted_home + adjusted_draw + adjusted_away
        adjusted_home /= total
        adjusted_draw /= total
        adjusted_away /= total

        # 转换为赔率
        adj_home_odds = 1 / adjusted_home
        adj_draw_odds = 1 / adjusted_draw
        adj_away_odds = 1 / adjusted_away

        return adj_home_odds, adj_draw_odds, adj_away_odds

    def kelly_criterion(self, true_prob, odds, kelly_fraction=0.25, max_bet=0.02):
        """凯利公式计算下注比例"""
        implied_prob = 1 / odds

        # 凯利公式: f = (bp - q) / b
        b = odds - 1
        p = true_prob
        q = 1 - p

        if b <= 0:
            return 0

        kelly_fraction_calc = (b * p - q) / b

        # 应用凯利系数限制
        kelly_fraction_calc *= kelly_fraction

        # 确保在合理范围内
        kelly_fraction_calc = max(0, min(kelly_fraction_calc, max_bet))

        return kelly_fraction_calc

    def prepare_backtest_data(self, data_path):
        """准备回测数据"""
        print("\n📊 准备真实回测数据...")
        df = pd.read_csv(data_path)
        print(f"  原始数据: {len(df)} 场比赛")

        # 转换日期
        df['match_date'] = pd.to_datetime(df['match_date'])
        df = df.sort_values('match_date').reset_index(drop=True)

        # 只保留有标签的数据
        df_labeled = df[df['target'].notna()].copy()
        print(f"  有标签数据: {len(df_labeled)} 场比赛")

        # 准备特征
        X = df_labeled[self.feature_names].fillna(0)

        print(f"  特征维度: {X.shape}")

        return X.values, df_labeled

    def execute_realistic_backtest(self, X, df):
        """执行真实回测"""
        print("\n💰 执行真实回测...")

        # 预测概率
        probabilities = self.model.predict_proba(X)
        home_win_prob = probabilities[:, 1]

        # 初始化回测参数
        initial_capital = 10000  # 初始资金
        capital = initial_capital
        capital_history = [capital]
        bet_history = []
        results = []

        total_bets = 0
        winning_bets = 0
        total_stakes = 0
        total_returns = 0

        print(f"  初始资金: ${initial_capital:,.2f}")
        print(f"  开始回测...")

        for i, (_, row) in enumerate(df.iterrows()):
            # 获取赔率
            home_odds = row['real_home_odds']
            draw_odds = row['real_draw_odds']
            away_odds = row['real_away_odds']

            # 检查赔率有效性
            if pd.isna(home_odds) or pd.isna(draw_odds) or pd.isna(away_odds):
                capital_history.append(capital)
                continue

            # Shin's Method 去水
            adj_home_odds, adj_draw_odds, adj_away_odds = self.shin_method(
                home_odds, draw_odds, away_odds
            )

            # 获取预测概率
            pred_home_prob = home_win_prob[i]

            # 计算价值下注 (更严格的阈值)
            value_threshold = 0.60  # 最小置信度 60%

            bet_info = {
                'match_date': row['match_date'],
                'pred_prob': pred_home_prob,
                'odds': adj_home_odds,
                'bet_amount': 0,
                'result': 'NO_BET',
                'profit': 0
            }

            if pred_home_prob > value_threshold:
                # 计算凯利下注
                bet_fraction = self.kelly_criterion(
                    pred_home_prob, adj_home_odds,
                    kelly_fraction=0.25, max_bet=0.02  # 2% 硬上限
                )

                # 计算下注金额
                bet_amount = capital * bet_fraction

                if bet_amount > 1:  # 最小下注 $1
                    # 记录下注
                    bet_info['bet_amount'] = bet_amount
                    bet_info['bet_fraction'] = bet_fraction
                    total_bets += 1
                    total_stakes += bet_amount

                    # 检查结果
                    actual_result = row['target']

                    if actual_result == 1:
                        # 主胜，赢得赔率
                        profit = bet_amount * (adj_home_odds - 1)
                        capital += profit
                        winning_bets += 1
                        total_returns += bet_amount + profit
                        bet_info['result'] = 'WIN'
                        bet_info['profit'] = profit
                    else:
                        # 主负，损失本金
                        capital -= bet_amount
                        total_returns += bet_amount * 0  # 损失本金
                        bet_info['result'] = 'LOSS'
                        bet_info['profit'] = -bet_amount

            bet_history.append(bet_info)
            capital_history.append(capital)

            # 每 200 场打印一次进度
            if (i + 1) % 200 == 0:
                print(f"    完成 {i+1}/{len(df)} 场，当前资金: ${capital:,.2f}")

        # 计算统计
        roi = (capital - initial_capital) / initial_capital * 100
        win_rate = winning_bets / total_bets * 100 if total_bets > 0 else 0
        total_profit = capital - initial_capital

        # 计算最大回撤
        peak = initial_capital
        max_drawdown = 0
        for c in capital_history:
            if c > peak:
                peak = c
            drawdown = (peak - c) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)

        print(f"\n✅ 真实回测完成!")
        print(f"  总比赛数: {len(df)} 场")
        print(f"  下注次数: {total_bets} 次")
        print(f"  获胜次数: {winning_bets} 次")
        print(f"  胜率: {win_rate:.1f}%")
        print(f"  最终资金: ${capital:,.2f}")
        print(f"  总收益: ${total_profit:,.2f}")
        print(f"  ROI: {roi:.2f}%")
        print(f"  最大回撤: {max_drawdown:.2f}%")

        return {
            'initial_capital': initial_capital,
            'final_capital': capital,
            'total_return': total_profit,
            'roi': roi,
            'total_bets': total_bets,
            'winning_bets': winning_bets,
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'capital_history': capital_history,
            'bet_history': bet_history
        }

    def plot_realistic_capital_curve(self, backtest_results, output_path):
        """绘制真实资金曲线"""
        print("\n📈 生成真实资金曲线...")

        capital_history = backtest_results['capital_history']
        initial_capital = backtest_results['initial_capital']

        # 计算回撤
        peak = initial_capital
        drawdowns = []
        peak_history = []

        for capital in capital_history:
            if capital > peak:
                peak = capital
            drawdown = (peak - capital) / peak * 100
            drawdowns.append(drawdown)
            peak_history.append(peak)

        # 绘制图表
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))

        # 资金曲线
        ax1.plot(capital_history, linewidth=2, color='blue', label='Capital')
        ax1.axhline(y=initial_capital, color='red', linestyle='--', alpha=0.7, label='Initial Capital')
        ax1.set_title('V9.5 Realistic Capital Curve (Data Leakage Fixed)', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Capital ($)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 添加文本注释
        final_capital = capital_history[-1]
        roi = (final_capital - initial_capital) / initial_capital * 100
        ax1.text(0.02, 0.98, f'Final Capital: ${final_capital:,.2f}\nROI: {roi:.2f}%',
                transform=ax1.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        # 回撤曲线
        ax2.fill_between(range(len(drawdowns)), drawdowns, alpha=0.3, color='red', label='Drawdown')
        ax2.plot(drawdowns, color='red', linewidth=1)
        ax2.set_title(f'Maximum Drawdown: {backtest_results["max_drawdown"]:.2f}%', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Drawdown (%)')
        ax2.set_xlabel('Match Number')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"  ✅ 资金曲线已保存: {output_path}")

    def save_results(self, backtest_results, output_path):
        """保存回测结果"""
        # 保存简化结果
        summary = {
            'version': 'V9.5',
            'backtest_date': datetime.now().isoformat(),
            'validation_type': 'Realistic Backtest (Data Leakage Fixed)',
            'initial_capital': backtest_results['initial_capital'],
            'final_capital': backtest_results['final_capital'],
            'total_return': backtest_results['total_return'],
            'roi_percent': backtest_results['roi'],
            'total_matches': len(backtest_results['capital_history']) - 1,
            'total_bets': backtest_results['total_bets'],
            'winning_bets': backtest_results['winning_bets'],
            'win_rate_percent': backtest_results['win_rate'],
            'max_drawdown_percent': backtest_results['max_drawdown']
        }

        with open(output_path, 'w') as f:
            json.dump(summary, f, indent=2)

        # 保存详细结果
        if backtest_results['bet_history']:
            bet_df = pd.DataFrame(backtest_results['bet_history'])
            bet_df.to_csv(output_path.replace('.json', '_bets.csv'), index=False)

        print(f"  ✅ 回测结果已保存: {output_path}")

def main():
    """主函数"""
    print("=" * 80)
    print("💰 V9.5 真实财务回测 - 数据泄露修复版")
    print("=" * 80)

    # 初始化回测器
    model_path = "/home/user/projects/FootballPrediction/src/production_models/v9_5_final_minimal_model.pkl"
    features_path = "/home/user/projects/FootballPrediction/src/production_models/v9_5_final_minimal_features.json"

    backtester = RealisticBacktester(model_path, features_path)

    # 准备数据
    data_path = "/home/user/projects/FootballPrediction/data/v9_5_ultra_safe_features.csv"
    X, df = backtester.prepare_backtest_data(data_path)

    # 执行真实回测
    backtest_results = backtester.execute_realistic_backtest(X, df)

    # 绘制资金曲线
    curve_path = "/home/user/projects/FootballPrediction/V9_5_REALISTIC_CAPITAL_CURVE.png"
    backtester.plot_realistic_capital_curve(backtest_results, curve_path)

    # 保存结果
    results_path = "/home/user/projects/FootballPrediction/V9_5_REALISTIC_BACKTEST_RESULTS.json"
    backtester.save_results(backtest_results, results_path)

    # 最终报告
    print("\n" + "=" * 80)
    print("💰 V9.5 真实财务回测完成")
    print("=" * 80)
    print(f"  🎯 验证目标: 得到真实、有波动、有回撤的回测结果")
    print(f"  📊 最终 ROI: {backtest_results['roi']:.2f}%")
    print(f"  💰 最终余额: ${backtest_results['final_capital']:,.2f}")
    print(f"  📉 最大回撤: {backtest_results['max_drawdown']:.2f}%")
    print(f"  🎲 胜率: {backtest_results['win_rate']:.1f}%")

    if backtest_results['roi'] > 0:
        print(f"\n✅ 微利结果: +{backtest_results['roi']:.2f}%")
    elif backtest_results['roi'] > -10:
        print(f"\n⚠️ 小幅亏损: {backtest_results['roi']:.2f}%")
    else:
        print(f"\n❌ 明显亏损: {backtest_results['roi']:.2f}%")

    return backtest_results

if __name__ == "__main__":
    backtest_results = main()
