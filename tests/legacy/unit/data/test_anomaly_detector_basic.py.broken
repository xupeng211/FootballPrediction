from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from src.data.quality import anomaly_detector as module


class MetricStub:
    def __init__(self):
        self.calls = []

    def labels(self, **labels):
        return MetricHandle(self.calls, labels)


class MetricHandle:
    def __init__(self, calls, labels):
        self.calls = calls
        self.labels = labels

    def inc(self, value=1):
        self.calls.append(("inc", self.labels, value))

    def observe(self, value):
        self.calls.append(("observe", self.labels, value))

    def set(self, value):
        self.calls.append(("set", self.labels, value))


@pytest.fixture
def metrics_stub(monkeypatch):
    counter = MetricStub()
    gauge = MetricStub()
    histogram = MetricStub()
    monkeypatch.setattr(module, "anomalies_detected_total", counter)
    monkeypatch.setattr(module, "data_drift_score", gauge)
    monkeypatch.setattr(module, "anomaly_detection_duration_seconds", histogram)
    return counter, gauge, histogram


def test_detect_outliers_3sigma_no_anomaly(metrics_stub):
    detector = module.StatisticalAnomalyDetector()
    series = pd.Series([100, 101, 99, 100, 102, 98], dtype=float)

    result = detector.detect_outliers_3sigma(series, "matches", "home_score")

    assert result.statistics["outliers_count"] == 0
    assert result.severity in {"low", "medium"}
    counter_calls, _, hist_calls = metrics_stub
    assert counter_calls.calls[0][2] == 0
    assert any(call[0] == "observe" for call in hist_calls.calls)


def test_detect_outliers_3sigma_with_anomaly(metrics_stub):
    detector = module.StatisticalAnomalyDetector()
    data = [100] * 100 + [300]  # single outlier in large sample
    series = pd.Series(data, dtype=float)

    result = detector.detect_outliers_3sigma(series, "matches", "home_score")

    assert result.statistics["outliers_count"] == 1
    assert any(rec["value"] == 300 for rec in result.anomalous_records)
    counter_calls, _, _ = metrics_stub
    assert counter_calls.calls[0][2] == 1


def test_detect_outliers_3sigma_empty(metrics_stub):
    detector = module.StatisticalAnomalyDetector()
    series = pd.Series(dtype=float)

    with pytest.raises(ValueError):
        detector.detect_outliers_3sigma(series, "matches", "home_score")


def test_detect_data_drift_no_shift(metrics_stub):
    detector = module.MachineLearningAnomalyDetector()
    baseline = pd.DataFrame(
        {
            "feature_a": np.linspace(0, 1, 50),
            "feature_b": np.linspace(1, 2, 50),
        }
    )
    current = baseline.copy()

    results = detector.detect_data_drift(
        baseline, current, "matches", drift_threshold=0.2
    )

    assert results == []
    _, gauge_calls, hist_calls = metrics_stub
    assert len([call for call in gauge_calls.calls if call[0] == "set"]) >= 2
    assert any(call[0] == "observe" for call in hist_calls.calls)


def test_detect_data_drift_with_shift(metrics_stub):
    detector = module.MachineLearningAnomalyDetector()
    baseline = pd.DataFrame(
        {
            "feature_a": np.zeros(50),
            "feature_b": np.ones(50),
        }
    )
    current = pd.DataFrame(
        {
            "feature_a": np.ones(50) * 5,
            "feature_b": np.zeros(50),
        }
    )

    results = detector.detect_data_drift(
        baseline, current, "matches", drift_threshold=0.1
    )

    assert results, "Expected drift detection results"
    drift_columns = {
        record["column"] for result in results for record in result.anomalous_records
    }
    assert drift_columns == {"feature_a", "feature_b"}
    for result in results:
        assert result.severity in {"critical", "high", "medium"}
    counter_calls, _, _ = metrics_stub
    assert len([call for call in counter_calls.calls if call[0] == "inc"]) >= 2


def test_detect_outliers_3sigma_log_transform(metrics_stub, monkeypatch):
    detector = module.StatisticalAnomalyDetector()
    series = pd.Series([1.0, 1.5, 2.0, 500000.0], dtype=float)

    log_called = {}

    original_log1p = module.np.log1p

    def tracking_log1p(values):
        log_called["count"] = len(values)
        return original_log1p(values)

    monkeypatch.setattr(module.np, "log1p", tracking_log1p)

    result = detector.detect_outliers_3sigma(series, "odds", "home_odds")

    assert log_called  # ensure log transform path executed
    assert result.statistics["total_records"] == 4


def test_isolation_forest_detects(metrics_stub):
    detector = module.MachineLearningAnomalyDetector()
    rng = np.random.default_rng(seed=42)
    normal = rng.normal(0, 1, (100, 2))
    outliers = np.array([[8, 8], [9, 9]])
    data = pd.DataFrame(
        np.vstack([normal, outliers]), columns=["feature_a", "feature_b"]
    )

    result = detector.detect_anomalies_isolation_forest(
        data, "matches", contamination=0.05, random_state=42
    )

    assert result.statistics["total_records"] == len(data)
    assert result.statistics["anomalies_count"] >= 1
    indices = {record["index"] for record in result.anomalous_records}
    assert indices.intersection({len(data) - 1, len(data) - 2})


