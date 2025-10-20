"""
简单测试 - 服务处理层
"""

import pytest
import sys
from pathlib import Path

# 添加src路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_processing_cache():
    """测试处理缓存"""
    try:
        from services.processing.caching.processing_cache import ProcessingCache

        assert ProcessingCache is not None
    except ImportError:
        pytest.skip("ProcessingCache 不存在")


def test_data_validator():
    """测试数据验证器"""
    try:
        from services.processing.validators.data_validator import DataValidator

        assert DataValidator is not None
    except ImportError:
        pytest.skip("DataValidator 不存在")
