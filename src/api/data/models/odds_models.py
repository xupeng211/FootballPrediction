from pydantic import BaseModel, Field

"""
赔率相关模型
Odds Related Models
"""


class OddsQueryParams(BaseModel):
    """赔率查询参数"""

    bookmaker: str | None = Field(None, description="博彩公司")
    market_type: str | None = Field(None, description="市场类型")
    limit: int = Field(50, ge=1, le=1000, description="返回数量限制")
    offset: int = Field(0, ge=0, description="偏移量")
