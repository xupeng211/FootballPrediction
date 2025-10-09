"""
Feast Mock 实现
Feast Mock Implementation

为测试环境提供轻量级的 Feast 替代实现。
"""

import os
from typing import Any, Dict, List

ENABLE_FEAST = os.getenv("ENABLE_FEAST", "true").lower() == "true"

try:
    if not ENABLE_FEAST:
        raise ImportError("Feast explicitly disabled via ENABLE_FEAST=false")

    from feast import Entity, FeatureStore, FeatureView, Field, ValueType
    from feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source import (
        PostgreSQLSource,
    )
    from feast.types import Float64, Int64

    HAS_FEAST = True
except ImportError:  # pragma: no cover
    HAS_FEAST = False

    class _MockFeastResult:
        """轻量的Feast查询结果，仅实现 to_df 方法。"""

        def __init__(self, rows: List[Dict[str, Any]]):
            self._rows = rows

        def to_df(self):
            import pandas as _pd

            return _pd.DataFrame(self._rows)

    class MockEntity:
        def __init__(self, name: str, *args, **kwargs):
            self.name = name

    class MockFeatureView:
        def __init__(self, name: str, entities: List[Any], schema=None, *args, **kwargs):
            self.name = name
            self.entities = entities
            self.schema = schema or []

    class MockField:
        def __init__(self, name: str, dtype: Any):
            self.name = name
            self.dtype = dtype

    class MockFloat64:
        pass

    class MockInt64:
        pass

    class MockPostgreSQLSource:
        def __init__(self, *args, **kwargs):
            pass

    class MockValueType:
        INT64 = "INT64"

    class MockFeatureStore:
        """测试友好的Feast替代实现。"""

        def __init__(self, *args, **kwargs):
            self.applied_objects: List[Any] = []

        def apply(self, obj: Any) -> None:
            self.applied_objects.append(obj)

        def get_online_features(
            self, features: List[str], entity_rows: List[Dict[str, Any]]
        ) -> _MockFeastResult:
            enriched_rows: List[Dict[str, Any]] = []
            for row in entity_rows:
                enriched = dict(row)
                for feature in features:
                    short_name = feature.split(":")[-1]
                    enriched.setdefault(short_name, 0.0)
                enriched_rows.append(enriched)
            return _MockFeastResult(enriched_rows)

        def get_historical_features(
            self,
            entity_df: Any,
            features: List[str],
            full_feature_names: bool = False,
        ) -> _MockFeastResult:
            return _MockFeastResult([])

        def push(self, *args, **kwargs) -> None:
            return None

    # 导出 Mock 类
    Entity = MockEntity
    FeatureStore = MockFeatureStore  # type: ignore[assignment]
    FeatureView = MockFeatureView
    Field = MockField
    Float64 = MockFloat64
    Int64 = MockInt64
    PostgreSQLSource = MockPostgreSQLSource
    ValueType = MockValueType