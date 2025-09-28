"""
Performance tests for the football prediction system.

This module contains performance tests that verify system performance requirements:
- API response times < 100ms for predictions
- Concurrent request handling
- Memory usage optimization
- Database query performance
"""

from .test_api_performance import TestAPIPerformance
from .test_concurrent_requests import TestConcurrentRequests

__all__ = [
    'TestAPIPerformance',
    'TestConcurrentRequests'
]