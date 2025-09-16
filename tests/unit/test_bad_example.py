"""
Tests for the bad_example module to improve test coverage.
"""

from src.bad_example import badly_formatted_function


def test_badly_formatted_function_positive():
    """Test badly_formatted_function with a positive number."""
    assert badly_formatted_function(1, 2, 3) == 6


def test_badly_formatted_function_zero():
    """Test badly_formatted_function with zero."""
    assert badly_formatted_function(0, 2, 3) is None


def test_badly_formatted_function_negative():
    """Test badly_formatted_function with a negative number."""
    assert badly_formatted_function(-1, 2, 3) is None
