from typing import Any, Dict, List, Optional, Union

"""
比赛相关模型
Match Related Models
"""

from datetime import datetime

from pydantic import BaseModel, Field


class MatchQueryParams(BaseModel):
    """比赛查询参数"""

    league_id: Optional[int] = Field(None, description="联赛ID")
    team_id: Optional[int] = Field(None, description="球队ID")
    status: Optional[str] = Field(None, description="比赛状态")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")
    limit: int = Field(50, ge=1, le=1000, description="返回数量限制")
    offset: int = Field(0, ge=0, description="偏移量")


class MatchCreateRequest(BaseModel):
    """创建比赛请求"""

    home_team_id: int = Field(..., description="主队ID")
    away_team_id: int = Field(..., description="客队ID")
    league_id: int = Field(..., description="联赛ID")
    match_time: datetime = Field(..., description="比赛时间")
    venue: Optional[str] = Field(None, description="比赛场地")


class MatchUpdateRequest(BaseModel):
    """更新比赛请求"""

    match_time: Optional[datetime] = Field(None, description="比赛时间")
    venue: Optional[str] = Field(None, description="比赛场地")
    home_score: Optional[int] = Field(None, ge=0, description="主队得分")
    away_score: Optional[int] = Field(None, ge=0, description="客队得分")
    home_half_score: Optional[int] = Field(None, ge=0, description="主队半场得分")
    away_half_score: Optional[int] = Field(None, ge=0, description="客队半场得分")
    status: Optional[str] = Field(None, description="比赛状态")
