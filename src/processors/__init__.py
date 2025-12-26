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
Version: V25.0
Date: 2025-12-26
"""

from src.processors.base_extractor import (
    BaseExtractor,
    ExtractionResult,
    ExtractionStatus,
    ValidationConfig,
    ExtractorRegistry,
    register_extractor,
)

from src.processors.exceptions import (
    ExtractionError,
    ValidationError,
    InsufficientFeaturesError,
    MissingRequiredKeyError,
    DataParsingError,
    SchemaMismatchError,
    ConfigurationError,
    CircuitBreakerOpenError,
    RateLimitError,
)

__all__ = [
    # 抽象基类
    "BaseExtractor",
    # 结果类型
    "ExtractionResult",
    "ExtractionStatus",
    # 配置
    "ValidationConfig",
    # 工厂
    "ExtractorRegistry",
    "register_extractor",
    # 异常
    "ExtractionError",
    "ValidationError",
    "InsufficientFeaturesError",
    "MissingRequiredKeyError",
    "DataParsingError",
    "SchemaMismatchError",
    "ConfigurationError",
    "CircuitBreakerOpenError",
    "RateLimitError",
]

# 版本信息
__version__ = "V25.0"
