# 临时修复：factories文件缺失，先注释掉导入
# from .team_factory import TeamFactory
# from .league_factory import LeagueFactory
# from .match_factory import MatchFactory
# from .odds_factory import OddsFactory
# from .prediction_factory import PredictionFactory
# from .user_factory import UserFactory
# from .data_factory import DataFactory
# from .mock_factory import MockFactory

# 临时占位符
class TeamFactory:
    pass

class LeagueFactory:
    pass

class MatchFactory:
    pass

class OddsFactory:
    pass

class PredictionFactory:
    pass

class UserFactory:
    pass

class DataFactory:
    pass

class MockFactory:
    pass

"""
测试数据工厂
使用Factory Boy创建测试数据
"""

# 导入所有工厂类

# 便捷导入
__all__ = [
    "TeamFactory",
    "LeagueFactory",
    "MatchFactory",
    "OddsFactory",
    "PredictionFactory",
    "UserFactory",
    "DataFactory",
    "MockFactory",
]
