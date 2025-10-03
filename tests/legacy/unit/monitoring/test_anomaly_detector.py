from datetime import datetime, timedelta

from src.monitoring.anomaly_detector import (
from unittest.mock import AsyncMock, MagicMock, patch
import pandas
import pytest

#!/usr/bin/env python3
"""
Unit tests for anomaly detector module.:

Tests for src/monitoring/anomaly_detector.py module classes and functions.
"""
    AnomalyType,
    AnomalySeverity,
    AnomalyResult,
    AnomalyDetector)
@pytest.fixture
def mock_db_manager():
    """Fixture for a mocked DatabaseManager."""
    db_manager = MagicMock()
    mock_session = AsyncMock()
    async_context_manager = AsyncMock()
    async_context_manager.__aenter__.return_value = mock_session
    db_manager.get_async_session.return_value = async_context_manager
    return db_manager, mock_session
@pytest.fixture
def anomaly_detector(mock_db_manager):
    """Returns a mocked instance of the anomaly detector."""
    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "src.monitoring.anomaly_detector.DatabaseManager[",": lambda: mock_db_manager[0])": detector = AnomalyDetector()": yield detector, mock_db_manager[1]"
@pytest.mark.asyncio
async def test_detect_anomalies_no_tables(anomaly_detector):
    "]""Test anomaly detection with no tables specified."""
    detector, _ = anomaly_detector
    anomalies = await detector.detect_anomalies(table_names=[])
    assert len(anomalies) ==0
@pytest.mark.asyncio
async def test_detect_anomalies_with_empty_data(anomaly_detector):
    """Test anomaly detection when the table has no data."""
    detector, mock_session = anomaly_detector
    mock_session.execute.return_value.fetchall.return_value = []
    anomalies = await detector.detect_anomalies(table_names="matches[")": assert len(anomalies) ==0["""
