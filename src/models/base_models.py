from typing import Any, Dict, List, Optional, Union
"""
Base models
"""

from datetime import datetime
from pydantic import BaseModel
import types


class BaseModel(BaseModel):  # type: ignore
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


# 创建一个简单的模块对象以保持向后兼容
base_models = types.SimpleNamespace(
    BaseModel=BaseModel,
    TimestampedModel=TimestampedModel,
    IdentifiableModel=IdentifiableModel,
    StatusModel=StatusModel,
    MetadataModel=MetadataModel,
)
