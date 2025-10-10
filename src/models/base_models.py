"""
Base models
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class BaseModel(BaseModel):
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
