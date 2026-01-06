"""
V35.0 生产级建模模块
====================

整合经过验证的建模逻辑：
- trainer_v2: XGBoost + LightGBM + Platt Scaling
- backtest_engine: 回测引擎

作者: V35.0 Architecture Team
版本: V35.0 Production
"""

from .backtest_engine import BacktestConfig, BacktestEngine, BacktestMetrics

__all__ = [
    "BacktestConfig",
    "BacktestEngine",
    "BacktestMetrics",
]
