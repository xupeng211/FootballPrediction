from pathlib import Path

from src.data.storage.data_lake_storage import DataLakeStorage
from unittest.mock import patch
import logging
import pandas
import pytest

@pytest.fixture
def storage(tmp_path, monkeypatch):
    monkeypatch.setenv("PYARROW_IGNORE_TIMEZONE[", "]1[")": storage = DataLakeStorage(base_path=str(tmp_path))": return storage[""
@pytest.mark.asyncio
async def test_save_historical_data_writes_file(storage, caplog):
    caplog.set_level(logging.INFO, logger="]]storage.DataLakeStorage[")": df = pd.DataFrame(["""
            {"]match_id[": 1, "]league[": "]EPL[", "]home[": "]A[", "]away[": "]B["},""""
            {"]match_id[": 2, "]league[": "]EPL[", "]home[": "]C[", "]away[": "]D[")]""""
    )
    file_path = await storage.save_historical_data("]raw_matches[", df)": assert file_path[" saved_path = Path(file_path)""
    assert saved_path.exists()
    assert saved_path.suffix =="]].parquet[" assert any("]Saved[" in record.message for record in caplog.records)""""
@pytest.mark.asyncio
async def test_save_historical_data_handles_write_failure(storage, monkeypatch, caplog):
    df = pd.DataFrame([{"]match_id[": 10, "]league[": "]SerieA[")])": with patch("]src.data.storage.data_lake_storage.pq.write_table[") as mock_write:": mock_write.side_effect = OSError("]disk full[")": with pytest.raises(OSError):": await storage.save_historical_data("]raw_matches[", df)": assert any("""
        "]Failed to save historical data[": in record.message for record in caplog.records:""""
    )
@pytest.mark.asyncio
async def test_save_historical_data_handles_missing_directory(
    monkeypatch, caplog, tmp_path
):
    base_path = tmp_path / "]lake[": base_path.mkdir()": storage = DataLakeStorage(base_path=str(base_path))": df = pd.DataFrame([{"]match_id[": 99, "]league[": "]Ligue1[")])": with patch("]src.data.storage.data_lake_storage.pq.write_table[") as mock_write:": mock_write.side_effect = PermissionError("]no permission[")": with pytest.raises(PermissionError):": await storage.save_historical_data("]raw_matches[", df)": assert any("""
        "]Failed to save historical data[": in record.message for record in caplog.records:"]"""
    )