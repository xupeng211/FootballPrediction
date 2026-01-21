"""
Processors - 特征处理器插件模块
================================

所有特征处理器的统一入口。

V22.0 新增:
    - LineupValueProcessor: 阵容价值处理器（50+维）
    - AdvancedPassingProcessor: 深度传球处理器（60+维）

V23.0 新增:
    - MarketOddsProcessor: 市场赔率与偏见处理器（30+维）
    - InjuryImpactProcessor: 战损与伤停深度处理器（40+维）

V24.0 新增:
    - HistoricalRollingProcessor: 历史追溯处理器（120+维）
    - TacticalCrossProcessor: 战术交叉处理器（500+维）

作者: FootballPrediction Architecture Team
版本: V24.0-alpha
"""

from .atomic import AtomicProcessor
from .context import ContextProcessor

# V24.0 新增
from .history import HistoricalRollingProcessor
from .injury_impact import InjuryImpactProcessor
from .lineup import LineupProcessor
from .lineup_value import LineupValueProcessor

# V23.0 新增
from .market_odds import MarketOddsProcessor
from .passing_dna import AdvancedPassingProcessor
from .referee import RefereeProcessor
from .tactical import TacticalProcessor
from .tactical_cross import TacticalCrossProcessor

__all__ = [
    "AdvancedPassingProcessor",
    "AtomicProcessor",
    "ContextProcessor",
    # V24.0 新增
    "HistoricalRollingProcessor",
    "InjuryImpactProcessor",
    "LineupProcessor",
    # V22.0 新增
    "LineupValueProcessor",
    # V23.0 新增
    "MarketOddsProcessor",
    "RefereeProcessor",
    "TacticalCrossProcessor",
    "TacticalProcessor",
]
