"""
测试数据工厂
使用Factory Boy创建测试数据
"""

# 导入所有工厂类
from .team_factory import TeamFactory
from .league_factory import LeagueFactory
from .match_factory import MatchFactory
from .odds_factory import OddsFactory
from .prediction_factory import PredictionFactory
from .user_factory import UserFactory

# 便捷导入
__all__ = [
    "TeamFactory",
    "LeagueFactory",
    "MatchFactory",
    "OddsFactory",
    "PredictionFactory",
    "UserFactory",
]
