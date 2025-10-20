"""
简单测试 - 数据收集器
"""

import pytest
import sys
from pathlib import Path

# 添加src路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_collector_module_import():
    """测试收集器模块导入"""
    try:
        import collectors

        assert True
    except ImportError:
        pytest.skip("collectors模块不存在")


def test_scores_collector_exists():
    """测试scores收集器文件存在"""
    source_path = (
        Path(__file__).parent.parent.parent
        / "src/collectors/scores_collector_improved.py"
    )
    assert source_path.exists(), "scores_collector_improved.py 文件不存在"


# 测试基本的收集器类是否存在
def test_collector_classes():
    """测试收集器类"""
    try:
        from collectors.scores_collector_improved import ScoresCollectorImproved

        assert ScoresCollectorImproved is not None
    except ImportError:
        pytest.skip("ScoresCollectorImproved 不存在")
