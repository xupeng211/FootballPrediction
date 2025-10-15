from typing import Any, Dict, List, Optional, Union

"""
数据收集器模块
负责从各种数据源收集足球相关数据
"""

from .fixtures_collector import FixturesCollector, FixturesCollectorFactory
from .odds_collector import OddsCollector, OddsCollectorFactory  # type: ignore
from .scores_collector import ScoresCollector, ScoresCollectorFactory

__all__ = [
    "FixturesCollector",
    "FixturesCollectorFactory",
    "OddsCollector",
    "OddsCollectorFactory",
    "ScoresCollector",
    "ScoresCollectorFactory",
]
