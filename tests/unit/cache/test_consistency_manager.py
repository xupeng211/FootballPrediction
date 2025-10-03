"""Cache consistency manager tests."""

import unittest.mock as mock

import pytest

from src.cache.consistency_manager import CacheConsistencyManager


@pytest.mark.unit
class TestCacheConsistencyManager:
    """Test Cache Consistency Manager."""

    @pytest.fixture
    def mock_redis_manager(self):
        """Create a mock Redis manager."""
        redis_manager = mock.MagicMock()
        # Make adelete an async mock
        redis_manager.adelete = mock.AsyncMock()
        return redis_manager

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        return mock.MagicMock()

    @pytest.fixture
    def consistency_manager(self, mock_redis_manager, mock_db_manager):
        """Create a consistency manager instance."""
        return CacheConsistencyManager(
            redis_manager=mock_redis_manager,
            db_manager=mock_db_manager
        )

    def test_initialization(self, consistency_manager, mock_redis_manager, mock_db_manager):
        """Test manager initialization."""
        assert consistency_manager.redis_manager == mock_redis_manager
        assert consistency_manager.db_manager == mock_db_manager

    @pytest.mark.asyncio
    async def test_invalidate_cache(self, consistency_manager, mock_redis_manager):
        """Test cache invalidation."""
        # Test with keys
        keys = ["key1", "key2", "key3"]
        await consistency_manager.invalidate_cache(keys)

        # Verify Redis manager was called
        mock_redis_manager.adelete.assert_called_once_with(*keys)

    @pytest.mark.asyncio
    async def test_invalidate_cache_empty_list(self, consistency_manager, mock_redis_manager):
        """Test cache invalidation with empty list."""
        # Test with empty keys
        await consistency_manager.invalidate_cache([])

        # Verify Redis manager was not called
        mock_redis_manager.adelete.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_cache_with_db(self, consistency_manager):
        """Test syncing cache with database."""
        # Test method exists and can be called
        await consistency_manager.sync_cache_with_db("match", 123)
        # No assertion needed as it's a placeholder implementation

    @pytest.mark.asyncio
    async def test_warm_cache(self, consistency_manager):
        """Test cache warming."""
        # Test method exists and can be called
        await consistency_manager.warm_cache("match", [1, 2, 3])
        # No assertion needed as it's a placeholder implementation