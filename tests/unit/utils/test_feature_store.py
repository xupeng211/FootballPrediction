import pytest

from src.data.features.feature_store import FeatureStore


@pytest.mark.unit
def test_feature_store():
    store = FeatureStore()
    assert store is not None


def test_store_methods():
    store = FeatureStore()
    assert hasattr(store, "store_features")
    assert hasattr(store, "retrieve_features")
