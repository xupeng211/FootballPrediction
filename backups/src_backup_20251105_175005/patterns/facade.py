"""facade 主模块.

此文件由长文件拆分工具自动生成

拆分策略: complexity_split
"""

# 导入拆分的模块
from .patterns.facade_models import *  # TODO: Convert to explicit imports

# 导出所有公共接口
__all__ = [
    "PredictionRequest",
    "PredictionResult",
    "DataCollectionConfig",
    "PredictionFacade",
    "DataCollectionFacade",
    "AnalyticsFacade",
    "FacadeFactory",
]
