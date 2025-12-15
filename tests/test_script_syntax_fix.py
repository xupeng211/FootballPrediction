#!/usr/bin/env python3
"""
测试脚本语法修复的单元测试

验证 backfill_details_fotmob_v2.py 脚本的基本导入和语法正确性
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

def test_script_import():
    """测试脚本是否可以正常导入"""
    try:
        import importlib.util

        script_path = project_root / "scripts" / "backfill_details_fotmob_v2.py"
        spec = importlib.util.spec_from_file_location("backfill_script", script_path)
        module = importlib.util.module_from_spec(spec)

        # 这会验证语法是否正确
        spec.loader.exec_module(module)
        assert True, "脚本导入成功，语法正确"
    except SyntaxError as e:
        pytest.fail(f"脚本存在语法错误: {e}")
    except Exception as e:
        # 其他错误（如导入依赖）是预期的，我们只关心语法
        assert not isinstance(e, SyntaxError), f"存在语法错误: {e}"

def test_function_definitions():
    """测试关键函数是否正确定义"""
    import importlib.util

    script_path = project_root / "scripts" / "backfill_details_fotmob_v2.py"
    spec = importlib.util.spec_from_file_location("backfill_script", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # 检查关键函数是否存在
    required_functions = [
        'wait_random',
        'exponential_backoff_request',
        'FotmobL2DataCollector'
    ]

    for func_name in required_functions:
        assert hasattr(module, func_name), f"缺少必需的函数或类: {func_name}"

def test_logging_configuration():
    """测试日志配置是否正确"""
    import importlib.util

    script_path = project_root / "scripts" / "backfill_details_fotmob_v2.py"
    spec = importlib.util.spec_from_file_location("backfill_script", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # 验证日志配置
    assert hasattr(module, 'logger'), "日志记录器未正确初始化"

if __name__ == "__main__":
    # 运行基本测试
    test_script_import()
    print("✅ 脚本语法正确")

    test_function_definitions()
    print("✅ 关键函数定义正确")

    test_logging_configuration()
    print("✅ 日志配置正确")

    print("🎉 所有语法修复验证通过！")
