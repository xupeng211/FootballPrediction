"""
联赛相关模型
League Related Models
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class LeagueQueryParams(BaseModel):
    """联赛查询参数"""

    country: Optional[str] = Field(None, description="国家")
    season: Optional[str] = Field(None, description="赛季")
    is_active: Optional[bool] = Field(None, description="是否活跃")
    search: Optional[str] = Field(None, description="搜索关键词")
    limit: int = Field(50, ge=1, le=1000, description="返回数量限制")
    offset: int = Field(0, ge=0, description="偏移量")


class LeagueCreateRequest(BaseModel):
    """创建联赛请求"""

    name: str = Field(..., min_length=1, max_length=100, description="联赛名称")
    country: str = Field(..., max_length=50, description="国家")
    season: str = Field(..., max_length=20, description="赛季")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")
