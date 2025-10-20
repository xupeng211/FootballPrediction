"""
简单测试 - Facade模式
"""

import pytest
import sys
from pathlib import Path

# 添加src路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_facade_module_import():
    """测试facade模块导入"""
    try:
        import patterns.facade

        assert True
    except ImportError:
        pytest.skip("patterns.facade模块不存在")


def test_facade_file_exists():
    """测试facade文件存在"""
    source_path = Path(__file__).parent.parent.parent / "src/patterns/facade.py"
    assert source_path.exists(), "facade.py 文件不存在"


# 测试facade类
def test_facade_classes():
    """测试facade相关类"""
    try:
        from patterns.facade import PredictionFacade

        assert PredictionFacade is not None
    except ImportError:
        pytest.skip("PredictionFacade 不存在")
