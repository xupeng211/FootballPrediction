"""
数据集成相关的Pydantic模型
"""

from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field


class DataCollectionRequest(BaseModel):
    """数据收集请求模型"""

    collection_type: str = Field(..., description="收集类型: all, team, league")
    days_ahead: int = Field(30, ge=1, le=365, description="向前收集的天数")
    force_refresh: bool = Field(False, description="是否强制刷新缓存")
    data_source: str = Field("mock", description="数据源名称")
    team_name: Optional[str] = Field(
        None, description="球队名称（当collection_type为team时）"
    )
    league_name: Optional[str] = Field(
        None, description="联赛名称（当collection_type为league时）"
    )


class DataCollectionResponse(BaseModel):
    """数据收集响应模型"""

    success: bool = Field(..., description="收集是否成功")
    message: str = Field(..., description="响应消息")
    collected_count: int = Field(..., description="收集到的数据数量")
    data_source: str = Field(..., description="使用的数据源")
    collection_type: str = Field(..., description="收集类型")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间")


class DataSourceStatusResponse(BaseModel):
    """数据源状态响应模型"""

    available_sources: List[str] = Field(..., description="可用的数据源列表")
    primary_source: str = Field(..., description="主要数据源")
    database_matches: int = Field(..., description="数据库中的比赛数量")
    database_teams: int = Field(..., description="数据库中的球队数量")
    last_update: Optional[str] = Field(None, description="最后更新时间")
    is_healthy: bool = Field(..., description="数据源是否健康")


class MatchResponse(BaseModel):
    """比赛响应模型"""

    id: int = Field(..., description="比赛ID")
    home_team: str = Field(..., description="主队名称")
    away_team: str = Field(..., description="客队名称")
    match_date: datetime = Field(..., description="比赛时间")
    league: str = Field(..., description="联赛名称")
    status: str = Field(..., description="比赛状态")
    home_score: Optional[int] = Field(None, description="主队得分")
    away_score: Optional[int] = Field(None, description="客队得分")
    venue: Optional[str] = Field(None, description="比赛场地")


class TeamResponse(BaseModel):
    """球队响应模型"""

    id: int = Field(..., description="球队ID")
    name: str = Field(..., description="球队名称")
    short_name: Optional[str] = Field(None, description="简称")
    venue: Optional[str] = Field(None, description="主场")
    website: Optional[str] = Field(None, description="官网")


class DataSourceTestResponse(BaseModel):
    """数据源测试响应模型"""

    success: bool = Field(..., description="测试是否成功")
    data_source: str = Field(..., description="数据源名称")
    test_matches: int = Field(..., description="测试获取的比赛数量")
    test_teams: int = Field(..., description="测试获取的球队数量")
    message: str = Field(..., description="测试结果消息")
    error: Optional[str] = Field(None, description="错误信息")


class DataStatsResponse(BaseModel):
    """数据统计响应模型"""

    total_matches: int = Field(..., description="总比赛数")
    upcoming_matches: int = Field(..., description="即将开始的比赛数")
    live_matches: int = Field(..., description="进行中的比赛数")
    finished_matches: int = Field(..., description="已结束的比赛数")
    total_teams: int = Field(..., description="总球队数")
    total_leagues: int = Field(..., description="总联赛数")
    data_source: dict = Field(..., description="数据源状态")
    last_updated: datetime = Field(..., description="最后更新时间")
