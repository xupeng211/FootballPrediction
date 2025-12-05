from typing import Optional

"""Models package for API data models with enhanced validation logic."""

# 传统模型（向后兼容）
try:
    from .league_models import LeagueQueryParams
    from .match_models import MatchQueryParams
    from .odds_models import OddsQueryParams
    from .team_models import TeamQueryParams
except ImportError:
    # 如果传统模型不存在，创建基本的占位符类
    from pydantic import BaseModel

    class LeagueQueryParams(BaseModel):
        id: int
        name: str
        country: str

    class MatchQueryParams(BaseModel):
        home_team: str
        away_team: str

    class OddsQueryParams(BaseModel):
        match_id: int
        home_win: float

    class TeamQueryParams(BaseModel):
        id: int
        name: str

# 增强版模型（新增业务验证）
try:
    from .enhanced_match_models import (
        EnhancedMatchQueryParams,
        EnhancedMatchCreateRequest,
        EnhancedMatchUpdateRequest,
        EnhancedMatchResponse,
        MatchDataQualityReport
    )
    from .enhanced_odds_models import (
        EnhancedOddsQueryParams,
        EnhancedOddsCreateRequest,
        EnhancedOddsUpdateRequest,
        EnhancedOddsResponse,
        OddsDataQualityReport
    )
    from .enhanced_team_models import (
        EnhancedTeamQueryParams,
        EnhancedTeamCreateRequest,
        EnhancedTeamUpdateRequest,
        EnhancedTeamResponse,
        TeamDataQualityReport
    )
    from .data_quality import (
        DataQualityReport,
        DataQualityConfig,
        create_quality_report,
        validate_dataset
    )
except ImportError as e:
    print(f"Warning: Could not import enhanced models: {e}")

    # 如果增强版模型不存在，创建占位符类
    from pydantic import BaseModel

    class EnhancedMatchQueryParams(BaseModel):
        id: int
        name: str

    class EnhancedOddsQueryParams(BaseModel):
        id: int
        match_id: int

    class EnhancedTeamQueryParams(BaseModel):
        id: int
        name: str

# 向后兼容的别名
LeagueInfo = LeagueQueryParams
MatchInfo = MatchQueryParams
OddsInfo = OddsQueryParams
TeamInfo = TeamQueryParams

# 导出所有模型
__all__ = [
    # 传统查询参数模型
    "LeagueQueryParams",
    "MatchQueryParams",
    "OddsQueryParams",
    "TeamQueryParams",

    # 向后兼容别名
    "LeagueInfo",
    "MatchInfo",
    "OddsInfo",
    "TeamInfo",

    # 增强版模型（如果可用）
    "EnhancedMatchQueryParams",
    "EnhancedMatchCreateRequest",
    "EnhancedMatchUpdateRequest",
    "EnhancedMatchResponse",
    "EnhancedOddsQueryParams",
    "EnhancedOddsCreateRequest",
    "EnhancedOddsUpdateRequest",
    "EnhancedOddsResponse",
    "EnhancedTeamQueryParams",
    "EnhancedTeamCreateRequest",
    "EnhancedTeamUpdateRequest",
    "EnhancedTeamResponse",

    # 数据质量工具
    "MatchDataQualityReport",
    "OddsDataQualityReport",
    "TeamDataQualityReport",
    "DataQualityReport",
    "DataQualityConfig",
    "create_quality_report",
    "validate_dataset",
]
