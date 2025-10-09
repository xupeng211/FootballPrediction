"""
common_models.py
通用数据模型

定义系统中使用的通用数据结构。
Defines common data structures used in the system.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class ContentType(Enum):
    """内容类型枚举"""

    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"


class UserRole(Enum):
    """用户角色枚举"""

    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    MODERATOR = "moderator"


class User(BaseModel):
    """用户模型"""

    id: Optional[int] = None
    username: str
    email: Optional[str] = None
    role: UserRole = UserRole.USER
    created_at: Optional[datetime] = None


class UserProfile(BaseModel):
    """用户档案"""

    user_id: int
    preferences: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}


class Content(BaseModel):
    """内容模型"""

    id: Optional[int] = None
    type: ContentType
    title: str
    content: str
    author_id: Optional[int] = None
    created_at: Optional[datetime] = None
    metadata: Dict[str, Any] = {}


class AnalysisResult(BaseModel):
    """分析结果模型"""

    id: Optional[str] = None
    content_id: Optional[int] = None
    analysis_type: str
    result: Dict[str, Any]
    confidence: Optional[float] = None
    created_at: Optional[datetime] = None


class DataValidationResult(BaseModel):
    """数据验证结果"""

    is_valid: bool
    errors: List[str] = []
    warnings: List[str] = []


class FeatureVector(BaseModel):
    """特征向量"""

    id: Optional[str] = None
    features: Dict[str, float]
    dimension: int
    metadata: Dict[str, Any] = {}


class MatchData(BaseModel):
    """比赛数据"""

    id: Optional[int] = None
    home_team: str
    away_team: str
    match_date: Optional[datetime] = None
    score: Optional[str] = None
    metadata: Dict[str, Any] = {}


class ModelMetrics(BaseModel):
    """模型指标"""

    model_name: str
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    metadata: Dict[str, Any] = {}


class PredictionRequest(BaseModel):
    """预测请求"""

    model_name: str
    input_data: Dict[str, Any]
    parameters: Dict[str, Any] = {}


class PredictionResponse(BaseModel):
    """预测响应"""

    prediction: Any
    confidence: Optional[float] = None
    model_name: str
    metadata: Dict[str, Any] = {}


# 导出所有类
__all__ = [
    "ContentType",
    "UserRole",
    "User",
    "UserProfile",
    "Content",
    "AnalysisResult",
    "DataValidationResult",
    "FeatureVector",
    "MatchData",
    "ModelMetrics",
    "PredictionRequest",
    "PredictionResponse",
]
