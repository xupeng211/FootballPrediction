"""



"""







    """获取模块信息"""




异常检测器 - 向后兼容性包装器
Anomaly Detector - Backward Compatibility Wrapper
⚠️  警告:此文件已被重构为模块化结构
⚠️  Warning: This file has been refactored into a modular structure
新的实现位于 src/monitoring/anomaly/ 目录下:
- models.py - 异常模型定义
- detector.py - 主检测器
- methods.py - 检测方法实现
- analyzers.py - 数据分析器
- summary.py - 异常摘要生成器
此文件保留用于向后兼容性,建议新代码直接导入新的模块.
# 从新的模块化结构导入所有功能
    AnomalyType,
    AnomalySeverity,
    AnomalyResult,
    AnomalyDetector,
    ThreeSigmaDetector,
    IQRDetector,
    ZScoreDetector,
    RangeDetector,
    FrequencyDetector,
    TimeGapDetector,
    TableAnalyzer,
    ColumnAnalyzer,
    AnomalySummarizer,
)
logger = logging.getLogger(__name__)
# =============================================================================
# 向后兼容性别名
# =============================================================================
# 为了保持向后兼容,保持原有的导入路径
__all__ = [
    # Enums
    "AnomalyType",
    "AnomalySeverity",
    # Result class
    "AnomalyResult",
    # Main detector
    "AnomalyDetector",
]
# =============================================================================
# 模块信息
# =============================================================================
def get_module_info() -> Dict[str, Any]:
    return {
        "module": "anomaly_detector",
        "status": "refactored", Dict, List, Optional
        "message": "This module has been refactored into a modular structure",
        "new_location": "src.monitoring.anomaly",
        "components": [
            "models - Anomaly data models (AnomalyType, AnomalySeverity, AnomalyResult)",
            "detector - Main detector class",
            "methods - Detection algorithms (3σ, IQR, Z-score, etc.)",
            "analyzers - Table and column analyzers",
            "summary - Anomaly summary generator",
        ],
        "migration_guide": {
            "old_import": "from src.monitoring.anomaly_detector import XXX",
            "new_import": "from src.monitoring.anomaly import XXX",
        },
        "enhanced_features": [
            "More modular structure for better maintainability",
            "Separate detection methods for easier testing",
            "Enhanced anomaly summary with recommendations",
            "Better separation of concerns",
        ],
    }
# 记录模块加载信息
logger.info(
    "Loading anomaly_detector module (deprecated) - "
    "consider importing from src.monitoring.anomaly instead"
)