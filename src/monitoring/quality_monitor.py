"""
数据质量监控器 / Data Quality Monitor

负责监控数据新鲜度、缺失率、完整性等数据质量指标。
支持实时监控、历史趋势分析、质量评分计算等功能。

Responsible for monitoring data quality metrics such as freshness, missing rates, and completeness.
Supports real-time monitoring, historical trend analysis, and quality score calculation.

主要类 / Main Classes:
    QualityMonitor: 数据质量监控主类 / Main data quality monitoring class
    DataFreshnessResult: 数据新鲜度检查结果 / Data freshness check result
    DataCompletenessResult: 数据完整性检查结果 / Data completeness check result

主要方法 / Main Methods:
    QualityMonitor.check_data_freshness(): 检查数据新鲜度 / Check data freshness
    QualityMonitor.check_data_completeness(): 检查数据完整性 / Check data completeness
    QualityMonitor.calculate_overall_quality_score(): 计算总体质量评分 / Calculate overall quality score

使用示例 / Usage Example:
    ```python
    from src.monitoring.quality_monitor import QualityMonitor

    # 创建监控器实例
    monitor = QualityMonitor()

    # 检查数据新鲜度
    freshness_results = await monitor.check_data_freshness()

    # 检查数据完整性
    completeness_results = await monitor.check_data_completeness()

    # 计算总体质量评分
    quality_score = await monitor.calculate_overall_quality_score()
    ```

依赖 / Dependencies:
    - sqlalchemy: 数据库查询 / Database queries
    - src.database.connection: 数据库连接管理 / Database connection management
"""

from .quality.core.monitor import QualityMonitor
from .quality.core.results import DataFreshnessResult, DataCompletenessResult

# 为了保持向后兼容，重新导出新模块化的类

__all__ = [
    "QualityMonitor",
    "DataFreshnessResult",
    "DataCompletenessResult",
]
