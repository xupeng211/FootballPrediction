import types
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# 创建一个简单的模块对象以保持向后兼容

from datetime import datetime

from sqlalchemy import Column, DateTime


"""
Base models
"""


class FootballBaseModel(BaseModel):
    """Base model class"""

    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TimestampedModel(BaseModel):
    """Timestamped base model"""

    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()


class IdentifiableModel(BaseModel):
    """Identifiable base model"""

    id: int
    name: str
    description: Optional[str] = None


class StatusModel(BaseModel):
    """Status base model"""

    status: str = "active"
    is_enabled: bool = True


class MetadataModel(BaseModel):
    """Metadata base model"""

    metadata: Dict[str, Any] = {}
    tags: List[str] = []


base_models = types.SimpleNamespace(
    BaseModel=FootballBaseModel,
    TimestampedModel=TimestampedModel,
    IdentifiableModel=IdentifiableModel,
    StatusModel=StatusModel,
    MetadataModel=MetadataModel,
)


class TimestampMixin:
    """时间戳混入类"""

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
