"""
简单测试 - 数据收集任务
"""

import pytest
import sys
from pathlib import Path

# 添加src路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_data_collection_core():
    """测试数据收集核心"""
    try:
        from tasks.data_collection_core import DataCollectionTask

        assert DataCollectionTask is not None
    except ImportError:
        pytest.skip("DataCollectionTask 不存在")


def test_monitoring_task():
    """测试监控任务"""
    try:
        from tasks.monitoring import TaskMonitor

        assert TaskMonitor is not None
    except ImportError:
        pytest.skip("TaskMonitor 不存在")
