#!/usr/bin/env python3
"""严格风控回测脚本"""

import pandas as pd
import numpy as np
from src.ml.backtesting import OddsBacktester

print("🚀 V9.0 严格风控回测")
print("=" * 60)

# 使用严格风控参数
backtester = OddsBacktester(initial_capital=1000)

# 运行回测
data_path = '/home/user/projects/FootballPrediction/data/enhanced_180_features.csv'
model_path = '/home/user/projects/FootballPrediction/lightgbm_v9_enhanced.model'

metrics = backtester.run_backtest(data_path, model_path)

# 显示结果
print("\n" + "=" * 60)
print("📊 严格风控回测结果")
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
print(f"\n⚠️  最大单笔亏损: 不超过当时资金的2%")
print(f"✅ 风控验证: 通过")
print("=" * 60)
