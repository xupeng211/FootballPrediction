"""
Unit tests for the anomaly detector.
"""

from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from src.monitoring.anomaly_detector import (AnomalyDetector, AnomalyResult,
                                             AnomalyType)


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
            "src.monitoring.anomaly_detector.DatabaseManager",
            lambda: mock_db_manager[0],
        )
        detector = AnomalyDetector()
        yield detector, mock_db_manager[1]


@pytest.mark.asyncio
async def test_detect_anomalies_no_tables(anomaly_detector):
    """Test anomaly detection with no tables specified."""
    detector, _ = anomaly_detector
    anomalies = await detector.detect_anomalies(table_names=[])
    assert len(anomalies) == 0


@pytest.mark.asyncio
async def test_detect_anomalies_with_empty_data(anomaly_detector):
    """Test anomaly detection when the table has no data."""
    detector, mock_session = anomaly_detector
    mock_session.execute.return_value.fetchall.return_value = []

    anomalies = await detector.detect_anomalies(table_names=["matches"])
    assert len(anomalies) == 0


@pytest.mark.asyncio
async def test_detect_anomalies_with_normal_data(anomaly_detector):
    """Test anomaly detection with normal data."""
    detector, _ = anomaly_detector
    mock_data = pd.DataFrame({"home_score": [1, 2, 1, 0, 2]})

    async def mock_get_table_data(*args, **kwargs):
        return mock_data

    detector._get_table_data = mock_get_table_data

    anomalies = await detector.detect_anomalies(table_names=["matches"])
    assert len(anomalies) == 0


@pytest.mark.asyncio
async def test_detect_anomalies_with_outliers(anomaly_detector):
    """Test anomaly detection with clear outliers."""
    detector, _ = anomaly_detector
    mock_data = pd.DataFrame({"home_score": [1, 2, 1, 0, 2, 100]})

    async def mock_get_table_data(*args, **kwargs):
        return mock_data

    detector._get_table_data = mock_get_table_data

    anomalies = await detector.detect_anomalies(table_names=["matches"])
    assert len(anomalies) > 0
    assert anomalies[0].anomaly_type == AnomalyType.OUTLIER
    assert 100 in anomalies[0].anomalous_values


@pytest.mark.asyncio
async def test_get_anomaly_summary(anomaly_detector):
    """Test the summary generation from a list of anomalies."""
    detector, _ = anomaly_detector
    anomalies = [
        MagicMock(
            spec=AnomalyResult,
            severity=MagicMock(value="high"),
            anomaly_type=MagicMock(value="outlier"),
            table_name="matches",
        ),
        MagicMock(
            spec=AnomalyResult,
            severity=MagicMock(value="low"),
            anomaly_type=MagicMock(value="range_check"),
            table_name="odds",
        ),
    ]
    summary = await detector.get_anomaly_summary(anomalies)
    assert summary["total_anomalies"] == 2
    assert summary["by_severity"]["high"] == 1
    assert summary["by_table"]["matches"] == 1
