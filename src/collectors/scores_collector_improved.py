"""
scores_collector_improved 主模块

此文件由长文件拆分工具自动生成

拆分策略: complexity_split
"""

# 导入拆分的模块
from .collectors.scores_collector_improved_services import *
from .collectors.scores_collector_improved_models import *
from .collectors.scores_collector_improved_utils import *

# 导出所有公共接口
__all__ = [
    "ScoresCollector",
    "ScoresCollectorManager",
    "get_scores_manager"
]