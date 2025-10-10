"""
pipeline.py
pipeline

此文件已被拆分为多个模块以提供更好的组织结构。
This file has been split into multiple modules for better organization.

为了向后兼容，此文件重新导出所有模块中的类。
For backward compatibility, this file re-exports all classes from the modules.
"""

import warnings

warnings.warn(
    "直接从 pipeline 导入已弃用。"
    "请从 src/services/data_processing/pipeline_mod 导入相关类。",
    DeprecationWarning,
    stacklevel=2,
)

# 从新模块导入所有内容
try:
    from ..data_processing.pipeline_mod import stages
    from ..data_processing.pipeline_mod import pipeline
    from ..data_processing.pipeline_mod import executor
    from ..data_processing.pipeline_mod import monitor
except ImportError:
    # 如果data_processing不是包，尝试直接导入
    import sys
    import os

    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "data_processing"))
    from pipeline_mod import stages
    from pipeline_mod import pipeline
    from pipeline_mod import executor
    from pipeline_mod import monitor

# 导出所有类
__all__ = ["stages", "pipeline", "executor", "monitor"]