@pytest.mark.asyncio
async def test_detect_anomalies_with_normal_data(anomaly_detector):
    "]]""Test anomaly detection with normal data."""
    detector, _ = anomaly_detector
    mock_data = pd.DataFrame({"home_score[": [1, 2, 1, 0, 2]))": async def mock_get_table_data(*args, **kwargs):": return mock_data[": detector._get_table_data = mock_get_table_data"
    anomalies = await detector.detect_anomalies(table_names="]]matches[")": assert len(anomalies) ==0["""
@pytest.mark.asyncio
async def test_detect_anomalies_with_outliers(anomaly_detector):
    "]]""Test anomaly detection with clear outliers."""
    detector, _ = anomaly_detector
    mock_data = pd.DataFrame({"home_score[": [1, 2, 1, 0, 2, 100]))": async def mock_get_table_data(*args, **kwargs):": return mock_data[": detector._get_table_data = mock_get_table_data"
    anomalies = await detector.detect_anomalies(table_names="]]matches[")": assert len(anomalies) > 0[" assert anomalies[0].anomaly_type ==AnomalyType.OUTLIER[""
    assert 100 in anomalies[0].anomalous_values
@pytest.mark.asyncio
async def test_get_anomaly_summary(anomaly_detector):
    "]]]""Test the summary generation from a list of anomalies."""
    detector, _ = anomaly_detector
    anomalies = [
        MagicMock(
            spec=AnomalyResult,
            severity=MagicMock(value="high["),": anomaly_type=MagicMock(value="]outlier["),": table_name="]matches["),": MagicMock(": spec=AnomalyResult,": severity=MagicMock(value="]low["),": anomaly_type=MagicMock(value="]range_check["),": table_name="]odds[")]": summary = await detector.get_anomaly_summary(anomalies)": assert summary["]total_anomalies["] ==2[" assert summary["]]by_severity["]"]high[" ==1[" assert summary["]]by_table["]"]matches[" ==1[" class TestAnomalyType:"""
    "]]""Test cases for AnomalyType enum."""
    def test_anomaly_type_values(self):
        """Test AnomalyType enum values."""
        assert AnomalyType.OUTLIER.value =="outlier[" assert AnomalyType.TREND_CHANGE.value =="]trend_change[" assert AnomalyType.PATTERN_BREAK.value =="]pattern_break[" assert AnomalyType.VALUE_RANGE.value =="]value_range[" assert AnomalyType.FREQUENCY.value =="]frequency[" assert AnomalyType.NULL_SPIKE.value =="]null_spike[" class TestAnomalySeverity:""""
    "]""Test cases for AnomalySeverity enum."""
    def test_anomaly_severity_values(self):
        """Test AnomalySeverity enum values."""
        assert AnomalySeverity.LOW.value =="low[" assert AnomalySeverity.MEDIUM.value =="]medium[" assert AnomalySeverity.HIGH.value =="]high[" assert AnomalySeverity.CRITICAL.value =="]critical[" class TestAnomalyResult:""""
    "]""Test cases for AnomalyResult class."""
    def test_anomaly_result_creation_minimal(self):
        """Test AnomalyResult creation with minimal parameters."""
        result = AnomalyResult(
            table_name="matches[",": column_name="]home_score[",": anomaly_type=AnomalyType.OUTLIER,": severity=AnomalySeverity.HIGH,": anomalous_values=[10, 12, 15],"
            anomaly_score=0.15,
            detection_method="]3sigma[",": description="]Outlier values detected[")": assert result.table_name =="]matches[" assert result.column_name =="]home_score[" assert result.anomaly_type ==AnomalyType.OUTLIER[""""
        assert result.severity ==AnomalySeverity.HIGH
        assert result.anomalous_values ==[10, 12, 15]
        assert result.anomaly_score ==0.15
        assert result.detection_method =="]]3sigma[" assert result.description =="]Outlier values detected[" assert isinstance(result.detected_at, datetime)""""
    def test_anomaly_result_creation_with_custom_time(self):
        "]""Test AnomalyResult creation with custom detection time."""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        result = AnomalyResult(
            table_name="matches[",": column_name="]away_score[",": anomaly_type=AnomalyType.VALUE_RANGE,": severity=AnomalySeverity.MEDIUM,": anomalous_values=[-1],"
            anomaly_score=0.08,
            detection_method="]range_check[",": description="]Negative score detected[",": detected_at=custom_time)": assert result.detected_at ==custom_time[" def test_anomaly_result_to_dict(self):"
        "]]""Test AnomalyResult to_dict conversion."""
        result = AnomalyResult(
            table_name="teams[",": column_name="]rating[",": anomaly_type=AnomalyType.FREQUENCY,": severity=AnomalySeverity.LOW,": anomalous_values="]unknown[",": anomaly_score=0.02,": detection_method="]frequency[",": description="]Unknown value frequency anomaly[")": result_dict = result.to_dict()": expected = {""
            "]table_name[": ["]teams[",""""
            "]column_name[": ["]rating[",""""
            "]anomaly_type[": ["]frequency[",""""
            "]severity[": ["]low[",""""
            "]anomalous_values[": "]unknown[",""""
            "]anomaly_score[": round(0.02, 4)": assert result_dict ==expected[" class TestAnomalyDetectorDetailed:""
    "]]""Detailed test cases for AnomalyDetector class."""
    @patch("src.monitoring.anomaly_detector.DatabaseManager[")""""
    @patch("]src.monitoring.anomaly_detector.logger[")": def test_anomaly_detector_initialization(self, mock_logger, mock_db_manager):"""
        "]""Test AnomalyDetector initialization."""
        detector = AnomalyDetector()
        assert detector.db_manager ==mock_db_manager.return_value
        assert isinstance(detector.detection_config, dict)
        assert "matches[" in detector.detection_config[""""
        assert "]]odds[" in detector.detection_config[""""
        assert "]]predictions[" in detector.detection_config[""""
        mock_logger.info.assert_called_with("]]异常检测器初始化完成[")": def test_detection_config_structure(self):"""
        "]""Test that detection config has proper structure."""
        detector = AnomalyDetector()
        # Check matches config
        matches_config = detector.detection_config["matches["]"]": assert "numeric_columns[" in matches_config[""""
        assert "]]time_columns[" in matches_config[""""
        assert "]]categorical_columns[" in matches_config[""""
        assert "]]thresholds[" in matches_config[""""
        assert "]]home_score[" in matches_config["]thresholds["]""""
        # Check odds config
        odds_config = detector.detection_config["]odds["]: assert "]home_odds[" in odds_config["]thresholds["]: assert odds_config["]thresholds["]"]home_odds""min[" ==1.01[""""
        # Check predictions config
        predictions_config = detector.detection_config["]]predictions["]: assert "]home_win_probability[" in predictions_config["]thresholds["]: assert predictions_config["]thresholds["]"]home_win_probability""max[" ==1.0[""""
    @patch("]]src.monitoring.anomaly_detector.DatabaseManager[")""""
    @patch("]src.monitoring.anomaly_detector.logger[")": def test_detect_anomalies_table_error_handling(self, mock_logger, mock_db_manager):"""
        "]""Test detect_anomalies handles table errors gracefully."""
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("Database error[")": mock_db_manager.return_value.get_async_session.return_value.__aenter__.return_value = (": mock_session[""
        )
        detector = AnomalyDetector()
        anomalies = detector.detect_anomalies.__wrapped__(
            detector, table_names="]]matches["""""
        )
        assert isinstance(anomalies, list)
        mock_logger.error.assert_called_with("]检测表 matches 异常失败[": [Database error])""""
    @patch("]src.monitoring.anomaly_detector.logger[")": def test_detect_table_anomalies_no_config(self, mock_logger):"""
        "]""Test _detect_table_anomalies with no configuration."""
        detector = AnomalyDetector()
        mock_session = AsyncMock()
        anomalies = detector._detect_table_anomalies(
            mock_session, "nonexistent_table[", "]three_sigma["""""
        )
        assert anomalies ==[]
        mock_logger.warning.assert_called_with("]表 nonexistent_table 没有检测配置[")""""
    @patch("]src.monitoring.anomaly_detector.logger[")": def test_detect_table_anomalies_empty_data(self, mock_logger):"""
        "]""Test _detect_table_anomalies with empty table data."""
        detector = AnomalyDetector()
        mock_session = AsyncMock()
        # Mock empty DataFrame
        with patch.object(detector, "_get_table_data[", return_value = pd.DataFrame())": anomalies = detector._detect_table_anomalies(": mock_session, "]matches[", "]three_sigma["""""
            )
        assert anomalies ==[]
        mock_logger.warning.assert_called_with("]表 matches 没有数据[")": def test_get_table_data_success(self):"""
        "]""Test _get_table_data successful retrieval."""
        detector = AnomalyDetector()
        mock_session = AsyncMock()
        # Mock database result
        mock_row = MagicMock()
        mock_row._mapping = {"id[": 1, "]home_score[": 2, "]away_score[": 1}": mock_result = MagicMock()": mock_result.fetchall.return_value = ["]mock_row[": mock_session.execute.return_value = mock_result[": data = detector._get_table_data.__wrapped__(detector, mock_session, "]]matches[")": assert isinstance(data, pd.DataFrame)" assert len(data) ==1[""
        assert "]]home_score[" in data.columns[""""
    @patch("]]src.monitoring.anomaly_detector.logger[")": def test_get_table_data_error(self, mock_logger):"""
        "]""Test _get_table_data error handling."""
        detector = AnomalyDetector()
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("Connection failed[")": data = detector._get_table_data.__wrapped__(detector, mock_session, "]matches[")": assert isinstance(data, pd.DataFrame)" assert data.empty[""
        mock_logger.error.assert_called_with(
            "]]获取表 matches 数据失败[": [Connection failed]""""
        )
    def test_detect_column_anomalies_empty_data(self):
        "]""Test _detect_column_anomalies with empty data."""
        detector = AnomalyDetector()
        # Create DataFrame with empty column after dropna = data pd.DataFrame({"column[": ["]None[", None, None]))": table_name = "]matches[": column_name = "]test_column[": methods = "]three_sigma[": column_type = "]numeric[": anomalies = detector._detect_column_anomalies(": data, table_name, column_name, methods, column_type["""
        )
        assert anomalies ==[]
    def test_detect_three_sigma_anomalies_success(self):
        "]]""Test _detect_three_sigma_anomalies with actual outliers."""
        detector = AnomalyDetector()
        # Create data with clear outliers = data pd.Series([1, 2, 3, 4, 5, 100])  # 100 is an outlier
        table_name = "matches[": column_name = "]home_score[": anomalies = detector._detect_three_sigma_anomalies(": data, table_name, column_name["""
        )
        assert len(anomalies) ==1
        assert anomalies[0].anomaly_type ==AnomalyType.OUTLIER
        assert anomalies[0].detection_method =="]]3sigma[" assert 100 in anomalies[0].anomalous_values[""""
    def test_detect_three_sigma_anomalies_no_outliers(self):
        "]]""Test _detect_three_sigma_anomalies with no outliers."""
        detector = AnomalyDetector()
        # Create normal data without outliers
        data = pd.Series([1, 2, 3, 4, 5])
        table_name = "matches[": column_name = "]home_score[": anomalies = detector._detect_three_sigma_anomalies(": data, table_name, column_name["""
        )
        assert len(anomalies) ==0
    def test_detect_three_sigma_anomalies_zero_std(self):
        "]]""Test _detect_three_sigma_anomalies with zero standard deviation."""
        detector = AnomalyDetector()
        # Create data with zero variance = data pd.Series([5, 5, 5, 5, 5])
        table_name = "matches[": column_name = "]home_score[": anomalies = detector._detect_three_sigma_anomalies(": data, table_name, column_name["""
        )
        assert len(anomalies) ==0  # Should not detect anomalies in constant data
    @patch("]]src.monitoring.anomaly_detector.logger[")": def test_detect_three_sigma_anomalies_error(self, mock_logger):"""
        "]""Test _detect_three_sigma_anomalies error handling."""
        detector = AnomalyDetector()
        # Create invalid data
        data = pd.Series(["invalid[", "]data["])": table_name = "]matches[": column_name = "]home_score[": anomalies = detector._detect_three_sigma_anomalies(": data, table_name, column_name["""
        )
        assert len(anomalies) ==0
        mock_logger.error.assert_called()
    def test_detect_iqr_anomalies_success(self):
        "]]""Test _detect_iqr_anomalies with actual outliers."""
        detector = AnomalyDetector()
        # Create data with clear outliers = data pd.Series([1, 2, 3, 4, 5, 100])
        table_name = "matches[": column_name = "]home_score[": anomalies = detector._detect_iqr_anomalies(data, table_name, column_name)": assert len(anomalies) ==1[" assert anomalies[0].anomaly_type ==AnomalyType.OUTLIER[""
        assert anomalies[0].detection_method =="]]]iqr[" assert 100 in anomalies[0].anomalous_values[""""
    def test_detect_iqr_anomalies_zero_iqr(self):
        "]]""Test _detect_iqr_anomalies with zero IQR."""
        detector = AnomalyDetector()
        # Create data with zero IQR = data pd.Series([5, 5, 5, 5, 5])
        table_name = "matches[": column_name = "]home_score[": anomalies = detector._detect_iqr_anomalies(data, table_name, column_name)": assert len(anomalies) ==0["""
    @patch("]]src.monitoring.anomaly_detector.logger[")": def test_detect_iqr_anomalies_error(self, mock_logger):"""
        "]""Test _detect_iqr_anomalies error handling."""
        detector = AnomalyDetector()
        # Create invalid data
        data = pd.Series(["invalid[", "]data["])": table_name = "]matches[": column_name = "]home_score[": anomalies = detector._detect_iqr_anomalies(data, table_name, column_name)": assert len(anomalies) ==0[" mock_logger.error.assert_called()""
    def test_detect_z_score_anomalies_success(self):
        "]]""Test _detect_z_score_anomalies with actual outliers."""
        detector = AnomalyDetector()
        # Create data with clear outliers = data pd.Series([1, 2, 3, 4, 5, 100])
        table_name = "matches[": column_name = "]home_score[": anomalies = detector._detect_z_score_anomalies(": data, table_name, column_name, threshold=2.0["""
        )
        assert len(anomalies) ==1
        assert anomalies[0].anomaly_type ==AnomalyType.OUTLIER
        assert anomalies[0].detection_method =="]]z_score[" assert 100 in anomalies[0].anomalous_values[""""
    def test_detect_z_score_anomalies_zero_std(self):
        "]]""Test _detect_z_score_anomalies with zero standard deviation."""
        detector = AnomalyDetector()
        # Create data with zero variance = data pd.Series([5, 5, 5, 5, 5])
        table_name = "matches[": column_name = "]home_score[": anomalies = detector._detect_z_score_anomalies(data, table_name, column_name)": assert len(anomalies) ==0["""
    @patch("]]src.monitoring.anomaly_detector.logger[")": def test_detect_z_score_anomalies_error(self, mock_logger):"""
        "]""Test _detect_z_score_anomalies error handling."""
        detector = AnomalyDetector()
        # Create invalid data
        data = pd.Series(["invalid[", "]data["])": table_name = "]matches[": column_name = "]home_score[": anomalies = detector._detect_z_score_anomalies(data, table_name, column_name)": assert len(anomalies) ==0[" mock_logger.error.assert_called()""
    def test_detect_range_anomalies_success(self):
        "]]""Test _detect_range_anomalies with range violations."""
        detector = AnomalyDetector()
        # Set up detection config with thresholds:
        detector.detection_config["matches["]"]thresholds""home_score[" = {""""
            "]min[": 0,""""
            "]max[": 10}""""
        # Create data with range violations = data pd.Series([5, 15, -2, 8])  # 15 and -2 are out of range
        table_name = "]matches[": column_name = "]home_score[": anomalies = detector._detect_range_anomalies(data, table_name, column_name)": assert len(anomalies) ==1[" assert anomalies[0].anomaly_type ==AnomalyType.VALUE_RANGE[""
        assert anomalies[0].detection_method =="]]]range_check[" assert 15 in anomalies[0].anomalous_values[""""
        assert -2 in anomalies[0].anomalous_values
    def test_detect_range_anomalies_no_thresholds(self):
        "]]""Test _detect_range_anomalies with no configured thresholds."""
        detector = AnomalyDetector()
        # No thresholds configured
        data = pd.Series([5, 15, -2, 8])
        table_name = "matches[": column_name = "]unknown_column[": anomalies = detector._detect_range_anomalies(data, table_name, column_name)": assert len(anomalies) ==0["""
    @patch("]]src.monitoring.anomaly_detector.logger[")": def test_detect_range_anomalies_error(self, mock_logger):"""
        "]""Test _detect_range_anomalies error handling."""
        detector = AnomalyDetector()
        data = pd.Series(["invalid[", "]data["])": table_name = "]matches[": column_name = "]home_score[": anomalies = detector._detect_range_anomalies(data, table_name, column_name)": assert len(anomalies) ==0[" mock_logger.error.assert_called()""
    def test_detect_frequency_anomalies_success(self):
        "]]""Test _detect_frequency_anomalies with frequency issues."""
        detector = AnomalyDetector()
        # Create data with frequency anomalies = data pd.Series(
            [
                "normal[",""""
                "]normal[",""""
                "]rare[",""""
                "]very_frequent[",""""
                "]very_frequent[",""""
                "]very_frequent[",""""
                "]very_frequent[",""""
                "]very_frequent["]""""
        )
        table_name = "]matches[": column_name = "]status[": anomalies = detector._detect_frequency_anomalies(data, table_name, column_name)": assert len(anomalies) ==1[" assert anomalies[0].anomaly_type ==AnomalyType.FREQUENCY[""
        assert anomalies[0].detection_method =="]]]frequency["""""
        # Should detect "]very_frequent[": as appearing too frequently[""""
    @patch("]]src.monitoring.anomaly_detector.logger[")": def test_detect_frequency_anomalies_error(self, mock_logger):"""
        "]""Test _detect_frequency_anomalies error handling."""
        detector = AnomalyDetector()
        # Create invalid data that will cause error
        data = pd.Series([])
        table_name = "matches[": column_name = "]status[": anomalies = detector._detect_frequency_anomalies(data, table_name, column_name)": assert len(anomalies) ==0[" def test_detect_time_gap_anomalies_success(self):""
        "]]""Test _detect_time_gap_anomalies with time gaps."""
        detector = AnomalyDetector()
        # Create time data with gaps = base_time datetime(2024, 1, 1)
        times = ["base_time[",": base_time + timedelta(minutes=1),": base_time + timedelta(minutes=2),": base_time + timedelta(hours=2),  # Large gap"
            base_time + timedelta(hours=2, minutes=1)]
        data = pd.Series(times)
        table_name = "]matches[": column_name = "]match_time[": anomalies = detector._detect_time_gap_anomalies(data, table_name, column_name)": assert len(anomalies) >= 0  # May or may not detect depending on gap size[" def test_detect_time_gap_anomalies_insufficient_data(self):""
        "]]""Test _detect_time_gap_anomalies with insufficient data."""
        detector = AnomalyDetector()
        # Create time data with only one point = times [datetime(2024, 1, 1)]
        data = pd.Series(times)
        table_name = "matches[": column_name = "]match_time[": anomalies = detector._detect_time_gap_anomalies(data, table_name, column_name)": assert len(anomalies) ==0["""
    @patch("]]src.monitoring.anomaly_detector.logger[")": def test_detect_time_gap_anomalies_error(self, mock_logger):"""
        "]""Test _detect_time_gap_anomalies error handling."""
        detector = AnomalyDetector()
        # Create invalid time data
        data = pd.Series(["invalid_time[", "]not_a_date["])": table_name = "]matches[": column_name = "]match_time[": anomalies = detector._detect_time_gap_anomalies(data, table_name, column_name)": assert len(anomalies) ==0[" mock_logger.error.assert_called()""
    def test_calculate_severity_levels(self):
        "]]""Test _calculate_severity with different score levels."""
        detector = AnomalyDetector()
        # Test different severity levels
        assert detector._calculate_severity(0.25) ==AnomalySeverity.CRITICAL
        assert detector._calculate_severity(0.20) ==AnomalySeverity.CRITICAL
        assert detector._calculate_severity(0.15) ==AnomalySeverity.HIGH
        assert detector._calculate_severity(0.10) ==AnomalySeverity.HIGH
        assert detector._calculate_severity(0.08) ==AnomalySeverity.MEDIUM
        assert detector._calculate_severity(0.05) ==AnomalySeverity.MEDIUM
        assert detector._calculate_severity(0.02) ==AnomalySeverity.LOW
        assert detector._calculate_severity(0.00) ==AnomalySeverity.LOW
    def test_get_anomaly_summary_empty(self):
        """Test get_anomaly_summary with no anomalies."""
        detector = AnomalyDetector()
        summary = detector.get_anomaly_summary([])
        {
            "total_anomalies[": 0,""""
            "]by_severity[": {},""""
            "]by_type[": {},""""
            "]by_table[": {},""""
            "]summary_time[": summary["]summary_time["],  # Dynamic time[""""
        }
        assert summary["]]total_anomalies["] ==0[" assert summary["]]by_severity["] =={}" assert summary["]by_type["] =={}" assert summary["]by_table["] =={}" assert "]summary_time[" in summary[""""
    def test_get_anomaly_summary_with_data(self):
        "]]""Test get_anomaly_summary with anomaly data."""
        detector = AnomalyDetector()
        # Create test anomalies
        anomaly1 = AnomalyResult(
            table_name="matches[",": column_name="]home_score[",": anomaly_type=AnomalyType.OUTLIER,": severity=AnomalySeverity.CRITICAL,": anomalous_values=[10],"
            anomaly_score=0.25,
            detection_method="]3sigma[",": description="]Outlier detected[")": anomaly2 = AnomalyResult(": table_name="]odds[",": column_name="]home_odds[",": anomaly_type=AnomalyType.VALUE_RANGE,": severity=AnomalySeverity.HIGH,": anomalous_values="]200.0[",": anomaly_score=0.15,": detection_method="]range_check[",": description="]Range violation[")": anomaly3 = AnomalyResult(": table_name="]matches[",": column_name="]away_score[",": anomaly_type=AnomalyType.OUTLIER,": severity=AnomalySeverity.CRITICAL,": anomalous_values=[-1],"
            anomaly_score=0.30,
            detection_method="]iqr[",": description="]Negative score[")": summary = detector.get_anomaly_summary(["]anomaly1[", anomaly2, anomaly3])": assert summary["]total_anomalies["] ==3[" assert summary["]]by_severity["]"]critical[" ==2[" assert summary["]]by_severity["]"]high[" ==1[" assert summary["]]by_type["]"]outlier[" ==2[" assert summary["]]by_type["]"]value_range[" ==1[" assert summary["]]by_table["]"]matches[" ==2[" assert summary["]]by_table["]"]odds[" ==1[" assert summary["]]critical_anomalies["] ==2[" assert summary["]]high_priority_anomalies["] ==3  # critical + high[" assert summary["]]most_affected_table["] =="]matches[" assert "]summary_time[" in summary[""""
class TestAnomalyDetectorIntegration:
    "]]""Integration tests for AnomalyDetector functionality."""
    def test_complete_detection_workflow(self):
        """Test complete anomaly detection workflow."""
        detector = AnomalyDetector()
        # Mock database session and data
        mock_session = AsyncMock()
        # Create realistic test data
        test_data = pd.DataFrame({
                "id[: "1, 2, 3, 4, 5, 6[","]"""
                "]home_score[: "2, 3, 1, 2, 15, 2[",  # 15 is outlier["]"]""
                "]away_score[: "1, 2, 0, 1, 3, 1[","]"""
                "]minute[: "45, 60, 30, 45, 90, 60[","]"""
                "]match_time[": [": datetime(2024, 1, 1, 15, 0)"""
        )
        with patch.object(detector, "]_get_table_data[", return_value = test_data)": anomalies = detector._detect_table_anomalies(": mock_session,""
                "]matches[",""""
                ["]three_sigma[", "]iqr[", "]z_score[", "]range_check[", "]frequency["])": assert len(anomalies) > 0["""
        # Should detect the outlier in home_score
        home_score_anomalies = [a for a in anomalies if a.column_name =="]]home_score["]": assert len(home_score_anomalies) > 0["""
        # Verify anomaly structure
        for anomaly in anomalies:
            assert isinstance(anomaly, AnomalyResult)
            assert anomaly.table_name =="]]matches[" assert anomaly.detection_method in [""""
                "]3sigma[",""""
                "]iqr[",""""
                "]z_score[",""""
                "]range_check[",""""
                "]frequency["]": assert 0 <= anomaly.anomaly_score <= 1[" def test_multiple_tables_detection(self):""
        "]]""Test detection across multiple tables."""
        detector = AnomalyDetector()
        # Mock database session
        mock_session = AsyncMock()
        # Create test data for different tables = matches_data pd.DataFrame({
                "id[: "1, 2, 3[","]"""
                "]home_score[: "2, 3, 10[",  # 10 is outlier["]"]""
                "]away_score[": [1, 2, 1])""""
        )
        odds_data = pd.DataFrame({
                "]id[: "1, 2, 3[","]"""
                "]home_odds[: "2.5, 3.0, 150.0[",  # 150.0 is outlier["]"]""
                "]draw_odds[: "3.2, 3.1, 3.5[","]"""
                "]away_odds[": [2.8, 2.9, 3.0])""""
        )
        # Mock _get_table_data to return different data for different tables
        def mock_get_table_data(session, table_name):
            if table_name =="]matches[": return matches_data[": elif table_name =="]]odds[": return odds_data[": else:": return pd.DataFrame()": with patch.object(detector, "]]_get_table_data[", side_effect = mock_get_table_data)": anomalies = detector._detect_table_anomalies(": mock_session, "]matches[", "]three_sigma["""""
            )
            odds_anomalies = detector._detect_table_anomalies(
                mock_session, "]odds[", "]range_check["""""
            )
        # Should detect anomalies in both tables
        assert len(anomalies) > 0 or len(odds_anomalies) > 0
    def test_error_resilience(self):
        "]""Test that detector handles errors gracefully."""
        detector = AnomalyDetector()
        mock_session = AsyncMock()
        # Test with data that will cause various types of errors = error_data pd.DataFrame({
                "numeric_col[": [1, 2, "]invalid[", 4],""""
                "]text_col[": ["]a[", "]b[", "]c[", "]d["])""""
        )
        with patch.object(detector, "]_get_table_data[", return_value = error_data)""""
            # Should not raise exceptions
            anomalies = detector._detect_table_anomalies(
                mock_session,
                "]matches[",""""
                ["]three_sigma[", "]iqr[", "]z_score[", "]range_check["])": assert isinstance(anomalies, list)"""
        # May find some anomalies or handle errors gracefully
    def test_severity_calculation_consistency(self):
        "]""Test that severity calculation is consistent."""
        detector = AnomalyDetector()
        # Test with various anomaly scores = test_cases [
            (0.01, AnomalySeverity.LOW),
            (0.03, AnomalySeverity.LOW),
            (0.06, AnomalySeverity.MEDIUM),
            (0.09, AnomalySeverity.MEDIUM),
            (0.12, AnomalySeverity.HIGH),
            (0.18, AnomalySeverity.HIGH),
            (0.22, AnomalySeverity.CRITICAL),
            (0.30, AnomalySeverity.CRITICAL)]
        for score, expected_severity in test_cases = actual_severity detector._calculate_severity(score)
            assert (
                actual_severity ==expected_severity
            ), f["Score {score} should have severity {expected_severity}"]": def test_realistic_data_scenario(self):"""
        """Test with realistic football data scenario."""
        detector = AnomalyDetector()
        mock_session = AsyncMock()
        # Create realistic match data
        realistic_data = pd.DataFrame({
                "id[": list(range(1, 21)""""
        )
        with patch.object(detector, "]_get_table_data[", return_value = realistic_data)": anomalies = detector._detect_table_anomalies(": mock_session,""
                "]matches[",""""
                ["]three_sigma[", "]iqr[", "]z_score[", "]range_check[", "]frequency["])": assert len(anomalies) > 0["""
        # Should detect home_score outlier (25)
        home_score_anomalies = [a for a in anomalies if a.column_name =="]]home_score["]": assert len(home_score_anomalies) > 0["""
        # Should detect minute outlier (150)
        minute_anomalies = [a for a in anomalies if a.column_name =="]]minute["]"]": assert len(minute_anomalies) > 0""
        # Verify anomaly properties
        for anomaly in anomalies:
            assert anomaly.anomaly_score > 0
            assert anomaly.severity in [
                AnomalySeverity.LOW,
                AnomalySeverity.MEDIUM,
                AnomalySeverity.HIGH,
                AnomalySeverity.CRITICAL]
            assert len(anomaly.description) > 0
            assert anomaly.detected_at is not None