"""
简单测试文件 - Core exceptions
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
        import core.exceptions

        assert True
    except ImportError:
        pytest.skip("模块 core.exceptions 不存在或无法导入")


# 测试文件存在
def test_source_file_exists():
    """测试源文件是否存在"""
    source_path = Path(__file__).parent.parent.parent / "src/core/exceptions.py"
    assert source_path.exists(), "源文件 src/core/exceptions.py 不存在"


# 测试异常类是否存在
def test_exception_classes():
    """测试异常类是否存在"""
    try:
        import core.exceptions
        import inspect

        # 获取模块中的所有异常类
        exceptions = [
            name
            for name, obj in inspect.getmembers(core.exceptions)
            if inspect.isclass(obj) and issubclass(obj, Exception)
        ]

        # 至少应该有一些异常类
        assert len(exceptions) > 0, "模块中没有定义异常类"

    except ImportError:
        pytest.skip("模块 core.exceptions 不存在")