def test_detect_distribution_shift_detects(metrics_stub):
    detector = module.StatisticalAnomalyDetector()
    baseline = pd.Series(np.random.normal(0, 1, 200))
    current = pd.Series(np.random.normal(5, 1, 200))

    result = detector.detect_distribution_shift(
        baseline, current, "matches", "home_score", significance_level=0.05
    )

    assert result.statistics["distribution_shifted"] is True
    assert result.severity in {"critical", "high", "medium"}
    assert result.anomalous_records


def test_dbscan_clustering_detects(metrics_stub):
    detector = module.MachineLearningAnomalyDetector()
    rng = np.random.default_rng(seed=7)
    cluster_a = rng.normal(loc=0, scale=0.05, size=(20, 2))
    cluster_b = rng.normal(loc=1, scale=0.05, size=(20, 2))
    noise = np.array([[5, 5], [6, 6]])
    data = pd.DataFrame(
        np.vstack([cluster_a, cluster_b, noise]), columns=["metric_a", "metric_b"]
    )

    result = detector.detect_anomalies_clustering(
        data, "matches", eps=0.2, min_samples=5
    )

    assert result.statistics["anomalies_count"] >= 2
    indices = {record["index"] for record in result.anomalous_records}
    assert indices.intersection({len(data) - 1, len(data) - 2})


def test_isolation_forest_requires_numeric(metrics_stub):
    detector = module.MachineLearningAnomalyDetector()
    data = pd.DataFrame({"category": ["home", "away", "draw"]})

    with pytest.raises(ValueError, match="没有可用的数值列"):
        detector.detect_anomalies_isolation_forest(data, "matches")


def test_dbscan_requires_numeric(metrics_stub):
    detector = module.MachineLearningAnomalyDetector()
    data = pd.DataFrame({"flag": ["a", "b", "c", "d", "e"]})

    with pytest.raises(ValueError, match="没有可用的数值列"):
        detector.detect_anomalies_clustering(data, "matches")


def test_detect_outliers_iqr(metrics_stub):
    detector = module.StatisticalAnomalyDetector()
    series = pd.Series([10, 11, 12, 13, 14, 200], dtype=float)

    result = detector.detect_outliers_iqr(series, "matches", "shots")

    assert result.statistics["outliers_count"] >= 1
    assert any(rec["value"] == 200 for rec in result.anomalous_records)


@pytest.mark.asyncio
async def test_advanced_anomaly_detector_comprehensive(monkeypatch, metrics_stub):
    detector = module.AdvancedAnomalyDetector()
    detector.db_manager = SimpleNamespace()  # unused due to monkeypatching
    detector.detection_config = {
        "matches": {
            "enabled_methods": [
                "3sigma",
                "iqr",
                "data_drift",
                "distribution_shift",
            ],
            "key_columns": ["home_score"],
            "drift_baseline_days": 7,
        }
    }

    async def fake_get_table_data(table_name, hours):
        return pd.DataFrame({"home_score": [1.0, 2.0, 3.0]})

    async def fake_get_total_records(table_name):
        return 30

    async def fake_get_baseline(table_name, baseline_days):
        return pd.DataFrame({"home_score": [0.5, 0.6, 0.7]})

    monkeypatch.setattr(detector, "_get_table_data", fake_get_table_data)
    monkeypatch.setattr(detector, "_get_total_records", fake_get_total_records)
    monkeypatch.setattr(detector, "_get_baseline_data", fake_get_baseline)

    detector.statistical_detector.detect_outliers_3sigma = MagicMock(
        return_value=module.AnomalyDetectionResult(
            "matches", "3sigma", "statistical_outlier"
        )
    )
    detector.statistical_detector.detect_outliers_iqr = MagicMock(
        return_value=module.AnomalyDetectionResult(
            "matches", "iqr", "statistical_outlier"
        )
    )
    detector.statistical_detector.detect_distribution_shift = MagicMock(
        return_value=module.AnomalyDetectionResult(
            "matches", "ks_test", "distribution_shift"
        )
    )
    detector.ml_detector.detect_data_drift = MagicMock(
        return_value=[
            module.AnomalyDetectionResult("matches", "data_drift", "feature_drift")
        ]
    )

    results = await detector.run_comprehensive_detection("matches", time_window_hours=1)

    assert len(results) == 4
    methods = {result.detection_method for result in results}
    assert methods == {"3sigma", "iqr", "data_drift", "ks_test"}


def test_detect_data_drift_no_numeric_columns(metrics_stub):
    detector = module.MachineLearningAnomalyDetector()
    baseline = pd.DataFrame({"category": ["a", "b", "c"]})
    current = baseline.copy()

    results = detector.detect_data_drift(baseline, current, "matches")

    assert results == []
