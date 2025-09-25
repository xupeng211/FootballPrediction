"""慢速健康检查相关的Redis测试。"""

import pytest


@pytest.mark.asyncio
@pytest.mark.slow
async def test_check_redis_basic_functionality():
    """验证Redis健康检查在真实等待下的表现。"""
    from src.api.health import _check_redis

    result = await _check_redis()

    assert result["status"] in ["healthy", "unhealthy"]
    assert (
        "Redis" in result["details"]["message"]
        or "Redis连接失败" in result["details"]["message"]
    )
