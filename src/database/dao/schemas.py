"""
DAO层的Pydantic模式定义
DAO Layer Pydantic Schema Definitions

定义用于数据传输和验证的Pydantic模型。
这些模型用于DAO层的输入输出接口。
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, validator


class MatchBase(BaseModel):
    """比赛基础模式"""

    home_team: str = Field(..., min_length=1, max_length=100, description="主队名称")
    away_team: str = Field(..., min_length=1, max_length=100, description="客队名称")
    league_id: Optional[int] = Field(None, description="联赛ID")
    match_time: datetime = Field(..., description="比赛时间")
    venue: Optional[str] = Field(None, max_length=200, description="比赛场地")
    status: str = Field("scheduled", description="比赛状态")

    @validator('status')
    def validate_status(cls, v):
        """验证比赛状态"""
        allowed_statuses = ['scheduled', 'live', 'finished', 'postponed', 'cancelled']
        if v not in allowed_statuses:
            raise ValueError(f'比赛状态必须是以下之一: {allowed_statuses}')
        return v


class MatchCreate(MatchBase):
    """创建比赛模式"""

    pass


class MatchUpdate(BaseModel):
    """更新比赛模式"""

    home_team: Optional[str] = Field(None, min_length=1, max_length=100)
    away_team: Optional[str] = Field(None, min_length=1, max_length=100)
    league_id: Optional[int] = None
    match_time: Optional[datetime] = None
    venue: Optional[str] = Field(None, max_length=200)
    status: Optional[str] = None

    @validator('status')
    def validate_status(cls, v):
        """验证比赛状态"""
        if v is None:
            return v
        allowed_statuses = ['scheduled', 'live', 'finished', 'postponed', 'cancelled']
        if v not in allowed_statuses:
            raise ValueError(f'比赛状态必须是以下之一: {allowed_statuses}')
        return v


class MatchResponse(MatchBase):
    """比赛响应模式"""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# 导出所有模式
__all__ = [
    'MatchBase',
    'MatchCreate',
    'MatchUpdate',
    'MatchResponse'
]