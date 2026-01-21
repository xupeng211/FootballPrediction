#!/usr/bin/env python3
"""
L2 特征提取器模块

提供统一的特征提取接口，支持策略模式和工厂模式。

使用示例:
    >>> from src.processors import ExtractorRegistry, BaseExtractor
    >>>
    >>> # 创建提取器实例
    >>> extractor = ExtractorRegistry.create("V25.0")
    >>>
    >>> # 提取特征
    >>> result = extractor.extract_with_validation(raw_data)
    >>>
    >>> # 获取特征
    >>> features = result.features

Author: Architecture Team
Version: V26.0 (Stable)
Date: 2025-12-27
"""

from src.processors.base_extractor import (
    BaseExtractor,
    ExtractionResult,
    ExtractionStatus,
    ExtractorRegistry,
    ValidationConfig,
    register_extractor,
)
from src.processors.exceptions import (
    CircuitBreakerOpenError,
    ConfigurationError,
    DataParsingError,
    ExtractionError,
    InsufficientFeaturesError,
    MissingRequiredKeyError,
    RateLimitError,
    SchemaMismatchError,
    ValidationError,
)
from src.processors.integrity_guard import (
    BatchAuditor,
    GoldenShieldConfig,
    IntegrityGuard,
    ValidationResult,
)

__all__ = [
    # 抽象基类
    "BaseExtractor",
    "BatchAuditor",
    "CircuitBreakerOpenError",
    "ConfigurationError",
    "DataParsingError",
    # 异常
    "ExtractionError",
    # 结果类型
    "ExtractionResult",
    "ExtractionStatus",
    # 工厂
    "ExtractorRegistry",
    # V41.350: Integrity Guard (Golden Shield)
    "GoldenShieldConfig",
    "InsufficientFeaturesError",
    "IntegrityGuard",
    "MissingRequiredKeyError",
    "RateLimitError",
    "SchemaMismatchError",
    # 配置
    "ValidationConfig",
    "ValidationError",
    "ValidationResult",
    "register_extractor",
]

# 版本信息
__version__ = "V26.0 (Stable)"
