"""
改进的实时比分收集器
Improved Real-time Scores Collector

提供高性能的实时比分数据收集功能，支持：
- 多数据源集成
- WebSocket实时推送
- 数据去重和验证
- 异常处理和重试
- 性能优化

Provides high-performance real-time scores collection with:
- Multi-source integration
- WebSocket real-time push
- Data deduplication and validation
- Error handling and retry
- Performance optimization

⚠️ 注意：此文件已重构为模块化结构。
为了向后兼容性，这里保留了原始的导入接口。
建议使用：from src.collectors.scores import ScoresCollector

"""

# 为了向后兼容性，从新的模块化结构中导入所有类

# 重新导出以保持原始接口
__all__ = ["ScoresCollector", "ScoresCollectorManager", "get_scores_manager"]


# 原始实现已移至 src/collectors/scores/collector.py
# 此处保留仅用于向后兼容性
# 请使用新的模块化结构以获得更好的维护性

class _ScoresCollectorCompat(ScoresCollector):
    """
    向后兼容性包装器。
    建议直接使用从 src.collectors.scores 导入的 ScoresCollector。
    """
    pass

# 如果需要直接使用原始接口，请使用别名
ScoresCollector = _ScoresCollectorCompat


# 原始管理器实现已移至 src/collectors/scores/manager.py
# 此处保留仅用于向后兼容性
class _ScoresCollectorManagerCompat(ScoresCollectorManager):
    """
    向后兼容性包装器。
    建议直接使用从 src.collectors.scores 导入的 ScoresCollectorManager。
    """
    pass

from .scores.collector import ScoresCollector
from .scores.manager import ScoresCollectorManager, get_scores_manager

# 使用别名保持向后兼容性
ScoresCollectorManager = _ScoresCollectorManagerCompat
