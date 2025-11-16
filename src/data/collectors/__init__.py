"""数据采集器模块.

实现足球数据的采集功能，包括:
- DataCollector: 抽象基类，定义统一的采集接口
- FixturesCollector: 赛程数据采集，防重复防丢失
- OddsCollector: 赔率数据采集,高频更新去重
- ScoresCollector: 实时比分采集,WebSocket或轮询

基于 DATA_DESIGN.md 第1节设计实现.
"""

from .base_collector import BaseCollector
from .fixtures_collector import FixturesCollector
from .odds_collector import OddsCollector
from .scores_collector import ScoresCollector

__all__ = [
    "BaseCollector",
    "FixturesCollector",
    "OddsCollector",
    "ScoresCollector",
]
