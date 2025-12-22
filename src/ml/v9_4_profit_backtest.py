#!/usr/bin/env python3
"""
V9.4 2188 场盈利回测系统
使用 V9.4 模型对全量数据进行模拟下注
计算最终账户余额和资金回撤曲线
"""

import pandas as pd
import numpy as np
import joblib
import json
import matplotlib.pyplot as plt
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class V94ProfitBacktester:
    """V9.4 盈利回测器"""

    def __init__(self, model_path, features_path):
        # 加载模型
        print("📦 加载 V9.4 模型...")
        self.model = joblib.load(model_path)

        # 加载特征名称
        with open(features_path, 'r') as f:
            self.feature_names = json.load(f)

        print(f"  ✅ 模型已加载: {len(self.feature_names)} 个特征")

    def shin_method(self, home_odds, draw_odds, away_odds, margin=0.033):
        """Shin's Method 去水 (移除 3.3% 庄家抽水)"""
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
        # 这是一个简化的实现，实际的 Shin's Method 更复杂
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
        # 计算隐含概率
        implied_prob = 1 / odds

        # 凯利公式: f = (bp - q) / b
        # b = 赔率 - 1, p = 真实概率, q = 1 - p
        b = odds - 1
        p = true_prob
        q = 1 - p

        kelly_fraction_calc = (b * p - q) / b

        # 应用凯利系数限制
        kelly_fraction_calc *= kelly_fraction

        # 确保在合理范围内
        kelly_fraction_calc = max(0, min(kelly_fraction_calc, max_bet))

        return kelly_fraction_calc

    def prepare_full_data(self, data_path):
        """准备全量回测数据"""
        print("\n📊 准备 2188 场全量回测数据...")
        df = pd.read_csv(data_path)
        print(f"  原始数据量: {len(df)} 场比赛")

        # 转换日期
        df['match_date'] = pd.to_datetime(df['match_date'])
        df = df.sort_values('match_date').reset_index(drop=True)

        # 准备特征
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        exclude_cols = [
            'real_home_odds', 'real_draw_odds', 'real_away_odds',
            'real_match_date', 'real_season', 'actual_home_goals',
            'actual_away_goals', 'season', 'match_date'
        ]

        feature_names = [col for col in numeric_cols if col not in exclude_cols]
        X = df[feature_names].fillna(0)

        # 添加赔率特征
        X['home_prob'] = 1 / df['real_home_odds'].fillna(2.0)
        X['draw_prob'] = 1 / df['real_draw_odds'].fillna(3.5)
        X['away_prob'] = 1 / df['real_away_odds'].fillna(3.5)
        X['total_prob'] = X['home_prob'] + X['draw_prob'] + X['away_prob']
        X['home_prob_norm'] = X['home_prob'] / X['total_prob']
        X['draw_prob_norm'] = X['draw_prob'] / X['total_prob']
        X['away_prob_norm'] = X['away_prob'] / X['total_prob']

        # 计算 xG 差异 (如果存在)
        if 'home_xg' in df.columns and 'away_xg' in df.columns:
            X['xg_diff'] = df['home_xg'] - df['away_xg']

        print(f"  特征维度: {X.shape}")

        return X.values, df

    def predict_and_bet(self, X, df):
        """预测和下注"""
        print("\n🎯 开始预测和下注...")

        # 预测概率
        probabilities = self.model.predict_proba(X)
        home_win_prob = probabilities[:, 1]  # 主胜概率

        # 初始化回测参数
        initial_capital = 10000  # 初始资金
        capital = initial_capital
        capital_history = [capital]
        bet_history = []
        results = []

        total_bets = 0
        winning_bets = 0

        print(f"  初始资金: ${initial_capital:,.2f}")
        print(f"  开始回测...")

        for i, (_, row) in enumerate(df.iterrows()):
            # 获取赔率
            home_odds = row['real_home_odds']
            draw_odds = row['real_draw_odds']
            away_odds = row['real_away_odds']

            # 如果缺少赔率，使用默认值
            if pd.isna(home_odds):
                home_odds = 2.0
            if pd.isna(draw_odds):
                draw_odds = 3.5
            if pd.isna(away_odds):
                away_odds = 3.5

            # Shin's Method 去水
            adj_home_odds, adj_draw_odds, adj_away_odds = self.shin_method(
                home_odds, draw_odds, away_odds
            )

            # 获取预测概率
            pred_home_prob = home_win_prob[i]

            # 计算价值下注 (只对主胜下注)
            value_threshold = 0.55  # 最小置信度 55%

            if pred_home_prob > value_threshold:
                # 计算凯利下注
                bet_fraction = self.kelly_criterion(
                    pred_home_prob, adj_home_odds,
                    kelly_fraction=0.25, max_bet=0.02
                )

                # 计算下注金额
                bet_amount = capital * bet_fraction

                if bet_amount > 0:
                    # 记录下注
                    bet_info = {
                        'match_date': row['match_date'],
                        'home_team': row.get('home_team_name', 'Home'),
                        'away_team': row.get('away_team_name', 'Away'),
                        'pred_prob': pred_home_prob,
                        'odds': adj_home_odds,
                        'bet_amount': bet_amount,
                        'bet_fraction': bet_fraction
                    }
                    bet_history.append(bet_info)
                    total_bets += 1

                    # 检查结果
                    actual_result = row.get('actual_result', np.nan)

                    if pd.notna(actual_result):
                        # 有实际结果，检查输赢
                        if actual_result == 'H':
                            # 主胜，赢得赔率
                            profit = bet_amount * (adj_home_odds - 1)
                            capital += profit
                            winning_bets += 1
                            bet_info['result'] = 'WIN'
                            bet_info['profit'] = profit
                        else:
                            # 主负，损失本金
                            capital -= bet_amount
                            bet_info['result'] = 'LOSS'
                            bet_info['profit'] = -bet_amount
                    else:
                        # 没有实际结果，等待中
                        bet_info['result'] = 'PENDING'
                        bet_info['profit'] = 0

            else:
                # 没有价值下注
                bet_info = {
                    'match_date': row['match_date'],
                    'home_team': row.get('home_team_name', 'Home'),
                    'away_team': row.get('away_team_name', 'Away'),
                    'pred_prob': pred_home_prob,
                    'odds': np.nan,
                    'bet_amount': 0,
                    'bet_fraction': 0,
                    'result': 'NO_BET',
                    'profit': 0
                }

            capital_history.append(capital)

            # 每 500 场打印一次进度
            if (i + 1) % 500 == 0:
                print(f"    完成 {i+1}/{len(df)} 场，当前资金: ${capital:,.2f}")

        # 计算统计
        roi = (capital - initial_capital) / initial_capital * 100

        print(f"\n✅ 回测完成!")
        print(f"  总比赛数: {len(df)} 场")
        print(f"  下注次数: {total_bets} 次")
        print(f"  获胜次数: {winning_bets} 次")
        print(f"  胜率: {winning_bets/total_bets*100:.1f}%" if total_bets > 0 else "  胜率: N/A")
        print(f"  最终资金: ${capital:,.2f}")
        print(f"  总收益: ${capital - initial_capital:,.2f}")
        print(f"  ROI: {roi:.2f}%")

        return {
            'initial_capital': initial_capital,
            'final_capital': capital,
            'total_return': capital - initial_capital,
            'roi': roi,
            'total_bets': total_bets,
            'winning_bets': winning_bets,
            'win_rate': winning_bets/total_bets*100 if total_bets > 0 else 0,
            'capital_history': capital_history,
            'bet_history': bet_history
        }

    def plot_capital_curve(self, backtest_results, output_path):
        """绘制资金曲线"""
        print("\n📈 生成资金回撤曲线...")

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

        max_drawdown = max(drawdowns)

        # 绘制图表
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))

        # 资金曲线
        ax1.plot(capital_history, linewidth=2, color='blue', label='Capital')
        ax1.axhline(y=initial_capital, color='red', linestyle='--', alpha=0.7, label='Initial Capital')
        ax1.set_title('V9.4 Capital Curve (2188 Matches)', fontsize=14, fontweight='bold')
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
        ax2.set_title(f'Maximum Drawdown: {max_drawdown:.2f}%', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Drawdown (%)')
        ax2.set_xlabel('Match Number')
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"  ✅ 资金曲线已保存: {output_path}")
        print(f"  📊 最大回撤: {max_drawdown:.2f}%")

        return max_drawdown

    def save_results(self, backtest_results, output_path):
        """保存回测结果"""
        # 保存简化结果
        summary = {
            'version': 'V9.4',
            'backtest_date': datetime.now().isoformat(),
            'initial_capital': backtest_results['initial_capital'],
            'final_capital': backtest_results['final_capital'],
            'total_return': backtest_results['total_return'],
            'roi_percent': backtest_results['roi'],
            'total_matches': len(backtest_results['capital_history']) - 1,
            'total_bets': backtest_results['total_bets'],
            'winning_bets': backtest_results['winning_bets'],
            'win_rate_percent': backtest_results['win_rate']
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
    print("=" * 70)
    print("💰 V9.4 2188 场盈利回测 - 最终账户余额 & 资金回撤曲线")
    print("=" * 70)

    # 初始化回测器
    model_path = "/home/user/projects/FootballPrediction/src/production_models/v9_4_calibrated_model.pkl"
    features_path = "/home/user/projects/FootballPrediction/src/production_models/v9_4_feature_names.json"

    backtester = V94ProfitBacktester(model_path, features_path)

    # 准备数据
    data_path = "/home/user/projects/FootballPrediction/data/v9_3_comprehensive_dataset.csv"
    X, df = backtester.prepare_full_data(data_path)

    # 执行回测
    backtest_results = backtester.predict_and_bet(X, df)

    # 绘制资金曲线
    curve_path = "/home/user/projects/FootballPrediction/V9_4_CAPITAL_CURVE.png"
    max_drawdown = backtester.plot_capital_curve(backtest_results, curve_path)

    # 保存结果
    results_path = "/home/user/projects/FootballPrediction/V9_4_BACKTEST_RESULTS.json"
    backtester.save_results(backtest_results, results_path)

    # 最终报告
    print("\n" + "=" * 70)
    print("💰 V9.4 盈利回测完成 - 最终账户余额报告")
    print("=" * 70)
    print(f"  🎯 验证目标: ROI 是否能维持在 +10% 以上")
    print(f"  📊 最终 ROI: {backtest_results['roi']:.2f}%")
    print(f"  💰 最终余额: ${backtest_results['final_capital']:,.2f}")
    print(f"  📉 最大回撤: {max_drawdown:.2f}%")
    print(f"  ✅ 目标达成: {'是' if backtest_results['roi'] >= 10 else '否'}")

    if backtest_results['roi'] >= 10:
        print(f"\n🎉 恭喜！ROI {backtest_results['roi']:.2f}% 超过 +10% 目标！")
    else:
        print(f"\n⚠️  ROI {backtest_results['roi']:.2f}% 未达 +10% 目标")

    return backtest_results

if __name__ == "__main__":
    backtest_results = main()
