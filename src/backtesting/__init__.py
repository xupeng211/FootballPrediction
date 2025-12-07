"""
回测系统模块 (Backtesting System)

提供历史数据回测功能，用于评估预测策略的盈利能力。

主要组件:
- BacktestEngine: 核心回测引擎
- StrategyProtocol: 策略接口定义
- Portfolio: 资金管理和下注记录
- SimpleValueStrategy: 默认价值投资策略

作者: Backtesting Engineer (P2-4)
创建时间: 2025-12-06
版本: 1.0.0
"""

from .engine import BacktestEngine
from .strategy import StrategyProtocol, SimpleValueStrategy
from .portfolio import Portfolio
from .models import BetDecision, BetResult, BacktestResult

__all__ = [
    "BacktestEngine",
    "StrategyProtocol",
    "SimpleValueStrategy",
    "Portfolio",
    "BetDecision",
    "BetResult",
    "BacktestResult",
]
