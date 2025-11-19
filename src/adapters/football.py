"""football 主模块
Football Main Module.

此文件由长文件拆分工具自动生成
拆分策略: complexity_split
"""

# 导入基础模型
from .adapters.football_models import (
    FootballData,
    MatchStatus,
)
from .adapters.football_models import (
    Match as FootballMatch,
)
from .adapters.football_models import (
    Player as FootballPlayer,
)
from .adapters.football_models import (
    Team as FootballTeam,
)

# 为了向后兼容，创建基础适配器类
from .base import BaseAdapter


class FootballDataAdapter(BaseAdapter):
    """足球数据适配器基类."""

    pass


class ApiFootballAdapter(FootballDataAdapter):
    """API Football适配器."""

    pass


class OptaDataAdapter(FootballDataAdapter):
    """Opta数据适配器."""

    pass


class CompositeFootballAdapter(FootballDataAdapter):
    """复合足球适配器."""

    pass


# 其他兼容类别名
class FootballApiAdapter(ApiFootballAdapter):
    pass


class ApiFootballAdaptee(FootballData):
    pass


class OptaDataAdaptee(FootballData):
    pass


class FootballApiAdaptee(FootballData):
    pass


class FootballDataTransformer:
    """足球数据转换器."""

    pass


# 导出所有公共接口
__all__ = [
    "MatchStatus",
    "FootballMatch",
    "FootballTeam",
    "FootballPlayer",
    "FootballData",
    "FootballApiAdaptee",
    "ApiFootballAdaptee",
    "OptaDataAdaptee",
    "FootballDataTransformer",
    "FootballApiAdapter",
    "ApiFootballAdapter",
    "OptaDataAdapter",
    "CompositeFootballAdapter",
    "FootballDataAdapter",
]
