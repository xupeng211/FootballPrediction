"""feature_calculator 主模块.

此文件由长文件拆分工具自动生成

拆分策略: component_split
"""

# 导入拆分的模块
try:
    from src.features.features.feature_calculator_calculators import FeatureCalculator
except ImportError:
    # 如果拆分模块不存在，提供一个简单的占位符
    class FeatureCalculator:
        """FeatureCalculator 占位符实现."""

        def __init__(self, *args, **kwargs):
            pass


# 导出所有公共接口
__all__ = ["FeatureCalculator"]
