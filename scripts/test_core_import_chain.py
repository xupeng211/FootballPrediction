#!/usr/bin/env python3
"""
测试core模块的导入链
"""
import sys
import time
from functools import wraps

class DetailedImportTracer:
    """详细的导入追踪器"""
    def __init__(self):
        self.times = {}
        self.original_import = __builtins__.__import__
        self.level = 0

    def __call__(self, name, globals=None, locals=None, fromlist=(), level=0):
        """追踪导入"""
        indent = "  " * self.level
        start = time.time()

        # 避免递归追踪
        self.level += 1
        if self.level < 10:  # 防止过深的递归
            module = self.original_import(name, globals, locals, fromlist, level)
        else:
            module = self.original_import(name, globals, locals, fromlist, level)
        self.level -= 1

        elapsed = time.time() - start
        if self.level == 0 and elapsed > 0.1:  # 只记录顶级导入
            self.times[name] = elapsed
            print(f"{indent}[导入] {name}: {elapsed:.3f}秒")

        return module

def test_core_import():
    """测试core模块导入"""
    tracer = DetailedImportTracer()
    __builtins__.__import__ = tracer

    print("开始测试core模块导入...\n")

    start = time.time()

    # 逐步导入
    print("1. 导入logging:")
    import logging

    print("\n2. 导入src.core.logger:")
    from src.core.logger import Logger

    print("\n3. 导入src.core.exceptions:")
    from src.core.exceptions import FootballPredictionError

    print("\n4. 导入src.core.config:")
    from src.core.config import Config

    total = time.time() - start
    print(f"\n总时间: {total:.3f}秒")

    return total

if __name__ == "__main__":
    test_core_import()