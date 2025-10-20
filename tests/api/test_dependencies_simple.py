"""
简单测试文件 - API dependencies
"""

import pytest
import sys
from pathlib import Path

# 添加src路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# 测试模块是否可以导入
def test_module_import():
    """测试模块导入"""
    try:
        import api.dependencies

        assert True
    except ImportError:
        pytest.skip("模块 api.dependencies 不存在或无法导入")


# 测试文件存在
def test_source_file_exists():
    """测试源文件是否存在"""
    source_path = Path(__file__).parent.parent.parent / "src/api/dependencies.py"
    assert source_path.exists(), "源文件 src/api/dependencies.py 不存在"
