from src.monitoring.alert_manager import AlertManager


def test_alert_manager():
    manager = AlertManager()
    assert manager is not None


def test_alert_methods():
    manager = AlertManager()
    assert hasattr(manager, "send_alert")
    assert hasattr(manager, "check_thresholds")
