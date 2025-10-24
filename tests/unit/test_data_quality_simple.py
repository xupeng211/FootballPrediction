# 数据质量简单测试
from src.data.quality.anomaly_detector import AnomalyDetector
from src.data.quality.data_quality_monitor import DataQualityMonitor


def test_anomaly_detector():
    detector = AnomalyDetector()
    assert detector is not None


def test_data_quality_monitor():
    monitor = DataQualityMonitor()
    assert monitor is not None


def test_quality_checks():
    # 测试质量检查相关方法
    monitor = DataQualityMonitor()
    assert hasattr(monitor, "check_data_quality")
