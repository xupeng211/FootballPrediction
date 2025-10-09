from src.monitoring.quality_monitor import QualityMonitor

def test_quality_monitor():
    monitor = QualityMonitor()
    assert monitor is not None

def test_quality_checks():
    monitor = QualityMonitor()
    assert hasattr(monitor, 'check_data_quality')
    assert hasattr(monitor, 'generate_report')