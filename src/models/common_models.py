"""
通用数据模型定义

提供项目中使用的通用数据结构和枚举类型：
- AnalysisResult: 分析结果数据模型
- Content: 内容数据模型
- ContentType: 内容类型枚举
- User: 用户数据模型
- UserProfile: 用户配置文件模型
- UserRole: 用户角色枚举
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


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


@dataclass
class AnalysisResult:
    """分析结果数据模型"""

    id: str
    analysis_type: str
    result: Dict[str, Any]
    confidence: float
    timestamp: datetime
    content_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "analysis_type": self.analysis_type,
            "result": self.result,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "content_id": self.content_id,
            "metadata": self.metadata or {},
        }


@dataclass
class Content:
    """内容数据模型"""

    id: str
    title: str
    content_type: ContentType
    data: Any
    created_at: datetime
    updated_at: Optional[datetime] = None
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "title": self.title,
            "content_type": self.content_type.value,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "tags": self.tags or [],
            "metadata": self.metadata or {},
        }


@dataclass
class UserProfile:
    """用户配置文件模型"""

    user_id: str
    display_name: str
    email: str
    preferences: Dict[str, Any]
    created_at: datetime
    last_login: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "email": self.email,
            "preferences": self.preferences,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }


@dataclass
class User:
    """用户数据模型"""

    id: str
    username: str
    role: UserRole
    profile: UserProfile
    is_active: bool = True
    created_at: Optional[datetime] = None

    def __post_init__(self):
        """初始化后处理"""
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role.value,
            "profile": self.profile.to_dict(),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def has_permission(self, permission: str) -> bool:
        """检查用户是否有指定权限"""
        # 管理员拥有所有权限
        if self.role == UserRole.ADMIN:
            return True

        # 版主拥有内容管理权限
        if self.role == UserRole.MODERATOR:
            return permission in ["read", "write", "moderate"]

        # 普通用户只有读写权限
        if self.role == UserRole.USER:
            return permission in ["read", "write"]

        # 访客只有读权限
        if self.role == UserRole.GUEST:
            return permission == "read"

        return False


@dataclass
class DataValidationResult:
    """数据验证结果模型"""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    validated_at: Optional[datetime] = None

    def __post_init__(self):
        """初始化后处理"""
        if self.validated_at is None:
            self.validated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "validated_at": (
                self.validated_at.isoformat() if self.validated_at else None
            ),
        }

    def add_error(self, error: str) -> None:
        """添加错误信息"""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """添加警告信息"""
        self.warnings.append(warning)

    def get_summary(self) -> str:
        """获取验证结果摘要"""
        return f"验证结果: {'有效' if self.is_valid else '无效'}, 错误: {len(self.errors)}, 警告: {len(self.warnings)}"


@dataclass
class FeatureVector:
    """特征向量模型"""

    match_id: str
    features: List[float]
    feature_names: Optional[List[str]] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        """初始化后处理"""
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "match_id": self.match_id,
            "features": self.features,
            "feature_names": self.feature_names or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def normalize(self) -> List[float]:
        """归一化特征向量"""
        if not self.features:
            return []

        min_val = min(self.features)
        max_val = max(self.features)

        if max_val == min_val:
            return [0.0] * len(self.features)

        return [(f - min_val) / (max_val - min_val) for f in self.features]

    def scale(self, factor: float) -> List[float]:
        """缩放特征向量"""
        return [f * factor for f in self.features]

    def get_statistics(self) -> Dict[str, float]:
        """获取特征向量统计信息"""
        if not self.features:
            return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}

        import statistics

        return {
            "mean": statistics.mean(self.features),
            "std": statistics.stdev(self.features) if len(self.features) > 1 else 0.0,
            "min": min(self.features),
            "max": max(self.features),
        }

    def is_empty(self) -> bool:
        """检查特征向量是否为空"""
        return len(self.features) == 0


@dataclass
class MatchData:
    """比赛数据模型"""

    match_id: str
    home_team: str
    away_team: str
    match_date: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    league: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "match_id": self.match_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "match_date": self.match_date,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "league": self.league,
        }

    def get_result(self) -> str:
        """获取比赛结果"""
        if self.home_score is None or self.away_score is None:
            return "unknown"

        if self.home_score > self.away_score:
            return "home_win"
        elif self.home_score < self.away_score:
            return "away_win"
        else:
            return "draw"

    def is_valid(self) -> bool:
        """验证比赛数据是否有效"""
        return (
            bool(self.match_id and self.match_id.strip())
            and bool(self.home_team and self.home_team.strip())
            and bool(self.away_team and self.away_team.strip())
            and self.home_team != self.away_team
            and bool(self.match_date and self.match_date.strip())
        )


@dataclass
class ModelMetrics:
    """模型指标模型"""

    accuracy: float
    precision: float
    recall: float
    f1_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
        }

    def get_overall_score(self) -> float:
        """计算综合评分"""
        return (self.accuracy + self.precision + self.recall + self.f1_score) / 4

    def is_better_than(self, other: "ModelMetrics") -> bool:
        """比较是否比另一个指标更好"""
        return self.get_overall_score() > other.get_overall_score()


@dataclass
class PredictionRequest:
    """预测请求模型"""

    match_id: str
    home_team: str
    away_team: str
    features: Optional[Dict[str, float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "match_id": self.match_id,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "features": self.features or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PredictionRequest":
        """从字典创建预测请求"""
        return cls(
            match_id=data.get("match_id", ""),
            home_team=data.get("home_team", ""),
            away_team=data.get("away_team", ""),
            features=data.get("features"),
        )

    def is_valid(self) -> bool:
        """验证预测请求是否有效"""
        return (
            bool(self.match_id and self.match_id.strip())
            and bool(self.home_team and self.home_team.strip())
            and bool(self.away_team and self.away_team.strip())
            and self.home_team != self.away_team
        )


@dataclass
class PredictionResponse:
    """预测响应模型"""

    match_id: str
    home_win_prob: float
    draw_prob: float
    away_win_prob: float
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "match_id": self.match_id,
            "home_win_prob": self.home_win_prob,
            "draw_prob": self.draw_prob,
            "away_win_prob": self.away_win_prob,
            "confidence": self.confidence,
        }

    def get_most_likely_outcome(self) -> str:
        """获取最可能的结果"""
        probabilities = {
            "home_win": self.home_win_prob,
            "draw": self.draw_prob,
            "away_win": self.away_win_prob,
        }
        return max(probabilities.items(), key=lambda x: x[1])[0]
