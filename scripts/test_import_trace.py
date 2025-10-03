#!/usr/bin/env python3
"""
逐步追踪导入耗时
"""
import time
import sys

def timed_import(module_name, description):
    """计时导入"""
    print(f"\n导入 {description}...")
    start = time.time()
    try:
        exec(f"import {module_name}")
        elapsed = time.time() - start
        print(f"  ✓ 耗时: {elapsed:.3f}秒")
        return elapsed
    except Exception as e:
        print(f"  ✗ 错误: {e}")
        return None

def main():
    print("=== 逐步追踪导入耗时 ===\n")

    total_time = 0

    # 1. 基础模块
    total_time += timed_import("src.core.logger", "日志模块")

    # 2. 基础服务类
    total_time += timed_import("src.services.base", "基础服务类")

    # 3. 逐个导入服务类
    total_time += timed_import("src.services.content_analysis", "内容分析服务")
    total_time += timed_import("src.services.user_profile", "用户配置服务")
    total_time += timed_import("src.services.data_processing", "数据处理服务")

    # 4. 服务管理器
    total_time += timed_import("src.services.manager", "服务管理器")

    print(f"\n总导入时间: {total_time:.3f}秒")

    if total_time > 5:
        print("\n❌ 导入时间过长！")
        return 1
    else:
        print("\n✅ 导入时间可接受")
        return 0

if __name__ == "__main__":
    sys.exit(main())