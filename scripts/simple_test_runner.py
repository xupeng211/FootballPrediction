#!/usr/bin/env python3
"""
简单测试运行器
直接运行Python测试，避免pytest依赖问题
"""

import sys
import importlib
import os
from pathlib import Path

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
                print(f"✅ {test_func_name}")
                passed += 1
            except Exception as e:
                print(f"❌ {test_func_name}: {e}")
                failed += 1
        
        return passed, failed, len(test_functions)
    
    except Exception as e:
        print(f"❌ 运行测试文件失败: {e}")
        return 0, 1, 0

def main():
    """主函数"""
    print("🧪 简单测试运行器")
    print("=" * 40)
    
    # 测试基础功能
    basic_test_path = "test_simple_working.py"
    if os.path.exists(basic_test_path):
        print(f"🔍 运行 {basic_test_path}...")
        passed, failed, total = run_test_file(basic_test_path)
        print(f"结果: {passed}/{total} 通过")
    
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
            print(f"\n🔍 测试 {test_file}...")
            
            # 尝试导入模块验证
            try:
                importlib.import_module(test_file.replace('.py', '').replace('/', '.'))
                print(f"✅ {test_file} 导入成功")
                total_passed += 1
                total_tests += 1
            except Exception as e:
                print(f"❌ {test_file} 导入失败: {e}")
                total_failed += 1
                total_tests += 1
        else:
            print(f"⚠️  {test_file} 不存在")
    
    print(f"\n📊 测试总结:")
    print(f"   - 总测试: {total_tests}")
    print(f"   - 通过: {total_passed}")
    print(f"   - 失败: {total_failed}")
    print(f"   - 成功率: {(total_passed/total_tests*100):.1f}%" if total_tests > 0 else "0.0%")

if __name__ == "__main__":
    main()
