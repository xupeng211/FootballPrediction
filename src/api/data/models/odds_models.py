from typing import Any, Dict, List, Optional, Union

"""
赔率相关模型
Odds Related Models
"""


from pydantic import BaseModel, Field


class OddsQueryParams(BaseModel):
    """赔率查询参数"""

    bookmaker: Optional[str] = Field(None, description="博彩公司")
    market_type: Optional[str] = Field(None, description="市场类型")
    limit: int = Field(50, ge=1, le=1000, description="返回数量限制")
    offset: int = Field(0, ge=0, description="偏移量")
