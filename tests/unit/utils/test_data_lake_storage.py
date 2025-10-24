from src.data.storage.data_lake_storage import DataLakeStorage
import pytest


@pytest.mark.unit

def test_data_lake_storage():
    storage = DataLakeStorage()
    assert storage is not None


def test_storage_methods():
    storage = DataLakeStorage()
    assert hasattr(storage, "store_data")
    assert hasattr(storage, "retrieve_data")
