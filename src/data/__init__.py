"""
数据处理模块

提供数据验证、标准化和预处理功能。
"""

from .preprocessors.data_normalizer import (
    DataFormatNormalizer,
    detect_data_format,
    normalize_match_data,
)
from .validators.data_validator import (
    DataValidator,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    validate_batch,
)

__all__ = [
    # 验证器
    "DataValidator",
    "ValidationResult",
    "ValidationIssue",
    "ValidationSeverity",
    "validate_batch",
    # 标准化器
    "DataFormatNormalizer",
    "normalize_match_data",
    "detect_data_format",
]
