#!/usr/bin/env python3
"""
测试配置导入耗时
"""
import time
import sys

def test_config_import():
    """测试配置模块导入"""
    print("测试配置模块导入...")

    # 测试导入pydantic相关
    start = time.time()
    try:
        from pydantic import Field
        from pydantic_settings import BaseSettings
        print(f"Pydantic导入耗时: {time.time() - start:.3f}秒")
    except ImportError as e:
        print(f"Pydantic导入失败: {e}")

    # 测试导入config模块
    start = time.time()
    from src.core.config import Config
    print(f"Config类导入耗时: {time.time() - start:.3f}秒")

    # 测试创建Config实例
    start = time.time()
    config = Config()
    elapsed = time.time() - start
    print(f"Config实例创建耗时: {elapsed:.3f}秒")

    return elapsed < 2.0

if __name__ == "__main__":
    success = test_config_import()
    if success:
        print("\n✅ 配置导入正常")
    else:
        print("\n❌ 配置导入耗时过长")
    sys.exit(0 if success else 1)