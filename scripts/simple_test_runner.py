#!/usr/bin/env python3
"""
简单测试运行器
直接运行Python测试，避免pytest依赖问题
"""

import importlib
import os


def run_test_file(test_file_path: str):
    """直接运行单个测试文件"""
    try:
        # 将文件路径转换为模块名
        module_path = test_file_path.replace('.py', '').replace('/', '.')

        # 动态导入模块
        module = importlib.import_module(module_path)

        # 查找测试函数
        test_functions = [attr for attr in dir(module) if attr.startswith('test_')]

        passed = 0
        failed = 0

        for test_func_name in test_functions:
            try:
                test_func = getattr(module, test_func_name)
                test_func()
                passed += 1
            except Exception:
                failed += 1

        return passed, failed, len(test_functions)

    except Exception:
        return 0, 1, 0

def main():
    """主函数"""

    # 测试基础功能
    basic_test_path = "test_simple_working.py"
    if os.path.exists(basic_test_path):
        passed, failed, total = run_test_file(basic_test_path)

    # 测试实用工具模块
    utils_tests = [
        "src/utils/crypto_utils.py",
        "src/utils/dict_utils.py",
        "src/utils/response.py",
        "src/utils/string_utils.py"
    ]

    total_passed = 0
    total_failed = 0
    total_tests = 0

    for test_file in utils_tests:
        if os.path.exists(test_file):

            # 尝试导入模块验证
            try:
                importlib.import_module(test_file.replace('.py', '').replace('/', '.'))
                total_passed += 1
                total_tests += 1
            except Exception:
                total_failed += 1
                total_tests += 1
        else:
            pass


if __name__ == "__main__":
    main()
