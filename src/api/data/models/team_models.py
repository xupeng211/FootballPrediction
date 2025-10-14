from typing import Any, Dict, List, Optional, Union
"""
球队相关模型
Team Related Models
"""


from pydantic import BaseModel, Field


class TeamQueryParams(BaseModel):
    """球队查询参数"""

    country: Optional[str] = Field(None, description="国家")
    is_active: Optional[bool] = Field(None, description="是否活跃")
    search: Optional[str] = Field(None, description="搜索关键词")
    limit: int = Field(50, ge=1, le=1000, description="返回数量限制")
    offset: int = Field(0, ge=0, description="偏移量")


class TeamCreateRequest(BaseModel):
    """创建球队请求"""

    name: str = Field(..., min_length=1, max_length=100, description="球队名称")
    country: Optional[str] = Field(None, max_length=50, description="国家")
    founded_year: Optional[int] = Field(None, ge=1800, le=2030, description="成立年份")
    stadium: Optional[str] = Field(None, max_length=100, description="球场名称")
    logo_url: Optional[str] = Field(None, max_length=255, description="队徽URL")


class TeamUpdateRequest(BaseModel):
    """更新球队请求"""

    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="球队名称"
    )
    country: Optional[str] = Field(None, max_length=50, description="国家")
    founded_year: Optional[int] = Field(None, ge=1800, le=2030, description="成立年份")
    stadium: Optional[str] = Field(None, max_length=100, description="球场名称")
    logo_url: Optional[str] = Field(None, max_length=255, description="队徽URL")
    is_active: Optional[bool] = Field(None, description="是否活跃")
