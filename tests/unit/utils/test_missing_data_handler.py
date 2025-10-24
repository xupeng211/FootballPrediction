from src.data.processing.missing_data_handler import MissingDataHandler
import pytest


@pytest.mark.unit

def test_missing_data_handler():
    handler = MissingDataHandler()
    assert handler is not None


def test_handling_methods():
    handler = MissingDataHandler()
    assert hasattr(handler, "handle_missing")
    assert hasattr(handler, "impute_values")
