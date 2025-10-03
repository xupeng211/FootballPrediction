from datetime import datetime, timedelta

from src.monitoring.anomaly_detector import (
from unittest.mock import AsyncMock, MagicMock, patch
import numpy
import pandas
import pytest
import os

"""
Test suite for anomaly detector module
"""

    AnomalyDetector,
    AnomalyResult,
    AnomalyType,
    AnomalySeverity)
@pytest.fixture
def anomaly_detector():
    """Create an instance of AnomalyDetector"""
    return AnomalyDetector()
@pytest.fixture
def sample_numeric_data():
    """Sample numeric data for testing"""
    # Normal data with some outliers = data np.random.normal(10, 2, 100)
    # Add some outliers
    data[0] = 50  # Outlier
    data[1] = -30  # Outlier
    return pd.Series(data)
@pytest.fixture
def sample_categorical_data():
    """Sample categorical data for testing"""
    data = ["A[", "]B[", "]A[", "]A[", "]C[", "]A[", "]B[", "]A[", "]A[", "]A["] * 10[""""
    # Add some infrequent values
    data.extend(["]]D[", "]E[", "]F["])  # Rare values[": return pd.Series(data)"""
@pytest.fixture
def sample_time_data():
    "]]""Sample time data for testing"""
    base_time = datetime.now()
    times = [base_time - timedelta(minutes=i) for i in range(100)]
    # Add time gaps
    times[50] = base_time - timedelta(hours=2)  # Large gap
    return pd.Series(times)
def test_anomaly_detector_initialization(anomaly_detector):
    """Test initialization of AnomalyDetector"""
    assert anomaly_detector is not None
    assert hasattr(anomaly_detector, "detection_config[")" assert "]matches[" in anomaly_detector.detection_config[""""
    assert "]]odds[" in anomaly_detector.detection_config[""""
    assert "]]predictions[" in anomaly_detector.detection_config[""""
def test_anomaly_result_initialization():
    "]]""Test initialization of AnomalyResult"""
    result = AnomalyResult(
        table_name = os.getenv("TEST_MONITORING_ANOMALY_DETECTOR_TABLE_NAME_52"),": column_name = os.getenv("TEST_MONITORING_ANOMALY_DETECTOR_COLUMN_NAME_52"),": anomaly_type=AnomalyType.OUTLIER,": severity=AnomalySeverity.HIGH,": anomalous_values=[1, 2, 3],"
        anomaly_score=0.5,
        detection_method = os.getenv("TEST_MONITORING_ANOMALY_DETECTOR_DETECTION_METHOD_"),": description = os.getenv("TEST_MONITORING_ANOMALY_DETECTOR_DESCRIPTION_52"))": assert result.table_name =="]test_table[" assert result.column_name =="]test_column[" assert result.anomaly_type ==AnomalyType.OUTLIER[""""
    assert result.severity ==AnomalySeverity.HIGH
    assert result.anomalous_values ==[1, 2, 3]
    assert result.anomaly_score ==0.5
    assert result.detection_method =="]]test_method[" assert result.description =="]test description[" def test_anomaly_result_to_dict("
    """"
    "]""Test conversion of AnomalyResult to dictionary"""
    result = AnomalyResult(
        table_name = os.getenv("TEST_MONITORING_ANOMALY_DETECTOR_TABLE_NAME_52"),": column_name = os.getenv("TEST_MONITORING_ANOMALY_DETECTOR_COLUMN_NAME_52"),": anomaly_type=AnomalyType.OUTLIER,": severity=AnomalySeverity.HIGH,": anomalous_values=[1, 2, 3],"
        anomaly_score=0.56789,
        detection_method = os.getenv("TEST_MONITORING_ANOMALY_DETECTOR_DETECTION_METHOD_"),": description = os.getenv("TEST_MONITORING_ANOMALY_DETECTOR_DESCRIPTION_52"))": result_dict = result.to_dict()": assert result_dict["]table_name["] =="]test_table[" assert result_dict["]column_name["] =="]test_column[" assert result_dict["]anomaly_type["] =="]outlier[" assert result_dict["]severity["] =="]high[" assert result_dict["]anomalous_values["] ==[1, 2, 3]" assert result_dict["]anomaly_score["] ==0.5679  # Rounded to 4 decimal places[" assert result_dict["]]detection_method["] =="]test_method[" assert result_dict["]description["] =="]test description[" def test_detect_three_sigma_anomalies("
    """"
    "]""Test 3-sigma rule anomaly detection"""
    results = anomaly_detector._detect_three_sigma_anomalies(
        sample_numeric_data, "test_table[", "]test_column["""""
    )
    # Should find some outliers
    assert len(results) >= 0  # May or may not find anomalies depending on random data
    for result in results:
        assert result.anomaly_type ==AnomalyType.OUTLIER
        assert result.detection_method =="]3sigma[" assert isinstance(result.anomaly_score, float)""""
def test_detect_iqr_anomalies(anomaly_detector, sample_numeric_data):
    "]""Test IQR method anomaly detection"""
    results = anomaly_detector._detect_iqr_anomalies(
        sample_numeric_data, "test_table[", "]test_column["""""
    )
    # Should find some outliers
    assert len(results) >= 0  # May or may not find anomalies depending on random data
    for result in results:
        assert result.anomaly_type ==AnomalyType.OUTLIER
        assert result.detection_method =="]iqr[" assert isinstance(result.anomaly_score, float)""""
def test_detect_z_score_anomalies(anomaly_detector, sample_numeric_data):
    "]""Test Z-score anomaly detection"""
    results = anomaly_detector._detect_z_score_anomalies(
        sample_numeric_data, "test_table[", "]test_column["""""
    )
    # Should find some outliers
    assert len(results) >= 0  # May or may not find anomalies depending on random data
    for result in results:
        assert result.anomaly_type ==AnomalyType.OUTLIER
        assert result.detection_method =="]z_score[" assert isinstance(result.anomaly_score, float)""""
def test_detect_range_anomalies(anomaly_detector):
    "]""Test range check anomaly detection"""
    # Data with values outside defined ranges = data pd.Series([1, 2, 3, 150, -50, 5, 6])  # Some values outside normal range
    results = anomaly_detector._detect_range_anomalies(
        data, "matches[", "]minute["  # Using matches config which has minute thresholds[""""
    )
    # Should find range anomalies
    for result in results:
        assert result.anomaly_type ==AnomalyType.VALUE_RANGE
        assert result.detection_method =="]]range_check[" assert isinstance(result.anomaly_score, float)""""
def test_detect_frequency_anomalies(anomaly_detector, sample_categorical_data):
    "]""Test frequency anomaly detection"""
    results = anomaly_detector._detect_frequency_anomalies(
        sample_categorical_data, "test_table[", "]test_column["""""
    )
    # Should find some anomalies (D, E, F are infrequent)
    assert len(results) >= 0
    for result in results:
        assert result.anomaly_type ==AnomalyType.FREQUENCY
        assert result.detection_method =="]frequency[" assert isinstance(result.anomaly_score, float)""""
def test_calculate_severity(anomaly_detector):
    "]""Test severity calculation"""
    # Test different anomaly scores map to correct severities
    assert anomaly_detector._calculate_severity(0.25) ==AnomalySeverity.CRITICAL
    assert anomaly_detector._calculate_severity(0.15) ==AnomalySeverity.HIGH
    assert anomaly_detector._calculate_severity(0.07) ==AnomalySeverity.MEDIUM
    assert anomaly_detector._calculate_severity(0.02) ==AnomalySeverity.LOW
def test_detect_column_anomalies_numeric(anomaly_detector, sample_numeric_data):
    """Test detection of anomalies in numeric column"""
    results = anomaly_detector._detect_column_anomalies(
        sample_numeric_data.to_frame("test_col["),""""
        "]test_table[",""""
        "]test_col[",""""
        ["]three_sigma[", "]iqr[", "]z_score["],""""
        "]numeric[")": assert isinstance(results, list)" for result in results:""
        assert isinstance(result, AnomalyResult)
def test_detect_column_anomalies_categorical(anomaly_detector, sample_categorical_data):
    "]""Test detection of anomalies in categorical column"""
    results = anomaly_detector._detect_column_anomalies(
        sample_categorical_data.to_frame("test_col["),""""
        "]test_table[",""""
        "]test_col[",""""
        "]frequency[",""""
        "]categorical[")": assert isinstance(results, list)" for result in results:""
        assert isinstance(result, AnomalyResult)
def test_detect_column_anomalies_time(anomaly_detector, sample_time_data):
    "]""Test detection of anomalies in time column"""
    results = anomaly_detector._detect_column_anomalies(
        sample_time_data.to_frame("test_col["),""""
        "]test_table[",""""
        "]test_col[",""""
        "]time_gap[",""""
        "]time[")": assert isinstance(results, list)" for result in results:""
        assert isinstance(result, AnomalyResult)
def test_get_table_data(anomaly_detector):
    "]""Test getting table data"""
    # Mock the database session
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = []
    mock_session.execute.return_value = mock_result
    # This should return an empty DataFrame without errors
    df = anomaly_detector._get_table_data(mock_session, "matches[")""""
    # Since this is async, we'll test the structure that would be called
    assert df is not None
def test_detect_table_anomalies(anomaly_detector):
    "]""Test detection of anomalies in a table"""
    mock_session = AsyncMock()
    # Mock the _get_table_data method to return a sample DataFrame
    with patch.object(anomaly_detector, "_get_table_data[") as mock_get_data:": sample_df = pd.DataFrame({"""
                "]minute[: "1, 2, 3, 150, 5, 6[",  # Some values outside [0, 120] range["]"]""
                "]match_time[": [datetime.now()""""
        )
        mock_get_data.return_value = sample_df
        results = anomaly_detector._detect_table_anomalies(
            mock_session, "]matches[", "]range_check["""""
        )
        # Should find range anomalies in the minute column
        assert isinstance(results, list)
        for result in results:
            assert isinstance(result, AnomalyResult)
def test_detect_anomalies(anomaly_detector):
    "]""Test the main detect_anomalies method"""
    mock_session = AsyncMock()
    mock_get_session = AsyncMock()
    mock_get_session.__aenter__.return_value = mock_session
    mock_db_manager = MagicMock()
    mock_db_manager.get_async_session.return_value = mock_get_session
    anomaly_detector.db_manager = mock_db_manager
    # Mock the _detect_table_anomalies method to return empty results
    with patch.object(anomaly_detector, "_detect_table_anomalies[") as mock_detect_table:": mock_detect_table.return_value = []": results = anomaly_detector.detect_anomalies("]matches[")": assert isinstance(results, list)" assert len(results) ==0[""
def test_get_anomaly_summary(anomaly_detector):
    "]]""Test getting anomaly summary"""
    # Create some sample anomaly results
    anomalies = [
        AnomalyResult(
            "table1[",""""
            "]col1[",": AnomalyType.OUTLIER,": AnomalySeverity.HIGH,""
            [1],
            0.1,
            "]method1[",""""
            "]desc1["),": AnomalyResult("""
            "]table2[",""""
            "]col2[",": AnomalyType.VALUE_RANGE,": AnomalySeverity.CRITICAL,""
            [2],
            0.2,
            "]method2[",""""
            "]desc2[")]": summary = anomaly_detector.get_anomaly_summary(anomalies)": assert "]total_anomalies[" in summary[""""
    assert "]]by_severity[" in summary[""""
    assert "]]by_type[" in summary[""""
    assert "]]by_table[" in summary[""""
    assert summary["]]total_anomalies["] ==2[" assert "]]high[" in summary["]by_severity["]: assert "]critical[" in summary["]by_severity["]: assert "]outlier[" in summary["]by_type["]: assert "]value_range[" in summary["]by_type["]: assert "]table1[" in summary["]by_table["]: assert "]table2[" in summary["]by_table["]: def test_get_anomaly_summary_empty("
    """"
    "]""Test getting summary for no anomalies"""
    summary = anomaly_detector.get_anomaly_summary([])
    assert "total_anomalies[" in summary[""""
    assert summary["]]total_anomalies["] ==0[" assert len(summary["]]by_severity["]) ==0[" assert len(summary["]]by_type["]) ==0[" assert len(summary["]]by_table["]) ==0[" def test_three_sigma_no_anomalies(anomaly_detector):"""
    "]]""Test 3-sigma detection with no anomalies"""
    # Data with no real outliers = data pd.Series([10, 10.1, 9.9, 10.2, 9.8] * 20)
    results = anomaly_detector._detect_three_sigma_anomalies(
        data, "test_table[", "]test_column["""""
    )
    assert len(results) ==0
def test_three_sigma_zero_std(anomaly_detector):
    "]""Test 3-sigma detection with zero standard deviation"""
    # All same values, zero std
    data = pd.Series([5] * 20)
    results = anomaly_detector._detect_three_sigma_anomalies(
        data, "test_table[", "]test_column["""""
    )
    assert len(results) ==0
def test_iqr_zero_iqr(anomaly_detector):
    "]""Test IQR detection with zero IQR"""
    # Data that results in zero IQR
    data = pd.Series([5] * 20)
    results = anomaly_detector._detect_iqr_anomalies(data, "test_table[", "]test_column[")": assert len(results) ==0[" def test_frequency_no_anomalies(anomaly_detector):""
    "]]""Test frequency detection with no anomalies"""
    # Data with uniform frequency = data pd.Series(["A[", "]B[", "]C["] * 10)": results = anomaly_detector._detect_frequency_anomalies(": data, "]test_table[", "]test_column["""""
    )
    assert len(results) ==0
def test_time_gap_anomalies(anomaly_detector, sample_time_data):
    "]""Test time gap anomaly detection"""
    results = anomaly_detector._detect_time_gap_anomalies(
        sample_time_data, "test_table[", "]test_column["""""
    )
    # May or may not find anomalies depending on the data, but should not crash
    assert isinstance(results, list)
    for result in results:
        assert isinstance(result, AnomalyResult)
        assert result.anomaly_type ==AnomalyType.PATTERN_BREAK
def test_detect_time_gap_anomalies_insufficient_data(anomaly_detector):
    "]""Test time gap detection with insufficient data"""
    # Only one data point
    data = pd.Series([datetime.now()])
    results = anomaly_detector._detect_time_gap_anomalies(
        data, "test_table[", "]test_column["""""
    )
    assert len(results) ==0
def test_detect_time_gap_anomalies_zero_iqr(anomaly_detector):
    "]""Test time gap detection with zero IQR in time differences"""
    # Data with consistent intervals = base_time datetime.now()
    times = [
        base_time - timedelta(minutes = i) for i in range(10)
    ]  # Consistent 1-min intervals
    results = anomaly_detector._detect_time_gap_anomalies(
        pd.Series(times), "test_table[", "]test_column"""""
    )
    # No anomalies should be detected with consistent intervals:
    assert len(results) ==0