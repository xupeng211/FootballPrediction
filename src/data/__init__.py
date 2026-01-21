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
    # 标准化器
    "DataFormatNormalizer",
    # 验证器
    "DataValidator",
    "ValidationIssue",
    "ValidationResult",
    "ValidationSeverity",
    "detect_data_format",
    "normalize_match_data",
    "validate_batch",
]
