#!/usr/bin/env python3
"""
隔离测试各个模块的导入
"""
import time
import sys
import os

# 设置环境变量禁用某些功能
os.environ['MLFLOW_TRACKING_URI'] = 'file:///tmp/mlflow'

def timed_import(module_path, description):
    """计时导入并显示详细信息"""
    print(f"\n{'='*50}")
    print(f"测试导入: {description}")
    print(f"模块路径: {module_path}")

    start = time.time()
    try:
        # 使用importlib避免预导入
        import importlib
        module = importlib.import_module(module_path)
        elapsed = time.time() - start
        print(f"✓ 导入成功，耗时: {elapsed:.3f}秒")
        return elapsed, module
    except Exception as e:
        elapsed = time.time() - start
        print(f"✗ 导入失败，耗时: {elapsed:.3f}秒")
        print(f"  错误: {e}")
        return elapsed, None

def main():
    print("=== 隔离测试模块导入 ===\n")

    results = []

    # 测试基础模块
    results.append(timed_import("pathlib", "pathlib"))
    results.append(timed_import("json", "json"))
    results.append(timed_import("logging", "logging"))

    # 测试第三方库
    results.append(timed_import("pydantic", "pydantic"))
    results.append(timed_import("pydantic_settings", "pydantic_settings"))

    # 禁用警告
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=UserWarning)

    # 测试项目模块
    results.append(timed_import("src.core.exceptions", "src.core.exceptions"))
    results.append(timed_import("src.core.logger", "src.core.logger"))
    results.append(timed_import("src.core.config", "src.core.config"))

    # 分析结果
    print(f"\n{'='*50}")
    print("导入时间分析:")
    print(f"{'='*50}")

    total_time = 0
    for elapsed, module in results:
        if module:
            total_time += elapsed

    print(f"总导入时间: {total_time:.3f}秒")

    if total_time > 5:
        print("\n❌ 导入时间过长，需要优化")
        return 1
    else:
        print("\n✅ 导入时间可接受")
        return 0

if __name__ == "__main__":
    sys.exit(main())