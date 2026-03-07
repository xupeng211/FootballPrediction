#!/usr/bin/env python3
"""
L2 特征提取器模块 (Legacy 兼容层)
===================================

⚠️  V4.13 声明：此模块为遗留兼容层，仅限维护脚本调用。
新代码请使用 Node.js 特征引擎 (src/feature_engine/)

提供统一的特征提取接口，支持策略模式和工厂模式。

使用示例:
    >>> from src.ml.feature_engine.legacy import ExtractorRegistry, BaseExtractor
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
Version: V26.0 (Legacy)
Date: 2025-12-27
"""

# V4.13: 使用相对路径导入
from .base_extractor import (
    BaseExtractor,
    ExtractionResult,
    ExtractionStatus,
    ExtractorRegistry,
    ValidationConfig,
    register_extractor,
)
from .exceptions import (
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
from .integrity_guard import (
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
__version__ = "V26.0 (Legacy)"
