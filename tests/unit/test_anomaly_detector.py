from src.monitoring.anomaly_detector import AnomalyDetector

def test_anomaly_detector():
    detector = AnomalyDetector()
    assert detector is not None

def test_detection_methods():
    detector = AnomalyDetector()
    assert hasattr(detector, 'detect_anomaly')
    assert hasattr(detector, 'train_model')