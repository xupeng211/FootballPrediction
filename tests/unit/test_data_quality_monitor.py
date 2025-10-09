from src.data.quality.data_quality_monitor import DataQualityMonitor

def test_data_quality_monitor():
    monitor = DataQualityMonitor()
    assert monitor is not None

def test_monitoring_methods():
    monitor = DataQualityMonitor()
    assert hasattr(monitor, 'check_quality')
    assert hasattr(monitor, 'report_issues')