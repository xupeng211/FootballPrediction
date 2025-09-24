import json

import pytest

from src.database.types import (
    CompatibleJSON,
    CompatJsonType,
    JsonbType,
    JsonType,
    SQLiteCompatibleJSONB,
    get_json_type,
)

pytestmark = pytest.mark.unit


class _DummyDialect:
    def __init__(self, name: str):
        self.name = name
        self.requested_descriptor = None

    def type_descriptor(self, type_):
        self.requested_descriptor = type_
        return type_


def test_sqlite_compatible_jsonb_loads_dialect_specific_type() -> None:
    jsonb_type = SQLiteCompatibleJSONB()

    pg_dialect = _DummyDialect("postgresql")
    sqlite_dialect = _DummyDialect("sqlite")

    returned_pg = jsonb_type.load_dialect_impl(pg_dialect)
    returned_sqlite = jsonb_type.load_dialect_impl(sqlite_dialect)

    assert isinstance(returned_pg, JSONB)
    assert returned_sqlite.__class__.__name__ == "Text"


def test_sqlite_compatible_jsonb_process_bind_param_handles_various_values() -> None:
    jsonb_type = SQLiteCompatibleJSONB()
    pg_dialect = _DummyDialect("postgresql")
    sqlite_dialect = _DummyDialect("sqlite")

    data = {"team": "A", "score": 2}

    assert jsonb_type.process_bind_param(data, pg_dialect) is data

    sqlite_result = jsonb_type.process_bind_param(data, sqlite_dialect)
    assert isinstance(sqlite_result, str)
    assert json.loads(sqlite_result) == data

    pre_serialized = json.dumps({"valid": True})
    assert (
        jsonb_type.process_bind_param(pre_serialized, sqlite_dialect) == pre_serialized
    )

    non_json_string = "not-json"
    serialized = jsonb_type.process_bind_param(non_json_string, sqlite_dialect)
    assert json.loads(serialized) == non_json_string

    assert jsonb_type.process_bind_param(42, sqlite_dialect) == json.dumps(42)
    assert jsonb_type.process_bind_param(None, sqlite_dialect) is None
    assert jsonb_type.process_bind_param(None, pg_dialect) is None


def test_sqlite_compatible_jsonb_process_result_value_deserializes() -> None:
    jsonb_type = SQLiteCompatibleJSONB()
    pg_dialect = _DummyDialect("postgresql")
    sqlite_dialect = _DummyDialect("sqlite")

    payload = {"key": "value"}
    assert jsonb_type.process_result_value(payload, pg_dialect) is payload

    encoded = json.dumps(payload)
    assert jsonb_type.process_result_value(encoded, sqlite_dialect) == payload

    invalid = "not-json"
    assert jsonb_type.process_result_value(invalid, sqlite_dialect) == invalid
    assert jsonb_type.process_result_value(None, sqlite_dialect) is None
    assert jsonb_type.process_result_value(None, pg_dialect) is None


def test_compatible_json_serialization_roundtrip() -> None:
    compat_type = CompatibleJSON()
    pg_dialect = _DummyDialect("postgresql")
    sqlite_dialect = _DummyDialect("sqlite")

    payload = {"league": "Premier League"}

    assert compat_type.load_dialect_impl(pg_dialect).__class__.__name__ == "JSON"
    assert compat_type.load_dialect_impl(sqlite_dialect).__class__.__name__ == "Text"

    assert compat_type.process_bind_param(payload, pg_dialect) is payload

    sqlite_encoded = compat_type.process_bind_param(payload, sqlite_dialect)
    assert json.loads(sqlite_encoded) == payload

    assert (
        compat_type.process_result_value(json.dumps(payload), sqlite_dialect) == payload
    )
    assert compat_type.process_bind_param(None, sqlite_dialect) is None
    assert compat_type.process_result_value(None, sqlite_dialect) is None
    assert compat_type.process_result_value(None, pg_dialect) is None


def test_get_json_type_helpers_return_new_instances() -> None:
    assert isinstance(JsonType, SQLiteCompatibleJSONB)
    assert isinstance(JsonbType, SQLiteCompatibleJSONB)
    assert isinstance(CompatJsonType, CompatibleJSON)

    assert isinstance(get_json_type(True), SQLiteCompatibleJSONB)
    assert isinstance(get_json_type(False), CompatibleJSON)


from sqlalchemy.dialects.postgresql import JSONB
