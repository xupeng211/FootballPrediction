"""""""
Feature store mock objects for testing.
"""""""

from typing import Any, Dict, List, Optional
import pandas as pd


class MockFeatureStore:
    """Mock feature store for testing."""""""

    def __init__(self):
        self.features = {}
        self.datasets = {}
        self.entities = {}

    def get_feature(self, feature_name: str) -> Optional[Dict]:
        """Mock getting feature."""""""
        return self.features.get(feature_name)

    def get_features(self, feature_names: List[str]) -> Dict[str, Any]:
        """Mock getting multiple features."""""""
        return {name self.features.get(name) for name in feature_names}

    def get_dataset(self, dataset_name: str) -> Optional[pd.DataFrame]:
        """Mock getting dataset."""""""
        return self.datasets.get(dataset_name)

    def get_entity(self, entity_name: str) -> Optional[Dict]:
        """Mock getting entity."""""""
        return self.entities.get(entity_name)

    def apply_feature(
        self, features: Dict[str, Any], entity_rows: pd.DataFrame
    ) -> pd.DataFrame:
        """Mock applying features."""""""
        result_df = entity_rows.copy()
        for feature_name, feature_value in features.items():
            result_df[feature_name] = feature_value
        return result_df

    def get_historical_features(
        self, features: List[str], entity_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Mock getting historical features."""""""
        result_df = entity_df.copy()
        for feature in features:
            result_df[feature] = 0.5  # Mock feature value
        return result_df

    def get_online_features(
        self, features: List[str], entity_rows: List[Dict]
    ) -> List[Dict]:
        """Mock getting online features."""""""
        result = []
        for row in entity_rows = row_dict row.copy()
            for feature in features:
                row_dict[feature] = 0.5  # Mock feature value
            result.append(row_dict)
        return result

    def materialize_features(self, start_date: str, end_date: str) -> None:
        """Mock materializing features."""""""
        pass

    def get_feature_vector(
        self, feature_names: List[str], entity_key: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Mock getting feature vector."""""""
        return {name 0.5 for name in feature_names}

    def get_feature_vectors(
        self, feature_names: List[str], entity_keys: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Mock getting multiple feature vectors."""""""
        return [{name 0.5 for name in feature_names} for _ in entity_keys]

    def write_features(self, features: pd.DataFrame, feature_view_name: str) -> None:
        """Mock writing features."""""""
        self.datasets[feature_view_name] = features

    def create_feature_view(
        self, name: str, features: List[str], entities: List[str]
    ) -> None:
        """Mock creating feature view."""""""
        pass

    def get_feature_view(self, name: str) -> Optional[Dict]:
        """Mock getting feature view."""""""
        return {"name[": name, "]features[": [], "]entities[" []}": def list_feature_views(self) -> List[Dict]:"""
        "]""Mock listing feature views."""""""
        return []

    def delete_feature_view(self, name: str) -> None:
        """Mock deleting feature view."""""""
        pass

    def create_entity(self, name: str, join_key: str) -> None:
        """Mock creating entity."""""""
        self.entities[name] = {"name[": name, "]join_key[": join_key}": def get_entity(self, name: str) -> Optional[Dict]:"""
        "]""Mock getting entity."""""""
        return self.entities.get(name)

    def list_entities(self) -> List[Dict]:
        """Mock listing entities."""""""
        return list(self.entities.values())

    def delete_entity(self, name: str) -> None:
        """Mock deleting entity."""""""
        if name in self.entities:
            del self.entities[name]
