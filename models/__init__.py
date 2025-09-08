"""
AICultureKit 数据模型模块

提供系统中使用的数据模型，包括：
- 用户模型
- 内容模型
- 分析结果模型
- 配置模型
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class ContentType(Enum):
    """内容类型枚举"""

    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"


class UserRole(Enum):
    """用户角色枚举"""

    VIEWER = "viewer"
    CREATOR = "creator"
    ADMIN = "admin"
    ANALYST = "analyst"


@dataclass
class User:
    """用户模型"""

    id: str
    username: str
    email: str
    role: UserRole = UserRole.VIEWER
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class Content:
    """内容模型"""

    id: str
    title: str
    content_type: ContentType
    content_data: Union[str, bytes, Dict[str, Any]]
    author_id: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "title": self.title,
            "content_type": self.content_type.value,
            "content_data": self.content_data,
            "author_id": self.author_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": (self.updated_at.isoformat() if self.updated_at else None),
            "tags": self.tags,
            "metadata": self.metadata,
        }


@dataclass
class AnalysisResult:
    """分析结果模型"""

    id: str
    content_id: str
    analysis_type: str
    result_data: Dict[str, Any]
    confidence_score: float
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "content_id": self.content_id,
            "analysis_type": self.analysis_type,
            "result_data": self.result_data,
            "confidence_score": self.confidence_score,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class UserProfile:
    """用户画像模型"""

    user_id: str
    interests: List[str] = field(default_factory=list)
    preferences: Dict[str, Any] = field(default_factory=dict)
    behavior_patterns: Dict[str, Any] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "user_id": self.user_id,
            "interests": self.interests,
            "preferences": self.preferences,
            "behavior_patterns": self.behavior_patterns,
            "updated_at": self.updated_at.isoformat(),
        }


__all__ = [
    "ContentType",
    "UserRole",
    "User",
    "Content",
    "AnalysisResult",
    "UserProfile",
]
