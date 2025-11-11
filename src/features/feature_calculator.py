"""
feature_calculator 主模块

此文件由长文件拆分工具自动生成

拆分策略: component_split
"""

# 导入拆分的模块
try:
    from .calculators.feature_calculator_main import FeatureCalculator
except ImportError:
    from .feature_definitions import FeatureCalculator

# 导出所有公共接口
__all__ = ["FeatureCalculator"]
