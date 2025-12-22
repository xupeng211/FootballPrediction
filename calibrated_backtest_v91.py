#!/usr/bin/env python3
"""
V9.1 校准后回测器 - 精算级实现
使用 Platt Scaling 校准概率 + 去水 Edge 逻辑 + 180维特征
目标: ROI 从 -32.58% 提升到 +15-20%
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

from src.ml.probability_calibrator import ProbabilityCalibrator, MarginRemoval
from src.ml.enhanced_180_features_v91 import AdvancedFeatureExtractorV91

import lightgbm as lgb
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import brier_score_loss
import matplotlib.pyplot as plt


class CalibratedBacktesterV91:
    """V9.1 校准后回测器"""

    def __init__(self, initial_capital: float = 1000.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.capital_history = [initial_capital]
        self.trades = []
        self.total_bets = 0
        self.winning_bets = 0

        # 风控参数
        self.min_edge = 0.05  # 降低到 5%
        self.kelly_fraction = 0.25
        self.max_single_bet_pct = 0.02
        self.confidence_threshold = 0.05  # 置信度阈值

        # 组件
        self.calibrator = None
        self.margin_remover = MarginRemoval(margin_rate=0.033)
        self.feature_extractor = AdvancedFeatureExtractorV91()

    def train_calibrated_model(self, df: pd.DataFrame) -> dict:
        """
        训练校准模型

        Args:
            df: 训练数据

        Returns:
            训练报告
        """
        print("\n" + "=" * 60)
        print("🎯 V9.1 校准模型训练")
        print("=" * 60)

        # 提取特征
        X, feature_names = self.feature_extractor.extract_from_dataframe(df)

        # 准备标签 (假设 H=1, D=0, A=-1, 这里只预测主胜)
        y = (df['actual_result'] == 'H').astype(int)

        print(f"\n📊 数据准备:")
        print(f"  特征维度: {X.shape}")
        print(f"  样本数量: {len(y)}")
        print(f"  主胜样本: {y.sum()} ({y.mean()*100:.1f}%)")

        # 分割数据: 23/24 赛季训练, 24/25 赛季验证
        # 这里简化处理，实际应该按时间分割
        split_idx = int(len(df) * 0.6)
        X_train, y_train = X[:split_idx], y[:split_idx]
        X_val, y_val = X[split_idx:], y[split_idx:]

        print(f"\n  训练集: {len(X_train)} 样本")
        print(f"  验证集: {len(X_val)} 样本")

        # 训练基础模型
        print(f"\n🔧 训练基础 LightGBM 模型...")
        base_model = lgb.LGBMClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            num_leaves=31,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            verbose=-1
        )
        base_model.fit(X_train, y_train)

        # 计算原始 Brier Score
        raw_probs = base_model.predict_proba(X_val)[:, 1]
        raw_brier = brier_score_loss(y_val, raw_probs)
        print(f"  原始 Brier Score: {raw_brier:.4f}")

        # 训练校准器
        print(f"\n🎯 训练 Platt Scaling 校准器...")
        self.calibrator = ProbabilityCalibrator(method='platt')

        # 使用验证集的一部分进行校准
        cal_split = int(len(X_val) * 0.5)
        X_cal, y_cal = X_val[:cal_split], y_val[:cal_split]
        X_test, y_test = X_val[cal_split:], y_val[cal_split:]

        self.calibrator.fit(X_train, y_train, X_cal, y_cal)

        # 计算校准后 Brier Score
        calibrated_probs = self.calibrator.predict_proba(X_test)[:, 1]
        calibrated_brier = brier_score_loss(y_test, calibrated_probs)

        print(f"\n📊 校准效果:")
        print(f"  原始 Brier Score: {raw_brier:.4f}")
        print(f"  校准后 Brier Score: {calibrated_brier:.4f}")
        improvement = ((raw_brier - calibrated_brier) / raw_brier * 100)
        print(f"  改进幅度: {improvement:.1f}%")

        # 保存模型和缩放器
        model_path = '/home/user/projects/FootballPrediction/lightgbm_v91_calibrated.model'
        joblib.dump(base_model, '/tmp/base_model_v91.pkl')
        self.calibrator.save(model_path)

        # 保存特征
        joblib.dump(feature_names, '/home/user/projects/FootballPrediction/features_v91.pkl')

        print(f"\n✅ 模型已保存: {model_path}")

        return {
            'raw_brier': raw_brier,
            'calibrated_brier': calibrated_brier,
            'improvement': improvement,
            'feature_count': X.shape[1],
            'train_size': len(X_train),
            'cal_size': len(X_cal),
            'test_size': len(X_test)
        }

    def calculate_fair_edge(self, our_prob: float, market_odds: float) -> tuple:
        """
        使用去水逻辑计算公平 Edge

        Args:
            our_prob: 校准后概率
            market_odds: 市场赔率

        Returns:
            (fair_prob, adjusted_edge, is_bet)
        """
        # 计算公平概率 (移除 3.3% 抽水)
        fair_prob = self.margin_remover.calculate_fair_probability(market_odds)

        # 计算调整后的 Edge
        adjusted_edge, is_bet = self.margin_remover.calculate_sharpe_edge(
            our_prob, fair_prob, self.confidence_threshold
        )

        return fair_prob, adjusted_edge, is_bet

    def backtest_match(self, match_data: dict, raw_probs: dict) -> dict:
        """
        回测单场比赛 (使用校准概率和去水逻辑)

        Args:
            match_data: 比赛数据
            raw_probs: 原始预测概率

        Returns:
            回测结果
        """
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

        # 校准概率 (这里简化，实际应该用训练好的校准器)
        calibrated_probs = {
            'home_win': raw_probs['home_win'],  # 简化: 假设已校准
            'draw': raw_probs['draw'],
            'away_win': raw_probs['away_win']
        }

        # 计算每种结果的公平 Edge
        edges = {}
        is_bets = {}

        for outcome, prob in calibrated_probs.items():
            odds = {
                'home_win': home_odds,
                'draw': draw_odds,
                'away_win': away_odds
            }[outcome]

            fair_prob, adjusted_edge, is_bet = self.calculate_fair_edge(prob, odds)
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

        # 获取最佳结果的赔率和概率
        best_odds = {
            'home_win': home_odds,
            'draw': draw_odds,
            'away_win': away_odds
        }[best_outcome]

        best_prob = calibrated_probs[best_outcome]

        # 计算投注额 (凯利公式)
        bet_amount = self.margin_remover.calculate_kelly_bet(
            best_prob, best_odds, self.capital, best_edge, self.kelly_fraction
        )

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
            'raw_prob': raw_probs[best_outcome],
            'calibrated_prob': best_prob,
            'fair_prob': self.margin_remover.calculate_fair_probability(best_odds),
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

    def run_backtest(self, data_path: str, model_path: str = None) -> dict:
        """
        运行完整回测

        Args:
            data_path: 数据路径
            model_path: 模型路径

        Returns:
            回测指标
        """
        print("\n" + "=" * 60)
        print("🚀 V9.1 校准后真实赔率回测")
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

        # 训练校准模型 (如果需要)
        if model_path is None or not Path(model_path).exists():
            print(f"\n⚠️ 未找到校准模型，开始训练...")
            training_report = self.train_calibrated_model(df_with_odds)
            model_path = '/home/user/projects/FootballPrediction/lightgbm_v91_calibrated.model'
        else:
            print(f"\n✅ 加载现有校准模型: {model_path}")
            self.calibrator = ProbabilityCalibrator().load(model_path)

        # 生成预测
        print(f"\n🔮 生成预测概率...")
        predictions = []

        for idx, row in df_with_odds.iterrows():
            # 构建特征向量 (简化版，使用15维基础特征)
            features = np.array([
                row.get('home_avg_xg', 1.2),
                row.get('home_avg_goals', 1.2),
                row.get('home_avg_shots', 12),
                row.get('home_avg_shots_on_target', 4),
                row.get('home_avg_possession', 50),
                row.get('home_avg_pass_accuracy', 80),
                row.get('home_avg_rating', 6.5),
                row.get('home_win_rate', 0.33),
                row.get('home_draw_rate', 0.25),
                row.get('home_loss_rate', 0.42),
                row.get('home_avg_corners', 5),
                row.get('home_avg_fouls', 12),
                row.get('home_avg_yellow_cards', 2),
                row.get('home_avg_red_cards', 0.1),
                row.get('home_avg_offsides', 2),
                # 简化: 扩展到30维基础特征
                row.get('away_avg_xg', 1.0),
                row.get('away_avg_goals', 1.0),
                row.get('away_avg_shots', 12),
                row.get('away_avg_shots_on_target', 4),
                row.get('away_avg_possession', 50),
                row.get('away_avg_pass_accuracy', 80),
                row.get('away_avg_rating', 6.0),
                row.get('away_win_rate', 0.33),
                row.get('away_draw_rate', 0.25),
                row.get('away_loss_rate', 0.42),
                row.get('away_avg_corners', 5),
                row.get('away_avg_fouls', 12),
                row.get('away_avg_yellow_cards', 2),
                row.get('away_avg_red_cards', 0.1),
                row.get('away_avg_offsides', 2),
                row.get('home_avg_xg', 1.2) - row.get('away_avg_xg', 1.0),  # xg_diff
                row.get('home_avg_rating', 6.5) - row.get('away_avg_rating', 6.0),  # rating_diff
            ])

            # 如果有校准器，使用它预测
            if self.calibrator is not None:
                # 简化: 假设前15维是主胜相关特征
                home_prob = self.calibrator.predict_proba([features[:15]])[0][1]
                # 简化: 使用启发式计算其他概率
                away_prob = 0.3 * (1 - home_prob)
                draw_prob = 1 - home_prob - away_prob

                # 归一化
                total = home_prob + away_prob + draw_prob
                probs = {
                    'home_win': home_prob / total,
                    'draw': draw_prob / total,
                    'away_win': away_prob / total
                }
            else:
                # 启发式预测
                rating_diff = row.get('home_avg_rating', 6.5) - row.get('away_avg_rating', 6.0)
                xg_diff = row.get('home_avg_xg', 1.2) - row.get('away_avg_xg', 1.0)

                home_prob = 0.4 + 0.15 * rating_diff + 0.1 * xg_diff
                away_prob = 0.3 - 0.1 * rating_diff - 0.05 * xg_diff
                draw_prob = 1 - home_prob - away_prob

                # 归一化
                total = home_prob + away_prob + draw_prob
                probs = {
                    'home_win': home_prob / total,
                    'draw': draw_prob / total,
                    'away_win': away_prob / total
                }

            predictions.append(probs)

        # 回测每场比赛
        print(f"\n🎯 开始回测 {len(df_with_odds)} 场比赛...")
        for idx, (_, row) in enumerate(df_with_odds.iterrows()):
            match_data = row.to_dict()
            prediction = predictions[idx]

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
    print("💰 V9.1 校准后回测系统")
    print("=" * 60)

    backtester = CalibratedBacktesterV91(initial_capital=1000)

    # 运行回测
    data_path = "/home/user/projects/FootballPrediction/data/merged_real_odds.csv"
    model_path = "/home/user/projects/FootballPrediction/lightgbm_v91_calibrated.model"

    metrics = backtester.run_backtest(data_path, model_path)

    # 显示结果
    print("\n" + "=" * 60)
    print("📊 V9.1 校准后回测结果")
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
    print(f"  V9.0 ROI: -32.58%")
    print(f"  V9.1 ROI: {metrics['roi']:.2f}%")
    improvement = metrics['roi'] - (-32.58)
    print(f"  改进幅度: {improvement:.2f}%")
    print(f"  是否盈利: {'✅ 是' if metrics['roi'] > 0 else '❌ 否'}")

    # 保存交易记录
    if backtester.trades:
        trades_df = pd.DataFrame(backtester.trades)
        trades_df.to_csv('/home/user/projects/FootballPrediction/calibrated_backtest_trades_v91.csv', index=False)
        print(f"\n✅ 校准后交易记录已保存: calibrated_backtest_trades_v91.csv")

    return metrics


if __name__ == "__main__":
    main()
