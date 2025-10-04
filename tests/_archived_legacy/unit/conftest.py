import pytest

"""Test-wide configuration for unit test suite."""
# Automatically tag every test in tests/unit as a unit test unless overridden.
pytestmark = pytest.mark.unit
