"""EventBus DB policy focused tests — no DB, no Docker, source inspection."""

from __future__ import annotations

import importlib
from pathlib import Path
import re
import sys
import types

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"


def _seed_namespace_package(name: str, package_path: Path) -> None:
    """Lightweight namespace package to avoid src/__init__.py side-effects."""
    if name in sys.modules:
        return
    module = types.ModuleType(name)
    module.__path__ = [str(package_path)]  # type: ignore[attr-defined]
    sys.modules[name] = module


# Seed namespace packages so src.config.common can be imported directly
# without loading src/config/__init__.py (which requires pydantic).
_seed_namespace_package("src", SRC_ROOT)
_seed_namespace_package("src.core", SRC_ROOT / "core")
_seed_namespace_package("src.config", SRC_ROOT / "config")

common = importlib.import_module("src.config.common")

DatabaseConfigurationError = common.DatabaseConfigurationError
validate_db_name_for_environment = common.validate_db_name_for_environment
allowed_db_names_for_environment = common.allowed_db_names_for_environment
ALLOWED_DB_NAME = common.ALLOWED_DB_NAME
NON_PRODUCTION_DB_NAMES = common.NON_PRODUCTION_DB_NAMES

EVENT_BUS_PATH = SRC_ROOT / "services" / "event_bus.py"


# ——————————————————————————————————————————————————————————————————————————————
# Source inspection: verify legacy guard is removed and shared policy is used
# ——————————————————————————————————————————————————————————————————————————————


def _read_event_bus_source() -> str:
    return EVENT_BUS_PATH.read_text(encoding="utf-8")


def test_event_bus_does_not_have_legacy_direct_db_name_guard():
    """event_bus.py must no longer contain the direct DB_NAME=football_db equality
    guard that bypassed the shared DB policy."""
    source = _read_event_bus_source()
    pattern = re.compile(r'db_name\s*!=\s*"football_db"')
    assert not pattern.search(source), (
        "Legacy direct DB_NAME=football_db guard still present in event_bus.py. "
        "It should be replaced by validate_db_name_for_environment()."
    )


def test_event_bus_imports_validate_db_name_for_environment():
    """event_bus.py must import the shared DB policy function."""
    source = _read_event_bus_source()
    assert "validate_db_name_for_environment" in source, (
        "event_bus.py must import validate_db_name_for_environment from src.config.common."
    )


def test_event_bus_does_not_compare_db_name_against_football_db():
    """event_bus.py must not directly compare DB_NAME against 'football_db' literal
    as the sole guard condition."""
    source = _read_event_bus_source()
    legacy_if_pattern = re.compile(r'if\s+db_name\s*!=\s*"football_db"\s*:')
    assert not legacy_if_pattern.search(source), (
        "Direct DB_NAME != 'football_db' comparison still present in event_bus.py."
    )


def test_event_bus_calls_validate_db_name_for_environment():
    """event_bus.py must call the shared validation function, not just import it."""
    source = _read_event_bus_source()
    assert "validate_db_name_for_environment(" in source, (
        "event_bus.py must call validate_db_name_for_environment() in main()."
    )


# ——————————————————————————————————————————————————————————————————————————————
# Shared DB policy behavior verification
# ——————————————————————————————————————————————————————————————————————————————


def test_event_bus_policy_accepts_staging_db_name_in_staging_env():
    """Non-production environments must accept football_prediction_staging."""
    result = validate_db_name_for_environment("football_prediction_staging", "staging")
    assert result == "football_prediction_staging"


def test_event_bus_policy_accepts_football_db_in_production():
    """Production must still accept football_db."""
    result = validate_db_name_for_environment("football_db", "production")
    assert result == "football_db"


def test_event_bus_policy_rejects_staging_db_in_production():
    """Production must reject football_prediction_staging (safety boundary)."""
    with pytest.raises(DatabaseConfigurationError):
        validate_db_name_for_environment("football_prediction_staging", "production")


def test_event_bus_policy_rejects_unsafe_db_name():
    """Any environment must reject DB names not in the allowed set."""
    with pytest.raises(DatabaseConfigurationError):
        validate_db_name_for_environment("rogue_database", "development")
    with pytest.raises(DatabaseConfigurationError):
        validate_db_name_for_environment("football-db", "staging")


def test_event_bus_policy_rejects_empty_db_name():
    """Empty DB_NAME must be rejected with a clear error."""
    with pytest.raises(DatabaseConfigurationError):
        validate_db_name_for_environment("", "development")
    with pytest.raises(DatabaseConfigurationError):
        validate_db_name_for_environment(None, "staging")


def test_event_bus_policy_allows_non_prod_names_in_development():
    """All non-production DB names must be allowed in development."""
    for db_name in sorted(NON_PRODUCTION_DB_NAMES):
        result = validate_db_name_for_environment(db_name, "development")
        assert result == db_name


def test_event_bus_policy_production_only_allows_football_db():
    """Production must only allow football_db."""
    allowed = allowed_db_names_for_environment("production")
    assert allowed == frozenset({ALLOWED_DB_NAME})
    assert "football_prediction_staging" not in allowed


def test_event_bus_policy_non_production_allows_staging():
    """Non-production must allow football_prediction_staging."""
    allowed = allowed_db_names_for_environment("staging")
    assert "football_prediction_staging" in allowed
    assert "football_db" in allowed


# ——————————————————————————————————————————————————————————————————————————————
# Integration sanity: old assertions still valid after EventBus fix
# ——————————————————————————————————————————————————————————————————————————————


def test_existing_db_policy_behaviour_unchanged():
    """DB name policy assertions from config_package_test remain valid."""
    assert common.validate_db_name_for_environment("football_db", "production") == "football_db"
    assert (
        common.validate_db_name_for_environment("football_prediction_staging", "staging")
        == "football_prediction_staging"
    )
    assert common.validate_db_name_for_environment("football_test", "testing") == "football_test"
    assert common.validate_db_name_for_environment("test_db", "development") == "test_db"

    with pytest.raises(DatabaseConfigurationError):
        common.validate_db_name_for_environment("football_prediction_staging", "production")
    with pytest.raises(DatabaseConfigurationError):
        common.validate_db_name_for_environment("rogue_database", "development")
    with pytest.raises(DatabaseConfigurationError):
        common.validate_db_name_for_environment("football-db", "staging")
