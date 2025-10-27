"""
features_processor.py
features_processor

此文件已被拆分为多个模块以提供更好的组织结构。
This file has been split into multiple modules for better organization.

为了向后兼容，此文件重新导出所有模块中的类。
For backward compatibility, this file re-exports all classes from the modules.
"""

import warnings

from ............src.services.processing.processors.features import (
    aggregator, calculator, processor, validator)

warnings.warn(
    "直接从 features_processor 导入已弃用。"
    "请从 src/services/processing/processors/features 导入相关类。",
    DeprecationWarning,
    stacklevel=2,
)

# 从新模块导入所有内容

# 导出所有类
__all__ = ["calculator", "aggregator", "validator", "processor"]
