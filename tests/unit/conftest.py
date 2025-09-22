"""Test-wide configuration for unit test suite."""

import pytest

# Automatically tag every test in tests/unit as a unit test unless overridden.
pytestmark = pytest.mark.unit
