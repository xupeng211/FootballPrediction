"""Shared public feature-adapter types.

The legacy import surface is preserved by src.ml.feature_adapter.

lifecycle: permanent
"""

# These type diagnostics predate this mechanical extraction; do not change the
# public type surface while relocating the compatibility definitions.
# mypy: disable_error_code="type-arg"

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np
import pandas as pd


class ModelType(str, Enum):  # noqa -- public compatibility enum; StrEnum would change supported runtime behavior.
    """支持的模型类型"""

    V19_ROLLING = "v19_rolling"  # 48 维滚动特征
    V26_BASELINE = "v26_baseline"  # 6000 维特征
    V26_MINI = "v26_mini"  # 微型特征集（用于快速验证）
    V26_5_PRODUCTION = "v26_5_production"  # V26.5 生产模型（37 维真实特征）
    V26_6_PRE_MATCH = "v26_6_pre_match"  # V26.6 真赛前模型（19 维，无泄露）


@dataclass
class AdaptationResult:
    """
    特征适配结果

    Attributes:
        success: 是否成功
        features: 适配后的特征矩阵
        feature_names: 特征名称列表
        missing_features: 缺失的特征列表
        errors: 错误信息
    """

    success: bool
    features: pd.DataFrame | np.ndarray | None
    feature_names: list[str]
    missing_features: list[str]
    errors: list[str]
    canonical_diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """转换为字典"""
        payload = {
            "success": self.success,
            "feature_count": len(self.feature_names),
            "missing_features": self.missing_features,
            "errors": self.errors,
        }
        if self.canonical_diagnostics:
            payload["canonical_diagnostics"] = self.canonical_diagnostics
        return payload


class BaseFeatureAdapter(ABC):
    """特征适配器基类"""

    @abstractmethod
    def adapt(self, raw_features: dict[str, Any]) -> AdaptationResult:
        """
        将原始特征适配为目标模型所需的特征

        Args:
            raw_features: V25.1 提取的原始特征字典

        Returns:
            AdaptationResult: 适配结果
        """

    @abstractmethod
    def get_required_features(self) -> list[str]:
        """获取目标模型所需的特征列表"""


# Preserve the historical public module identity for callers that introspect
# or serialize these public compatibility symbols.
_PUBLIC_FACADE_MODULE = "src.ml.feature_adapter"
ModelType.__module__ = _PUBLIC_FACADE_MODULE
AdaptationResult.__module__ = _PUBLIC_FACADE_MODULE
BaseFeatureAdapter.__module__ = _PUBLIC_FACADE_MODULE
