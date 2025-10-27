"""
common_models.py
common_models

此文件已被拆分为多个模块以提供更好的组织结构。
This file has been split into multiple modules for better organization.

为了向后兼容，此文件重新导出所有模块中的类。
For backward compatibility, this file re-exports all classes from the modules.
"""

import warnings
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from ..common import api_models
# from ..api.data.models import api_models  # 已重构，移除此导入
from .base_models import base_models as base_models_mod

# utils 模块不存在，注释掉以避免导入错误
# from ..common import utils

# 为了向后兼容
base_models = base_models_mod
data_models = api_models  # 别名以保持兼容性
utils = None  # 临时设置为 None 以避免导入错误

warnings.warn(
    "直接从 common_models 导入已弃用。请从 src/models/common 导入相关类。",
    DeprecationWarning,
    stacklevel=2,
)

# 从新模块导入所有内容

# 从 database.models 导入 User 以保持兼容性
from ..database.models import User
# 从 services.content_analysis 导入 Content, ContentType, AnalysisResult, UserProfile 和 UserRole 以保持兼容性
from ..services.content_analysis import (AnalysisResult, Content, ContentType,
                                         UserProfile, UserRole)

# 导出所有类
__all__ = [
    "base_models",
    "data_models",
    "Content",
    "ContentType",
    "AnalysisResult",
    "UserProfile",
    "UserRole",
    "User",
    "DataValidationResult",
    "FeatureVector",
    "MatchData",
    "ModelMetrics",
]


class DataValidationResult(BaseModel):
    """数据验证结果"""

    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    def add_error(self, error: str):
        """添加错误"""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str):
        """添加警告"""
        self.warnings.append(warning)


class FeatureVector(BaseModel):
    """特征向量"""

    match_id: int
    features: Dict[str, float]
    feature_names: List[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def get_feature(self, name: str) -> Optional[float]:
        """获取特征值"""
        return self.features.get(name)

    def set_feature(self, name: str, value: float):
        """设置特征值"""
        self.features[name] = value
        if name not in self.feature_names:
            self.feature_names.append(name)


class MatchData(BaseModel):
    """比赛数据"""

    match_id: int
    home_team: str
    away_team: str
    league: str
    match_date: datetime
    status: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    odds: Optional[Dict[str, float]] = None
    features: Optional[FeatureVector] = None


class ModelMetrics(BaseModel):
    """模型指标"""

    model_name: str
    model_version: str
    accuracy: float = Field(ge=0, le=1)
    precision: float = Field(ge=0, le=1)
    recall: float = Field(ge=0, le=1)
    f1_score: float = Field(ge=0, le=1)
    total_predictions: int
    correct_predictions: int
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    @property
    def error_rate(self) -> float:
        """错误率"""
        return 1 - self.accuracy

    def update_metrics(self, predictions: int, correct: int):
        """更新指标"""
        self.total_predictions += predictions
        self.correct_predictions += correct
        self.accuracy = self.correct_predictions / self.total_predictions
        self.last_updated = datetime.utcnow()


from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class APIResponse(BaseModel):
    """通用API响应模型"""

    success: bool = True
    message: str = "Success"
    data: Optional[Any] = None
    timestamp: datetime = datetime.utcnow()


class ErrorResponse(BaseModel):
    """错误响应模型"""

    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[dict] = None
    timestamp: datetime = datetime.utcnow()
