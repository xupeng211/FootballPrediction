"""
数据API模块
Data API Module

提供完整的数据管理API接口，包括：
- 比赛数据查询
- 球队数据查询
- 联赛数据查询
- 比分和赔率数据
- 数据统计和分析
"""

from .models.common import TeamInfo, LeagueInfo, MatchInfo, OddsInfo
from .matches.routes import router as matches_router
from .teams.routes import router as teams_router
from .leagues.routes import router as leagues_router
from .odds.routes import router as odds_router
from .statistics.routes import router as statistics_router

# 创建主路由器并整合所有子路由
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/data", tags=["data"])

# 整合所有子路由
router.include_router(matches_router, prefix="/matches", tags=["matches"])
router.include_router(teams_router, prefix="/teams", tags=["teams"])
router.include_router(leagues_router, prefix="/leagues", tags=["leagues"])
router.include_router(odds_router, tags=["odds"])
router.include_router(statistics_router, prefix="/statistics", tags=["statistics"])

# 导出所有模型
__all__ = [
    "router",
    "TeamInfo",
    "LeagueInfo",
    "MatchInfo",
    "OddsInfo",
]