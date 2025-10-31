"""
common_models.py
此文件已被拆分为多个模块以提供更好的组织结构。
为了向后兼容,此文件重新导出所有模块中的类.
"""

import warnings
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# 从基础模块导入
from .base_models import base_models as base_models_mod
from src.common import api_models


# 基础配置
base_models = base_models_mod
data_models = api_models  # 别名以保持兼容性
utils = None  # 临时设置为 None 以避免导入错误

# 向后兼容警告
warnings.warn(
    "直接从 common_models 导入已弃用。请从 src/models/common 导入相关类.",
    DeprecationWarning,
    stacklevel=2,
)

# 导出列表
__all__ = [
    "base_models",
    "data_models",
    "DataValidationResult",
    "FeatureVector",
    "MatchData",
    "ModelMetrics",
    "APIResponse",
    "ErrorResponse",
]


class DataValidationResult(BaseModel):
    """数据验证结果"""

    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    def add_error(self, error: str):
        """函数文档字符串"""
        pass
  # 添加pass语句
        """添加错误"""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str):
        """函数文档字符串"""
        pass
  # 添加pass语句
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
        """函数文档字符串"""
        pass
  # 添加pass语句
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
        """函数文档字符串"""
        pass
  # 添加pass语句
        """更新指标"""
        self.total_predictions += predictions
        self.correct_predictions += correct
        self.accuracy = self.correct_predictions / self.total_predictions
        self.last_updated = datetime.utcnow()


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
