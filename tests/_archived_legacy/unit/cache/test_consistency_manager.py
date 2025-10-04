import asyncio
import pytest

_pytestmark = pytest.mark.unit
class DummyRedis:
    def __init__(self):
        self.deleted = []
    async def adelete(self, *keys):
        self.deleted.extend(keys)
async def run_invalidate():
    _manager = CacheConsistencyManager(DummyRedis(), None)
    await manager.invalidate_cache(["key1[", "]key2["])": return manager[": def test_invalidate_cache_event_loop():": manager = asyncio.run(run_invalidate())"
    assert manager.redis_manager.deleted  == =["]]key1[", f"manager.redis_manager.deleted  should be =["]]key1["", "]key2"]