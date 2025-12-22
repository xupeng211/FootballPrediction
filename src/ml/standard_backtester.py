#!/usr/bin/env python3
"""
V9.6 标准化回测器 - 生产级标准组件
V9.1 盈利回测的唯一官方实现

核心功能:
1. 自动输出 Brier Score
2. 自动输出 ROI
3. 自动输出最大回撤
4. 生成 V9.2 版本的 HTML 报告

作者: Claude Code
版本: V9.6
"""

import pandas as pd
import numpy as np
import joblib
import json
import os
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import warnings
warnings.filterwarnings('ignore')


class StandardBacktester:
    """
    标准化回测器 - V9.1 黄金配方的盈利验证实现

    核心参数 (V9.1 黄金配方):
    - MIN_EDGE = 7%: 最小预测边际
    - MIN_CONFIDENCE = 45%: 最小置信度
    - Kelly Fraction = 0.25: 凯利准则投注比例
    - MAX_BET = 2%: 单场最大投注比例
    - Water Removal: Shin's Method (3.3% 抽水)
    """

    def __init__(self, version: str = "V9.6"):
        """初始化回测器"""
        self.version = version
        self.model = None
        self.feature_names = None

        # V9.1 黄金配方参数
        self.MIN_EDGE = 0.07  # 7% 最小边际
        self.MIN_CONFIDENCE = 0.45  # 45% 最小置信度
        self.KELLY_FRACTION = 0.25  # 25% 凯利系数
        self.MAX_BET = 0.02  # 2% 最大投注
        self.WATER_REMOVAL = 0.033  # 3.3% Shin's Method

    def load_model(self, model_path: str, features_path: str) -> bool:
        """
        加载训练好的模型

        Args:
            model_path: 模型文件路径
            features_path: 特征文件路径

        Returns:
            bool: 加载是否成功
        """
        print(f"📦 加载 V9.6 标准化模型...")
        try:
            self.model = joblib.load(model_path)
            with open(features_path, 'r') as f:
                self.feature_names = json.load(f)
            print(f"  ✅ 模型加载成功")
            print(f"     模型: {model_path}")
            print(f"     特征数: {len(self.feature_names)}")
            return True
        except Exception as e:
            print(f"  ❌ 模型加载失败: {e}")
            return False

    def shin_method(self, home_odds: float, draw_odds: float, away_odds: float) -> Tuple[float, float, float]:
        """
        Shin's Method 去水 (移除 3.3% 庄家抽水)

        Args:
            home_odds: 主胜赔率
            draw_odds: 平局赔率
            away_odds: 客胜赔率

        Returns:
            Tuple: (调整后主胜赔率, 调整后平局赔率, 调整后客胜赔率)
        """
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
        adjusted_home = p_home * (1 - self.WATER_REMOVAL)
        adjusted_draw = p_draw * (1 - self.WATER_REMOVAL)
        adjusted_away = p_away * (1 - self.WATER_REMOVAL)

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

    def kelly_criterion(self, true_prob: float, odds: float) -> float:
        """
        凯利公式计算投注比例

        Args:
            true_prob: 真实概率
            odds: 赔率

        Returns:
            float: 投注比例
        """
        implied_prob = 1 / odds

        # 凯利公式: f = (bp - q) / b
        b = odds - 1
        p = true_prob
        q = 1 - p

        if b <= 0:
            return 0

        kelly_fraction_calc = (b * p - q) / b

        # 应用凯利系数限制
        kelly_fraction_calc *= self.KELLY_FRACTION

        # 确保在合理范围内
        kelly_fraction_calc = max(0, min(kelly_fraction_calc, self.MAX_BET))

        return kelly_fraction_calc

    def validate_real_odds_data(self, df: pd.DataFrame) -> bool:
        """
        验证是否包含真实赔率数据

        Args:
            df: 输入数据框

        Returns:
            bool: 是否包含真实赔率
        """
        print(f"🔍 验证真实赔率数据...")

        # 检查必要列
        required_cols = ['real_home_odds', 'real_draw_odds', 'real_away_odds', 'actual_result']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            print(f"  ❌ 缺失必要列: {missing_cols}")
            return False

        # 检查数据完整性
        complete_data = df[required_cols].dropna()
        completeness = len(complete_data) / len(df)

        print(f"  数据完整性: {completeness:.1%}")
        print(f"  完整记录: {len(complete_data)} / {len(df)}")

        if completeness < 0.5:
            print(f"  ⚠️  警告: 真实赔率数据不足 50%")
            return False

        print(f"  ✅ 真实赔率数据验证通过")
        return True

    def prepare_backtest_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, pd.DataFrame]:
        """
        准备回测数据

        Args:
            df: 输入数据框

        Returns:
            Tuple: (X, df_processed)
        """
        print(f"\n📊 准备回测数据...")

        # 过滤有效数据
        df_clean = df[
            df['real_home_odds'].notna() &
            df['real_draw_odds'].notna() &
            df['real_away_odds'].notna() &
            df['actual_result'].notna()
        ].copy()

        # 转换日期并排序
        if 'match_date' in df_clean.columns:
            df_clean['match_date'] = pd.to_datetime(df_clean['match_date'])
            df_clean = df_clean.sort_values('match_date').reset_index(drop=True)

        # 准备特征
        X = df_clean[self.feature_names].fillna(0)

        print(f"  有效数据: {len(df_clean)} 场比赛")
        print(f"  特征维度: {X.shape}")

        return X.values, df_clean

    def execute_backtest(self, X: np.ndarray, df: pd.DataFrame) -> Dict[str, Any]:
        """
        执行回测

        Args:
            X: 特征矩阵
            df: 数据框

        Returns:
            Dict: 回测结果
        """
        print(f"\n💰 执行 V9.1 黄金配方回测...")
        print("=" * 80)

        # 预测概率
        probabilities = self.model.predict_proba(X)
        home_win_prob = probabilities[:, 1]

        # 初始化回测参数
        initial_capital = 10000
        capital = initial_capital
        capital_history = [capital]
        bet_history = []

        total_bets = 0
        winning_bets = 0
        total_stakes = 0
        total_returns = 0

        print(f"  初始资金: ${initial_capital:,.2f}")
        print(f"  V9.1 黄金配方参数:")
        print(f"    - 最小边际: {self.MIN_EDGE:.1%}")
        print(f"    - 最小置信度: {self.MIN_CONFIDENCE:.1%}")
        print(f"    - 凯利系数: {self.KELLY_FRACTION:.1%}")
        print(f"    - 最大投注: {self.MAX_BET:.1%}")
        print(f"    - 去水方法: Shin's Method ({self.WATER_REMOVAL:.1%})")
        print(f"  开始回测...")

        for i, (_, row) in enumerate(df.iterrows()):
            # 获取赔率
            home_odds = row['real_home_odds']
            draw_odds = row['real_draw_odds']
            away_odds = row['real_away_odds']

            # Shin's Method 去水
            adj_home_odds, adj_draw_odds, adj_away_odds = self.shin_method(
                home_odds, draw_odds, away_odds
            )

            # 获取预测概率
            pred_home_prob = home_win_prob[i]

            # 计算价值下注
            bet_info = {
                'match_date': row.get('match_date', f'Match_{i}'),
                'home_team': row.get('home_team_name', 'Home'),
                'away_team': row.get('away_team_name', 'Away'),
                'pred_prob': pred_home_prob,
                'odds': adj_home_odds,
                'bet_amount': 0,
                'result': 'NO_BET',
                'profit': 0,
                'capital_after': capital
            }

            # V9.1 黄金配方逻辑
            # 1. 检查最小置信度
            if pred_home_prob < self.MIN_CONFIDENCE:
                bet_history.append(bet_info)
                capital_history.append(capital)
                continue

            # 2. 计算预测边际
            implied_prob = 1 / adj_home_odds
            edge = pred_home_prob - implied_prob

            # 3. 检查最小边际
            if edge < self.MIN_EDGE:
                bet_history.append(bet_info)
                capital_history.append(capital)
                continue

            # 4. 凯利公式计算投注
            bet_fraction = self.kelly_criterion(pred_home_prob, adj_home_odds)
            bet_amount = capital * bet_fraction

            if bet_amount > 1:  # 最小投注 $1
                # 记录下注
                bet_info['bet_amount'] = bet_amount
                bet_info['bet_fraction'] = bet_fraction
                bet_info['edge'] = edge
                total_bets += 1
                total_stakes += bet_amount

                # 检查结果
                actual_result = row['actual_result']

                if actual_result == 'H':
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
                    total_returns += 0
                    bet_info['result'] = 'LOSS'
                    bet_info['profit'] = -bet_amount

            bet_history.append(bet_info)
            capital_history.append(capital)

            # 每 100 场打印一次进度
            if (i + 1) % 100 == 0:
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

        # 计算 Brier Score
        y_true = (df['actual_result'] == 'H').astype(int)
        brier_score = np.mean((home_win_prob - y_true) ** 2)

        print(f"\n✅ V9.1 黄金配方回测完成!")
        print(f"=" * 80)
        print(f"  📊 核心指标:")
        print(f"    - Brier Score: {brier_score:.4f}")
        print(f"    - ROI: {roi:.2f}%")
        print(f"    - 最大回撤: {max_drawdown:.2f}%")
        print(f"  💰 财务指标:")
        print(f"    - 最终资金: ${capital:,.2f}")
        print(f"    - 总收益: ${total_profit:,.2f}")
        print(f"  🎲 交易指标:")
        print(f"    - 下注次数: {total_bets} 次")
        print(f"    - 获胜次数: {winning_bets} 次")
        print(f"    - 胜率: {win_rate:.1f}%")

        return {
            'initial_capital': initial_capital,
            'final_capital': capital,
            'total_return': total_profit,
            'roi_percent': roi,
            'brier_score': brier_score,
            'max_drawdown_percent': max_drawdown,
            'total_bets': total_bets,
            'winning_bets': winning_bets,
            'win_rate_percent': win_rate,
            'capital_history': capital_history,
            'bet_history': bet_history,
            'home_win_probabilities': home_win_prob
        }

    def generate_html_report(self, backtest_results: Dict[str, Any],
                           output_path: str) -> str:
        """
        生成 V9.2 版本的 HTML 报告

        Args:
            backtest_results: 回测结果
            output_path: 输出路径

        Returns:
            str: HTML 报告路径
        """
        print(f"\n📊 生成 V9.2 风格 HTML 报告...")

        # 创建图表
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle(f'{self.version} 盈利回测报告', fontsize=16, fontweight='bold')

        # 1. 资金曲线
        ax1 = axes[0, 0]
        capital_history = backtest_results['capital_history']
        ax1.plot(capital_history, linewidth=2, color='blue')
        ax1.axhline(y=backtest_results['initial_capital'], color='red',
                   linestyle='--', alpha=0.7, label='初始资金')
        ax1.set_title('资金曲线')
        ax1.set_ylabel('资金 ($)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 2. 胜负分布饼图
        ax2 = axes[0, 1]
        win_count = backtest_results['winning_bets']
        loss_count = backtest_results['total_bets'] - win_count
        if win_count > 0 or loss_count > 0:
            ax2.pie([win_count, loss_count], labels=['获胜', '失败'],
                   colors=['green', 'red'], autopct='%1.1f%%')
            ax2.set_title('胜负分布')

        # 3. 收益分布直方图
        ax3 = axes[1, 0]
        bet_history = backtest_results['bet_history']
        profits = [bet['profit'] for bet in bet_history if bet['profit'] != 0]
        if profits:
            ax3.hist(profits, bins=30, alpha=0.7, color='skyblue')
            ax3.set_title('收益分布')
            ax3.set_xlabel('收益 ($)')
            ax3.set_ylabel('频次')
            ax3.grid(True, alpha=0.3)

        # 4. 滚动胜率曲线
        ax4 = axes[1, 1]
        if len(profits) > 10:
            # 计算滚动胜率
            window = 20
            rolling_wins = []
            rolling_total = []
            for i in range(len(bet_history)):
                start_idx = max(0, i - window + 1)
                window_bets = bet_history[start_idx:i+1]
                wins = sum(1 for bet in window_bets if bet['result'] == 'WIN')
                total = sum(1 for bet in window_bets if bet['result'] in ['WIN', 'LOSS'])
                if total > 0:
                    rolling_wins.append(wins)
                    rolling_total.append(total)

            if rolling_total:
                rolling_win_rate = [w/t*100 if t > 0 else 0
                                  for w, t in zip(rolling_wins, rolling_total)]
                ax4.plot(rolling_win_rate, linewidth=2, color='green')
                ax4.axhline(y=50, color='red', linestyle='--', alpha=0.7, label='50%基准')
                ax4.set_title(f'滚动胜率 (窗口={window})')
                ax4.set_ylabel('胜率 (%)')
                ax4.legend()
                ax4.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_path.replace('.html', '.png'), dpi=150, bbox_inches='tight')
        plt.close()

        # 生成 HTML
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{self.version} 盈利回测报告</title>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .metric {{ display: inline-block; margin: 10px; padding: 15px;
                  background-color: #e8f4f8; border-radius: 5px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
        .metric-label {{ font-size: 12px; color: #7f8c8d; }}
        .chart {{ margin: 20px 0; text-align: center; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{self.version} 盈利回测报告</h1>
        <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>版本: {self.version} 标准化回测器 - V9.1 黄金配方</p>
    </div>

    <h2>核心指标</h2>
    <div class="metric">
        <div class="metric-value">{backtest_results['roi_percent']:.2f}%</div>
        <div class="metric-label">ROI</div>
    </div>
    <div class="metric">
        <div class="metric-value">{backtest_results['brier_score']:.4f}</div>
        <div class="metric-label">Brier Score</div>
    </div>
    <div class="metric">
        <div class="metric-value">{backtest_results['max_drawdown_percent']:.2f}%</div>
        <div class="metric-label">最大回撤</div>
    </div>
    <div class="metric">
        <div class="metric-value">${backtest_results['final_capital']:,.2f}</div>
        <div class="metric-label">最终资金</div>
    </div>
    <div class="metric">
        <div class="metric-value">{backtest_results['win_rate_percent']:.1f}%</div>
        <div class="metric-label">胜率</div>
    </div>

    <h2>资金曲线</h2>
    <div class="chart">
        <img src="{os.path.basename(output_path).replace('.html', '.png')}" width="800">
    </div>

    <h2>交易统计</h2>
    <table>
        <tr><th>指标</th><th>数值</th></tr>
        <tr><td>初始资金</td><td>${backtest_results['initial_capital']:,.2f}</td></tr>
        <tr><td>最终资金</td><td>${backtest_results['final_capital']:,.2f}</td></tr>
        <tr><td>总收益</td><td>${backtest_results['total_return']:,.2f}</td></tr>
        <tr><td>下注次数</td><td>{backtest_results['total_bets']}</td></tr>
        <tr><td>获胜次数</td><td>{backtest_results['winning_bets']}</td></tr>
        <tr><td>胜率</td><td>{backtest_results['win_rate_percent']:.1f}%</td></tr>
    </table>

    <h2>V9.1 黄金配方参数</h2>
    <table>
        <tr><th>参数</th><th>值</th><th>说明</th></tr>
        <tr><td>最小边际</td><td>{self.MIN_EDGE:.1%}</td><td>最小预测边际</td></tr>
        <tr><td>最小置信度</td><td>{self.MIN_CONFIDENCE:.1%}</td><td>最小置信度阈值</td></tr>
        <tr><td>凯利系数</td><td>{self.KELLY_FRACTION:.1%}</td><td>凯利准则投注比例</td></tr>
        <tr><td>最大投注</td><td>{self.MAX_BET:.1%}</td><td>单场最大投注比例</td></tr>
        <tr><td>去水方法</td><td>Shin's Method</td><td>移除 {self.WATER_REMOVAL:.1%} 庄家抽水</td></tr>
    </table>

    <h2>评估结论</h2>
    <p>
        {'✅' if backtest_results['roi_percent'] > 10 else '⚠️' if backtest_results['roi_percent'] > 0 else '❌'}
        ROI 为 {backtest_results['roi_percent']:.2f}%
        {'，超过 10% 目标，表现优秀' if backtest_results['roi_percent'] > 10 else
         '，为正收益，表现良好' if backtest_results['roi_percent'] > 0 else
         '，为负收益，需要优化'}
    </p>
    <p>
        Brier Score 为 {backtest_results['brier_score']:.4f}，
        {'表现优秀' if backtest_results['brier_score'] < 0.25 else
         '表现良好' if backtest_results['brier_score'] < 0.3 else
         '需要改进'}。
    </p>
</body>
</html>
        """

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"  ✅ HTML 报告已生成: {output_path}")
        return output_path

    def run_full_backtest(self, data_path: str, model_path: str,
                         features_path: str, output_dir: str = "reports") -> Dict[str, Any]:
        """
        运行完整回测流程

        Args:
            data_path: 数据文件路径
            model_path: 模型文件路径
            features_path: 特征文件路径
            output_dir: 输出目录

        Returns:
            Dict: 完整回测结果
        """
        print("=" * 80)
        print(f"🚀 {self.version} 标准化回测器 - 完整流程")
        print("=" * 80)

        # 1. 加载模型
        if not self.load_model(model_path, features_path):
            raise ValueError("模型加载失败")

        # 2. 加载数据
        print(f"\n第二步：加载数据...")
        df = pd.read_csv(data_path)
        print(f"  数据路径: {data_path}")
        print(f"  数据量: {len(df)} 场比赛")

        # 3. 验证真实赔率数据
        if not self.validate_real_odds_data(df):
            raise ValueError("真实赔率数据验证失败")

        # 4. 准备回测数据
        X, df_clean = self.prepare_backtest_data(df)

        # 5. 执行回测
        backtest_results = self.execute_backtest(X, df_clean)

        # 6. 生成报告
        os.makedirs(output_dir, exist_ok=True)
        report_path = os.path.join(output_dir, f'{self.version.lower()}_backtest_report.html')
        self.generate_html_report(backtest_results, report_path)

        # 7. 保存结果
        results_path = os.path.join(output_dir, f'{self.version.lower()}_backtest_results.json')
        summary = {
            'version': self.version,
            'backtest_date': datetime.now().isoformat(),
            'model_path': model_path,
            'data_path': data_path,
            'initial_capital': backtest_results['initial_capital'],
            'final_capital': backtest_results['final_capital'],
            'total_return': backtest_results['total_return'],
            'roi_percent': backtest_results['roi_percent'],
            'brier_score': backtest_results['brier_score'],
            'max_drawdown_percent': backtest_results['max_drawdown_percent'],
            'total_bets': backtest_results['total_bets'],
            'winning_bets': backtest_results['winning_bets'],
            'win_rate_percent': backtest_results['win_rate_percent'],
            'report_path': report_path
        }

        with open(results_path, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"\n✅ {self.version} 标准化回测完成")
        print("=" * 80)
        print(f"  📊 Brier Score: {backtest_results['brier_score']:.4f}")
        print(f"  💰 ROI: {backtest_results['roi_percent']:.2f}%")
        print(f"  📉 最大回撤: {backtest_results['max_drawdown_percent']:.2f}%")
        print(f"  📁 报告: {report_path}")
        print(f"  📁 结果: {results_path}")

        return backtest_results


def main():
    """主函数 - 示例用法"""
    # 创建回测器
    backtester = StandardBacktester(version="V9.6")

    # 运行完整回测
    results = backtester.run_full_backtest(
        data_path="/home/user/projects/FootballPrediction/data/combined_multi_season_odds.csv",
        model_path="/home/user/projects/FootballPrediction/src/production_models/v9_6_standard_model.pkl",
        features_path="/home/user/projects/FootballPrediction/src/production_models/v9_6_standard_features.json",
        output_dir="/home/user/projects/FootballPrediction/reports"
    )

    print(f"\n🎉 回测完成!")
    print(f"  ROI: {results['roi_percent']:.2f}%")


if __name__ == "__main__":
    main()
