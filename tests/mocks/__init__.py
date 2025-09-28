"""
Unified mock objects for testing.
"""

from .database_mocks import MockDatabaseManager, MockAsyncSession, MockConnectionPool
from .redis_mocks import MockRedisManager, MockRedisPubSub
from .storage_mocks import MockDataLakeStorage, MockObjectStorage
from .api_mocks import (
    MockAPIClient, MockFootballDataAPI, MockWeatherAPI,
    MockNotificationAPI, MockAnalyticsAPI, MockWebSocketClient, MockRateLimiter
)
from .service_mocks import (
    MockDataProcessingService, MockPredictionService,
    MockFeatureStore, MockCacheService
)

__all__ = [
    'MockDatabaseManager',
    'MockAsyncSession',
    'MockConnectionPool',
    'MockRedisManager',
    'MockRedisPubSub',
    'MockDataLakeStorage',
    'MockObjectStorage',
    'MockAPIClient',
    'MockFootballDataAPI',
    'MockWeatherAPI',
    'MockNotificationAPI',
    'MockAnalyticsAPI',
    'MockWebSocketClient',
    'MockRateLimiter',
    'MockDataProcessingService',
    'MockPredictionService',
    'MockFeatureStore',
    'MockCacheService'
]