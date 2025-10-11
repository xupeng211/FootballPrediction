from src.data.processing.football_data_cleaner_mod import FootballDataCleaner
from src.data.processing.missing_data_handler import MissingDataHandler


def test_data_cleaner():
    cleaner = FootballDataCleaner()
    assert cleaner is not None
    assert hasattr(cleaner, "clean_data")


def test_missing_data_handler():
    handler = MissingDataHandler()
    assert handler is not None
    assert hasattr(handler, "handle_missing")


def test_feature_store():
    from src.data.features.feature_store import FeatureStore

    store = FeatureStore()
    assert store is not None
